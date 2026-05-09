from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


_STORYBOARD_REF_PATTERN = re.compile(r"@(main_subject|subject_id_\d+)\b")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ElementBinding(StrictModel):
    storyboard_ref: str = Field(pattern=r"^@(main_subject|subject_id_\d+)$")
    kling_ref: str = Field(pattern=r"^@Element[1-9]\d*$")
    description: str = Field(min_length=1)


class KlingMultiPromptElement(StrictModel):
    prompt: str = Field(min_length=1)
    duration: int = Field(ge=1, le=15)


class TextOverlayInstruction(StrictModel):
    required: bool
    copy_text: str | None
    safe_area: str
    render_in_video_model: bool

    @model_validator(mode="after")
    def validate_render_policy(self) -> "TextOverlayInstruction":
        if self.render_in_video_model:
            raise ValueError("text overlays must be composited later, not generated in Kling")
        return self


class KlingScenePromptPayload(StrictModel):
    prompt: str | None = Field(min_length=1)
    multi_prompt: list[KlingMultiPromptElement] | None
    duration: int = Field(ge=3, le=15)
    shot_type: Literal["customize"] | None
    negative_prompt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_prompt_shape(self) -> "KlingScenePromptPayload":
        has_prompt = self.prompt is not None
        has_multi_prompt = bool(self.multi_prompt)

        if has_prompt == has_multi_prompt:
            raise ValueError("exactly one of prompt or multi_prompt must be provided")

        if has_multi_prompt:
            if self.shot_type != "customize":
                raise ValueError('shot_type must be "customize" when multi_prompt is used')

            total_multi_duration = sum(item.duration for item in self.multi_prompt or [])
            if total_multi_duration != self.duration:
                raise ValueError("multi_prompt durations must sum to scene duration")
        elif self.shot_type is not None:
            raise ValueError("shot_type is only allowed when multi_prompt is used")

        return self

    def positive_prompt_text(self) -> str:
        if self.prompt is not None:
            return self.prompt
        return "\n".join(item.prompt for item in self.multi_prompt or [])


class SceneVideoPromptDraft(StrictModel):
    scene_id: str
    prompt_mode: Literal["single", "multi"]
    element_refs: list[str] = Field(min_length=1)
    prompt: str | None = Field(min_length=1)
    multi_prompt: list[KlingMultiPromptElement] | None

    @model_validator(mode="after")
    def validate_prompt_shape(self) -> "SceneVideoPromptDraft":
        has_prompt = self.prompt is not None
        has_multi_prompt = bool(self.multi_prompt)

        if has_prompt == has_multi_prompt:
            raise ValueError("exactly one of prompt or multi_prompt must be provided")

        expected_mode = "multi" if has_multi_prompt else "single"
        if self.prompt_mode != expected_mode:
            raise ValueError("prompt_mode must match prompt shape")

        return self

    def positive_prompt_text(self) -> str:
        if self.prompt is not None:
            return self.prompt
        return "\n".join(item.prompt for item in self.multi_prompt or [])


class VideoPromptDraftOutput(StrictModel):
    scene_prompts: list[SceneVideoPromptDraft] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_output(self) -> "VideoPromptDraftOutput":
        scene_ids = [scene.scene_id for scene in self.scene_prompts]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene ids must be unique")
        return self


class SceneVideoPrompt(StrictModel):
    scene_id: str
    duration_sec: float = Field(gt=0)
    prompt_mode: Literal["single", "multi"]
    start_image_strategy: str = Field(min_length=1)
    element_refs: list[str] = Field(min_length=1)
    text_overlay: TextOverlayInstruction
    payload: KlingScenePromptPayload

    @model_validator(mode="after")
    def validate_scene_prompt(self) -> "SceneVideoPrompt":
        if self.duration_sec != self.payload.duration:
            raise ValueError("duration_sec must match payload.duration")

        payload_is_multi = bool(self.payload.multi_prompt)
        expected_mode = "multi" if payload_is_multi else "single"
        if self.prompt_mode != expected_mode:
            raise ValueError("prompt_mode must match payload prompt shape")

        positive_prompt_text = self.payload.positive_prompt_text()
        if _STORYBOARD_REF_PATTERN.search(positive_prompt_text):
            raise ValueError("final prompts must use Kling @ElementN refs, not storyboard refs")

        if not any(element_ref in positive_prompt_text for element_ref in self.element_refs):
            raise ValueError("final prompts must reference at least one listed Kling element")

        copy_text = self.text_overlay.copy_text
        if copy_text and copy_text.lower() in positive_prompt_text.lower():
            raise ValueError("overlay copy must not appear in Kling prompt text")

        return self


class VideoPromptGeneratorOutput(StrictModel):
    aspect_ratio: str
    element_bindings: list[ElementBinding] = Field(min_length=1)
    scene_prompts: list[SceneVideoPrompt] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_output(self) -> "VideoPromptGeneratorOutput":
        scene_ids = [scene.scene_id for scene in self.scene_prompts]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene ids must be unique")

        storyboard_refs = [binding.storyboard_ref for binding in self.element_bindings]
        if len(storyboard_refs) != len(set(storyboard_refs)):
            raise ValueError("storyboard refs must be unique")

        kling_refs = [binding.kling_ref for binding in self.element_bindings]
        if len(kling_refs) != len(set(kling_refs)):
            raise ValueError("Kling refs must be unique")

        known_kling_refs = set(kling_refs)
        for scene in self.scene_prompts:
            unknown_refs = set(scene.element_refs) - known_kling_refs
            if unknown_refs:
                raise ValueError(f"unknown Kling element refs: {sorted(unknown_refs)}")

        return self
