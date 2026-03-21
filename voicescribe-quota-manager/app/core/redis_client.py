"""Redis async client."""

from __future__ import annotations

import os
from typing import Any

import redis.asyncio as redis
from structlog import get_logger

logger = get_logger(__name__)

_client: redis.Redis | None = None


def get_redis_url() -> str:
    """Build Redis URL from env."""
    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "2")
    password = os.getenv("REDIS_PASSWORD", "")
    auth = f":{password}@" if password else ""
    return f"redis://{auth}{host}:{port}/{db}"


async def get_redis() -> redis.Redis | None:
    """Get Redis client. Lazy init."""
    global _client
    if _client is None:
        url = get_redis_url()
        try:
            _client = redis.from_url(url, decode_responses=True)
            await _client.ping()
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error("Redis init failed", error=str(e))
            return None
    return _client


async def close_redis() -> None:
    """Close Redis client."""
    global _client
    if _client:
        await _client.aclose()
        _client = None
        logger.info("Redis client closed")


async def redis_ping() -> bool:
    """Check Redis connectivity."""
    r = await get_redis()
    if r is None:
        return False
    try:
        await r.ping()
        return True
    except Exception:
        return False
