import folium as folium
import geopandas as gpd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from shapely.geometry import Polygon
# import rasterio
# import rasterio.mask
# from rasterio.plot import show
# from rasterio.transform import Affine
import os
from PIL import Image

import pandas as pd
from django.shortcuts import redirect
from django.views import generic
from django.contrib.gis.geos import Point
from .models import Location, WorldBorder, CountryRegion
from django.db.models import Subquery, Avg, Count, F, OuterRef

import plotly.express as px


#generic.ListView
class InteractiveMap(generic.ListView):
    model = Location
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

        if 'visual_type' not in self.request.session:
            self.request.session['visual_type'] = 'points'

        if self.request.session['country'] == '':
            self.request.session['country'] = 10

        if self.request.session['meteo_var'] == '':
            self.request.session['meteo_var'] = 'temp'

        if self.request.session['date'] == '':
            self.request.session['date'] = 0

        if self.request.session['visual_type'] == '':
            self.request.session['visual_type'] = 'points'
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


        # Plotly timeseries plot
        # ----------------
        #

        queryset = Location.objects.filter(geometry__intersects=country_geometry).values('time').annotate(
            meteo_var=Avg(selected_var)).order_by()
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

        avg = Location.objects.filter(geometry__intersects=country_geometry).values('time'). \
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

        # initialize blank folium map
        m = folium.Map([selected_country['lat'], selected_country['lon']], zoom_start=7)

        # folium.raster_layers.TileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}.png?api_key=e379e366-57a6-4682-ad6f-2f1a779548b2',
        #                                name='Stadia.AlidadeSmoothDark',
        #                                attr='Stadia.AlidadeSmoothDark').add_to(m)
        # folium.raster_layers.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        #                                name='Esri.WorldImagery',
        #                                attr='Esri.WorldImagery').add_to(m)
        #
        # folium.LayerControl().add_to(m)

        if self.request.session['visual_type'] == 'points':
            self.render_points(map=m, points=points, context=context, selected_country=selected_country, selected_var=selected_var)
        elif self.request.session['visual_type'] == 'choropleth':
            self.render_choropleth(m=m, datetime_obj=datetime_obj)


        m = m._repr_html_()
        context['map'] = m


        return context



    def post(self, request, *args, **kwargs):
        request.session['visual_type'] = request.POST.get('visual_type')
        request.session['country'] = request.POST.get('country')
        request.session['date'] = request.POST.get('date')
        request.session['meteo_var'] = request.POST.get('meteo_var')
        return redirect('/map')


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

    def render_points(self, map, points, context, selected_country, selected_var):
        var_data = self.long_name_and_unit(selected_var)

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
                          popup=popup
                          ).add_to(map)

    def render_choropleth(self, m, datetime_obj):
        # get data
        world = list(WorldBorder.objects.values('iso2', geometry=F('mpoly')))
        #
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
        #
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
        geojson1 = folium.features.GeoJson(
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

        # add popups
        geojson2 = folium.features.GeoJson(
            data=data_gdf,
            name='Temperature',
            smooth_factor=2,
            style_function=lambda x: {'color': 'black', 'fillColor': 'transparent', 'weight': 0.5},
            tooltip=folium.features.GeoJsonTooltip(
                fields=['country_name',
                        'iso2',
                        'temp_avg',],
                aliases=['Country:',
                         'Country code:',
                         f"{temp_data['long_name']} [{temp_data['unit']}] ",],
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

        folium.LayerControl().add_to(m)


from django.shortcuts import render


def home(request):
    return render(request, 'stations/homepage.html')

def getting_started(request):
    return render(request, 'analysis_page/getting_started.html')

def timeseries(request):
    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'variables': ['temp', 'rel_hum', 'tcc', 'spec_hum', 'u_wind', 'v_wind', 'gust', 'pwat']
    }

    if request.method == 'POST':
        if 'plot-1' in request.POST:
            context['chosen_countries'] = WorldBorder.objects.filter(id__in=request.POST.getlist('country[]')).values()
            context['chosen_var'] = request.POST.get('variable')


            # plot 1 - multiple countries
            var_data = long_name_and_unit(context['chosen_var'])

            meteo_vars = []
            i = 0
            time = 0
            for country in context['chosen_countries']:
                if i == 0:
                    res = extract_var(country=country, meteo_variable=context['chosen_var'])
                    time = res['time']
                    meteo_var = res['meteo_var']
                else:
                    meteo_var = extract_var(country=country, meteo_variable=context['chosen_var'])['meteo_var']
                meteo_vars.append(meteo_var)

            timezone_corrected_l = [datetime.strptime(
                datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
                "%d-%m-%Y %H:%M"
            ) for TIME in time]

            fig = px.line(
                x=timezone_corrected_l,
                y=meteo_vars,
                title=f'Average {var_data["long_name"]} [{var_data["unit"]}] in Selected Countries',
                # width=900,
                # height=250,
                labels={"x": "Date", "value": var_data['long_name'] + ' [' + var_data['unit'] + ']'},
                markers=True
            )
            fig.update_layout(legend_title_text='Country')

            country_names = context['chosen_countries'].values_list('name', flat=True)
            old_names = ['wide_variable_' + str(num) for num in list(range(len(country_names)))]
            new_names = {old_names[i]: country_names[i] for i in range(len(old_names))}
            fig.for_each_trace(lambda t: t.update(name=new_names[t.name],
                                                  legendgroup=new_names[t.name],
                                                  hovertemplate=t.hovertemplate.replace(t.name, new_names[t.name])
                                                  )
                               )

            fig = fig._repr_html_()
            context['timeseries1'] = fig

        elif 'plot-5' in request.POST:
            # plot 5 - correlation
            context['chosen_country5'] = WorldBorder.objects.filter(id=request.POST.get('country5')).values().last()
            country_geometry = WorldBorder.objects.filter(name=context['chosen_country5']['name']).values().last()['mpoly']
            queryset = Location.objects.filter(geometry__intersects=country_geometry).values('time').annotate(
                avg_temp=Avg('temp')).annotate(
                avg_rel_hum=Avg('rel_hum')).annotate(
                avg_spec_hum=Avg('spec_hum')).order_by()
            temp = queryset.values_list('avg_temp', flat=True)
            rel_hum = queryset.values_list('avg_rel_hum', flat=True)
            spec_hum = queryset.values_list('avg_spec_hum', flat=True)
            meteo_vars = [temp, rel_hum, spec_hum]

            time = queryset.values_list('time', flat=True)
            timezone_corrected_l = [datetime.strptime(
                datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
                "%d-%m-%Y %H:%M"
            ) for TIME in time]

            fig = px.line(
                x=timezone_corrected_l,
                y=meteo_vars,
                title=f'Comparison of Average Values of Meteorological Variables in {context["chosen_country5"]["name"]}',
                # width=900,
                # height=250,
                labels={"x": "Date", "value": "Variables"},
                markers=True
            )
            fig.update_layout(legend_title_text='Variable')
            var_names = ['Temperature [K]', 'Relative Humidity [%]', 'Specific Humidity [kg/kg]']
            old_names = ['wide_variable_' + str(num) for num in list(range(len(var_names)))]
            new_names = {old_names[i]: var_names[i] for i in range(len(old_names))}
            fig.for_each_trace(lambda t: t.update(name=new_names[t.name],
                                                  legendgroup=new_names[t.name],
                                                  hovertemplate=t.hovertemplate.replace(t.name, new_names[t.name])
                                                  )
                               )
            fig = fig._repr_html_()
            context['timeseries5'] = fig

        elif 'plot-2' in request.POST:
            context['chosen_country2'] = WorldBorder.objects.filter(id=request.POST.get('country2')).values().last()
            context['chosen_var2'] = request.POST.get('variable2')
            context['regions'] = CountryRegion.objects.filter(country_iso3=context['chosen_country2']['iso3']).values()

            country_geometry = WorldBorder.objects.filter(name=context['chosen_country2']['name']).values().last()['mpoly']
            queryset = Location.objects.filter(geometry__intersects=country_geometry).annotate(
                region=Subquery(
                    CountryRegion.objects.filter(geometry__contains=OuterRef('geometry')).values('name')
                )
            ).values('time', context['chosen_var2'], 'region')

            queryset = queryset.values('time', 'region').annotate(meteo_var=Avg(context['chosen_var2'])).order_by()\
                .values('time', 'region', 'meteo_var')


            var_data = long_name_and_unit(context['chosen_var2'])

            time = queryset.values_list('time', flat=True)
            meteo_var = queryset.values_list('meteo_var', flat=True)
            region = queryset.values_list('region', flat=True)

            timezone_corrected_l = [datetime.strptime(
                datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
                "%d-%m-%Y %H:%M"
            ) for TIME in time]

            fig = px.line(
                x=timezone_corrected_l,
                y=meteo_var,
                color=region,
                markers=True,
                title=f'Average {var_data["long_name"]} [{var_data["unit"]}] in each region of selected country',
                labels={"x": "Date", "y": var_data['long_name'] + ' [' + var_data['unit'] + ']'},
            )
            fig.update_layout(legend_title_text='Regions')

            fig = fig._repr_html_()
            context['timeseries2'] = fig




    return render(request, 'analysis_page/timeseries.html', context)


def extract_var(country, meteo_variable):
    # filter
    country_geometry = WorldBorder.objects.filter(name=country['name']).values().last()['mpoly']
    queryset = Location.objects.filter(geometry__intersects=country_geometry).values('time').annotate(
        meteo_var=Avg(meteo_variable)).order_by()
    # extract time and variable
    time = queryset.values_list('time', flat=True)
    meteo_var = queryset.values_list('meteo_var', flat=True)
    #
    return {'time': time, 'meteo_var': meteo_var}


def interpolation(request):
    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'variables': ['temp', 'rel_hum', 'tcc', 'spec_hum', 'u_wind', 'v_wind', 'gust', 'pwat'],
        'times': Location.objects.values('time').distinct().order_by('time')
    }

    if request.method == 'POST':
        if 'plot-1' in request.POST:
            context['chosen_country'] = WorldBorder.objects.filter(id=request.POST.get('country')).values().last()
            context['chosen_var'] = request.POST.get('variable')
            context['chosen_date'] = datetime.strptime((request.POST.get('date')), "%d-%m-%Y %H:%M")

            # geopandas visualization
            # filter points
            points = list(Location.objects.filter(time=context['chosen_date'], geometry__intersects=context['chosen_country']['mpoly'])\
                .values(context['chosen_var'], 'geometry'))
            country = list(WorldBorder.objects.filter(id=request.POST.get('country')).values('iso2', geometry=F('mpoly')))

            # transform data
            country_gdf = gpd.GeoDataFrame(country, crs='EPSG:4326')
            wkt1 = country_gdf.geometry.apply(lambda x: x.wkt)
            country_gdf = gpd.GeoDataFrame(country_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs='EPSG:4326')

            data_df = pd.DataFrame(points)
            data_df.dropna(axis=0, inplace=True)
            wkt2 = data_df.geometry.apply(lambda x: x.wkt)
            data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs='EPSG:4326')

            [fig, plot] = get_plot(country_gdf, data_gdf, context['chosen_var'], context['chosen_date'])

            context['matplotlib_plot'] = plot


    return render(request, 'analysis_page/interpolation.html', context)

