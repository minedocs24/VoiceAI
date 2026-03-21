"""HTTP client for SVC-03 Quota Manager."""

from __future__ import annotations

from typing import Any

import httpx
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)


async def check_quota(tenant_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Check quota for tenant. Returns {allowed, used, limit, remaining}."""
    headers = {"X-Internal-Token": settings.internal_service_token}
    if request_id:
        headers["X-Request-Id"] = request_id

    async with httpx.AsyncClient(timeout=settings.quota_timeout_seconds) as client:
        r = await client.get(
            f"{settings.svc03_url.rstrip('/')}/quota/check/{tenant_id}",
            headers=headers,
        )
        r.raise_for_status()
        return r.json()


async def consume_quota(tenant_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Consume one quota unit. Returns {consumed, used, limit, remaining}. 429 if exceeded."""
    headers = {"X-Internal-Token": settings.internal_service_token}
    if request_id:
        headers["X-Request-Id"] = request_id

    async with httpx.AsyncClient(timeout=settings.quota_timeout_seconds) as client:
        r = await client.post(
            f"{settings.svc03_url.rstrip('/')}/quota/consume/{tenant_id}",
            headers=headers,
        )
        data = r.json() if r.content else {}
        if r.status_code == 429:
            return data
        r.raise_for_status()
        return data


async def rollback_quota(tenant_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Rollback consumed quota."""
    headers = {"X-Internal-Token": settings.internal_service_token}
    if request_id:
        headers["X-Request-Id"] = request_id

    async with httpx.AsyncClient(timeout=settings.quota_timeout_seconds) as client:
        r = await client.post(
            f"{settings.svc03_url.rstrip('/')}/quota/rollback/{tenant_id}",
            headers=headers,
        )
        r.raise_for_status()
        return r.json() if r.content else {}
