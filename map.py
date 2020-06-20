import numpy as np
from datetime import date, timedelta


def correct_scottish_data(scot_data):
    """ Scotland started adding the UK "pillar 2" tests to their figures on
        2020-6-15. This causes a discontinuity. Spread the discontinuity over
        the preceding 50 days. This is awful code but I can't work out how to do it better.
    """
    scot_data["corrected_cases"] = scot_data["cases"].copy()
    spread_days = 50
    end = date(2020, 6, 15)
    start = end - timedelta(days=spread_days)

    for gss in scot_data["gss_code"].values:
        ser = scot_data.sel(gss_code=gss)["corrected_cases"]
        cases_added = (
            ser.sel(date="2020-06-15")
            - ser.sel(date="2020-06-14")
            - (ser.sel(date="2020-06-14") - ser.sel(date="2020-06-13"))
        )
        offset_cases = np.arange(0, spread_days) * (int(cases_added) / spread_days)
        off = np.where(ser["date"] == np.datetime64(start))[0][0]
        ser[off : off + spread_days] += offset_cases

    return scot_data


def map_data(by_ltla_gss, scot_data, populations, scot_populations, provisional_days):
    history_days = 45

    scot_data = correct_scottish_data(scot_data)

    eng_new_cases = (
        by_ltla_gss["cases"]
        .interpolate_na("date", method="nearest")
        .fillna(0)[:, :-provisional_days]
        .diff("date")
    )
    eng_weekly_cases = eng_new_cases.rolling(date=7).sum()

    scot_new_cases = (
        scot_data["cases"]
        .interpolate_na("date", method="nearest")
        .fillna(0)
        .diff("date")
    )
    scot_weekly_cases = scot_new_cases.rolling(date=7).sum()

    cases_england = {}

    for gss_code in eng_weekly_cases["gss_code"].values:
        this_week = int(eng_weekly_cases.sel(gss_code=gss_code).values[-1])
        history = eng_new_cases[:, -history_days:].sel(gss_code=gss_code).values
        cases_england[gss_code] = {
            "prevalence": (this_week / populations[gss_code]),
            "cases": this_week,
            "history": list(map(int, history)),
        }

    cases_scotland = {}

    for gss_code in scot_weekly_cases["gss_code"].values:
        this_week = int(scot_weekly_cases.sel(gss_code=gss_code).values[-1])
        history = scot_new_cases[:, -history_days:].sel(gss_code=gss_code).values
        cases_scotland[gss_code] = {
            "prevalence": (this_week / scot_populations[gss_code]),
            "cases": this_week,
            "history": list(map(int, history)),
        }

    return {"england": cases_england, "scotland": cases_scotland}
