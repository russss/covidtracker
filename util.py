import xarray as xr


def dict_to_xr(source, dim_name):
    return xr.DataArray(data=list(source.values()), coords={dim_name: list(source.keys())},
                        dims=[dim_name])
