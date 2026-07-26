from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Header, HTTPException
from sqlalchemy.orm import Session

from api.auth import AuthenticationError, OIDCVerifier
from app_config import get_settings
from persistence.database import get_session
from storage import ObjectStorage, get_object_storage


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    owner_id: str


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """Return a verified principal, or the fixed local principal in local mode."""

    settings = get_settings()
    if settings.auth_enabled:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail="A bearer token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            claims = get_oidc_verifier().verify(authorization[7:].strip())
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=401,
                detail="Bearer token is invalid.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        return Principal(tenant_id=claims.tenant_id, owner_id=claims.owner_id)
    return Principal(tenant_id="tenant_local", owner_id="owner_local")


@lru_cache(maxsize=1)
def get_oidc_verifier() -> OIDCVerifier:
    return OIDCVerifier(get_settings())


def get_database_session() -> Generator[Session, None, None]:
    yield from get_session()


def get_storage() -> ObjectStorage:
    return get_object_storage()