def get_graph():
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png)
    graph = graph.decode('utf-8')
    buffer.close()
    return graph


def get_plot(country_gdf, data_gdf, chosen_var, chosen_date):
    plt.switch_backend('AGG')
    fig, ax = plt.subplots(figsize=(10, 7))

    # country borders
    country_gdf.plot(ax=ax, edgecolor="black", linewidth=0.5, color='white')

    # bins
    step = 0.125

    all_points = data_gdf.geometry.tolist()
    all_poly = [Polygon([[first.x - step, first.y + step],
                                          [first.x + step, first.y + step],
                                          [first.x + step, first.y - step],
                                          [first.x - step, first.y - step],
                                          [first.x - step, first.y + step]]) for first in all_points]

    poly_df = gpd.GeoDataFrame({'geometry': all_poly}, crs="EPSG:4326")
    poly_df['variable'] = data_gdf[chosen_var]
    poly_df.plot(ax=ax, edgecolor="white", linewidth=0.5, column="variable", cmap="viridis", alpha=.5, legend=True)

    # points
    # data_gdf.plot(ax=ax, column=chosen_var, cmap="viridis", legend=True, edgecolor="black", linewidth=0.2,
    #             legend_kwds={'shrink': 0.75}, markersize=300, marker='s')
    data_gdf.geometry.plot(ax=ax, color='white', markersize=1)

    var_data = long_name_and_unit(chosen_var)
    date_str = datetime.strftime(chosen_date + timedelta(hours=2), "%d-%m-%Y %H:%M")
    ax.set_title(f'{var_data["long_name"]} [{var_data["unit"]}] on {date_str}', fontdict={'fontsize': '15', 'fontweight': '3'})

    plt.tight_layout()
    plot = get_graph()
    return [fig, plot]


