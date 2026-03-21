from __future__ import annotations

from app.models.schemas import SegmentResult
from app.services.transcription import build_transcript_result


def test_build_transcript_result_sets_rtf():
    segments = [
        SegmentResult(start=0.0, end=1.0, text="ciao", confidence=0.9, words=[]),
    ]
    result = build_transcript_result(job_id="00000000-0000-0000-0000-000000000001", language="it", duration=10.0, inference_ms=200, segments=segments)

    assert result.job_id.endswith("0001")
    assert result.language == "it"
    assert result.rtf == 0.02
    assert len(result.segments) == 1
