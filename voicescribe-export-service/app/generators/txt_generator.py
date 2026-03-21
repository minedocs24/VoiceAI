"""TXT format generator - plain text with optional speaker labels and timestamps."""

from __future__ import annotations

import re
from typing import Union

from app.models.schemas import DiarizationResult, TranscriptResult

ExportInput = Union[TranscriptResult, DiarizationResult]


def _normalize_text(text: str) -> str:
    """Remove multiple spaces, capitalize first letter of segment."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


def _format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


class TxtGenerator:
    """Produces plain text from transcript/diarization."""

    def generate(
        self,
        data: ExportInput,
        *,
        include_timestamps: bool = False,
    ) -> str:
        """
        Generate TXT content.
        - With diarization: [SPEAKER_XX] on dedicated line before each speaker change
        - Without diarization: segments separated by blank lines
        - Timestamps optional via include_timestamps
        """
        lines: list[str] = []
        prev_speaker: str | None = None
        has_diarization = isinstance(data, DiarizationResult) and any(
            s.speaker for s in data.segments
        )

        for seg in data.segments:
            text = _normalize_text(seg.text)
            if not text:
                continue

            if has_diarization and seg.speaker:
                if seg.speaker != prev_speaker:
                    lines.append(f"[{seg.speaker}]")
                    prev_speaker = seg.speaker
                if include_timestamps:
                    ts = _format_timestamp(seg.start)
                    lines.append(f"{ts} {text}")
                else:
                    lines.append(text)
            else:
                if include_timestamps:
                    ts = _format_timestamp(seg.start)
                    lines.append(f"{ts} {text}")
                else:
                    lines.append(text)
                if not has_diarization:
                    lines.append("")  # Blank line between segments

        return "\n".join(lines).strip()
