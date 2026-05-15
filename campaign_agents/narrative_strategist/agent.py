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
        return {
            "concept": "Turn PRIME Hydration Lemonade into the unofficial ‘sun-activated accessory’ of summer: a neon-yellow bottle that behaves like a portable festival prop, beach ritual, and club entrance stamp all at once. The campaign frames hydration as the thing that lets the party last longer, glow brighter, and look cooler while doing it.",
            "story_premise": "A group of young adults hits a heatwave-drenched summer circuit: beach at noon, festival by sunset, club after dark. In each scene, the bright yellow PRIME bottle becomes the same magical object—passed around like a totem, photographed like fashion, and carried like proof that you’re still going when everyone else is fading. The lemonade flavor is the sparkling, citrusy reset button that keeps the night alive without the crash of an energy drink.",
            "hook": "A sun-soaked opener where the bottle seems to ‘charge’ the scene: the moment PRIME Lemonade hits the frame, umbrellas pop brighter, bass gets louder, and the entire party color-grades from hot to electric yellow. Tag the idea as: ‘When the day gets too hot, the party turns PRIME.’",
            "conflict": "The heat, the sweat, the long queues, and the all-day-to-all-night stamina test threaten to drain the fun. Everyone wants to stay in the moment, but the body is trying to tap out. PRIME Lemonade solves the tension by positioning hydration as the rebellious move—the clean, cold, zero-caffeine answer to burnout, helping the crew keep their sparkle without switching to an energy-drink personality.",
            "tone": ["sun-drenched and euphoric", "playfully rebellious", "high-energy luxe"],
        }

        return self._run_sdk(
            user_input=(
                "I want a creative and bold marketing narrative strategy for an upcoming campaign.\n"
                f"The campaign theme is {campaign_theme} and the intended target audience is {target_audience}.\n"
                f"Here is the details of the subject in question for the campaign that I am running: {product_analysis}\n"
                "Do research when coming up with the marketing narrative strategy.\n"
                "To research, first use the web search tool to run web searches, then use web fetch tool to extract comprehensive data from any URL."
            )            
        )
