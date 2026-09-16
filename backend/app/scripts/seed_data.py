"""
Seed the database with demo data for the Darukaa.Earth hackathon build.

No real satellite/remote-sensing data is available for the hackathon, so
this script generates plausible-looking synthetic data instead (documented
as a deliberate trade-off in the project README): a demo user, 2-3 demo
projects, 2-3 sites per project (small polygons scattered across real
Western Ghats, India landmarks), and 12 months of `site_metrics` per site
with gently increasing carbon sequestration, a seasonally-noisy
biodiversity index, and NDVI in the 0.3-0.8 range.

Usage (from inside `backend/`, with DATABASE_URL pointing at a migrated
Postgres/PostGIS instance):

    python -m app.scripts.seed_data
"""

import math
import random
from datetime import date, datetime, timezone

from geoalchemy2.shape import from_shape
from passlib.context import CryptContext
from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401
from app.db import base_all  # noqa: F401 (registers all models on Base.metadata)
from app.db.session import SessionLocal, engine
from app.models.project import Project
from app.models.site import Site
from app.models.site_metric import SiteMetric
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_USER_EMAIL = "demo@darukaa.earth"
DEMO_USER_PASSWORD = "DemoPassword123!"
DEMO_USER_FULL_NAME = "Darukaa Demo User"

METERS_PER_DEGREE_LAT = 111_320.0

# Real-ish Western Ghats, India landmarks used as site centers.
WESTERN_GHATS_LOCATIONS = [
    {"name": "Munnar Highlands", "lat": 10.0889, "lon": 77.0595},
    {"name": "Wayanad Forest Fringe", "lat": 11.6854, "lon": 76.1320},
    {"name": "Agasthyamalai Slopes", "lat": 8.6132, "lon": 77.2445},
    {"name": "Coorg Coffee Belt", "lat": 12.3375, "lon": 75.8069},
    {"name": "Nilgiri Shola Patch", "lat": 11.4064, "lon": 76.6932},
    {"name": "Silent Valley Buffer", "lat": 11.0833, "lon": 76.4333},
    {"name": "Periyar Reserve Edge", "lat": 9.4635, "lon": 77.2419},
    {"name": "Anamalai Ridge", "lat": 10.3500, "lon": 76.9333},
]

PROJECT_DEFS = [
    {
        "name": "Western Ghats Reforestation Initiative",
        "description": (
            "Community-led reforestation and carbon monitoring across degraded "
            "shola-grassland mosaics in the southern Western Ghats."
        ),
        "site_count": 3,
    },
    {
        "name": "Nilgiri Biodiversity Corridor",
        "description": (
            "Habitat connectivity and biodiversity monitoring project linking "
            "fragmented forest patches in the Nilgiri Biosphere Reserve."
        ),
        "site_count": 2,
    },
    {
        "name": "Agasthyamalai Carbon Project",
        "description": (
            "Long-term carbon stock monitoring in evergreen and semi-evergreen "
            "forest plots within the Agasthyamalai Biosphere Reserve."
        ),
        "site_count": 3,
    },
]

SITE_TYPES = ["carbon", "biodiversity"]


def make_site_polygon(
    center_lat: float,
    center_lon: float,
    avg_radius_m: float = 350.0,
    num_vertices: int = 6,
    irregularity: float = 0.35,
    rng: random.Random = random,
):
    """
    Build a small, simple (non-self-intersecting) polygon around a center
    point, and return (shapely Polygon in lon/lat, area_hectares).

    Vertices are placed at monotonically increasing angles around the
    center (one per angular sector) so the resulting ring never
    self-intersects, while per-vertex radius jitter keeps the shape
    "real-looking" rather than a perfect regular polygon.
    """
    lat_rad = math.radians(center_lat)
    meters_per_degree_lon = METERS_PER_DEGREE_LAT * math.cos(lat_rad)

    lonlat_points = []
    meter_points = []  # local (dx, dy) meters, used for an exact area calc
    for i in range(num_vertices):
        sector_start = 2 * math.pi * i / num_vertices
        sector_end = 2 * math.pi * (i + 1) / num_vertices
        angle = rng.uniform(sector_start, sector_end)
        radius = avg_radius_m * (1 + rng.uniform(-irregularity, irregularity))
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        meter_points.append((dx, dy))
        lon = center_lon + dx / meters_per_degree_lon
        lat = center_lat + dy / METERS_PER_DEGREE_LAT
        lonlat_points.append((lon, lat))

    # Close the ring.
    lonlat_points.append(lonlat_points[0])
    meter_points.append(meter_points[0])

    # Shoelace formula in local meter-space for an accurate area regardless
    # of lat/lon projection distortion.
    area_m2 = 0.0
    for (x1, y1), (x2, y2) in zip(meter_points[:-1], meter_points[1:]):
        area_m2 += x1 * y2 - x2 * y1
    area_m2 = abs(area_m2) / 2.0
    area_hectares = area_m2 / 10_000.0

    return Polygon(lonlat_points), round(area_hectares, 3)


