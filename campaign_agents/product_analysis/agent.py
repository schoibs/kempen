from __future__ import annotations

import logging

from pathlib import Path
from typing import Any

from ..base import BaseAgent
from ..tools import tinyfish_web_search, web_fetch
from ..utils import image_to_data_url
from .prompt import SYSTEM_PROMPT
from .schema import ProductAnalysisOutput


logger = logging.getLogger(__name__)


class ProductAnalysisAgent(BaseAgent):
    """Extract visible product facts and preservation constraints from an image."""

    name = "product_analysis_agent"
    output_type = ProductAnalysisOutput
    tools = [tinyfish_web_search, web_fetch]
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.7

    def run(self, product_image_path: str | Path) -> dict[str, Any]:
        # return {'product_name': 'PRIME Hydration Lemonade flavour bottle', 'category': 'Beverage / sports drink', 'primary_colors': {'name': 'bright yellow', 'hex': '#F6E300'}, 'visible_text': ['LEMONADE', 'FLAVOUR', 'PRIME', 'HYDRATION', '500 mL'], 'preservation_constraints': {'must_preserve': ['Tall plastic bottle with rounded shoulders and yellow cap', 'Bright yellow bottle/body with black vertical PRIME wordmark', "Small 'LEMONADE' text near the top and 'FLAVOUR' beneath it", "'HYDRATION' and '500 mL' text near the bottom", 'Clean white background with centered single-product composition'], 'must_not_introduce': ['Additional objects, hands, or scenery', 'Different bottle shape or cap color', 'New labels, badges, or flavor claims not visible', 'Changes to the visible text layout or orientation', 'Dark or colored background that changes the product presentation']}}

        image_path = str(product_image_path)
        user_content: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"You are given the following image: {image_path}.\n"
                            "Identify the main subject(s) in the image, then analyze and research the identified subject(s).\n"
                            "You may use the web search tool."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": image_to_data_url(image_path),
                    },
                ],
            },
        ]
        return self._run_sdk(user_content)
