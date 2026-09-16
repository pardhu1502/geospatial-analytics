"""initial schema: postgis extension + users, projects, sites, site_metrics

Revision ID: 0001
Revises:
Create Date: 2026-09-16

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS must be enabled before any Geometry column can be created.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_projects_id", "projects", ["id"])
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])

    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="POLYGON", srid=4326),
            nullable=False,
        ),
        sa.Column("area_hectares", sa.Float(), nullable=True),
        sa.Column("site_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sites_id", "sites", ["id"])
    op.create_index("ix_sites_project_id", "sites", ["project_id"])
    # GeoAlchemy2 also auto-creates a GIST spatial index on `geom` via its
    # `Table` "after_create" DDL event (since Geometry defaults to
    # spatial_index=True), but we create it explicitly too for clarity and
    # so it exists even if that event hook is ever bypassed.
    op.execute("CREATE INDEX IF NOT EXISTS idx_sites_geom ON sites USING GIST (geom);")

    op.create_table(
        "site_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "site_id",
            sa.Integer(),
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("carbon_tons", sa.Float(), nullable=False),
        sa.Column("biodiversity_index", sa.Float(), nullable=False),
        sa.Column("ndvi", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_site_metrics_id", "site_metrics", ["id"])
    op.create_index("ix_site_metrics_site_id", "site_metrics", ["site_id"])
    op.create_index("ix_site_metrics_date", "site_metrics", ["date"])


def downgrade() -> None:
    op.drop_index("ix_site_metrics_date", table_name="site_metrics")
    op.drop_index("ix_site_metrics_site_id", table_name="site_metrics")
    op.drop_index("ix_site_metrics_id", table_name="site_metrics")
    op.drop_table("site_metrics")

    op.execute("DROP INDEX IF EXISTS idx_sites_geom;")
    op.drop_index("ix_sites_project_id", table_name="sites")
    op.drop_index("ix_sites_id", table_name="sites")
    op.drop_table("sites")

    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_index("ix_projects_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    # Intentionally not dropping the postgis extension on downgrade: it may
    # be relied on by other databases/schemas in the same Postgres instance.
