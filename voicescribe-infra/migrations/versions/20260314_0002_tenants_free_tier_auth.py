"""Add email and password_hash to tenants for Free Tier login

Revision ID: 20260314_0002
Revises: 20260314_0001
Create Date: 2026-03-14 14:00:00
"""

from alembic import op

revision = "20260314_0002"
down_revision = "20260314_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE")
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")
    op.execute(
        "COMMENT ON COLUMN tenants.email IS 'Email per login Free Tier (nullable per PRO/Enterprise)'"
    )
    op.execute(
        "COMMENT ON COLUMN tenants.password_hash IS 'Hash bcrypt password (nullable per PRO/Enterprise)'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenants_email ON tenants(email) WHERE email IS NOT NULL"
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_tenants_email;
        ALTER TABLE tenants DROP COLUMN IF EXISTS email;
        ALTER TABLE tenants DROP COLUMN IF EXISTS password_hash;
        """
    )
