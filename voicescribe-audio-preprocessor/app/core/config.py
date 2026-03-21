"""Configuration from environment and preprocessor.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_preprocessor_config() -> dict[str, Any]:
    """Load config/preprocessor.yml. Returns empty dict if file not found."""
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "preprocessor.yml",
        Path("config") / "preprocessor.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    celery_broker_url: str = Field(default="redis://redis:6379/0")
    celery_result_backend: str = Field(default="redis://redis:6379/1")
    celery_queue_name: str = Field(default="cpu_tasks")
    celery_worker_concurrency: int = Field(default=12, ge=1, le=64)

    ramdisk_path: str = Field(default="/mnt/ramdisk")
    storage_base_path: str = Field(default="/data/input")
    svc02_url: str = Field(default="http://voicescribe-file-ingestion:8001")
    svc05_url: str = Field(default="http://voicescribe-job-orchestrator:8004")
    svc03_url: str = Field(default="http://voicescribe-quota-manager:8002")

    internal_service_token: str = Field(default="")

    port: int = Field(default=8003, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    ffmpeg_timeout_seconds: int = Field(default=120, ge=10)

    @property
    def output_sample_rate(self) -> int:
        cfg = load_preprocessor_config()
        return cfg.get("output", {}).get("sample_rate", 16000)

    @property
    def output_channels(self) -> int:
        cfg = load_preprocessor_config()
        return cfg.get("output", {}).get("channels", 1)

    @property
    def loudness_target_lufs(self) -> float:
        cfg = load_preprocessor_config()
        return cfg.get("loudness", {}).get("target_lufs", -23.0)

    @property
    def noise_reduction_enabled(self) -> bool:
        cfg = load_preprocessor_config()
        return cfg.get("noise_reduction", {}).get("enabled", True)

    @property
    def supported_formats(self) -> list[str]:
        cfg = load_preprocessor_config()
        return cfg.get("supported_formats", ["mp3", "mp4", "wav", "m4a", "ogg", "flac", "webm", "mkv"])


settings = Settings()


def get_preprocessor_config() -> dict[str, Any]:
    """Return non-secret preprocessor config."""
    return load_preprocessor_config()
