from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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
    fake_provider_mode: bool = True

    database_url: str = "postgresql+psycopg://campaign:campaign@localhost:5432/campaign"
    redis_url: str = "redis://localhost:6379/0"

    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_region: str = "us-east-1"
    object_storage_bucket: str = "campaign-assets"
    object_storage_access_key: SecretStr = SecretStr("campaign-local")
    object_storage_secret_key: SecretStr = SecretStr("campaign-local-secret")
    upload_url_expiry_sec: int = Field(default=900, ge=60, le=3600)
    download_url_expiry_sec: int = Field(default=900, ge=60, le=3600)
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    max_image_width: int = Field(default=8192, gt=0)
    max_image_height: int = Field(default=8192, gt=0)
    max_image_pixels: int = Field(default=40_000_000, gt=0)
    unattached_upload_retention_sec: int = Field(default=24 * 60 * 60, gt=0)

    auth_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None

    dispatcher_interval_sec: float = Field(default=5.0, gt=0)

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

    @model_validator(mode="after")
    def validate_runtime_mode(self) -> "Settings":
        if not self.fake_provider_mode:
            missing = [
                name
                for name, value in (
                    ("OPENAI_API_KEY", self.openai_api_key),
                    ("TINYFISH_API_KEY", self.tinyfish_api_key),
                    ("FAL_KEY", self.fal_key),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "Real-provider mode requires: " + ", ".join(missing)
                )

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

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
