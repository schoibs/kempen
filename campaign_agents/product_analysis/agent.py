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
        # TODO: to remove this comment
        # return {'product_name': 'PRIME Hydration Lemonade', 'category': 'Sports drink / hydration beverage', 'primary_colors': {'name': 'Yellow', 'hex': '#F6E300'}, 'visible_facts': ['A bright yellow bottle of PRIME Hydration is shown.', 'The label says "LEMONADE" and "FLAVOUR".', 'The front label prominently displays the word "PRIME" vertically in black.', 'The bottle says "HYDRATION" and "500 mL" near the bottom.', 'The bottle has a yellow cap and a clear neck.', 'The packaging is minimal and uses high-contrast black text on a yellow background.'], 'additional_facts': ['Official PRIME product pages describe Lemonade Hydration as zero added sugar, 25 calories, caffeine-free, with 10% coconut water, BCAAs, B vitamins, antioxidants, and electrolytes.', 'PRIME positions this drink as a hydration-focused sports beverage rather than an energy drink.', 'Search results show the product is sold in a 500 mL bottle and also in multipacks.', 'Ingredient listings from retail pages commonly include water, coconut water concentrate, citric acid, dipotassium phosphate, natural flavors, magnesium citrate, sucralose, and amino acids such as L-leucine and L-isoleucine.', 'The flavor is part of PRIME Hydration’s broader lineup that includes options like Strawberry Watermelon, Ice Pop, Blue Raspberry, Tropical Punch, and Lemon Lime.']}     
        
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
