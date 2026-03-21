from __future__ import annotations

import os

import pytest

from app.services.model_loader import load_model_once
from app.services.transcription import transcribe_audio


@pytest.mark.gpu
def test_gpu_transcription_wer_and_rtf():
    if os.getenv("RUN_GPU_TESTS", "false").lower() != "true":
        pytest.skip("GPU tests disabled")

    fixture = "tests/fixtures/sample_it_20s.wav"
    if not os.path.exists(fixture):
        pytest.skip("Fixture audio missing")

    model = load_model_once()
    result = transcribe_audio(
        job_id="00000000-0000-0000-0000-000000000123",
        audio_path=fixture,
        model=model,
    )

    assert result.rtf < 0.05
    assert result.language in {"it", "it-IT", "unknown"}
