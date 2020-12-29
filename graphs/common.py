import numpy as np
import pandas as pd
from math import pi
from bokeh.models import Legend, DatetimeTickFormatter, Span, ColumnDataSource, Label
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure as bokeh_figure
from datetime import date, timedelta

LOCKDOWN_COLOUR = "#CC5050"
RELEASE_COLOUR = "#50CCA5"

england_interventions = [
    (date(2020, 3, 23), "Lockdown", LOCKDOWN_COLOUR),
    (date(2020, 5, 10), "Stay Alert", RELEASE_COLOUR),
    (date(2020, 6, 1), "Schools Open", RELEASE_COLOUR),
    (date(2020, 6, 15), "Non-essential shops open", RELEASE_COLOUR),
    (date(2020, 7, 4), "1m plus distancing, pubs open", RELEASE_COLOUR),
    (date(2020, 9, 14), "Rule of six", LOCKDOWN_COLOUR),
    (date(2020, 9, 24), "10pm pub closing", LOCKDOWN_COLOUR),
    (date(2020, 11, 5), "Lockdown #2", LOCKDOWN_COLOUR),
    (date(2020, 12, 2), "Tier system", RELEASE_COLOUR),
    (date(2020, 12, 20), "Tier 4", LOCKDOWN_COLOUR),
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


def figure(interventions=True, **kwargs):
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
    if interventions:
        add_interventions(fig)

    legend = Legend()
    legend.click_policy = "hide"
    fig.add_layout(legend)
    fig.xaxis.formatter = DatetimeTickFormatter(days="%d %b", months="%d %b")
    fig.xgrid.visible = False
    fig.y_range.start = 0
    return fig


def add_provisional(fig, provisional_days=7, start_date=None):
    if not start_date:
        start_date = date.today() - timedelta(days=provisional_days)

    end_date = date.today() + timedelta(days=1)

    fill_color = "#030002"
    provisional_renderer = fig.varea(
        x=[
            np.datetime64(start_date),
            np.datetime64(end_date),
        ],
        y1=-10e6,
        y2=10e6,
        fill_color=fill_color,
        fill_alpha=0.05,
        level="underlay",
    )
    fig.y_range.renderers = [
        r for r in fig.renderers if r.id != provisional_renderer.id
    ]

    label = Label(
        x=date.today(),
        x_offset=-49,
        y=40,
        y_units="screen",
        text="INCOMPLETE",
        background_fill_color="#F2F2F2",
        render_mode="css",
        text_font="Noto Sans",
        text_font_size="14px",
        text_color="#cccccc",
        angle=pi / 2,
        level="underlay"
    )
    fig.add_layout(label)


def max_date(data):
    return pd.Timestamp(data.dropna("date").date.max().values).to_pydatetime()
