"""Add storage cleanup audit records for operational maintenance jobs."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_0005"
down_revision: str | None = "20260725_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "storage_cleanup_actions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("asset_id", sa.String(length=64)),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_storage_cleanup_actions_created", "storage_cleanup_actions", ["created_at"])
    op.create_index("ix_storage_cleanup_actions_asset", "storage_cleanup_actions", ["asset_id"])


def downgrade() -> None:
    op.drop_index("ix_storage_cleanup_actions_asset", table_name="storage_cleanup_actions")
    op.drop_index("ix_storage_cleanup_actions_created", table_name="storage_cleanup_actions")
    op.drop_table("storage_cleanup_actions")
