import numpy as np
import pandas as pd
import xarray as xr
from itertools import cycle
from datetime import timedelta, date
from bokeh.plotting import figure as bokeh_figure
from bokeh.models import (
    NumeralTickFormatter,
    DatetimeTickFormatter,
    ColumnDataSource,
    DatetimeAxis,
    Span,
    Label,
)
from bokeh.transform import linear_cmap
from bokeh.models.tools import HoverTool
from bokeh.palettes import Dark2, RdYlBu

from util import dict_to_xr
from .common import (
    figure,
    country_hover_tool,
    region_hover_tool,
    xr_to_cds,
    add_provisional,
    max_date,
)

BAR_COLOUR = "#D5DFED"
LINE_COLOUR = ["#3D6CB3", "#B33D43"]

PROVISIONAL_DAYS = 5

NATION_COLOURS = {
    "England": "#E6A6A1",
    "Scotland": "#A1A3E6",
    "Wales": "#A6C78B",
    "Northern Ireland": "#E0C795",
}

nhs_region_pops = {
    "North West": 7012947,
    "North East and Yorkshire": 8566925,
    "Midlands": 10537679,
    "East of England": 6493188,
    "London": 8908081,
    "South East": 8852361,
    "South West": 5605997,
}

nation_populations = dict_to_xr(
    {
        "England": 56287000,
        "Wales": 3152900,
        "Scotland": 5463300,
        "Northern Ireland": 1893700,
    },
    "location",
)

AGE_RANGES = [
    "0-4",
    "5-9",
    "10-14",
    "15-19",
    "20-24",
    "25-29",
    "30-34",
    "35-39",
    "40-44",
    "45-49",
    "50-54",
    "55-59",
    "60-64",
    "65-69",
    "70-74",
    "75-79",
    "80-84",
    "85-89",
    "90+",
]


def stack_datasource(source, series):
    data = {}
    for i in range(0, len(series)):
        y = sum(source.sel(location=loc) for loc in series[0 : i + 1]).values
        data[series[i]] = y

    data["date"] = source["date"].values
    return ColumnDataSource(data)


def uk_cases_graph(uk_cases):
    fig = figure(title="New cases by nation", interventions=False)
    fig.add_tools(country_hover_tool())

    uk_cases_national = uk_cases / nation_populations * 100000 * 7

    layers = ["England", "Scotland", "Wales", "Northern Ireland"]

    for layer in layers:
        label = layer
        fig.line(
            x=uk_cases_national["date"].values,
            y=uk_cases_national.sel(location=layer)["cases_rolling"].values,
            line_width=2,
            line_color=NATION_COLOURS[layer],
            legend_label=label,
            name=layer,
        )

    fig.yaxis.formatter = NumeralTickFormatter(format="0.0")
    fig.yaxis.axis_label = "Weekly cases per 100,000"
    fig.legend.location = "top_left"
    add_provisional(
        fig, start_date=max_date(uk_cases) - timedelta(days=PROVISIONAL_DAYS)
    )
    return fig


