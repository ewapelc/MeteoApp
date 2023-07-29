# Generated by Django 3.2.18 on 2023-07-29 18:34

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactiveMap', '0002_auto_20230607_0906'),
    ]

    operations = [
        migrations.CreateModel(
            name='CountryRegion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country_iso3', models.CharField(max_length=3, verbose_name='3 Digit ISO')),
                ('country_name', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=50)),
                ('type', models.CharField(max_length=50)),
                ('geometry', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
            ],
        ),
    ]
