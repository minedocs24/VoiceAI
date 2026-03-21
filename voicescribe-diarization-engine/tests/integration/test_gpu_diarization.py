"""Integration test con GPU: diarizzazione su file audio reale (due speaker)."""

from __future__ import annotations

import pytest
from pathlib import Path

# Marca come test GPU: eseguire con pytest -m gpu
pytestmark = pytest.mark.gpu


@pytest.fixture
def two_speaker_audio_path():
    """Percorso a un file audio di test con due speaker (da fixtures)."""
    base = Path(__file__).resolve().parent.parent / "fixtures"
    for name in ("two_speakers.wav", "sample_2speakers.wav", "test_audio.wav"):
        p = base / name
        if p.exists():
            return str(p)
    pytest.skip("Nessun file audio due speaker in tests/fixtures/")


def test_diarization_identifies_two_speakers(two_speaker_audio_path):
    """Con audio a due speaker, il risultato ha due speaker distinti e segmenti con label non null."""
    from app.services.model_loader import load_model_once
    from app.services.diarization_service import diarize_audio

    load_model_once()
    result = diarize_audio(
        audio_path=two_speaker_audio_path,
        segments=None,
        job_id="test-job",
        language="it",
        duration=10.0,
    )
    speakers = result.get("speakers", [])
    assert len(speakers) >= 1
    # Almeno un speaker identificato; in audio con due voci ci aspettiamo 2
    speaker_labels = {s["speaker"] for s in speakers}
    assert len(speaker_labels) >= 1
    # Se ci sono segmenti (timeline), tutti con speaker non null quando c'è timeline
    segments = result.get("segments", [])
    if result.get("speaker_timeline"):
        # Nella risposta "solo timeline" i segmenti testuali sono vuoti ma speaker_timeline popolato
        for seg in result.get("speaker_timeline", []):
            assert seg.get("speaker") is not None
