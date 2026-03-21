"""Unit tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": "test-internal-token"}


def test_formats_no_auth(client):
    """GET /formats does not require auth."""
    r = client.get("/formats")
    assert r.status_code == 200
    data = r.json()
    assert "formats" in data
    assert "mp3" in data["formats"]


def test_preprocess_requires_auth(client):
    """POST /preprocess requires X-Internal-Token."""
    r = client.post("/preprocess", json={"job_id": "11111111-1111-1111-1111-111111111111", "tenant_id": "t1"})
    assert r.status_code == 401


def test_preprocess_invalid_job_id(client, auth_headers):
    """Invalid job_id returns 422."""
    r = client.post(
        "/preprocess",
        json={"job_id": "invalid", "tenant_id": "t1"},
        headers=auth_headers,
    )
    assert r.status_code in (400, 422)


def test_preprocess_status_requires_auth(client):
    """GET /preprocess/{task_id}/status requires auth."""
    r = client.get("/preprocess/some-task-id/status")
    assert r.status_code == 401
