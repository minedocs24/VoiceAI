"""Health e metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.gpu_state import runtime_state
from app.models.schemas import DependencyStatus, HealthResponse

health_router = APIRouter(tags=["health"])
metrics_router = APIRouter(tags=["metrics"])


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    deps = [
        DependencyStatus(
            name="model",
            status="ok" if runtime_state.ready else "error",
            message=None if runtime_state.ready else (runtime_state.last_error or "Model not loaded"),
        ),
    ]
    status = "healthy" if all(dep.status == "ok" for dep in deps) else "unhealthy"
    payload = HealthResponse(status=status, dependencies=deps)
    if status != "healthy":
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
    return payload


@metrics_router.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
