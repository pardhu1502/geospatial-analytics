"""
Full-stack integration tests against a REAL Postgres/PostGIS database.

Why this needs a real DB (and can't use SQLite/mocks like the other test
files here): `Site.geom` is a GeoAlchemy2 `Geometry("POLYGON", srid=4326)`
column. GeoAlchemy2 only knows how to manage that column type against
PostGIS (or SpatiaLite, which isn't wired up here) — `Base.metadata.create_all()`
against a plain SQLite engine fails outright with
`OperationalError: no such function: RecoverGeometryColumn`, confirmed
while building this test suite. So the create-project -> create-site ->
get-project-with-nested-GeoJSON flow can only be exercised against the
real thing.

How to run these for real:

    docker compose up -d db        # from the repo root
    cd backend
    alembic upgrade head
    pytest tests/test_integration_db.py -v

If neither `DATABASE_URL` nor a reachable Postgres/PostGIS instance is
found, every test in this module is SKIPPED (not failed) with a message
explaining why — see `_db_is_reachable()` below.
"""

import uuid

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db import base_all  # noqa: F401  (registers all models on Base.metadata)
from app.db.session import get_db
from app.main import app


def _db_is_reachable() -> bool:
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
            # Also confirm PostGIS is actually enabled, not just Postgres.
            conn.execute(sqlalchemy.text("SELECT postgis_version()"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_is_reachable(),
    reason=(
        "No reachable Postgres/PostGIS at settings.DATABASE_URL "
        f"({settings.DATABASE_URL!r}). Run `docker compose up -d db` from the "
        "repo root (and `alembic upgrade head`) to enable these tests."
    ),
)


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(settings.DATABASE_URL, future=True)
    Base.metadata.create_all(bind=engine)  # no-op for tables Alembic already made
    yield engine
    engine.dispose()


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _unique_email() -> str:
    return f"integration-{uuid.uuid4().hex[:10]}@darukaa.earth"


def _auth_headers(client: TestClient) -> dict:
    email = _unique_email()
    resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "IntegrationTest123!",
            "full_name": "Integration Tester",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


SAMPLE_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [76.65, 10.00],
            [76.65, 10.01],
            [76.66, 10.01],
            [76.66, 10.00],
            [76.65, 10.00],
        ]
    ],
}


