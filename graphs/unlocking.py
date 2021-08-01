import pandas as pd
from graphs.common import figure
from bokeh.models import NumeralTickFormatter, Span, Label
import coviddata


def load_prediction(path):
    return pd.read_csv(
        "./unlocking_projections/" + path,
        names=["date", "hospitalisations"],
        parse_dates=["date"],
    ).set_index("date")


def unlocking_graph(log=True):
    hosp = coviddata.uk.hospitalisations_phe(key="gss", area_type="nation")
    imperial = load_prediction("2021-07-07/imperial.csv")
    warwick = load_prediction("2021-07-07/warwick.csv")
    lshtm = load_prediction("2021-07-07/lshtm-no-waning.csv")
    lshtm_waning = load_prediction("2021-07-07/lshtm-waning.csv")
    # spimo_7 = load_prediction("spi-m-o-2021-6-7.csv")
    # spimo_28 = load_prediction("spi-m-o-2021-6-28.csv")
    # spimo_7_7 = load_prediction("2021-07-07/spi-m-o.csv")

    hosp_change = hosp.diff("date")
    data = hosp_change.sel(
        gss_code="E92000001", date=slice("2021-06-01", hosp["date"].max() - 2)
    )

    title = "SAGE 93 unlocking projections: England hospital admissions"
    if log:
        title += " (log scale)"

    fig = figure(
        x_range=[data["date"].min().values, pd.to_datetime("2021-12-01")],
        y_axis_type="log" if log else "linear",
        title=title,
    )

    fig.line(x=data["date"].values, y=data["admissions"].values, color="#cccccc")

    fig.line(
        source=imperial,
        x="date",
        y="hospitalisations",
        color="red",
        legend_label="Imperial",
        line_alpha=0.6,
    )
    fig.line(
        source=warwick,
        x="date",
        y="hospitalisations",
        color="orange",
        legend_label="Warwick",
        line_alpha=0.6,
    )
    fig.line(
        source=lshtm,
        x="date",
        y="hospitalisations",
        color="blue",
        legend_label="LSHTM (no waning)",
        line_alpha=0.6,
    )
    fig.line(
        source=lshtm_waning,
        x="date",
        y="hospitalisations",
        color="teal",
        legend_label="LSHTM (waning)",
        line_alpha=0.6,
    )

    avg = data.rolling(date=7, center=True).mean().dropna("date")
    fig.line(
        x=avg["date"].values,
        y=avg["admissions"].values,
        color="#333333",
        legend_label="Actual",
    )

    fig.add_layout(
        Span(
            location=4232,
            level="underlay",
            dimension="width",
            line_color="#777777",
            line_dash="dashed",
            line_width=1,
        )
    )

    fig.add_layout(
        Span(
            location=3116,
            level="underlay",
            dimension="width",
            line_color="#777777",
            line_dash="dashed",
            line_width=1,
        )
    )

    fig.add_layout(
        Label(
            x=pd.to_datetime("2021-11-10"),
            y=3116,
            y_offset=2,
            text="First wave peak",
            text_font="Noto Sans",
            text_color="#999999",
            text_font_size="12px",
        )
    )

    fig.add_layout(
        Label(
            x=pd.to_datetime("2021-11-10"),
            y=4240,
            y_offset=2,
            text="Second wave peak",
            text_font="Noto Sans",
            text_color="#999999",
            text_font_size="12px",
        )
    )

    fig.yaxis.axis_label = "Daily Admissions"
    if log:
        fig.yaxis.axis_label += " (log scale)"
    fig.yaxis.formatter = NumeralTickFormatter(format="0")
    fig.legend.location = "top_left"
    fig.toolbar_location = None
    return fig
