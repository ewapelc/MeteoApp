from django.shortcuts import render
from django.views import generic
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance
from .models import Map, WorldBorder

latitude = 51.919438
longitude = 19.145136

# srid - spatial reference system
user_location = Point(longitude, latitude, srid=4326)

# Create your views here.
class Home(generic.ListView):
    model = Map
    context_object_name = 'stations'
    # country_borders = Polygon(WorldBorder.objects.filter(name='Poland').get('mpoly'))
    # queryset = Map.objects.filter(latitude__gte=49, latitude__lte=55, longitude__gte=14, longitude__lte=24).values()
    country = WorldBorder.objects.filter(name='Poland').values()
    country_geometry = country[0]['mpoly']
    queryset = Map.objects.filter(geometry__intersects=country_geometry)
    # queryset = []
    # for station in points:
    #     p = Point(station.latitude, station.longitude)
    #     queryset.append(country_borders.contains(p))
    #queryset = Map.objects.annotate()
    template_name = "stations/index.html"



