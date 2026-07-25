from __future__ import annotations

import base64
import hashlib
import json
import logging

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.dependencies import Principal, get_database_session, get_principal, get_storage
from api.errors import ApiProblem
from api.schemas.assets import AssetDownloadResponse
from api.schemas.campaigns import (
    CampaignAcceptedResponse,
    CampaignDetailResponse,
    CampaignErrorResponse,
    CampaignInputResponse,
    CampaignLinks,
    CampaignListResponse,
    CampaignResultsResponse,
    CampaignSummaryResponse,
    CreateCampaignRequest,
)
from app_config import get_settings
from domain.enums import CampaignStage, CampaignStatus, PROGRESS_PERCENT_BY_STAGE, PUBLIC_STAGE_BY_STAGE
from persistence.ids import new_resource_id
from persistence.models import Campaign, CampaignEvent, CampaignStageRun, DispatchOutbox, IdempotencyRecord
from persistence.repositories import AssetRepository, CampaignRepository
from storage import ObjectStorage, ObjectStorageError


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
Storage = Annotated[ObjectStorage, Depends(get_storage)]
IdempotencyKey = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=16, max_length=128),
]

_CREATE_ROUTE = "/v1/campaigns"
_TOTAL_PUBLIC_STAGES = 5
_COMPLETED_STAGES_BY_CURRENT_STAGE = {
    CampaignStage.VALIDATE_INPUT: 0,
    CampaignStage.PRODUCT_ANALYSIS: 1,
    CampaignStage.NARRATIVE_STRATEGY: 2,
    CampaignStage.STORYBOARD_GENERATION: 3,
    CampaignStage.VIDEO_SUBMISSION: 4,
    CampaignStage.VIDEO_POLL: 4,
    CampaignStage.VIDEO_FINALIZE: 4,
    CampaignStage.FINALIZE_CAMPAIGN: 4,
}


