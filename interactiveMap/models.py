from django.contrib.gis.db import models


# Create your models here.
class WorldBorder(models.Model):
    # Regular Django fields corresponding to the attributes in the
    # world borders shapefile.
    name = models.CharField(max_length=50)
    area = models.IntegerField()
    pop2005 = models.IntegerField("Population 2005")
    fips = models.CharField("FIPS Code", max_length=2, null=True)
    iso2 = models.CharField("2 Digit ISO", max_length=2)
    iso3 = models.CharField("3 Digit ISO", max_length=3)
    un = models.IntegerField("United Nations Code")
    region = models.IntegerField("Region Code")
    subregion = models.IntegerField("Sub-Region Code")
    lon = models.FloatField()
    lat = models.FloatField()

    # GeoDjango-specific: a geometry field (MultiPolygonField)
    mpoly = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):
        return self.name


class Location(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    time = models.DateTimeField()
    step = models.DurationField()
    atmosphereSingleLayer = models.FloatField()
    valid_time = models.DateTimeField()
    # Meteorological variables
    temp = models.FloatField()
    rel_hum = models.FloatField()
    tcc = models.FloatField()
    spec_hum = models.FloatField()
    u_wind = models.FloatField()
    v_wind = models.FloatField()
    gust = models.FloatField()
    pwat = models.FloatField()
    #
    geometry = models.PointField()


class CountryRegion(models.Model):
    # Regular Django fields corresponding to the attributes in the
    # regions GeoJson file.
    country_iso3 = models.CharField("3 Digit ISO", max_length=3)
    country_name = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50)

    # GeoDjango-specific: a geometry field (MultiPolygonField)
    geometry = models.MultiPolygonField()

    # Returns the string representation of the model.
    def __str__(self):
        return self.name


class RelevantCountry(models.Model):
    iso3 = models.CharField("3 Digit ISO", max_length=3)
    # conveys the information if all regions of the country intersect points
    all_regions = models.BooleanField()
