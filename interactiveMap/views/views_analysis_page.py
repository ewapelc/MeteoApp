import geopandas as gpd
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from shapely.geometry import Polygon
import os
from PIL import Image
import plotly.express as px
import libpysal
from sklearn.metrics import pairwise as skm
import numpy as np
import spopt
from affine import Affine

from pykrige.ok import OrdinaryKriging
from shapely.geometry import Point
from sklearn.model_selection import train_test_split

from interactiveMap.models import Location, WorldBorder, CountryRegion
from django.db.models import Subquery, Avg, F, OuterRef, Min, Max
from django.shortcuts import render


def home(request):
    """ Renders home page. """

    return render(request, 'stations/homepage.html')


def getting_started(request):
    """ Renders Getting Started tab. """

    return render(request, 'analysis_page/getting_started.html')


def timeseries(request):
    """ Renders the Timeseries tab. """

    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'variables': ['temp', 'rel_hum', 'tcc', 'spec_hum', 'u_wind', 'v_wind', 'gust', 'pwat']
    }

    if request.method == 'POST':
        if 'plot-1' in request.POST:
            # save user selection
            context['chosen_countries'] = WorldBorder.objects.filter(id__in=request.POST.getlist('country[]')).values()
            context['chosen_var'] = request.POST.get('variable')

            var_data = long_name_and_unit(context['chosen_var'])

            # save meteorological variables from selected countries
            meteo_vars = []
            i = 0
            time = 0
            for country in context['chosen_countries']:
                if i == 0:
                    res = extract_var(
                        country=country,
                        meteo_variable=context['chosen_var']
                    )
                    time = res['time']
                    meteo_var = res['meteo_var']
                else:
                    meteo_var = extract_var(
                        country=country,
                        meteo_variable=context['chosen_var']
                    )['meteo_var']
                meteo_vars.append(meteo_var)

            # transform timezone
            timezone_corrected_l = [datetime.strptime(
                datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
                "%d-%m-%Y %H:%M"
            ) for TIME in time]

            # plot the time series for selected countries
            fig = px.line(
                x=timezone_corrected_l,
                y=meteo_vars,
                title=f'Multi-Country Average {var_data["long_name"]} [{var_data["unit"]}] Time Series',
                labels={"x": "Time of Day (UTC)", "value": var_data['long_name'] + ' [' + var_data['unit'] + ']'},
                markers=True
            )
            fig.update_layout(legend_title_text='Country')

            # update traces
            country_names = context['chosen_countries'].values_list('name', flat=True)
            old_names = ['wide_variable_' + str(num) for num in list(range(len(country_names)))]
            new_names = {old_names[i]: country_names[i] for i in range(len(old_names))}
            fig.for_each_trace(
                lambda t: t.update(
                    name=new_names[t.name],
                    legendgroup=new_names[t.name],
                    hovertemplate=t.hovertemplate.replace(t.name, new_names[t.name])
                )
            )

            fig = fig._repr_html_()
            context['timeseries1'] = fig

        elif 'plot-5' in request.POST:
            # save user selection
            context['chosen_country5'] = WorldBorder.objects.filter(id=request.POST.get('country5')).values().last()
            context['chosen_variables5'] = request.POST.getlist('variable5[]')

            meteo_vars = []
            i = 0
            time = 0
            for variable in context['chosen_variables5']:
                if i == 0:
                    res = extract_var(
                        country=context['chosen_country5'],
                        meteo_variable=variable
                    )
                    time = res['time']
                    meteo_var = res['meteo_var']
                else:
                    meteo_var = extract_var(
                        country=context['chosen_country5'],
                        meteo_variable=variable
                    )['meteo_var']
                meteo_vars.append(meteo_var)

            # transform timezone
            timezone_corrected_l = [datetime.strptime(
                datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
                "%d-%m-%Y %H:%M"
            ) for TIME in time]

            # plot the time series for selected countries
            fig = px.line(
                x=timezone_corrected_l,
                y=meteo_vars,
                title=f'Comparison of Average Meteorological Trends in {context["chosen_country5"]["name"]} Time Series',
                labels={"x": "Time of Day (UTC)", "value": "Average Value"},
                markers=True
            )
            fig.update_layout(legend_title_text='Variable with Unit')

            # update traces
            variable_names = list(context['chosen_variables5'])
            old_names = ['wide_variable_' + str(num) for num in list(range(len(variable_names)))]
            full_names = ["".join([long_name_and_unit(var)["long_name"], " [", long_name_and_unit(var)["unit"], "]"])
                          for var in variable_names]
            new_names = {old_names[i]: full_names[i] for i in range(len(old_names))}
            fig.for_each_trace(
                lambda t: t.update(
                    name=new_names[t.name],
                    legendgroup=new_names[t.name],
                    hovertemplate=t.hovertemplate.replace(t.name, new_names[t.name])
                )
            )

            fig = fig._repr_html_()
            context['timeseries5'] = fig

        elif 'plot-2' in request.POST:
            # save user selection
            context['chosen_country2'] = WorldBorder.objects.filter(id=request.POST.get('country2')).values().last()
            context['chosen_var2'] = request.POST.get('variable2')

            # filter the data for regions
            queryset = Location.objects.filter(
                geometry__intersects=context['chosen_country2']['mpoly']
            ).annotate(
                region=Subquery(
                    CountryRegion.objects.filter(
                        country_iso3=context['chosen_country2']['iso3'],
                        geometry__contains=OuterRef('geometry')
                    ).values('name')
                )
            ).values('time', context['chosen_var2'], 'region')

            # get the average value of the selected variable for the regions
            queryset = queryset.values('time', 'region').annotate(
                meteo_var=Avg(context['chosen_var2'])
            ).order_by().values('time', 'region', 'meteo_var')

            var_data = long_name_and_unit(context['chosen_var2'])

            # get the data for the plot
            time = queryset.values_list('time', flat=True)
            meteo_var = queryset.values_list('meteo_var', flat=True)
            region = queryset.values_list('region', flat=True)

            # convert the timezone
            timezone_corrected_l = [datetime.strptime(
                datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
                "%d-%m-%Y %H:%M"
            ) for TIME in time]

            # plot the time series
            fig = px.line(
                x=timezone_corrected_l,
                y=meteo_var,
                color=region,
                markers=True,
                title=f'Country Region-wise Average {var_data["long_name"]} [{var_data["unit"]}] Time Series',
                labels={"x": "Time of Day (UTC)", "y": var_data['long_name'] + ' [' + var_data['unit'] + ']'},
            )
            fig.update_layout(legend_title_text='Regions')

            fig = fig._repr_html_()
            context['timeseries2'] = fig

    return render(request, 'analysis_page/timeseries.html', context)


