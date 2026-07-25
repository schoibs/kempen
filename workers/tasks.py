from __future__ import annotations

import hashlib
import logging
import secrets
import tempfile

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app_config import get_settings
from domain.campaigns import CampaignInput
from domain.enums import CampaignStage, CampaignStatus, PROGRESS_PERCENT_BY_STAGE, PUBLIC_STAGE_BY_STAGE, StageStatus
from domain.orchestration import CampaignStageOperations
from persistence.database import get_session_factory
from persistence.ids import new_resource_id
from persistence.models import Asset, Campaign, CampaignEvent, CampaignStageRun, DispatchOutbox
from storage import ObjectNotFoundError, ObjectStorage, ObjectStorageError, get_object_storage
from storage.keys import campaign_artifact_key
from workers.celery_app import celery_app
from workers.image_validation import InputImageValidationError, download_and_validate_product_image


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClaimedStage:
    campaign_id: str
    stage_run_id: str
    stage: CampaignStage
    run_token: str


@dataclass(frozen=True)
class StageExecution:
    output: dict[str, Any]
    next_stage: CampaignStage | None = None
    wait_until: datetime | None = None


@celery_app.task(name="campaign.healthcheck")
def healthcheck() -> dict[str, Any]:
    """Non-provider task used to verify worker startup and queue wiring."""

    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "fake_provider_mode": settings.fake_provider_mode,
    }


@celery_app.task(name="campaign.run_stage")
def run_stage(*, campaign_id: str, stage_run_id: str) -> dict[str, str]:
    """Claim and execute one fixed pipeline stage using identifier-only payloads."""

    claim = _claim_stage(campaign_id=campaign_id, stage_run_id=stage_run_id)
    if claim is None:
        return {"status": "noop"}

    try:
        execution = _execute_stage(claim)
        if execution.wait_until is not None:
            _wait_for_external(claim, execution)
            return {"status": "waiting_external"}
        _complete_stage(claim, execution)
        return {"status": "completed"}
    except InputImageValidationError:
        _fail_stage(
            claim,
            code="INPUT_IMAGE_INVALID",
            message="The product image could not be validated.",
            retryable=False,
        )
        return {"status": "failed"}
    except ObjectNotFoundError:
        _fail_stage(
            claim,
            code="INPUT_ASSET_MISSING",
            message="A required campaign asset is no longer available.",
            retryable=False,
        )
        return {"status": "failed"}
    except ObjectStorageError:
        _fail_stage(
            claim,
            code="ARTIFACT_UPLOAD_FAILED",
            message="Campaign artifact storage is temporarily unavailable.",
            retryable=True,
        )
        return {"status": "failed"}
    except Exception:
        logger.error(
            "Campaign stage failed campaign_id=%s stage=%s",
            claim.campaign_id,
            claim.stage.value,
        )
        _fail_stage(
            claim,
            code="INTERNAL_ERROR",
            message="Campaign generation could not complete.",
            retryable=False,
        )
        return {"status": "failed"}


@celery_app.task(name="campaign.validate_input_asset")
def validate_input_asset(asset_id: str) -> dict[str, Any]:
    """Validate an uploaded image before a later worker can call a provider."""

    session = get_session_factory()()
    try:
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise InputImageValidationError("Input asset is missing.")
        with tempfile.TemporaryDirectory(prefix="campaign-validate-") as directory:
            validated = download_and_validate_product_image(
                storage=get_object_storage(),
                asset=asset,
                output_path=Path(directory) / "product-input",
                settings=get_settings(),
            )
        asset.width = validated.width
        asset.height = validated.height
        asset.sha256 = validated.sha256
        session.commit()
        return {
            "asset_id": asset.id,
            "content_type": validated.content_type,
            "width": validated.width,
            "height": validated.height,
            "sha256": validated.sha256,
        }
    except (InputImageValidationError, ObjectStorageError):
        session.rollback()
        asset = session.get(Asset, asset_id)
        if asset is not None:
            asset.status = "quarantined"
            session.commit()
        raise
    finally:
        session.close()


