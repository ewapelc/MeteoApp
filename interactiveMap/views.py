from django.shortcuts import render, redirect, reverse
from django.views import generic
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.db.models.functions import Distance
from .models import Location, WorldBorder

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
            self.request.session['country'] = 1
        #
        context['my_country'] = WorldBorder.objects.filter(id=self.request.session['country']).values().last()

        country = WorldBorder.objects.filter(name=context['my_country']['name']).values()
        country_geometry = country[0]['mpoly']
        points = Location.objects.filter(geometry__intersects=country_geometry)
        context['stations'] = points
        context['countries'] = WorldBorder.objects.all().order_by('name')
        return context



    def post(self, request, *args, **kwargs):
        # self.object = None
        # context = super().get_context_data()
        # context['country_selection'] = WorldBorder.objects.filter(id=request.POST.get('country')).values()
        # #---------------------
        # country = WorldBorder.objects.filter(name='Poland').values()
        # country_geometry = country[0]['mpoly']
        # points = Map.objects.filter(geometry__intersects=country_geometry)
        #
        # context['stations'] = points
        # context['countries'] = WorldBorder.objects.all()
        # return context
        request.session['country'] = request.POST.get('country')
        return redirect('/')




# country = WorldBorder.objects.filter(name='Poland').values()
# country_geometry = country[0]['mpoly']
# queryset = Map.objects.filter(geometry__intersects=country_geometry)