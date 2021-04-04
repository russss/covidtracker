import pandas as pd
import numpy as np
from datetime import date, timedelta
from itertools import cycle
from bokeh.models import NumeralTickFormatter, HoverTool
from bokeh.palettes import Set2, Category10, Category20
from .common import figure, add_provisional

PROVISIONAL_DAYS = 30

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


def fetch_cog_metadata():
    data = pd.read_csv(
        "https://cog-uk.s3.climb.ac.uk/phylogenetics/latest/cog_metadata.csv",
        parse_dates=["sample_date"],
    )
    data["d614g"] = data["d614g"] == "G"
    data["n439k"] = data["n439k"] == "K"
    data["p323l"] = data["p323l"] == "L"
    data["a222v"] = data["a222v"] == "V"
    data["y453f"] = data["y453f"] == "F"
    data["n501y"] = data["n501y"] == "Y"
    data["t1001i"] = data["t1001i"] == "I"
    data["p681h"] = data["p681h"] == "H"
    data["q27stop"] = data["q27stop"] == "*"
    data["e484k"] = data["e484k"] == "K"
    data["del_21765_6"] = data["del_21765_6"] == "del"
    return data


def extract_sequencing_source(seq_name):
    parts = seq_name.split("/")
    if "-" not in parts[1]:
        source = parts[1][:3]
    else:
        source = parts[1].split("-")[0]
    return sources_map.get(source, source)


def extract_sequencing_region(seq_name):
    parts = seq_name.split("/")
    if parts[0] != "England":
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
    add_provisional(fig, PROVISIONAL_DAYS)
    return fig


def mutation_prevalence(data):
    fig = figure(title="UK mutation prevalence", interventions=True)
    fig.add_tools(prevalence_hover_tool())

    mutations = {
        "S D614G": "d614g",
        "S A222V": "a222v",
        "S N501Y": "n501y",
        "S P681H": "p681h",
        "S E484K": "e484k",
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
    add_provisional(fig, PROVISIONAL_DAYS)
    return fig


def variant_prevalence_by_region(data, lineage, title):
    data["location"] = data["sequence_name"].map(extract_sequencing_region)
    count = data.groupby(["sample_date", "location"])["sequence_name"].count()

    prevalence = pd.DataFrame(
        {
            "prevalence": data[data["lineage"] == lineage]
            .groupby(["sample_date", "location"])["sequence_name"]
            .count()
            / count
        }
    )

    prevalence = prevalence.fillna(0).unstack().rolling(7, center=True).mean()
    prevalence.columns = prevalence.columns.get_level_values(1)
    prevalence.drop(columns=["England"], inplace=True)

    colours = cycle(Category10[10])

    fig = figure(
        title=title,
        x_range=(
            np.datetime64(date(2020, 9, 15)),
            np.datetime64(date.today() + timedelta(days=1)),
        ),
    )

    fig.add_tools(prevalence_hover_tool())
    for y in prevalence.columns:
        fig.line(
            source=prevalence,
            x="sample_date",
            y=y,
            color=next(colours),
            legend_label=y,
            name=y,
        )
    fig.legend.location = "top_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    add_provisional(fig, PROVISIONAL_DAYS)
    return fig


# Fetch the parent lineages map. We only care about cases where a new letter gets assigned.
parent_lineages = {
    row["alias"]: ".".join(row["lineage"].split(".")[:-1])
    for _, row in pd.read_csv(
        "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/full_alias_key.txt"
    ).iterrows() if row['alias'].count('.') == 1
}


def summarise_lineages(data, threshold=0.15, always_interesting=[]):
    """Summarise a COG-UK metadata dataframe, merging each lineage with its
    parent lineage unless it has an average prevalence of more than `threshold` during
    any 7-day window.
    """
    data = data[
        ~data["lineage"].isnull()
    ].copy()  # Filter out missing lineages to start
    count = data.groupby("sample_date").count()["sequence_name"].rolling(7).mean()

    # Don't use days with fewer than 300 samples to calculate prevalence
    count = count[count > 300]

    while True:
        lineage_prevalence = (
            pd.DataFrame(
                {
                    "sample_date": data["sample_date"],
                    "lineage": data["lineage"],
                    "count": 1,
                }
            )
            .set_index(["lineage", "sample_date"])
            .sort_index()
            .groupby(level=[0, 1])
            .agg("sum")
            .rolling(7)
            .mean()
        )

        lineage_prevalence["prevalence"] = lineage_prevalence["count"] / count
        max_lineages = lineage_prevalence.groupby("lineage").max()

        interesting_lineages = set(
            max_lineages[max_lineages["prevalence"] > threshold].index
        ) | set(always_interesting)
        try:
            interesting_lineages.remove("")
        except KeyError:
            pass

        filtered_lineage = []
        summarised_count = 0
        for lin in data["lineage"]:
            if lin in interesting_lineages:
                filtered_lineage.append(lin)
            elif lin in parent_lineages:
                summarised_count += 1
                filtered_lineage.append(parent_lineages[lin])
            else:
                lineage_parts = lin.split(".")
                if len(lineage_parts) == 1:
                    summarised_lineage = lineage_parts[0]
                else:
                    summarised_count += 1
                    summarised_lineage = ".".join(lineage_parts[:-1])
                filtered_lineage.append(summarised_lineage)

        data["lineage"] = filtered_lineage

        if summarised_count == 0:
            break

    return data


def lineage_prevalence(data):
    summarised = summarise_lineages(data, always_interesting=["B.1.351"])
    count = summarised.groupby(["sample_date"]).count()["sequence_name"]
    grouped = (
        summarised.groupby(["sample_date", "lineage"]).count()["sequence_name"] / count
    )
    stackers = list(sorted(grouped.index.get_level_values(1).unique()))
    grouped = grouped.unstack().fillna(0).rolling(7, center=True).mean().reset_index()

    colour_iter = cycle(Category20[20])
    colours = [next(colour_iter) for i in stackers]

    fig = figure(interventions=False, title="UK lineage prevalence")
    fig.varea_stack(
        source=grouped,
        x="sample_date",
        stackers=stackers,
        color=colours,
        legend_label=stackers,
        fill_alpha=0.7,
    )
    fig.legend.location = "bottom_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.y_range.end = 1
    add_provisional(fig, PROVISIONAL_DAYS)
    return fig
