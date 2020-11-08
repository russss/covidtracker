import numpy as np
import pandas as pd
import xarray as xr
import colorcet
from itertools import cycle
from datetime import date, timedelta
from bokeh.plotting import figure as bokeh_figure
from bokeh.models import (
    NumeralTickFormatter,
    DatetimeTickFormatter,
    Span,
    ColumnDataSource,
    Legend,
    DatetimeAxis,
)
from bokeh.transform import linear_cmap
from bokeh.models.tools import HoverTool
from bokeh.palettes import Dark2, YlOrRd

from util import dict_to_xr

BAR_COLOUR = "#D5DFED"
LINE_COLOUR = ["#3D6CB3", "#B33D43"]


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

LOCKDOWN_COLOUR = "#CC5050"
RELEASE_COLOUR = "#50CCA5"

england_interventions = [
    (date(2020, 3, 23), "Lockdown", LOCKDOWN_COLOUR),
    (date(2020, 5, 10), "Stay Alert", RELEASE_COLOUR),
    (date(2020, 6, 1), "Schools Open", RELEASE_COLOUR),
    (date(2020, 6, 15), "Non-essential shops open", RELEASE_COLOUR),
    (date(2020, 7, 4), "1m plus distancing, pubs open", RELEASE_COLOUR),
    (date(2020, 9, 9), "Rule of six", LOCKDOWN_COLOUR),
    (date(2020, 9, 24), "10pm pub closing", LOCKDOWN_COLOUR),
    (date(2020, 11, 5), "Lockdown #2", LOCKDOWN_COLOUR),
]


def region_hover_tool():
    return HoverTool(
        tooltips=[
            ("Region", "$name"),
            ("Cases per 100,000", "$y{0.00}"),
            ("Date", "$x{%d %b}"),
        ],
        formatters={"$x": "datetime"},
        toggleable=False,
    )


def country_hover_tool():
    return HoverTool(
        tooltips=[
            ("Country", "$name"),
            ("Cases per 100,000", "$y{0.00}"),
            ("Date", "$x{%d %b}"),
        ],
        formatters={"$x": "datetime"},
        toggleable=False,
    )


def intervention(fig, date, label, colour="red"):
    span = Span(
        location=date,
        dimension="height",
        line_color=colour,
        line_width=1,
        line_alpha=0.5,
        line_dash="dashed",
    )
    fig.add_layout(span)

    # span_label = Label(
    #    text=label,
    #    text_font="Noto Sans",
    #    text_font_size="10px",
    #    x=date,
    #    y=0,
    #    x_offset=-20,
    #    y_offset=-10,
    #    background_fill_color="white",
    # )
    # fig.add_layout(span_label)


def xr_to_cds(xr, x_series="date"):
    data = {}
    for series in xr:
        data[series] = xr[series].values

    data[x_series] = xr[x_series].values
    return ColumnDataSource(data=data)


def add_interventions(fig):
    for when, label, colour in england_interventions:
        intervention(fig, when, label, colour)


def figure(**kwargs):
    if "x_range" not in kwargs:
        kwargs["x_range"] = (
            np.datetime64(date(2020, 3, 1)),
            np.datetime64(date.today() + timedelta(days=1)),
        )
    fig = bokeh_figure(
        width=1200,
        height=500,
        toolbar_location="right",
        sizing_mode="scale_width",
        tools="reset,box_zoom",
        **kwargs
    )
    fig.toolbar.logo = None
    add_interventions(fig)
    legend = Legend()
    legend.click_policy = "hide"
    fig.add_layout(legend)
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b", months="%d %b")
    fig.xgrid.visible = False
    fig.y_range.start = 0
    return fig


def stack_datasource(source, series):
    data = {}
    for i in range(0, len(series)):
        y = sum(source.sel(location=loc) for loc in series[0 : i + 1]).values
        data[series[i]] = y

    data["date"] = source["date"].values
    return ColumnDataSource(data)


