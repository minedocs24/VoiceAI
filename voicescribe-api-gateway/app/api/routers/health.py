"""Health and metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

health_router = APIRouter()


@health_router.get("/health")
async def health():
    """Health check - no auth required."""
    return {"status": "healthy", "service": "api-gateway"}


@health_router.get("/metrics")
async def metrics():
    """Prometheus metrics - no auth required."""
    from prometheus_client import REGISTRY
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )
