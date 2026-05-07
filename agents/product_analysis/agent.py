from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import BaseAgent
from ..schemas import PRODUCT_ANALYSIS_SCHEMA
from ..utils import image_to_data_url
from .prompt import SYSTEM_PROMPT


class ProductAnalysisAgent(BaseAgent):
    """Extract visible product facts and preservation constraints from an image."""

    name = "product_analysis_agent"
    schema_name = "product_analysis"
    output_schema = PRODUCT_ANALYSIS_SCHEMA
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.1

    def run(self, product_image_path: str | Path) -> dict[str, Any]:
        image_path = str(product_image_path)
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Research and extract the visible facts and constraints for "
                    f"this product image: {image_path}. Include preservation "
                    "constraints that will keep generated images/videos faithful "
                    "to the shown subject."
                ),
            },
            {
                "type": "image_url",
                "image_url": {"url": image_to_data_url(image_path)},
            },
        ]
        return self._call_json(user_content=user_content, temperature=0.1)
