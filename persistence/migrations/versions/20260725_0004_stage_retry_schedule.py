"""Store scheduled automatic stage retries separately from video polling.

Revision ID: 20260725_0004
Revises: 20260725_0003
Create Date: 2026-07-25
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_0004"
down_revision: str | None = "20260725_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "campaign_stage_runs",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_column("campaign_stage_runs", "next_attempt_at")
