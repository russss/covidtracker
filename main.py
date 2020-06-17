from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import pandas as pd
from datetime import datetime, date
from bokeh.plotting import curdoc
from bokeh.themes import Theme
from bokeh.embed import json_item
import coviddata.uk
import coviddata.world

from graphs import (
    england_cases,
    england_deaths,
    regional_cases,
    regional_deaths,
    triage_graph,
    #    patients_in_hospital_graph,
)
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

    triage["count_rolling_14"] = (
        triage["count"].fillna(0).rolling(date=14, center=True).mean().dropna("date")
    )
    triage["count_rolling_7"] = (
        triage["count"].fillna(0).rolling(date=7, center=True).mean().dropna("date")
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

    triage["count_rolling_14"] = (
        triage["count"].fillna(0).rolling(date=14, center=True).mean().dropna("date")
    )
    triage["count_rolling_7"] = (
        triage["count"].fillna(0).rolling(date=7, center=True).mean().dropna("date")
    )
    return triage


ccg_lookup = (
    pd.read_csv("ccg_region.csv").drop_duplicates("CCG20CD").set_index("CCG20CD")
)

uk_cases = coviddata.uk.cases_phe("countries")
ecdc_cases = coviddata.world.cases_ecdc()

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

# patients_in_hospital = coviddata.uk.people_in_hospital()
# patients_in_hospital["patients_rolling_3"] = (
#    patients_in_hospital["patients"].rolling(date=3, center=True).mean().dropna("date")
# )


excess_deaths = pd.read_csv(
    "./excess_deaths.csv", index_col="date", parse_dates=["date"], dayfirst=True
)
triage_online = online_triage_by_nhs_region()
triage_pathways = pathways_triage_by_nhs_region()


render_template(
    "index.html",
    graphs={
        "confirmed_cases": england_cases(uk_cases, ecdc_cases),
        "deaths": england_deaths(uk_cases, excess_deaths),
        "regional_cases": regional_cases(nhs_region_cases),
        "regional_deaths": regional_deaths(nhs_deaths),
        "triage_online": triage_graph(triage_online, "Online triage"),
        "triage_pathways": triage_graph(triage_pathways, "Phone triage"),
        #        "patients": patients_in_hospital_graph(patients_in_hospital),
    },
    scores=calculate_score(
        nhs_deaths,
        nhs_region_cases,
        triage_online,
        triage_pathways,
        None
        #        patients_in_hospital,
    ),
    sources=[
        (
            "European Centres for Disease Control",
            "Data on the geographic distribution of COVID-19 cases worldwide",
            "https://www.ecdc.europa.eu/en/publications-data/download-todays-data-geographic-distribution-covid-19-cases-worldwide",
            ecdc_cases.attrs["date"],
        ),
        (
            "Public Health England",
            "Coronavirus (COVID-19) in the UK",
            "https://coronavirus.data.gov.uk",
            uk_cases.attrs["date"],
        ),
        (
            "ONS",
            "Deaths registered weekly in England and Wales, provisional",
            "https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages"
            "/deaths/datasets/weeklyprovisionalfiguresondeathsregisteredinenglandandwales",
            date(2020, 6, 16),
        ),
        (
            "NHS",
            "Potential COVID-19 symptoms reported through NHS Pathways and 111 online",
            "https://digital.nhs.uk/data-and-information/publications/statistical"
            "/mi-potential-covid-19-symptoms-reported-through-nhs-pathways-and-111-online",
            pd.Timestamp(triage_online["date"].max().item(0)).date(),
        ),
        #        (
        #            "UK Government",
        #            "Slides and datasets from daily press conference",
        #            patients_in_hospital.attrs["source_url"],
        #            patients_in_hospital.attrs["date"].date(),
        #        ),
    ],
)
