"""Unit tests for TXT generator."""

from __future__ import annotations

import pytest

from app.generators.txt_generator import TxtGenerator
from app.models.schemas import DiarizationResult, TranscriptResult, TranscriptSegment


def test_txt_without_speaker(sample_transcript: TranscriptResult):
    gen = TxtGenerator()
    out = gen.generate(sample_transcript)
    assert "Buongiorno a tutti." in out
    assert "Grazie per essere qui." in out
    assert "[SPEAKER" not in out
    assert "\n\n" in out  # blank line between segments


def test_txt_with_speaker(sample_diarization: DiarizationResult):
    gen = TxtGenerator()
    out = gen.generate(sample_diarization)
    assert "[SPEAKER_00]" in out
    assert "[SPEAKER_01]" in out
    assert "Buongiorno a tutti." in out
    assert "Grazie per essere qui." in out


def test_txt_with_timestamps(sample_transcript: TranscriptResult):
    gen = TxtGenerator()
    out = gen.generate(sample_transcript, include_timestamps=True)
    assert "00:00:00.000" in out or "00:00:00" in out
    assert "Buongiorno" in out


def test_txt_normalizes_spaces():
    data = TranscriptResult(
        job_id="x",
        language="it",
        duration=1.0,
        segments=[
            TranscriptSegment(start=0, end=1, text="  multiple   spaces   here  "),
        ],
    )
    gen = TxtGenerator()
    out = gen.generate(data)
    assert "  " not in out or out.count("  ") == 0
    assert "Multiple" in out or "multiple" in out
