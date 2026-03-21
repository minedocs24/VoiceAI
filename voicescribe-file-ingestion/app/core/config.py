"""Configuration loading from environment and ingestion.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_ingestion_config() -> dict[str, Any]:
    """Load config/ingestion.yml. Returns empty dict if file not found."""
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "ingestion.yml",
        Path("config") / "ingestion.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    storage_base_path: str = Field(default="/data/input")
    temp_upload_dir: str = Field(default="/tmp/voicescribe-upload")
    upload_max_bytes: int = Field(default=2 * 1024 * 1024 * 1024, ge=1)

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=3, ge=0, le=15)
    redis_password: str = Field(default="")
    redis_timeout: int = Field(default=5, ge=1)

    database_url: str = Field(default="")
    quota_manager_url: str = Field(default="http://voicescribe-quota-manager:8002")

    internal_service_token: str = Field(default="")

    port: int = Field(default=8001, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    probe_timeout_seconds: int = Field(default=30, ge=1)
    probe_cache_ttl_seconds: int = Field(default=3600, ge=1)
    free_tier_max_duration_seconds: int = Field(default=1800, ge=1)

    health_disk_degraded_threshold_pct: int = Field(default=80, ge=1, le=99)
    temp_file_max_age_seconds: int = Field(default=3600, ge=60)
    temp_cleanup_interval_seconds: int = Field(default=900, ge=60)
    upload_chunk_size: int = Field(default=262144, ge=1024)
    magic_buffer_size: int = Field(default=64, ge=8)

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()


def get_ingestion_config() -> dict[str, Any]:
    """Return non-secret ingestion config."""
    return load_ingestion_config()