def uk_cases_graph(uk_cases):
    fig = figure(title="New cases by nation")
    fig.add_tools(country_hover_tool())

    uk_cases_national = uk_cases / nation_populations * 100000 * 7

    layers = ["England", "Scotland", "Wales", "Northern Ireland"]
    colours = {
        "England": "#E6A6A1",
        "Scotland": "#A1A3E6",
        "Wales": "#A6C78B",
        "Northern Ireland": "#E0C795",
    }

    for layer in layers:
        label = layer
        fig.line(
            x=uk_cases_national["date"].values,
            y=uk_cases_national.sel(location=layer)["cases_rolling"].values,
            line_width=2,
            line_color=colours[layer],
            legend_label=label,
            name=layer,
        )
        fig.line(
            x=uk_cases_national["date"].values,
            y=uk_cases_national.sel(location=layer)["cases_rolling_provisional"].values,
            line_width=2,
            line_alpha=0.4,
            line_color=colours[layer],
            legend_label=label,
            name=layer,
        )

    fig.yaxis.formatter = NumeralTickFormatter(format="0.0")
    fig.yaxis.axis_label = "Weekly cases per 100,000"
    fig.legend.location = "top_left"
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
        fig.line(
            x=s["date"].values,
            y=s["cases_rolling_provisional"].values / nhs_region_pops[loc] * 100000 * 7,
            legend_label=loc,
            name=loc,
            color=color,
            line_width=1,
            line_alpha=0.4,
        )

    fig.legend.location = "top_center"
    fig.yaxis.axis_label = "Weekly cases per 100,000"
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
        fig.line(
            x=s["date"].values,
            y=s["deaths_rolling_provisional"].values
            / nhs_region_pops[loc]
            * 100000
            * 7,
            legend_label=loc,
            name=loc,
            color=color,
            line_width=1,
            line_alpha=0.4,
        )

    fig.legend.location = "top_right"
    fig.xaxis.axis_label = "Date of death"
    fig.yaxis.axis_label = "Weekly deaths per 100,000"
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

    fig.legend.location = "top_right"
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


def age_heatmap(age_rate):
    age_rate = age_rate.copy()
    #    age_rate.index = [datetime.combine(date.fromisocalendar(2020, week, 7), datetime.min.time()) for week in age_rate.index]
    age_rate.index.name = "Week Ending"
    age_rate.columns.name = "Age"
    fig = bokeh_figure(
        width=1200,
        height=300,
        title="Infection rate in England by age",
        tools="",
        toolbar_location=None,
        x_range=[age_rate.index[0], age_rate.index[-1]],
        y_range=list(age_rate.columns),
    )

    fig.add_tools(
        HoverTool(
            tooltips=[
                ("Week", "@{Week Ending}"),
                ("Age range", "@Age"),
                ("Cases", "@rate{0.00} per 100,000"),
            ],
            toggleable=False,
        )
    )

    df = pd.DataFrame(age_rate.stack(), columns=["rate"]).reset_index()
    ds = ColumnDataSource(df)

    fig.rect(
        "Week Ending",
        "Age",
        dilate=True,
        width=1.001,
        height=1.001,
        source=ds,
        line_color=None,
        fill_color=linear_cmap("rate", palette=colorcet.kbc, low=1, high=180),
    )

    fig.xaxis.axis_label = "Week number"

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


def app_keys(data, by="export"):
    if by == "export":
        title = "Exposure keys by date of publication"
        counts = data.groupby(data.export_date.dt.date).size()
    elif by == "interval":
        title = "Exposure keys by date of broadcast and risk level"
        counts = (
            pd.DataFrame(
                data.groupby(
                    [data.interval_start.dt.date, data.transmission_risk_level]
                ).size()
            )
            .reset_index()
            .set_index("interval_start")
            .pivot(columns="transmission_risk_level")
        )
        counts.columns = [str(i[1]) for i in counts.columns.to_flat_index()]
    fig = figure(
        title=title,
        x_range=(
            np.datetime64(date(2020, 9, 10)),
            np.datetime64(date.today() + timedelta(days=1)),
        ),
    )
    width = 60 * 60 * 24 * 1000 * 0.9
    if by == "export":
        fig.vbar(x=counts.index, top=counts, width=width)
        fig.xaxis.axis_label = "Day of export"
    elif by == "interval":
        columns = list(counts.columns)
        fig.vbar_stack(
            columns,
            x="interval_start",
            width=width,
            source=counts,
            fill_color=list(reversed(YlOrRd[7])),
            line_width=0,
            legend_label=columns,
        )
        fig.xaxis.axis_label = "Day of broadcast"
        fig.legend.title = "Risk level"
        fig.legend.location = "top_left"
    return fig


def risky_venues(risky_venues):
    counts = risky_venues.groupby(risky_venues.export_date.dt.date).size()
    fig = figure(
        title="Risky venues",
        x_range=(
            np.datetime64(date(2020, 9, 10)),
            np.datetime64(date.today() + timedelta(days=1)),
        ),
    )
    fig.vbar(x=counts.index, top=counts, width=60 * 60 * 24 * 1000 * 0.9)
    fig.xaxis.axis_label = "Day of export"
    return fig