def _claim_stage(*, campaign_id: str, stage_run_id: str) -> ClaimedStage | None:
    settings = get_settings()
    session = get_session_factory()()
    try:
        with session.begin():
            stage_run = session.scalar(
                select(CampaignStageRun)
                .where(
                    CampaignStageRun.id == stage_run_id,
                    CampaignStageRun.campaign_id == campaign_id,
                )
                .with_for_update()
            )
            if stage_run is None:
                return None
            campaign = session.scalar(
                select(Campaign).where(Campaign.id == campaign_id).with_for_update()
            )
            if campaign is None or campaign.status not in {
                CampaignStatus.QUEUED.value,
                CampaignStatus.RUNNING.value,
            }:
                return None
            if campaign.current_stage != stage_run.stage:
                return None

            now = datetime.now(UTC)
            if not _stage_is_claimable(stage_run, now):
                return None

            run_token = secrets.token_urlsafe(24)
            stage_run.status = StageStatus.RUNNING.value
            stage_run.run_token = run_token
            stage_run.lease_expires_at = now + timedelta(seconds=settings.stage_lease_sec)
            stage_run.next_poll_at = None
            stage_run.started_at = stage_run.started_at or now
            stage_run.updated_at = now
            campaign.status = CampaignStatus.RUNNING.value
            campaign.started_at = campaign.started_at or now
            campaign.progress_percent = max(
                campaign.progress_percent,
                PROGRESS_PERCENT_BY_STAGE[CampaignStage(stage_run.stage)],
            )
            campaign.updated_at = now
            campaign.version += 1
            _append_event(
                session=session,
                campaign_id=campaign.id,
                event_type="stage.started",
                payload={"stage": PUBLIC_STAGE_BY_STAGE[CampaignStage(stage_run.stage)].value},
                now=now,
            )
            return ClaimedStage(
                campaign_id=campaign.id,
                stage_run_id=stage_run.id,
                stage=CampaignStage(stage_run.stage),
                run_token=run_token,
            )
    finally:
        session.close()


def _stage_is_claimable(stage_run: CampaignStageRun, now: datetime) -> bool:
    if stage_run.status == StageStatus.PENDING.value:
        return True
    if stage_run.status == StageStatus.RUNNING.value:
        return stage_run.lease_expires_at is None or stage_run.lease_expires_at <= now
    if stage_run.status == StageStatus.WAITING_EXTERNAL.value:
        return stage_run.next_poll_at is None or stage_run.next_poll_at <= now
    return False


