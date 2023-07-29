from pathlib import Path
from django.contrib.gis.utils import LayerMapping
from .models import CountryRegion

regions_mapping = {
    "country_iso3": "GID_0",
    "country_name": "COUNTRY",
    "name": "NAME_1",
    "type": "ENGTYPE_1",
    "geometry": "geometry",
}

regions_shp = Path(__file__).resolve().parent / "data" / "regions" / "regions_merged.shp"


def run(verbose=True):
    lm = LayerMapping(CountryRegion, regions_shp, regions_mapping, transform=False)
    lm.save(strict=True, verbose=verbose)