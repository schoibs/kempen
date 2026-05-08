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
        return {'product_name': 'PRIME Hydration Lemonade', 'category': 'sports drink / hydration beverage', 'primary_colors': {'name': 'yellow', 'hex': '#F8E71C'}, 'visible_facts': ['A bright yellow plastic bottle is shown.', 'The label reads PRIME in large vertical black letters with white outline.', 'The flavor shown is Lemonade.', 'The bottle says HYDRATION near the bottom.', 'The bottle size is 500 mL.', 'The cap is yellow.', 'The product appears to be a single-serve beverage bottle.', 'The design is minimal with a white background and bold branding.'], 'additional_facts': ['Official PRIME product page lists Hydration Lemonade as zero added sugar, 25 calories, 10% coconut water, BCAAs + B vitamins, antioxidants + electrolytes, and caffeine-free.', 'PRIME Hydration is marketed as a sports/hydration drink rather than an energy drink.', 'Common ingredient listings include filtered water, coconut water from concentrate, citric acid, dipotassium phosphate, sweeteners such as sucralose and acesulfame potassium, natural flavor, and added electrolytes/minerals.', 'The product is sold in multi-pack and single-bottle formats through retail and online channels.', 'Lemonade is one of several PRIME Hydration flavors, alongside options like Ice Pop, Blue Raspberry, Tropical Punch, and Lemon Lime.']}
        
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
                            "To research, first use the web search tool to run web searches, then use web fetch tool to extract comprehensive data from any URL."
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
