from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import BaseAgent
from ..tools import tinyfish_web_search
from ..utils import image_to_data_url
from .prompt import SYSTEM_PROMPT
from .schema import ProductAnalysisOutput


class ProductAnalysisAgent(BaseAgent):
    """Extract visible product facts and preservation constraints from an image."""

    name = "product_analysis_agent"
    output_type = ProductAnalysisOutput
    tools = [tinyfish_web_search]
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.1

    def run(self, product_image_path: str | Path) -> dict[str, Any]:
        image_path = str(product_image_path)
        user_content: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract the visible facts and constraints for "
                            f"this product image: {image_path}. Include preservation "
                            "constraints that will keep generated images/videos faithful "
                            "to the shown subject. Use web search only if it helps clarify "
                            "current public context for visible product text or packaging."
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
