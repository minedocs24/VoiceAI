"""Health and metrics endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from structlog import get_logger

from app.core.database import _pool
from app.core.redis_client import redis_ping
from app.models.schemas import DependencyStatus, HealthResponse

logger = get_logger(__name__)

health_router = APIRouter(tags=["health"])
metrics_router = APIRouter(tags=["metrics"])

# Prometheus metrics
QUOTA_CHECK_TOTAL = Counter(
    "quota_check_total",
    "Total quota check operations",
    ["result"],
)
QUOTA_CONSUME_TOTAL = Counter(
    "quota_consume_total",
    "Total quota consume operations",
    ["result"],
)
REDIS_LATENCY = Histogram(
    "quota_redis_operation_seconds",
    "Redis operation latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
PG_FALLBACK_TOTAL = Counter(
    "quota_pg_fallback_total",
    "PostgreSQL fallback/write failures",
    ["operation"],
)
ACTIVE_COUNTERS = Gauge(
    "quota_active_counters",
    "Number of active Redis quota keys",
)


@health_router.get("/health", response_model=HealthResponse)
async def health():
    """Health check with dependency status. Returns 503 when unhealthy."""
    deps = []
    redis_ok = await redis_ping()
    deps.append(
        DependencyStatus(
            name="redis",
            status="ok" if redis_ok else "error",
            message=None if redis_ok else "Connection failed",
        )
    )
    pg_ok = False
    if _pool:
        try:
            await _pool.fetchval("SELECT 1")
            pg_ok = True
        except Exception as e:
            logger.warning("PostgreSQL health check failed", error=str(e))
    deps.append(
        DependencyStatus(
            name="postgresql",
            status="ok" if pg_ok else "error",
            message=None if pg_ok else "Connection failed",
        )
    )

    errors = sum(1 for d in deps if d.status == "error")
    if errors == 0:
        status = "healthy"
    elif redis_ok:
        status = "degraded"
    else:
        status = "unhealthy"

    resp = HealthResponse(
        status=status,
        dependencies=deps,
        timestamp=datetime.now(timezone.utc),
    )
    if status == "unhealthy":
        return JSONResponse(status_code=503, content=resp.model_dump())
    return resp


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics."""
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
