from datetime import date as date_, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.site import Site


class SiteMetric(Base):
    __tablename__ = "site_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(
        ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_] = mapped_column(Date, nullable=False, index=True)

    carbon_tons: Mapped[float] = mapped_column(Float, nullable=False)
    biodiversity_index: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    ndvi: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    site: Mapped["Site"] = relationship("Site", back_populates="metrics")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SiteMetric site_id={self.site_id} date={self.date}>"
