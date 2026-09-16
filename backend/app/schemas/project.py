from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.site import SiteNested


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    """Partial update for `PATCH /projects/{project_id}`.

    Both fields are optional so a caller can rename a project without
    touching its description (and vice versa). `description` is
    explicitly nullable so it can be cleared.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectBulkDelete(BaseModel):
    """Request body for `POST /projects/bulk-delete`."""

    ids: List[int] = Field(min_length=1)


class BulkDeleteResult(BaseModel):
    """How many of the requested projects were actually deleted.

    Projects that don't exist or aren't owned by the caller are silently
    skipped rather than erroring, so a partially-stale selection in the UI
    still deletes what it legitimately can.
    """

    deleted: int
    requested: int


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
