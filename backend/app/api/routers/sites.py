from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.geo import geom_to_geojson
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.site import Site
from app.models.site_metric import SiteMetric
from app.models.user import User
from app.schemas.site import AnalyticsSummary, SiteMetricOut, SiteOut

router = APIRouter(prefix="/sites", tags=["sites"])


def _get_owned_site(site_id: int, db: Session, current_user: User) -> Site:
    """A site is only visible if it belongs to a project owned by the
    current user, per ARCHITECTURE.md's auth scoping rule.
    """
    site = (
        db.query(Site)
        .join(Project, Site.project_id == Project.id)
        .filter(Site.id == site_id, Project.owner_id == current_user.id)
        .first()
    )
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )
    return site


@router.get("/{site_id}", response_model=SiteOut)
def get_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SiteOut:
    site = _get_owned_site(site_id, db, current_user)
    return SiteOut(
        id=site.id,
        project_id=site.project_id,
        name=site.name,
        site_type=site.site_type,
        geom=geom_to_geojson(site.geom),
        area_hectares=site.area_hectares,
        created_at=site.created_at,
    )


@router.get("/{site_id}/metrics", response_model=list[SiteMetricOut])
def get_site_metrics(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SiteMetricOut]:
    _get_owned_site(site_id, db, current_user)  # ownership check (raises 404)
    metrics = (
        db.query(SiteMetric)
        .filter(SiteMetric.site_id == site_id)
        .order_by(SiteMetric.date.asc())
        .all()
    )
    return [SiteMetricOut.model_validate(m) for m in metrics]


def _direction(
    first_avg: float, second_avg: float, threshold_ratio: float = 0.02
) -> int:
    """+1 if second half is meaningfully higher than first half, -1 if
    meaningfully lower, 0 if roughly flat. `threshold_ratio` guards against
    noise being read as a trend (2% of the first-half average, with a small
    absolute floor for near-zero baselines).
    """
    baseline = max(abs(first_avg), 1e-6)
    threshold = max(threshold_ratio * baseline, 1e-6)
    delta = second_avg - first_avg
    if delta > threshold:
        return 1
    if delta < -threshold:
        return -1
    return 0


@router.get("/{site_id}/analytics/summary", response_model=AnalyticsSummary)
def get_site_analytics_summary(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsSummary:
    _get_owned_site(site_id, db, current_user)  # ownership check (raises 404)
    metrics = (
        db.query(SiteMetric)
        .filter(SiteMetric.site_id == site_id)
        .order_by(SiteMetric.date.asc())
        .all()
    )

    if not metrics:
        return AnalyticsSummary(
            total_carbon_tons=0.0,
            avg_biodiversity_index=0.0,
            avg_ndvi=0.0,
            trend="stable",
        )

    n = len(metrics)
    avg_biodiversity_index = sum(m.biodiversity_index for m in metrics) / n
    avg_ndvi = sum(m.ndvi for m in metrics) / n

    # `carbon_tons` in the seed/synthetic data is a running carbon-stock
    # figure per month (gently increasing over time), not a per-month
    # increment. Summing 12 already-cumulative snapshots would wildly
    # overstate the site's stock, so "total_carbon_tons" is the most recent
    # (latest-dated) reading — i.e. the site's current total carbon stock.
    total_carbon_tons = metrics[-1].carbon_tons

    # Trend: split the series into first-half / second-half and compare
    # averages per metric (carbon_tons, biodiversity_index, ndvi). Each
    # metric votes improving(+1)/declining(-1)/stable(0); the overall trend
    # is whichever direction has the most votes, "stable" on a tie.
    mid = n // 2
    if mid == 0:
        trend = "stable"
    else:
        first_half = metrics[:mid]
        second_half = metrics[mid:]

        votes = 0
        for attr in ("carbon_tons", "biodiversity_index", "ndvi"):
            first_avg = sum(getattr(m, attr) for m in first_half) / len(first_half)
            second_avg = sum(getattr(m, attr) for m in second_half) / len(second_half)
            votes += _direction(first_avg, second_avg)

        if votes > 0:
            trend = "improving"
        elif votes < 0:
            trend = "declining"
        else:
            trend = "stable"

    return AnalyticsSummary(
        total_carbon_tons=round(total_carbon_tons, 2),
        avg_biodiversity_index=round(avg_biodiversity_index, 2),
        avg_ndvi=round(avg_ndvi, 3),
        trend=trend,
    )
