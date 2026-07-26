from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, StrictInt, field_validator

from api.schemas.assets import AssetDownloadResponse, StrictSchema


SUPPORTED_ASPECT_RATIOS = (
    "auto",
    "21:9",
    "16:9",
    "4:3",
    "1:1",
    "3:4",
    "9:16",
)


class CreateCampaignRequest(StrictSchema):
    product_image_asset_id: str = Field(min_length=1, max_length=64)
    campaign_theme: str = Field(min_length=1, max_length=2000)
    target_audience: str = Field(min_length=1, max_length=2000)
    target_duration_sec: StrictInt = Field(default=15, ge=4, le=15)
    aspect_ratio: Literal["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"] = "9:16"

    @field_validator("campaign_theme", "target_audience")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank.")
        return normalized


class CampaignLinks(StrictSchema):
    self: str
    cancel: str


class CampaignAcceptedResponse(StrictSchema):
    id: str
    status: str
    stage: str
    progress_percent: int
    created_at: datetime
    updated_at: datetime
    links: CampaignLinks


class CampaignInputResponse(StrictSchema):
    product_image_asset_id: str
    campaign_theme: str
    target_audience: str
    target_duration_sec: int
    aspect_ratio: str


class CampaignResultsResponse(StrictSchema):
    product_analysis: dict[str, object] | None
    narrative_strategy: dict[str, object] | None
    storyboard: AssetDownloadResponse | None
    video: AssetDownloadResponse | None


class CampaignErrorResponse(StrictSchema):
    code: str
    message: str
    retryable: bool


class CampaignDetailResponse(CampaignAcceptedResponse):
    completed_stages: int
    total_stages: int
    input: CampaignInputResponse
    results: CampaignResultsResponse
    error: CampaignErrorResponse | None
    started_at: datetime | None
    completed_at: datetime | None


class CampaignSummaryResponse(CampaignAcceptedResponse):
    completed_stages: int
    total_stages: int


class CampaignListResponse(StrictSchema):
    items: list[CampaignSummaryResponse]
    next_cursor: str | None
