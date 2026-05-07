from __future__ import annotations

import json
from typing import Any

from ..base import BaseAgent
from ..schemas import NARRATIVE_STRATEGY_SCHEMA
from .prompt import SYSTEM_PROMPT


class NarrativeStrategistAgent(BaseAgent):
    """Create the campaign concept from product analysis and campaign inputs."""

    name = "narrative_strategist_agent"
    schema_name = "narrative_strategy"
    output_schema = NARRATIVE_STRATEGY_SCHEMA
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.5

    def run(
        self,
        product_analysis: dict[str, Any],
        campaign_theme: str,
        target_duration_sec: int = 15,
        target_audience: str = "general social audience",
        research_context: str | list[str] | None = None,
    ) -> dict[str, Any]:
        brief = {
            "product_analysis": product_analysis,
            "campaign_theme": campaign_theme,
            "target_duration_sec": target_duration_sec,
            "target_audience": target_audience,
            "research_context": research_context or "No external research context supplied.",
        }

        return self._call_json(
            user_content = f"Create the campaign narrative strategy from this brief:\n {json.dumps(brief, indent=2)}",
            temperature=0.5,
        )
