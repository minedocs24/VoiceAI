"""Pydantic schemas for API Gateway."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    detail: str | None = None


class AuthenticatedTenant(BaseModel):
    """Tenant after successful authentication (JWT or API Key)."""

    tenant_id: str
    tier: Literal["FREE", "PRO", "ENTERPRISE"]
    permissions: list[str] = Field(default_factory=list)


# Auth
class LoginRequest(BaseModel):
    """Login request for Free Tier."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """New access token from refresh."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Jobs
class TranscribeResponse(BaseModel):
    """Response after successful transcribe submission."""

    job_id: str
    status: str = "QUEUED"
    message: str = "Job queued for processing"


class JobStatus(BaseModel):
    """Job status for list/detail."""

    id: str
    tenant_id: str
    status: str
    tier_at_creation: str
    created_at: str
    completed_at: str | None = None
    error_message: str | None = None


class JobListResponse(BaseModel):
    """List of jobs."""

    jobs: list[JobStatus]
    total: int
