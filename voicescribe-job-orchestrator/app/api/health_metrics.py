"""Health and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.database import close_pool, get_pool
from app.core.redis_client import close_redis, get_redis
from app.models.schemas import DependencyStatus, HealthResponse

health_router = APIRouter(tags=["health"])
metrics_router = APIRouter(tags=["metrics"])


async def _db_ok() -> bool:
    try:
        pool = await get_pool()
        await pool.fetchval("SELECT 1")
        return True
    except Exception:
        return False


def _redis_ok() -> bool:
    try:
        r = get_redis()
        return r.ping()
    except Exception:
        return False


@health_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse | JSONResponse:
    """Health with dependency checks."""
    deps: list[DependencyStatus] = []

    db_ok = await _db_ok()
    deps.append(DependencyStatus(name="postgresql", status="ok" if db_ok else "error", message=None if db_ok else "Connection failed"))

    redis_ok = _redis_ok()
    deps.append(DependencyStatus(name="redis", status="ok" if redis_ok else "error", message=None if redis_ok else "Connection failed"))

    status = "healthy" if all(d.status == "ok" for d in deps) else "unhealthy"
    resp = HealthResponse(status=status, dependencies=deps, timestamp=datetime.now(timezone.utc))

    if status == "unhealthy":
        return JSONResponse(status_code=503, content=resp.model_dump(mode="json"))
    return resp


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    """Prometheus metrics."""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
