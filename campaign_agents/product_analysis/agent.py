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