def england_deaths(phe_deaths, excess_deaths, uk_cases):
    fig = figure(title="Deaths in England & Wales")

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Date", "$x{%d %b}"),
                ("Deaths", "@deaths{0}"),
                ("Reported deaths", "@deaths_report_date{0}"),
                ("Excess deaths", "@excess_deaths{0}"),
            ],
            formatters={"$x": "datetime"},
            toggleable=False,
        )
    )

    data = phe_deaths.ffill("date").sum("location").diff("date")
    data["deaths_provisional"] = data["deaths"][-7:]
    data["deaths"][-7:] = np.nan
    data["deaths_rolling"] = data["deaths"].rolling(date=7, center=True).mean()

    data["deaths_report_date"] = (
        uk_cases.sel(location=["England", "Wales"])["deaths"]
        .ffill("date")
        .sum("location")
        .diff("date")
        .rolling(date=7, center=True)
        .mean()
    )

    data["excess_deaths"] = excess_deaths["deaths"]
    data["excess_deaths"] = (
        data["excess_deaths"].interpolate_na("date", method="akima") / 7
    ).shift(date=-4)

    data["recorded_deaths"] = excess_deaths["covid_deaths"]
    data["recorded_deaths"] = (
        data["recorded_deaths"].interpolate_na("date", method="akima") / 7
    ).shift(date=-4)

    ds = xr_to_cds(data)

    bar_width = 8640 * 10e3 * 0.7
    fig.vbar(
        x="date",
        top="deaths",
        source=ds,
        width=bar_width,
        legend_label="Deaths (date of death)",
        name="Deaths",
        line_width=0,
        fill_color=BAR_COLOUR,
    )
    fig.vbar(
        x="date",
        top="deaths_provisional",
        source=ds,
        width=bar_width,
        name="Deaths",
        line_width=0,
        fill_color=BAR_COLOUR,
        fill_alpha=0.4,
    )

    fig.line(
        x="date",
        y="deaths_rolling",
        source=ds,
        line_width=2,
        line_color=LINE_COLOUR[0],
        legend_label="Rolling average",
        name="Rolling average",
    )

    fig.line(
        x="date",
        y="deaths_report_date",
        source=ds,
        line_width=1.5,
        line_color="#666666",
        line_dash="dashed",
        legend_label="Deaths (date of report, rolling avg)",
    )

    fig.line(
        x="date",
        y="excess_deaths",
        source=ds,
        line_width=1.5,
        line_color=LINE_COLOUR[1],
        legend_label="Excess deaths (weekly, smoothed)",
        name="Excess deaths",
    )

    fig.line(
        x="date",
        y="recorded_deaths",
        source=ds,
        line_width=1.5,
        line_color="#DEB53A",
        legend_label="Recorded deaths (weekly, smoothed)",
        name="Recorded deaths",
    )

    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    return fig


def regional_cases(regions):
    fig = figure(title="New cases by region")

    fig.add_tools(region_hover_tool())

    colours = cycle(Dark2[7])

    for loc in sorted([str(loc.data) for loc in regions["location"]]):
        s = regions.sel(location=loc)
        color = next(colours)
        fig.line(
            x=s["date"].values,
            y=s["cases_rolling"].values / nhs_region_pops[loc] * 100000 * 7,
            legend_label=loc,
            name=loc,
            color=color,
            line_width=1,
        )

    fig.legend.location = "top_left"
    fig.yaxis.axis_label = "Weekly cases per 100,000"
    add_provisional(
        fig, start_date=max_date(regions) - timedelta(days=PROVISIONAL_DAYS)
    )
    return fig


def regional_deaths(nhs_deaths):
    fig = figure(title="Deaths in hospital")

    fig.add_tools(region_hover_tool())

    colours = cycle(Dark2[7])

    for loc in sorted([str(loc.data) for loc in nhs_deaths["location"]]):
        s = nhs_deaths.sel(location=loc)
        color = next(colours)
        fig.line(
            x=s["date"].values,
            y=s["deaths_rolling"].values / nhs_region_pops[loc] * 100000 * 7,
            legend_label=loc,
            name=loc,
            color=color,
            line_width=1,
        )

    fig.legend.location = "top_center"
    fig.xaxis.axis_label = "Date of death"
    fig.yaxis.axis_label = "Weekly deaths per 100,000"
    add_provisional(
        fig, start_date=max_date(nhs_deaths) - timedelta(days=PROVISIONAL_DAYS)
    )
    return fig


def triage_graph(triage_online, title=""):
    fig = figure(title=title)
    fig.add_tools(region_hover_tool())

    colours = cycle(Dark2[7])
    for loc in sorted([str(loc.item()) for loc in triage_online["region"]]):
        s = triage_online.sel(region=loc)
        color = next(colours)
        fig.line(
            x=s["date"].values,
            y=s["count_rolling_7"].values / nhs_region_pops[loc] * 100000 * 7,
            legend_label=loc,
            name=loc,
            color=color,
            line_width=1,
        )

    fig.legend.location = "top_right"
    fig.yaxis.axis_label = "Weekly instances per 100,000"
    return fig


def hospital_admissions_graph(hosp):
    fig = figure(title="Hospital admissions")
    fig.add_tools(region_hover_tool())

    colours = cycle(Dark2[7])

    for loc in hosp["location"].values:
        s = hosp.sel(location=loc)
        color = next(colours)
        fig.line(
            x=s["date"].values,
            y=s["admissions_rolling"].values / nhs_region_pops[loc] * 100000 * 7,
            legend_label=loc,
            name=loc,
            color=color,
            line_width=1,
        )

    fig.legend.location = "top_center"
    fig.yaxis.axis_label = "Weekly admissions per 100,000"
    return fig


