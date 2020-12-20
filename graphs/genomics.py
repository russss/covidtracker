import pandas as pd
import numpy as np
from itertools import cycle
from bokeh.models import NumeralTickFormatter, HoverTool
from bokeh.palettes import Set2
from .common import figure


def prevalence_hover_tool():
    return HoverTool(
        tooltips=[
            ("Name", "$name"),
            ("Prevalence", "$y{0.0%}"),
            ("Date", "$x{%d %b}"),
        ],
        formatters={"$x": "datetime"},
        toggleable=False,
    )


def genomes_by_nation(data):
    fig = figure(title="Virus genomes sequenced by nation", interventions=False)
    by_country = data.set_index("adm1")
    by_country = (
        pd.DataFrame(
            {
                "England": by_country.loc["UK-ENG"]
                .groupby("sample_date")["sequence_name"]
                .count(),
                "Scotland": by_country.loc["UK-SCT"]
                .groupby("sample_date")["sequence_name"]
                .count(),
                "Northern Ireland": by_country.loc["UK-NIR"]
                .groupby("sample_date")["sequence_name"]
                .count(),
                "Wales": by_country.loc["UK-WLS"]
                .groupby("sample_date")["sequence_name"]
                .count(),
            }
        )
        .fillna(0)
        .rolling(7, center=True)
        .mean()
    )

    layers = ["England", "Scotland", "Wales", "Northern Ireland"]
    colours = ["#E6A6A1", "#A1A3E6", "#A6C78B", "#E0C795"]
    fig.varea_stack(
        source=by_country,
        x="sample_date",
        color=colours,
        stackers=layers,
        legend_label=layers,
    )
    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0,0")
    fig.xaxis.axis_label = "Sample date"
    return fig


def mutation_prevalence(data):
    fig = figure(title="Mutation prevalence", interventions=True)
    fig.add_tools(prevalence_hover_tool())

    mutations = {
        "S D614G": "d614g",
        "S A222V": "a222v",
        "S N501Y": "n501y",
        "S P681H": "p681h",
        "S Δ69-70": "del_21765_6",
        "ORF8 Q27stop": "q27stop",
        "ORF1ab T1001I": "t1001i"
    }
    count = data.groupby("sample_date")["sequence_name"].count()

    summary = (
        pd.DataFrame(
            {
                name: data.groupby("sample_date")[mutation].sum() / count
                for name, mutation in mutations.items()
            }
        )
        .rolling(7, center=True)
        .mean()
    )

    colours = cycle(Set2[len(mutations)])

    for name in mutations.keys():
        fig.line(
            source=summary,
            x="sample_date",
            y=name,
            name=name,
            legend_label=name,
            color=next(colours),
        )

    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.xaxis.axis_label = "Sample date"
    return fig


def variant_prevalence(data, mutations, title):
    fig = figure(title=title, interventions=True)
    count = data.groupby("sample_date")["sequence_name"].count()
    prevalence = pd.DataFrame(
        {
            "prevalence": data[np.logical_and.reduce([data[col] for col in mutations])]
            .groupby("sample_date")["sequence_name"]
            .count()
            / count
        }
    )
    prevalence = prevalence.fillna(0).rolling(7, center=True).mean()

    fig.line(source=prevalence, x="sample_date", y="prevalence")
    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.xaxis.axis_label = "Sample date"
    return fig
