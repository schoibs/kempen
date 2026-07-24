from __future__ import annotations

from typing import Any

from app_config import get_settings
from workers.celery_app import celery_app


@celery_app.task(name="campaign.healthcheck")
def healthcheck() -> dict[str, Any]:
    """Non-provider task used to verify worker startup and queue wiring."""

    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "fake_provider_mode": settings.fake_provider_mode,
    }
