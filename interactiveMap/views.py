import folium as folium
import geopandas as gpd
from datetime import datetime, timedelta

import pandas as pd
from django.shortcuts import redirect
from django.views import generic
from django.contrib.gis.geos import Point
from .models import Location, WorldBorder
from django.db.models import Subquery, Avg, Count, F, OuterRef
from itertools import chain

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
        # change this later
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

        selected_var = self.request.session['meteo_var']
        var_data = self.long_name_and_unit(selected_var)


        #------------
        m = folium.Map([selected_country['lat'], selected_country['lon']], zoom_start=7)

        for station in points:
            card_points = self.cardinal_points(lat=station['latitude'], lon=station['longitude'])
            # setup the content of the popup
            html = '''\
            <body style="background-color:pink;">
            <p style="color:red;">Country name: <br><strong>{country}</strong></p>
            <p>Location coordinates:<br>
            Latitude: <strong>{lat} {cp_lat}</strong><br>
            Longitude <strong>{lon} {cp_lon}</strong>
            </p>
            <p>{var_name}: <br><strong>{value} [{var_unit}]</strong></p>
            </body>\
            '''.format(country=context['selected_country']['name'],
                       lat=station['latitude'],
                       cp_lat=card_points['lat'],
                       lon=station['longitude'],
                       cp_lon=card_points['lon'],
                       value=station[self.request.session['meteo_var']],
                       var_name=var_data['long_name'],
                       var_unit=var_data['unit'])

            iframe = folium.IFrame(html, width=200, height=200)

            # initialize the popup
            popup = folium.Popup(iframe)

            # create marker
            folium.Marker([station['latitude'], station['longitude']],
                          popup=popup).add_to(m)


        # Plotly timeseries plot
        #----------------
        #


        queryset = Location.objects.filter(geometry__intersects=country_geometry).values('time').annotate(meteo_var=Avg(selected_var)).order_by()
        time = queryset.values_list('time', flat=True)
        meteo_var = queryset.values_list('meteo_var', flat=True)

        timezone_corrected_l = [datetime.strptime(
            datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
            "%d-%m-%Y %H:%M"
        ) for TIME in time]

        fig = px.line(
            x=timezone_corrected_l,
            y=meteo_var,
            title=f'Average {var_data["long_name"]} [{var_data["unit"]}] in {context["selected_country"]["name"]}',
            width=900,
            height=250,
            labels={"x": "Date", "y": var_data['long_name'] + ' [' + var_data['unit'] + ']'},
            markers=True
        )

        avg = Location.objects.filter(geometry__intersects=country_geometry).values('time').\
            annotate(meteo_var=Avg(selected_var)).order_by().aggregate(avg=Avg('meteo_var'))['avg']

        fig.add_hline(y=avg, line_width=3, line_dash="dash", line_color="red")

        time = queryset.filter(time=datetime_obj).values_list('time', flat=True)
        val = queryset.filter(time=datetime_obj).values_list('meteo_var', flat=True)

        timezone_corrected = datetime.strptime(
            datetime.strftime(time[0] + timedelta(hours=2), "%d-%m-%Y %H:%M"),
            "%d-%m-%Y %H:%M"
        )

        fig.add_scatter(
            x=[timezone_corrected],
            y=list(val),
            marker=dict(size=10, color="red"),
            name='Selected date',
        )

        # style the plot
        fig.update_layout(margin=dict(b=30, l=30, r=30, t=30))

        # # remove label titles
        # fig.update_layout(yaxis_title=None)
        # fig.update_layout(xaxis_title=None)

        fig = fig._repr_html_()  # updated

        context['plot_div'] = fig


        # Choropleth
        # ------------------------------------------------------------------

        # initialize blank folium map
        m = folium.Map([selected_country['lat'], selected_country['lon']], zoom_start=7)

        # get data
        world = list(WorldBorder.objects.values('iso2', geometry=F('mpoly')))

        iso2_codes = list(WorldBorder.objects.order_by('iso2').values_list('iso2', flat=True))
        data = [self.get_avg_by_country(datetime_obj=datetime_obj, country_iso2=ISO2_CODE) for ISO2_CODE in iso2_codes]

        # transform data
        world_gdf = gpd.GeoDataFrame(world, crs='EPSG:4326')
        wkt1 = world_gdf.geometry.apply(lambda x: x.wkt)
        world_gdf = gpd.GeoDataFrame(world_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs='EPSG:4326')

        data_df = pd.DataFrame(data)
        data_df.dropna(axis=0, inplace=True)
        wkt2 = data_df.geometry.apply(lambda x: x.wkt)
        data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs='EPSG:4326')

        # initialize choropleth maps
        self.create_choropleth(map=m, variable='temp', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='viridis')
        self.create_choropleth(map=m, variable='rel_hum', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='Blues')
        self.create_choropleth(map=m, variable='spec_hum', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='Reds')
        self.create_choropleth(map=m, variable='tcc', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='Oranges')
        self.create_choropleth(map=m, variable='pwat', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='Greens')
        self.create_choropleth(map=m, variable='u_wind', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='PuRd')
        self.create_choropleth(map=m, variable='v_wind', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='OrRd')
        self.create_choropleth(map=m, variable='gust', datetime_obj=datetime_obj, geo_data=world_gdf, data=data_df, color_palette='GnBu')

        temp_data = self.long_name_and_unit('temp')
        rel_hum_data = self.long_name_and_unit('rel_hum')
        spec_hum_data = self.long_name_and_unit('spec_hum')
        tcc_data = self.long_name_and_unit('tcc')
        pwat_data = self.long_name_and_unit('pwat')
        u_wind_data = self.long_name_and_unit('u_wind')
        v_wind_data = self.long_name_and_unit('v_wind')
        gust_data = self.long_name_and_unit('gust')

        # add popups
        geojson = folium.features.GeoJson(
            data=data_gdf,
            name='Temperature',
            smooth_factor=2,
            style_function=lambda x: {'color': 'black', 'fillColor': 'transparent', 'weight': 0.5},
            tooltip=folium.features.GeoJsonTooltip(
                fields=['country_name',
                        'iso2',
                        'temp_avg',
                        'rel_hum_avg',
                        'spec_hum_avg',
                        'tcc_avg',
                        'pwat_avg',
                        'u_wind_avg',
                        'v_wind_avg',
                        'gust_avg'],
                aliases=['Country:',
                         'Country code:',
                         f"{temp_data['long_name']} [{temp_data['unit']}] ",
                         f"{rel_hum_data['long_name']} [{rel_hum_data['unit']}] ",
                         f"{spec_hum_data['long_name']} [{spec_hum_data['unit']}] ",
                         f"{tcc_data['long_name']} [{tcc_data['unit']}] ",
                         f"{pwat_data['long_name']} [{pwat_data['unit']}] ",
                         f"{u_wind_data['long_name']} [{u_wind_data['unit']}] ",
                         f"{v_wind_data['long_name']} [{v_wind_data['unit']}] ",
                         f"{gust_data['long_name']} [{gust_data['unit']}] ", ],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                               background-color: #F0EFEF;
                               border: 2px solid black;
                               border-radius: 3px;
                               box-shadow: 3px;
                           """,
                max_width=800, ),
            highlight_function=lambda x: {'weight': 3, 'fillColor': 'grey'},
        ).add_to(m)
        #----------------------------------------------------


        folium.LayerControl().add_to(m)



        # X=Location.objects.filter(geometry__intersects=country_geometry).values('time').annotate(meteo_var=Avg(selected_var)).order_by()
        #
        # # WAZNE
        # data = Location.objects.filter(time=datetime_obj).annotate(\
        #         iso2=Subquery(\
        #             WorldBorder.objects.filter(mpoly__contains=OuterRef('geometry')).values('iso2'))
        #     ).values('iso2').annotate(avg=Avg('temp')).order_by().values('iso2', 'avg')
        #
        # context['results'] = world



        m = m._repr_html_()
        context['map'] = m


        return context



    def post(self, request, *args, **kwargs):
        request.session['country'] = request.POST.get('country')
        request.session['date'] = request.POST.get('date')
        request.session['meteo_var'] = request.POST.get('meteo_var')
        return redirect('/')


    def long_name_and_unit(self, var):
        if var == 'temp':
            return {'long_name': 'Temperature', 'unit': 'K'}
        elif var == 'rel_hum':
            return {'long_name': 'Relative Humidity', 'unit': '%'}
        elif var == 'spec_hum':
            return {'long_name': 'Specific Humidity', 'unit': 'kg/kg'}
        elif var == 'tcc':
            return {'long_name': 'Total Cloud Cover', 'unit': '%'}
        elif var == 'u_wind':
            return {'long_name': 'U-Component of Wind', 'unit': 'm/s'}
        elif var == 'v_wind':
            return {'long_name': 'V-Component of Wind', 'unit': 'm/s'}
        elif var == 'gust':
            return {'long_name': 'Wind Speed (Gust)', 'unit': 'm/s'}
        elif var == 'pwat':
            return {'long_name': 'Precipitable Water', 'unit': 'kg/m^2'}


    def cardinal_points(self, lat, lon):
        card_point_lat = card_point_lon = ''

        if lat > 0 and lat <= 90:
            card_point_lat = 'N'
        elif lat < 0 and lat >= -90:
            card_point_lat = 'S'

        if lon < 0 and lon > -180:
            card_point_lon = 'W'
        elif lon > 0 and lon < 180:
            card_point_lon = 'E'

        return {'lat': card_point_lat, 'lon': card_point_lon}


    def kelvin_to_celcius(self, kelvin):
        return kelvin - 273.15


    def get_avg_by_country(self, country_iso2, datetime_obj):
        country = WorldBorder.objects.filter(iso2=country_iso2).values('mpoly', 'iso2', 'name')[0]
        data = Location.objects.filter(time=datetime_obj, geometry__intersects=country['mpoly']).aggregate(\
            temp_avg=Avg('temp'),
            rel_hum_avg=Avg('rel_hum'),
            spec_hum_avg=Avg('spec_hum'),
            tcc_avg=Avg('tcc'),
            u_wind_avg=Avg('u_wind'),
            v_wind_avg=Avg('v_wind'),
            gust_avg=Avg('gust'),
            pwat_avg=Avg('pwat')
        )
        data['iso2'] = country['iso2']
        data['country_name'] = country['name']
        data['geometry'] = country['mpoly']

        return data

    def create_choropleth(self, map, variable, datetime_obj, geo_data, data, color_palette):
        var_data = self.long_name_and_unit(variable)

        choropleth = folium.Choropleth(
            name=f"{var_data['long_name']}",
            geo_data=geo_data,
            data=data,
            columns=["iso2", f"{variable}_avg"],
            key_on="feature.properties.iso2",
            fill_color=color_palette,
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=f"Average {var_data['long_name']} [{var_data['unit']}] on {datetime_obj}"
        ).add_to(map)



