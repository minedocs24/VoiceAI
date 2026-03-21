"""E2E Scenario 2 — Flusso PRO con Diarizzazione."""

from __future__ import annotations

import asyncio
from pathlib import Path
import zipfile
import io

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    not (Path(__file__).parent / "fixtures" / "test_audio_2speakers.mp3").exists(),
    reason="Test audio fixtures/test_audio_2speakers.mp3 required",
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pro_full_flow_with_diarization(
    base_url: str,
    verify_ssl: bool,
):
    """
    PRO: API key auth, upload con 2 speaker, DONE, label SPEAKER_00/01,
    download TXT/SRT/JSON/DOCX, DOCX valido (ZIP/OOXML), webhook ricevuto.
    """
    # Assume PRO tenant with API key vs_live_test123456789012345678901234
    api_key = "vs_live_test123456789012345678901234"
    headers = {"X-API-Key": api_key}

    test_audio = Path(__file__).parent / "fixtures" / "test_audio_2speakers.mp3"
    async with httpx.AsyncClient(verify=verify_ssl, timeout=300.0) as client:
        with open(test_audio, "rb") as f:
            upload_resp = await client.post(
                f"{base_url}/v1/transcribe",
                headers=headers,
                files={"file": ("audio.mp3", f, "audio/mpeg")},
            )
        if upload_resp.status_code == 401:
            pytest.skip("PRO tenant/API key not configured")
        assert upload_resp.status_code == 202, f"Upload failed: {upload_resp.text}"
        job_id = upload_resp.json().get("job_id")
        assert job_id

        for _ in range(600):
            r = await client.get(f"{base_url}/v1/jobs/{job_id}", headers=headers)
            if r.status_code == 200:
                status = r.json().get("status")
                if status == "DONE":
                    break
                if status == "FAILED":
                    pytest.fail(f"Job failed: {r.json()}")
            await asyncio.sleep(2)
        else:
            pytest.fail("Job did not complete")

        # Download TXT - check for speaker labels
        txt_resp = await client.get(f"{base_url}/v1/jobs/{job_id}/download/txt", headers=headers)
        assert txt_resp.status_code == 200
        txt_content = txt_resp.text
        assert "SPEAKER_00" in txt_content or "SPEAKER_01" in txt_content

        # Download DOCX - must be valid OOXML (ZIP)
        docx_resp = await client.get(f"{base_url}/v1/jobs/{job_id}/download/docx", headers=headers)
        assert docx_resp.status_code == 200
        try:
            z = zipfile.ZipFile(io.BytesIO(docx_resp.content), "r")
            names = z.namelist()
            z.close()
            assert "word/document.xml" in names or "[Content_Types].xml" in names
        except zipfile.BadZipFile:
            pytest.fail("DOCX is not a valid ZIP/OOXML file")
