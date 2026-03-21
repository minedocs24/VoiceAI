"""Pytest fixtures and env bootstrap."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def settings_setup(tmp_path):
    settings.internal_service_token = "test-internal-token"
    settings.storage_base_path = str(tmp_path / "input")
    settings.temp_upload_dir = str(tmp_path / "temp")
    settings.upload_max_bytes = 5 * 1024 * 1024
    settings.free_tier_max_duration_seconds = 1800
    settings.upload_chunk_size = 64 * 1024
    settings.magic_buffer_size = 64
    Path(settings.storage_base_path).mkdir(parents=True, exist_ok=True)
    Path(settings.temp_upload_dir).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {
        "X-Internal-Token": "test-internal-token",
        "X-Tenant-Id": "tenant-123",
        "X-Job-Id": "11111111-1111-1111-1111-111111111111",
    }