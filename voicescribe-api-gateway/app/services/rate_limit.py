"""Rate limiting: auth failure and functional per-tier."""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException, Request, status

from app.services.redis_client import get_redis


async def check_auth_failure_rate_limit(client_ip: str) -> None:
    """Check if IP is blocked due to auth failures. Raises 429 if blocked."""
    r = await get_redis()
    block_key = f"auth_block:{client_ip}"
    if await r.exists(block_key):
        ttl = await r.ttl(block_key)
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(max(1, ttl))},
        )


async def record_auth_failure(client_ip: str, config: dict[str, Any] | None = None) -> None:
    """Record auth failure. Block IP if threshold exceeded."""
    config = config or {}
    max_attempts = config.get("auth_failure_max_attempts", 5)
    window_min = config.get("auth_failure_window_minutes", 15)
    block_min = config.get("auth_failure_block_minutes", 30)

    r = await get_redis()
    counter_key = f"auth_fail:{client_ip}"
    block_key = f"auth_block:{client_ip}"

    pipe = r.pipeline()
    pipe.incr(counter_key)
    pipe.expire(counter_key, window_min * 60)
    results = await pipe.execute()
    count = results[0]

    if count >= max_attempts:
        await r.setex(block_key, block_min * 60, "1")
        await r.delete(counter_key)
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. IP temporarily blocked.",
            headers={"Retry-After": str(block_min * 60)},
        )


async def check_rate_limit(tenant_id: str, tier: str, config: dict[str, Any]) -> tuple[bool, int, int, int]:
    """
    Check functional rate limit per tenant/tier.
    Returns (allowed, limit, remaining, reset_timestamp).
    """
    rpm_map = {
        "FREE": config.get("free_tier_rpm", 10),
        "PRO": config.get("pro_tier_rpm", 100),
        "ENTERPRISE": config.get("enterprise_tier_rpm", 500),
    }
    limit = rpm_map.get(tier.upper(), 10)

    r = await get_redis()
    window_start = int(time.time() // 60) * 60
    key = f"ratelimit:{tier}:{tenant_id}:{window_start}"

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 120)
    results = await pipe.execute()
    count = results[0]

    remaining = max(0, limit - count)
    reset_ts = window_start + 60
    allowed = count <= limit

    return allowed, limit, remaining, reset_ts
