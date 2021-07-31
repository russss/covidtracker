import numpy as np
import pandas as pd
from datetime import date, timedelta
from bokeh.palettes import YlOrRd
from .common import figure


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
    counts = (
        risky_venues.groupby(
            [risky_venues.export_date.dt.date, risky_venues.message_type]
        )
        .size()
        .unstack()
    ).fillna(0)
    colors = ["#718dbf", "#e84d60"]
    labels = ["Inform", "Book test"]
    fig = figure(
        title="Risky venue notifications",
        x_range=(
            np.datetime64(date(2020, 9, 10)),
            np.datetime64(date.today() + timedelta(days=1)),
        ),
    )
    fig.vbar_stack(
        ["M1", "M2"],
        source=counts,
        color=colors,
        x="export_date",
        width=60 * 60 * 24 * 1000 * 0.6,
        legend_label=labels,
    )
    fig.xaxis.axis_label = "Day of export"
    fig.legend.location = "top_left"
    fig.legend.title = "Notification type"
    return fig
