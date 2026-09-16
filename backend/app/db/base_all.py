"""
Single import point that pulls in every SQLAlchemy model so that
`Base.metadata` is fully populated before Alembic autogenerate (or
`Base.metadata.create_all`) runs.

Import this module (not the individual model modules) wherever you need
all models registered on the metadata, e.g. from `alembic/env.py`:

    from app.db.base import Base
    from app.db import base_all  # noqa: F401
    target_metadata = Base.metadata
"""

from app.models.user import User  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.site import Site  # noqa: F401
from app.models.site_metric import SiteMetric  # noqa: F401
