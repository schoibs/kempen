from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from ..schemas import StrictModel


_DURATION_TOLERANCE_SEC = 0.01


class Shot(StrictModel):
    shot_id: str
    duration_sec: float = Field(gt=0)
    framing: str
    camera_motion: str
    subject_motion: str
    environment_motion: str
    transition: str


class SfxCue(StrictModel):
    at_sec: float = Field(ge=0)
    cue: str
    linked_visual_action: str


class StartingImage(StrictModel):
    image_path: str
    description: str


class SceneIntent(StrictModel):
    audience_feeling: str
    cinematic_style: str
    pace: str


class AudioDirection(StrictModel):
    generate_audio: bool
    mode: str
    ambience: str
    sfx_timeline: list[SfxCue]
    dialogue: list[str]


class TextOverlay(StrictModel):
    enabled: bool
    copy_text: str | None = Field(alias="copy")
    safe_area: str


class Continuity(StrictModel):
    previous_scene_transition: str
    next_scene_transition: str
    continuity_requirements: list[str]


class Scene(StrictModel):
    id: str
    duration_sec: float = Field(gt=0)
    visual_purpose: str
    narrative_beat: str
    starting_image: StartingImage
    scene_intent: SceneIntent
    shot_sequence: list[Shot] = Field(min_length=1)
    audio_direction: AudioDirection
    text_overlay: TextOverlay
    continuity: Continuity

    @model_validator(mode="after")
    def validate_shot_sequence(self) -> "Scene":
        shot_ids = [shot.shot_id for shot in self.shot_sequence]
        if len(shot_ids) != len(set(shot_ids)):
            raise ValueError("shot ids must be unique within a scene")

        total_shot_duration = sum(shot.duration_sec for shot in self.shot_sequence)
        if abs(total_shot_duration - self.duration_sec) > _DURATION_TOLERANCE_SEC:
            raise ValueError("shot durations must sum to scene duration_sec")

        return self


class StoryboardOutput(StrictModel):
    total_duration_sec: float = Field(gt=0)
    aspect_ratio: Literal["9:16"]
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scene_sequence(self) -> "StoryboardOutput":
        scene_ids = [scene.id for scene in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("scene ids must be unique")

        total_scene_duration = sum(scene.duration_sec for scene in self.scenes)
        if abs(total_scene_duration - self.total_duration_sec) > _DURATION_TOLERANCE_SEC:
            raise ValueError("scene durations must sum to total_duration_sec")

        return self
