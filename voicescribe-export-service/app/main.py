"""FastAPI application - Export Service."""

from __future__ import annotations

import yaml
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.cleanup import router as cleanup_router
from app.api.health_metrics import health_router, metrics_router
from app.api.routers import router as export_router
from app.api.webhook import router as webhook_router


def load_openapi_yaml() -> dict:
    paths = [
        Path(__file__).resolve().parent.parent / "openapi.yaml",
        Path("openapi.yaml"),
    ]
    for path in paths:
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                return yaml.safe_load(handle)
    return {}


def create_app() -> FastAPI:
    app = FastAPI(title="Export Service API", version="0.1.0")
    app.include_router(export_router)
    app.include_router(cleanup_router)
    app.include_router(webhook_router)
    app.include_router(health_router)
    app.include_router(metrics_router)

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_json():
        spec = load_openapi_yaml()
        if spec:
            return JSONResponse(content=spec)
        return JSONResponse(content=app.openapi())

    return app


app = create_app()
