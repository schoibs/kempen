from __future__ import annotations

import json
from typing import Any

from ..base import BaseAgent
from ..schemas import NarrativeStrategyOutput
from .prompt import SYSTEM_PROMPT
from ..tools import tinyfish_web_search


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
