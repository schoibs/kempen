from __future__ import annotations

from enum import Enum


class StringEnum(str, Enum):
    """Python 3.10-compatible string enum base."""

    def __str__(self) -> str:
        return self.value


class CampaignStatus(StringEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageStatus(StringEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_EXTERNAL = "waiting_external"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CampaignStage(StringEnum):
    VALIDATE_INPUT = "validate_input"
    PRODUCT_ANALYSIS = "product_analysis"
    NARRATIVE_STRATEGY = "narrative_strategy"
    STORYBOARD_GENERATION = "storyboard_generation"
    VIDEO_SUBMISSION = "video_submission"
    VIDEO_POLL = "video_poll"
    VIDEO_FINALIZE = "video_finalize"
    FINALIZE_CAMPAIGN = "finalize_campaign"


class PublicStage(StringEnum):
    VALIDATING_INPUT = "validating_input"
    ANALYZING_PRODUCT = "analyzing_product"
    BUILDING_NARRATIVE = "building_narrative"
    GENERATING_STORYBOARD = "generating_storyboard"
    GENERATING_VIDEO = "generating_video"
    FINALIZING = "finalizing"


STAGE_ORDER: tuple[CampaignStage, ...] = tuple(CampaignStage)

PUBLIC_STAGE_BY_STAGE: dict[CampaignStage, PublicStage] = {
    CampaignStage.VALIDATE_INPUT: PublicStage.VALIDATING_INPUT,
    CampaignStage.PRODUCT_ANALYSIS: PublicStage.ANALYZING_PRODUCT,
    CampaignStage.NARRATIVE_STRATEGY: PublicStage.BUILDING_NARRATIVE,
    CampaignStage.STORYBOARD_GENERATION: PublicStage.GENERATING_STORYBOARD,
    CampaignStage.VIDEO_SUBMISSION: PublicStage.GENERATING_VIDEO,
    CampaignStage.VIDEO_POLL: PublicStage.GENERATING_VIDEO,
    CampaignStage.VIDEO_FINALIZE: PublicStage.GENERATING_VIDEO,
    CampaignStage.FINALIZE_CAMPAIGN: PublicStage.FINALIZING,
}

TERMINAL_CAMPAIGN_STATUSES = frozenset(
    {
        CampaignStatus.SUCCEEDED,
        CampaignStatus.FAILED,
        CampaignStatus.CANCELLED,
    }
)

PROGRESS_PERCENT_BY_STAGE: dict[CampaignStage, int] = {
    CampaignStage.VALIDATE_INPUT: 5,
    CampaignStage.PRODUCT_ANALYSIS: 10,
    CampaignStage.NARRATIVE_STRATEGY: 35,
    CampaignStage.STORYBOARD_GENERATION: 60,
    CampaignStage.VIDEO_SUBMISSION: 80,
    CampaignStage.VIDEO_POLL: 80,
    CampaignStage.VIDEO_FINALIZE: 80,
    CampaignStage.FINALIZE_CAMPAIGN: 95,
}
