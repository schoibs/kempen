from __future__ import annotations

from typing import Literal

from pydantic import Field

from ..schemas import StrictServiceModel


class ImagePrompt(StrictServiceModel):
    scene_id: str
    model: Literal["gpt-image-2"]
    mode: Literal["edit_with_reference"]
    reference_image_path: str
    prompt: str = Field(min_length=1)
    size: Literal["1080x1920"]
    quality: Literal["high"]


class ImagePromptGeneratorOutput(StrictServiceModel):
    image_prompts: list[ImagePrompt] = Field(min_length=1)
