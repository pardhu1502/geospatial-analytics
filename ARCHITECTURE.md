# Darukaa.Earth — Architecture Contract

This is the shared contract every part of the codebase must follow. It exists so the
frontend, backend, database, and CI/CD pieces integrate correctly even though they are
built somewhat independently. **Do not deviate from names/paths/ports defined here**
without updating this file.

## Monorepo layout

```
Darukaa hackathon/
├── frontend/           # React (Vite) app
├── backend/            # FastAPI app
│   ├── app/
│   │   ├── api/routers/    # FastAPI routers (auth.py, projects.py, sites.py)
│   │   ├── core/           # config.py, security.py (JWT/password hashing)
│   │   ├── db/             # session.py, base.py
│   │   ├── models/         # SQLAlchemy + GeoAlchemy2 models
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── scripts/        # seed_data.py
│   │   └── main.py
│   ├── alembic/            # migrations
│   └── tests/
├── .github/workflows/
├── docker-compose.yml
└── README.md
```

## Tech stack (locked decisions)

- Backend: **FastAPI** (Python 3.11+), SQLAlchemy 2.x + **GeoAlchemy2** for PostGIS,
  Alembic for migrations, **python-jose** for JWT, **passlib[bcrypt]** for password hashing.
- Database: **PostgreSQL 15 + PostGIS 3**, run locally via `docker-compose.yml`.
- Frontend: **React 18 + Vite**, `react-router-dom`, `mapbox-gl` + `@mapbox/mapbox-gl-draw`
  for drawing site polygons, **Highcharts** (`highcharts-react-official`) for analytics,
  `axios` for API calls.
- Code quality: ESLint + Prettier (frontend), Ruff + Black (backend), Husky + lint-staged
  at repo root for pre-commit enforcement.
- Deployment target: **Render.com** — backend as a Web Service, Postgres/PostGIS as a
  Render managed Postgres instance (with PostGIS enabled via `CREATE EXTENSION`), frontend
  as a Static Site. Defined in `render.yaml` (Render Blueprint) at repo root.

## Ports & local URLs

- Backend API: `http://localhost:8000` (uvicorn), docs at `/docs`
- Frontend dev server: `http://localhost:5173`
- Postgres/PostGIS: `localhost:5432`, db name `darukaa`, user `darukaa`, password `darukaa`

## Environment variables

Backend (`backend/.env`, see `backend/.env.example`):
- `DATABASE_URL=postgresql+psycopg2://darukaa:darukaa@localhost:5432/darukaa`
- `JWT_SECRET_KEY=<random>`
- `JWT_ALGORITHM=HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `CORS_ORIGINS=http://localhost:5173`

Frontend (`frontend/.env`, see `frontend/.env.example`):
- `VITE_API_BASE_URL=http://localhost:8000`
- `VITE_MAPBOX_TOKEN=<your mapbox token>`

## Database schema

- **users**: `id (pk)`, `email (unique)`, `hashed_password`, `full_name`, `created_at`
- **projects**: `id (pk)`, `name`, `description`, `owner_id (fk users.id)`, `created_at`
- **sites**: `id (pk)`, `project_id (fk projects.id)`, `name`,
  `geom (GEOMETRY(POLYGON, 4326))`, `area_hectares (float, computed on save)`,
  `site_type (str, e.g. "carbon" | "biodiversity")`, `created_at`
- **site_metrics**: `id (pk)`, `site_id (fk sites.id)`, `date (date)`,
  `carbon_tons (float)`, `biodiversity_index (float, 0-100)`, `ndvi (float, 0-1)`,
  `created_at`
  - One row per site per month; used to power the analytics time-series charts.

## REST API contract

All endpoints under `http://localhost:8000`. JWT auth via `Authorization: Bearer <token>`.

- `POST /auth/register` `{email, password, full_name}` → `{access_token, token_type}`
- `POST /auth/login` `{email, password}` → `{access_token, token_type}`
- `GET /auth/me` → current user
- `GET /projects` → list projects owned by current user (with nested site count)
- `POST /projects` `{name, description}` → created project
- `GET /projects/{project_id}` → project detail with nested `sites` (id, name, geom as GeoJSON, site_type)
- `POST /projects/{project_id}/sites` `{name, site_type, geom: GeoJSON Polygon}` → created site
- `GET /sites/{site_id}` → site detail (incl. geom as GeoJSON, area_hectares)
- `GET /sites/{site_id}/metrics` → list of `{date, carbon_tons, biodiversity_index, ndvi}` sorted by date, for charting
- `GET /sites/{site_id}/analytics/summary` → `{total_carbon_tons, avg_biodiversity_index, avg_ndvi, trend}` for stat tiles

Geometry is always transported as **GeoJSON** (`{"type": "Polygon", "coordinates": [...]}`)
over the wire — never WKT — so the frontend Mapbox layer can consume it directly.

## Mock/seed data

No real satellite data is available for a hackathon build. `backend/app/scripts/seed_data.py`
generates 2-3 demo projects, 2-3 sites each (polygons in plausible forest regions, e.g.
around the Western Ghats, India), and 12 months of synthetic but realistic-looking
`site_metrics` (gently increasing carbon sequestration, biodiversity index with seasonal
noise, NDVI 0.3-0.8). This choice is documented in the README as a deliberate trade-off:
real remote-sensing ingestion (e.g. Sentinel-2 NDVI pipelines) is out of scope for the
hackathon timeframe.

## Build order

1. **Database** — models, migrations, seed script (backend/app/models, backend/app/db, backend/alembic, backend/app/scripts)
2. **Frontend core** — app scaffold, auth, project dashboard, Mapbox draw (frontend/*), leaves a stub `frontend/src/pages/SiteDetail/SiteDetail.jsx`
3. **DevOps** — CI workflows, Husky/lint-staged, Dockerfiles, render.yaml, docker-compose.yml
4. **Backend API** (after DB models exist) — main.py, routers, schemas, security (backend/app/api, backend/app/core/security.py, backend/app/schemas)
5. **Charting** (after frontend scaffold exists) — fills in SiteDetail page + Highcharts components (frontend/src/pages/SiteDetail, frontend/src/components/charts)
6. **Final review** — pass over the whole repo against the hackathon brief and evaluation criteria before submitting