def la_rate_plot(data, names, region, rolling_days=7):
    data = (
        data["cases_norm"]
        .resample(date="1D")
        .nearest(tolerance="1D")
        .ffill("date")
        .fillna(0)
        .diff("date")[:, :-4]
        .rolling(date=rolling_days, center=True)
        .sum()
        .dropna("date")
    )

    palette = [
        (0, "#f1f1f1"),
        (5, "#fef0d9"),
        (10, "#fdd49e"),
        (25, "#fdbb84"),
        (50, "#fc8d59"),
        (100, "#e34a33"),
        (100000, "#b30000"),
    ]

    def colour_val(cases):
        for threshold, colour in palette:
            if cases <= threshold:
                return colour
        return palette[-1][1]

    colours = []
    y_range = []
    yname = []
    xname = []
    for la in names.index:
        if la not in data["gss_code"]:
            continue
        name = names[la]
        y_range.append(name)
        xname += list(data["date"].values)
        for val in data.sel(gss_code=la).values * 100000 * (7 / rolling_days):
            yname.append(name)
            colours.append(colour_val(val))

    x_range = [data["date"].min().values, data["date"].max().values]
    height = len(y_range) * 12 + 100
    fig = bokeh_figure(
        y_range=y_range,
        x_range=x_range,
        width=1200,
        height=height,
        title=region,
        sizing_mode="scale_width",
        tools="",
        toolbar_location=None,
    )

    data_source = {"y": yname, "x": xname, "colours": colours}
    fig.rect(
        "x",
        "y",
        1.01 * (60 * 60 * 24 * 1000),
        0.85,
        source=data_source,
        color="colours",
        line_color=None,
        dilate=True,
    )
    fig.axis.axis_line_color = None
    fig.grid.grid_line_color = None
    fig.yaxis.major_tick_line_color = None
    fig.add_layout(DatetimeAxis(), "above")
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b", months="%d %b")
    return fig


def case_ratio_heatmap(by_age):
    # Note: by-age data is already subject to the dashboard's cutoff.
    by_age["cases_rolling"] = by_age["cases"].rolling(date=7, center=True).mean()
    by_age["cases_change"] = (
        by_age["cases_rolling"] / by_age.shift(date=7)["cases_rolling"]
    )
    by_age["cases_log_change"] = np.log(by_age["cases_change"].dropna("date"))

    df = by_age.drop_sel(age="unassigned").to_dataframe().dropna().reset_index()
    months = 4
    fig = bokeh_figure(
        width=1200,
        height=400,
        title=f"Change in cases in England by age (last {months} months)",
        tools="",
        toolbar_location=None,
        x_range=[
            by_age["date"].max().values - pd.to_timedelta(months * 30, unit="days"),
            by_age["date"].max().values,
        ],
        y_range=AGE_RANGES,
    )

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Date", "@date{%d %b}"),
                ("Age range", "@age"),
                ("Change in cases", "@cases_change{0%}"),
                ("Cases", "@cases_rolling{0,0}"),
            ],
            formatters={"@date": "datetime"},
            toggleable=False,
        )
    )

    fig.rect(
        "date",
        "age",
        dilate=True,
        width=60 * 60 * 24 * 1000 * 1.1,
        height=1.01,
        source=df,
        line_color=None,
        fill_color=linear_cmap(
            "cases_log_change", palette=RdYlBu[11], low=-0.8, high=0.8
        ),
    )
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b", months="%d %b")
    fig.grid.grid_line_color = None
    return fig


def uk_test_positivity(positivity):
    fig = figure(title="Test positivity")

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Positivity", "$y{0.0%}"),
                ("Date", "$x{%d %b}"),
            ],
            formatters={"$x": "datetime"},
            toggleable=False,
        )
    )

    fig.line(
        x=positivity["date"].values,
        y=positivity.values,
        line_width=2,
    )

    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.xaxis.axis_label = "Date of report"
    return fig


