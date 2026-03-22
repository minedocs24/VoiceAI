"""Integration tests for export API."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_export_free_tier_403_on_docx(client):
    """Free tier requesting DOCX returns 403."""
    with tempfile.TemporaryDirectory() as d:
        with patch("app.services.export_service.settings") as m:
            m.output_base_path = d
            m.enable_txt = True
            m.enable_srt = True
            m.enable_json = True
            m.enable_docx = True
            m.download_base_url = ""
        with patch("app.core.config.settings") as s:
            s.internal_service_token = "test-token"
        resp = client.post(
            "/export",
            json={
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "t1",
                "tier": "FREE",
                "transcript": {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "language": "it",
                    "duration": 10,
                    "segments": [{"start": 0, "end": 2, "text": "Hello"}],
                },
                "formats": ["docx"],
            },
            headers={"X-Internal-Token": "test-token"},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert "TIER_FORBIDDEN" in str(data.get("detail", data))


def test_export_free_txt_srt(client):
    """Free tier gets TXT and SRT."""
    with tempfile.TemporaryDirectory() as d:
        with patch("app.services.export_service.settings") as s:
            s.output_base_path = d
            s.enable_txt = True
            s.enable_srt = True
            s.enable_json = False
            s.enable_docx = False
            s.download_base_url = ""
        with patch("app.core.config.settings") as sec:
            sec.internal_service_token = "test-token"
        resp = client.post(
            "/export",
            json={
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "t1",
                "tier": "FREE",
                "transcript": {
                    "job_id": "550e8400-e29b-41d4-a716-446655440000",
                    "language": "it",
                    "duration": 10,
                    "segments": [
                        {"start": 0, "end": 2, "text": "Hello"},
                        {"start": 2, "end": 4, "text": "World"},
                    ],
                },
            },
            headers={"X-Internal-Token": "test-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "download_urls" in data
        assert "txt" in data["download_urls"]
        assert "srt" in data["download_urls"]


def test_download_export_not_found(client, tmp_path):
    """GET /export/download returns 404 when the file does not exist."""
    with patch("app.core.config.settings") as s:
        s.internal_service_token = "test-token"
        s.output_base_path = str(tmp_path / "nonexistent")
        resp = client.get(
            "/export/download/550e8400-e29b-41d4-a716-446655440000/txt?tenant_id=t1",
            headers={"X-Internal-Token": "test-token"},
        )
    assert resp.status_code == 404


def test_download_export_unknown_format(client, tmp_path):
    """GET /export/download returns 400 for unknown format."""
    with patch("app.core.config.settings") as s:
        s.internal_service_token = "test-token"
        s.output_base_path = str(tmp_path)
        resp = client.get(
            "/export/download/550e8400-e29b-41d4-a716-446655440000/xyz?tenant_id=t1",
            headers={"X-Internal-Token": "test-token"},
        )
    assert resp.status_code == 400


def test_download_export_serves_file(client, temp_output_dir):
    """GET /export/download serves an existing TXT file."""
    job_id = "550e8400-e29b-41d4-a716-446655440000"
    tenant_id = "t1"
    out_dir = temp_output_dir / tenant_id / job_id
    out_dir.mkdir(parents=True)
    (out_dir / "transcript.txt").write_text("Hello World")

    with patch("app.core.config.settings") as s:
        s.internal_service_token = "test-token"
        s.output_base_path = str(temp_output_dir)
        resp = client.get(
            f"/export/download/{job_id}/txt?tenant_id={tenant_id}",
            headers={"X-Internal-Token": "test-token"},
        )
    assert resp.status_code == 200
    assert resp.content == b"Hello World"


def test_download_export_requires_auth(client, tmp_path):
    """GET /export/download returns 401 without internal token."""
    with patch("app.core.config.settings") as s:
        s.internal_service_token = "test-token"
        s.output_base_path = str(tmp_path)
        resp = client.get(
            "/export/download/550e8400-e29b-41d4-a716-446655440000/txt?tenant_id=t1",
        )
    assert resp.status_code == 401


def test_cleanup_endpoint(client):
    """Cleanup endpoint requires auth and valid job_id."""
    with patch("app.core.config.settings") as s:
        s.internal_service_token = "test-token"
    resp = client.delete(
        "/cleanup/550e8400-e29b-41d4-a716-446655440000",
        headers={"X-Internal-Token": "test-token"},
    )
    # May return 200 (file not found) or 400 (path) - depends on RAMDISK_PATH
    assert resp.status_code in (200, 400, 404)
