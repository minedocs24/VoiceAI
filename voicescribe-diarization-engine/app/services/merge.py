"""Merge trascrizione (segmenti Whisper) con timeline speaker Pyannote.

Algoritmo: per ogni segmento Whisper, assegna lo speaker con massima sovrapposizione temporale.
Funzione pura, testabile senza GPU.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SpeakerSegment:
    """Segmento temporale con etichetta speaker."""

    start: float
    end: float
    speaker: str


@dataclass
class TextSegmentWithSpeaker:
    """Segmento di testo con speaker assegnato."""

    start: float
    end: float
    text: str
    speaker: str | None
    # Campi opzionali da trascrizione (confidence, words, ecc.)
    extra: dict[str, Any] | None = None


def _overlap_length(seg_start: float, seg_end: float, sp_start: float, sp_end: float) -> float:
    """Lunghezza della sovrapposizione tra [seg_start, seg_end] e [sp_start, sp_end]."""
    overlap_start = max(seg_start, sp_start)
    overlap_end = min(seg_end, sp_end)
    if overlap_end <= overlap_start:
        return 0.0
    return overlap_end - overlap_start


def merge_transcript_with_diarization(
    segments: list[dict[str, Any]],
    speaker_timeline: list[SpeakerSegment],
) -> list[TextSegmentWithSpeaker]:
    """
    Associa ogni segmento di trascrizione allo speaker con massima sovrapposizione temporale.

    - segments: lista di dict con almeno 'start', 'end', 'text'; altri campi preservati in extra.
    - speaker_timeline: lista di segmenti speaker (start, end, speaker).
    - Ritorna segmenti con campo speaker (str o None se nessuna sovrapposizione).
    """
    result: list[TextSegmentWithSpeaker] = []

    for seg in segments:
        start = float(seg["start"])
        end = float(seg["end"])
        text = seg.get("text", "")
        extra = {k: v for k, v in seg.items() if k not in ("start", "end", "text")}
        if extra:
            extra = dict(extra)
        else:
            extra = None

        best_speaker: str | None = None
        best_overlap: float = 0.0

        for sp in speaker_timeline:
            overlap = _overlap_length(start, end, sp.start, sp.end)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = sp.speaker

        result.append(
            TextSegmentWithSpeaker(
                start=start,
                end=end,
                text=text,
                speaker=best_speaker,
                extra=extra,
            )
        )

    return result


def build_speakers_list(
    segments_with_speaker: list[TextSegmentWithSpeaker],
) -> list[dict[str, Any]]:
    """
    Costruisce la lista degli speaker unici con conteggio interventi.
    Ordine: prima apparizione nel documento.
    """
    order: list[str] = []
    counts: dict[str, int] = {}

    for s in segments_with_speaker:
        if s.speaker is None:
            continue
        if s.speaker not in counts:
            order.append(s.speaker)
            counts[s.speaker] = 0
        counts[s.speaker] += 1

    return [{"speaker": sp, "utterance_count": counts[sp]} for sp in order]
