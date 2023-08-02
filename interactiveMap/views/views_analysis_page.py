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
from interactiveMap.models import Location, WorldBorder, CountryRegion
from django.db.models import Subquery, Avg, Count, F, OuterRef

import plotly.express as px

from django.shortcuts import render


def home(request):
    context = {
        'variables': ['one', 'two', 'three']
    }
    return render(request, 'stations/homepage.html', context)

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
            path_to_gif = os.path.join(parent(parent((__file__))), 'static', 'images', 'animation.gif')
            if os.path.isfile(path_to_gif):
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
                destination = os.path.join(parent(parent(parent(((__file__))))), 'filestorage', 'animations', 'frames', filename)

                # save result
                result = fig.get_figure()
                result.savefig(destination, format='png', dpi=100)

            # here read all saved plots and make a gif, later return gif to template

            # Create the frames
            frames = []
            path = os.path.join(parent(parent(parent((__file__)))), 'filestorage', 'animations', 'frames')
            for i in os.listdir(path):
                new_frame = Image.open(os.path.join(path, i))
                frames.append(new_frame)

            # Save into a GIF file that loops forever
            #path_to_gif = os.path.join(parent(parent((__file__))), 'filestorage', 'animations', 'gif')
            path_to_gif = os.path.join(parent(parent(((__file__)))), 'static', 'images')
            gif_destination = os.path.join(path_to_gif, 'animation.gif')
            frames[0].save(gif_destination, format='GIF',
                           append_images=frames[1:],
                           save_all=True,
                           duration=900, loop=0)


            # remove frames
            path = os.path.join(parent(parent(parent(((__file__))))), 'filestorage', 'animations', 'frames')
            for file_name in os.listdir(path):
                # construct full file path
                file = os.path.join(path, file_name)
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



