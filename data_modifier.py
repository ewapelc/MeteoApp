import xarray as xr


def prepare_data(filepath):
    """
    Prepare data before loading to database.
    :param
    file: file in GRIB2 format
        The file that needs to be processed. Data is stored at different levels.
    :return:
    df: DataFrame
        DataFrame that contains all of the meteorological fields exctracted from different atmosphere levels, that
        correspond to specific locations [lat, lon].
    """
    ds = xr.open_dataset(filepath, engine="cfgrib", filter_by_keys={'typeOfLevel': 'isobaricInhPa'})
    df = ds.to_dataframe()

    # Add data saved on different levels

    # Wind Speed - 'gust'
    ds_surface = xr.open_dataset(filepath, engine="cfgrib", filter_by_keys={'typeOfLevel': 'surface'})
    df_surface = ds_surface.get('gust').to_dataframe()
    df['gust'] = df_surface['gust']

    # Precipitable Water - 'pwat'
    ds_single_layer = xr.open_dataset(filepath, engine="cfgrib",
                                      filter_by_keys={'typeOfLevel': 'atmosphereSingleLayer'})
    df_single_layer = ds_single_layer.get('pwat').to_dataframe()
    df['pwat'] = df_single_layer['pwat']

    df.reset_index(inplace=True)

    # Convert longitude values from range [0, 360] into the standard range [-180, 180]
    df.loc[:, "longitude"] = df["longitude"].apply(lambda x: x - 180)

    return df

