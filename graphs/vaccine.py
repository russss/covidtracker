import pandas as pd
import datetime
from bokeh.models import NumeralTickFormatter, HoverTool
from bokeh.palettes import Greens
from .common import figure, xr_to_cds


def vax_rate_graph(vax_data):
    vax_rate = (
        vax_data.interp(
            date=pd.date_range(vax_data.date.values.min(), vax_data.date.values.max())
        )
        .astype(int)
        .diff("date")
    )
    vax_rate["first_dose_rolling"] = vax_rate["first_dose"].rolling(date=7).mean()
    vax_rate["second_dose_rolling"] = vax_rate["second_dose"].rolling(date=7).mean()
    vax_rate["third_dose_rolling"] = vax_rate["third_dose"].rolling(date=7).mean()
    vax_rate["total_rolling"] = (
        vax_rate["first_dose_rolling"] + vax_rate["second_dose_rolling"] + vax_rate["third_dose_rolling"]
    )

    fig = figure(
        x_range=(vax_rate.date.values.min(), datetime.datetime.now()),
        title="Daily vaccination rate",
        interventions=False,
    )

    ds = xr_to_cds(vax_rate)

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Date", "@date{%a %d %b}"),
                ("First dose", "@first_dose{0,0}"),
                ("Second dose", "@second_dose{0,0}"),
                ("Third dose", "@third_dose{0,0}"),
            ],
            formatters={"@date": "datetime"},
            toggleable=False,
            names=["total"],
        )
    )

    fig.varea_stack(
        source=ds,
        x="date",
        stackers=["first_dose_rolling", "second_dose_rolling", "third_dose_rolling"],
        legend_label=["First dose", "Second dose", "Third dose"],
        color=list(reversed(Greens[3])),
    )

    fig.line(
        source=ds,
        x="date",
        y="total_rolling",
        color="#888888",
        name="total"
    )

    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig


def vax_cumulative_graph(vax_data):
    vax_data = vax_data.interp(
        date=pd.date_range(vax_data.date.values.min(), vax_data.date.values.max())
    )

    vax_data["first_dose_only"] = vax_data.first_dose - vax_data.second_dose
    vax_data["second_dose_only"] = vax_data.second_dose - vax_data.third_dose

    fig = figure(
        title="Total people vaccinated",
        x_range=(vax_data.date.values.min(), datetime.datetime.now()),
        interventions=False,
        y_range=(0, vax_data.first_dose.values.max() * 1.3),
    )

    ds = xr_to_cds(vax_data)

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Date", "@date{%d %b}"),
                ("One dose", "@first_dose_only{0,0}"),
                ("Two doses", "@second_dose{0,0}"),
                ("Three doses", "@third_dose{0,0}"),
                ("Total", "@first_dose{0,0}"),
            ],
            formatters={"@date": "datetime"},
            toggleable=False,
            names=["total"],
        )
    )

    fig.varea_stack(
        source=ds,
        x="date",
        stackers=["third_dose", "second_dose_only", "first_dose_only"],
        color=Greens[3],
        legend_label=["Three doses", "Two doses", "One dose"],
    )
    fig.line(source=ds, x="date", y="first_dose", color="#888888", name="total")
    #fig.line(
    #    x=[pd.to_datetime("2021-02-19"), pd.to_datetime("2021-7-31")],
    #    y=[vax_data.sel(date="2021-2-19")["first_dose"].data, 52534000],
    #    color="#444444",
    #    line_dash="dashed",
    #    legend_label="July Target",
    #)
    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig
