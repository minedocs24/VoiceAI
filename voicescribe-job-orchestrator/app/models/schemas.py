"""Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    """Request to create a job."""

    tenant_id: str = Field(..., pattern=r"^[a-zA-Z0-9\-]{1,64}$")
    tier: str = Field(..., pattern=r"^(FREE|PRO|ENTERPRISE)$")
    duration_seconds: float | None = None
    job_id: str | None = None  # Optional: if provided, use existing job (from api-gateway)


class JobCreateResponse(BaseModel):
    """Response with job ID."""

    job_id: UUID
    status: str = "QUEUED"


class JobStatusResponse(BaseModel):
    """Job status response."""

    id: UUID
    tenant_id: str
    status: str
    tier_at_creation: str
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None


class PreprocessingCompleteRequest(BaseModel):
    """Callback from SVC-04."""

    job_id: str
    tenant_id: str
    success: bool
    ramdisk_path: str | None = None
    sha256: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class TranscriptionCompleteRequest(BaseModel):
    """Callback from SVC-06."""

    job_id: str
    tenant_id: str
    success: bool
    transcription_raw: dict | None = None
    gpu_inference_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None


class DiarizationCompleteRequest(BaseModel):
    """Callback from SVC-07."""

    job_id: str
    tenant_id: str
    success: bool
    diarization_raw: dict | None = None
    diarization_available: bool = True  # False quando SVC-07 in fallback (es. token HF invalido)
    error_code: str | None = None
    error_message: str | None = None


class ExportCompleteRequest(BaseModel):
    """Callback from SVC-08."""

    job_id: str
    tenant_id: str
    success: bool
    download_urls: dict[str, str] | None = None
    error_code: str | None = None
    error_message: str | None = None


class DependencyStatus(BaseModel):
    """Health dependency status."""

    name: str
    status: str
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    dependencies: list[DependencyStatus]
    timestamp: str | None = None


class QueueStatsResponse(BaseModel):
    """Queue statistics."""

    queued: int
    preprocessing: int
    transcribing: int
    diarizing: int
    exporting: int
    done: int
    failed: int
