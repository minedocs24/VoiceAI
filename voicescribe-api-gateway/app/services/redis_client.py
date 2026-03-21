"""Redis client for cache, rate limit, refresh tokens."""

from __future__ import annotations

from typing import Any

import redis.asyncio as redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get Redis connection."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


async def get_cached_tenant(api_key_hash: str) -> dict[str, Any] | None:
    """Get tenant from cache (60s TTL)."""
    r = await get_redis()
    key = f"tenant:apikey:{api_key_hash}"
    data = await r.get(key)
    if data:
        import json
        return json.loads(data)
    return None


async def set_cached_tenant(api_key_hash: str, tenant: dict[str, Any], ttl: int = 60) -> None:
    """Cache tenant verification result."""
    r = await get_redis()
    key = f"tenant:apikey:{api_key_hash}"
    import json
    await r.setex(key, ttl, json.dumps(tenant))


async def store_refresh_token(jti: str, tenant_id: str, ttl_seconds: int) -> None:
    """Store refresh token in Redis for revocation check."""
    r = await get_redis()
    key = f"refresh:{jti}"
    await r.setex(key, ttl_seconds, tenant_id)


async def revoke_refresh_token(jti: str) -> bool:
    """Revoke refresh token. Returns True if existed."""
    r = await get_redis()
    key = f"refresh:{jti}"
    deleted = await r.delete(key)
    return deleted > 0


async def is_refresh_valid(jti: str) -> bool:
    """Check if refresh token exists (not revoked, not expired)."""
    r = await get_redis()
    key = f"refresh:{jti}"
    return await r.exists(key) > 0
