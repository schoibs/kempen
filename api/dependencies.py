from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app_config import get_settings
from persistence.database import get_session
from storage import ObjectStorage, get_object_storage


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    owner_id: str


def get_principal() -> Principal:
    """Provide the fixed local principal until OIDC authentication is introduced."""

    if get_settings().auth_enabled:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")
    return Principal(tenant_id="tenant_local", owner_id="owner_local")


def get_database_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_storage() -> ObjectStorage:
    return get_object_storage()
