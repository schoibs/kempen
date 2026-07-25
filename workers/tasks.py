from __future__ import annotations

import tempfile

from pathlib import Path
from typing import Any

from app_config import get_settings
from persistence.database import get_session_factory
from persistence.models import Asset
from storage import ObjectStorageError, get_object_storage
from workers.celery_app import celery_app
from workers.image_validation import (
    InputImageValidationError,
    download_and_validate_product_image,
)


@celery_app.task(name="campaign.healthcheck")
def healthcheck() -> dict[str, Any]:
    """Non-provider task used to verify worker startup and queue wiring."""

    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "fake_provider_mode": settings.fake_provider_mode,
    }


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