def uk_test_capacity(testing):
    fig = figure(title="Testing capacity")

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Pillar 1", "@p1{0.0%}"),
                ("Pillar 2", "@p2{0.0%}"),
                ("Date", "$x{%d %b}"),
            ],
            formatters={"$x": "datetime"},
            toggleable=False,
        )
    )

    colours = cycle(Dark2[4])

    ds = xr_to_cds(
        xr.merge(
            [
                {
                    "p1": testing["newPillarOneTestsByPublishDate"]
                    / testing["capacityPillarOne"]
                },
                {
                    "p2": testing["newPillarTwoTestsByPublishDate"]
                    / testing["capacityPillarTwo"]
                },
            ]
        )
    )

    fig.line(
        source=ds,
        x="date",
        y="p1",
        line_width=2,
        color=next(colours),
        legend_label="Pillar 1",
        name="Pillar 1",
    )

    fig.line(
        source=ds,
        x="date",
        y="p2",
        line_width=2,
        color=next(colours),
        legend_label="Pillar 2",
        name="Pillar 2",
    )

    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.legend.location = "top_left"
    fig.yaxis.axis_label = "Capacity used"
    fig.xaxis.axis_label = "Date of report"
    return fig


def rising_cases(eng_by_gss):
    cases_rolling_change = (
        (eng_by_gss["cases"].diff("date").rolling(date=7).mean())
        .dropna("date")
        .diff("date")
    )

    rising = (
        cases_rolling_change.where(cases_rolling_change > 0)
        .count("gss_code")
        .rolling(date=5)
        .mean()
        .to_dataframe("rising")
    ) / 380

    fig = figure(
        title="Fraction of local authorities with rising case rates",
        y_range=(0, 1),
        x_range=(rising.index.min(), rising.index.max()),
    )

    fig.add_layout(
        Span(
            location=0.5,
            dimension="width",
            line_color="#333333",
            line_dash="dashed",
            line_width=1,
        )
    )

    fig.line(x=rising.index, y=rising["rising"])

    fig.yaxis.formatter = NumeralTickFormatter(format="0%")

    return fig


def case_ratio(cases_data, location="England"):
    series = (
        cases_data.diff("date")
        .sel(location=location)
        .sel(date=slice(np.datetime64(date(2020, 3, 15)), None))
    )
    series = series.where(series["cases"] != 0).dropna("date")

    graph_data = (series / series.shift(date=7)).rename(cases="ratio")
    graph_data["ratio_rolling"] = (
        graph_data["ratio"].rolling(date=7, center=True).mean()
    )
    graph_data = graph_data.sel(
        date=slice(
            np.datetime64(date.today() - timedelta(days=120)),
            graph_data["date"].max().values,
        )
    )

    fig = figure(
        title=f"7-day case ratio by reporting date: {location}",
        x_range=None,
        y_range=None,
        y_axis_type="log",
    )
    fig.ygrid.visible = False

    ds = xr_to_cds(graph_data)

    fig.add_layout(
        Span(
            location=1,
            dimension="width",
            line_color="#dddddd",
            line_width=1,
            level="underlay",
        )
    )

    lines = [
        (2, "One week doubling"),
        (2 ** (1 / 2), "Two week doubling"),
        (2 ** (1 / 4), "Four week doubling"),
        (0.5, "One week halving"),
        (0.5 ** (1 / 2), "Two week halving"),
        (0.5 ** (1 / 4), "Four week halving"),
    ]

    for loc, text in lines:
        fig.add_layout(
            Span(
                location=loc,
                dimension="width",
                line_color="#dddddd",
                line_width=1,
                level="underlay",
                line_dash="dashed",
            )
        )

        fig.add_layout(
            Label(
                y=loc,
                x=3,
                x_units="screen",
                text=text,
                text_font="Noto Sans",
                text_font_size="10px",
                text_color="#aaaaaa",
                level="underlay",
            )
        )

    fig.circle(
        source=ds,
        x="date",
        y="ratio",
        alpha=0.4,
        line_color="#333333",
        line_width=1,
        line_alpha=0.4,
    )
    fig.line(source=ds, x="date", y="ratio_rolling", line_width=2)

    fig.yaxis.ticker = [0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0]
    fig.yaxis.axis_label = "Log(case ratio)"

    return fig
