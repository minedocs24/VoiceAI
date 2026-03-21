from datetime import datetime, timezone
from io import BytesIO

import pytest

from app.models.schemas import FileRecord


@pytest.fixture
def mp3_like_bytes():
    return bytes.fromhex("49 44 33 04 00 00") + (b"A" * 4096)


def test_upload_rejects_without_token(client, mp3_like_bytes):
    files = {"file": ("song.mp3", BytesIO(mp3_like_bytes), "audio/mpeg")}
    response = client.post(
        "/upload",
        files=files,
        headers={
            "X-Tenant-Id": "tenant-123",
            "X-Job-Id": "11111111-1111-1111-1111-111111111111",
        },
    )
    assert response.status_code == 401


def test_upload_rejects_png_renamed_mp3(client, auth_headers):
    png_bytes = bytes.fromhex("89 50 4E 47 0D 0A 1A 0A") + (b"B" * 1024)
    files = {"file": ("evil.mp3", BytesIO(png_bytes), "audio/mpeg")}
    response = client.post("/upload", files=files, headers=auth_headers)
    assert response.status_code == 400


def test_upload_rejects_free_tier_duration(client, auth_headers, monkeypatch, mp3_like_bytes):
    async def fake_probe_media_file(job_id: str, file_path: str):
        return {
            "job_id": job_id,
            "duration_seconds": 2700.0,
            "audio_codec": "aac",
            "sample_rate": 44100,
            "channels": 2,
            "bitrate": 128000,
            "cached": False,
        }

    monkeypatch.setattr("app.api.routers.probe_media_file", fake_probe_media_file)

    headers = {**auth_headers, "X-Free-Tier": "true"}
    files = {"file": ("long.mp3", BytesIO(mp3_like_bytes), "audio/mpeg")}
    response = client.post("/upload", files=files, headers=headers)

    assert response.status_code == 422
    assert "Free tier duration exceeded" in response.json()["detail"]


def test_upload_valid_returns_201(client, auth_headers, monkeypatch, mp3_like_bytes):
    async def fake_insert_file_record(**kwargs):
        now = datetime.now(timezone.utc)
        return FileRecord(
            tenant_id=kwargs["tenant_id"],
            job_id=kwargs["job_id"],
            file_uuid=kwargs["file_uuid"],
            storage_path=kwargs["storage_path"],
            size_bytes=kwargs["size_bytes"],
            detected_ext=kwargs["detected_ext"],
            sha256=kwargs["sha256"],
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr("app.api.routers.insert_file_record", fake_insert_file_record)

    files = {"file": ("ok.mp3", BytesIO(mp3_like_bytes), "audio/mpeg")}
    response = client.post("/upload", files=files, headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["file"]["detected_ext"] == "mp3"


def test_probe_returns_metadata(client, auth_headers, monkeypatch):
    now = datetime.now(timezone.utc)

    async def fake_get_latest_file_for_job(job_id: str):
        return FileRecord(
            tenant_id="tenant-123",
            job_id=job_id,
            file_uuid="11111111-1111-1111-1111-111111111111",
            storage_path="/tmp/fake.mp3",
            size_bytes=123,
            detected_ext="mp3",
            sha256="0" * 64,
            created_at=now,
            updated_at=now,
        )

    async def fake_probe_media_file(job_id: str, file_path: str):
        return {
            "job_id": job_id,
            "duration_seconds": 42.5,
            "audio_codec": "mp3",
            "sample_rate": 44100,
            "channels": 2,
            "bitrate": 128000,
            "cached": False,
        }

    monkeypatch.setattr("app.api.routers.get_latest_file_for_job", fake_get_latest_file_for_job)
    monkeypatch.setattr("app.api.routers.probe_media_file", fake_probe_media_file)

    response = client.get("/probe/11111111-1111-1111-1111-111111111111", headers={"X-Internal-Token": "test-internal-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["duration_seconds"] == 42.5
    assert data["audio_codec"] == "mp3"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code in (200, 503)


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200