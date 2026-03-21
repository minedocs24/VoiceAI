"""Health and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.metrics import PREPROCESS_DURATION_SECONDS, PREPROCESS_TASKS_TOTAL
from app.models.schemas import DependencyStatus, HealthResponse

health_router = APIRouter(tags=["health"])
metrics_router = APIRouter(tags=["metrics"])


def _ffmpeg_available() -> bool:
    """Check if ffmpeg is in PATH."""
    import shutil

    return shutil.which("ffmpeg") is not None


def _ramdisk_writable() -> bool:
    """Check if ramdisk path is writable."""
    try:
        p = Path(settings.ramdisk_path)
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()
        return True
    except Exception:
        return False


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    """Health with dependency checks."""
    deps: list[DependencyStatus] = []

    ff_ok = _ffmpeg_available()
    deps.append(
        DependencyStatus(
            name="ffmpeg",
            status="ok" if ff_ok else "error",
            message=None if ff_ok else "ffmpeg not in PATH",
        )
    )

    ramdisk_ok = _ramdisk_writable()
    deps.append(
        DependencyStatus(
            name="ramdisk",
            status="ok" if ramdisk_ok else "error",
            message=None if ramdisk_ok else f"Cannot write to {settings.ramdisk_path}",
        )
    )

    status = "healthy" if all(d.status == "ok" for d in deps) else "unhealthy"
    resp = HealthResponse(status=status, dependencies=deps, timestamp=datetime.now(timezone.utc))

    if status == "unhealthy":
        return JSONResponse(status_code=503, content=resp.model_dump(mode="json"))
    return resp


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
