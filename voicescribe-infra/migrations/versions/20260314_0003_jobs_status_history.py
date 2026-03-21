"""Add status_history to jobs for transition metrics

Revision ID: 20260314_0003
Revises: 20260314_0002
Create Date: 2026-03-14 15:00:00
"""

from alembic import op

revision = "20260314_0003"
down_revision = "20260314_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS status_history JSONB DEFAULT '[]'::jsonb"
    )
    op.execute(
        "COMMENT ON COLUMN jobs.status_history IS 'History of status transitions with timestamps and stage duration'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS status_history")
