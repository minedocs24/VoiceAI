"""Unit tests for quota service logic (mocked Redis)."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.quota_service import consume_quota, check_quota, rollback_quota


@pytest.mark.asyncio
async def test_check_quota_redis_unavailable():
    with patch("app.services.quota_service.get_redis", return_value=None):
        result = await check_quota("tenant-1", 2)
        assert result.allowed is False
        assert result.used == 0
        assert result.limit == 2


@pytest.mark.asyncio
async def test_check_quota_allowed():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="1")
    with patch("app.services.quota_service.get_redis", return_value=mock_redis):
        result = await check_quota("tenant-1", 2)
        assert result.allowed is True
        assert result.used == 1
        assert result.limit == 2


@pytest.mark.asyncio
async def test_check_quota_denied():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="2")
    with patch("app.services.quota_service.get_redis", return_value=mock_redis):
        result = await check_quota("tenant-1", 2)
        assert result.allowed is False
        assert result.used == 2


@pytest.mark.asyncio
async def test_check_quota_empty_key():
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    with patch("app.services.quota_service.get_redis", return_value=mock_redis):
        result = await check_quota("tenant-1", 2)
        assert result.allowed is True
        assert result.used == 0


@pytest.mark.asyncio
async def test_consume_quota_success():
    mock_redis = AsyncMock()
    mock_pipe = Mock()
    mock_pipe.incr = Mock(return_value=mock_pipe)
    mock_pipe.expire = Mock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[1, True])
    mock_redis.pipeline = lambda: mock_pipe
    with patch("app.services.quota_service.get_redis", return_value=mock_redis):
        with patch("app.services.quota_service.asyncio.create_task"):
            result = await consume_quota("tenant-1", 2)
            assert result.consumed is True
            assert result.used == 1
            assert result.allowed is True


@pytest.mark.asyncio
async def test_consume_quota_exceeded():
    mock_redis = AsyncMock()
    mock_pipe = Mock()
    mock_pipe.incr = Mock(return_value=mock_pipe)
    mock_pipe.expire = Mock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[3, True])
    mock_redis.pipeline = lambda: mock_pipe
    mock_redis.decr = AsyncMock(return_value=2)
    with patch("app.services.quota_service.get_redis", return_value=mock_redis):
        with patch("app.services.quota_service.asyncio.create_task"):
            result = await consume_quota("tenant-1", 2)
            assert result.consumed is False
            assert result.allowed is False
            assert result.used == 2
