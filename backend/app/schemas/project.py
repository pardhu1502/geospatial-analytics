from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.site import SiteNested


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectOut(BaseModel):
    """List/create response shape: project + nested site count."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    site_count: int = 0


class ProjectDetail(ProjectOut):
    """`GET /projects/{project_id}` response: project + full nested sites
    (with GeoJSON geometry), per ARCHITECTURE.md.
    """

    sites: List[SiteNested] = []
