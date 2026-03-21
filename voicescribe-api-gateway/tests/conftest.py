"""Pytest fixtures."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set env before importing app
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_DB", "15")  # Use different DB for tests

from app.main import app


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis for tests."""
    with patch("app.services.redis_client.get_redis") as m:
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock()
        redis_mock.exists = AsyncMock(return_value=0)
        redis_mock.incr = AsyncMock(return_value=1)
        redis_mock.expire = AsyncMock()
        redis_mock.delete = AsyncMock(return_value=1)
        redis_mock.pipeline = MagicMock(return_value=AsyncMock())
        m.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_db():
    """Mock database for tests."""
    with patch("app.core.database.get_pool") as m:
        pool = AsyncMock()
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchval = AsyncMock(return_value=0)
        conn.execute = AsyncMock()
        pool.acquire = MagicMock(return_value=conn)
        m.return_value = pool
        yield pool
