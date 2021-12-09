import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
from itertools import cycle
from bokeh.models import NumeralTickFormatter, HoverTool
from bokeh.palettes import Set2, Category10, Greys
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
    data["e484k"] = data["e484k"].isin(["K", "Q"])
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
    fig = figure(title="UK mutation prevalence", interventions=True, y_axis_type="log")
    fig.y_range.start = 0.005
    fig.y_range.end = 1
    fig.add_tools(prevalence_hover_tool())

    mutations = {
        "S D614G": "d614g",
        "S A222V": "a222v",
        "S N501Y": "n501y",
        "S P681H": "p681h",
        "S E484[K|Q]": "e484k",
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


parent_lineages = requests.get(
    "https://raw.githubusercontent.com/cov-lineages/pango-designation/master/pango_designation/alias_key.json"
).json()

# Further info on the lineage naming rules here:
# https://virological.org/t/pango-lineage-nomenclature-provisional-rules-for-naming-recombinant-lineages/657


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
        for lineage in data["lineage"]:
            if lineage in interesting_lineages:
                filtered_lineage.append(lineage)
                continue

            summarised_lineage = summarise_lineage(lineage)

            if summarised_lineage != lineage:
                summarised_count += 1
            filtered_lineage.append(summarised_lineage)

        data["lineage"] = filtered_lineage

        if summarised_count == 0:
            break

    return data


def summarise_lineage(lin):
    lineage_parts = lin.split(".")

    if len(lineage_parts) < 3:
        # We're either one step up from the root of a lineage, or we are at the root of the lineage.
        root = lineage_parts[0]
        parent = parent_lineages.get(root)

        if not parent:
            # Parent lineage either doesn't exist in the data file, or is one of the root lineages (A or B)
            return lineage_parts[0]

        if isinstance(parent, list):
            # This happens if the lineage is a recombination of two parents
            # Pick the one with the longest lineage chain to be the parent,
            # ie. the most dots in the lineage name. Does not handle ties as is.
            return max(parent, key=lambda x: len(x.split(".")))

        return parent_lineages[root]

    return ".".join(lineage_parts[:-1])


named_lineages = {
    "B.1.1.7": "Alpha",
    "B.1.617.2": "Delta",
    "AY": "Delta",
    "B.1.1.529": "Omicron",
    "BA": "Omicron",
}

lineage_colours = {
    "Alpha": cycle(
        [
            "#3182bd",
            "#6baed6",
            "#9ecae1",
            "#c6dbef",
        ]
    ),
    "Delta": cycle(
        [
            "#e6550d",
            "#fd8d3c",
            "#fdae6b",
            "#fdd0a2",
        ]
    ),
    "Omicron": cycle(
        [
            "#31a354",
            "#74c476",
            "#a1d99b",
            "#c7e9c0",
        ]
    ),
    "": cycle(Greys[7]),
}


def lineage_prevalence(data):
    summarised = summarise_lineages(data, always_interesting=["B.1.1.529"])
    count = summarised.groupby(["sample_date"]).count()["sequence_name"]
    grouped = (
        summarised.groupby(["sample_date", "lineage"]).count()["sequence_name"] / count
    )

    grouped = grouped.unstack().fillna(0).rolling(7, center=True).mean().reset_index()
    grouped.drop(columns=["None"], inplace=True)

    lineage_data = []
    for lin in set(grouped.columns) - {"sample_date"}:
        d = {
            "lineage": lin,
            "variant": "",
            "first_date": grouped[grouped[lin] > 0.05]["sample_date"].min(),
        }
        for named_lin, name in named_lineages.items():
            if lin.startswith(named_lin):
                d["variant"] = name
                break
        lineage_data.append(d)

    lineage_data = list(
        sorted(lineage_data, key=lambda x: (x["variant"], x["first_date"]))
    )

    stackers = []
    labels = []
    colours = []

    for lin in lineage_data:
        stackers.append(lin["lineage"])
        if lin["variant"]:
            labels.append(f"{lin['lineage']} ({lin['variant']})")
        else:
            labels.append(lin["lineage"])

        colours.append(next(lineage_colours[lin["variant"]]))

    fig = figure(interventions=False, title="UK lineage prevalence")
    fig.varea_stack(
        source=grouped,
        x="sample_date",
        stackers=stackers,
        color=colours,
        legend_label=labels,
        fill_alpha=0.7,
    )
    fig.legend.location = "bottom_left"
    fig.yaxis.formatter = NumeralTickFormatter(format="0%")
    fig.y_range.end = 1
    add_provisional(fig, PROVISIONAL_DAYS)
    return fig
