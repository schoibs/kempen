from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


JSON_VALUE = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_tenant_created", "tenant_id", "created_at", "id"),
        Index("ix_campaigns_tenant_status_created", "tenant_id", "status", "created_at"),
        Index("ix_campaigns_status_stage_updated", "status", "current_stage", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_image_asset_id: Mapped[str] = mapped_column(
        ForeignKey(
            "assets.id",
            name="fk_campaigns_product_image_asset",
            use_alter=True,
        ),
        nullable=False,
    )
    campaign_theme: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    target_duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pipeline_version: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_VALUE, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_retryable: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CampaignStageRun(Base):
    __tablename__ = "campaign_stage_runs"
    __table_args__ = (
        UniqueConstraint("campaign_id", "stage", "attempt", name="uq_stage_attempt"),
        Index("ix_stage_runs_campaign_stage", "campaign_id", "stage"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    run_token: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    provider_name: Mapped[str | None] = mapped_column(String(64))
    provider_request_id: Mapped[str | None] = mapped_column(String(256))
    provider_status: Mapped[str | None] = mapped_column(String(128))
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    error_retryable: Mapped[bool | None] = mapped_column(Boolean)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_assets_size_positive"),
        Index("ix_assets_tenant_owner", "tenant_id", "owner_id"),
        Index("ix_assets_campaign_role", "campaign_id", "role"),
        Index(
            "uq_assets_ready_campaign_role",
            "campaign_id",
            "role",
            unique=True,
            postgresql_where=text("status = 'ready' AND campaign_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CampaignEvent(Base):
    __tablename__ = "campaign_events"
    __table_args__ = (
        UniqueConstraint("campaign_id", "sequence", name="uq_campaign_event_sequence"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_VALUE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "route", "idempotency_key", name="uq_idempotency_scope"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DispatchOutbox(Base):
    __tablename__ = "dispatch_outbox"
    __table_args__ = (Index("ix_dispatch_outbox_available", "dispatched_at", "available_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(128), nullable=False)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("campaign_stage_runs.id", ondelete="CASCADE"),
    )
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StorageCleanupAction(Base):
    __tablename__ = "storage_cleanup_actions"
    __table_args__ = (
        Index("ix_storage_cleanup_actions_created", "created_at"),
        Index("ix_storage_cleanup_actions_asset", "asset_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(64))
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