def month_starts_back(n: int, from_date: date | None = None) -> list[date]:
    """Return `n` month-start dates, oldest first, ending at the current month.

    Implemented with plain calendar arithmetic (no python-dateutil dependency).
    """
    anchor = (from_date or datetime.now(timezone.utc).date()).replace(day=1)
    result = []
    for months_back in range(n - 1, -1, -1):
        total_months = anchor.year * 12 + (anchor.month - 1) - months_back
        year, month0 = divmod(total_months, 12)
        result.append(date(year, month0 + 1, 1))
    return result


def generate_metrics_for_site(site_type: str, rng: random.Random) -> list[dict]:
    """Generate 12 months of gently-trending, seasonally-noisy metrics."""
    months = month_starts_back(12)

    base_carbon = rng.uniform(80, 200)  # starting carbon stock (tons)
    monthly_carbon_gain = rng.uniform(1.5, 4.0)

    base_biodiversity = (
        rng.uniform(45, 65) if site_type == "carbon" else rng.uniform(55, 75)
    )
    base_ndvi = rng.uniform(0.45, 0.6)

    rows = []
    for i, month in enumerate(months):
        seasonal_phase = 2 * math.pi * (month.month - 1) / 12

        carbon_tons = base_carbon + monthly_carbon_gain * i + rng.uniform(-1.5, 1.5)

        biodiversity_index = (
            base_biodiversity + 8 * math.sin(seasonal_phase) + rng.uniform(-3, 3)
        )
        biodiversity_index = max(0.0, min(100.0, biodiversity_index))

        ndvi = (
            base_ndvi + 0.12 * math.sin(seasonal_phase + 0.5) + rng.uniform(-0.03, 0.03)
        )
        ndvi = max(0.3, min(0.8, ndvi))

        rows.append(
            {
                "date": month,
                "carbon_tons": round(carbon_tons, 2),
                "biodiversity_index": round(biodiversity_index, 2),
                "ndvi": round(ndvi, 3),
            }
        )
    return rows


def seed(db: Session) -> None:
    rng = random.Random(42)  # deterministic, "real-looking" demo data

    existing = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
    if existing:
        print(
            f"Demo user '{DEMO_USER_EMAIL}' already exists (id={existing.id}); "
            "skipping seed to avoid duplicates."
        )
        return

    demo_user = User(
        email=DEMO_USER_EMAIL,
        hashed_password=pwd_context.hash(DEMO_USER_PASSWORD),
        full_name=DEMO_USER_FULL_NAME,
    )
    db.add(demo_user)
    db.flush()  # assign demo_user.id

    locations = list(WESTERN_GHATS_LOCATIONS)
    rng.shuffle(locations)
    location_iter = iter(locations)

    total_sites = 0
    for project_def in PROJECT_DEFS:
        project = Project(
            name=project_def["name"],
            description=project_def["description"],
            owner_id=demo_user.id,
        )
        db.add(project)
        db.flush()  # assign project.id

        for site_index in range(project_def["site_count"]):
            location = next(location_iter)
            polygon, area_hectares = make_site_polygon(
                center_lat=location["lat"],
                center_lon=location["lon"],
                avg_radius_m=rng.uniform(250, 500),
                rng=rng,
            )
            site_type = SITE_TYPES[site_index % len(SITE_TYPES)]

            site = Site(
                project_id=project.id,
                name=f"{location['name']} Site",
                geom=from_shape(polygon, srid=4326),
                area_hectares=area_hectares,
                site_type=site_type,
            )
            db.add(site)
            db.flush()  # assign site.id

            for metric in generate_metrics_for_site(site_type, rng):
                db.add(SiteMetric(site_id=site.id, **metric))

            total_sites += 1

    db.commit()
    print(
        f"Seeded 1 demo user, {len(PROJECT_DEFS)} projects, {total_sites} sites, "
        f"and {total_sites * 12} site_metric rows."
    )
    print(f"Demo login: {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD}")


def main() -> None:
    # Convenience fallback so the script also works before Alembic has been
    # run manually. This only creates missing tables (checkfirst=True is the
    # default for `create_all`) and never drops/alters existing ones, so it
    # is safe to run alongside Alembic-managed schemas. Requires the
    # `postgis` extension to already exist (created by migration 0001).
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
