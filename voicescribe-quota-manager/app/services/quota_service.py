"""Quota service: check, consume, rollback with Redis + async PostgreSQL."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import NamedTuple

from structlog import get_logger

from app.core.database import (
    increment_quota_exceeded,
    tenant_exists,
    upsert_free_tier_usage,
)
from app.core.redis_client import get_redis
from app.core.redis_utils import (
    redis_quota_key,
    seconds_until_midnight_utc,
    usage_date_utc,
)

logger = get_logger(__name__)


class QuotaResult(NamedTuple):
    """Result of quota operation."""

    allowed: bool
    used: int
    limit: int
    consumed: bool = False  # For consume: was it actually consumed


async def check_quota(tenant_id: str, limit: int) -> QuotaResult:
    """
    Check quota without consuming. Returns allowed/denied and current usage.
    """
    r = await get_redis()
    if r is None:
        logger.error("Redis unavailable for check_quota", tenant_id=tenant_id)
        return QuotaResult(allowed=False, used=0, limit=limit)

    key = redis_quota_key(tenant_id)
    try:
        used = await r.get(key)
        used = int(used) if used else 0
        allowed = used < limit
        return QuotaResult(allowed=allowed, used=used, limit=limit)
    except Exception as e:
        logger.error("check_quota failed", tenant_id=tenant_id, error=str(e))
        return QuotaResult(allowed=False, used=0, limit=limit)


async def consume_quota(tenant_id: str, limit: int) -> QuotaResult:
    """
    Atomically consume one unit of quota. Uses Redis pipeline: INCR + EXPIRE.
    Returns QuotaResult with consumed=True only if quota was actually consumed.
    If quota exceeded, increments quota_exceeded_attempts in PG (async, non-blocking).
    """
    r = await get_redis()
    if r is None:
        logger.error("Redis unavailable for consume_quota", tenant_id=tenant_id)
        return QuotaResult(allowed=False, used=0, limit=limit, consumed=False)

    key = redis_quota_key(tenant_id)
    usage_date = usage_date_utc()
    ttl = seconds_until_midnight_utc()

    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        new_used = results[0]

        if new_used > limit:
            # Rollback: we exceeded, decrement
            await r.decr(key)
            # Record quota_exceeded for analytics (async, fire-and-forget)
            asyncio.create_task(increment_quota_exceeded(tenant_id, usage_date))
            return QuotaResult(
                allowed=False,
                used=limit,  # Report limit as "used" for clarity
                limit=limit,
                consumed=False,
            )

        # Success: persist to PG async (fire-and-forget)
        asyncio.create_task(upsert_free_tier_usage(tenant_id, usage_date, new_used, 0))
        return QuotaResult(
            allowed=True,
            used=new_used,
            limit=limit,
            consumed=True,
        )
    except Exception as e:
        logger.error("consume_quota failed", tenant_id=tenant_id, error=str(e))
        return QuotaResult(allowed=False, used=0, limit=limit, consumed=False)


async def rollback_quota(tenant_id: str, limit: int) -> QuotaResult:
    """
    Rollback one consumed unit. Idempotent: if key expired or already 0, no-op.
    """
    r = await get_redis()
    if r is None:
        logger.error("Redis unavailable for rollback_quota", tenant_id=tenant_id)
        return QuotaResult(allowed=True, used=0, limit=limit, consumed=False)

    key = redis_quota_key(tenant_id)
    usage_date = usage_date_utc()
    ttl = seconds_until_midnight_utc()

    try:
        current = await r.get(key)
        if current is None:
            # Key expired or never existed - idempotent, consider rolled back
            return QuotaResult(allowed=True, used=0, limit=limit, consumed=False)

        current_int = int(current)
        if current_int <= 0:
            return QuotaResult(allowed=True, used=0, limit=limit, consumed=False)

        pipe = r.pipeline()
        pipe.decr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        new_used = results[0]
        new_used = max(0, new_used)

        # Persist to PG (async)
        asyncio.create_task(upsert_free_tier_usage(tenant_id, usage_date, new_used, 0))
        return QuotaResult(
            allowed=True,
            used=new_used,
            limit=limit,
            consumed=False,  # Rollback, not consume
        )
    except Exception as e:
        logger.error("rollback_quota failed", tenant_id=tenant_id, error=str(e))
        return QuotaResult(allowed=True, used=0, limit=limit, consumed=False)