def _execute_stage(claim: ClaimedStage) -> StageExecution:
    session = get_session_factory()()
    try:
        campaign = session.get(Campaign, claim.campaign_id)
        if campaign is None:
            raise ObjectNotFoundError("Campaign is missing.")
        operations = CampaignStageOperations()
        with tempfile.TemporaryDirectory(prefix=f"campaign-{campaign.id}-") as directory:
            workspace = Path(directory)
            if claim.stage == CampaignStage.VALIDATE_INPUT:
                validated = _materialize_product_image(
                    campaign=campaign,
                    session=session,
                    storage=get_object_storage(),
                    workspace=workspace,
                )
                return StageExecution(
                    output={
                        "content_type": validated["content_type"],
                        "width": validated["width"],
                        "height": validated["height"],
                        "sha256": validated["sha256"],
                    },
                    next_stage=CampaignStage.PRODUCT_ANALYSIS,
                )

            if claim.stage == CampaignStage.PRODUCT_ANALYSIS:
                product = _materialize_product_image(
                    campaign=campaign,
                    session=session,
                    storage=get_object_storage(),
                    workspace=workspace,
                )
                return StageExecution(
                    output=operations.analyze_product(product_image_path=product["path"]),
                    next_stage=CampaignStage.NARRATIVE_STRATEGY,
                )

            if claim.stage == CampaignStage.NARRATIVE_STRATEGY:
                product_analysis = _required_stage_output(
                    session=session,
                    campaign_id=campaign.id,
                    stage=CampaignStage.PRODUCT_ANALYSIS,
                )
                return StageExecution(
                    output=operations.build_narrative(
                        product_analysis=product_analysis,
                        campaign_input=_campaign_input(campaign, ""),
                    ),
                    next_stage=CampaignStage.STORYBOARD_GENERATION,
                )

            if claim.stage == CampaignStage.STORYBOARD_GENERATION:
                product = _materialize_product_image(
                    campaign=campaign,
                    session=session,
                    storage=get_object_storage(),
                    workspace=workspace,
                )
                storyboard_path = workspace / "storyboard.png"
                result = operations.generate_storyboard(
                    product_image_path=product["path"],
                    product_analysis=_required_stage_output(
                        session=session,
                        campaign_id=campaign.id,
                        stage=CampaignStage.PRODUCT_ANALYSIS,
                    ),
                    narrative_strategy=_required_stage_output(
                        session=session,
                        campaign_id=campaign.id,
                        stage=CampaignStage.NARRATIVE_STRATEGY,
                    ),
                    campaign_input=_campaign_input(campaign, product["path"]),
                    output_path=storyboard_path,
                )
                artifact = _upload_generated_artifact(
                    storage=get_object_storage(),
                    campaign=campaign,
                    role="storyboard",
                    content_type="image/png",
                    local_path=result["image_path"],
                )
                return StageExecution(
                    output={"asset": artifact},
                    next_stage=CampaignStage.VIDEO_SUBMISSION,
                )

            if claim.stage == CampaignStage.VIDEO_SUBMISSION:
                product = _materialize_product_image(
                    campaign=campaign,
                    session=session,
                    storage=get_object_storage(),
                    workspace=workspace,
                )
                storyboard = _materialize_generated_asset(
                    campaign_id=campaign.id,
                    role="storyboard",
                    session=session,
                    storage=get_object_storage(),
                    workspace=workspace,
                    filename="storyboard.png",
                )
                return StageExecution(
                    output=operations.submit_video(
                        storyboard_image_path=storyboard,
                        product_image_path=product["path"],
                        product_analysis=_required_stage_output(
                            session=session,
                            campaign_id=campaign.id,
                            stage=CampaignStage.PRODUCT_ANALYSIS,
                        ),
                        campaign_input=_campaign_input(campaign, product["path"]),
                    ),
                    next_stage=CampaignStage.VIDEO_POLL,
                )

            if claim.stage == CampaignStage.VIDEO_POLL:
                submission = _required_stage_output(
                    session=session,
                    campaign_id=campaign.id,
                    stage=CampaignStage.VIDEO_SUBMISSION,
                )
                request_id = _required_request_id(submission)
                output = operations.poll_video(request_id=request_id)
                if output.get("status") == "completed":
                    return StageExecution(
                        output=output,
                        next_stage=CampaignStage.VIDEO_FINALIZE,
                    )
                if output.get("status") in {"failed", "cancelled"}:
                    raise RuntimeError("Video provider returned a terminal failure state.")
                return StageExecution(
                    output=output,
                    wait_until=datetime.now(UTC)
                    + timedelta(seconds=get_settings().video_poll_interval_sec),
                )

            if claim.stage == CampaignStage.VIDEO_FINALIZE:
                submission = _required_stage_output(
                    session=session,
                    campaign_id=campaign.id,
                    stage=CampaignStage.VIDEO_SUBMISSION,
                )
                request_id = _required_request_id(submission)
                result = operations.finalize_video(
                    request_id=request_id,
                    output_path=workspace / "campaign.mp4",
                )
                artifact = _upload_generated_artifact(
                    storage=get_object_storage(),
                    campaign=campaign,
                    role="campaign_video",
                    content_type="video/mp4",
                    local_path=result["video_path"],
                )
                return StageExecution(
                    output={
                        "asset": artifact,
                        "seed": result.get("seed"),
                        "request_id": request_id,
                    },
                    next_stage=CampaignStage.FINALIZE_CAMPAIGN,
                )

            if claim.stage == CampaignStage.FINALIZE_CAMPAIGN:
                return StageExecution(output={"status": "succeeded"})
    finally:
        session.close()
    raise RuntimeError(f"Unsupported campaign stage: {claim.stage.value}")