def extract_var(country, meteo_variable):
    """ Extracts times and meteorological variable for a given country. """

    # filter
    country_geometry = WorldBorder.objects.filter(name=country['name']).values().last()['mpoly']
    queryset = Location.objects.filter(
        geometry__intersects=country_geometry
    ).values('time').annotate(
        meteo_var=Avg(meteo_variable)
    ).order_by()

    # extract time and variable
    time = queryset.values_list('time', flat=True)
    meteo_var = queryset.values_list('meteo_var', flat=True)

    return {'time': time, 'meteo_var': meteo_var}


def interpolation(request):
    """ Renders the Interpolation tab. """

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

            # projection string typical for California - change this later
            proj = "+proj=aea +lat_1=50 +lat_2=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=-4000000 +ellps=GRS80 +datum=NAD83 +units=m +no_defs "

            # filter and transform borders data
            country = list(
                WorldBorder.objects.filter(
                    id=request.POST.get('country')
                ).values('iso2', geometry=F('mpoly'))
            )

            # here change crs to 'EPSG:43'
            country_gdf = gpd.GeoDataFrame(country, crs=proj)
            wkt1 = country_gdf.geometry.apply(lambda x: x.wkt)
            country_gdf = gpd.GeoDataFrame(country_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs=proj)

            # filter and transform data
            points = list(
                Location.objects.filter(
                    time=context['chosen_date'],
                    geometry__intersects=context['chosen_country']['mpoly']
                ).values(context['chosen_var'], 'geometry')
            )
            data_df = pd.DataFrame(points)
            data_df.dropna(axis=0, inplace=True)
            wkt2 = data_df.geometry.apply(lambda x: x.wkt)
            data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs=proj)

            # get X and Y coordinates of rainfall points
            x_rain = data_gdf["geometry"].x
            y_rain = data_gdf["geometry"].y

            # create list of XY coordinate pairs
            coords_rain = [list(xy) for xy in zip(x_rain, y_rain)]

            # get extent of counties feature
            min_x_counties, min_y_counties, max_x_counties, max_y_counties = country_gdf.total_bounds

            # get list of rainfall "values"
            value_rain = list(data_gdf[context['chosen_var']])

            #-------------------------------------------------------------------------------
            # Split data into testing and training sets
            coords_rain_train, coords_rain_test, value_rain_train, value_rain_test = train_test_split(coords_rain,
                                                                                                      value_rain,
                                                                                                      test_size=0.20,
                                                                                                      random_state=42)

            # Create separate GeoDataFrames for testing and training sets
            rain_train_gdf = gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in coords_rain_train], crs=proj)
            rain_train_gdf["Actual_Value"] = value_rain_train
            rain_test_gdf = gpd.GeoDataFrame(geometry=[Point(x, y) for x, y in coords_rain_test], crs=proj)
            rain_test_gdf["Actual_Value"] = value_rain_test

            # Get minimum and maximum coordinate values of rainfall training points
            min_x_rain, min_y_rain, max_x_rain, max_y_rain = rain_train_gdf.total_bounds
            #-------------------------------------------------------------------------------

            # Adapted from: https://geostat-framework.readthedocs.io/projects/pykrige/en/latest/examples/04_krige_geometric.html

            # Create a 100 by 100 grid
            # Horizontal and vertical cell counts should be the same
            XX_pk_krig = np.linspace(min_x_rain, max_x_rain, 100)
            YY_pk_krig = np.linspace(min_y_rain, max_y_rain, 100)

            # Generate ordinary kriging object
            OK = OrdinaryKriging(
                np.array(x_rain),
                np.array(y_rain),
                value_rain,
                variogram_model="linear",
                verbose=False,
                enable_plotting=False,
                coordinates_type="euclidean",
            )

            # Evaluate the method on grid
            Z_pk_krig, sigma_squared_p_krig = OK.execute("grid", XX_pk_krig, YY_pk_krig)

            # Get resolution
            xres = (max_x_rain - min_x_rain) / len(XX_pk_krig)
            yres = (max_y_rain - min_y_rain) / len(YY_pk_krig)

            # Set transform
            transform = Affine.translation(min_x_rain - xres / 2, min_y_rain - yres / 2) * Affine.scale(xres, yres)

            plot_input = np.ma.getdata(Z_pk_krig)

            fig, ax = plt.subplots(1, figsize=(7, 7))

            # this line changes every plot
            plt.style.use('bmh')

            plt.imshow(plot_input, extent=[min_x_counties, max_x_counties, max_y_counties, min_y_counties])

            plt.gca().invert_yaxis()

            # # ax.plot(x_rain, y_rain, 'k.', markersize = 2, alpha = 0.5)
            country_gdf.plot(ax=ax, color='none', edgecolor='black')

            #ax.set_aspect('auto')

            plt.tight_layout()

            # convert the plot into memory buffer - needed for static plots
            fig = get_graph()

            # fig = interpolation_plot(
            #     country_gdf,
            #     data_gdf,
            #     datetime_obj,
            #     chosen_vars,
            #     chosen_country
            # )
            #
            context['interpolation_plot'] = fig

    return render(request, 'analysis_page/interpolation.html', context)


