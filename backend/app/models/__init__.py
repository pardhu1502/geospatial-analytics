"""
SQLAlchemy models package.

Import order matters for relationship resolution but SQLAlchemy resolves
string-based relationship references lazily, so plain imports here are
enough to register every model on `Base.metadata`.
"""

from app.models.user import User
from app.models.project import Project
from app.models.site import Site
from app.models.site_metric import SiteMetric

__all__ = ["User", "Project", "Site", "SiteMetric"]
