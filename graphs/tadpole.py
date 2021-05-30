import pandas as pd
import xarray as xr
from bokeh.plotting import figure as bokeh_figure
from bokeh.models.tools import HoverTool
from bokeh.transform import factor_cmap
from bokeh.models import NumeralTickFormatter
from .common import xr_to_cds
from . import NATION_COLOURS


def la_tadpole(eng_by_gss, vax_uptake, vaccine_shift=14, tail_days=7):
    vax = vax_uptake.shift(date=vaccine_shift) / 100
    vax['combined'] = vax['first'] * 0.4 + vax['second'] * 0.6

    # Forward fill is necessary due to timing differences between cases and vax
    vax_vs_cases = xr.merge(
        [
            vax,
            (eng_by_gss.diff('date') * 100000 * 7)
            .rolling(date=7)
            .mean()["cases_norm"],
        ]
    ).ffill("date")
    # Drop the most recent 4 days of data to remove incomplete
    vax_vs_cases = vax_vs_cases.where(
        vax_vs_cases.date < vax_vs_cases.date.max() - pd.Timedelta(days=3), drop=True
    )

    gss_prefix = {
        "E": "England",
        "S": "Scotland",
        "N": "Northern Ireland",
        "W": "Wales",
    }

    vax_vs_cases["nation"] = [
        gss_prefix[str(g.values)[0]] for g in vax_vs_cases.gss_code
    ]

    lad_lookup = pd.read_csv('data/lads.csv').set_index('LAD19CD')
    vax_vs_cases['name'] = [lad_lookup.loc[str(g.data)]['LAD19NM'] for g in vax_vs_cases.gss_code]

    history = vax_vs_cases.sel(
        date=slice(
            vax_vs_cases.date.max() - pd.Timedelta(days=tail_days), vax_vs_cases.date.max()
        )
    )

    fig = bokeh_figure(
        width=1200,
        height=700,
        x_range=(-5, int(history.cases_norm.max()) + 5),
        toolbar_location="right",
        sizing_mode="scale_width",
        tools="reset,box_zoom",
        title="Vaccine coverage vs case rate by local authority",
    )
    fig.toolbar.logo = None
    fig.xgrid.visible = False

    xs = []
    ys = []

    for gss in history.gss_code.values:
        data = history.sel(gss_code=gss, drop=True)
        xs.append(data["cases_norm"].values)
        ys.append(data["combined"].values)

    fig.multi_line(xs=xs, ys=ys, color="#777777", width=1.2, alpha=0.3)

    latest_ds = xr_to_cds(
        vax_vs_cases.sel(date=vax_vs_cases.date.max()),
        x_series="cases_norm",
        include_coords=["nation", "name"],
    )

    fig.circle(
        source=latest_ds,
        x="cases_norm",
        y="combined",
        size=7,
        alpha=1,
        line_width=0.5,
        line_color="#444444",
        name="point",
        color=factor_cmap(
            "nation",
            palette=list(NATION_COLOURS.values()),
            factors=list(NATION_COLOURS.keys()),
        ),
    )

    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.yaxis.axis_label = "Combined adult vaccination coverage"
    fig.xaxis.axis_label = "Weekly cases per 100,000 (7-day average)"
    fig.add_tools(
        HoverTool(
            names=["point"],
            tooltips=[
                ("", "@name, @nation"),
                ("Cases", "@cases_norm{0.0} per 100,000"),
                ("First doses", "@first{0.0%}"),
                ("Second doses", "@second{0.0%}"),
                ("Combined vaccination coverage", "@combined{0.0%}"),
            ],
            toggleable=False,
        )
    )
    return fig
