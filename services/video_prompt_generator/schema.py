from __future__ import annotations

from pydantic import Field

from ..schemas import StrictServiceModel


class VideoPrompt(StrictServiceModel):
    scene_id: str
    prompt: str = Field(min_length=1)
    negative_prompt: str = Field(min_length=1)


class VideoPromptGeneratorOutput(StrictServiceModel):
    video_prompts: list[VideoPrompt] = Field(min_length=1)
