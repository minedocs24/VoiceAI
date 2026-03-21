"""Redis async client."""

from __future__ import annotations

import json

import redis.asyncio as redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get Redis client. Lazy init."""
    global _client
    if _client is None:
        try:
            _client = redis.from_url(settings.redis_url, decode_responses=True)
            await _client.ping()
            logger.info("redis_client_initialized")
        except Exception as exc:
            logger.error("redis_init_failed", error=str(exc))
            return None
    return _client


async def close_redis() -> None:
    """Close Redis client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def redis_ping() -> bool:
    """Check Redis connectivity."""
    client = await get_redis()
    if client is None:
        return False
    try:
        await client.ping()
        return True
    except Exception:
        return False


async def get_json_cache(key: str) -> dict | None:
    """Get cached JSON dictionary by key."""
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def set_json_cache(key: str, payload: dict, ttl_seconds: int) -> None:
    """Set JSON payload to Redis cache."""
    client = await get_redis()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(payload), ex=ttl_seconds)
    except Exception:
        logger.warning("redis_set_failed", key=key)