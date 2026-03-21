"""Pydantic schemas - TranscriptResult/DiarizationResult from SVC-06/SVC-07."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TranscriptWord(BaseModel):
    word: str
    start: float | None = None
    end: float | None = None
    probability: float | None = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    confidence: float | None = None
    words: list[TranscriptWord] | None = None
    speaker: str | None = None  # Present in DiarizationResult


class TranscriptResult(BaseModel):
    """Schema from SVC-06 Transcription Engine."""

    job_id: str
    language: str = "unknown"
    duration: float = 0.0
    rtf: float | None = None
    inference_ms: int | None = None
    segments: list[TranscriptSegment] = Field(default_factory=list)


class SpeakerStats(BaseModel):
    speaker: str
    utterance_count: int = 0


class DiarizationResult(TranscriptResult):
    """TranscriptResult extended with speaker per segment - from SVC-07."""

    speakers: list[SpeakerStats] | None = None


# --- Export API schemas ---


class ExportRequest(BaseModel):
    """Request body for POST /export."""

    job_id: str
    tenant_id: str
    tier: str = Field(..., pattern=r"^(FREE|PRO|ENTERPRISE)$")
    transcript: dict[str, Any]  # TranscriptResult or DiarizationResult as dict
    formats: list[str] | None = None  # If None, generate all allowed for tier
    include_timestamps_txt: bool = False
    webhook_url: str | None = None


class ExportResponse(BaseModel):
    """Response from POST /export."""

    job_id: str
    files: list[str] = Field(default_factory=list)
    download_urls: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response."""

    code: str
    message: str
    detail: str | None = None


# --- Callback schema (to SVC-05) ---


class ExportCompletePayload(BaseModel):
    """Payload sent to SVC-05 callback."""

    job_id: str
    tenant_id: str
    success: bool
    download_urls: dict[str, str] | None = None
    error_code: str | None = None
    error_message: str | None = None
