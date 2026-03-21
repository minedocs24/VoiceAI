"""FastAPI application - Transcription Engine Service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.health_metrics import health_router, metrics_router
from app.api.routers import router as transcription_router
from app.core.config import settings
from app.services.model_loader import load_model_once


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


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_model_once()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Transcription Engine API", version="0.1.0", lifespan=lifespan)

    app.include_router(transcription_router)
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
