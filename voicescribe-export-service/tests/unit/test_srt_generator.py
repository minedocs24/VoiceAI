"""Unit tests for SRT generator."""

from __future__ import annotations

import re

import pytest

from app.generators.srt_generator import SrtGenerator
from app.models.schemas import DiarizationResult, TranscriptResult, TranscriptSegment


def _srt_timestamp_format(s: str) -> bool:
    """Check HH:MM:SS,mmm format."""
    return bool(re.match(r"\d{2}:\d{2}:\d{2},\d{3}", s))


def test_srt_simple(sample_transcript: TranscriptResult):
    gen = SrtGenerator()
    out = gen.generate(sample_transcript)
    lines = out.split("\n")
    assert len(lines) >= 6  # 2 subtitles * 3 lines each (num, time, text)
    assert lines[0] == "1"
    assert " --> " in lines[1]
    assert _srt_timestamp_format(lines[1].split(" --> ")[0])
    assert _srt_timestamp_format(lines[1].split(" --> ")[1])


def test_srt_progressive_numbering(sample_diarization: DiarizationResult):
    gen = SrtGenerator()
    out = gen.generate(sample_diarization)
    assert "1\n" in out
    assert "2\n" in out


def test_srt_speaker_prefix(sample_diarization: DiarizationResult):
    gen = SrtGenerator()
    out = gen.generate(sample_diarization)
    assert "SPEAKER_00:" in out or "SPEAKER_00" in out
    assert "Buongiorno" in out


def test_srt_splits_long_segment(sample_diarization_long_segment: DiarizationResult):
    gen = SrtGenerator(max_chars_per_line=80, max_duration_seconds=3.0)
    out = gen.generate(sample_diarization_long_segment)
    # Should have multiple subtitles due to splitting
    lines = out.split("\n")
    assert len(lines) > 5  # at least 2 subtitles: one per char-split chunk


def test_srt_timestamp_format():
    srt = SrtGenerator()
    data = TranscriptResult(
        job_id="x",
        language="en",
        duration=1.0,
        segments=[
            TranscriptSegment(start=1.5, end=5.0, text="Hello"),
        ],
    )
    out = srt.generate(data)
    assert "00:00:01,500" in out or "01,500" in out
    assert "00:00:05,000" in out or "05,000" in out
