import pandas as pd
from django.core.management.base import BaseCommand
from interactiveMap.models import RelevantCountry1
import os
from sqlalchemy import create_engine

class Command(BaseCommand):
    """
    Load a CSV file to the database - Relevant Countries
    """

    def handle(self, *args, **options):

        print("Load data to database.\n")

        parent = os.path.dirname
        f = os.path.join(parent(parent(parent(((__file__))))), 'data', 'relevant_countries', 'relevant.csv')

        if os.path.isfile(f):
            df = pd.read_csv(f)
            engine = create_engine("postgresql://meteoadmin:test123@localhost:5432/meteo_global")
            df.to_sql(RelevantCountry1._meta.db_table, if_exists='append', con=engine, index=False)

            print('\x1b[6;30;42m' + 'Successfully loaded data.' + '\x1b[0m')