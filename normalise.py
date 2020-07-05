import xarray as xr


def normalise_population(data, populations, name=None):
    """ Normalise the data in the DataArray `data` by the region populations in the
        mapping `populations`.

        Returns a new DataArray with the name `name`.
    """
    new_data = [s.data / populations[str(s["gss_code"].data)] for s in data]
    return xr.DataArray(
        new_data,
        {"date": data["date"], "gss_code": data["gss_code"]},
        dims=["gss_code", "date"],
        name=name,
    )
