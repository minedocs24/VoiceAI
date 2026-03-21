"""E2E Scenario 1 — Flusso Free Tier Completo."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path

import httpx
import pytest

# Skip entire module if no test audio
pytestmark = pytest.mark.skipif(
    not (Path(__file__).parent / "fixtures" / "test_audio_2min.mp3").exists(),
    reason="Test audio fixtures/test_audio_2min.mp3 required",
)


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload (no verify, for test only)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    return json.loads(base64.urlsafe_b64decode(payload_b64))


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_free_tier_full_flow(
    base_url: str,
    verify_ssl: bool,
    test_audio_path: Path,
):
    """
    Free Tier: login, upload 2 min, poll DONE, download TXT/SRT, 403 su DOCX.
    Secondo upload OK. Terzo upload 429 + Retry-After.
    """
    async with httpx.AsyncClient(verify=verify_ssl, timeout=120.0) as client:
        # 1. Login (Free Tier - requires seed: free@test.local / test123)
        login_resp = await client.post(
            f"{base_url}/v1/auth/login",
            json={"email": "free@test.local", "password": "password"},
        )
        if login_resp.status_code != 200:
            pytest.skip(f"Login failed (seed user required): {login_resp.text}")
        data = login_resp.json()
        token = data.get("access_token")
        assert token, "No access_token in login response"
        tenant_id = _decode_jwt_payload(token).get("tenant_id", "free-tier-tenant")

        headers = {"Authorization": f"Bearer {token}"}

        # 2. Upload first file
        with open(test_audio_path, "rb") as f:
            upload_resp = await client.post(
                f"{base_url}/v1/transcribe",
                headers=headers,
                files={"file": ("audio.mp3", f, "audio/mpeg")},
            )
        assert upload_resp.status_code == 202, f"Upload failed: {upload_resp.text}"
        job_id = upload_resp.json().get("job_id")
        assert job_id

        # 3. Poll until DONE
        for _ in range(300):
            r = await client.get(f"{base_url}/v1/jobs/{job_id}", headers=headers)
            if r.status_code == 200:
                status = r.json().get("status")
                if status == "DONE":
                    break
                if status == "FAILED":
                    pytest.fail(f"Job failed: {r.json()}")
            await asyncio.sleep(2)
        else:
            pytest.fail("Job did not complete in time")

        # 4. Download TXT and SRT
        txt_resp = await client.get(f"{base_url}/v1/jobs/{job_id}/download/txt", headers=headers)
        assert txt_resp.status_code == 200
        assert len(txt_resp.content) > 0

        srt_resp = await client.get(f"{base_url}/v1/jobs/{job_id}/download/srt", headers=headers)
        assert srt_resp.status_code == 200
        assert len(srt_resp.content) > 0

        # 5. DOCX must return 403 for Free Tier
        docx_resp = await client.get(f"{base_url}/v1/jobs/{job_id}/download/docx", headers=headers)
        assert docx_resp.status_code == 403

        # 6. Second upload - should complete
        with open(test_audio_path, "rb") as f:
            upload2 = await client.post(
                f"{base_url}/v1/transcribe",
                headers=headers,
                files={"file": ("audio2.mp3", f, "audio/mpeg")},
            )
        assert upload2.status_code == 202
        job_id2 = upload2.json().get("job_id")
        for _ in range(300):
            r = await client.get(f"{base_url}/v1/jobs/{job_id2}", headers=headers)
            if r.status_code == 200 and r.json().get("status") == "DONE":
                break
            await asyncio.sleep(2)
        else:
            pytest.fail("Second job did not complete")

        # 7. Third upload - must return 429 (quota exceeded)
        with open(test_audio_path, "rb") as f:
            upload3 = await client.post(
                f"{base_url}/v1/transcribe",
                headers=headers,
                files={"file": ("audio3.mp3", f, "audio/mpeg")},
            )
        assert upload3.status_code == 429
        assert "Retry-After" in upload3.headers or "retry-after" in str(upload3.headers).lower()
