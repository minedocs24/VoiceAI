"""Unit tests for Redis TTL and key utilities."""

from datetime import datetime, timezone, timedelta

import pytest

from app.core.redis_utils import (
    redis_quota_key,
    seconds_until_midnight_utc,
    usage_date_utc,
)


class TestRedisQuotaKey:
    def test_key_format(self):
        key = redis_quota_key("tenant-123")
        assert key.startswith("quota:tenant-123:")
        assert len(key.split(":")[-1]) == 10  # YYYY-MM-DD

    def test_key_with_date(self):
        dt = datetime(2026, 3, 14, 15, 30, 0, tzinfo=timezone.utc)
        key = redis_quota_key("t1", dt)
        assert key == "quota:t1:2026-03-14"


class TestSecondsUntilMidnightUtc:
    def test_midday(self):
        dt = datetime(2026, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        secs = seconds_until_midnight_utc(dt)
        assert secs == 12 * 3600

    def test_one_second_before_midnight(self):
        dt = datetime(2026, 3, 14, 23, 59, 59, tzinfo=timezone.utc)
        secs = seconds_until_midnight_utc(dt)
        assert secs == 1

    def test_at_midnight(self):
        dt = datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc)
        secs = seconds_until_midnight_utc(dt)
        assert secs == 86400

    def test_early_morning(self):
        dt = datetime(2026, 3, 14, 1, 0, 0, tzinfo=timezone.utc)
        secs = seconds_until_midnight_utc(dt)
        assert secs == 23 * 3600


class TestUsageDateUtc:
    def test_format(self):
        dt = datetime(2026, 3, 14, 12, 0, 0, tzinfo=timezone.utc)
        assert usage_date_utc(dt) == "2026-03-14"
