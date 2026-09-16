"""
Application settings, loaded from environment variables / `backend/.env`.

Every backend env var listed in ARCHITECTURE.md is exposed here, even the
ones only consumed elsewhere (e.g. JWT_SECRET_KEY is used by the
auth/security module, not by this DB layer), so that all downstream
modules can do `from app.core.config import settings`.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---------------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg2://darukaa:darukaa@localhost:5432/darukaa"

    # --- Auth / JWT (used by app/core/security.py) -----
    JWT_SECRET_KEY: str = "change-me-in-production-this-is-a-dev-only-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS ---------------------------------------------------------------
    # Comma-separated list of allowed origins in the raw env var, e.g.
    # "http://localhost:5173,http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS_ORIGINS split into a list, for use in FastAPI's CORSMiddleware."""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Cached Settings singleton accessor."""
    return Settings()


settings = get_settings()
