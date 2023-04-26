from django.shortcuts import render
from django.views import generic
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import Map

latitude = 51.919438
longitude = 19.145136

# srid - spatial reference system
user_location = Point(longitude, latitude, srid=4326)

# Create your views here.
class Home(generic.ListView):
    model = Map
    context_object_name = 'stations'
    queryset = Map.objects.filter(latitude__gte=49, latitude__lte=55, longitude__gte=14, longitude__lte=24).values()
    #queryset = queryset.annotate('pwat')
    template_name = "stations/index.html"



