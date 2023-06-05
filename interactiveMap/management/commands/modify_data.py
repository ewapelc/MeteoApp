import geopandas as gpd
import xarray as xr
from django.core.management.base import BaseCommand
from interactiveMap.models import Location
import os
import re

class Command(BaseCommand):

    # def add_arguments(self, parser):
    #     # Positional arguments
    #     parser.add_argument("filename", nargs="+")

    def handle(self, *args, **options):
        """
        Prepare data before loading to database.
        """
        parent = os.path.dirname
        file_path = os.path.join(parent(parent(parent(parent((__file__))))), 'filestorage')

        for file in os.listdir(file_path):
            if file.endswith("grib2"):
                f = os.path.join(file_path, file)

                print("Processing file: ", file)

                # Prepare GRIB2 data
                ds = xr.open_dataset(f, engine="cfgrib", filter_by_keys={'typeOfLevel': 'isobaricInhPa'})
                df = ds.to_dataframe()

                # Wind Speed - 'gust'
                ds_surface = xr.open_dataset(f, engine="cfgrib", filter_by_keys={'typeOfLevel': 'surface'})
                ds_surface = ds_surface.get('gust').to_dataframe()
                df['gust'] = ds_surface['gust']

                # Precipitable Water - 'pwat'
                ds_single_layer = xr.open_dataset(f, engine="cfgrib",
                                                  filter_by_keys={'typeOfLevel': 'atmosphereSingleLayer'})
                ds_single_layer = ds_single_layer.get('pwat').to_dataframe()
                df['pwat'] = ds_single_layer['pwat']

                df.reset_index(inplace=True)

                # Convert longitude values into the standard range [-180, 180]
                df.loc[:, "longitude"] = df["longitude"].apply(lambda x: x - 180)
                df['geometry'] = gpd.GeoSeries.from_xy(df['longitude'], df['latitude']).set_crs('epsg:4326')

                new = {'isobaricInhPa': 'atmosphereSingleLayer',
                       't': 'temp',
                       'r': 'rel_hum',
                       'q': 'spec_hum',
                       'u': 'u_wind',
                       'v': 'v_wind'
                       }
                df.rename(columns=new, inplace=True)

                param_search = re.search('.*gfs[.](.*)[.]t(.*)z[.].*', str(file), re.IGNORECASE)

                if param_search:
                    date = param_search.group(1)
                    cycle = param_search.group(2)
                    new_filename = date + '.' + cycle

                    destination = os.path.join(file_path, 'csv', new_filename)
                    df.to_csv(destination + 'csv', index=False)



