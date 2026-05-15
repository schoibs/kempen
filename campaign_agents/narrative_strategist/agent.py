from __future__ import annotations

from typing import Any

from ..base import BaseAgent
from ..tools import tinyfish_web_search, web_fetch
from .prompt import SYSTEM_PROMPT
from .schema import NarrativeStrategyOutput


class NarrativeStrategistAgent(BaseAgent):
    """Create the campaign concept from product analysis and campaign inputs."""

    name = "narrative_strategist_agent"
    output_type = NarrativeStrategyOutput
    system_prompt = SYSTEM_PROMPT
    tools = [tinyfish_web_search, web_fetch]
    default_temperature = 1.0

    def run(
        self,
        product_analysis: dict[str, Any],
        campaign_theme: str,
        target_audience: str,
        target_duration_sec: int = 15,
    ) -> dict[str, Any]:
        return self._run_sdk(
            user_input=(
                "I want a creative and bold marketing narrative strategy for an upcoming campaign.\n"
                f"The campaign theme is {campaign_theme} and the intended target audience is {target_audience}.\n"
                f"Here is the details of the subject in question for the campaign that I am running: {product_analysis}\n"
                "Do research when coming up with the marketing narrative strategy.\n"
                "To research, first use the web search tool to run web searches, then use web fetch tool to extract comprehensive data from any URL."
            )            
        )
