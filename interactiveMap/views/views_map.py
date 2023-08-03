import folium as folium
import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta
from matplotlib import cm
import plotly.express as px
from shapely.geometry import Polygon

from interactiveMap.models import Location, WorldBorder, CountryRegion
from django.db.models import Subquery, OuterRef
from django.db.models import Avg, Max, Min
from django.shortcuts import render


def map_page(request):
    """ Renders the Interactive Map page. """

    context = {
        'countries': WorldBorder.objects.all().order_by('name'),
        'times': Location.objects.values('time').distinct().order_by('time'),
    }

    if request.method != 'POST':
        m = folium.Map([0, 0], zoom_start=2)
    elif request.method == 'POST':
        # store user selection as session variables
        request.session['visual_type'] = request.POST.get('visual_type')
        request.session['chosen_country'] = request.POST.get('country')
        request.session['date'] = request.POST.get('date')
        request.session['meteo_var'] = request.POST.get('meteo_var')

        context['selected_country'] = WorldBorder.objects.filter(id=request.session['country']).values().last()

        country_geometry = WorldBorder.objects.filter(name=context['selected_country']['name']).values().last()['mpoly']
        datetime_obj = datetime.strptime((request.session['date']), "%d-%m-%Y %H:%M")
        points = Location.objects.filter(time=datetime_obj, geometry__intersects=country_geometry).values()

        context['count'] = points.count()

        selected_var = request.session['meteo_var']
        var_data = long_name_and_unit(selected_var)

        # prepare queryset for timeseries plot
        queryset = Location.objects.filter(geometry__intersects=country_geometry).values('time').annotate(
            meteo_var=Avg(selected_var)).order_by()

        meteo_var = queryset.values_list('meteo_var', flat=True)
        time = queryset.values_list('time', flat=True)
        timezone_corrected_l = [datetime.strptime(
            datetime.strftime(TIME + timedelta(hours=2), "%d-%m-%Y %H:%M"),
            "%d-%m-%Y %H:%M"
        ) for TIME in time]

        fig = create_timeseries(
            timezone_corrected_l,
            meteo_var,
            var_data,
            context,
            selected_var,
            country_geometry,
            queryset,
            datetime_obj
        )
        fig = fig._repr_html_()
        context['plot_div'] = fig

        # initialize blank folium map
        m = folium.Map([context['selected_country']['lat'], context['selected_country']['lon']], zoom_start=6)

        folium.raster_layers.TileLayer(
            'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}.png?api_key=e379e366-57a6-4682-ad6f-2f1a779548b2',
            name='Stadia.AlidadeSmoothDark',
            attr='Stadia.AlidadeSmoothDark'
        ).add_to(m)
        folium.raster_layers.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name='Esri.WorldImagery',
            attr='Esri.WorldImagery'
        ).add_to(m)

        if request.session['visual_type'] == 'points':
            render_polygons(
                m=m,
                points=points,
                selected_country=context['selected_country'],
                selected_var=selected_var
            )
        elif request.session['visual_type'] == 'choropleth':
            render_choropleth(
                m=m,
                datetime_obj=datetime_obj,
                selected_country=context['selected_country'],
                selected_var=selected_var
            )

        folium.LayerControl().add_to(m)

    m = m._repr_html_()
    context['map'] = m
    return render(request, 'stations/index.html', context)


def create_timeseries(timezone_corrected_l, meteo_var, var_data, context, selected_var, country_geometry, queryset, datetime_obj):
    """ Creates a time series graph for the Interactive Map page. """

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

    return fig


def long_name_and_unit(var):
    """ Returns the full name and unit of the meteorological variable. """

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


# def cardinal_points(self, lat, lon):
#     card_point_lat = card_point_lon = ''
#
#     if lat > 0 and lat <= 90:
#         card_point_lat = 'N'
#     elif lat < 0 and lat >= -90:
#         card_point_lat = 'S'
#
#     if lon < 0 and lon > -180:
#         card_point_lon = 'W'
#     elif lon > 0 and lon < 180:
#         card_point_lon = 'E'
#
#     return {'lat': card_point_lat, 'lon': card_point_lon}


# def kelvin_to_celsius(self, kelvin):
#     return kelvin - 273.15

def normalize(value, min_value, max_value):
    """ Converts a value to a decimal number between 0 and 1. """
    return (value - min_value) / (max_value - min_value)


def rgba_to_hex(rgba_tuple):
    """ Converts an RGB float tuple into a color hex string. """
    r, g, b, a = rgba_tuple
    return "#{:02x}{:02x}{:02x}{:02x}".format(int(255 * r), int(255 * g), int(255 * b), int(255 * a))


def render_polygons(m, points, selected_country, selected_var):
    """ Creates and adds to the map a geojson layer created from custom polygons. """
    var_data = long_name_and_unit(selected_var)

    # save data to GeoDataFrame
    points_adjusted = list(points.values('geometry', selected_var, 'latitude', 'longitude'))
    data_df = pd.DataFrame(points_adjusted)
    data_df.dropna(axis=0, inplace=True)
    wkt2 = data_df.geometry.apply(lambda x: x.wkt)
    data_gdf = gpd.GeoDataFrame(data_df, geometry=gpd.GeoSeries.from_wkt(wkt2), crs='EPSG:4326')

    # create polygons from original points, save them to GeoDataFrame
    step = 0.125
    all_points = data_gdf.geometry.tolist()
    all_poly = [Polygon([[first.x - step, first.y + step],
                         [first.x + step, first.y + step],
                         [first.x + step, first.y - step],
                         [first.x - step, first.y - step],
                         [first.x - step, first.y + step]]) for first in all_points]

    poly_gdf = gpd.GeoDataFrame({'geometry': all_poly}, crs="EPSG:4326")
    poly_gdf['variable'] = data_gdf[selected_var]
    poly_gdf['latitude'] = data_gdf['latitude']
    poly_gdf['longitude'] = data_gdf['longitude']

    # create GeoJson from polygons GeoDataFrame
    geojson = poly_gdf.to_json()

    # save min and max values to variables - needed for normalization
    min_var = Location.objects.filter(
        geometry__intersects=selected_country['mpoly']
    ).aggregate(min=Min(selected_var))['min']
    max_var = Location.objects.filter(
        geometry__intersects=selected_country['mpoly']
    ).aggregate(max=Max(selected_var))['max']

    viridis = cm.get_cmap('viridis')

    # add geojson layer to map
    folium.features.GeoJson(
        geojson,
        name='geojson',
        style_function=lambda feature: {
            'fillColor': rgba_to_hex(
                rgba_tuple=viridis(
                    normalize(feature['properties']['variable'], min_var, max_var)
                )
            ),
            'fillOpacity': 0.7,
            'color': 'black',
            'opacity': 1,
            'weight': 1,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                'variable',
                'latitude',
                'longitude'
            ],
            aliases=[
                f"{var_data['long_name']} [{var_data['unit']}]: ",
                "Latitude:",
                "Longitude: "
            ],
            localize=True,
            sticky=False,
            labels=True,
            style="""
               background-color: #F0EFEF;
               border: 2px solid black;
               border-radius: 3px;
               box-shadow: 3px;
                """,
        ),
        ).add_to(m)


def render_choropleth(m, datetime_obj, selected_country, selected_var):
    """ Creates and adds to the map a Choropleth Map with a tooltip layer. """

    queryset = Location.objects.filter(time=datetime_obj, geometry__intersects=selected_country['mpoly']).annotate(
        region=Subquery(
            CountryRegion.objects.filter(geometry__contains=OuterRef('geometry')).values('name')
        )
    ).values('region', selected_var)

    queryset = queryset.values('region').annotate(avg=Avg(selected_var))

    region_names = queryset.values_list('region', flat=True)

    qs = CountryRegion.objects.filter(country_iso3=selected_country['iso3'],
                                      name__in=region_names)\
        .order_by('name').values('geometry')

    world_gdf = gpd.GeoDataFrame(list(qs), crs='EPSG:4326')
    wkt1 = world_gdf.geometry.apply(lambda x: x.wkt)
    world_gdf = gpd.GeoDataFrame(world_gdf, geometry=gpd.GeoSeries.from_wkt(wkt1), crs='EPSG:4326')

    data_df = pd.DataFrame(list(queryset))
    data_df.dropna(axis=0, inplace=True)

    world_gdf['region'] = data_df['region']
    world_gdf['avg'] = data_df['avg']

    geojson = world_gdf.to_json()

    create_choropleth(
        m=m,
        variable=selected_var,
        datetime_obj=datetime_obj,
        geo_data=geojson,
        data=world_gdf
    )

    var_data = long_name_and_unit(selected_var)
    folium.features.GeoJson(
        geojson,
        name='Tooltips',
        style_function=lambda x: {'color': 'black', 'fillColor': 'transparent', 'weight': 0.5},
        tooltip=folium.GeoJsonTooltip(
            fields=[
                'region',
                'avg'
            ],
            aliases=[
                "Region name: ",
                f"{var_data['long_name']} [{var_data['unit']}]: "
            ],
            localize=True,
            sticky=False,
            labels=True,
            style="""
       background-color: #F0EFEF;
       border: 2px solid black;
       border-radius: 3px;
       box-shadow: 3px;
        """,
        ),
    ).add_to(m)


def create_choropleth(m, variable, datetime_obj, geo_data, data):
    """ Creates a Choropleth Map. """

    var_data = long_name_and_unit(variable)

    folium.Choropleth(
        name="Choropleth",
        geo_data=geo_data,
        data=data,
        columns=["region", "avg"],
        key_on="feature.properties.region",
        fill_color='YlOrRd',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name=f"Average {var_data['long_name']} [{var_data['unit']}] on {datetime_obj}"
    ).add_to(m)
