from __future__ import annotations

import logging

from dataclasses import asdict, dataclass
from dotenv import load_dotenv
from typing import Any

from logging_config import configure_logging 
from campaign_agents import NarrativeStrategistAgent, ProductAnalysisAgent
from campaign_agents import StoryboardAgent
from services import VideoPromptGeneratorService


load_dotenv()
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CampaignInput:
    product_image_path: str
    campaign_theme: str
    target_audience: str
    target_duration_sec: int = 15
    aspect_ratio: str = "9:16"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CampaignAgentPipeline:
    """Run campaign planning agents, then generate image and video prompts."""

    def __init__(self, campaign_input: CampaignInput) -> None:
        self.campaign_input = campaign_input
        self.product_agent = ProductAnalysisAgent(model="gpt-5.4-mini")
        self.narrative_agent = NarrativeStrategistAgent(model="gpt-5.4-mini")
        self.storyboard_agent = StoryboardAgent(model="gpt-5.4-mini")
        self.video_prompt_service = VideoPromptGeneratorService(model="gpt-5.4-mini")

    def run(self) -> dict[str, Any]:
        logger.info("Pipeline initialized...")
        campaign_input = self.campaign_input

        logger.info("Campaign inputs: %s", campaign_input)

        product_analysis = self.product_agent.run(
            product_image_path=campaign_input.product_image_path
        )

        logger.info(f"{product_analysis=}")

        narrative_strategy = self.narrative_agent.run(
            product_analysis=product_analysis,
            campaign_theme=campaign_input.campaign_theme,
            target_duration_sec=campaign_input.target_duration_sec,
            target_audience=campaign_input.target_audience,
        )

        logger.info(f"{narrative_strategy=}")

        # Generate storyboard
        storyboard = self.storyboard_agent.run(
            product_analysis=product_analysis,
            narrative_strategy=narrative_strategy,
            product_image_path=campaign_input.product_image_path,
            target_duration_sec=campaign_input.target_duration_sec,
            aspect_ratio=campaign_input.aspect_ratio,
        )

        logger.info(f"{storyboard=}")

        video_prompts = self.video_prompt_service.run(
            storyboard=storyboard,
            prompt_mode="auto",
        )

        logger.info(f"{video_prompts=}")

        raise Exception("stop here")
        
        return {
            "input": campaign_input.to_dict(),
            "product_analysis": product_analysis,
            "narrative_strategy": narrative_strategy,
            "storyboard": storyboard,
            "video_prompts": video_prompts,
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
