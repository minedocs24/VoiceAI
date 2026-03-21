"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.models.schemas import DiarizationResult, SpeakerStats, TranscriptResult, TranscriptSegment


@pytest.fixture
def sample_transcript() -> TranscriptResult:
    """TranscriptResult without diarization."""
    return TranscriptResult(
        job_id="550e8400-e29b-41d4-a716-446655440000",
        language="it",
        duration=10.0,
        rtf=0.05,
        inference_ms=500,
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Buongiorno a tutti."),
            TranscriptSegment(start=2.5, end=5.0, text="Grazie per essere qui."),
        ],
    )


@pytest.fixture
def sample_diarization() -> DiarizationResult:
    """DiarizationResult with speakers."""
    return DiarizationResult(
        job_id="550e8400-e29b-41d4-a716-446655440000",
        language="it",
        duration=10.0,
        rtf=0.05,
        inference_ms=500,
        segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Buongiorno a tutti.", speaker="SPEAKER_00"),
            TranscriptSegment(start=2.5, end=5.0, text="Grazie per essere qui.", speaker="SPEAKER_01"),
        ],
        speakers=[
            SpeakerStats(speaker="SPEAKER_00", utterance_count=1),
            SpeakerStats(speaker="SPEAKER_01", utterance_count=1),
        ],
    )


@pytest.fixture
def sample_diarization_long_segment() -> DiarizationResult:
    """Segment > 80 chars for SRT splitting test."""
    long_text = "A" * 100
    return DiarizationResult(
        job_id="test-job",
        language="en",
        duration=10.0,
        segments=[
            TranscriptSegment(start=0.0, end=5.0, text=long_text, speaker="SPEAKER_00"),
        ],
        speakers=[SpeakerStats(speaker="SPEAKER_00", utterance_count=1)],
    )


@pytest.fixture
def temp_output_dir():
    """Temporary directory for output files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
