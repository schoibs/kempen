from __future__ import annotations

import re

from datetime import datetime
from pathlib import PurePath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UploadIntentRequest(StrictSchema):
    filename: str = Field(min_length=1, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    size_bytes: StrictInt = Field(gt=0)
    sha256: str | None = None

    @field_validator("filename")
    @classmethod
    def retain_basename(cls, value: str) -> str:
        filename = PurePath(value.strip().replace("\\", "/")).name
        if not filename or filename in {".", ".."} or "\x00" in filename:
            raise ValueError("filename must contain a basename.")
        return filename

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not SHA256_PATTERN.fullmatch(value):
            raise ValueError("sha256 must be lowercase hexadecimal.")
        return value


class AssetSummary(StrictSchema):
    id: str
    status: str
    content_type: str
    size_bytes: int


class UploadDescriptor(StrictSchema):
    method: Literal["PUT"]
    url: str
    headers: dict[str, str]
    expires_at: datetime


class UploadIntentResponse(StrictSchema):
    asset: AssetSummary
    upload: UploadDescriptor


class UploadCompleteResponse(StrictSchema):
    id: str
    status: str
    content_type: str
    size_bytes: int


class AssetDownloadResponse(StrictSchema):
    id: str
    content_type: str
    size_bytes: int
    sha256: str | None
    download_url: str
    download_url_expires_at: datetime
