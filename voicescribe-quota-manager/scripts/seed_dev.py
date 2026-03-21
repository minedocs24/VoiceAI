#!/usr/bin/env python3
"""Seed development database with test tenants and usage data."""

import asyncio
import os
import sys
from datetime import date, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg


async def main():
    url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url or "postgresql" not in url:
        print("DATABASE_URL not set or invalid")
        sys.exit(1)

    conn = await asyncpg.connect(url)

    try:
        # Insert test tenants
        await conn.execute("""
            INSERT INTO tenants (id, name, tier, is_active)
            VALUES
                ('tenant-free-001', 'Free Tier Test', 'FREE', true),
                ('tenant-free-002', 'Another Free User', 'FREE', true),
                ('tenant-pro-001', 'Pro User', 'PRO', true)
            ON CONFLICT (id) DO NOTHING;
        """)
        print("Tenants seeded")

        # Insert test free_tier_usage
        today = date.today()
        yesterday = today - timedelta(days=1)
        await conn.execute("""
            INSERT INTO free_tier_usage (tenant_id, usage_date, used_count, quota_exceeded_attempts, reset_at)
            VALUES
                ('tenant-free-001', $1, 1, 2, $1::timestamp + interval '1 day'),
                ('tenant-free-001', $2, 2, 0, $2::timestamp + interval '1 day'),
                ('tenant-free-002', $1, 0, 5, $1::timestamp + interval '1 day')
            ON CONFLICT (tenant_id, usage_date) DO UPDATE SET
                used_count = EXCLUDED.used_count,
                quota_exceeded_attempts = EXCLUDED.quota_exceeded_attempts,
                updated_at = NOW();
        """, today, yesterday)
        print("free_tier_usage seeded")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