def test_create_project_create_site_and_get_project_with_geojson(client: TestClient):
    headers = _auth_headers(client)

    project_resp = client.post(
        "/projects",
        json={
            "name": "Test Reforestation Plot",
            "description": "Integration test project",
        },
        headers=headers,
    )
    assert project_resp.status_code == 201, project_resp.text
    project = project_resp.json()
    assert project["site_count"] == 0

    site_resp = client.post(
        f"/projects/{project['id']}/sites",
        json={"name": "Plot A", "site_type": "carbon", "geom": SAMPLE_POLYGON_GEOJSON},
        headers=headers,
    )
    assert site_resp.status_code == 201, site_resp.text
    site = site_resp.json()
    assert site["geom"]["type"] == "Polygon"
    assert site["area_hectares"] > 0

    detail_resp = client.get(f"/projects/{project['id']}", headers=headers)
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["site_count"] == 1
    assert len(detail["sites"]) == 1
    nested_site = detail["sites"][0]
    assert nested_site["id"] == site["id"]
    assert nested_site["geom"]["type"] == "Polygon"
    assert nested_site["geom"]["coordinates"]

    # Site detail + metrics + analytics summary endpoints, scoped correctly.
    site_detail_resp = client.get(f"/sites/{site['id']}", headers=headers)
    assert site_detail_resp.status_code == 200

    metrics_resp = client.get(f"/sites/{site['id']}/metrics", headers=headers)
    assert metrics_resp.status_code == 200
    assert metrics_resp.json() == []  # no metrics seeded for a freshly created site

    summary_resp = client.get(f"/sites/{site['id']}/analytics/summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["trend"] == "stable"


def test_project_and_site_are_not_visible_to_other_users(client: TestClient):
    owner_headers = _auth_headers(client)
    other_headers = _auth_headers(client)

    project_resp = client.post(
        "/projects", json={"name": "Private Project"}, headers=owner_headers
    )
    project_id = project_resp.json()["id"]

    site_resp = client.post(
        f"/projects/{project_id}/sites",
        json={
            "name": "Private Site",
            "site_type": "biodiversity",
            "geom": SAMPLE_POLYGON_GEOJSON,
        },
        headers=owner_headers,
    )
    site_id = site_resp.json()["id"]

    # Another authenticated user gets 404s, not the owner's data.
    assert (
        client.get(f"/projects/{project_id}", headers=other_headers).status_code == 404
    )
    assert (
        client.post(
            f"/projects/{project_id}/sites",
            json={
                "name": "Sneaky Site",
                "site_type": "carbon",
                "geom": SAMPLE_POLYGON_GEOJSON,
            },
            headers=other_headers,
        ).status_code
        == 404
    )
    assert client.get(f"/sites/{site_id}", headers=other_headers).status_code == 404
    assert (
        client.get(f"/sites/{site_id}/metrics", headers=other_headers).status_code
        == 404
    )

    # And a fully unauthenticated caller gets 401, not 404 or 200.
    assert client.get(f"/projects/{project_id}").status_code == 401
    assert client.get(f"/sites/{site_id}").status_code == 401


def test_update_project_patches_only_supplied_fields(client: TestClient):
    headers = _auth_headers(client)
    created = client.post(
        "/projects",
        json={"name": "Original name", "description": "Original description"},
        headers=headers,
    ).json()

    # Renaming must not wipe the description that wasn't part of the payload.
    resp = client.patch(
        f"/projects/{created['id']}", json={"name": "New name"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "New name"
    assert body["description"] == "Original description"

    # Explicit null clears it, which `exclude_unset` must still allow through.
    resp = client.patch(
        f"/projects/{created['id']}", json={"description": None}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["description"] is None
    assert resp.json()["name"] == "New name"


def test_delete_project_cascades_to_sites(client: TestClient):
    headers = _auth_headers(client)
    project = client.post(
        "/projects", json={"name": "To delete"}, headers=headers
    ).json()
    site = client.post(
        f"/projects/{project['id']}/sites",
        json={
            "name": "Doomed site",
            "site_type": "carbon",
            "geom": SAMPLE_POLYGON_GEOJSON,
        },
        headers=headers,
    ).json()

    resp = client.delete(f"/projects/{project['id']}", headers=headers)
    assert resp.status_code == 204, resp.text

    # Project and its cascaded site are both unreachable afterwards.
    assert client.get(f"/projects/{project['id']}", headers=headers).status_code == 404
    assert client.get(f"/sites/{site['id']}", headers=headers).status_code == 404


def test_cannot_update_or_delete_another_users_project(client: TestClient):
    owner_headers = _auth_headers(client)
    project = client.post(
        "/projects", json={"name": "Private project"}, headers=owner_headers
    ).json()

    intruder_headers = _auth_headers(client)
    assert (
        client.patch(
            f"/projects/{project['id']}",
            json={"name": "hacked"},
            headers=intruder_headers,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/projects/{project['id']}", headers=intruder_headers
        ).status_code
        == 404
    )

    # Still intact and unchanged for its real owner.
    resp = client.get(f"/projects/{project['id']}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Private project"


def test_bulk_delete_only_removes_own_projects(client: TestClient):
    owner_headers = _auth_headers(client)
    keep = client.post("/projects", json={"name": "Keep"}, headers=owner_headers).json()
    drop_a = client.post(
        "/projects", json={"name": "Drop A"}, headers=owner_headers
    ).json()
    drop_b = client.post(
        "/projects", json={"name": "Drop B"}, headers=owner_headers
    ).json()

    other_headers = _auth_headers(client)
    foreign = client.post(
        "/projects", json={"name": "Someone else's"}, headers=other_headers
    ).json()

    # Mix in a foreign id and a nonexistent one: both are skipped, not fatal.
    resp = client.post(
        "/projects/bulk-delete",
        json={"ids": [drop_a["id"], drop_b["id"], foreign["id"], 99_999_999]},
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": 2, "requested": 4}

    assert (
        client.get(f"/projects/{drop_a['id']}", headers=owner_headers).status_code
        == 404
    )
    assert (
        client.get(f"/projects/{drop_b['id']}", headers=owner_headers).status_code
        == 404
    )
    assert (
        client.get(f"/projects/{keep['id']}", headers=owner_headers).status_code == 200
    )
    # The other user's project survived someone else's bulk delete.
    assert (
        client.get(f"/projects/{foreign['id']}", headers=other_headers).status_code
        == 200
    )


def test_bulk_delete_rejects_empty_id_list(client: TestClient):
    headers = _auth_headers(client)
    resp = client.post("/projects/bulk-delete", json={"ids": []}, headers=headers)
    assert resp.status_code == 422
