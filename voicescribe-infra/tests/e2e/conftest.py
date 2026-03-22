"""Pytest fixtures for e2e tests."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
import yaml

# Base URL for API (via nginx or direct to api-gateway)
BASE_URL = os.environ.get("E2E_BASE_URL", "https://localhost")
# Skip TLS verify for dev certs
VERIFY_SSL = os.environ.get("E2E_VERIFY_SSL", "false").lower() == "true"


@pytest.fixture(scope="session")
def base_url():
    """Base URL for API requests."""
    return BASE_URL


@pytest.fixture(scope="session")
def verify_ssl():
    """Whether to verify SSL certificates."""
    return VERIFY_SSL


@pytest.fixture(scope="session")
def compose_project_dir():
    """Path to docker-compose project (voicescribe-infra)."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def free_tier_quota_limit() -> int:
    """Daily quota limit for Free Tier, read from quota manager config."""
    quota_yml = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "voicescribe-quota-manager"
        / "config"
        / "quota.yml"
    )
    if quota_yml.exists():
        with open(quota_yml, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return int(cfg.get("quota", {}).get("daily_limit", 2))
    return 2  # fallback matches current default


@pytest.fixture(scope="session")
def test_audio_path():
    """Path to test audio file (2 min)."""
    path = Path(__file__).parent / "fixtures" / "test_audio_2min.mp3"
    if not path.exists():
        pytest.skip("Test audio file not found. Create fixtures/test_audio_2min.mp3 (2 min audio)")
    return path
