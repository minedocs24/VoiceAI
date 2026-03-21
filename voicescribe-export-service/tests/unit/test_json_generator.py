"""Unit tests for JSON generator."""

from __future__ import annotations

import json

import pytest

from app.generators.json_generator import JsonGenerator
from app.models.schemas import DiarizationResult, TranscriptResult


def test_json_serialization(sample_transcript: TranscriptResult):
    gen = JsonGenerator()
    out = gen.generate(
        sample_transcript,
        job_id="job-1",
        tenant_id="t1",
        tier="PRO",
    )
    data = json.loads(out)
    assert data["job_id"] == "job-1"
    assert data["tenant_id"] == "t1"
    assert data["tier"] == "PRO"
    assert "processed_at" in data
    assert "segments" in data
    assert len(data["segments"]) == 2


def test_json_diarization(sample_diarization: DiarizationResult):
    gen = JsonGenerator()
    out = gen.generate(
        sample_diarization,
        job_id="job-1",
        tenant_id="t1",
        tier="PRO",
    )
    data = json.loads(out)
    assert data["speakers"] is not None
    assert len(data["speakers"]) == 2
    assert data["segments"][0]["speaker"] == "SPEAKER_00"


def test_json_pretty_print(sample_transcript: TranscriptResult):
    gen = JsonGenerator()
    out = gen.generate(sample_transcript, job_id="x", tenant_id="t", tier="FREE")
    assert out.startswith("{\n")
    assert "  " in out  # indent
