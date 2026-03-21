"""HTTP client for SVC-05 Job Orchestrator."""

from __future__ import annotations

import httpx
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


async def dispatch_job(
    job_id: str,
    tenant_id: str,
    tier: str,
    duration_seconds: float | None = None,
    request_id: str | None = None,
) -> dict:
    """Call SVC-05 POST /jobs to dispatch preprocessing. Job must already exist in DB."""
    headers = {
        "X-Internal-Token": settings.internal_service_token,
        "Content-Type": "application/json",
    }
    if request_id:
        headers["X-Request-Id"] = request_id

    payload = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "tier": tier,
    }
    if duration_seconds is not None:
        payload["duration_seconds"] = duration_seconds

    async with httpx.AsyncClient(timeout=settings.upstream_timeout_seconds) as client:
        r = await client.post(
            f"{settings.svc05_url.rstrip('/')}/jobs",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        return r.json()
