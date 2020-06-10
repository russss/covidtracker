import pandas as pd


def calculate_score(deaths, cases, triage_online, triage_pathways, hospitals):
    cases_change = (
        cases["cases_rolling"] / cases["cases_rolling"].shift(date=7)
    ).dropna("date") - 1
    deaths_change = (
        deaths["deaths_rolling"] / deaths["deaths_rolling"].shift(date=7)
    ).dropna("date") - 1
    online_change = (
        triage_online["count_rolling_14"]
        / triage_online["count_rolling_14"].shift(date=14)
    ).dropna("date") - 1
    pathways_change = (
        triage_pathways["count_rolling_14"]
        / triage_pathways["count_rolling_14"].shift(date=14)
    ).dropna("date") - 1
    #    patients_change = (
    #        hospitals["patients_rolling_3"]
    #        / hospitals["patients_rolling_3"].shift(date=7)
    #    ).dropna("date") - 1

    data = {"scores": {}}
    for loc in [loc.item() for loc in cases_change["location"]]:
        data["scores"][loc] = {
            "cases": cases_change[:, -1].sel(location=loc).item() * 100,
            "deaths": deaths_change[-1].sel(location=loc).item() * 100,
            "triage_online": online_change[:, -1].sel(region=loc).item() * 100,
            "triage_pathways": pathways_change[:, -1].sel(region=loc).item() * 100,
            #            "patients": patients_change[:, -1].sel(location=loc).item() * 100
        }

    data["dates"] = {
        "cases": pd.to_datetime(cases_change[:, -1]["date"].data),
        "deaths": pd.to_datetime(deaths_change[-1]["date"].data),
        "triage_online": pd.to_datetime(online_change[:, -1]["date"].data),
        "triage_pathways": pd.to_datetime(pathways_change[:, -1]["date"].data),
        #        "patients": pd.to_datetime(patients_change[:, -1]["date"].data),
    }
    return data
