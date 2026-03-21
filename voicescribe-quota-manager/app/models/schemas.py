"""Pydantic schemas for API request/response."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# --- Error ---
class ErrorResponse(BaseModel):
    """Standard error response for 4xx and 5xx."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable message")
    detail: str | None = Field(default=None, description="Optional detail")


# --- Quota Check ---
class QuotaCheckResponse(BaseModel):
    """Response for GET /quota/check."""

    allowed: bool = Field(..., description="Whether quota allows the operation")
    used: int = Field(..., ge=0, description="Current usage count for the day")
    limit: int = Field(..., ge=1, description="Daily limit")
    remaining: int = Field(..., ge=0, description="Remaining quota")


# --- Quota Consume ---
class QuotaConsumeRequest(BaseModel):
    """Request body for POST /quota/consume."""

    pass  # No body required, tenant_id from path


class QuotaConsumeResponse(BaseModel):
    """Response for POST /quota/consume."""

    consumed: bool = Field(..., description="Whether quota was consumed")
    used: int = Field(..., ge=0, description="Usage count after consume")
    limit: int = Field(..., ge=1, description="Daily limit")
    remaining: int = Field(..., ge=0, description="Remaining quota")


# --- Quota Status ---
class QuotaStatusResponse(BaseModel):
    """Response for GET /quota/status/{tenant_id}."""

    tenant_id: str = Field(..., description="Tenant identifier")
    usage_date: date = Field(..., description="Date of usage (UTC)")
    used_count: int = Field(..., ge=0, description="Consumed count")
    limit: int = Field(..., ge=1, description="Daily limit")
    remaining: int = Field(..., ge=0, description="Remaining quota")
    reset_at: datetime | None = Field(default=None, description="When quota resets (midnight UTC)")


# --- Rollback ---
class QuotaRollbackRequest(BaseModel):
    """Request body for POST /quota/rollback."""

    pass  # No body required


class QuotaRollbackResponse(BaseModel):
    """Response for POST /quota/rollback."""

    rolled_back: bool = Field(..., description="Whether rollback was applied")
    used: int = Field(..., ge=0, description="Usage count after rollback")
    limit: int = Field(..., ge=1, description="Daily limit")
    message: str = Field(default="Quota restored", description="Status message")


# --- Analytics ---
class AnalyticsItem(BaseModel):
    """Single analytics row."""

    tenant_id: str
    usage_date: date
    used_count: int
    quota_exceeded_attempts: int


class AnalyticsResponse(BaseModel):
    """Response for GET /analytics."""

    items: list[AnalyticsItem] = Field(default_factory=list)
    total: int = Field(..., ge=0, description="Total count matching filters")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)


# --- Health ---
class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    name: str
    status: Literal["ok", "error"]
    message: str | None = None


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: Literal["healthy", "degraded", "unhealthy"]
    dependencies: list[DependencyStatus] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
