"""E2E Scenario 3 — Resilienza agli errori."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_free_tier_45min_returns_422(
    base_url: str,
    verify_ssl: bool,
):
    """Upload file 45 min come Free Tier → 422."""
    # Create a long silent file or use fixture
    long_audio = Path(__file__).parent / "fixtures" / "test_audio_45min.mp3"
    if not long_audio.exists():
        pytest.skip("fixtures/test_audio_45min.mp3 required")
    async with httpx.AsyncClient(verify=verify_ssl, timeout=60.0) as client:
        login_resp = await client.post(
            f"{base_url}/v1/auth/login",
            json={"email": "free@test.local", "password": "password"},
        )
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        with open(long_audio, "rb") as f:
            r = await client.post(
                f"{base_url}/v1/transcribe",
                headers=headers,
                files={"file": ("long.mp3", f, "audio/mpeg")},
            )
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_path_traversal_upload_rejected(
    base_url: str,
    verify_ssl: bool,
):
    """Path traversal in filename → 400/422."""
    async with httpx.AsyncClient(verify=verify_ssl, timeout=30.0) as client:
        login_resp = await client.post(
            f"{base_url}/v1/auth/login",
            json={"email": "free@test.local", "password": "password"},
        )
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        r = await client.post(
            f"{base_url}/v1/transcribe",
            headers=headers,
            files={"file": ("../../../etc/passwd", b"fake", "audio/mpeg")},
        )
        assert r.status_code in (400, 422, 413)
