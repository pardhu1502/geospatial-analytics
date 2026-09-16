from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.geo import GeoJSONPolygon


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    site_type: str = Field(
        min_length=1, max_length=50, examples=["carbon", "biodiversity"]
    )
    geom: GeoJSONPolygon


class SiteNested(BaseModel):
    """Site shape nested inside `GET /projects/{project_id}` responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    site_type: str
    geom: GeoJSONPolygon
    area_hectares: Optional[float] = None


class SiteOut(SiteNested):
    """Full site detail returned by `GET /sites/{site_id}` and
    `POST /projects/{project_id}/sites`.
    """

    project_id: int
    created_at: datetime


class SiteMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    carbon_tons: float
    biodiversity_index: float
    ndvi: float


class AnalyticsSummary(BaseModel):
    total_carbon_tons: float
    avg_biodiversity_index: float
    avg_ndvi: float
    trend: str
