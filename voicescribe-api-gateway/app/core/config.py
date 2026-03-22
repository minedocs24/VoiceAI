"""Configuration loading from environment and gateway.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_gateway_config() -> dict[str, Any]:
    """Load config/gateway.yml. Returns empty dict if file not found."""
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "gateway.yml",
        Path("config") / "gateway.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def get_gateway_config() -> dict[str, Any]:
    """Return gateway config from YAML."""
    return load_gateway_config()


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Upstream services
    svc02_url: str = Field(default="http://voicescribe-file-ingestion:8001")
    svc03_url: str = Field(default="http://voicescribe-quota-manager:8002")
    svc05_url: str = Field(default="http://voicescribe-job-orchestrator:8004")

    # Internal auth
    internal_service_token: str = Field(default="")

    # JWT
    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_expires_hours: int = Field(default=24, ge=1)
    jwt_refresh_expires_days: int = Field(default=7, ge=1)

    # Database (PostgreSQL for tenant/API key verification)
    database_url: str = Field(default="")

    # Redis (rate limit, cache tenant, refresh tokens)
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_password: str = Field(default="")

    # Server
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")
    log_level: str = Field(default="INFO")
    swagger_ui_enabled: bool = Field(default=False)

    # Timeouts (seconds)
    upstream_timeout_seconds: int = Field(default=30, ge=1)
    quota_timeout_seconds: int = Field(default=10, ge=1)

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def model_post_init(self, __context) -> None:
        if not self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY must be set — refusing to start with empty JWT secret")
        if not self.internal_service_token:
            raise ValueError("INTERNAL_SERVICE_TOKEN must be set — refusing to start with empty internal token")


settings = Settings()
