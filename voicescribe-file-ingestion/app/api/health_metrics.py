"""Health and metrics endpoints."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.core.database import db_ping
from app.core.metrics import DISK_SPACE_BYTES
from app.core.redis_client import redis_ping
from app.models.schemas import DependencyStatus, HealthResponse
from app.services.probe import ffmpeg_available

health_router = APIRouter(tags=["health"])
metrics_router = APIRouter(tags=["metrics"])


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    """Health with dependency checks and degraded state on low disk."""
    deps: list[DependencyStatus] = []

    fs_ok = True
    fs_msg = None
    try:
        usage = shutil.disk_usage(settings.storage_base_path)
        DISK_SPACE_BYTES.labels(kind="total").set(usage.total)
        DISK_SPACE_BYTES.labels(kind="used").set(usage.used)
        DISK_SPACE_BYTES.labels(kind="free").set(usage.free)
    except Exception as exc:
        fs_ok = False
        fs_msg = str(exc)
        usage = None

    deps.append(DependencyStatus(name="filesystem", status="ok" if fs_ok else "error", message=fs_msg))

    db_ok = await db_ping()
    deps.append(DependencyStatus(name="postgresql", status="ok" if db_ok else "error", message=None if db_ok else "Connection failed"))

    redis_ok = await redis_ping()
    deps.append(DependencyStatus(name="redis", status="ok" if redis_ok else "error", message=None if redis_ok else "Connection failed"))

    ff_ok = ffmpeg_available()
    deps.append(DependencyStatus(name="ffmpeg", status="ok" if ff_ok else "error", message=None if ff_ok else "ffprobe not available in PATH"))

    errors = sum(1 for d in deps if d.status == "error")
    status = "healthy"

    if usage is not None:
        used_pct = (usage.used / usage.total) * 100 if usage.total else 100
        if used_pct >= settings.health_disk_degraded_threshold_pct:
            status = "degraded"
            deps.append(
                DependencyStatus(
                    name="disk_threshold",
                    status="error",
                    message=(
                        f"Disk usage {used_pct:.2f}% is above threshold "
                        f"{settings.health_disk_degraded_threshold_pct}%"
                    ),
                )
            )

    if errors > 0 and status != "degraded":
        status = "unhealthy"

    resp = HealthResponse(status=status, dependencies=deps, timestamp=datetime.now(timezone.utc))

    if status == "unhealthy":
        return JSONResponse(status_code=503, content=resp.model_dump(mode="json"))
    return resp


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)