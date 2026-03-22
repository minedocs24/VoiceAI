"""Async Redis client for pub/sub job status."""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_client: Redis | None = None


async def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def publish_job_status(job_id: str, status: str, payload: dict[str, Any] | None = None) -> None:
    """Publish job status to Redis channel job:{job_id}:status."""
    try:
        r = await get_redis()
        msg = {"status": status, **(payload or {})}
        channel = f"job:{job_id}:status"
        await r.publish(channel, json.dumps(msg))
    except Exception as e:
        logger.warning("redis_publish_failed", job_id=job_id, error=str(e))
