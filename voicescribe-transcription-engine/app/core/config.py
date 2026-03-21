"""Configuration from environment and transcription.yml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_transcription_config() -> dict[str, Any]:
    paths = [
        Path(__file__).resolve().parent.parent.parent / "config" / "transcription.yml",
        Path("config") / "transcription.yml",
    ]
    for p in paths:
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    celery_broker_url: str = Field(default="redis://redis:6379/0")
    celery_result_backend: str = Field(default="redis://redis:6379/1")
    celery_queue_name: str = Field(default="gpu_tasks")
    celery_worker_concurrency: int = Field(default=1, ge=1, le=8)

    whisper_model: str = Field(default="large-v3")
    whisper_compute_type: str = Field(default="int8_float16")
    whisper_beam_size: int = Field(default=5, ge=1, le=20)
    whisper_vad_filter: bool = Field(default=True)
    whisper_batch_size: int = Field(default=1, ge=1, le=32)
    whisper_device: str = Field(default="cuda")
    whisper_cache_dir: str = Field(default="/models/whisper")

    svc05_url: str = Field(default="http://voicescribe-job-orchestrator:8004")
    internal_service_token: str = Field(default="")

    port: int = Field(default=8005, ge=1, le=65535)
    log_level: str = Field(default="INFO")
    inference_timeout_seconds: int = Field(default=1800, ge=60)

    @property
    def temperature(self) -> float:
        return float(load_transcription_config().get("inference", {}).get("temperature", 0.0))

    @property
    def condition_on_previous_text(self) -> bool:
        return bool(load_transcription_config().get("inference", {}).get("condition_on_previous_text", False))

    @property
    def word_timestamps(self) -> bool:
        return bool(load_transcription_config().get("inference", {}).get("word_timestamps", True))

    @property
    def vad_threshold(self) -> float:
        return float(load_transcription_config().get("vad", {}).get("threshold", 0.5))

    @property
    def vad_min_silence_duration_ms(self) -> int:
        return int(load_transcription_config().get("vad", {}).get("min_silence_duration_ms", 400))

    @property
    def auto_split_threshold_s(self) -> int:
        minutes = float(load_transcription_config().get("auto_split", {}).get("threshold_minutes", 90))
        return int(minutes * 60)

    @property
    def auto_split_chunk_length_s(self) -> int:
        return int(load_transcription_config().get("auto_split", {}).get("chunk_length_s", 1800))

    @property
    def auto_split_stride_length_s(self) -> int:
        return int(load_transcription_config().get("auto_split", {}).get("stride_length_s", 10))


settings = Settings()
