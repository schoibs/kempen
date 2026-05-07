from __future__ import annotations

import json
from typing import Any

from ..base import BaseAgent
from ..tools import tinyfish_web_search
from .prompt import SYSTEM_PROMPT
from .schema import NarrativeStrategyOutput


class NarrativeStrategistAgent(BaseAgent):
    """Create the campaign concept from product analysis and campaign inputs."""

    name = "narrative_strategist_agent"
    output_type = NarrativeStrategyOutput
    system_prompt = SYSTEM_PROMPT
    tools = [tinyfish_web_search]
    default_temperature = 0.5

    def run(
        self,
        product_analysis: dict[str, Any],
        campaign_theme: str,
        target_audience: str,
        target_duration_sec: int = 15,
        research_context: str | list[str] | None = None,
    ) -> dict[str, Any]:
        return {'concept_title': 'Sun-Soaked Energy Drop', 'hook': 'A single bottle, center frame, that looks like summer in one glance.', 'message': 'Keep the visual dead simple and high-impact: the bright yellow PRIME Hydration Lemonade bottle stays perfectly centered on a clean white background, letting the color do the talking. The narrative should feel like a quick burst of sunny festival energy—fresh, playful, and ready for beach days, late nights, and everything in between. Since the product itself is the hero, the strategy is to frame it as the visual equivalent of a summer mood: bold, crisp, and instantly recognizable. No extra props or scenery—just a clean product spotlight that feels premium, upbeat, and made for young adults chasing fun.', 'tone': ['bright', 'sunny', 'fun', 'youthful', 'clean', 'premium', 'energetic'], 'cta': 'Spot the yellow. Grab the vibe.'}

        brief = {
            "product_analysis": product_analysis,
            "campaign_theme": campaign_theme,
            "target_duration_sec": target_duration_sec,
            "target_audience": target_audience,
            "research_context": research_context or "No external research context supplied.",
        }

        return self._run_sdk(
            user_input=f"Create the campaign narrative strategy from this brief:\n{json.dumps(brief, indent=2)}"
        )
