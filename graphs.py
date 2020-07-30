import numpy as np
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
from bokeh.models.tools import HoverTool
from bokeh.palettes import Dark2

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

england_interventions = [
    (date(2020, 3, 23), "Lockdown", "#CC5450"),
    (date(2020, 5, 10), "Stay Alert", "#50CCA5"),
    (date(2020, 6, 1), "Schools Open", "#50CCA5"),
    (date(2020, 6, 15), "Non-essential shops open", "#50CCA5"),
    (date(2020, 7, 4), "1m plus distancing, pubs open", "#50CCA5"),
]


def region_hover_tool():
    return HoverTool(
        tooltips=[
            ("Region", "$name"),
            ("Value per 100,000", "$y{0.00}"),
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
    fig = bokeh_figure(
        width=1200,
        height=500,
        toolbar_location="right",
        x_range=(
            np.datetime64(date(2020, 3, 1)),
            np.datetime64(date.today() + timedelta(days=1)),
        ),
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


def uk_cases_graph(uk_cases_national, uk_cases):
    # provisional_days = 4
    bar_width = 8640 * 10e3 * 0.8

    fig = figure(title="New cases")

    uk_cases_national = uk_cases_national.ffill("date").diff("date")

    uk_cases = (
        uk_cases.ffill("date")
        .sum("location")
        .diff("date")
        .rolling(date=7, center=True)
        .mean()
    )["cases"]

    layers = ["England", "Scotland", "Wales"]
    colours = {"England": "#E6A6A1", "Scotland": "#A1A3E6", "Wales": "#A6C78B"}

    cases_ds = stack_datasource(uk_cases_national, layers)

    lower = 0
    for layer in layers:
        label = layer
        fig.vbar(
            source=cases_ds,
            x="date",
            bottom=lower,
            top=layer,
            width=bar_width,
            line_width=0,
            fill_color=colours[layer],
            fill_alpha=0.4,
            legend_label=label,
        )
        lower = layer

    # fig.line(
    #    x=uk_cases["date"].values,
    #    y=uk_cases.values,
    #    line_color=LINE_COLOUR[0],
    #    line_width=2,
    #    legend_label="UK (rolling avg)",
    # )

    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
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

    fig.legend.location = "top_right"
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
