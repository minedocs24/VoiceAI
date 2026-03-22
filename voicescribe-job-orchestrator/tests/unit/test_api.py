"""Unit tests for API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    import app.main as main_mod
    mock_pool = AsyncMock()
    mock_pool.fetchval = AsyncMock(return_value=1)
    with (
        patch.object(main_mod, "get_pool", new_callable=AsyncMock, return_value=mock_pool),
        patch.object(main_mod, "close_pool", new_callable=AsyncMock),
        patch("app.core.redis_client.get_redis") as mock_redis,
    ):
        mock_redis.return_value = MagicMock(ping=MagicMock(return_value=True))
        yield TestClient(main_mod.app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": "test-internal-token"}


@pytest.fixture(autouse=True)
def mock_all():
    with (
        patch("app.core.database.create_job", new_callable=AsyncMock) as mock_create,
        patch("app.core.database.transition_job", new_callable=AsyncMock) as mock_transition,
        patch("app.core.database.get_job", new_callable=AsyncMock) as mock_get,
        patch("app.core.database.get_job_for_update", new_callable=AsyncMock) as mock_get_update,
        patch("app.services.http_client.call_svc04_preprocess") as mock_svc04,
    ):
        mock_create.return_value = {}
        mock_transition.return_value = True
        mock_get.return_value = None
        mock_get_update.return_value = None
        mock_svc04.return_value = "celery-task-123"
        yield


def test_create_job_requires_auth(client):
    r = client.post("/jobs", json={"tenant_id": "t1", "tier": "FREE"})
    assert r.status_code == 401


def test_create_job_success(client, auth_headers):
    """POST /jobs with an existing job_id (pre-created by api-gateway) dispatches preprocessing."""
    job_id = uuid4()
    fake_job = {"id": job_id, "status": "QUEUED", "tier_at_creation": "FREE", "tenant_id": "t1"}
    with (
        patch("app.core.database.get_job_for_update", new_callable=AsyncMock, return_value=fake_job),
        patch("app.core.database.transition_job", new_callable=AsyncMock, return_value=True),
        patch("app.services.http_client.call_svc04_preprocess", return_value="task-123"),
    ):
        r = client.post(
            "/jobs",
            json={"job_id": str(job_id), "tenant_id": "t1", "tier": "FREE"},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "PREPROCESSING"


def test_get_job_404(client, auth_headers):
    with patch("app.core.database.get_job", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        r = client.get(f"/jobs/{uuid4()}", headers=auth_headers)
    assert r.status_code == 404


def test_queue_stats_requires_auth(client):
    r = client.get("/queue/stats")
    assert r.status_code == 401


def test_create_job_requires_job_id(client, auth_headers):
    """POST /jobs without job_id must return 422 — dead code path removed."""
    r = client.post("/jobs", json={"tenant_id": "t1", "tier": "FREE"}, headers=auth_headers)
    assert r.status_code == 422


import asyncio
import inspect


def test_publish_job_status_is_coroutine():
    """publish_job_status must be async — sync Redis blocks the event loop in FastAPI routes."""
    from app.core.redis_client import publish_job_status
    assert asyncio.iscoroutinefunction(publish_job_status), (
        "publish_job_status must be async — sync Redis blocks the event loop in FastAPI routes"
    )
