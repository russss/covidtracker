import numpy as np
from itertools import cycle
from datetime import date, timedelta
from bokeh.plotting import figure as bokeh_figure
from bokeh.models import NumeralTickFormatter, DatetimeTickFormatter
from bokeh.palettes import Category10

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


def figure(**kwargs):
    fig = bokeh_figure(
        width=1200,
        height=500,
        toolbar_location=None,
        x_range=(
            np.datetime64(date(2020, 3, 1)),
            np.datetime64(date.today() + timedelta(days=1)),
        ),
        sizing_mode="scale_width",
        tools="",
        **kwargs
    )
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b")
    fig.xgrid.visible = False
    return fig


def england_cases(uk_cases):
    provisional_days = 4
    location = "England"

    fig = figure(title="New confirmed cases in English hospitals")
    cases = uk_cases.sel(location=location)["cases"].dropna("date").diff("date")
    rolling = cases[:-provisional_days].rolling({"date": 7}, center=True).mean()

    bar_width = 8640 * 10e3 * 0.7
    fig.vbar(
        x=cases["date"].values[:-provisional_days],
        top=cases.values[:-provisional_days],
        width=bar_width,
        line_width=0,
        fill_color=BAR_COLOUR,
    )
    fig.vbar(
        x=cases["date"].values[-provisional_days:],
        top=cases.values[-provisional_days:],
        width=bar_width,
        line_width=0,
        fill_color="#EDEDED",
    )
    fig.line(
        x=rolling["date"].values,
        y=rolling.values,
        line_width=2,
        line_color=LINE_COLOUR[0],
    )
    return fig


def england_deaths(uk_cases, excess_deaths):
    fig = figure(title="Deaths in England")

    deaths = uk_cases["deaths"].sel(location="England").diff("date").fillna(0)
    deaths_mean = deaths.rolling(date=7, center=True).mean().dropna("date")

    bar_width = 8640 * 10e3 * 0.7
    fig.vbar(
        x=deaths["date"].values,
        top=deaths.values,
        width=bar_width,
        line_width=0,
        fill_color=BAR_COLOUR,
    )
    fig.line(
        x=deaths_mean["date"].values,
        y=deaths_mean.values,
        line_width=2,
        legend_label="Reported COVID-19 deaths (7 day average)",
        line_color=LINE_COLOUR[0],
    )

    excess = (
        excess_deaths.xs(("UK", "England", "week"))["excess_deaths"].interpolate() / 7
    )
    fig.line(
        x=excess.index,
        y=excess.values,
        line_width=2,
        line_color=LINE_COLOUR[1],
        legend_label="Excess deaths (Weekly)",
    )

    fig.y_range.start = 0
    fig.xaxis.axis_label = "Date of report"
    return fig


def regional_cases(regions):
    fig = figure(title="New cases in hospital")

    colours = cycle(Category10[10])

    for loc in sorted([str(loc.data) for loc in regions["location"]]):
        s = regions.sel(location=loc)
        color = next(colours)
        fig.line(
            x=s["date"].values,
            y=s["cases_rolling"].values / nhs_region_pops[loc] * 100000,
            legend_label=loc,
            color=color,
            line_width=1,
        )
        fig.line(
            x=s["date"].values,
            y=s["cases_rolling_provisional"].values / nhs_region_pops[loc] * 100000,
            legend_label=loc,
            color=color,
            line_width=1,
            line_alpha=0.4,
        )

    fig.legend.location = "top_right"
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b")
    fig.yaxis.axis_label = "Cases per 100,000 population"
    return fig


def regional_deaths(nhs_deaths):
    fig = figure(title="Deaths in hospital")

    colours = cycle(Category10[7])

    for loc in sorted([str(loc.data) for loc in nhs_deaths["location"]]):
        s = nhs_deaths.sel(location=loc)
        color = next(colours)
        fig.line(
            x=s["date"].values,
            y=s["deaths_rolling"].values / nhs_region_pops[loc] * 100000,
            legend_label=loc,
            color=color,
            line_width=1,
        )
        fig.line(
            x=s["date"].values,
            y=s["deaths_rolling_provisional"].values / nhs_region_pops[loc] * 100000,
            legend_label=loc,
            color=color,
            line_width=1,
            line_alpha=0.4,
        )

    fig.legend.location = "top_right"
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b")
    fig.xaxis.axis_label = "Date of death"
    fig.yaxis.axis_label = "Deaths per 100,000 population"
    return fig
