"""FastAPI application - Job Orchestrator."""

from __future__ import annotations

import yaml
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.callbacks import router as callbacks_router
from app.api.health_metrics import health_router, metrics_router
from app.api.jobs import router as jobs_router
from app.api.queue_stats import router as queue_router
from app.core.database import close_pool, get_pool


def load_openapi_yaml() -> dict:
    paths = [
        Path(__file__).resolve().parent.parent / "openapi.yaml",
        Path("openapi.yaml"),
    ]
    for path in paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
    return {}


async def lifespan(app: FastAPI):
    """Startup: init DB pool. Shutdown: close pool and redis."""
    try:
        await get_pool()
    except Exception:
        pass
    yield
    from app.core.redis_client import close_redis
    await close_pool()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(title="Job Orchestrator API", version="0.1.0", lifespan=lifespan)

    app.include_router(jobs_router)
    app.include_router(callbacks_router)
    app.include_router(queue_router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    @app.exception_handler(HTTPException)
    async def http_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": f"http_{exc.status_code}", "message": "Request failed", "detail": str(exc.detail)},
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_json():
        spec = load_openapi_yaml()
        if spec:
            return JSONResponse(content=spec)
        return JSONResponse(content=get_openapi(title=app.title, version=app.version, openapi_version=app.openapi_version, routes=app.routes))

    return app


app = create_app()
