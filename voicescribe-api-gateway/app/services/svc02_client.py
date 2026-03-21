"""HTTP client for SVC-02 File Ingestion."""

from __future__ import annotations

import io
from typing import Any

import httpx
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


async def upload_file(
    file_content: bytes,
    filename: str,
    tenant_id: str,
    job_id: str,
    free_tier: bool = False,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Upload file to SVC-02. Returns upload response or raises."""
    headers = {
        "X-Internal-Token": settings.internal_service_token,
        "X-Tenant-Id": tenant_id,
        "X-Job-Id": job_id,
    }
    if free_tier:
        headers["X-Free-Tier"] = "true"
    if request_id:
        headers["X-Request-Id"] = request_id

    files = {"file": (filename, io.BytesIO(file_content))}
    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
        r = await client.post(
            f"{settings.svc02_url.rstrip('/')}/upload",
            headers=headers,
            files=files,
        )
        r.raise_for_status()
        return r.json()


async def delete_files_by_job(job_id: str, request_id: str | None = None) -> None:
    """Delete files for job from SVC-02."""
    headers = {
        "X-Internal-Token": settings.internal_service_token,
    }
    if request_id:
        headers["X-Request-Id"] = request_id

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.delete(
            f"{settings.svc02_url.rstrip('/')}/files/{job_id}",
            headers=headers,
        )
        r.raise_for_status()


async def probe_job(job_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Get probe metadata for job from SVC-02."""
    headers = {
        "X-Internal-Token": settings.internal_service_token,
    }
    if request_id:
        headers["X-Request-Id"] = request_id

    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
        r = await client.get(
            f"{settings.svc02_url.rstrip('/')}/probe/{job_id}",
            headers=headers,
        )
        r.raise_for_status()
        return r.json()
