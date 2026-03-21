"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import RequestIdMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.api.routers import auth_router, jobs_router
from app.api.routers.health import health_router
from app.api.routers.websocket import ws_router
from app.api.routers.api_docs import api_docs_router
from app.core.config import get_gateway_config, settings
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware
from app.core.error_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: setup and teardown."""
    configure_logging(settings.log_level)
    yield
    # Teardown if needed


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    gateway_config = get_gateway_config()
    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

    app = FastAPI(
        title="VoiceScribe API Gateway",
        version="0.1.0",
        description="Single public entry point for VoiceScribe AI",
        docs_url="/docs" if settings.swagger_ui_enabled else None,
        redoc_url="/redoc" if settings.swagger_ui_enabled else None,
        openapi_url="/openapi.json" if settings.swagger_ui_enabled else None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, config=gateway_config.get("rate_limit", {}))

    register_exception_handlers(app)

    app.include_router(auth_router, prefix="/v1/auth", tags=["auth"])
    app.include_router(jobs_router, prefix="/v1", tags=["jobs"])
    app.include_router(ws_router, tags=["websocket"])
    app.include_router(api_docs_router, tags=["docs"])
    app.include_router(health_router, tags=["health"])

    return app


app = create_app()
