"""
GeoJSON <-> DB geometry conversion helpers, and server-side area calculation.

Per ARCHITECTURE.md, geometry is always transported as GeoJSON over the
wire and stored as PostGIS geometry (WKB) in the DB — never WKT on the
wire. This module is the single place those conversions happen so routers
don't duplicate shapely/geoalchemy2 plumbing.

Area calculation choice
------------------------
`Site.area_hectares` must be computed with a geodesic-aware method: naive
planar area of lon/lat coordinates (degrees) is meaningless as "hectares".
We use **pyproj's `Geod.geometry_area_perimeter`**, which computes the true
geodesic area of a polygon directly on the WGS84 ellipsoid (Karney's
algorithm) — no need to pick/reproject into a local equal-area or UTM CRS,
and it stays accurate for polygons of any size or location. This was
chosen over a raw-SQL `ST_Transform(..., <equal-area SRID>)` +
`ST_Area(geography)` round trip because it keeps the computation in the
same Python/shapely layer as the rest of this module, with no extra DB
round trip, while giving comparable (actually slightly more accurate,
ellipsoidal vs spherical) results to PostGIS's own `ST_Area(geography)`.
"""

from __future__ import annotations

from typing import Any, Mapping

from geoalchemy2.shape import to_shape
from pyproj import Geod
from shapely.geometry import mapping, shape
from shapely.geometry.polygon import Polygon

_GEOD = Geod(ellps="WGS84")


def geom_to_geojson(geom: Any) -> dict:
    """Convert a GeoAlchemy2 geometry column value (WKBElement) to a plain
    GeoJSON dict, e.g. `{"type": "Polygon", "coordinates": [...]}`.
    """
    shapely_geom = to_shape(geom)
    geojson = mapping(shapely_geom)
    # `mapping()` returns nested tuples; normalize to lists so the shape is
    # exactly what `json.dumps` / Pydantic would produce for a GeoJSON body.
    return _tuples_to_lists(geojson)


def geojson_to_polygon(geojson: Mapping) -> Polygon:
    """Parse an incoming GeoJSON Polygon mapping into a shapely Polygon,
    validating that it is in fact a Polygon (not some other geometry type).
    """
    geom = shape(dict(geojson))
    if not isinstance(geom, Polygon):
        raise ValueError(f"Expected a GeoJSON Polygon, got {geom.geom_type!r}")
    if not geom.is_valid:
        raise ValueError(
            "Polygon geometry is not valid (self-intersecting or degenerate)"
        )
    return geom


def polygon_area_hectares(polygon: Polygon) -> float:
    """Geodesic area of a lon/lat WGS84 polygon, in hectares. See module
    docstring for why `pyproj.Geod` is used instead of a planar/PostGIS
    calculation.
    """
    area_m2, _perimeter_m = _GEOD.geometry_area_perimeter(polygon)
    return round(abs(area_m2) / 10_000.0, 4)


def _tuples_to_lists(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _tuples_to_lists(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_tuples_to_lists(v) for v in value]
    return value
