"""Integration tests with real Redis (testcontainers)."""

import asyncio
import os

import pytest
from redis.asyncio import Redis
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="module")
def redis_url(redis_container):
    return redis_container.get_connection_url()


@pytest.fixture(autouse=True)
def patch_redis(redis_url, monkeypatch):
    """Patch Redis URL for tests."""
    # redis_url like redis://localhost:49153/0
    url = redis_url.replace("redis://", "")
    if "@" in url:
        url = url.split("@")[1]
    host_port, _, db = url.partition("/")
    host, _, port = host_port.partition(":")
    monkeypatch.setenv("REDIS_HOST", host or "localhost")
    monkeypatch.setenv("REDIS_PORT", port or "6379")
    monkeypatch.setenv("REDIS_DB", db or "0")
    monkeypatch.setenv("REDIS_PASSWORD", "")


@pytest.mark.asyncio
async def test_full_flow_check_consume_consume_429_rollback_consume(redis_url):
    """Test: check -> consume x2 -> 3rd consume 429 -> rollback -> consume ok."""
    from app.core.redis_client import get_redis, close_redis
    from app.core.redis_utils import redis_quota_key, seconds_until_midnight_utc
    from app.services.quota_service import check_quota, consume_quota, rollback_quota

    # Reset Redis client to pick up new URL
    import app.core.redis_client as rc
    rc._client = None

    try:
        limit = 2
        tenant_id = "test-tenant-flow"

        # Check: should be allowed (0 used)
        result = await check_quota(tenant_id, limit)
        assert result.allowed is True
        assert result.used == 0

        # Consume 1
        result = await consume_quota(tenant_id, limit)
        assert result.consumed is True
        assert result.used == 1

        # Consume 2
        result = await consume_quota(tenant_id, limit)
        assert result.consumed is True
        assert result.used == 2

        # Consume 3: must be rejected
        result = await consume_quota(tenant_id, limit)
        assert result.consumed is False
        assert result.allowed is False

        # Rollback
        result = await rollback_quota(tenant_id, limit)
        assert result.used == 1

        # Consume again: should succeed
        result = await consume_quota(tenant_id, limit)
        assert result.consumed is True
        assert result.used == 2
    finally:
        await close_redis()
        rc._client = None


@pytest.mark.asyncio
async def test_race_condition_50_requests(redis_url):
    """50 simultaneous consumes with limit 2 - counter must not exceed 2."""
    from app.core.redis_client import get_redis, close_redis
    from app.services.quota_service import consume_quota, check_quota

    import app.core.redis_client as rc
    rc._client = None

    try:
        limit = 2
        tenant_id = "test-tenant-race"
        n_requests = 50

        # Reset: delete key first
        from app.core.redis_utils import redis_quota_key
        r = await get_redis()
        key = redis_quota_key(tenant_id)
        await r.delete(key)

        # Fire 50 concurrent consumes
        tasks = [consume_quota(tenant_id, limit) for _ in range(n_requests)]
        results = await asyncio.gather(*tasks)

        consumed_count = sum(1 for res in results if res.consumed)
        assert consumed_count <= limit
        assert sum(1 for res in results if res.consumed) == limit
    finally:
        await close_redis()
        rc._client = None
