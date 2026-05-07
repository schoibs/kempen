from __future__ import annotations

from dataclasses import asdict, dataclass
from dotenv import load_dotenv

from typing import Any, Optional

from agents import NarrativeStrategistAgent, ProductAnalysisAgent
from agents import StoryboardAgent
from clients import LLMClient


load_dotenv()


@dataclass(frozen=True)
class CampaignInput:
    product_image_path: str
    campaign_theme: str
    target_duration_sec: int = 15
    aspect_ratio: str = "9:16"
    target_audience: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CampaignAgentPipeline:
    """Run the three campaign planning agents in sequence."""

    def __init__(self, campaign_input: CampaignInput) -> None:
        shared_client = LLMClient()
        self.campaign_input = campaign_input
        self.product_agent = ProductAnalysisAgent(shared_client)
        self.narrative_agent = NarrativeStrategistAgent(shared_client)
        self.storyboard_agent = StoryboardAgent(shared_client)

    def run(self) -> dict[str, Any]:

        campaign_input = self.campaign_input
        
        # Analyse product
        product_analysis = self.product_agent.run(
            product_image_path=campaign_input.product_image_path
        )

        # Generate narrative strategy
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
        
        return {
            "input": campaign_input.to_dict(),
            "product_analysis": product_analysis,
            "narrative_strategy": narrative_strategy,
            "storyboard": storyboard,
        }

pipeline = CampaignAgentPipeline(
    campaign_input=CampaignInput(
        product_image_path="",
        campaign_theme="",

    )
)
pipeline.run()
