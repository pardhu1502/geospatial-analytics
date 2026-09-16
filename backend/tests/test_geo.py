"""
Unit tests for app/core/geo.py's GeoJSON <-> shapely conversions and the
geodesic area calculation. These need no database at all: `from_shape`/
`to_shape` work purely on WKB bytes in memory.
"""

import pytest
from shapely.geometry import Polygon

from app.core.geo import geojson_to_polygon, geom_to_geojson, polygon_area_hectares


SQUARE_DEGREE_NEAR_EQUATOR = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [0.0, 0.01], [0.01, 0.01], [0.01, 0.0], [0.0, 0.0]]],
}


def test_geojson_to_polygon_parses_valid_polygon():
    polygon = geojson_to_polygon(SQUARE_DEGREE_NEAR_EQUATOR)
    assert isinstance(polygon, Polygon)
    assert polygon.is_valid
    assert len(list(polygon.exterior.coords)) == 5


def test_geojson_to_polygon_rejects_non_polygon():
    point_geojson = {"type": "Point", "coordinates": [0.0, 0.0]}
    with pytest.raises(ValueError):
        geojson_to_polygon(point_geojson)


def test_polygon_area_hectares_matches_expected_order_of_magnitude():
    # ~0.01deg x 0.01deg near the equator is roughly 1.11km x 1.11km,
    # i.e. roughly 123 hectares. We assert a loose range rather than an
    # exact figure since the geodesic calc differs slightly from a flat
    # equirectangular approximation.
    polygon = geojson_to_polygon(SQUARE_DEGREE_NEAR_EQUATOR)
    area_ha = polygon_area_hectares(polygon)
    assert 100 < area_ha < 150


def test_polygon_area_hectares_is_always_positive_regardless_of_winding():
    coords = SQUARE_DEGREE_NEAR_EQUATOR["coordinates"][0]
    reversed_geojson = {"type": "Polygon", "coordinates": [list(reversed(coords))]}
    forward_area = polygon_area_hectares(geojson_to_polygon(SQUARE_DEGREE_NEAR_EQUATOR))
    reverse_area = polygon_area_hectares(geojson_to_polygon(reversed_geojson))
    assert forward_area == pytest.approx(reverse_area)


def test_geom_to_geojson_round_trips_with_geojson_to_polygon():
    from geoalchemy2.shape import from_shape

    original_polygon = geojson_to_polygon(SQUARE_DEGREE_NEAR_EQUATOR)
    wkb_element = from_shape(original_polygon, srid=4326)

    geojson = geom_to_geojson(wkb_element)
    assert geojson["type"] == "Polygon"
    assert isinstance(geojson["coordinates"], list)
    assert isinstance(geojson["coordinates"][0], list)
    assert isinstance(geojson["coordinates"][0][0], list)  # tuples normalized to lists

    round_tripped_polygon = geojson_to_polygon(geojson)
    assert original_polygon.equals(round_tripped_polygon)
