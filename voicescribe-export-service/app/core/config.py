"""Configuration from environment and export.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_export_config() -> dict[str, Any]:
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "export.yml",
        Path("config") / "export.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    output_base_path: str = Field(default="/data/output")
    ramdisk_path: str = Field(default="/mnt/ramdisk")
    output_ttl_days: int = Field(default=30, ge=1, le=365)

    redis_url: str = Field(default="redis://redis:6379/0")
    database_url: str = Field(default="postgresql://user:pass@postgres:5432/voicescribe")

    svc05_callback_url: str = Field(default="http://voicescribe-job-orchestrator:8004")
    internal_service_token: str = Field(default="")

    celery_broker_url: str = Field(default="redis://redis:6379/0")
    celery_result_backend: str = Field(default="redis://redis:6379/1")
    celery_queue_name: str = Field(default="export_tasks")

    port: int = Field(default=8007, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    enable_txt: bool = Field(default=True)
    enable_srt: bool = Field(default=True)
    enable_json: bool = Field(default=True)
    enable_docx: bool = Field(default=True)

    download_base_url: str = Field(default="", description="Base URL per download_urls (es. https://api.example.com/downloads)")


settings = Settings()
