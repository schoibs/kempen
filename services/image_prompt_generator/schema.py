from __future__ import annotations

from typing import Literal

from pydantic import Field

from ..schemas import StrictServiceModel


class ImagePrompt(StrictServiceModel):
    scene_id: str
    reference_image_path: str
    prompt: str = Field(min_length=1)


class ImagePromptGeneratorOutput(StrictServiceModel):
    image_prompts: list[ImagePrompt] = Field(min_length=1)