def interpolation_plot(country_gdf, data_gdf, datetime_obj, chosen_vars, chosen_country):
    """ Returns interpolation plot. """

    return 1


def get_graph():
    """ Saves the matplotlib plot to memory buffer. """

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png)
    graph = graph.decode('utf-8')
    buffer.close()
    return graph


def get_plot(country_gdf, data_gdf, chosen_country, chosen_var, chosen_date):
    """ Creates and returns a matplotlib spatial-binning plot from custom polygons. """

    plt.switch_backend('AGG')
    fig, ax = plt.subplots(figsize=(10, 7))

    # plot of country borders
    country_gdf.plot(
        ax=ax,
        edgecolor="black",
        linewidth=0.5,
        color='white'
    )

    # create custom polygons
    step = 0.125
    all_points = data_gdf.geometry.tolist()
    all_poly = [Polygon([
        [p.x - step, p.y + step],
        [p.x + step, p.y + step],
        [p.x + step, p.y - step],
        [p.x - step, p.y - step],
        [p.x - step, p.y + step]]) for p in all_points]

    # create GeoDataFrame from custom polygons
    poly_df = gpd.GeoDataFrame({'geometry': all_poly}, crs="EPSG:4326")
    poly_df['variable'] = data_gdf[chosen_var]

    # min, max values for normalization
    vmin = Location.objects.filter(
        geometry__intersects=chosen_country['mpoly']
    ).aggregate(min=Min(chosen_var))['min']
    vmax = Location.objects.filter(
        geometry__intersects=chosen_country['mpoly']
    ).aggregate(max=Max(chosen_var))['max']

    # plot the custom polygons, the fill color is mapped from the variable
    poly_df.plot(
        ax=ax,
        edgecolor="white",
        linewidth=0.1,
        column="variable",
        cmap="viridis"
    )

    # add details
    var_data = long_name_and_unit(chosen_var)
    date_str = datetime.strftime(chosen_date + timedelta(hours=2), "%d-%m-%Y %H:%M")
    ax.set_title(
        f'{var_data["long_name"]} [{var_data["unit"]}] in {chosen_country["name"]} at {date_str}',
        fontdict={'fontsize': '15', 'fontweight': '2'},
        pad=15
    )
    ax.set_xlabel(u"Longitude [\N{DEGREE SIGN}]")
    ax.set_ylabel(u"Latitude [\N{DEGREE SIGN}]")

    # normalized legend
    sm = plt.cm.ScalarMappable(cmap='viridis', norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    fig.colorbar(sm)

    plt.tight_layout()

    # # convert the plot into memory buffer - needed for static plots
    # plot = get_graph()
    return fig


def animation(request):
    """ Renders the Animation tab. """

    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'variables': ['temp', 'rel_hum', 'tcc', 'spec_hum', 'u_wind', 'v_wind', 'gust', 'pwat'],
    }

    if request.method == 'POST':
        if 'plot-1' in request.POST:
            context['chosen_country'] = WorldBorder.objects.filter(id=request.POST.get('country')).values().last()
            context['chosen_var'] = request.POST.get('variable')

            parent = os.path.dirname
            path_to_gif = os.path.join(parent(parent(__file__)), 'static', 'images', 'animation.gif')
            if os.path.isfile(path_to_gif):
                os.remove(path_to_gif)

            # filter and transform borders data
            country = list(
                WorldBorder.objects.filter(
                    id=request.POST.get('country')
                ).values('iso2', geometry=F('mpoly'))
            )

            country_gdf = gpd.GeoDataFrame(country, crs='EPSG:4326')
            wkt1 = country_gdf.geometry.apply(lambda x: x.wkt)
            country_gdf = gpd.GeoDataFrame(country_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs='EPSG:4326')

            all_dates = list(Location.objects.values('time').distinct().order_by('time'))
            for date in all_dates:
                # filter and transform meteorological data
                points = list(
                    Location.objects.filter(
                        time=date['time'],
                        geometry__intersects=context['chosen_country']['mpoly']
                    ).values(context['chosen_var'], 'geometry')
                )

                data_df = pd.DataFrame(points)
                data_df.dropna(axis=0, inplace=True)
                wkt2 = data_df.geometry.apply(lambda x: x.wkt)
                data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs='EPSG:4326')

                fig = get_plot(country_gdf, data_gdf, context['chosen_country'], context['chosen_var'], date['time'])

                # file destination
                date_str = datetime.strftime(date['time'] + timedelta(hours=2), "%d%m%Y-t%Hz")
                filename = date_str + '-frame.png'
                parent = os.path.dirname
                destination = os.path.join(
                    parent(parent(parent(__file__))), 'filestorage', 'animations', 'frames', filename
                )

                # save result
                result = fig.get_figure()
                result.savefig(destination, format='png', dpi=100)

            # create the frames
            frames = []
            path = os.path.join(parent(parent(parent(__file__))), 'filestorage', 'animations', 'frames')
            for i in os.listdir(path):
                new_frame = Image.open(os.path.join(path, i))
                frames.append(new_frame)

            # save into a GIF file that loops forever
            path_to_gif = os.path.join(parent(parent(__file__)), 'static', 'images')
            gif_destination = os.path.join(path_to_gif, 'animation.gif')
            frames[0].save(
                gif_destination,
                format='GIF',
                append_images=frames[1:],
                save_all=True,
                duration=900,
                loop=0
            )

            # remove frames
            path = os.path.join(parent(parent(parent(__file__))), 'filestorage', 'animations', 'frames')
            for file_name in os.listdir(path):
                # construct full file path
                file = os.path.join(path, file_name)
                if os.path.isfile(file):
                    os.remove(file)

            context['animation_gif'] = True

    return render(request, 'analysis_page/animation.html', context)


