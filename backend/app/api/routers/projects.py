from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.geo import geojson_to_polygon, geom_to_geojson, polygon_area_hectares
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.site import Site
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectDetail, ProjectOut
from app.schemas.site import SiteCreate, SiteNested, SiteOut

router = APIRouter(tags=["projects"])


def _get_owned_project(project_id: int, db: Session, current_user: User) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )
    if project is None:
        # Same 404 whether the project doesn't exist or belongs to someone
        # else, so we never leak which projects exist to other users.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ProjectOut]:
    rows = (
        db.query(Project, func.count(Site.id).label("site_count"))
        .outerjoin(Site, Site.project_id == Project.id)
        .filter(Project.owner_id == current_user.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        ProjectOut(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            site_count=site_count,
        )
        for project, site_count in rows
    ]


@router.post(
    "/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectOut:
    project = Project(
        name=payload.name, description=payload.description, owner_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        site_count=0,
    )


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetail:
    project = (
        db.query(Project)
        .options(joinedload(Project.sites))
        .filter(Project.id == project_id, Project.owner_id == current_user.id)
        .first()
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    sites = [
        SiteNested(
            id=site.id,
            name=site.name,
            site_type=site.site_type,
            geom=geom_to_geojson(site.geom),
            area_hectares=site.area_hectares,
        )
        for site in project.sites
    ]
    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        site_count=len(sites),
        sites=sites,
    )


@router.post(
    "/projects/{project_id}/sites",
    response_model=SiteOut,
    status_code=status.HTTP_201_CREATED,
)
def create_site(
    project_id: int,
    payload: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SiteOut:
    project = _get_owned_project(project_id, db, current_user)

    try:
        polygon = geojson_to_polygon(payload.geom.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    # area_hectares computed server-side; see app/core/geo.py docstring for
    # the geodesic-area (pyproj Geod) approach and why it was chosen.
    area_hectares = polygon_area_hectares(polygon)

    site = Site(
        project_id=project.id,
        name=payload.name,
        site_type=payload.site_type,
        geom=from_shape(polygon, srid=4326),
        area_hectares=area_hectares,
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    return SiteOut(
        id=site.id,
        project_id=site.project_id,
        name=site.name,
        site_type=site.site_type,
        geom=geom_to_geojson(site.geom),
        area_hectares=site.area_hectares,
        created_at=site.created_at,
    )
