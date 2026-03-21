"""Global exception handlers."""

from __future__ import annotations

import traceback
import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from structlog import get_logger

from app.models.schemas import ErrorResponse

logger = get_logger(__name__)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return standard ErrorResponse."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    tb = traceback.format_exc()
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        error=str(exc),
        traceback=tb,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="http_500",
            message="Internal server error",
            detail=None,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    """Handle HTTPException with standard ErrorResponse format."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    status_code = getattr(exc, "status_code", 500)
    detail_val = getattr(exc, "detail", None)
    if isinstance(detail_val, str):
        message = detail_val
        detail = None
    elif isinstance(detail_val, dict):
        message = detail_val.get("message", "Request failed")
        detail = str(detail_val) if len(str(detail_val)) < 500 else None
    else:
        message = "Request failed"
        detail = str(detail_val) if detail_val and len(str(detail_val)) < 500 else None
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=f"http_{status_code}", message=message, detail=detail).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""
    from fastapi.exceptions import HTTPException

    app.add_exception_handler(Exception, generic_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
