"""API endpoint tests (requires running service or TestClient with mocked deps)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-Internal-Token": "test-internal-token"}


def test_health_no_auth_required(client):
    """Health endpoint does not require auth."""
    r = client.get("/health")
    # May be 200 or 503 depending on Redis/DB
    assert r.status_code in (200, 503)


def test_metrics_no_auth_required(client):
    """Metrics endpoint does not require auth."""
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "quota_check_total" in r.text or "quota_consume_total" in r.text


def test_quota_check_401_without_token(client):
    """Quota check requires X-Internal-Token."""
    r = client.get("/quota/check/tenant-123")
    assert r.status_code == 401


def test_quota_check_401_bad_token(client):
    """Quota check rejects wrong token."""
    r = client.get("/quota/check/tenant-123", headers={"X-Internal-Token": "wrong"})
    assert r.status_code == 401


def test_openapi_json(client):
    """OpenAPI JSON is served from openapi.yaml."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    data = r.json()
    assert "paths" in data
    assert "/quota/check/{tenant_id}" in data["paths"]
