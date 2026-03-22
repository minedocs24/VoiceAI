"""Tests for the download proxy endpoint (GET /jobs/{job_id}/download/{fmt})."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("INTERNAL_SERVICE_TOKEN", "test-internal-token")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("REDIS_HOST", "localhost")

import httpx
from fastapi.testclient import TestClient

from app.main import app


def _make_jwt(tenant_id: str, tier: str = "FREE") -> str:
    import jwt as pyjwt
    return pyjwt.encode(
        {"sub": tenant_id, "tenant_id": tenant_id, "tier": tier, "type": "access"},
        "test-secret-key-for-testing-only",
        algorithm="HS256",
    )


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def tenant_id():
    return str(uuid4())


@pytest.fixture
def job_id():
    return str(uuid4())


def test_download_proxy_job_not_done(client, tenant_id, job_id):
    """Returns 404 if job is not DONE yet."""
    token = _make_jwt(tenant_id)
    fake_job = {"id": job_id, "tenant_id": tenant_id, "status": "TRANSCRIBING", "tier_at_creation": "FREE"}

    with (
        patch("app.api.routers.jobs.get_job", new_callable=AsyncMock, return_value=fake_job),
        patch("app.services.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=(True, 100, 99, 9999999999)),
    ):
        resp = client.get(
            f"/v1/jobs/{job_id}/download/txt",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404
    # The gateway error handler puts the message in "message", not "detail"
    body = resp.json()
    message = (body.get("message") or "").lower()
    assert "not ready" in message or "not completed" in message or "not done" in message


def test_download_proxy_format_forbidden_free_tier(client, tenant_id, job_id):
    """Free tier cannot download docx — returns 403 before calling SVC-08."""
    token = _make_jwt(tenant_id, "FREE")
    fake_job = {"id": job_id, "tenant_id": tenant_id, "status": "DONE", "tier_at_creation": "FREE"}

    with (
        patch("app.api.routers.jobs.get_job", new_callable=AsyncMock, return_value=fake_job),
        patch("app.services.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=(True, 100, 99, 9999999999)),
    ):
        resp = client.get(
            f"/v1/jobs/{job_id}/download/docx",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


def test_download_proxy_success(client, tenant_id, job_id):
    """Returns file content proxied from SVC-08."""
    token = _make_jwt(tenant_id)
    fake_job = {"id": job_id, "tenant_id": tenant_id, "status": "DONE", "tier_at_creation": "FREE"}
    fake_svc08_response = MagicMock()
    fake_svc08_response.status_code = 200
    fake_svc08_response.content = b"Hello transcript"
    fake_svc08_response.headers = {
        "content-type": "text/plain; charset=utf-8",
        "content-disposition": 'attachment; filename="transcript.txt"',
    }

    with (
        patch("app.api.routers.jobs.get_job", new_callable=AsyncMock, return_value=fake_job),
        patch("app.services.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=(True, 100, 99, 9999999999)),
        patch("app.api.routers.jobs.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=fake_svc08_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        resp = client.get(
            f"/v1/jobs/{job_id}/download/txt",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.content == b"Hello transcript"


def test_download_proxy_svc08_unavailable(client, tenant_id, job_id):
    """Returns 503 when SVC-08 is unreachable."""
    token = _make_jwt(tenant_id)
    fake_job = {"id": job_id, "tenant_id": tenant_id, "status": "DONE", "tier_at_creation": "FREE"}

    with (
        patch("app.api.routers.jobs.get_job", new_callable=AsyncMock, return_value=fake_job),
        patch("app.services.rate_limit.check_rate_limit", new_callable=AsyncMock, return_value=(True, 100, 99, 9999999999)),
        patch("app.api.routers.jobs.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        resp = client.get(
            f"/v1/jobs/{job_id}/download/txt",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 503
