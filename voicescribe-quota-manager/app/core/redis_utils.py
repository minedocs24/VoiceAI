"""Redis utilities: TTL calculation, key format, atomic operations."""

from __future__ import annotations

from datetime import datetime, timezone


def redis_quota_key(tenant_id: str, date_utc: datetime | None = None) -> str:
    """Build Redis key for quota: quota:{tenant_id}:{YYYY-MM-DD}."""
    dt = date_utc or datetime.now(timezone.utc)
    return f"quota:{tenant_id}:{dt.strftime('%Y-%m-%d')}"


def seconds_until_midnight_utc(when: datetime | None = None) -> int:
    """
    Return seconds until midnight UTC of the current day.
    Edge case: at exactly midnight UTC, returns 86400 (next day).
    """
    dt = when or datetime.now(timezone.utc)
    # Next midnight: today + 1 day at 00:00:00
    next_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if dt >= next_midnight:
        # We're at or past midnight today - next midnight is tomorrow
        from datetime import timedelta

        next_midnight = next_midnight + timedelta(days=1)
    delta = next_midnight - dt
    return int(delta.total_seconds())


def usage_date_utc(when: datetime | None = None) -> str:
    """Return usage date as YYYY-MM-DD in UTC."""
    dt = when or datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%d")
