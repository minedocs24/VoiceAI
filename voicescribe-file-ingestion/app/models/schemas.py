"""Pydantic schemas for API I/O."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: str | None = None


class FileRecord(BaseModel):
    tenant_id: str
    job_id: str
    file_uuid: str
    storage_path: str
    size_bytes: int
    detected_ext: str
    sha256: str
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    status: str = "uploaded"
    file: FileRecord


class FileListResponse(BaseModel):
    job_id: str
    files: list[FileRecord]


class DeleteResponse(BaseModel):
    job_id: str
    deleted_files: int


class ProbeResponse(BaseModel):
    job_id: str
    duration_seconds: float = Field(ge=0)
    audio_codec: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bitrate: int | None = None
    cached: bool = False


class DependencyStatus(BaseModel):
    name: str
    status: str
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]
    timestamp: datetime