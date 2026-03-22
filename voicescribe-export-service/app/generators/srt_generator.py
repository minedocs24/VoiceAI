"""SRT format generator - subtitles compatible with VLC, YouTube."""

from __future__ import annotations

from typing import Union

from app.models.schemas import DiarizationResult, TranscriptResult

ExportInput = Union[TranscriptResult, DiarizationResult]


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _split_segment_for_srt(
    start: float,
    end: float,
    text: str,
    speaker: str | None,
    max_chars: int = 80,
    max_duration: float = 3.0,
) -> list[tuple[float, float, str]]:
    """
    Split a segment into sub-segments if too long.
    Returns list of (start, end, text) for each subtitle.
    """
    duration = end - start
    has_speaker = bool(speaker)
    prefix = f"{speaker}: " if has_speaker else ""

    if duration <= max_duration and len(text) <= max_chars:
        return [(start, end, f"{prefix}{text}".strip())]

    # Split by words
    words = text.split()
    if not words:
        return [(start, end, prefix.strip() or "...")]

    # If there's a single word that exceeds max_chars, split by characters instead
    effective_max = max_chars - len(prefix)
    if effective_max < 10:
        effective_max = 10  # always allow at least 10 chars of text
    if len(words) == 1 and len(text) > max_chars:
        chunks = [text[i : i + effective_max] for i in range(0, len(text), effective_max)]
        total_chars = len(text)
        sub_segments: list[tuple[float, float, str]] = []
        seg_start = start
        for chunk in chunks:
            chunk_duration = duration * len(chunk) / total_chars
            seg_end = seg_start + chunk_duration
            txt = f"{prefix}{chunk}".strip() if has_speaker else chunk
            sub_segments.append((seg_start, seg_end, txt))
            seg_start = seg_end
        # align last segment end with original end
        if sub_segments:
            last = sub_segments[-1]
            sub_segments[-1] = (last[0], end, last[2])
        return sub_segments

    sub_segments = []
    current_text: list[str] = []
    current_start = start
    word_duration = duration / len(words) if words else 0

    for i, w in enumerate(words):
        current_text.append(w)
        candidate = " ".join(current_text)
        seg_duration = (i + 1) * word_duration
        seg_end = start + seg_duration

        if len(candidate) >= max_chars or seg_duration >= max_duration:
            txt = f"{prefix}{candidate}".strip() if has_speaker else candidate
            sub_segments.append((current_start, seg_end, txt))
            current_text = []
            current_start = seg_end

    if current_text:
        candidate = " ".join(current_text)
        txt = f"{prefix}{candidate}".strip() if has_speaker else candidate
        sub_segments.append((current_start, end, txt))

    return sub_segments


class SrtGenerator:
    """Produces SRT subtitles with splitting for long segments."""

    def __init__(self, max_chars_per_line: int = 80, max_duration_seconds: float = 3.0):
        self.max_chars = max_chars_per_line
        self.max_duration = max_duration_seconds

    def generate(self, data: ExportInput) -> str:
        """Generate SRT content with progressive numbering and HH:MM:SS,mmm format."""
        sub_entries: list[tuple[int, float, float, str]] = []
        idx = 1

        has_diarization = isinstance(data, DiarizationResult) and any(
            s.speaker for s in data.segments
        )

        for seg in data.segments:
            text = seg.text.strip()
            if not text:
                continue

            speaker = seg.speaker if has_diarization else None
            parts = _split_segment_for_srt(
                seg.start,
                seg.end,
                text,
                speaker,
                max_chars=self.max_chars,
                max_duration=self.max_duration,
            )
            for s, e, t in parts:
                sub_entries.append((idx, s, e, t))
                idx += 1

        lines: list[str] = []
        for num, start, end, text in sub_entries:
            lines.append(str(num))
            lines.append(
                f"{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}"
            )
            lines.append(text)
            lines.append("")

        return "\n".join(lines).strip()