def clustering(request):
    """ Renders the Clustering tab. """

    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'times': Location.objects.values('time').distinct().order_by('time'),
        'variables': ['temp', 'rel_hum', 'spec_hum', 'tcc', 'u_wind', 'v_wind', 'gust', 'pwat']
    }

    if request.method == 'POST':
        context['selected_country'] = WorldBorder.objects.filter(id=request.POST.get('country')).values().last()
        context['selected_date'] = request.POST.get('date')
        context['selected_variables'] = request.POST.getlist('variable[]')

        context['n_clusters'] = int(request.POST.get('n_clusters'))
        context['floor'] = int(request.POST.get('floor'))
        if request.POST.get('islands') == 'yes':
            context['islands'] = "increase"
        elif request.POST.get('islands') == 'no':
            context['islands'] = "ignore"

        # create country border GeoDataFrame
        country = list(
            WorldBorder.objects.filter(
                id=request.POST.get('country')
            ).values('iso2', geometry=F('mpoly'))
        )
        country_gdf = gpd.GeoDataFrame(country, crs='EPSG:4326')
        wkt1 = country_gdf.geometry.apply(lambda x: x.wkt)
        country_gdf = gpd.GeoDataFrame(country_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs='EPSG:4326')

        # filter data by country and date
        datetime_obj = datetime.strptime((context['selected_date']), "%d-%m-%Y %H:%M")
        points = Location.objects.filter(
            time=datetime_obj,
            geometry__intersects=context['selected_country']['mpoly']
        ).values()

        # change queryset into GeoDataFrame
        data_df = pd.DataFrame(points)
        data_df.dropna(axis=0, inplace=True)
        wkt2 = data_df.geometry.apply(lambda x: x.wkt)
        data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs='EPSG:4326')

        # set parameters for model
        # attrs_name = context['selected_variables']
        w = libpysal.weights.Queen.from_dataframe(data_gdf)
        trace = False
        # n_clusters = 5
        # floor = 5
        # islands = "increase"

        spanning_forest_kwds = dict(
            dissimilarity=skm.manhattan_distances,
            affinity=None,
            reduction=np.sum,
            center=np.mean,
            verbose=2
        )

        # create SKATER model
        model = spopt.region.Skater(
            data_gdf,
            w,
            context['selected_variables'],
            n_clusters=context['n_clusters'],
            floor=context['floor'],
            trace=trace,
            islands=context['islands'],
            spanning_forest_kwds=spanning_forest_kwds
        )

        try:
            model.solve()

            # store labels (clusters) from the model
            data_gdf["model_regions"] = model.labels_

            # plot the border and data clusters
            fig = cluster_plot(
                country_gdf,
                data_gdf,
                datetime_obj,
                context['selected_variables'],
                context['selected_country']
            )

            # calculate statistics
            data_gdf["count"] = 1
            data_gdf[["model_regions", "count"]].groupby(by="model_regions").count()

            # return to context
            context['clustering_plot'] = fig

        except Exception as error:
            context['error'] = error
            if "Islands must be larger than the quorum" in str(error):
                context['info'] = "One possible solution is to reduce the minimum number of points in each cluster."

    return render(request, 'analysis_page/clustering.html', context)


