"""API routes per Diarization Engine."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.gpu_state import runtime_state
from app.core.security import validate_job_id, verify_internal_token
from app.models.schemas import DiarizationResult, DiarizeRequest, ModelStatusResponse
from app.services.diarization_service import DiarizationUnavailableError, diarize_audio

router = APIRouter(tags=["diarization"])


@router.post("/diarize", response_model=DiarizationResult)
async def post_diarize(
    body: DiarizeRequest,
    _: Annotated[None, Depends(verify_internal_token)] = None,
) -> DiarizationResult:
    """
    Diarizza un file audio. Se `segments` è fornito, allinea la timeline speaker
    alla trascrizione (merge). Se `segments` è omesso, restituisce solo la
    timeline speaker (uso standalone senza trascrizione).
    """
    if not runtime_state.ready:
        raise HTTPException(
            status_code=503,
            detail="Diarization unavailable. HuggingFace token invalid or model not loaded. See docs/HUGGINGFACE-SETUP.md.",
        )
    validate_job_id(body.job_id)
    try:
        result = diarize_audio(
            audio_path=body.input_path,
            segments=body.segments,
            job_id=body.job_id,
            language=body.language,
            duration=body.duration,
            num_speakers=body.num_speakers,
            min_speakers=body.min_speakers,
            max_speakers=body.max_speakers,
        )
    except DiarizationUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Costruisce response con segmenti in formato Pydantic
    segments_out = []
    for s in result.get("segments", []):
        seg = {
            "start": s["start"],
            "end": s["end"],
            "text": s.get("text", ""),
            "confidence": s.get("confidence", 0.0),
            "words": s.get("words", []),
            "speaker": s.get("speaker"),
        }
        segments_out.append(seg)
    speakers_out = [
        {"speaker": x["speaker"], "utterance_count": x["utterance_count"]}
        for x in result.get("speakers", [])
    ]
    return DiarizationResult(
        job_id=result["job_id"],
        language=result["language"],
        duration=result["duration"],
        rtf=result["rtf"],
        inference_ms=result["inference_ms"],
        segments=segments_out,
        speakers=speakers_out,
    )


@router.get("/models/status", response_model=ModelStatusResponse)
async def get_models_status() -> ModelStatusResponse:
    """Stato del modello: caricato, token HF valido (mai in chiaro), VRAM, tempo di caricamento."""
    return ModelStatusResponse(
        model_loaded=runtime_state.ready,
        hf_token_valid=runtime_state.hf_token_valid,
        vram_used_mb=runtime_state.model_vram_used_mb,
        load_seconds=runtime_state.load_seconds,
        model_name=runtime_state.model_name,
        service_ready=runtime_state.ready,
    )
