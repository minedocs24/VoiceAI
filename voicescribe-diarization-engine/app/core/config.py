"""Configuration from environment and diarization.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_diarization_config() -> dict[str, Any]:
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "diarization.yml",
        Path("config") / "diarization.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    huggingface_token: str = Field(default="", description="Token HuggingFace obbligatorio per Pyannote")
    pyannote_model: str = Field(default="pyannote/speaker-diarization-3.1")
    hf_home: str = Field(default="/models/pyannote", description="Cache modelli HuggingFace")

    celery_broker_url: str = Field(default="redis://redis:6379/0")
    celery_result_backend: str = Field(default="redis://redis:6379/1")
    celery_queue_name: str = Field(default="gpu_tasks")
    celery_worker_concurrency: int = Field(default=1, ge=1, le=8)

    svc05_url: str = Field(default="http://voicescribe-job-orchestrator:8004")
    internal_service_token: str = Field(default="")

    port: int = Field(default=8006, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    diarization_timeout_seconds: int = Field(default=600, ge=60)

    @property
    def min_speaker_segment_duration(self) -> float:
        return float(load_diarization_config().get("min_speaker_segment_duration", 0.3))

    @property
    def num_speakers_default(self) -> int | None:
        val = load_diarization_config().get("num_speakers_default")
        return int(val) if val is not None else None

    @property
    def num_speakers_max(self) -> int:
        return int(load_diarization_config().get("num_speakers_max", 20))

    @property
    def max_diarization_seconds(self) -> int:
        return int(
            load_diarization_config().get("timeouts", {}).get("max_diarization_seconds", 600)
        )


settings = Settings()