# def export_kde_raster(Z, XX, YY, min_x, max_x, min_y, max_y, proj, filename):
#     '''Export and save a kernel density raster.'''
#
#     # Get resolution
#     xres = (max_x - min_x) / len(XX)
#     yres = (max_y - min_y) / len(YY)
#
#     # Set transform
#     transform = Affine.translation(min_x - xres / 2, min_y - yres / 2) * Affine.scale(xres, yres)
#
#     # Export array as raster
#     with rasterio.open(
#             filename,
#             mode = "w",
#             driver = "GTiff",
#             height = Z.shape[0],
#             width = Z.shape[1],
#             count = 1,
#             dtype = Z.dtype,
#             crs = proj,
#             transform = transform,
#     ) as new_dataset:
#             new_dataset.write(Z, 1)

def kriging():
    '''Adapted from https://pygis.io/docs/e_interpolation.html#kriging'''





def animation(request):
    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'variables': ['temp', 'rel_hum', 'tcc', 'spec_hum', 'u_wind', 'v_wind', 'gust', 'pwat'],
    }

    if request.method == 'POST':
        if 'plot-1' in request.POST:
            context['chosen_country'] = WorldBorder.objects.filter(id=request.POST.get('country')).values().last()
            context['chosen_var'] = request.POST.get('variable')

            parent = os.path.dirname
            path_to_gif = os.path.join(parent((__file__)), 'static', 'images', 'animation.gif')
            if path_to_gif:
                os.remove(path_to_gif)


            # filter and transofrm borders data
            country = list(
                WorldBorder.objects.filter(id=request.POST.get('country')).values('iso2', geometry=F('mpoly')))

            country_gdf = gpd.GeoDataFrame(country, crs='EPSG:4326')
            wkt1 = country_gdf.geometry.apply(lambda x: x.wkt)
            country_gdf = gpd.GeoDataFrame(country_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs='EPSG:4326')


            all_dates = list(Location.objects.values('time').distinct().order_by('time'))
            for date in all_dates:
                # filter and tranform meteorological data
                points = list(Location.objects.filter(time=date['time'],
                                                      geometry__intersects=context['chosen_country']['mpoly']) \
                              .values(context['chosen_var'], 'geometry'))

                data_df = pd.DataFrame(points)
                data_df.dropna(axis=0, inplace=True)
                wkt2 = data_df.geometry.apply(lambda x: x.wkt)
                data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs='EPSG:4326')

                [fig, plot] = get_plot(country_gdf, data_gdf, context['chosen_var'], date['time'])

                # file destination
                date_str = datetime.strftime(date['time'] + timedelta(hours=2), "%d%m%Y-t%Hz")

                filename = date_str + '-frame.png'
                parent = os.path.dirname
                destination = os.path.join(parent(parent((__file__))), 'filestorage', 'animations', 'frames', filename)

                # save result
                result = fig.get_figure()
                result.savefig(destination, format='png', dpi=100)

            # here read all saved plots and make a gif, later return gif to template

            # Create the frames
            frames = []
            path = os.path.join(parent(parent((__file__))), 'filestorage', 'animations', 'frames')
            for i in os.listdir(path):
                new_frame = Image.open(os.path.join(path, i))
                frames.append(new_frame)

            # Save into a GIF file that loops forever
            #path_to_gif = os.path.join(parent(parent((__file__))), 'filestorage', 'animations', 'gif')
            path_to_gif = os.path.join(parent((__file__)), 'static', 'images')
            gif_destination = os.path.join(path_to_gif, 'animation.gif')
            frames[0].save(gif_destination, format='GIF',
                           append_images=frames[1:],
                           save_all=True,
                           duration=900, loop=0)


            # remove frames
            path = os.path.join(parent(parent((__file__))), 'filestorage', 'animations', 'frames')
            for file_name in os.listdir(path):
                # construct full file path
                file = path + file_name
                if os.path.isfile(file):
                    os.remove(file)


            context['animation_gif'] = True



    return render(request, 'analysis_page/animation.html', context)


def clusterization(request):
    return render(request, 'analysis_page/clusterization.html')

def long_name_and_unit(var):
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





