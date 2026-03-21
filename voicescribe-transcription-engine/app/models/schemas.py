"""Pydantic schemas for API and transcript results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WordResult(BaseModel):
    word: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    probability: float = Field(ge=0, le=1)


class SegmentResult(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    confidence: float = Field(ge=0, le=1)
    words: list[WordResult] = Field(default_factory=list)

    @field_validator("end")
    @classmethod
    def validate_end(cls, value: float, info):
        start = info.data.get("start", 0.0)
        if value < start:
            raise ValueError("end must be greater than or equal to start")
        return value


class TranscriptResult(BaseModel):
    job_id: str
    language: str
    duration: float = Field(ge=0)
    rtf: float = Field(ge=0)
    inference_ms: int = Field(ge=0)
    segments: list[SegmentResult]


class TranscribeRequest(BaseModel):
    job_id: str
    tenant_id: str | None = None
    input_path: str
    beam_size: int | None = Field(default=None, ge=1, le=20)


class AsyncTranscribeResponse(BaseModel):
    task_id: str
    job_id: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: TranscriptResult | None = None
    error: str | None = None


class ModelInfo(BaseModel):
    name: str
    compute_type: str
    loaded: bool


class ModelsResponse(BaseModel):
    active_model: ModelInfo
    supported_models: list[str]


class GPUStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str
    compute_type: str
    cuda_version: str
    vram_total_gb: float
    vram_used_gb: float
    vram_free_gb: float
    last_rtf: float
    ready_for_new_job: bool
    service_ready: bool


class DependencyStatus(BaseModel):
    name: str
    status: str
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]
    timestamp: datetime | None = None


class CallbackPayload(BaseModel):
    job_id: str
    tenant_id: str
    success: bool
    transcription_raw: dict | None = None
    gpu_inference_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
