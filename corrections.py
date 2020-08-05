import numpy as np
import coviddata.uk
from datetime import date, timedelta

WALES_LTLAS = [
"Isle of Anglesey",
"Gwynedd",
"Conwy",
"Denbighshire",
"Flintshire",
"Wrexham",
"Ceredigion",
"Pembrokeshire",
"Carmarthenshire",
"Swansea",
"Neath Port Talbot",
"Bridgend",
"Vale of Glamorgan",
"Cardiff",
"Rhondda Cynon Taf",
"Caerphilly",
"Blaenau Gwent",
"Torfaen",
"Monmouthshire",
"Newport",
"Powys",
"Merthyr Tydfil"
]


def correct_scottish_data(scot_data):
    """ Scotland started adding the UK "pillar 2" tests to their figures on
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


def cases_by_nhs_region(la_region_mapping):
    regions = coviddata.uk.cases_phe("ltlas").ffill("date")
    nhs_regions = []
    for a in regions["location"]:
        name = str(a.data)
        if name in WALES_LTLAS:
            nhs_regions.append("Wales")
            continue
        if name == "Cornwall and Isles of Scilly":
            name = "Cornwall"
        if name == "Hackney and City of London":
            name = "Hackney"
        nhs_regions.append(la_region_mapping["nhs_name"][name])

    res = regions.assign_coords({"location": nhs_regions})
    return res.groupby("location").sum().drop_sel(location='Wales')
