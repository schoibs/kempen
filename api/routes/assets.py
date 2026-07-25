from __future__ import annotations

import base64
import logging

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from api.dependencies import Principal, get_database_session, get_principal, get_storage
from api.errors import ApiProblem
from api.schemas.assets import (
    AssetDownloadResponse,
    AssetSummary,
    UploadCompleteResponse,
    UploadDescriptor,
    UploadIntentRequest,
    UploadIntentResponse,
)
from app_config import get_settings
from persistence.ids import new_resource_id
from persistence.models import Asset
from persistence.repositories.assets import AssetRepository
from storage import ObjectNotFoundError, ObjectStorage, ObjectStorageError
from storage.keys import upload_object_key


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/assets", tags=["assets"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
Storage = Annotated[ObjectStorage, Depends(get_storage)]


@router.post(
    "/upload-intents",
    response_model=UploadIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_upload_intent(
    request: UploadIntentRequest,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    storage: Storage,
) -> UploadIntentResponse:
    settings = get_settings()
    if request.size_bytes > settings.max_upload_bytes:
        raise ApiProblem(
            status=422,
            code="VALIDATION_ERROR",
            title="Invalid upload size",
            detail="The product image exceeds the configured upload size limit.",
        )

    asset_id = new_resource_id("ast")
    asset = Asset(
        id=asset_id,
        tenant_id=principal.tenant_id,
        owner_id=principal.owner_id,
        role="product_input",
        status="pending_upload",
        bucket=settings.object_storage_bucket,
        object_key=upload_object_key(
            tenant_id=principal.tenant_id,
            asset_id=asset_id,
            content_type=request.content_type,
        ),
        content_type=request.content_type,
        size_bytes=request.size_bytes,
        sha256=request.sha256,
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.unattached_upload_retention_sec),
    )

    try:
        storage.ensure_bucket()
        upload = storage.create_upload_url(
            object_key=asset.object_key,
            content_type=asset.content_type,
            expires_in_sec=settings.upload_url_expiry_sec,
            checksum_sha256=asset.sha256,
        )
        AssetRepository(session).add(asset)
        session.commit()
    except (ObjectStorageError, ValueError) as exc:
        session.rollback()
        logger.exception("Could not create upload intent for asset_id=%s", asset_id)
        raise ApiProblem(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Upload service unavailable",
            detail="The upload service is temporarily unavailable.",
        ) from exc

    expires_at = datetime.now(UTC) + timedelta(seconds=settings.upload_url_expiry_sec)
    return UploadIntentResponse(
        asset=AssetSummary(
            id=asset.id,
            status=asset.status,
            content_type=asset.content_type,
            size_bytes=asset.size_bytes,
        ),
        upload=UploadDescriptor(
            method="PUT",
            url=upload.url,
            headers=upload.headers,
            expires_at=expires_at,
        ),
    )


@router.post("/{asset_id}/complete", response_model=UploadCompleteResponse)
def complete_upload(
    asset_id: str,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    storage: Storage,
) -> UploadCompleteResponse:
    asset = _owned_asset_or_not_found(
        repository=AssetRepository(session),
        asset_id=asset_id,
        principal=principal,
    )
    if asset.status == "ready":
        return _complete_response(asset)
    if asset.status != "pending_upload":
        raise ApiProblem(
            status=409,
            code="INVALID_ASSET_STATE",
            title="Asset cannot be completed",
            detail="This asset is not awaiting an upload.",
        )

    try:
        object_metadata = storage.head_object(object_key=asset.object_key)
    except ObjectNotFoundError as exc:
        raise ApiProblem(
            status=422,
            code="ASSET_MISMATCH",
            title="Uploaded asset is missing",
            detail="Upload the product image before completing it.",
        ) from exc
    except ObjectStorageError as exc:
        logger.exception("Could not inspect uploaded asset_id=%s", asset.id)
        raise ApiProblem(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Upload service unavailable",
            detail="The upload service is temporarily unavailable.",
        ) from exc

    if not _metadata_matches(asset, object_metadata.content_type, object_metadata.size_bytes, object_metadata.checksum_sha256):
        _quarantine_mismatched_asset(session=session, storage=storage, asset=asset)
        raise ApiProblem(
            status=422,
            code="ASSET_MISMATCH",
            title="Uploaded asset does not match the upload intent",
            detail="Upload an image that matches the requested type, size, and checksum.",
        )

    asset.status = "ready"
    asset.ready_at = datetime.now(UTC)
    session.commit()
    return _complete_response(asset)


@router.get("/{asset_id}/download", response_model=AssetDownloadResponse)
def create_download_url(
    asset_id: str,
    principal: CurrentPrincipal,
    session: DatabaseSession,
    storage: Storage,
    response: Response,
) -> AssetDownloadResponse:
    asset = _owned_asset_or_not_found(
        repository=AssetRepository(session),
        asset_id=asset_id,
        principal=principal,
    )
    if asset.status != "ready":
        raise ApiProblem(
            status=409,
            code="ASSET_NOT_READY",
            title="Asset is not ready",
            detail="Complete the product image upload before requesting a download.",
        )

    settings = get_settings()
    try:
        url = storage.create_download_url(
            object_key=asset.object_key,
            expires_in_sec=settings.download_url_expiry_sec,
        )
    except ObjectStorageError as exc:
        logger.exception("Could not create download URL for asset_id=%s", asset.id)
        raise ApiProblem(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Download service unavailable",
            detail="The download service is temporarily unavailable.",
        ) from exc

    response.headers["Cache-Control"] = "private, no-store"
    return AssetDownloadResponse(
        id=asset.id,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        download_url=url,
        download_url_expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.download_url_expiry_sec),
    )


def _owned_asset_or_not_found(
    *,
    repository: AssetRepository,
    asset_id: str,
    principal: Principal,
) -> Asset:
    asset = repository.get_owned(
        asset_id=asset_id,
        tenant_id=principal.tenant_id,
        owner_id=principal.owner_id,
    )
    if asset is None:
        raise ApiProblem(
            status=404,
            code="NOT_FOUND",
            title="Asset not found",
            detail="The requested asset does not exist.",
        )
    return asset


def _complete_response(asset: Asset) -> UploadCompleteResponse:
    return UploadCompleteResponse(
        id=asset.id,
        status=asset.status,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
    )


def _metadata_matches(
    asset: Asset,
    content_type: str | None,
    size_bytes: int,
    checksum_sha256: str | None,
) -> bool:
    if content_type is None or content_type.split(";", 1)[0].lower() != asset.content_type:
        return False
    if size_bytes != asset.size_bytes:
        return False
    if asset.sha256 and checksum_sha256:
        expected_checksum = base64.b64encode(bytes.fromhex(asset.sha256)).decode("ascii")
        if checksum_sha256 != expected_checksum:
            return False
    return True


def _quarantine_mismatched_asset(
    *,
    session: Session,
    storage: ObjectStorage,
    asset: Asset,
) -> None:
    asset.status = "quarantined"
    try:
        storage.delete_object(object_key=asset.object_key)
    except ObjectStorageError:
        logger.exception("Could not remove mismatched asset_id=%s", asset.id)
    finally:
        session.commit()
