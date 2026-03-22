"""Integration tests with mocked SVC-02/SVC-03."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def free_tier_token():
    token, _ = create_access_token("free-tenant", "FREE")
    return token


@pytest.fixture
def pro_token():
    token, _ = create_access_token("pro-tenant", "PRO")
    return token


@patch("app.api.routers.jobs.svc05_dispatch", new_callable=AsyncMock)
@patch("app.api.routers.jobs.svc02_upload", new_callable=AsyncMock)
@patch("app.api.routers.jobs.insert_job", new_callable=AsyncMock)
@patch("app.api.routers.jobs.check_rate_limit", new_callable=AsyncMock)
def test_transcribe_pro_no_quota(mock_rate_limit, mock_insert, mock_upload, mock_dispatch, client, pro_token):
    """PRO user can upload without quota check."""
    mock_rate_limit.return_value = (True, 100, 99, 999999)
    mock_upload.return_value = {"status": "uploaded"}
    mock_insert.return_value = None
    mock_dispatch.return_value = None

    r = client.post(
        "/v1/transcribe",
        headers={"Authorization": f"Bearer {pro_token}"},
        files={"file": ("test.mp3", b"fake audio content", "audio/mpeg")},
    )
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data
    assert data["status"] == "QUEUED"
    mock_upload.assert_called_once()
    mock_insert.assert_called_once()


@patch("app.api.routers.jobs.get_job", new_callable=AsyncMock)
def test_download_docx_free_tier_403(mock_get_job, client, free_tier_token):
    """Free Tier cannot download DOCX."""
    mock_get_job.return_value = {
        "id": "123",
        "tenant_id": "free-tenant",
        "status": "DONE",
        "tier_at_creation": "FREE",
        "created_at": None,
        "completed_at": None,
        "error_message": None,
    }
    r = client.get(
        "/v1/jobs/123/download/docx",
        headers={"Authorization": f"Bearer {free_tier_token}"},
    )
    assert r.status_code == 403


def test_transcribe_requires_auth(client):
    """Transcribe requires authentication."""
    r = client.post(
        "/v1/transcribe",
        files={"file": ("test.mp3", b"content", "audio/mpeg")},
    )
    assert r.status_code == 401
