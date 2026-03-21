"""Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PreprocessRequest(BaseModel):
    """Request to queue preprocessing."""

    job_id: str = Field(..., description="Job UUID")
    tenant_id: str = Field(..., description="Tenant ID")
    input_path: str | None = Field(None, description="Optional full or relative input path; if omitted, fetched from SVC-02")


class PreprocessResponse(BaseModel):
    """Response with Celery task id."""

    task_id: str = Field(..., description="Celery task ID")
    job_id: str = Field(..., description="Job UUID")


class PreprocessStatusResponse(BaseModel):
    """Task status from Celery."""

    task_id: str
    status: str = Field(..., description="pending, success, failure")
    result: dict | None = None
    error: str | None = None


class FormatsResponse(BaseModel):
    """Supported audio formats."""

    formats: list[str]


class DependencyStatus(BaseModel):
    """Health dependency status."""

    name: str
    status: str  # ok, error
    message: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # healthy, degraded, unhealthy
    dependencies: list[DependencyStatus]
    timestamp: str | None = None
