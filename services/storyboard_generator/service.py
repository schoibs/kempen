from __future__ import annotations

import logging

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from clients import ImageGenerationClient, ImageGenerationClientError

from .prompt import build_storyboard_prompt


logger = logging.getLogger(__name__)


class StoryboardGeneratorServiceError(RuntimeError):
    """Raised when storyboard generation cannot produce usable output."""


@dataclass(frozen=True)
class StoryboardGeneratorServiceOutput:
    image_path: str


class StoryboardGeneratorService:
    """Generate a storyboard sheet image for the campaign."""

    default_model = "gpt-image-2"
    default_size = "1152x2048"
    default_quality = "medium"
    default_output_format = "png"
    default_output_path = Path("assets/generated/storyboard_sheet.png")

    def __init__(
        self,
        model: str = default_model,
        size: str = default_size,
        quality: str = default_quality,
        output_format: str = default_output_format,
        image_client: Any | None = None,
    ) -> None:
        self.model = model
        self.size = size
        self.quality = quality
        self.output_format = output_format
        self.image_client = image_client

    def run(
        self,
        *,
        product_image_path: str | Path,
        product_analysis: dict[str, Any],
        narrative_strategy: dict[str, Any],
        campaign_input: Any,
        output_path: str | Path | None = None,
    ) -> StoryboardGeneratorServiceOutput:
        campaign_input_dict = self._campaign_input_to_dict(campaign_input)
        output_path = Path(output_path or self.default_output_path)

        prompt = build_storyboard_prompt(
            product_analysis=product_analysis,
            narrative_strategy=narrative_strategy,
            campaign_input=campaign_input_dict,
        )

        logger.info(f"Generating storyboard sheet at {output_path}")
        try:
            generated_path = self._image_client().edit_with_reference(
                reference_image_path=product_image_path,
                prompt=prompt,
                output_path=output_path,
                size=self.size,
                quality=self.quality,
                output_format=self.output_format,
            )
        except (ImageGenerationClientError, OSError, ValueError) as exc:
            raise StoryboardGeneratorServiceError(f"Storyboard image generation failed: {exc}") from exc

        return StoryboardGeneratorServiceOutput(
            image_path=str(generated_path)
        )

    def _image_client(self) -> ImageGenerationClient:
        if self.image_client is None:
            self.image_client = ImageGenerationClient(model=self.model)
        return self.image_client

    @staticmethod
    def _campaign_input_to_dict(campaign_input: Any) -> dict[str, Any]:
        if isinstance(campaign_input, dict):
            return dict(campaign_input)
        if is_dataclass(campaign_input):
            return asdict(campaign_input)

        return {
            "product_image_path": getattr(campaign_input, "product_image_path", None),
            "campaign_theme": getattr(campaign_input, "campaign_theme", None),
            "target_audience": getattr(campaign_input, "target_audience", None),
            "target_duration_sec": getattr(campaign_input, "target_duration_sec", 15),
            "aspect_ratio": getattr(campaign_input, "aspect_ratio", "9:16"),
        }
