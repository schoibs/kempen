from __future__ import annotations

from dataclasses import asdict, dataclass
from dotenv import load_dotenv

from typing import Any

from campaign_agents import NarrativeStrategistAgent, ProductAnalysisAgent
from campaign_agents import StoryboardAgent
from services import ImagePromptGeneratorService, VideoPromptGeneratorService


load_dotenv()


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

    def __init__(
        self,
        campaign_input: CampaignInput,
    ) -> None:
        self.campaign_input = campaign_input
        self.product_agent = ProductAnalysisAgent()
        self.narrative_agent = NarrativeStrategistAgent()
        self.storyboard_agent = StoryboardAgent()
        self.image_prompt_service = ImagePromptGeneratorService()
        self.video_prompt_service = VideoPromptGeneratorService()

    def run(self) -> dict[str, Any]:

        campaign_input = self.campaign_input

        product_analysis = self.product_agent.run(
            product_image_path=campaign_input.product_image_path
        )

        narrative_strategy = self.narrative_agent.run(
            product_analysis=product_analysis,
            campaign_theme=campaign_input.campaign_theme,
            target_duration_sec=campaign_input.target_duration_sec,
            target_audience=campaign_input.target_audience,
        )

        # Generate storyboard
        storyboard = self.storyboard_agent.run(
            product_analysis=product_analysis,
            narrative_strategy=narrative_strategy,
            product_image_path=campaign_input.product_image_path,
            target_duration_sec=campaign_input.target_duration_sec,
            aspect_ratio=campaign_input.aspect_ratio,
        )

        # Given the storyboard, generate the prompt needed for the starting images
        image_prompts = self.image_prompt_service.run(
            storyboard=storyboard,
            product_analysis=product_analysis,
            narrative_strategy=narrative_strategy,
            product_image_path=campaign_input.product_image_path,
        )

        # Given the storyboard, generate the prompt needed for the scenes
        video_prompts = self.video_prompt_service.run(
            storyboard=storyboard,
            product_analysis=product_analysis,
            narrative_strategy=narrative_strategy,
        )

        return {
            "input": campaign_input.to_dict(),
            "product_analysis": product_analysis,
            "narrative_strategy": narrative_strategy,
            "storyboard": storyboard,
            "image_prompts": image_prompts,
            "video_prompts": video_prompts,
        }


if __name__ == "__main__":
    pipeline = CampaignAgentPipeline(
        campaign_input=CampaignInput(
            product_image_path="",
            campaign_theme="",
            target_audience="",
        )
    )
    pipeline.run()
