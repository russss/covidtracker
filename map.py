def map_data(data, positivity, provisional_days):
    history_days = 44

    data = data.ffill("date").fillna(0).diff("date")
    # Filter out numbers below 0 which happen when cases are un-reported.
    data = data.where(data > 0, 0)

    weekly = data.rolling(date=7).sum()
    weekly = weekly.where(weekly > 0, 0)

    result = {}
    for gss_code in weekly["gss_code"].values:
        ser = weekly.sel(gss_code=gss_code)
        cases = ser["cases"].values[-1]
        cases_norm = ser["cases_norm"].values[-1]

        change = ser["cases_norm"].values[-1] - ser["cases_norm"].values[-8]

        if provisional_days is not None:
            cases = max(
                cases,
                ser["cases"].values[-provisional_days],
            )
            cases_norm = max(
                cases_norm,
                ser["cases_norm"].values[-provisional_days],
            )
            change = max(
                change,
                ser["cases_norm"].values[-provisional_days]
                - ser["cases_norm"].values[-(provisional_days + 7)],
            )

        history = data.sel(gss_code=gss_code)["cases"].values[-history_days:]

        if gss_code in positivity.gss_code:
            pos = positivity.sel(gss_code=gss_code)["positivity"][-1].item()
        else:
            pos = None

        result[gss_code] = {
            "prevalence": cases_norm,
            "change": change,
            "positivity": pos,
            "cases": int(cases),
            "history": list(map(int, history)),
            "provisional_days": provisional_days,
        }

    return result
