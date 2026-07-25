"""Align server-default timestamp columns with the persistence model.

Revision ID: 20260725_0003
Revises: 20260725_0002
Create Date: 2026-07-25
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_0003"
down_revision: str | None = "20260725_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TIMESTAMP_COLUMNS = (
    ("assets", "created_at"),
    ("campaign_events", "created_at"),
    ("campaign_stage_runs", "updated_at"),
    ("campaigns", "created_at"),
    ("campaigns", "updated_at"),
    ("dispatch_outbox", "created_at"),
    ("idempotency_records", "created_at"),
)


def upgrade() -> None:
    for table_name, column_name in TIMESTAMP_COLUMNS:
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )


def downgrade() -> None:
    for table_name, column_name in TIMESTAMP_COLUMNS:
        op.alter_column(
            table_name,
            column_name,
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )
