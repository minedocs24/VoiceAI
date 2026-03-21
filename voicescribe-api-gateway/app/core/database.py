"""Database connection and queries for tenant/API key verification and jobs."""

from __future__ import annotations

from typing import Any

import asyncpg
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


def _get_database_url() -> str:
    """Convert postgresql+asyncpg to postgresql for asyncpg."""
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


async def get_pool() -> asyncpg.Pool:
    """Get or create connection pool."""
    global _pool
    if _pool is None:
        url = _get_database_url()
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=10, command_timeout=10)
    return _pool


async def close_pool() -> None:
    """Close connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def verify_api_key(api_key_hash: str) -> dict[str, Any] | None:
    """Verify API key hash against tenants. Returns tenant row or None."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, name, tier, is_active
            FROM tenants
            WHERE api_key_hash = $1 AND is_active = TRUE
            """,
            api_key_hash,
        )
        if row:
            return dict(row)
    return None


async def get_tenant_by_email(email: str) -> dict[str, Any] | None:
    """Get tenant by email (for Free Tier login)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, name, tier, password_hash, is_active
            FROM tenants
            WHERE email = $1 AND is_active = TRUE
            """,
            email.lower().strip(),
        )
        if row:
            return dict(row)
    return None


async def get_job(job_id: str) -> dict[str, Any] | None:
    """Get job by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, tenant_id, status, tier_at_creation, created_at, completed_at, error_message
            FROM jobs
            WHERE id = $1
            """,
            job_id,
        )
        if row:
            return dict(row)
    return None


async def list_jobs_for_tenant(tenant_id: str, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """List jobs for tenant with pagination."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM jobs WHERE tenant_id = $1",
            tenant_id,
        )
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, status, tier_at_creation, created_at, completed_at, error_message
            FROM jobs
            WHERE tenant_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            tenant_id,
            limit,
            offset,
        )
        return [dict(r) for r in rows], total or 0


async def insert_job(
    job_id: str,
    tenant_id: str,
    tier: str,
    status: str = "QUEUED",
    priority: int = 1,
) -> None:
    """Insert new job record."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO jobs (id, tenant_id, tier_at_creation, status, priority)
            VALUES ($1, $2, $3::tier_at_creation, $4::job_status, $5)
            """,
            job_id,
            tenant_id,
            tier,
            status,
            priority,
        )
