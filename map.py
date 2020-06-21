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


def region_data(new_cases, populations):
    history_days = 45
    weekly_cases = new_cases.rolling(date=7).sum()

    cases = {}
    for gss_code in weekly_cases["gss_code"].values:
        this_week = int(weekly_cases.sel(gss_code=gss_code).values[-1])
        history = new_cases[:, -history_days:].sel(gss_code=gss_code).values
        cases[gss_code] = {
            "prevalence": (this_week / populations[gss_code]),
            "cases": this_week,
            "history": list(map(int, history)),
        }
    return cases


def map_data(eng_data, wales_data, scot_data, populations, scot_populations, provisional_days):
    scot_data = correct_scottish_data(scot_data)
    eng_new_cases = (
        eng_data["cases"]
        .ffill("date")
        .fillna(0)[:, :-provisional_days]
        .diff("date")
    )
    wales_new_cases = (
        wales_data["cases"]
        .ffill("date")
        .fillna(0)[:, :-provisional_days]
        .diff("date")
    )
    scot_new_cases = (
        scot_data["corrected_cases"]
        .ffill("date")
        .fillna(0)
        .diff("date")
    )

    cases_england = region_data(eng_new_cases, populations)
    cases_wales = region_data(wales_new_cases, populations)
    cases_scotland = region_data(scot_new_cases, scot_populations)
    return {"england": cases_england, "scotland": cases_scotland, "wales": cases_wales}
