from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from persistence.models import Asset, Campaign, CampaignStageRun, IdempotencyRecord


class CampaignRepository:
    """Scoped campaign reads shared by the HTTP API and worker transitions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_owned(
        self,
        *,
        campaign_id: str,
        tenant_id: str,
        owner_id: str,
    ) -> Campaign | None:
        return self.session.scalar(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
                Campaign.owner_id == owner_id,
            )
        )

    def get_idempotency_record(
        self,
        *,
        tenant_id: str,
        route: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        return self.session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.tenant_id == tenant_id,
                IdempotencyRecord.route == route,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )

    def list_owned(
        self,
        *,
        tenant_id: str,
        owner_id: str,
        limit: int,
        status: str | None,
        before: tuple[datetime, str] | None,
    ) -> list[Campaign]:
        filters = [
            Campaign.tenant_id == tenant_id,
            Campaign.owner_id == owner_id,
        ]
        if status is not None:
            filters.append(Campaign.status == status)
        if before is not None:
            created_at, campaign_id = before
            filters.append(
                or_(
                    Campaign.created_at < created_at,
                    and_(
                        Campaign.created_at == created_at,
                        Campaign.id < campaign_id,
                    ),
                )
            )
        return list(
            self.session.scalars(
                select(Campaign)
                .where(*filters)
                .order_by(Campaign.created_at.desc(), Campaign.id.desc())
                .limit(limit)
            )
        )

    def succeeded_stage_output(
        self,
        *,
        campaign_id: str,
        stage: str,
    ) -> dict[str, object] | None:
        stage_run = self.session.scalar(
            select(CampaignStageRun)
            .where(
                CampaignStageRun.campaign_id == campaign_id,
                CampaignStageRun.stage == stage,
                CampaignStageRun.status == "succeeded",
            )
            .order_by(CampaignStageRun.attempt.desc())
            .limit(1)
        )
        if stage_run is None or stage_run.output_json is None:
            return None
        return dict(stage_run.output_json)

    def ready_asset(self, *, campaign_id: str, role: str) -> Asset | None:
        return self.session.scalar(
            select(Asset).where(
                Asset.campaign_id == campaign_id,
                Asset.role == role,
                Asset.status == "ready",
            )
        )