def cluster_plot(country_gdf, data_gdf, datetime_obj, chosen_vars, chosen_country):
    """ Returns cluster plot. """

    # needed for plot
    plt.switch_backend('AGG')
    fig, ax = plt.subplots(figsize=(10, 7))

    country_gdf.plot(
        ax=ax,
        edgecolor="black",
        linewidth=0.5,
        color='white'
    )

    data_gdf.plot(
        ax=ax,
        column="model_regions",
        categorical=True,
        edgecolor="w",
        legend=True
    )

    # add details
    full_names_with_units = []
    for var in chosen_vars:
        var_data = long_name_and_unit(var)
        s = "".join([var_data['long_name'], ' [', var_data['unit'], ']'])
        full_names_with_units.append(s)

    vars_str = ", ".join(full_names_with_units)
    date_str = datetime.strftime(datetime_obj, "%d-%m-%Y %H:%M")
    plt.suptitle(
        f'Multi-Variable Clusters in {chosen_country["name"]} at {date_str}',
        fontsize=15
    )
    plt.title(
        f'Clustering Model Based on {vars_str}',
        pad=15,
        fontdict={'fontsize': 11}
    )
    ax.set_xlabel(u"Longitude [\N{DEGREE SIGN}]")
    ax.set_ylabel(u"Latitude [\N{DEGREE SIGN}]")

    plt.tight_layout()

    # convert the plot into memory buffer - needed for static plots
    fig = get_graph()

    return fig


def long_name_and_unit(var):
    """ Returns full name and unit of a meteorological variable. """

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
