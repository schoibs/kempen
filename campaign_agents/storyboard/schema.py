from __future__ import annotations

from pydantic import Field

from ..schemas import StrictModel


class Shot(StrictModel):
    shot_id: str
    duration_sec: float
    framing: str
    camera_motion: str
    subject_motion: str
    environment_motion: str
    transition: str


class SfxCue(StrictModel):
    at_sec: float
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
    duration_sec: float
    visual_purpose: str
    narrative_beat: str
    starting_image: StartingImage
    scene_intent: SceneIntent
    shot_sequence: list[Shot] = Field(min_length=1)
    audio_direction: AudioDirection
    text_overlay: TextOverlay
    continuity: Continuity


class StoryboardOutput(StrictModel):
    total_duration_sec: float
    aspect_ratio: str
    scenes: list[Scene] = Field(min_length=1)
