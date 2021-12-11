import json
import logging
import pandas as pd
from datetime import date
import coviddata.uk
import coviddata.uk.scotland
import coviddata.uk.wales
import coviddata.world
import sys
import os


from graphs import (
    uk_cases_graph,
    regional_cases,
    case_ratio_heatmap,
    case_ratio,
    hospital_admissions_graph,
    uk_test_positivity,
    uk_test_capacity,
)
from graphs.genomics import (
    fetch_cog_metadata,
    genomes_by_nation,
    mutation_prevalence,
    lineage_prevalence,
)
from graphs.vaccine import vax_rate_graph, vax_cumulative_graph
from graphs.app import risky_venues, app_keys
from graphs.tadpole import la_tadpole
from graphs.unlocking import unlocking_graph
from template import render_template
from map import map_data
from score import calculate_score
from corrections import correct_scottish_data, cases_by_nhs_region
from nhs_app import NHSAppData

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.INFO)
log = logging.getLogger(__name__)

log.info("Generating pages...")

la_region = pd.read_csv(
    "https://raw.githubusercontent.com/russss/local_authority_nhs_region"
    "/master/local_authority_nhs_region.csv",
    index_col=["la_gss"],
)


def online_triage_by_nhs_region():
    triage_online = coviddata.uk.triage_nhs_online()
    triage = (
        triage_online.sum(["age_band", "sex"])
        .assign_coords(
            {
                "ccg": [
                    ccg_lookup["NHSER20NM"].get(i.item()) for i in triage_online["ccg"]
                ]
            }
        )
        .rename(ccg="region")
        .groupby("region")
        .sum()
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
            {
                "ccg": [
                    ccg_lookup["NHSER20NM"].get(i.item())
                    for i in triage_pathways["ccg"]
                ]
            }
        )
        .groupby("ccg")
        .sum()
        .rename(ccg="region")
    )

    triage["count_rolling_7"] = (
        triage["count"].fillna(0).rolling(date=7, center=True).mean().dropna("date")
    )
    return triage


ccg_lookup = (
    pd.read_csv("./data/ccg_region.csv").drop_duplicates("CCG20CD").set_index("CCG20CD")
)

populations = pd.read_csv("./data/region_populations.csv", thousands=",")
populations = populations[populations["Code"].str.len() == 9]
populations = (
    populations.rename(columns={"Code": "gss_code"})
    .set_index("gss_code")["All ages"]
    .to_xarray()
)

scot_populations = pd.read_csv("./data/scot_populations.csv", thousands=",").set_index(
    "gss code"
)

provisional_days = 5

uk_cases = coviddata.uk.cases_phe("countries")

uk_cases["cases_rolling"] = (
    uk_cases["cases"].diff("date").rolling(date=7, center=True).mean().dropna("date")
)

eng_by_gss = coviddata.uk.cases_phe("ltlas", key="gss_code")

eng_by_gss["cases_rolling_14"] = (
    eng_by_gss["cases"].diff("date").rolling(date=14, center=True).mean()
)
eng_by_gss["cases_norm"] = eng_by_gss["cases"] / populations

nhs_region_cases = cases_by_nhs_region(eng_by_gss, la_region)

nhs_region_cases["cases_rolling"] = (
    nhs_region_cases["cases"]
    .diff("date")
    .rolling(date=7, center=True)
    .mean()
    .dropna("date")
)

hospital_admissions = coviddata.uk.hospitalisations_phe()
hospital_admissions["admissions_rolling"] = (
    hospital_admissions["admissions"]
    .diff("date")
    .rolling(date=7, center=True)
    .mean()
    .dropna("date")
)

excess_deaths = pd.read_csv(
    "./data/excess_deaths.csv", index_col="date", parse_dates=["date"], dayfirst=True
)

triage_online = None
triage_pathways = None

by_age = coviddata.uk.cases_by_age()
by_report_date = coviddata.uk.cases_phe(basis="report")

