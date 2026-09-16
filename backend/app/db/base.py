"""
Declarative base for all SQLAlchemy models.

Alembic's `env.py` imports `Base.metadata` from this module to support
`--autogenerate`. To make sure autogenerate can "see" every model, this
module also imports `app.db.base_class` -> models via `base_all`.

Usage:
    from app.db.base import Base
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""

    pass
