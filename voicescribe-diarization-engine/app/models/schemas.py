"""Pydantic schemas per API e DiarizationResult."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WordResult(BaseModel):
    word: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    probability: float = Field(ge=0, le=1)


class TranscriptSegment(BaseModel):
    """Segmento trascrizione (compatibile SVC-06) con speaker opzionale."""

    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    confidence: float = Field(ge=0, le=1, default=0.0)
    words: list[WordResult] = Field(default_factory=list)
    speaker: str | None = None


class SpeakerStats(BaseModel):
    speaker: str
    utterance_count: int = Field(ge=0)


class DiarizationResult(BaseModel):
    """TranscriptResult arricchito con speaker per segmento e lista speakers."""

    job_id: str
    language: str
    duration: float = Field(ge=0)
    rtf: float = Field(ge=0)
    inference_ms: int = Field(ge=0)
    segments: list[TranscriptSegment]
    speakers: list[SpeakerStats] = Field(default_factory=list)


class DiarizeRequest(BaseModel):
    job_id: str
    input_path: str
    segments: list[dict] | None = None  # Opzionale: se assente solo timeline speaker
    language: str = "unknown"
    duration: float = Field(ge=0, default=0.0)
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None


class ModelStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_loaded: bool
    hf_token_valid: bool
    vram_used_mb: float
    load_seconds: float
    model_name: str = ""
    service_ready: bool = False


class DependencyStatus(BaseModel):
    name: str
    status: str
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]


class CallbackPayload(BaseModel):
    """Payload per callback SVC-05 diarization-complete."""

    job_id: str
    tenant_id: str
    success: bool
    diarization_raw: dict | None = None
    diarization_available: bool = True
    error_code: str | None = None
    error_message: str | None = None
