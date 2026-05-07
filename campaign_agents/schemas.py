from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Color(StrictModel):
    name: str
    hex: str = Field(description="Best-effort hex color in #RRGGBB format.")


class PreservationConstraints(StrictModel):
    must_preserve: list[str]
    must_not_introduce: list[str]


class ProductAnalysisOutput(StrictModel):
    product_name: str
    category: str
    primary_colors: Color
    visible_text: list[str]
    preservation_constraints: PreservationConstraints


class NarrativeStrategyOutput(StrictModel):
    concept_title: str
    hook: str
    message: str
    tone: list[str] = Field(min_length=1)
    cta: str


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


PRODUCT_ANALYSIS_SCHEMA = ProductAnalysisOutput.model_json_schema()
NARRATIVE_STRATEGY_SCHEMA = NarrativeStrategyOutput.model_json_schema()
STORYBOARD_SCHEMA = StoryboardOutput.model_json_schema()
