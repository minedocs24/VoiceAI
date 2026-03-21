"""Health, GPU status and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.gpu_state import runtime_state
from app.models.schemas import DependencyStatus, GPUStatusResponse, HealthResponse
from app.services.transcription import _torch_cuda_info

health_router = APIRouter(tags=["health"])
metrics_router = APIRouter(tags=["metrics"])


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    deps: list[DependencyStatus] = []

    model_loaded = runtime_state.ready
    deps.append(
        DependencyStatus(
            name="model",
            status="ok" if model_loaded else "error",
            message=None if model_loaded else runtime_state.last_error or "Model not loaded",
        )
    )

    status = "healthy" if all(dep.status == "ok" for dep in deps) else "unhealthy"
    payload = HealthResponse(status=status, dependencies=deps, timestamp=datetime.now(timezone.utc))
    if status != "healthy":
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
    return payload


@health_router.get("/gpu/status", response_model=GPUStatusResponse)
async def gpu_status() -> GPUStatusResponse:
    free_mb, total_mb = _torch_cuda_info()
    used_mb = max(total_mb - free_mb, 0.0)
    return GPUStatusResponse(
        model_name=runtime_state.model_name,
        compute_type=runtime_state.compute_type,
        cuda_version=runtime_state.cuda_version,
        vram_total_gb=total_mb / 1024,
        vram_used_gb=used_mb / 1024,
        vram_free_gb=free_mb / 1024,
        last_rtf=runtime_state.last_rtf,
        ready_for_new_job=(not runtime_state.busy and runtime_state.ready),
        service_ready=runtime_state.ready,
    )


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
