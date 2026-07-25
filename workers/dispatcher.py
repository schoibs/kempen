from __future__ import annotations

import argparse
import logging
import signal
import threading

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select

from app_config import get_settings
from domain.enums import CampaignStage, CampaignStatus, StageStatus
from infrastructure import check_database_and_migrations, check_redis
from logging_config import configure_logging
from persistence.database import get_session_factory
from persistence.ids import new_resource_id
from persistence.models import Campaign, CampaignStageRun, DispatchOutbox
from workers.celery_app import celery_app


logger = logging.getLogger(__name__)


class Dispatcher:
    """Publish transactional outbox records and repair lost broker messages."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._stop_event = threading.Event()

    def check_dependencies(self) -> None:
        check_database_and_migrations()
        check_redis()

    def run(self, *, once: bool = False) -> None:
        while not self._stop_event.is_set():
            try:
                self.check_dependencies()
                repaired = self.reconcile()
                published = self.publish_available()
            except Exception:
                logger.exception("Dispatcher dependency check failed; will retry.")
                if once:
                    raise
            else:
                logger.info(
                    "Dispatcher heartbeat: environment=%s fake_provider_mode=%s repaired=%s published=%s",
                    self.settings.environment,
                    self.settings.fake_provider_mode,
                    repaired,
                    published,
                )
            if once:
                return
            self._stop_event.wait(self.settings.dispatcher_interval_sec)

    def stop(self, *_: object) -> None:
        self._stop_event.set()

    def publish_available(self, *, limit: int = 50) -> int:
        """Publish pending records after commit; duplicate delivery is harmless to workers."""

        published = 0
        session = get_session_factory()()
        try:
            for _ in range(limit):
                now = datetime.now(UTC)
                with session.begin():
                    outbox = session.scalar(
                        select(DispatchOutbox)
                        .where(
                            DispatchOutbox.dispatched_at.is_(None),
                            DispatchOutbox.available_at <= now,
                        )
                        .order_by(DispatchOutbox.available_at, DispatchOutbox.id)
                        .with_for_update(skip_locked=True)
                        .limit(1)
                    )
                    if outbox is None:
                        break
                    celery_app.send_task(
                        outbox.task_type,
                        kwargs={
                            "campaign_id": outbox.campaign_id,
                            "stage_run_id": outbox.stage_run_id,
                        },
                        queue=_queue_for_stage_run(session, outbox.stage_run_id),
                    )
                    outbox.delivery_attempts += 1
                    outbox.dispatched_at = now
                    published += 1
        finally:
            session.close()
        return published

    def reconcile(self, *, limit: int = 50) -> int:
        """Requeue due work and expired stage leases whose delivery may be lost."""

        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=self.settings.dispatcher_reconcile_after_sec)
        repaired = 0
        session = get_session_factory()()
        try:
            candidates = list(
                session.scalars(
                    select(CampaignStageRun)
                    .join(Campaign, Campaign.id == CampaignStageRun.campaign_id)
                    .where(
                        Campaign.status.in_(
                            [
                                CampaignStatus.QUEUED.value,
                                CampaignStatus.RUNNING.value,
                                CampaignStatus.CANCEL_REQUESTED.value,
                            ]
                        ),
                        Campaign.current_stage == CampaignStageRun.stage,
                        or_(
                            CampaignStageRun.status == StageStatus.PENDING.value,
                            (
                                CampaignStageRun.status == StageStatus.WAITING_EXTERNAL.value,
                                (CampaignStageRun.next_poll_at.is_(None))
                                | (CampaignStageRun.next_poll_at <= now),
                            ),
                            (
                                CampaignStageRun.status == StageStatus.RUNNING.value,
                                (CampaignStageRun.lease_expires_at.is_(None))
                                | (CampaignStageRun.lease_expires_at <= now),
                            ),
                        ),
                    )
                    .order_by(CampaignStageRun.updated_at, CampaignStageRun.id)
                    .limit(limit)
                )
            )
            for stage_run in candidates:
                latest_dispatch = session.scalar(
                    select(func.max(DispatchOutbox.dispatched_at)).where(
                        DispatchOutbox.stage_run_id == stage_run.id
                    )
                )
                has_pending_outbox = session.scalar(
                    select(DispatchOutbox.id)
                    .where(
                        DispatchOutbox.stage_run_id == stage_run.id,
                        DispatchOutbox.dispatched_at.is_(None),
                    )
                    .limit(1)
                )
                if has_pending_outbox is not None or latest_dispatch is None or latest_dispatch > cutoff:
                    continue
                session.add(
                    DispatchOutbox(
                        id=new_resource_id("obx"),
                        task_type="campaign.run_stage",
                        campaign_id=stage_run.campaign_id,
                        stage_run_id=stage_run.id,
                        available_at=now,
                        delivery_attempts=0,
                        created_at=now,
                    )
                )
                repaired += 1
            if repaired:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return repaired


def _queue_for_stage_run(session: object, stage_run_id: str | None) -> str:
    if stage_run_id is None:
        return "planning"
    stage_run = getattr(session, "get")(CampaignStageRun, stage_run_id)
    if stage_run is None:
        return "planning"
    media_stages = {
        CampaignStage.STORYBOARD_GENERATION.value,
        CampaignStage.VIDEO_SUBMISSION.value,
        CampaignStage.VIDEO_POLL.value,
        CampaignStage.VIDEO_FINALIZE.value,
    }
    return "media" if stage_run.stage in media_stages else "planning"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the campaign dispatcher shell.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check dependencies once and exit.",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.log_level)
    dispatcher = Dispatcher()
    signal.signal(signal.SIGTERM, dispatcher.stop)
    signal.signal(signal.SIGINT, dispatcher.stop)
    dispatcher.run(once=args.once)


if __name__ == "__main__":
    main()
