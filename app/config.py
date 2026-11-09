"""Application settings.

Every value is read from the environment with a working in-code default so a
fresh clone boots with no ``.env`` file and no exported variables at all.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Development-only fallback for the cookie signing key. A real deployment sets
# SECRET_KEY (install.sh writes one on first run); this keeps a bare
# `uvicorn app.main:app` bootable.
DEV_SECRET_KEY = "cenius-dev-4c9f2a7d1e6b8350"


class Settings(BaseSettings):
    """Runtime configuration with boot-safe defaults."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Releasesmith"
    secret_key: str = Field(
        default=DEV_SECRET_KEY,
        validation_alias=AliasChoices("SECRET_KEY", "SESSION_SECRET", "secret_key"),
    )
    database_url: str = Field(
        default="sqlite:///./releasesmith.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    session_cookie_name: str = "releasesmith_session"
    session_max_age: int = 60 * 60 * 24 * 14
    debug: bool = False

    @field_validator("secret_key", mode="before")
    @classmethod
    def _blank_secret_uses_default(cls, value):
        """An empty SECRET_KEY= line in .env falls back to the dev key."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEV_SECRET_KEY
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _blank_database_uses_default(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return "sqlite:///./releasesmith.db"
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
