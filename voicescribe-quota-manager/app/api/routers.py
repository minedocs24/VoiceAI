"""API routers for quota, analytics, health, metrics."""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from structlog import get_logger

from app.api.dependencies import validate_tenant_id, verify_internal_token
from app.core.config import get_quota_config
from app.models.schemas import (
    AnalyticsItem,
    AnalyticsResponse,
    ErrorResponse,
    QuotaCheckResponse,
    QuotaConsumeResponse,
    QuotaRollbackResponse,
    QuotaStatusResponse,
)
from app.services.quota_service import check_quota, consume_quota, rollback_quota

from app.api.health_metrics import QUOTA_CHECK_TOTAL, QUOTA_CONSUME_TOTAL

logger = get_logger(__name__)

quota_router = APIRouter(prefix="/quota", tags=["quota"])
analytics_router = APIRouter(tags=["analytics"])


def get_limit() -> int:
    """Get daily limit from config or env."""
    import os
    env_limit = os.getenv("FREE_TIER_DAILY_LIMIT")
    if env_limit:
        try:
            return int(env_limit)
        except ValueError:
            pass
    cfg = get_quota_config()
    return cfg.get("quota", {}).get("daily_limit", 2)


@quota_router.get(
    "/check/{tenant_id}",
    response_model=QuotaCheckResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def check(
    request: Request,
    tenant_id: Annotated[str, Depends(validate_tenant_id)],
    _: Annotated[None, Depends(verify_internal_token)],
):
    """Check quota without consuming."""
    start = time.perf_counter()
    limit = get_limit()
    result = await check_quota(tenant_id, limit)
    duration_ms = (time.perf_counter() - start) * 1000
    QUOTA_CHECK_TOTAL.labels(result="allowed" if result.allowed else "denied").inc()
    logger.info(
        "quota_check",
        tenant_id=tenant_id,
        operation="check",
        result="allowed" if result.allowed else "denied",
        duration_ms=round(duration_ms, 2),
    )
    return QuotaCheckResponse(
        allowed=result.allowed,
        used=result.used,
        limit=result.limit,
        remaining=max(0, result.limit - result.used),
    )


@quota_router.post(
    "/consume/{tenant_id}",
    response_model=QuotaConsumeResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        429: {"model": QuotaConsumeResponse},
        503: {"model": ErrorResponse},
    },
)
async def consume(
    request: Request,
    tenant_id: Annotated[str, Depends(validate_tenant_id)],
    _: Annotated[None, Depends(verify_internal_token)],
):
    """Consume one unit of quota."""
    start = time.perf_counter()
    limit = get_limit()
    result = await consume_quota(tenant_id, limit)
    duration_ms = (time.perf_counter() - start) * 1000
    consume_result = "success" if result.consumed else ("quota_exceeded" if not result.allowed else "error")
    QUOTA_CONSUME_TOTAL.labels(result=consume_result).inc()
    logger.info(
        "quota_consume",
        tenant_id=tenant_id,
        operation="consume",
        result=consume_result,
        duration_ms=round(duration_ms, 2),
    )
    resp = QuotaConsumeResponse(
        consumed=result.consumed,
        used=result.used,
        limit=result.limit,
        remaining=max(0, result.limit - result.used),
    )
    if not result.consumed and not result.allowed:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content=resp.model_dump())
    return resp


@quota_router.get(
    "/status/{tenant_id}",
    response_model=QuotaStatusResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def status(
    request: Request,
    tenant_id: Annotated[str, Depends(validate_tenant_id)],
    _: Annotated[None, Depends(verify_internal_token)],
):
    """Get quota status for tenant."""
    start = time.perf_counter()
    limit = get_limit()
    result = await check_quota(tenant_id, limit)
    duration_ms = (time.perf_counter() - start) * 1000
    from datetime import datetime
    usage_date = datetime.now(timezone.utc).date()
    reset_at = datetime(usage_date.year, usage_date.month, usage_date.day, 0, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    reset_at = reset_at + timedelta(days=1)
    logger.info(
        "quota_status",
        tenant_id=tenant_id,
        operation="status",
        result="ok",
        duration_ms=round(duration_ms, 2),
    )
    return QuotaStatusResponse(
        tenant_id=tenant_id,
        usage_date=usage_date,
        used_count=result.used,
        limit=result.limit,
        remaining=max(0, result.limit - result.used),
        reset_at=reset_at,
    )


@quota_router.post(
    "/rollback/{tenant_id}",
    response_model=QuotaRollbackResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def rollback(
    request: Request,
    tenant_id: Annotated[str, Depends(validate_tenant_id)],
    _: Annotated[None, Depends(verify_internal_token)],
):
    """Rollback one consumed unit."""
    start = time.perf_counter()
    limit = get_limit()
    result = await rollback_quota(tenant_id, limit)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "quota_rollback",
        tenant_id=tenant_id,
        operation="rollback",
        result="ok",
        duration_ms=round(duration_ms, 2),
    )
    return QuotaRollbackResponse(
        rolled_back=result.used < limit,
        used=result.used,
        limit=result.limit,
        message="Quota restored",
    )


@analytics_router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    responses={401: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def analytics(
    _: Annotated[None, Depends(verify_internal_token)],
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    min_exceeded: int | None = Query(None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Analytics for upgrade candidates."""
    from app.core.database import _pool
    pool = _pool
    if pool is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable")
    cfg = get_quota_config()
    threshold = cfg.get("quota", {}).get("upgrade_candidate_threshold", 5)
    min_ex = min_exceeded if min_exceeded is not None else threshold

    # Build query with positional params
    conditions = ["quota_exceeded_attempts >= $1"]
    params: list = [min_ex]
    n = 2
    if from_date:
        conditions.append(f"usage_date >= ${n}")
        params.append(from_date)
        n += 1
    if to_date:
        conditions.append(f"usage_date <= ${n}")
        params.append(to_date)
        n += 1
    where = " AND ".join(conditions)

    # Count total
    count_query = f"SELECT COUNT(*) FROM free_tier_usage WHERE {where}"
    total = await pool.fetchval(count_query, *params)

    # Fetch page
    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    limit_idx, offset_idx = n, n + 1
    query = f"""
        SELECT tenant_id, usage_date, used_count, quota_exceeded_attempts
        FROM free_tier_usage
        WHERE {where}
        ORDER BY quota_exceeded_attempts DESC
        LIMIT ${limit_idx} OFFSET ${offset_idx}
    """
    rows = await pool.fetch(query, *params)

    items = [
        AnalyticsItem(
            tenant_id=r["tenant_id"],
            usage_date=r["usage_date"],
            used_count=r["used_count"],
            quota_exceeded_attempts=r["quota_exceeded_attempts"],
        )
        for r in rows
    ]
    return AnalyticsResponse(items=items, total=total, page=page, page_size=page_size)
