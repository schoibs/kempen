from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed process configuration shared by the API and workers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CAMPAIGN_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Kempen Campaign API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"
    campaign_creation_enabled: bool = True

    database_url: str = "postgresql+psycopg://campaign:campaign@localhost:5432/campaign"
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=5, ge=0, le=100)
    redis_url: str = "redis://localhost:6379/0"

    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_public_endpoint: str | None = None
    object_storage_region: str = "us-east-1"
    object_storage_bucket: str = "campaign-assets"
    object_storage_access_key: SecretStr = SecretStr("campaign-local")
    object_storage_secret_key: SecretStr = SecretStr("campaign-local-secret")
    upload_url_expiry_sec: int = Field(default=900, ge=60, le=3600)
    download_url_expiry_sec: int = Field(default=900, ge=60, le=3600)
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    max_generated_video_bytes: int = Field(default=500 * 1024 * 1024, gt=0)
    max_image_width: int = Field(default=8192, gt=0)
    max_image_height: int = Field(default=8192, gt=0)
    max_image_pixels: int = Field(default=40_000_000, gt=0)
    unattached_upload_retention_sec: int = Field(default=24 * 60 * 60, gt=0)

    auth_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_required_scope: str | None = None
    cors_allowed_origins: str = ""

    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_sec: int = Field(default=60, ge=1)
    tenant_concurrent_campaign_quota: int = Field(default=20, ge=1)
    tenant_daily_campaign_quota: int = Field(default=1000, ge=1)

    dispatcher_interval_sec: float = Field(default=5.0, gt=0)
    dispatcher_reconcile_after_sec: float = Field(default=15.0, gt=0)
    stage_lease_sec: int = Field(default=900, ge=1, le=3600)
    input_validation_deadline_sec: int = Field(default=120, ge=1)
    planning_stage_deadline_sec: int = Field(default=15 * 60, ge=1)
    storyboard_stage_deadline_sec: int = Field(default=10 * 60, ge=1)
    video_submission_deadline_sec: int = Field(default=120, ge=1)
    video_poll_deadline_sec: int = Field(default=45 * 60, ge=1)
    video_finalize_deadline_sec: int = Field(default=10 * 60, ge=1)
    input_validation_max_attempts: int = Field(default=3, ge=1)
    planning_stage_max_attempts: int = Field(default=2, ge=1)
    storyboard_stage_max_attempts: int = Field(default=2, ge=1)
    video_submission_max_attempts: int = Field(default=2, ge=1)
    video_finalize_max_attempts: int = Field(default=3, ge=1)
    retry_backoff_min_sec: float = Field(default=5.0, ge=0.1)
    retry_backoff_max_sec: float = Field(default=60.0, ge=0.1)
    retry_jitter_ratio: float = Field(default=0.2, ge=0, le=1)
    video_poll_min_sec: float = Field(default=5.0, ge=1, le=30)
    video_poll_max_sec: float = Field(default=30.0, ge=1, le=120)
    video_poll_jitter_ratio: float = Field(default=0.2, ge=0, le=1)
    idempotency_retention_sec: int = Field(default=24 * 60 * 60, ge=60)
    artifact_retention_sec: int = Field(default=30 * 24 * 60 * 60, ge=60)
    cleanup_interval_sec: int = Field(default=15 * 60, ge=60)
    cleanup_batch_size: int = Field(default=100, ge=1, le=1000)

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )
    tinyfish_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="TINYFISH_API_KEY",
    )
    fal_key: SecretStr | None = Field(
        default=None,
        validation_alias="FAL_KEY",
    )

    @field_validator("object_storage_public_endpoint")
    @classmethod
    def validate_object_storage_public_endpoint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise ValueError(
                "object_storage_public_endpoint must be an absolute http or https URL with a host"
            )
        return value

    @model_validator(mode="after")
    def validate_runtime_mode(self) -> "Settings":
        if self.retry_backoff_min_sec > self.retry_backoff_max_sec:
            raise ValueError("retry_backoff_min_sec must not exceed retry_backoff_max_sec")
        if self.video_poll_min_sec > self.video_poll_max_sec:
            raise ValueError("video_poll_min_sec must not exceed video_poll_max_sec")
        missing = [
            name
            for name, value in (
                ("OPENAI_API_KEY", self.openai_api_key),
                ("TINYFISH_API_KEY", self.tinyfish_api_key),
                ("FAL_KEY", self.fal_key),
            )
            if value is None or not value.get_secret_value().strip()
        ]
        if missing:
            raise ValueError("Provider credentials are required: " + ", ".join(missing))

        if self.auth_enabled:
            missing = [
                name
                for name, value in (
                    ("CAMPAIGN_OIDC_ISSUER", self.oidc_issuer),
                    ("CAMPAIGN_OIDC_AUDIENCE", self.oidc_audience),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "Authentication requires: " + ", ".join(missing)
                )

        if self.environment == "production" and not self.cors_allowed_origins.strip():
            raise ValueError("Production requires CAMPAIGN_CORS_ALLOWED_ORIGINS.")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
