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
    vax_rate["first_dose_rolling"] = vax_rate["first_dose"].rolling(date=7).mean()
    vax_rate["second_dose_rolling"] = vax_rate["second_dose"].rolling(date=7).mean()

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
            ],
            formatters={"@date": "datetime"},
            toggleable=False,
            names=["first_dose", "second_dose"],
        )
    )

    fig.line(
        source=ds,
        x="date",
        y="first_dose",
        legend_label="First dose",
        name="first_dose",
        line_color="#8AB1EB",
    )
    fig.line(
        source=ds,
        x="date",
        y="first_dose_rolling",
        legend_label="First dose (weekly average)",
        name="first_dose_rolling",
        line_color="#3D6CB3",
        line_width=2,
    )
    fig.line(
        source=ds,
        x="date",
        y="second_dose",
        legend_label="Second dose",
        name="second_dose",
        line_color="#EB8A8F",
    )
    fig.line(
        source=ds,
        x="date",
        y="second_dose_rolling",
        legend_label="Second dose (weekly average)",
        name="second_dose_rolling",
        line_color="#B33D43",
        line_width=2,
    )

    # feb_target_rate = (15e6 - vax_data.sel(date="2021-1-11")["first_dose"].data) / (
    #    datetime.date(2021, 2, 15) - datetime.date(2021, 1, 11)
    # ).days

    # fig.line(
    #    x=[pd.to_datetime("2021-1-11"), pd.to_datetime("2021-2-15")],
    #    y=[feb_target_rate, feb_target_rate],
    #    color="#444444",
    #    line_dash="dashed",
    #    legend_label="Mid-February target",
    # )

    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig


def vax_cumulative_graph(vax_data):
    vax_data = vax_data.interp(
        date=pd.date_range(vax_data.date.values.min(), vax_data.date.values.max())
    )

    vax_data["first_dose_only"] = vax_data.first_dose - vax_data.second_dose

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
        stackers=["second_dose", "first_dose_only"],
        color=["#1f77b4", "#aec7e8"],
        legend_label=["Two doses", "One dose"],
    )
    fig.line(source=ds, x="date", y="first_dose", color="#888888", name="total")
    # fig.line(
    #    x=[pd.to_datetime("2021-01-11"), pd.to_datetime("2021-2-15")],
    #    y=[vax_data.sel(date="2021-1-11")["first_dose"].data, 15e6],
    #    color="#444444",
    #    line_dash="dashed",
    #    legend_label="Mid-February target",
    # )
    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig
