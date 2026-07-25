"""Add campaign, stage, asset, event, idempotency, and outbox tables.

Revision ID: 20260725_0002
Revises: 20260724_0001
Create Date: 2026-07-25
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260725_0002"
down_revision: str | None = "20260724_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jsonb = postgresql.JSONB(astext_type=sa.Text())

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("campaign_id", sa.String(length=64)),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("size_bytes > 0", name="ck_assets_size_positive"),
    )
    op.create_index("ix_assets_tenant_owner", "assets", ["tenant_id", "owner_id"])
    op.create_index("ix_assets_campaign_role", "assets", ["campaign_id", "role"])
    op.create_index(
        "uq_assets_ready_campaign_role",
        "assets",
        ["campaign_id", "role"],
        unique=True,
        postgresql_where=sa.text("status = 'ready' AND campaign_id IS NOT NULL"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("product_image_asset_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_theme", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("target_duration_sec", sa.Integer(), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_stage", sa.String(length=64), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=128), nullable=False),
        sa.Column("provider_config_snapshot", jsonb, nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("error_retryable", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_image_asset_id"],
            ["assets.id"],
            name="fk_campaigns_product_image_asset",
        ),
    )
    op.create_index("ix_campaigns_tenant_created", "campaigns", ["tenant_id", "created_at", "id"])
    op.create_index(
        "ix_campaigns_tenant_status_created",
        "campaigns",
        ["tenant_id", "status", "created_at"],
    )
    op.create_index(
        "ix_campaigns_status_stage_updated",
        "campaigns",
        ["status", "current_stage", "updated_at"],
    )
    op.create_foreign_key(
        "fk_assets_campaign",
        "assets",
        "campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "campaign_stage_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("run_token", sa.String(length=128)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("output_json", jsonb),
        sa.Column("provider_name", sa.String(length=64)),
        sa.Column("provider_request_id", sa.String(length=256)),
        sa.Column("provider_status", sa.String(length=128)),
        sa.Column("provider_metadata", jsonb),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("error_retryable", sa.Boolean()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("next_poll_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "stage", "attempt", name="uq_stage_attempt"),
    )
    op.create_index(
        "ix_stage_runs_campaign_stage",
        "campaign_stage_runs",
        ["campaign_id", "stage"],
    )

    op.create_table(
        "campaign_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", jsonb),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("campaign_id", "sequence", name="uq_campaign_event_sequence"),
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("route", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "route", "idempotency_key", name="uq_idempotency_scope"),
    )

    op.create_table(
        "dispatch_outbox",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_type", sa.String(length=128), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("stage_run_id", sa.String(length=64)),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_run_id"], ["campaign_stage_runs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_dispatch_outbox_available",
        "dispatch_outbox",
        ["dispatched_at", "available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_dispatch_outbox_available", table_name="dispatch_outbox")
    op.drop_table("dispatch_outbox")
    op.drop_table("idempotency_records")
    op.drop_table("campaign_events")
    op.drop_index("ix_stage_runs_campaign_stage", table_name="campaign_stage_runs")
    op.drop_table("campaign_stage_runs")
    op.drop_constraint("fk_assets_campaign", "assets", type_="foreignkey")
    op.drop_index("ix_campaigns_status_stage_updated", table_name="campaigns")
    op.drop_index("ix_campaigns_tenant_status_created", table_name="campaigns")
    op.drop_index("ix_campaigns_tenant_created", table_name="campaigns")
    op.drop_table("campaigns")
    op.drop_index("ix_assets_campaign_role", table_name="assets")
    op.drop_index("uq_assets_ready_campaign_role", table_name="assets")
    op.drop_index("ix_assets_tenant_owner", table_name="assets")
    op.drop_table("assets")
