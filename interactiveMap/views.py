import folium as folium
import geopandas as gpd
from datetime import datetime

import pandas as pd
from django.shortcuts import redirect
from django.views import generic
from django.contrib.gis.geos import Point
from .models import Location, WorldBorder
from django.db.models import Subquery, Avg

from django.shortcuts import render
from plotly.offline import plot
from plotly.graph_objs import Scatter
import plotly.express as px


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

        # for station in points:
        #     folium.Marker([station['latitude'], station['longitude']],
        #                   popup=station[self.request.session['meteo_var']]).add_to(m)


        # Plotly timeseries plot
        #----------------
        #
        queryset = Location.objects.values('time').annotate(temp=Avg('temp')).order_by()
        time = queryset.values_list('time', flat=True)
        temp = queryset.values_list('temp', flat=True)
        fig = px.line(
            x=time,
            y=temp,
            width=900,
            height=250,
            labels={"x": "Date", "y": "Variable"}
        )

        # style the plot
        fig.update_layout(margin=dict(b=30, l=30, r=30, t=30))

        # remove label titles
        fig.update_layout(yaxis_title=None)
        fig.update_layout(xaxis_title=None)


        fig = fig._repr_html_()  # updated

        context['plot_div'] = fig


        # Choropleth
        # ------------------------------------------------------------------

        # Required for Choropleth map
        borders_df = gpd.GeoDataFrame(WorldBorder.objects.all().values())
        # # meteo_df = gpd.GeoDataFrame(Location.objects.filter(time=datetime_obj).values())
        # #
        borders_df.rename(columns={'mpoly': 'geometry', 'iso2': 'country_iso2'}, inplace=True)
        borders_df.drop(columns=['id'], inplace=True)
        # meteo_df.drop(columns=['id'], inplace=True)

        # Later - change into postgis function on Query results
        # sjoin_res = gpd.sjoin(meteo_df, borders_df, how="left", predicate="intersects")
        # res = sjoin_res[['latitude', 'longitude', 'time', 'step', 'atmosphereSingleLayer',
        #                  'valid_time', 'temp', 'rel_hum', 'tcc', 'spec_hum', 'u_wind', 'v_wind',
        #                  'gust', 'pwat', 'geometry', 'ISO2']]

        # results = Location.objects.filter(time=datetime_obj).annotate(
        #     country_iso2=Subquery(
        #         WorldBorder.objects.filter(
        #             mpoly__contains=OuterRef('geometry')
        #         ).values('iso2')
        #     )
        # )
        # ).values('country_iso2').annotate(
        #     temp_avg=Avg('temp')
        #     # rel_hum_avg=Avg('rel_hum'),
        #     # spec_hum_avg=Avg('spec_hum'),
        #     # tcc_avg=Avg('tcc'),
        #     # u_wind_avg=Avg('u_wind'),
        #     # v_wind_avg=Avg('v_wind'),
        #     # gust_avg=Avg('gust'),
        #     # pwat_avg=Avg('pwat')
        # ).order_by()

        context['results'] = Location.objects.values('time').annotate(temp=Avg('temp')).order_by()

        #
        # context['results'] = results.values('country_iso2').annotate(avg=Avg('temp'))



        # grouped = res.groupby('country_iso2').mean().reset_index()
        #
        # borders_df.set_index('country_iso2', inplace=True)
        # geo_json = gpd.GeoSeries(data=borders_df['geometry']).__geo_interface__
        #
        # folium.Choropleth(
        #     name="temp",
        #     geo_data=geo_json,
        #     data=grouped,
        #     columns=["ISO2", "temp"],
        #     key_on="feature.id",
        #     fill_color="YlGn",
        #     fill_opacity=0.7,
        #     line_opacity=0.2,
        #     legend_name="Temperature"
        # ).add_to(m)
        #
        # folium.Choropleth(
        #     name="rel_hum",
        #     geo_data=geo_json,
        #     data=grouped,
        #     columns=["ISO2", "rel_hum"],
        #     key_on="feature.id",
        #     fill_color="Blues",
        #     fill_opacity=0.7,
        #     line_opacity=0.2,
        #     legend_name="Rel hum"
        # ).add_to(m)
        #
        # folium.LayerControl().add_to(m)



        #--------------------------------




        m = m._repr_html_()  # updated
        context['map'] = m
        #-------


        return context



    def post(self, request, *args, **kwargs):
        request.session['country'] = request.POST.get('country')
        request.session['date'] = request.POST.get('date')
        request.session['meteo_var'] = request.POST.get('meteo_var')
        return redirect('/')




