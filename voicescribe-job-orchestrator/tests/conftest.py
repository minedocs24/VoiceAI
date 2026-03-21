"""Pytest fixtures."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture(autouse=True)
def set_internal_token():
    settings.internal_service_token = "test-internal-token"


@pytest.fixture
def client():
    """Test client with mocked DB/Redis."""
    mock_pool = AsyncMock()
    mock_pool.fetchval = AsyncMock(return_value=1)
    with (
        patch("app.main.get_pool", new_callable=AsyncMock, return_value=mock_pool),
        patch("app.main.close_pool", new_callable=AsyncMock),
        patch("app.core.redis_client.get_redis") as mock_redis,
    ):
        mock_redis.return_value = MagicMock(ping=MagicMock(return_value=True))
        from app.main import app
        yield TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": "test-internal-token"}
