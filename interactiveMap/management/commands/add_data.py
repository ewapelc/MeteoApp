import pandas as pd
from django.core.management.base import BaseCommand
from interactiveMap.models import Location
import os
from sqlalchemy import create_engine
import fnmatch

class Command(BaseCommand):
    """
    Load a CSV file to the database
    """

    # def add_arguments(self, parser):
    #     # Positional arguments
    #     parser.add_argument("filename", nargs="+")

    def handle(self, *args, **options):

        parent = os.path.dirname
        file_path = os.path.join(parent(parent(parent(parent((__file__))))), 'filestorage', 'csv')
        n = len(fnmatch.filter(os.listdir(file_path), '*.csv'))
        i = 0

        print("Load data to database.\n")

        for file in os.listdir(file_path):
            if file.endswith("csv"):
                i = i + 1
                print(f"[{i}/{n}] Processing file: ", file)

                f = os.path.join(file_path, file)
                df = pd.read_csv(f)

                engine = create_engine("postgresql://meteoadmin:test123@localhost:5432/meteo_global")

                df.to_sql(Location._meta.db_table, if_exists='append', con=engine, index=False)


        print('\x1b[6;30;42m' + 'Successfully loaded data.' + '\x1b[0m')

