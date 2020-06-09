from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import pandas as pd
from datetime import datetime
from bokeh.plotting import curdoc
from bokeh.themes import Theme
from bokeh.embed import json_item
import coviddata.uk
import coviddata.world

from graphs import england_cases, england_deaths, regional_cases, regional_deaths
from score import calculate_score

curdoc().theme = Theme("./theme.yaml")

env = Environment(
    loader=FileSystemLoader("templates"), autoescape=select_autoescape(["html", "xml"])
)


def render_template(name, graphs={}, **kwargs):
    print(f"Rendering {name}...")

    graphs_data = json.dumps([json_item(graph, name) for name, graph in graphs.items()])

    generated = datetime.now()

    template = env.get_template(name)
    with open(f"output/{name}", "w") as f:
        f.write(template.render(graphs=graphs_data, generated=generated, **kwargs))


def cases_by_nhs_region():
    regions = coviddata.uk.cases_phe("ltlas").interpolate_na("date", "nearest")
    la_region_mapping = pd.read_csv(
        "https://raw.githubusercontent.com/russss/local_authority_nhs_region"
        "/master/local_authority_nhs_region.csv",
        index_col=["la_name"],
    )

    nhs_regions = []
    for a in regions["location"]:
        name = str(a.data)
        if name == "Cornwall and Isles of Scilly":
            name = "Cornwall"
        nhs_regions.append(la_region_mapping["nhs_name"][name])

    regions = regions.assign_coords({"location": nhs_regions})
    return regions.groupby("location").sum()


def online_triage_by_nhs_region():
    triage_online = coviddata.uk.triage_nhs_online()
    triage = (
        triage_online.sum(["age_band", "sex"])
        .assign_coords(
            {"ccg": [ccg_lookup["NHSER20NM"][i.item()] for i in triage_online["ccg"]]}
        )
        .rename(ccg="region")
        .groupby("region")
        .sum()
    )

    triage["count_rolling"] = (
        triage["count"].fillna(0).rolling(date=14, center=True).mean().dropna("date")
    )
    return triage


def pathways_triage_by_nhs_region():
    triage_pathways = coviddata.uk.triage_nhs_pathways()
    triage_pathways = triage_pathways.where(
        triage_pathways.ccg.str.startswith("E"), drop=True
    )
    triage = (
        triage_pathways.sum(["age_band", "sex", "site_type"])
        .assign_coords(
            {"ccg": [ccg_lookup["NHSER20NM"][i.item()] for i in triage_pathways["ccg"]]}
        )
        .groupby("ccg")
        .sum()
        .rename(ccg="region")
    )

    triage["count_rolling"] = (
        triage["count"].fillna(0).rolling(date=14, center=True).mean().dropna("date")
    )
    return triage


ccg_lookup = (
    pd.read_csv("ccg_region.csv").drop_duplicates("CCG20CD").set_index("CCG20CD")
)

uk_cases = coviddata.uk.cases_phe("countries")

provisional_days = 4

nhs_deaths = coviddata.uk.deaths_nhs()
nhs_deaths["deaths_rolling"] = (
    nhs_deaths["deaths"][:-provisional_days]
    .fillna(0)
    .rolling(date=7, center=True)
    .mean()
    .dropna("date")
    .fillna(0)
)
nhs_deaths["deaths_rolling_provisional"] = (
    nhs_deaths["deaths"].fillna(0).rolling(date=7, center=True).mean().dropna("date")
)

nhs_region_cases = cases_by_nhs_region()

nhs_region_cases["cases_rolling"] = (
    nhs_region_cases["cases"][:, :-provisional_days]
    .fillna(0)
    .diff("date")
    .rolling(date=7, center=True)
    .mean()
    .dropna("date")
)

nhs_region_cases["cases_rolling_provisional"] = (
    nhs_region_cases["cases"]
    .fillna(0)
    .diff("date")
    .rolling(date=7, center=True)
    .mean()
    .dropna("date")
)

excess_deaths = coviddata.world.excess_deaths_ft()
triage_online = online_triage_by_nhs_region()
triage_pathways = pathways_triage_by_nhs_region()


render_template(
    "index.html",
    graphs={
        "confirmed_cases": england_cases(uk_cases),
        "deaths": england_deaths(uk_cases, excess_deaths),
        "regional_cases": regional_cases(nhs_region_cases),
        "regional_deaths": regional_deaths(nhs_deaths)
    },
    scores=calculate_score(nhs_deaths, nhs_region_cases, triage_online, triage_pathways)
)
