"""FastAPI application - Quota Manager Service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.limiter import limiter
from structlog import get_logger

from app.api.health_metrics import health_router, metrics_router
from app.api.routers import analytics_router, quota_router
from app.core.config import load_quota_config
from app.core.database import init_pool, close_pool
from app.core.redis_client import get_redis, close_redis

logger = get_logger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    cfg = load_quota_config()
    db_cfg = cfg.get("database", {})
    pool_size = db_cfg.get("pool_size", 5)
    pool_timeout = db_cfg.get("pool_timeout", 30)
    await init_pool(max_size=pool_size, command_timeout=pool_timeout)
    yield
    await close_pool()
    await close_redis()


def load_openapi_yaml() -> dict:
    """Load openapi.yaml as dict."""
    paths = [
        Path(__file__).resolve().parent.parent / "openapi.yaml",
        Path("openapi.yaml"),
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f)
    return {}


def create_app() -> FastAPI:
    """Create FastAPI app with custom OpenAPI from openapi.yaml."""
    app = FastAPI(
        title="Quota Manager API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Routers
    app.include_router(quota_router)
    app.include_router(analytics_router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    # Rate limit on quota endpoints (internal, but defense in depth)
    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_json():
        """Serve OpenAPI schema from openapi.yaml (source of truth)."""
        spec = load_openapi_yaml()
        if spec:
            return JSONResponse(content=spec)
        # Fallback to generated
        return JSONResponse(content=get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            routes=app.routes,
        ))

    return app


app = create_app()