def _materialize_product_image(
    *,
    campaign: Campaign,
    session: Any,
    storage: ObjectStorage,
    workspace: Path,
) -> dict[str, Any]:
    asset = session.get(Asset, campaign.product_image_asset_id)
    if asset is None:
        raise ObjectNotFoundError("Product image asset is missing.")
    validated = download_and_validate_product_image(
        storage=storage,
        asset=asset,
        output_path=workspace / "product-input",
        settings=get_settings(),
    )
    return {
        "path": validated.local_path,
        "content_type": validated.content_type,
        "width": validated.width,
        "height": validated.height,
        "sha256": validated.sha256,
    }


def _materialize_generated_asset(
    *,
    campaign_id: str,
    role: str,
    session: Any,
    storage: ObjectStorage,
    workspace: Path,
    filename: str,
) -> str:
    asset = session.scalar(
        select(Asset).where(
            Asset.campaign_id == campaign_id,
            Asset.role == role,
            Asset.status == "ready",
        )
    )
    if asset is None:
        raise ObjectNotFoundError("Generated campaign asset is missing.")
    payload = storage.download_bytes(
        object_key=asset.object_key,
        max_bytes=get_settings().max_upload_bytes,
    )
    if not payload:
        raise ObjectStorageError("Generated campaign asset is empty.")
    destination = workspace / filename
    destination.write_bytes(payload)
    return str(destination)


def _upload_generated_artifact(
    *,
    storage: ObjectStorage,
    campaign: Campaign,
    role: str,
    content_type: str,
    local_path: str | Path,
) -> dict[str, Any]:
    source = Path(local_path)
    if not source.is_file() or source.stat().st_size <= 0:
        raise ObjectStorageError("Generated campaign artifact is empty.")
    checksum = _sha256_file(source)
    object_key = campaign_artifact_key(
        tenant_id=campaign.tenant_id,
        campaign_id=campaign.id,
        role=role,
        content_type=content_type,
    )
    storage.ensure_bucket()
    metadata = storage.upload_file(
        object_key=object_key,
        local_path=source,
        content_type=content_type,
    )
    if metadata.size_bytes != source.stat().st_size:
        raise ObjectStorageError("Generated artifact size changed during upload.")
    return {
        "id": new_resource_id("ast"),
        "role": role,
        "bucket": get_settings().object_storage_bucket,
        "object_key": object_key,
        "content_type": content_type,
        "size_bytes": metadata.size_bytes,
        "sha256": checksum,
    }


def _required_stage_output(
    *,
    session: Any,
    campaign_id: str,
    stage: CampaignStage,
) -> dict[str, Any]:
    stage_run = session.scalar(
        select(CampaignStageRun)
        .where(
            CampaignStageRun.campaign_id == campaign_id,
            CampaignStageRun.stage == stage.value,
            CampaignStageRun.status == StageStatus.SUCCEEDED.value,
        )
        .order_by(CampaignStageRun.attempt.desc())
        .limit(1)
    )
    if stage_run is None or stage_run.output_json is None:
        raise RuntimeError(f"Required {stage.value} checkpoint is missing.")
    return dict(stage_run.output_json)


def _required_request_id(submission: dict[str, Any]) -> str:
    request_id = submission.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise RuntimeError("Video submission checkpoint is missing its request ID.")
    return request_id


def _campaign_input(campaign: Campaign, product_image_path: str) -> CampaignInput:
    return CampaignInput(
        product_image_path=product_image_path,
        campaign_theme=campaign.campaign_theme,
        target_audience=campaign.target_audience,
        target_duration_sec=campaign.target_duration_sec,
        aspect_ratio=campaign.aspect_ratio,
    )


def _complete_stage(claim: ClaimedStage, execution: StageExecution) -> None:
    session = get_session_factory()()
    try:
        with session.begin():
            stage_run, campaign = _locked_stage_and_campaign(session, claim)
            if stage_run is None or campaign is None:
                return
            now = datetime.now(UTC)
            stage_run.status = StageStatus.SUCCEEDED.value
            stage_run.output_json = execution.output
            stage_run.completed_at = now
            stage_run.updated_at = now
            stage_run.lease_expires_at = None
            if claim.stage == CampaignStage.VALIDATE_INPUT:
                _save_validation_metadata(
                    session=session,
                    campaign=campaign,
                    output=execution.output,
                )
            if claim.stage == CampaignStage.VIDEO_SUBMISSION:
                stage_run.provider_name = str(execution.output.get("provider", "fal"))
                stage_run.provider_request_id = _required_request_id(execution.output)
            if claim.stage == CampaignStage.VIDEO_POLL:
                stage_run.provider_status = str(execution.output.get("status", "unknown"))
                stage_run.provider_metadata = dict(
                    execution.output.get("provider_metadata", {})
                )
            _save_generated_asset(session=session, campaign=campaign, output=execution.output)
            _append_event(
                session=session,
                campaign_id=campaign.id,
                event_type="stage.succeeded",
                payload={"stage": PUBLIC_STAGE_BY_STAGE[claim.stage].value},
                now=now,
            )

            if execution.next_stage is None:
                campaign.status = CampaignStatus.SUCCEEDED.value
                campaign.progress_percent = 100
                campaign.completed_at = now
                campaign.updated_at = now
                campaign.version += 1
                _append_event(
                    session=session,
                    campaign_id=campaign.id,
                    event_type="campaign.succeeded",
                    payload=None,
                    now=now,
                )
                return

            next_run = CampaignStageRun(
                id=new_resource_id("stg"),
                campaign_id=campaign.id,
                stage=execution.next_stage.value,
                attempt=1,
                status=StageStatus.PENDING.value,
                updated_at=now,
            )
            session.add(next_run)
            session.add(
                DispatchOutbox(
                    id=new_resource_id("obx"),
                    task_type="campaign.run_stage",
                    campaign_id=campaign.id,
                    stage_run_id=next_run.id,
                    available_at=now,
                    delivery_attempts=0,
                    created_at=now,
                )
            )
            campaign.current_stage = execution.next_stage.value
            campaign.progress_percent = max(
                campaign.progress_percent,
                PROGRESS_PERCENT_BY_STAGE[execution.next_stage],
            )
            campaign.updated_at = now
            campaign.version += 1
    finally:
        session.close()


def _wait_for_external(claim: ClaimedStage, execution: StageExecution) -> None:
    session = get_session_factory()()
    try:
        with session.begin():
            stage_run, campaign = _locked_stage_and_campaign(session, claim)
            if stage_run is None or campaign is None:
                return
            now = datetime.now(UTC)
            stage_run.status = StageStatus.WAITING_EXTERNAL.value
            stage_run.output_json = execution.output
            stage_run.provider_status = str(execution.output.get("status", "unknown"))
            stage_run.provider_metadata = dict(execution.output.get("provider_metadata", {}))
            stage_run.run_token = None
            stage_run.lease_expires_at = None
            stage_run.next_poll_at = execution.wait_until
            stage_run.updated_at = now
            session.add(
                DispatchOutbox(
                    id=new_resource_id("obx"),
                    task_type="campaign.run_stage",
                    campaign_id=campaign.id,
                    stage_run_id=stage_run.id,
                    available_at=execution.wait_until,
                    delivery_attempts=0,
                    created_at=now,
                )
            )
            _append_event(
                session=session,
                campaign_id=campaign.id,
                event_type="stage.waiting_external",
                payload={"stage": PUBLIC_STAGE_BY_STAGE[claim.stage].value},
                now=now,
            )
    finally:
        session.close()


