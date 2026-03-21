"""Redis client for pub/sub job status."""

from __future__ import annotations

import json
from typing import Any

import redis
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _client


def close_redis() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def publish_job_status(job_id: str, status: str, payload: dict[str, Any] | None = None) -> None:
    """Publish job status to Redis channel job:{job_id}:status."""
    try:
        r = get_redis()
        msg = {"status": status, **(payload or {})}
        channel = f"job:{job_id}:status"
        r.publish(channel, json.dumps(msg))
    except Exception as e:
        logger.warning("redis_publish_failed", job_id=job_id, error=str(e))
