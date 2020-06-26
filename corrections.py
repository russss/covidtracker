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
