from __future__ import annotations

from app.models.schemas import SegmentResult
from app.services.transcription import deduplicate_overlap_segments


def test_deduplicate_overlap_prefers_higher_confidence():
    segments = [
        SegmentResult(start=0.0, end=5.0, text="ciao mondo", confidence=0.65, words=[]),
        SegmentResult(start=4.0, end=7.0, text="ciao mondo", confidence=0.92, words=[]),
        SegmentResult(start=8.0, end=9.0, text="fine", confidence=0.80, words=[]),
    ]

    deduped = deduplicate_overlap_segments(segments)

    assert len(deduped) == 2
    assert deduped[0].confidence == 0.92
    assert deduped[1].text == "fine"
