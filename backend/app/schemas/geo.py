from typing import List, Literal

from pydantic import BaseModel


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry, e.g.:

        {"type": "Polygon", "coordinates": [[[lon, lat], [lon, lat], ...]]}

    `coordinates` is a list of linear rings (first = exterior, rest =
    holes); each ring is a list of [lon, lat] pairs.
    """

    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[List[float]]]
