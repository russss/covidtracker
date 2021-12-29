""" NHS App and test availability """

import numpy as np
import pandas as pd
from datetime import date, timedelta
from bokeh.models import FactorRange
from bokeh.transform import factor_cmap
from bokeh.palettes import YlOrRd, RdYlBu
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


def test_availability(home_test, walk_in):
    # Insert some blank rows at the current timestamp to extend time range to now.
    # Hacky. Also may misrepresent data if it stops being fetched.
    walk_in.loc[pd.Timestamp.now()] = ["Wales", None]
    home_test.loc[pd.Timestamp.now()] = [None, None, None]
    data = (
        walk_in.pivot(columns=["area"])
        .resample("30T")
        .last()
        .ffill()
        .melt(ignore_index=False, col_level=1)
        .reset_index()
    )
    data["area"] = data["area"].apply(
        lambda name: (
            "England" if name not in ("Wales", "Scotland", "Northern Ireland") else "",
            name,
        )
    )

    home_test.loc[pd.Timestamp.now()] = [None, None, None]
    home_data = (
        home_test.rename(
            columns={
                "pcr_keyworker": "PCR (key workers)",
                "pcr_public": "PCR (public)",
                "lfd_public": "LFD",
            }
        )
        .resample("30T")
        .last()
        .ffill()
        .melt(ignore_index=False)
        .reset_index()
        .rename(columns={"variable": "area"})
        .replace(True, "GOOD")
        .replace(False, "NONE")
    )
    home_data["area"] = home_data["area"].apply(lambda name: ("Home tests", name))
    data = pd.concat([home_data, data])
    data["value"] = data["value"].str.capitalize()

    regions = [
        ("Home tests", "PCR (key workers)"),
        ("Home tests", "PCR (public)"),
        ("Home tests", "LFD"),
        ("England", "North East England"),
        ("England", "North West England"),
        ("England", "Yorkshire and the Humber"),
        ("England", "East Midlands"),
        ("England", "West Midlands"),
        ("England", "East Of England"),
        ("England", "London"),
        ("England", "South East England"),
        ("England", "South West England"),
        ("", "Scotland"),
        ("", "Wales"),
        ("", "Northern Ireland"),
    ]

    fig = figure(
        y_range=FactorRange(*list(reversed(regions))),
        x_range=(data["date"].min(), pd.Timestamp.now()),
        title="COVID Test Availability",
        legend_position="right",
    )

    fig.rect(
        "date",
        "area",
        height=1,
        width=30 * 60 * 60 * 16,
        source=data,
        legend_field="value",
        color=factor_cmap("value", RdYlBu[3], ["Good", "Low", "None"]),
        alpha=1,
    )

    return fig
