"""Unit tests for Pydantic schemas."""

import pytest
from datetime import date, datetime, timezone

from app.models.schemas import (
    QuotaCheckResponse,
    QuotaConsumeResponse,
    QuotaStatusResponse,
    QuotaRollbackResponse,
    ErrorResponse,
    AnalyticsResponse,
    AnalyticsItem,
)


def test_quota_check_response():
    r = QuotaCheckResponse(allowed=True, used=1, limit=2, remaining=1)
    assert r.allowed is True
    assert r.remaining == 1


def test_quota_consume_response():
    r = QuotaConsumeResponse(consumed=True, used=1, limit=2, remaining=1)
    assert r.consumed is True


def test_error_response():
    r = ErrorResponse(error="NOT_FOUND", message="Tenant not found")
    assert r.error == "NOT_FOUND"


def test_analytics_response():
    items = [AnalyticsItem(tenant_id="t1", usage_date=date.today(), used_count=2, quota_exceeded_attempts=5)]
    r = AnalyticsResponse(items=items, total=1, page=1, page_size=20)
    assert len(r.items) == 1
    assert r.items[0].quota_exceeded_attempts == 5
