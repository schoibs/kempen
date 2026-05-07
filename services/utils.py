from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from .base import ServiceRunError


def model_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return value
    raise ServiceRunError(f"Expected a Pydantic model or dict, got {type(value).__name__}.")


def storyboard_scenes(storyboard: Any) -> list[dict[str, Any]]:
    storyboard_data = model_to_dict(storyboard)
    scenes = storyboard_data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ServiceRunError("Storyboard must contain a non-empty scenes list.")

    return [model_to_dict(scene) for scene in scenes]


def require_scene_id(scene: dict[str, Any]) -> str:
    scene_id = scene.get("id")
    if not isinstance(scene_id, str) or not scene_id:
        raise ServiceRunError("Every storyboard scene must include a non-empty id.")
    return scene_id


def require_starting_image_path(scene: dict[str, Any]) -> str:
    starting_image = scene.get("starting_image")
    if not isinstance(starting_image, dict):
        raise ServiceRunError("Every storyboard scene must include starting_image.")

    image_path = starting_image.get("image_path")
    if not isinstance(image_path, str) or not image_path:
        raise ServiceRunError("Every storyboard scene must include starting_image.image_path.")

    return image_path
