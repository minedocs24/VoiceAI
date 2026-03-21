"""Configuration loading from environment and quota.yml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_quota_config() -> dict[str, Any]:
    """Load config/quota.yml. Returns empty dict if file not found."""
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "quota.yml",
        Path("config") / "quota.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Redis
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=2, ge=0, le=15)
    redis_password: str = Field(default="")
    redis_timeout: int = Field(default=5, ge=1)

    # Database
    database_url: str = Field(default="")

    # Service
    port: int = Field(default=8002, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    # Quota
    free_tier_daily_limit: int = Field(default=2, ge=1)

    # Security
    internal_service_token: str = Field(default="")

    @property
    def redis_url(self) -> str:
        """Build Redis URL with password."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def sync_database_url(self) -> str:
        """Convert async URL to sync for Alembic."""
        return self.database_url.replace("+asyncpg", "+psycopg", 1) if self.database_url else ""


def get_quota_config() -> dict[str, Any]:
    """Get merged quota config (YAML overridden by env where applicable)."""
    return load_quota_config()
