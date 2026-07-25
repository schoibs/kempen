from __future__ import annotations

import logging

from pathlib import Path
from dotenv import load_dotenv
from typing import Any

from domain.campaigns import CampaignInput
from domain.orchestration import CampaignStageOperations
from logging_config import configure_logging 
from services import StoryboardGeneratorServiceOutput, VideoGeneratorServiceOutput


load_dotenv()
logger = logging.getLogger(__name__)
LOCAL_STORYBOARD_OUTPUT_PATH = Path("assets/generated/storyboard_sheet.png")
LOCAL_VIDEO_OUTPUT_PATH = Path("assets/generated/campaign_video.mp4")


class CampaignAgentPipeline:
    """Run campaign planning agents for a campaign brief."""

    def __init__(
        self,
        campaign_input: CampaignInput,
        operations: CampaignStageOperations | None = None,
    ) -> None:
        self.campaign_input = campaign_input
        self.operations = operations or CampaignStageOperations()

    def run(self) -> dict[str, Any]:
        logger.info("Campaign pipeline started.")
        result = self.operations.run_synchronously(
            self.campaign_input,
            storyboard_output_path=LOCAL_STORYBOARD_OUTPUT_PATH,
            video_output_path=LOCAL_VIDEO_OUTPUT_PATH,
        )
        return {
            "input": result["input"],
            "product_analysis": result["product_analysis"],
            "narrative_strategy": result["narrative_strategy"],
            "storyboard": StoryboardGeneratorServiceOutput(**result["storyboard"]),
            "video": VideoGeneratorServiceOutput(**result["video"]),
        }


if __name__ == "__main__":
    configure_logging()

    pipeline = CampaignAgentPipeline(
        campaign_input=CampaignInput(
            product_image_path="assets/prime.png",
            campaign_theme="bright, sunny and fun",
            target_audience="young adults who love summer festivals, beach parties and clubs",
        )
    )
    pipeline.run()
