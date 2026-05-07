from __future__ import annotations

from typing import Literal

from pydantic import Field

from ..schemas import StrictServiceModel


class VideoPrompt(StrictServiceModel):
    scene_id: str
    provider: Literal["fal_kling"]
    endpoint: Literal["fal-ai/kling-video/v3/standard/image-to-video"]
    start_image_path: str
    duration: str
    generate_audio: bool
    prompt: str = Field(min_length=1)
    negative_prompt: str = Field(min_length=1)
    cfg_scale: float


class VideoPromptGeneratorOutput(StrictServiceModel):
    video_prompts: list[VideoPrompt] = Field(min_length=1)
