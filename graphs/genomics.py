import pandas as pd
import numpy as np
from datetime import date, timedelta
from itertools import cycle
from bokeh.models import NumeralTickFormatter, HoverTool
from bokeh.palettes import Set2, Category10
from .common import figure

sources_map = {
    "PORT": "Portsmouth",
    "LOND": "London",  # UCL/Imperial
    "NORT": "Newcastle",  # University of Northumbria
    "EXET": "Exeter",  # University of Exeter
    "NORW": "Norwich",  # Quadram Institute Bioscience
    "MILK": "Milton Keynes",  # Lighthouse Lab Milton Keynes (Wellcome Sanger Institute)
    "ALDP": "Alderley Park",  # Lighthouse
    "QEUH": "Glasgow",  # Glasgow
    "BIRM": "Birmingham",  # University of Birmingham
    "BHRT": "London",  # Barking, Havering, Redbridge trust
    "PHEC": "London",  # PHE Colindale
    "CAMC": "Cambridge",  # Cambridge lighthouse lab,
    "WSFT": "Chichester",  # Western Sussex Foundation Trust
    "LIVE": "Liverpool",  # Liverpool Clinical Laboratories
    "NOTT": "Nottingham",  # DeepSeq Nottingham
    "LCST": "Nottingham",  # Seems to be nottingham but what does LCST stand for?
    "SHEF": "Sheffield",  # University of Sheffield
    "CAMB": "Cambridge",  # University of Cambridge
    "BRIS": "Bristol",
    "EKHU": "Ashford",
    "HECH": "Hereford",
    "KGHT": "Kettering",  # Kettering general hospital trust (presumed)
    "OXON": "Oxford",
    "LEED": "Leeds",
    "TBSD": "Torbay",  # The Department of Microbiology, Torbay and South Devon NHS Foundation Trust
    "GSTT": "London",  # Guys and St Thomas',
    "PHWC": "Cardiff",  # PHW Cardiff (presumably)
    "GCVR": "Glasgow",  # MRC-University of Glasgow Centre for Virus Research
    "EDB": "Edinburgh",
    "CVR": "Glasgow",
    "QEU": "Glasgow",
    "NIRE": "Northern Ireland",
    "TFCI": "London",  # The Francis Crick Institute
    "CWAR": "Warwick",  # Coventry and Warwick something something
    "MTUN": "Maidstone",  # Maidstone and Tunbridge Wells
    "PRIN": "Harlow",  # Princess Alexandra Hospital
}

sources_region_map = {
    "Alderley Park": "North West",
    "Ashford": "South East",
    "Birmingham": "Midlands",
    "Bristol": "South West",
    "Cambridge": "East of England",
    "Cardiff": "Wales",
    "Chichester": "South East",
    "Edinburgh": "Scotland",
    "Exeter": "South West",
    "Glasgow": "Scotland",
    "Harlow": "East of England",
    "Hereford": "Midlands",
    "Kettering": "Midlands",
    "Leeds": "North East and Yorkshire",
    "Liverpool": "North West",
    "London": "London",
    "Maidstone": "South East",
    "Milton Keynes": "East of England",
    "Newcastle": "North East and Yorkshire",
    "Northern Ireland": "Northern Ireland",
    "Norwich": "East of England",
    "Nottingham": "Midlands",
    "Oxford": "South East",
    "Portsmouth": "South East",
    "Sheffield": "North East and Yorkshire",
    "Torbay": "South West",
    "Warwick": "Midlands",
}


def extract_sequencing_source(seq_name):
    parts = seq_name.split("/")
    if "-" not in parts[1]:
        source = parts[1][:3]
    else:
        source = parts[1].split("-")[0]
    return sources_map.get(source, source)


def extract_sequencing_region(seq_name):
    parts = seq_name.split("/")
    if parts[0] != 'England':
        return parts[0].replace("_", " ")
    city = extract_sequencing_source(seq_name)
    region = sources_region_map.get(city, parts[0])
    if region in ["Scotland", "Wales", "Northern Ireland"]:
        # This is an English genome sequenced outside England
        return parts[0]
    return region


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
        "ORF1ab T1001I": "t1001i",
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


def variant_prevalence(data, lineage, title):
    fig = figure(title=title, interventions=True)
    count = data.groupby("sample_date")["sequence_name"].count()
    prevalence = pd.DataFrame(
        {
            "prevalence": data[data['lineage'] == lineage]
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


def variant_prevalence_by_region(data, lineage, title):
    data["location"] = data["sequence_name"].map(extract_sequencing_region)
    count = data.groupby(["sample_date", "location"])["sequence_name"].count()

    prevalence = pd.DataFrame(
        {
            "prevalence": data[data['lineage'] == lineage]
            .groupby(["sample_date", "location"])["sequence_name"]
            .count()
            / count
        }
    )

    prevalence = prevalence.fillna(0).unstack().rolling(7, center=True).mean()
    prevalence.columns = prevalence.columns.get_level_values(1)
    prevalence.drop(columns=['England'], inplace=True)

    colours = cycle(Category10[10])

    fig = figure(
        title=title,
        x_range=(
            np.datetime64(date(2020, 9, 15)),
            np.datetime64(date.today() + timedelta(days=1)),
        )
    )
    fig.add_tools(prevalence_hover_tool())
    for y in prevalence.columns:
        fig.line(
            source=prevalence, x="sample_date", y=y, color=next(colours), legend_label=y, name=y
        )
    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    return fig
