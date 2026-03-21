"""Unit test per l'algoritmo di merge trascrizione + diarizzazione."""

from __future__ import annotations

import pytest

from app.services.merge import (
    SpeakerSegment,
    build_speakers_list,
    merge_transcript_with_diarization,
    TextSegmentWithSpeaker,
)


def test_merge_single_segment_single_speaker():
    """Un segmento Whisper sovrapposto a un solo speaker."""
    segments = [{"start": 0.0, "end": 2.0, "text": "Ciao"}]
    timeline = [SpeakerSegment(0.0, 3.0, "SPEAKER_00")]
    result = merge_transcript_with_diarization(segments, timeline)
    assert len(result) == 1
    assert result[0].speaker == "SPEAKER_00"
    assert result[0].text == "Ciao"


def test_merge_no_overlap_speaker_null():
    """Segmento Whisper che non si sovrappone a nessuno speaker -> speaker null."""
    segments = [{"start": 10.0, "end": 12.0, "text": "Silenzio"}]
    timeline = [
        SpeakerSegment(0.0, 5.0, "SPEAKER_00"),
        SpeakerSegment(5.0, 8.0, "SPEAKER_01"),
    ]
    result = merge_transcript_with_diarization(segments, timeline)
    assert len(result) == 1
    assert result[0].speaker is None


def test_merge_two_speakers_max_overlap_wins():
    """Segmento Whisper sovrapposto a due speaker: vince chi ha sovrapposizione maggiore."""
    # [0, 5] SPEAKER_00, [5, 10] SPEAKER_01
    # Segmento Whisper [3, 7]: overlap con SPEAKER_00 = 2s, con SPEAKER_01 = 2s -> pari merito
    # Implementazione: primo con overlap massimo vince (ordine timeline)
    segments = [{"start": 3.0, "end": 7.0, "text": "Test"}]
    timeline = [
        SpeakerSegment(0.0, 5.0, "SPEAKER_00"),
        SpeakerSegment(5.0, 10.0, "SPEAKER_01"),
    ]
    result = merge_transcript_with_diarization(segments, timeline)
    assert len(result) == 1
    # Overlap SPEAKER_00: min(5,7)-max(3,0)=2, SPEAKER_01: min(10,7)-max(5,3)=2 -> stesso overlap
    assert result[0].speaker in ("SPEAKER_00", "SPEAKER_01")


def test_merge_fifty_fifty_overlap_deterministic():
    """Segmento al 50% su due speaker: assegnazione deterministica (primo che vince per overlap)."""
    segments = [{"start": 2.0, "end": 4.0, "text": "Meta"}]
    timeline = [
        SpeakerSegment(0.0, 3.0, "SPEAKER_00"),  # overlap 1s
        SpeakerSegment(3.0, 6.0, "SPEAKER_01"),   # overlap 1s
    ]
    result = merge_transcript_with_diarization(segments, timeline)
    assert len(result) == 1
    # Entrambi overlap 1.0; il primo in ordine con overlap massimo vince
    assert result[0].speaker == "SPEAKER_00"


def test_merge_multiple_segments_dedupe_speakers():
    """Lista speakers deduplicata, ordine prima apparizione, conteggio interventi."""
    segments = [
        {"start": 0.0, "end": 1.0, "text": "A"},
        {"start": 1.5, "end": 2.5, "text": "B"},
        {"start": 3.0, "end": 4.0, "text": "C"},
    ]
    timeline = [
        SpeakerSegment(0.0, 2.0, "SPEAKER_00"),
        SpeakerSegment(2.0, 5.0, "SPEAKER_01"),
    ]
    merged = merge_transcript_with_diarization(segments, timeline)
    speakers_list = build_speakers_list(merged)
    assert len(speakers_list) == 2
    assert speakers_list[0]["speaker"] == "SPEAKER_00"
    assert speakers_list[0]["utterance_count"] == 2  # A e B
    assert speakers_list[1]["speaker"] == "SPEAKER_01"
    assert speakers_list[1]["utterance_count"] == 1  # C


def test_merge_preserves_extra_fields():
    """Campi extra (confidence, words) preservati in extra."""
    segments = [
        {"start": 0.0, "end": 1.0, "text": "Hi", "confidence": 0.95, "words": []},
    ]
    timeline = [SpeakerSegment(0.0, 2.0, "SPEAKER_00")]
    result = merge_transcript_with_diarization(segments, timeline)
    assert result[0].extra is not None
    assert result[0].extra.get("confidence") == 0.95
    assert result[0].extra.get("words") == []


def test_build_speakers_list_empty():
    """Nessun speaker -> lista vuota."""
    assert build_speakers_list([]) == []
    assert build_speakers_list([TextSegmentWithSpeaker(0, 1, "x", None)]) == []


def test_merge_empty_timeline_all_null():
    """Timeline speaker vuota -> tutti i segmenti con speaker null."""
    segments = [
        {"start": 0.0, "end": 1.0, "text": "A"},
        {"start": 1.0, "end": 2.0, "text": "B"},
    ]
    result = merge_transcript_with_diarization(segments, [])
    assert all(s.speaker is None for s in result)
    assert build_speakers_list(result) == []
