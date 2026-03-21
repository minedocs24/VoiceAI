"""Pytest fixtures."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def create_minimal_wav(path: Path) -> None:
    """Create a minimal valid WAV file (44.1kHz mono, 0.1s silence)."""
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * 4410)  # 0.1 sec


@pytest.fixture(autouse=True)
def settings_setup(tmp_path):
    """Override settings for tests."""
    settings.internal_service_token = "test-internal-token"
    settings.ramdisk_path = str(tmp_path / "ramdisk")
    settings.storage_base_path = str(tmp_path / "input")
    settings.celery_queue_name = "cpu_tasks"
    settings.ffmpeg_timeout_seconds = 30
    Path(settings.ramdisk_path).mkdir(parents=True, exist_ok=True)
    Path(settings.storage_base_path).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Headers with internal token."""
    return {"X-Internal-Token": "test-internal-token"}


@pytest.fixture
def sample_wav(tmp_path):
    """Minimal WAV file for testing."""
    p = tmp_path / "input" / "test.wav"
    create_minimal_wav(p)
    return str(p)