def _fail_stage(
    claim: ClaimedStage,
    *,
    code: str,
    message: str,
    retryable: bool,
) -> None:
    session = get_session_factory()()
    try:
        with session.begin():
            stage_run, campaign = _locked_stage_and_campaign(session, claim)
            if stage_run is None or campaign is None:
                return
            now = datetime.now(UTC)
            stage_run.status = StageStatus.FAILED.value
            stage_run.error_code = code
            stage_run.error_message = message
            stage_run.error_retryable = retryable
            stage_run.completed_at = now
            stage_run.updated_at = now
            stage_run.lease_expires_at = None
            campaign.status = CampaignStatus.FAILED.value
            campaign.error_code = code
            campaign.error_message = message
            campaign.error_retryable = retryable
            campaign.completed_at = now
            campaign.updated_at = now
            campaign.version += 1
            _append_event(
                session=session,
                campaign_id=campaign.id,
                event_type="stage.failed",
                payload={"stage": PUBLIC_STAGE_BY_STAGE[claim.stage].value, "code": code},
                now=now,
            )
            _append_event(
                session=session,
                campaign_id=campaign.id,
                event_type="campaign.failed",
                payload={"code": code},
                now=now,
            )
    finally:
        session.close()


def _locked_stage_and_campaign(
    session: Any,
    claim: ClaimedStage,
) -> tuple[CampaignStageRun | None, Campaign | None]:
    stage_run = session.scalar(
        select(CampaignStageRun)
        .where(
            CampaignStageRun.id == claim.stage_run_id,
            CampaignStageRun.campaign_id == claim.campaign_id,
            CampaignStageRun.run_token == claim.run_token,
            CampaignStageRun.status == StageStatus.RUNNING.value,
        )
        .with_for_update()
    )
    if stage_run is None:
        return None, None
    campaign = session.scalar(
        select(Campaign).where(Campaign.id == claim.campaign_id).with_for_update()
    )
    if campaign is None or campaign.current_stage != stage_run.stage:
        return None, None
    return stage_run, campaign


def _save_validation_metadata(
    *,
    session: Any,
    campaign: Campaign,
    output: dict[str, Any],
) -> None:
    asset = session.get(Asset, campaign.product_image_asset_id)
    if asset is None:
        raise ObjectNotFoundError("Product image asset is missing.")
    asset.width = int(output["width"])
    asset.height = int(output["height"])
    asset.sha256 = str(output["sha256"])


def _save_generated_asset(
    *,
    session: Any,
    campaign: Campaign,
    output: dict[str, Any],
) -> None:
    artifact = output.get("asset")
    if not isinstance(artifact, dict):
        return
    session.add(
        Asset(
            id=str(artifact["id"]),
            tenant_id=campaign.tenant_id,
            owner_id=campaign.owner_id,
            campaign_id=campaign.id,
            role=str(artifact["role"]),
            status="ready",
            bucket=str(artifact["bucket"]),
            object_key=str(artifact["object_key"]),
            content_type=str(artifact["content_type"]),
            size_bytes=int(artifact["size_bytes"]),
            sha256=str(artifact["sha256"]),
            ready_at=datetime.now(UTC),
        )
    )


def _append_event(
    *,
    session: Any,
    campaign_id: str,
    event_type: str,
    payload: dict[str, Any] | None,
    now: datetime,
) -> None:
    last_sequence = session.scalar(
        select(func.max(CampaignEvent.sequence)).where(
            CampaignEvent.campaign_id == campaign_id
        )
    )
    session.add(
        CampaignEvent(
            id=new_resource_id("evt"),
            campaign_id=campaign_id,
            sequence=(last_sequence or 0) + 1,
            event_type=event_type,
            payload=payload,
            created_at=now,
        )
    )
    session.flush()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
