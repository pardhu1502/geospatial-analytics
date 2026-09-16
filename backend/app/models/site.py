from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.site_metric import SiteMetric


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Stored as WKB in Postgres via PostGIS; always serialized to/from GeoJSON
    # at the API boundary (never WKT), per ARCHITECTURE.md.
    geom: Mapped[str] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326), nullable=False
    )

    # Computed on save (from `geom`, projected to an equal-area CRS) by the
    # Backend-API layer when a site is created/updated.
    area_hectares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    site_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="sites")
    metrics: Mapped[List["SiteMetric"]] = relationship(
        "SiteMetric", back_populates="site", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Site id={self.id} name={self.name!r} type={self.site_type!r}>"
