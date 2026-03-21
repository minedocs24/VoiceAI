"""FastAPI application - File Ingestion Service."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.health_metrics import health_router, metrics_router
from app.api.routers import router as ingestion_router
from app.core.config import settings
from app.core.database import close_pool, ensure_schema, init_pool
from app.core.redis_client import close_redis
from app.services.cleanup import cleanup_loop

_cleanup_stop = asyncio.Event()
_cleanup_task: asyncio.Task | None = None


def load_openapi_yaml() -> dict:
    """Load openapi.yaml as dict if available."""
    paths = [
        Path(__file__).resolve().parent.parent / "openapi.yaml",
        Path("openapi.yaml"),
    ]
    for path in paths:
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                return yaml.safe_load(handle)
    return {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Service startup and shutdown lifecycle."""
    Path(settings.storage_base_path).mkdir(parents=True, exist_ok=True)
    Path(settings.temp_upload_dir).mkdir(parents=True, exist_ok=True)

    await init_pool()
    await ensure_schema()

    global _cleanup_task
    _cleanup_task = asyncio.create_task(cleanup_loop(_cleanup_stop))

    yield

    _cleanup_stop.set()
    if _cleanup_task:
        await _cleanup_task

    await close_pool()
    await close_redis()


def create_app() -> FastAPI:
    """Create FastAPI app with custom OpenAPI serving."""
    app = FastAPI(
        title="File Ingestion API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(ingestion_router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"http_{exc.status_code}",
                "message": "Request failed",
                "detail": str(exc.detail),
            },
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_json():
        spec = load_openapi_yaml()
        if spec:
            return JSONResponse(content=spec)
        return JSONResponse(
            content=get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                routes=app.routes,
            )
        )

    return app


app = create_app()