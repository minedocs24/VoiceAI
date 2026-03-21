"""FastAPI application - Audio Preprocessor Service."""

from __future__ import annotations

import yaml
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.health_metrics import health_router, metrics_router
from app.api.routers import router as preprocess_router


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


def create_app() -> FastAPI:
    """Create FastAPI app."""
    app = FastAPI(
        title="Audio Preprocessor API",
        version="0.1.0",
    )

    app.include_router(preprocess_router)
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
