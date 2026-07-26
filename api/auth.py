from __future__ import annotations

import json
import threading

from dataclasses import dataclass
from urllib.parse import urljoin

from app_config import Settings


class AuthenticationError(RuntimeError):
    """Raised when a bearer token cannot be trusted."""


@dataclass(frozen=True)
class VerifiedClaims:
    tenant_id: str
    owner_id: str
    scopes: frozenset[str]


class OIDCVerifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._jwks_url: str | None = settings.oidc_jwks_url
        self._lock = threading.Lock()

    def verify(self, token: str) -> VerifiedClaims:
        try:
            import jwt
            from jwt import PyJWKClient
        except ImportError as exc:
            raise AuthenticationError("JWT verification dependency is unavailable.") from exc

        jwks_url = self._get_jwks_url()
        try:
            signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                audience=self.settings.oidc_audience,
                issuer=self.settings.oidc_issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except Exception as exc:
            raise AuthenticationError("Bearer token verification failed.") from exc

        tenant_id = claims.get("tenant_id") or claims.get("tenant") or claims.get("tid")
        owner_id = claims.get("owner_id") or claims.get("sub")
        if not isinstance(tenant_id, str) or not isinstance(owner_id, str):
            raise AuthenticationError("Bearer token does not contain tenant identity claims.")
        if not _safe_identifier(tenant_id) or not _safe_identifier(owner_id):
            raise AuthenticationError("Bearer token identity claims are invalid.")
        scope_claim = claims.get("scope", "")
        scopes = frozenset(scope_claim.split()) if isinstance(scope_claim, str) else frozenset()
        required_scope = self.settings.oidc_required_scope
        if required_scope and required_scope not in scopes:
            raise AuthenticationError("Bearer token lacks the required scope.")
        return VerifiedClaims(tenant_id=tenant_id, owner_id=owner_id, scopes=scopes)

    def _get_jwks_url(self) -> str:
        if self._jwks_url:
            return self._jwks_url
        issuer = self.settings.oidc_issuer
        if not issuer:
            raise AuthenticationError("OIDC issuer is not configured.")
        with self._lock:
            if self._jwks_url:
                return self._jwks_url
            try:
                import requests

                response = requests.get(
                    urljoin(issuer.rstrip("/") + "/", ".well-known/openid-configuration"),
                    timeout=3,
                )
                response.raise_for_status()
                discovery = json.loads(response.text)
                self._jwks_url = discovery["jwks_uri"]
            except Exception as exc:
                raise AuthenticationError("OIDC discovery failed.") from exc
        return self._jwks_url


def _safe_identifier(value: str) -> bool:
    return bool(value) and len(value) <= 128 and "/" not in value and "\\" not in value
