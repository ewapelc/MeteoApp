import folium as folium
from django.shortcuts import render, redirect, reverse
from django.views import generic
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance
from .models import Location, WorldBorder
import pytz
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q

from django.http import HttpResponseRedirect
from django.contrib.sessions.backends.db import SessionStore

latitude = 51.919438
longitude = 19.145136

# srid - spatial reference system
user_location = Point(longitude, latitude, srid=4326)

# Create your views here.
#generic.ListView
class Home(generic.ListView):
    model = Location
    #context_object_name = 'stations'
    template_name = "stations/index.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Change this later
        if 'country' not in self.request.session:
            self.request.session['country'] = 10

        if 'meteo_var' not in self.request.session:
            self.request.session['meteo_var'] = 'temp'

        if 'date' not in self.request.session:
            self.request.session['date'] = 0
        #

        selected_country = WorldBorder.objects.filter(id=self.request.session['country']).values().last()

        # wyrzucić selected country z context??
        context['selected_country'] = WorldBorder.objects.filter(id=self.request.session['country']).values().last()

        country = WorldBorder.objects.filter(name=context['selected_country']['name']).values()
        country_geometry = country[0]['mpoly']

        datetime_obj = datetime.strptime((self.request.session['date']), "%d-%m-%Y %H:%M")
        points = Location.objects.filter(time=datetime_obj, geometry__intersects=country_geometry).values()

        context['count'] = points.count()
        context['stations'] = points
        context['countries'] = WorldBorder.objects.all().order_by('name')
        context['times'] = Location.objects.values('time').distinct().order_by('time')



        #------------
        m = folium.Map([selected_country['lat'], selected_country['lon']], zoom_start=3)
        folium.Marker(location=[selected_country['lat'], selected_country['lon']],
                      popup=selected_country['name']).add_to(m)

        for station in points:
            folium.Marker([station['latitude'], station['longitude']],
                          popup=station[self.request.session['meteo_var']]).add_to(m)


        m = m._repr_html_()  # updated
        context['map'] = m
        #-------


        return context



    def post(self, request, *args, **kwargs):
        request.session['country'] = request.POST.get('country')
        request.session['date'] = request.POST.get('date')
        request.session['meteo_var'] = request.POST.get('meteo_var')
        return redirect('/')




