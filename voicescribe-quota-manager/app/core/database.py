"""PostgreSQL async connection pool."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from structlog import get_logger

logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


def get_pool_url() -> str:
    """Convert SQLAlchemy-style URL to asyncpg format."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return ""
    # postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def init_pool(
    min_size: int = 2,
    max_size: int = 10,
    command_timeout: int = 30,
) -> asyncpg.Pool | None:
    """Initialize connection pool."""
    global _pool
    url = get_pool_url()
    if not url:
        logger.warning("DATABASE_URL not set, PostgreSQL disabled")
        return None
    try:
        _pool = await asyncpg.create_pool(
            url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
        )
        await _pool.fetchval("SELECT 1")
        logger.info("PostgreSQL pool initialized")
        return _pool
    except Exception as e:
        logger.error("PostgreSQL pool init failed", error=str(e))
        return None


async def close_pool() -> None:
    """Close connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


@asynccontextmanager
async def get_conn() -> AsyncGenerator[asyncpg.Connection | None, None]:
    """Get a connection from the pool."""
    if _pool is None:
        yield None
        return
    async with _pool.acquire() as conn:
        yield conn


async def tenant_exists(tenant_id: str) -> bool:
    """Check if tenant exists in tenants table."""
    if _pool is None:
        return False
    try:
        row = await _pool.fetchrow(
            "SELECT 1 FROM tenants WHERE id = $1 AND is_active = TRUE",
            tenant_id,
        )
        return row is not None
    except Exception as e:
        logger.error("tenant_exists failed", tenant_id=tenant_id, error=str(e))
        return False


async def upsert_free_tier_usage(
    tenant_id: str,
    usage_date: str,
    used_count: int,
    quota_exceeded_attempts: int = 0,
) -> None:
    """
    Upsert free_tier_usage. Non-blocking, log errors without propagating.
    """
    if _pool is None:
        return
    try:
        from datetime import datetime, timezone

        reset_at = datetime.strptime(usage_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        await _pool.execute(
            """
            INSERT INTO free_tier_usage (tenant_id, usage_date, used_count, quota_exceeded_attempts, reset_at)
            VALUES ($1, $2::date, $3, $4, $5)
            ON CONFLICT (tenant_id, usage_date) DO UPDATE SET
                used_count = EXCLUDED.used_count,
                quota_exceeded_attempts = free_tier_usage.quota_exceeded_attempts + EXCLUDED.quota_exceeded_attempts,
                updated_at = NOW()
            """,
            tenant_id,
            usage_date,
            used_count,
            quota_exceeded_attempts,
            reset_at,
        )
    except Exception as e:
        logger.error(
            "upsert_free_tier_usage failed",
            tenant_id=tenant_id,
            usage_date=usage_date,
            error=str(e),
        )


async def increment_quota_exceeded(tenant_id: str, usage_date: str) -> None:
    """Increment quota_exceeded_attempts for a tenant/date."""
    if _pool is None:
        return
    try:
        await _pool.execute(
            """
            INSERT INTO free_tier_usage (tenant_id, usage_date, used_count, quota_exceeded_attempts, reset_at)
            VALUES ($1, $2::date, 0, 1, $3::timestamptz)
            ON CONFLICT (tenant_id, usage_date) DO UPDATE SET
                quota_exceeded_attempts = free_tier_usage.quota_exceeded_attempts + 1,
                updated_at = NOW()
            """,
            tenant_id,
            usage_date,
            f"{usage_date} 00:00:00+00",
        )
    except Exception as e:
        logger.error(
            "increment_quota_exceeded failed",
            tenant_id=tenant_id,
            usage_date=usage_date,
            error=str(e),
        )
