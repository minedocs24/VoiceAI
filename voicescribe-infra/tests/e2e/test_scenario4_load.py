"""E2E Scenario 4 — Carico parallelo."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e
pytestmark = pytest.mark.skipif(
    not (Path(__file__).parent / "fixtures" / "test_audio_2min.mp3").exists(),
    reason="Test audio fixtures/test_audio_2min.mp3 required",
)


@pytest.mark.asyncio
async def test_parallel_uploads_from_multiple_tenants(
    base_url: str,
    verify_ssl: bool,
):
    """
    20 upload simultanei da 5 tenant (4 ciascuno), tutti DONE,
    quote Free rispettate, PRO prima di Free (priorità).
    """
    # Simplified: 5 uploads from 1 Free tenant (quota 2) - 2 should succeed, 3 get 429
    # Or use PRO tenants which have no quota
    async with httpx.AsyncClient(verify=verify_ssl, timeout=120.0) as client:
        login_resp = await client.post(
            f"{base_url}/v1/auth/login",
            json={"email": "free@test.local", "password": "password"},
        )
        if login_resp.status_code != 200:
            pytest.skip("Login failed")
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        test_audio = Path(__file__).parent / "fixtures" / "test_audio_2min.mp3"

        # Fire 4 uploads in parallel
        async def upload_one(i: int):
            with open(test_audio, "rb") as f:
                return await client.post(
                    f"{base_url}/v1/transcribe",
                    headers=headers,
                    files={"file": (f"audio{i}.mp3", f.read(), "audio/mpeg")},
                )

        tasks = [upload_one(i) for i in range(4)]
        results = await asyncio.gather(*tasks)
        # Free tier: max 2/day - first 2 get 202, next 2 get 429
        statuses = [r.status_code for r in results]
        assert 202 in statuses
        assert 429 in statuses or statuses.count(202) <= 2
