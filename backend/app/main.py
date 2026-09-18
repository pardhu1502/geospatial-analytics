"""
FastAPI application entrypoint for Darukaa.Earth's backend.

Table creation is intentionally NOT performed here (no
`Base.metadata.create_all()` on startup): Alembic (backend/alembic) is the
single source of truth for schema, per ARCHITECTURE.md. Run
`alembic upgrade head` before starting the app against a fresh database.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.routers import auth, projects, sites
from app.core.config import settings

app = FastAPI(
    title="Darukaa.Earth API",
    description=(
        "Geospatial data analytics platform for forest carbon and "
        "biodiversity monitoring projects."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(sites.router)


# HEAD is included because Render probes the service root with HEAD.
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