@router.post("", response_model=CampaignAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_campaign(
    request: CreateCampaignRequest,
    response: Response,
    idempotency_key: IdempotencyKey,
    principal: CurrentPrincipal,
    session: DatabaseSession,
) -> CampaignAcceptedResponse:
    if idempotency_key != idempotency_key.strip():
        raise ApiProblem(
            status=422,
            code="VALIDATION_ERROR",
            title="Request validation failed",
            detail="Idempotency-Key must not include surrounding whitespace.",
        )

    request_hash = _request_hash(request)
    campaigns = CampaignRepository(session)
    existing = campaigns.get_idempotency_record(
        tenant_id=principal.tenant_id,
        route=_CREATE_ROUTE,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return _idempotent_replay(
            record=existing,
            request_hash=request_hash,
            campaigns=campaigns,
            principal=principal,
            response=response,
        )

    asset = AssetRepository(session).get_owned(
        asset_id=request.product_image_asset_id,
        tenant_id=principal.tenant_id,
        owner_id=principal.owner_id,
    )
    if asset is None:
        raise _not_found_problem("Product image asset")
    now = datetime.now(UTC)
    if asset.status != "ready" or (asset.expires_at is not None and asset.expires_at <= now):
        raise ApiProblem(
            status=409,
            code="ASSET_NOT_READY",
            title="Asset is not ready",
            detail="Complete the product image upload before creating a campaign.",
        )
    if asset.campaign_id is not None:
        raise ApiProblem(
            status=409,
            code="INVALID_ASSET_STATE",
            title="Asset cannot be used for a campaign",
            detail="The product image asset is already attached to a campaign.",
        )

    settings = get_settings()
    campaign = Campaign(
        id=new_resource_id("cmp"),
        tenant_id=principal.tenant_id,
        owner_id=principal.owner_id,
        product_image_asset_id=asset.id,
        campaign_theme=request.campaign_theme,
        target_audience=request.target_audience,
        target_duration_sec=request.target_duration_sec,
        aspect_ratio=request.aspect_ratio,
        status=CampaignStatus.QUEUED.value,
        current_stage=CampaignStage.VALIDATE_INPUT.value,
        progress_percent=0,
        pipeline_version="feature_1_async_api",
        provider_config_snapshot=_provider_config_snapshot(request),
        retry_count=0,
        created_at=now,
        updated_at=now,
        version=1,
    )
    stage_run = CampaignStageRun(
        id=new_resource_id("stg"),
        campaign_id=campaign.id,
        stage=CampaignStage.VALIDATE_INPUT.value,
        attempt=1,
        status="pending",
        updated_at=now,
    )
    record = IdempotencyRecord(
        id=new_resource_id("idr"),
        tenant_id=principal.tenant_id,
        route=_CREATE_ROUTE,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        campaign_id=campaign.id,
        response_status=status.HTTP_202_ACCEPTED,
        created_at=now,
        expires_at=now + timedelta(seconds=settings.idempotency_retention_sec),
    )
    outbox = DispatchOutbox(
        id=new_resource_id("obx"),
        task_type="campaign.run_stage",
        campaign_id=campaign.id,
        stage_run_id=stage_run.id,
        available_at=now,
        delivery_attempts=0,
        created_at=now,
    )
    event = CampaignEvent(
        id=new_resource_id("evt"),
        campaign_id=campaign.id,
        sequence=1,
        event_type="campaign.accepted",
        payload={"stage": _public_stage(campaign.current_stage)},
        created_at=now,
    )

    try:
        session.add(campaign)
        session.flush()
        asset.campaign_id = campaign.id
        asset.expires_at = None
        session.add_all([stage_run, record, outbox, event])
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = campaigns.get_idempotency_record(
            tenant_id=principal.tenant_id,
            route=_CREATE_ROUTE,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            logger.exception("Could not create campaign due to a database constraint.")
            raise ApiProblem(
                status=503,
                code="SERVICE_UNAVAILABLE",
                title="Campaign service unavailable",
                detail="The campaign could not be accepted. Please retry.",
            )
        return _idempotent_replay(
            record=existing,
            request_hash=request_hash,
            campaigns=campaigns,
            principal=principal,
            response=response,
        )

    response.headers["Location"] = _campaign_path(campaign.id)
    response.headers["Retry-After"] = "3"
    return _accepted_response(campaign)


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    principal: CurrentPrincipal,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    status_filter: CampaignStatus | None = Query(default=None, alias="status"),
) -> CampaignListResponse:
    campaigns = CampaignRepository(session).list_owned(
        tenant_id=principal.tenant_id,
        owner_id=principal.owner_id,
        limit=limit + 1,
        status=status_filter.value if status_filter is not None else None,
        before=_decode_cursor(cursor) if cursor is not None else None,
    )
    has_more = len(campaigns) > limit
    page = campaigns[:limit]
    next_cursor = _encode_cursor(page[-1]) if has_more and page else None
    return CampaignListResponse(
        items=[_summary_response(campaign) for campaign in page],
        next_cursor=next_cursor,
    )


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
def get_campaign(
    campaign_id: str,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    storage: Storage,
    response: Response,
) -> CampaignDetailResponse:
    campaign = _owned_campaign_or_not_found(
        campaigns=CampaignRepository(session),
        campaign_id=campaign_id,
        principal=principal,
    )
    response.headers["Cache-Control"] = "private, no-store"
    return _detail_response(
        campaign=campaign,
        campaigns=CampaignRepository(session),
        storage=storage,
    )


def _idempotent_replay(
    *,
    record: IdempotencyRecord,
    request_hash: str,
    campaigns: CampaignRepository,
    principal: Principal,
    response: Response,
) -> CampaignAcceptedResponse:
    if record.request_hash != request_hash:
        raise ApiProblem(
            status=409,
            code="IDEMPOTENCY_KEY_REUSED",
            title="Idempotency key was reused",
            detail="Use a new Idempotency-Key for a different campaign request.",
        )
    campaign = _owned_campaign_or_not_found(
        campaigns=campaigns,
        campaign_id=record.campaign_id,
        principal=principal,
    )
    response.status_code = status.HTTP_200_OK
    response.headers["Location"] = _campaign_path(campaign.id)
    response.headers["Retry-After"] = "3"
    return _accepted_response(campaign)


def _owned_campaign_or_not_found(
    *,
    campaigns: CampaignRepository,
    campaign_id: str,
    principal: Principal,
) -> Campaign:
    campaign = campaigns.get_owned(
        campaign_id=campaign_id,
        tenant_id=principal.tenant_id,
        owner_id=principal.owner_id,
    )
    if campaign is None:
        raise _not_found_problem("Campaign")
    return campaign


def _accepted_response(campaign: Campaign) -> CampaignAcceptedResponse:
    return CampaignAcceptedResponse(
        id=campaign.id,
        status=campaign.status,
        stage=_public_stage(campaign.current_stage),
        progress_percent=campaign.progress_percent,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        links=_links(campaign.id),
    )


def _summary_response(campaign: Campaign) -> CampaignSummaryResponse:
    return CampaignSummaryResponse(
        **_accepted_response(campaign).model_dump(),
        completed_stages=_completed_stages(campaign),
        total_stages=_TOTAL_PUBLIC_STAGES,
    )


def _detail_response(
    *,
    campaign: Campaign,
    campaigns: CampaignRepository,
    storage: ObjectStorage,
) -> CampaignDetailResponse:
    try:
        storyboard = _asset_response(
            asset=campaigns.ready_asset(campaign_id=campaign.id, role="storyboard"),
            storage=storage,
        )
        video = _asset_response(
            asset=campaigns.ready_asset(campaign_id=campaign.id, role="campaign_video"),
            storage=storage,
        )
    except ObjectStorageError as exc:
        logger.exception("Could not create campaign artifact download URLs campaign_id=%s", campaign.id)
        raise ApiProblem(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Artifact service unavailable",
            detail="Campaign artifacts are temporarily unavailable.",
        ) from exc

    product_analysis = campaigns.succeeded_stage_output(
        campaign_id=campaign.id,
        stage=CampaignStage.PRODUCT_ANALYSIS.value,
    )
    narrative_strategy = campaigns.succeeded_stage_output(
        campaign_id=campaign.id,
        stage=CampaignStage.NARRATIVE_STRATEGY.value,
    )
    return CampaignDetailResponse(
        **_accepted_response(campaign).model_dump(),
        completed_stages=_completed_stages(campaign),
        total_stages=_TOTAL_PUBLIC_STAGES,
        input=CampaignInputResponse(
            product_image_asset_id=campaign.product_image_asset_id,
            campaign_theme=campaign.campaign_theme,
            target_audience=campaign.target_audience,
            target_duration_sec=campaign.target_duration_sec,
            aspect_ratio=campaign.aspect_ratio,
        ),
        results=CampaignResultsResponse(
            product_analysis=product_analysis,
            narrative_strategy=narrative_strategy,
            storyboard=storyboard,
            video=video,
        ),
        error=(
            CampaignErrorResponse(
                code=campaign.error_code or "INTERNAL_ERROR",
                message=campaign.error_message or "Campaign generation failed.",
                retryable=bool(campaign.error_retryable),
            )
            if campaign.error_code is not None
            else None
        ),
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
    )


def _asset_response(*, asset: object, storage: ObjectStorage) -> AssetDownloadResponse | None:
    if asset is None:
        return None
    asset_id = getattr(asset, "id")
    url = storage.create_download_url(
        object_key=getattr(asset, "object_key"),
        expires_in_sec=get_settings().download_url_expiry_sec,
    )
    return AssetDownloadResponse(
        id=asset_id,
        content_type=getattr(asset, "content_type"),
        size_bytes=getattr(asset, "size_bytes"),
        sha256=getattr(asset, "sha256"),
        download_url=url,
        download_url_expires_at=datetime.now(UTC)
        + timedelta(seconds=get_settings().download_url_expiry_sec),
    )


def _links(campaign_id: str) -> CampaignLinks:
    campaign_path = _campaign_path(campaign_id)
    return CampaignLinks(self=campaign_path, cancel=f"{campaign_path}/cancel")


def _campaign_path(campaign_id: str) -> str:
    return f"/v1/campaigns/{campaign_id}"


def _public_stage(stage: str) -> str:
    return PUBLIC_STAGE_BY_STAGE[CampaignStage(stage)].value


def _completed_stages(campaign: Campaign) -> int:
    if campaign.status == CampaignStatus.SUCCEEDED.value:
        return _TOTAL_PUBLIC_STAGES
    return _COMPLETED_STAGES_BY_CURRENT_STAGE[CampaignStage(campaign.current_stage)]


def _request_hash(request: CreateCampaignRequest) -> str:
    serialized = json.dumps(
        request.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _provider_config_snapshot(request: CreateCampaignRequest) -> dict[str, object]:
    return {
        "pipeline_version": "feature_1_async_api",
        "product_analysis_model": "gpt-5.4-mini",
        "narrative_strategy_model": "gpt-5.4-mini",
        "storyboard": {
            "model": "gpt-image-2",
            "size": "1536x1024",
            "quality": "medium",
            "format": "png",
        },
        "video": {
            "endpoint": "bytedance/seedance-2.0/reference-to-video",
            "resolution": "720p",
            "generate_audio": True,
            "duration": request.target_duration_sec,
            "aspect_ratio": request.aspect_ratio,
        },
    }


def _encode_cursor(campaign: Campaign) -> str:
    payload = json.dumps(
        {"created_at": campaign.created_at.isoformat(), "id": campaign.id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        campaign_id = payload["id"]
        if created_at.tzinfo is None or not isinstance(campaign_id, str) or not campaign_id:
            raise ValueError
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ApiProblem(
            status=422,
            code="VALIDATION_ERROR",
            title="Request validation failed",
            detail="cursor is invalid.",
        ) from exc
    return created_at, campaign_id


def _not_found_problem(resource_name: str) -> ApiProblem:
    return ApiProblem(
        status=404,
        code="NOT_FOUND",
        title=f"{resource_name} not found",
        detail=f"The requested {resource_name.lower()} does not exist.",
    )
