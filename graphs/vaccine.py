import pandas as pd
import datetime
from bokeh.models import NumeralTickFormatter, HoverTool
from .common import figure, xr_to_cds


def vax_rate_graph(vax_data):
    vax_rate = (
        vax_data.interp(
            date=pd.date_range(vax_data.date.values.min(), vax_data.date.values.max())
        )
        .astype(int)
        .diff("date")
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
                ("Date", "@date{%d %b}"),
                ("First dose", "@first_dose{0,0}"),
                ("Second dose", "@second_dose{0,0}"),
            ],
            formatters={"@date": "datetime"},
            toggleable=False,
        )
    )

    fig.line(
        source=ds,
        x="date",
        y="first_dose",
        legend_label="First dose",
        line_color="#3D6CB3",
    )
    fig.line(
        source=ds,
        x="date",
        y="second_dose",
        legend_label="Second dose",
        line_color="#B33D43",
    )

    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig


def vax_cumulative_graph(vax_data):
    vax_data = vax_data.interp(
        date=pd.date_range(vax_data.date.values.min(), vax_data.date.values.max())
    )

    vax_data["first_dose_only"] = vax_data.first_dose - vax_data.second_dose

    fig = figure(
        title="Total vaccinations",
        x_range=(vax_data.date.values.min(), datetime.datetime.now()),
        interventions=False,
    )

    ds = xr_to_cds(vax_data)

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Date", "@date{%d %b}"),
                ("One dose", "@first_dose_only{0,0}"),
                ("Two doses", "@second_dose{0,0}"),
                ("Total", "@first_dose{0,0}"),
            ],
            formatters={"@date": "datetime"},
            toggleable=False,
        )
    )

    fig.varea_stack(
        source=ds,
        x="date",
        stackers=["second_dose", "first_dose_only"],
        color=["#1f77b4", "#aec7e8"],
        legend_label=["Two doses", "One dose"],
    )
    fig.line(source=ds, x="date", y="first_dose", color="#888888")
    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig
