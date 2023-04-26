from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from .models import Map

# Register your models here.
@admin.register(Map)
class MapAdmin(OSMGeoAdmin):
    list_display = ('id', 'latitude', 'longitude', 'time', 'pwat')