render_template(
    "index.html",
    graphs={
        "confirmed_cases": uk_cases_graph(uk_cases),
        "regional_cases": regional_cases(nhs_region_cases),
        "case_ratio_heatmap": case_ratio_heatmap(by_age),
        "hospital_admissions": hospital_admissions_graph(hospital_admissions),
        "case_ratio_england": case_ratio(by_report_date),
        "case_ratio_scotland": case_ratio(by_report_date, "Scotland"),
    },
    scores=calculate_score(
        nhs_region_cases,
        triage_online,
        triage_pathways,
        hospital_admissions,
    ),
    sources=[
        (
            "UKHSA",
            "Coronavirus (COVID-19) in the UK",
            "https://coronavirus.data.gov.uk",
            uk_cases.attrs["date"],
        ),
    ],
)

testing = coviddata.uk.tests_phe()

cases_by_publish_date = coviddata.uk.cases_phe(by="overview", basis="report")
uk_cases_pub_date = cases_by_publish_date.sel(location="United Kingdom").diff("date")[
    "cases"
]
uk_cases_pub_date = uk_cases_pub_date.where(uk_cases_pub_date > 0)
positivity = uk_cases_pub_date / (
    testing["newPillarOneTestsByPublishDate"]
    + testing["newPillarTwoTestsByPublishDate"]
)


render_template(
    "testing.html",
    graphs={
        "positivity": uk_test_positivity(positivity),
        "test_capacity": uk_test_capacity(testing),
    },
    sources=[
        (
            testing.attrs["source"],
            "Coronavirus (COVID-19) in the UK",
            testing.attrs["source_url"],
            testing.attrs["date"],
        )
    ],
)

positivity = coviddata.uk.test_positivity()
vaccine_uptake = coviddata.uk.vaccination_uptake_by_area()

render_template(
    "map.html",
    data=json.dumps(map_data(eng_by_gss, positivity, provisional_days, vaccine_uptake)),
    provisional_days=provisional_days,
    sources=[
        (
            "UKHSA",
            "Coronavirus (COVID-19) in the UK",
            "https://coronavirus.data.gov.uk",
            uk_cases.attrs["date"],
        ),
    ],
)

vax_data = coviddata.uk.vaccinations()
vax_uptake = coviddata.uk.vaccination_uptake_by_area_date()

render_template(
    "vaccination.html",
    graphs={
        "vax_rate": vax_rate_graph(vax_data),
        "vax_cumulative": vax_cumulative_graph(vax_data),
    },
    sources=[
        (
            "UKHSA",
            "Coronavirus (COVID-19) in the UK",
            "https://coronavirus.data.gov.uk",
            vax_data.attrs["date"],
        )
    ],
)

if os.environ.get("SKIP_SLOW"):
    print("SKIPPING SLOW STUFF")
    sys.exit(1)


app_data = NHSAppData()
exposures = app_data.exposures()
render_template(
    "app.html",
    graphs={
        "risky_venues": risky_venues(app_data.risky_venues()),
        "app_keys": app_keys(exposures),
        "app_keys_risk": app_keys(exposures, by="interval"),
    },
    sources=[
        (
            "Russ Garrett",
            "NHS COVID-19 App Data",
            "https://github.com/russss/nhs-covid19-app-data",
            date.today(),
        )
    ],
    risky_venues_count=app_data.risky_venues().count()["id"],
    risky_venues_unique=len(pd.unique(app_data.risky_venues()["id"])),
)


cog_metadata = fetch_cog_metadata()

try:
    lin_prev = lineage_prevalence(cog_metadata)
except Exception:
    print("Error generating lineage prevalence")
    lin_prev = None

render_template(
    "genomics.html",
    graphs={
        "genomes_by_nation": genomes_by_nation(cog_metadata),
        "mutation_prevalence": mutation_prevalence(cog_metadata),
        "lineage_prevalence": lin_prev,
    },
    sources=[
        (
            "COVID-19 Genomics UK (COG-UK) Consortium",
            "Latest sequence metadata",
            "https://www.cogconsortium.uk/",
            date.today(),
        )
    ],
)
