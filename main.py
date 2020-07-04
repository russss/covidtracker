import json
import pandas as pd
import xarray as xr
from datetime import date
from bokeh.plotting import curdoc
from bokeh.themes import Theme
from urllib.error import URLError
import coviddata.uk
import coviddata.uk.scotland
import coviddata.uk.wales
import coviddata.world

from graphs import (
    uk_cases_graph,
    england_deaths,
    regional_cases,
    regional_deaths,
    triage_graph,
)
from template import render_template
from map import map_data
from score import calculate_score
from corrections import correct_scottish_data

curdoc().theme = Theme("./theme.yaml")


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
        if name == "Hackney and City of London":
            name = "Hackney"
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
    pd.read_csv("./data/ccg_region.csv").drop_duplicates("CCG20CD").set_index("CCG20CD")
)

uk_cases = coviddata.uk.cases_phe("countries")

by_ltla_gss = coviddata.uk.cases_phe("ltlas", key="gss_code")
scot_data = correct_scottish_data(coviddata.uk.scotland.cases("gss_code"))
wales_cases = coviddata.uk.wales.cases()
wales_by_gss = coviddata.uk.wales.cases("gss_code")

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

uk_cases_combined = xr.concat(
    [
        uk_cases.sel(location="England")["cases"],
        scot_data.sel(gss_code="S92000003").assign_coords(location="Scotland")[
            "corrected_cases"
        ],
        wales_cases.sum("location").assign_coords(location="Wales")["cases"],
    ],
    "location",
)

excess_deaths = pd.read_csv(
    "./data/excess_deaths.csv", index_col="date", parse_dates=["date"], dayfirst=True
)
triage_online = online_triage_by_nhs_region()
triage_pathways = pathways_triage_by_nhs_region()


render_template(
    "index.html",
    graphs={
        "confirmed_cases": uk_cases_graph(uk_cases_combined),
        "deaths": england_deaths(uk_cases, excess_deaths),
        "regional_cases": regional_cases(nhs_region_cases),
        "regional_deaths": regional_deaths(nhs_deaths),
        "triage_online": triage_graph(triage_online, "Online triage"),
        "triage_pathways": triage_graph(triage_pathways, "Phone triage"),
    },
    scores=calculate_score(
        nhs_deaths, nhs_region_cases, triage_online, triage_pathways, None
    ),
    sources=[
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
            date(2020, 6, 23),
        ),
        (
            "NHS",
            "Potential COVID-19 symptoms reported through NHS Pathways and 111 online",
            "https://digital.nhs.uk/data-and-information/publications/statistical"
            "/mi-potential-covid-19-symptoms-reported-through-nhs-pathways-and-111-online",
            pd.Timestamp(triage_online["date"].max().item(0)).date(),
        ),
        (
            scot_data.attrs["source"],
            "Coronavirus - COVID-19 - Management Information",
            scot_data.attrs["source_url"],
            scot_data.attrs["date"],
        ),
        (
            wales_by_gss.attrs["source"],
            "Rapid COVID-19 Surveillance",
            wales_by_gss.attrs["source_url"],
            wales_by_gss.attrs["date"],
        ),
    ],
)


populations = pd.read_csv("./data/region_populations.csv", thousands=",").set_index(
    "Code"
)["All ages"]
scot_populations = pd.read_csv("./data/scot_populations.csv", thousands=",").set_index(
    "gss code"
)["population"]

provisional_days = 4
render_template(
    "map.html",
    data=json.dumps(
        map_data(
            by_ltla_gss,
            wales_by_gss,
            scot_data,
            populations,
            scot_populations,
            provisional_days,
        )
    ),
    sources=[
        (
            "Public Health England",
            "Coronavirus (COVID-19) in the UK",
            "https://coronavirus.data.gov.uk",
            uk_cases.attrs["date"],
        ),
        (
            scot_data.attrs["source"],
            "Coronavirus - COVID-19 - Management Information",
            scot_data.attrs["source_url"],
            scot_data.attrs["date"],
        ),
        (
            wales_by_gss.attrs["source"],
            "Rapid COVID-19 Surveillance",
            wales_by_gss.attrs["source_url"],
            wales_by_gss.attrs["date"],
        ),
    ],
)
