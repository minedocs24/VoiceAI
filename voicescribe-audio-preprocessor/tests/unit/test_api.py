"""Unit tests for API endpoints."""

from unittest.mock import MagicMock, patch

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


def test_secondary_quota_check_does_not_rollback():
    """
    When the secondary quota check fails, _rollback_quota must NOT be called.
    The quota was already consumed at the gateway layer — rolling back here
    would grant the tenant a free extra job.
    """
    with (
        patch("app.tasks._get_input_path", return_value="/tmp/audio.mp3"),
        patch("app.tasks._check_quota", return_value=False),
        patch("app.tasks._rollback_quota") as mock_rollback,
        patch("app.tasks._notify_svc05") as mock_notify,
        patch("app.tasks.QUOTA_CHECK_FAILURES_TOTAL") as mock_qmetric,
        patch("app.tasks.PREPROCESS_TASKS_TOTAL") as mock_tmetric,
    ):
        mock_qmetric.inc = MagicMock()
        mock_tmetric.labels = MagicMock(return_value=MagicMock(inc=MagicMock()))
        mock_notify.return_value = True

        from celery.exceptions import Reject
        from app.tasks import preprocess_task

        mock_self = MagicMock()
        mock_self.request.retries = 0

        with pytest.raises(Reject):
            preprocess_task.__wrapped__(mock_self, "job-123", "tenant-456")

        mock_rollback.assert_not_called()
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args[1]
        assert call_kwargs.get("success") is False
        assert call_kwargs.get("error_code") == "quota_exceeded"
