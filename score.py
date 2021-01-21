import pandas as pd

PROVISIONAL_DAYS = 5


def calculate_score(deaths, cases, triage_online, triage_pathways, admissions):
    cases_change = (
        cases["cases_rolling"][:,:-PROVISIONAL_DAYS]
        / cases["cases_rolling"][:,:-PROVISIONAL_DAYS].shift(date=7)
    ).dropna("date") - 1
    deaths_change = (
        deaths["deaths_rolling"][:-PROVISIONAL_DAYS]
        / deaths["deaths_rolling"][:-PROVISIONAL_DAYS].shift(date=7)
    ).dropna("date") - 1
    online_change = (
        triage_online["count_rolling_7"]
        / triage_online["count_rolling_7"].shift(date=7)
    ).dropna("date") - 1
    pathways_change = (
        triage_pathways["count_rolling_7"]
        / triage_pathways["count_rolling_7"].shift(date=7)
    ).dropna("date") - 1 if triage_pathways else None
    admissions_change = (
        admissions["admissions_rolling"]
        / admissions["admissions_rolling"].shift(date=7)
    ).dropna("date") - 1

    data = {"scores": {}}
    for loc in [loc.item() for loc in cases_change["location"]]:
        data["scores"][loc] = {
            "cases": cases_change[:, -1].sel(location=loc).item() * 100,
            "deaths": deaths_change[-1].sel(location=loc).item() * 100,
            "triage_online": online_change[:, -1].sel(region=loc).item() * 100,
            "triage_pathways": pathways_change[:, -1].sel(region=loc).item() * 100 if triage_pathways else None,
            "admissions": admissions_change[:, -1].sel(location=loc).item() * 100,
        }

    data["dates"] = {
        "cases": pd.to_datetime(cases_change[:, -1]["date"].data),
        "deaths": pd.to_datetime(deaths_change[-1]["date"].data),
        "triage_online": pd.to_datetime(online_change[:, -1]["date"].data),
        "triage_pathways": pd.to_datetime(pathways_change[:, -1]["date"].data) if triage_pathways else None,
        "admissions": pd.to_datetime(admissions_change[:, -1]["date"].data),
    }
    return data
