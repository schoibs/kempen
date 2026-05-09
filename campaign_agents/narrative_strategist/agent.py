from __future__ import annotations

import json
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
        # return {'concept_title': 'Sun-Soaked Energy Drop', 'hook': 'A single bottle, center frame, that looks like summer in one glance.', 'message': 'Keep the visual dead simple and high-impact: the bright yellow PRIME Hydration Lemonade bottle stays perfectly centered on a clean white background, letting the color do the talking. The narrative should feel like a quick burst of sunny festival energy—fresh, playful, and ready for beach days, late nights, and everything in between. Since the product itself is the hero, the strategy is to frame it as the visual equivalent of a summer mood: bold, crisp, and instantly recognizable. No extra props or scenery—just a clean product spotlight that feels premium, upbeat, and made for young adults chasing fun.', 'tone': ['bright', 'sunny', 'fun', 'youthful', 'clean', 'premium', 'energetic'], 'cta': 'Spot the yellow. Grab the vibe.'}
        return {'concept': 'Turn PRIME Hydration Lemonade into the unofficial sun-ritual of summer nightlife: a bright yellow ‘day-to-night’ hydration icon that starts at the beach, powers the festival, and survives the afterparty without becoming an energy-drink cliché.', 'key_message': 'PRIME Hydration Lemonade brings bright, caffeine-free refreshment with electrolytes and coconut water for all-day summer momentum.', 'campaign_slogan': 'Bright by day. Ready by night. PRIME Lemonade keeps the summer alive.', 'story_premise': 'A young adult crew chases one endless summer day—from sunrise beach setup to a noon festival, then into a neon club afterparty. Every scene is powered by the same yellow bottle, which becomes the crew’s ritual object for staying cool, collected, and socially untouchable while the sun keeps trying to win.', 'hook': 'A blinding yellow bottle lands in slow motion on hot sand like a tiny sun, and the whole beach scene seems to ‘charge up’ around it as the first sip triggers a chain reor, music, and movement.', 'conflict': 'The summer is too intense: heat, sweat, dehydration, sensory overload, and social stamina all collide. Everyone wants to keep the vibe going, but the body starts calling timeout. The bottle is the answer to the festival-beach-club marathon, but the challenge is making hydration feel like part of the party—not a break from it.', 'tone': ['sun-soaked', 'electric', 'playful', 'stylish', 'youthful', 'slightly surreal', 'festival-rave energy', 'boldly minimal'], 'cta': 'Grab a PRIME Lemonade and keep your summer on.'}

        return self._run_sdk(
            user_input=(
                "I want a creative and bold marketing narrative strategy for an upcoming campaign.\n"
                f"The campaign theme is {campaign_theme} and the intended target audience is {target_audience}.\n"
                f"Here is the details of the subject in question for the campaign that I am running: {product_analysis}\n"
                "Do research when coming up with the marketing narrative strategy.\n"
                "To research, first use the web search tool to run web searches, then use web fetch tool to extract comprehensive data from any URL."
            )            
        )
