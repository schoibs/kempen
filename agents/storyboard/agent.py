from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..base import BaseAgent
from ..schemas import STORYBOARD_SCHEMA
from .prompt import SYSTEM_PROMPT


class StoryboardAgent(BaseAgent):
    """Plan video scenes and shot sequences from a narrative strategy."""

    name = "storyboard_agent"
    schema_name = "campaign_storyboard"
    output_schema = STORYBOARD_SCHEMA
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.4

    def run(
        self,
        *,
        product_analysis: dict[str, Any],
        narrative_strategy: dict[str, Any],
        product_image_path: str | Path,
        target_duration_sec: int = 15,
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
    ) -> dict[str, Any]:
        storyboard_brief = {
            "product_analysis": product_analysis,
            "narrative_strategy": narrative_strategy,
            "product_image_path": str(product_image_path),
            "target_duration_sec": target_duration_sec,
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio,
            "scene_guidance": (
                "Ensure that the total durations of all scenes add up to the target_duration_sec value."
                "Use the provided product image path as the reference image path "
                "for starting images unless a later generated start frame is "
                "explicitly needed."
            ),
        }
        return self._call_json(
            user_content=f"Create the storyboard from this brief:\n {json.dumps(storyboard_brief, indent=2)}",
            temperature=0.4,
        )
