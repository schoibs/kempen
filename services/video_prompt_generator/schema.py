from __future__ import annotations

from typing import Literal

from pydantic import Field

from ..schemas import StrictServiceModel


KlingDuration = Literal[
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
]


class VideoPrompt(StrictServiceModel):
    scene_id: str
    provider: Literal["fal_kling"]
    endpoint: Literal["fal-ai/kling-video/v3/standard/image-to-video"]
    start_image_url: str = Field(min_length=1)
    duration: KlingDuration
    generate_audio: bool
    prompt: str = Field(min_length=1)
    negative_prompt: str = Field(min_length=1)
    cfg_scale: float = Field(ge=0)


class VideoPromptGeneratorOutput(StrictServiceModel):
    video_prompts: list[VideoPrompt] = Field(min_length=1)
