from django.contrib.gis.db import models

# Create your models here.
class Map(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    time = models.DateField()
    step = models.DurationField()
    atmosphereSingleLayer = models.FloatField()
    valid_time = models.DateField()
    pwat = models.FloatField()