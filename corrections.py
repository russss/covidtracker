import numpy as np
import coviddata.uk
from datetime import date, timedelta


def correct_scottish_data(scot_data):
    """Scotland started adding the UK "pillar 2" tests to their figures on
    2020-6-15. This causes a discontinuity. Spread the discontinuity over
    the preceding 50 days. This is awful code but I can't work out how to do it better.
    """
    spread_days = 50
    end = date(2020, 6, 15)
    start = end - timedelta(days=spread_days)

    for gss in scot_data["gss_code"].values:
        ser = scot_data.sel(gss_code=gss)["cases"]
        cases_added = (
            ser.sel(date="2020-06-15")
            - ser.sel(date="2020-06-14")
            - (ser.sel(date="2020-06-14") - ser.sel(date="2020-06-13"))
        )
        offset_cases = np.arange(0, spread_days) * (int(cases_added) / spread_days)
        off = np.where(ser["date"] == np.datetime64(start))[0][0]
        ser[off : off + spread_days] += offset_cases

    return scot_data


def cases_by_nhs_region(data, la_region_mapping):
    nhs_regions = []
    for a in data["gss_code"]:
        name = str(a.data)
        if name[0] == "E":
            nhs_regions.append(la_region_mapping["nhs_name"][name])
        elif name[0] == "W":
            nhs_regions.append("Wales")
        elif name[0] == "S":
            nhs_regions.append("Scotland")
        elif name[0] == "N":
            nhs_regions.append("Northern Ireland")

    res = data.assign_coords({"gss_code": nhs_regions}).rename({'gss_code': 'location'})
    return (
        res.ffill("date").groupby("location")
        .sum()
        .drop_sel(location=["Wales", "Scotland", "Northern Ireland"])
    )
