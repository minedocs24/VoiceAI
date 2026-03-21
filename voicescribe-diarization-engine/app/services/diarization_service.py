"""Servizio di diarizzazione: esecuzione pipeline Pyannote e merge con trascrizione."""

from __future__ import annotations

import time
from pathlib import Path

from structlog import get_logger

from app.core.config import settings
from app.core.gpu_state import loaded_model, runtime_state
from app.services.merge import (
    SpeakerSegment,
    build_speakers_list,
    merge_transcript_with_diarization,
)

logger = get_logger(__name__)


class DiarizationUnavailableError(RuntimeError):
    """Modello non caricato o token non valido."""

    pass


def _get_pipeline():
    """Ritorna il pipeline caricato o solleva DiarizationUnavailableError."""
    if loaded_model is None or not runtime_state.ready:
        raise DiarizationUnavailableError(
            runtime_state.last_error or "Model not loaded. HuggingFace token invalid or model unavailable."
        )
    return loaded_model


def diarize_audio(
    audio_path: str,
    segments: list[dict] | None = None,
    job_id: str = "",
    language: str = "unknown",
    duration: float = 0.0,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> dict:
    """
    Esegue diarizzazione su un file audio.
    Se segments è fornito, fa il merge e restituisce DiarizationResult (TranscriptResult + speaker).
    Se segments è None, restituisce solo la timeline speaker (per uso standalone).
    """
    pipeline = _get_pipeline()
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    start = time.perf_counter()
    kwargs: dict = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    if min_speakers is not None:
        kwargs["min_speakers"] = min_speakers
    if max_speakers is not None:
        kwargs["max_speakers"] = max_speakers

    diarization = pipeline(str(path), **kwargs)

    # Filtra segmenti speaker troppo brevi (rumore)
    min_dur = settings.min_speaker_segment_duration
    speaker_timeline: list[SpeakerSegment] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        if (turn.end - turn.start) >= min_dur:
            speaker_timeline.append(
                SpeakerSegment(start=turn.start, end=turn.end, speaker=speaker)
            )

    inference_s = time.perf_counter() - start
    inference_ms = int(inference_s * 1000)
    rtf = inference_s / duration if duration and duration > 0 else 0.0

    if segments is None or len(segments) == 0:
        # Solo timeline speaker (nessun merge)
        from app.services.merge import TextSegmentWithSpeaker

        fake_segments = [
            TextSegmentWithSpeaker(s.start, s.end, "", s.speaker, None)
            for s in speaker_timeline
        ]
        return {
            "job_id": job_id,
            "language": language,
            "duration": duration,
            "rtf": rtf,
            "inference_ms": inference_ms,
            "segments": [],
            "speakers": build_speakers_list(fake_segments),
            "speaker_timeline": [
                {"start": s.start, "end": s.end, "speaker": s.speaker}
                for s in speaker_timeline
            ],
        }

    # Merge con segmenti trascrizione
    merged = merge_transcript_with_diarization(segments, speaker_timeline)
    speakers_stats = build_speakers_list(merged)

    out_segments = []
    for m in merged:
        seg_dict = {
            "start": m.start,
            "end": m.end,
            "text": m.text,
            "speaker": m.speaker,
        }
        if m.extra:
            for k, v in m.extra.items():
                if k not in seg_dict:
                    seg_dict[k] = v
        out_segments.append(seg_dict)

    return {
        "job_id": job_id,
        "language": language,
        "duration": duration,
        "rtf": rtf,
        "inference_ms": inference_ms,
        "segments": out_segments,
        "speakers": speakers_stats,
    }
