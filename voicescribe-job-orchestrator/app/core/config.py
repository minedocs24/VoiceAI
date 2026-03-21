"""Configuration from environment and orchestrator.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_orchestrator_config() -> dict[str, Any]:
    """Load config/orchestrator.yml."""
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "orchestrator.yml",
        Path("config") / "orchestrator.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    celery_broker_url: str = Field(default="redis://redis:6379/0")
    celery_result_backend: str = Field(default="redis://redis:6379/1")
    database_url: str = Field(default="")
    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_db: int = Field(default=0, ge=0, le=15)
    redis_password: str = Field(default="")

    svc02_url: str = Field(default="http://voicescribe-file-ingestion:8001")
    svc03_url: str = Field(default="http://voicescribe-quota-manager:8002")
    svc04_url: str = Field(default="http://voicescribe-audio-preprocessor:8003")
    svc06_url: str = Field(default="http://voicescribe-transcription-engine:8005")
    svc07_url: str = Field(default="http://voicescribe-diarization-engine:8006")
    svc08_url: str = Field(default="http://voicescribe-export-service:8007")

    internal_service_token: str = Field(default="")
    port: int = Field(default=8004, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    circuit_breaker_failure_threshold: int = Field(default=5, ge=1)
    circuit_breaker_recovery_timeout: int = Field(default=60, ge=1)
    http_retry_attempts: int = Field(default=3, ge=1)
    http_retry_backoff_base: int = Field(default=2, ge=1)

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()


def get_priority_for_tier(tier: str) -> int:
    """Get Celery priority from tier."""
    cfg = load_orchestrator_config()
    priorities = cfg.get("celery", {}).get("queues", {}).get("cpu_tasks", {}).get("priority", {})
    return priorities.get(tier.upper(), 1)


def get_valid_transitions() -> dict[str, list[str]]:
    """Get state machine transitions from config."""
    cfg = load_orchestrator_config()
    return cfg.get("state_machine", {}).get("transitions", {})
