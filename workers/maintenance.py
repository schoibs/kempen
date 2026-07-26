from __future__ import annotations

import argparse
import logging
import signal
import threading

from datetime import UTC, datetime, timedelta
from time import monotonic

from sqlalchemy import select

from app_config import get_settings
from domain.enums import CampaignStatus
from infrastructure import get_redis_client
from persistence.database import get_session_factory
from persistence.ids import new_resource_id
from persistence.models import Asset, Campaign, StorageCleanupAction
from storage import get_object_storage
from workers.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="campaign.cleanup_storage")
def cleanup_storage() -> dict[str, int]:
    """Delete only expired, database-owned objects and audit each action."""

    settings = get_settings()
    storage = get_object_storage()
    now = datetime.now(UTC)
    storage.configure_lifecycle(
        upload_retention_days=max(1, settings.unattached_upload_retention_sec // (24 * 60 * 60)),
        artifact_retention_days=max(1, settings.artifact_retention_sec // (24 * 60 * 60)),
    )
    deleted = 0
    failed = 0
    session = get_session_factory()()
    try:
        candidates = list(
            session.scalars(
                select(Asset)
                .outerjoin(Campaign, Campaign.id == Asset.campaign_id)
                .where(
                    Asset.status.in_(["pending_upload", "ready"]),
                    (
                        (Asset.status == "pending_upload")
                        & (Asset.expires_at.is_not(None))
                        & (Asset.expires_at <= now)
                    )
                    | (
                        (Asset.status == "ready")
                        & Asset.role.in_(["storyboard", "campaign_video"])
                        & (Asset.ready_at.is_not(None))
                        & (Asset.ready_at <= now - timedelta(seconds=settings.artifact_retention_sec))
                        & Campaign.status.in_(
                            [
                                CampaignStatus.SUCCEEDED.value,
                                CampaignStatus.FAILED.value,
                                CampaignStatus.CANCELLED.value,
                            ]
                        )
                    ),
                )
                .order_by(Asset.created_at, Asset.id)
                .limit(settings.cleanup_batch_size)
            )
        )
        for asset in candidates:
            original_status = asset.status
            reason = "orphan_upload" if original_status == "pending_upload" else "expired_artifact"
            asset.status = "cleanup_pending"
            session.commit()
            try:
                _validate_scoped_key(asset.object_key, asset.tenant_id)
                storage.delete_object(object_key=asset.object_key)
            except Exception as exc:
                session.rollback()
                current = session.get(Asset, asset.id)
                if current is not None and current.status == "cleanup_pending":
                    current.status = original_status
                session.add(
                    StorageCleanupAction(
                        id=new_resource_id("cln"),
                        tenant_id=asset.tenant_id,
                        asset_id=asset.id,
                        object_key=asset.object_key,
                        reason=reason,
                        status="failed",
                        error_message=type(exc).__name__,
                        created_at=now,
                    )
                )
                session.commit()
                failed += 1
                logger.warning("Storage cleanup failed asset_id=%s reason=%s", asset.id, reason)
                continue

            current = session.get(Asset, asset.id)
            if current is None:
                continue
            current.status = "deleted"
            current.deleted_at = now
            session.add(
                StorageCleanupAction(
                    id=new_resource_id("cln"),
                    tenant_id=current.tenant_id,
                    asset_id=current.id,
                    object_key=current.object_key,
                    reason=reason,
                    status="deleted",
                    created_at=now,
                )
            )
            session.commit()
            deleted += 1
    finally:
        session.close()

    _reconcile_active_quotas()
    return {"deleted": deleted, "failed": failed}


@celery_app.task(name="campaign.configure_storage_lifecycle")
def configure_storage_lifecycle() -> dict[str, str]:
    settings = get_settings()
    storage = get_object_storage()
    storage.ensure_bucket()
    storage.configure_lifecycle(
        upload_retention_days=max(1, settings.unattached_upload_retention_sec // (24 * 60 * 60)),
        artifact_retention_days=max(1, settings.artifact_retention_sec // (24 * 60 * 60)),
    )
    return {"status": "ok"}


def _reconcile_active_quotas() -> None:
    settings = get_settings()
    session = get_session_factory()()
    try:
        active = list(
            session.execute(
                select(Campaign.tenant_id, Campaign.id).where(
                    Campaign.status.in_(
                        [
                            CampaignStatus.QUEUED.value,
                            CampaignStatus.RUNNING.value,
                            CampaignStatus.CANCEL_REQUESTED.value,
                        ]
                    )
                )
            )
        )
    finally:
        session.close()
    redis = get_redis_client()
    tenants: dict[str, list[str]] = {}
    for tenant_id, campaign_id in active:
        tenants.setdefault(tenant_id, []).append(campaign_id)
    for tenant_id, campaign_ids in tenants.items():
        key = f"campaign:active:{tenant_id}"
        redis.delete(key)
        if campaign_ids:
            redis.sadd(key, *campaign_ids)
            redis.expire(key, settings.artifact_retention_sec)


def _validate_scoped_key(object_key: str, tenant_id: str) -> None:
    expected_prefix = f"tenants/{tenant_id}/"
    if not object_key.startswith(expected_prefix) or ".." in object_key:
        raise ValueError("Object key is outside the tenant scope.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run storage cleanup and quota reconciliation.")
    parser.add_argument("--once", action="store_true", help="Run one bounded cleanup pass.")
    args = parser.parse_args()
    settings = get_settings()
    stop_event = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())
    while not stop_event.is_set():
        started = monotonic()
        try:
            result = cleanup_storage()
            logger.info("Storage cleanup heartbeat deleted=%s failed=%s", result["deleted"], result["failed"])
        except Exception:
            logger.exception("Storage cleanup pass failed")
        if args.once:
            return
        logger.info("Storage cleanup pass duration_ms=%s", round((monotonic() - started) * 1000))
        stop_event.wait(settings.cleanup_interval_sec)


if __name__ == "__main__":
    main()
