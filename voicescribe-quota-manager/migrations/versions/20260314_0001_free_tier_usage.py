"""free_tier_usage table for quota-manager

Revision ID: 20260314_0001
Revises:
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260314_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tier enum if not exists (required for tenants FK)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tier_at_creation AS ENUM ('FREE', 'PRO', 'ENTERPRISE');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    # Create tenants if not exists (required for free_tier_usage FK)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            tier tier_at_creation NOT NULL DEFAULT 'FREE',
            api_key_hash VARCHAR(128),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """)
    # Create free_tier_usage
    op.execute("""
        CREATE TABLE IF NOT EXISTS free_tier_usage (
            tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id) ON UPDATE CASCADE ON DELETE CASCADE,
            usage_date DATE NOT NULL,
            used_count INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
            quota_exceeded_attempts INTEGER NOT NULL DEFAULT 0 CHECK (quota_exceeded_attempts >= 0),
            reset_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (tenant_id, usage_date)
        );
        CREATE INDEX IF NOT EXISTS idx_free_tier_usage_date ON free_tier_usage(usage_date DESC);
        CREATE INDEX IF NOT EXISTS idx_free_tier_usage_exceeded ON free_tier_usage(quota_exceeded_attempts DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS free_tier_usage;")
    # Do not drop tenants - may be shared with other services
