import pandas as pd
from django.core.management.base import BaseCommand
from interactiveMap.models import Location
import os
from sqlalchemy import create_engine

class Command(BaseCommand):
    """
    Load a CSV file to the database
    """

    def handle(self, *args, **options):

        parent = os.path.dirname
        file_path = os.path.join(parent(parent(parent(parent((__file__))))), 'filestorage', 'csv', '20230501.00.csv')

        df = pd.read_csv(file_path)

        engine = create_engine("postgresql://meteoadmin:test123@localhost:5432/meteo_global")

        df.to_sql(Location._meta.db_table, if_exists='append', con=engine, index=False)

