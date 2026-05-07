from __future__ import annotations

from typing import Any


COLOR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "hex": {
            "type": "string",
            "description": "Best-effort hex color in #RRGGBB format.",
        },
    },
    "required": ["name", "hex"],
}

PRODUCT_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "product_name": {"type": "string"},
        "category": {"type": "string"},
        "primary_colors": COLOR_SCHEMA,
        "visible_text": {
            "type": "array",
            "items": {"type": "string"},
        },
        "preservation_constraints": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "must_preserve": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "must_not_introduce": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["must_preserve", "must_not_introduce"],
        },
    },
    "required": [
        "product_name",
        "category",
        "primary_colors",
        "visible_text",
        "preservation_constraints",
    ],
}

NARRATIVE_STRATEGY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "concept_title": {"type": "string"},
        "hook": {"type": "string"},
        "message": {"type": "string"},
        "tone": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "cta": {"type": "string"},
    },
    "required": ["concept_title", "hook", "message", "tone", "cta"],
}

SHOT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "shot_id": {"type": "string"},
        "duration_sec": {"type": "number"},
        "framing": {"type": "string"},
        "camera_motion": {"type": "string"},
        "subject_motion": {"type": "string"},
        "environment_motion": {"type": "string"},
        "transition": {"type": "string"},
    },
    "required": [
        "shot_id",
        "duration_sec",
        "framing",
        "camera_motion",
        "subject_motion",
        "environment_motion",
        "transition",
    ],
}

SFX_CUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "at_sec": {"type": "number"},
        "cue": {"type": "string"},
        "linked_visual_action": {"type": "string"},
    },
    "required": ["at_sec", "cue", "linked_visual_action"],
}

SCENE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "duration_sec": {"type": "number"},
        "visual_purpose": {"type": "string"},
        "narrative_beat": {"type": "string"},
        "starting_image": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "image_path": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["image_path", "description"],
        },
        "scene_intent": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "audience_feeling": {"type": "string"},
                "cinematic_style": {"type": "string"},
                "pace": {"type": "string"},
            },
            "required": ["audience_feeling", "cinematic_style", "pace"],
        },
        "shot_sequence": {
            "type": "array",
            "items": SHOT_SCHEMA,
            "minItems": 1,
        },
        "audio_direction": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "generate_audio": {"type": "boolean"},
                "mode": {"type": "string"},
                "ambience": {"type": "string"},
                "sfx_timeline": {
                    "type": "array",
                    "items": SFX_CUE_SCHEMA,
                },
                "dialogue": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "generate_audio",
                "mode",
                "ambience",
                "sfx_timeline",
                "dialogue",
            ],
        },
        "text_overlay": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "enabled": {"type": "boolean"},
                "copy": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ],
                },
                "safe_area": {"type": "string"},
            },
            "required": ["enabled", "copy", "safe_area"],
        },
        "continuity": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "previous_scene_transition": {"type": "string"},
                "next_scene_transition": {"type": "string"},
                "continuity_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "previous_scene_transition",
                "next_scene_transition",
                "continuity_requirements",
            ],
        },
    },
    "required": [
        "id",
        "duration_sec",
        "visual_purpose",
        "narrative_beat",
        "starting_image",
        "scene_intent",
        "shot_sequence",
        "audio_direction",
        "text_overlay",
        "continuity",
    ],
}

STORYBOARD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "total_duration_sec": {"type": "number"},
        "aspect_ratio": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": SCENE_SCHEMA,
            "minItems": 1,
        },
    },
    "required": ["total_duration_sec", "aspect_ratio", "scenes"],
}
