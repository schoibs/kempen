from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app_config import get_settings
from infrastructure import (
    MigrationStateError,
    check_database_and_migrations,
    check_object_storage,
    check_redis,
)


logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "alive",
        "service": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/ready")
def readiness() -> JSONResponse:
    settings = get_settings()
    checks = {
        "configuration": "ok",
        "database": "unknown",
        "migrations": "unknown",
        "redis": "unknown",
        "object_storage": "unknown",
    }

    try:
        check_database_and_migrations()
        checks["database"] = "ok"
        checks["migrations"] = "ok"
    except MigrationStateError:
        checks["database"] = "ok"
        checks["migrations"] = "out_of_date"
        logger.exception("Readiness migration check failed.")
    except Exception:
        checks["database"] = "unavailable"
        checks["migrations"] = "unknown"
        logger.exception("Readiness database check failed.")

    try:
        check_redis()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
        logger.exception("Readiness Redis check failed.")

    try:
        check_object_storage()
        checks["object_storage"] = "ok"
    except Exception:
        checks["object_storage"] = "unavailable"
        logger.exception("Readiness object-storage check failed.")

    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "service": settings.app_name,
            "environment": settings.environment,
            "fake_provider_mode": settings.fake_provider_mode,
            "checks": checks,
        },
    )
