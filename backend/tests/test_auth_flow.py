"""
Real end-to-end test of the auth flow (register -> login -> me) through the
actual FastAPI app, routers, Pydantic schemas, and app/core/security.py —
with `get_db` overridden to a tiny in-memory fake session (see
`tests/fake_db.py`) instead of a real Postgres connection.

This runs anywhere (no Docker/Postgres needed) and is not a placeholder:
it hits real HTTP routes via `TestClient` and asserts on real JWTs and
real bcrypt-hashed passwords.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from tests.fake_db import FakeSession


@pytest.fixture()
def client():
    fake_session = FakeSession()

    def override_get_db():
        yield fake_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_register_login_me_flow(client: TestClient):
    register_resp = client.post(
        "/auth/register",
        json={
            "email": "forest.ranger@darukaa.earth",
            "password": "SuperSecret123!",
            "full_name": "Forest Ranger",
        },
    )
    assert register_resp.status_code == 201, register_resp.text
    register_body = register_resp.json()
    assert register_body["token_type"] == "bearer"
    assert register_body["access_token"]

    # Duplicate registration should be rejected.
    dup_resp = client.post(
        "/auth/register",
        json={
            "email": "forest.ranger@darukaa.earth",
            "password": "AnotherPass123!",
            "full_name": "Someone Else",
        },
    )
    assert dup_resp.status_code == 400

    login_resp = client.post(
        "/auth/login",
        json={"email": "forest.ranger@darukaa.earth", "password": "SuperSecret123!"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    # Wrong password -> 401.
    bad_login_resp = client.post(
        "/auth/login",
        json={"email": "forest.ranger@darukaa.earth", "password": "wrong-password"},
    )
    assert bad_login_resp.status_code == 401

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, me_resp.text
    me_body = me_resp.json()
    assert me_body["email"] == "forest.ranger@darukaa.earth"
    assert me_body["full_name"] == "Forest Ranger"
    assert "hashed_password" not in me_body  # never leak the hash


def test_me_without_token_is_401(client: TestClient):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_with_garbage_token_is_401(client: TestClient):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert resp.status_code == 401


def test_protected_project_routes_require_auth_without_db():
    """`GET /projects` with no Authorization header must 401 before ever
    touching the database — verified here with the *real* `get_db` (no
    override), proving the 401 short-circuit in `get_current_user` never
    needs a live DB connection.
    """
    with TestClient(app) as unauthenticated_client:
        resp = unauthenticated_client.get("/projects")
        assert resp.status_code == 401
