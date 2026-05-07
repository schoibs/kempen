from __future__ import annotations

from typing import Any

from ..base import BasePromptService, ServiceRunError
from ..utils import (
    model_to_dict,
    require_scene_id,
    require_starting_image_path,
    storyboard_scenes,
)
from .prompt import SYSTEM_PROMPT
from .schema import ImagePromptGeneratorOutput


class ImagePromptGeneratorService(BasePromptService):
    """Generate OpenAI image prompt payloads from storyboard scenes."""

    output_type = ImagePromptGeneratorOutput
    response_schema_name = "image_prompt_generator_output"
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.25

    def run(
        self,
        *,
        storyboard: dict[str, Any],
        product_analysis: dict[str, Any],
        narrative_strategy: dict[str, Any] | None = None,
        product_image_path: str | None = None,
    ) -> dict[str, Any]:
        scene_briefs, reference_paths_by_scene_id = self._scene_briefs(
            storyboard=storyboard,
            product_image_path=product_image_path,
        )
        expected_scene_ids = set(reference_paths_by_scene_id)
        payload = {
            "service_goal": "Generate image edit prompts for storyboard start frames.",
            "product_analysis": model_to_dict(product_analysis),
            "narrative_strategy": model_to_dict(narrative_strategy) if narrative_strategy else None,
            "output_requirements": {
                "model": "gpt-image-2",
                "mode": "edit_with_reference",
                "size": "1080x1920",
                "quality": "high",
                "one_prompt_per_scene": True,
            },
            "scenes": scene_briefs,
        }

        output = self._run_structured_model(payload)
        self._validate_scene_coverage(
            actual_scene_ids={item.scene_id for item in output.image_prompts},
            expected_scene_ids=expected_scene_ids,
        )

        for item in output.image_prompts:
            item.model = "gpt-image-2"
            item.mode = "edit_with_reference"
            item.reference_image_path = reference_paths_by_scene_id[item.scene_id]
            item.size = "1080x1920"
            item.quality = "high"

        return output.model_dump(mode="json", by_alias=True)

    @staticmethod
    def _scene_briefs(
        *,
        storyboard: dict[str, Any],
        product_image_path: str | None,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        scene_briefs: list[dict[str, Any]] = []
        reference_paths_by_scene_id: dict[str, str] = {}

        for scene in storyboard_scenes(storyboard):
            scene_id = require_scene_id(scene)
            reference_image_path = product_image_path or require_starting_image_path(scene)
            reference_paths_by_scene_id[scene_id] = reference_image_path
            scene_briefs.append(
                {
                    "scene_id": scene_id,
                    "duration_sec": scene.get("duration_sec"),
                    "visual_purpose": scene.get("visual_purpose"),
                    "narrative_beat": scene.get("narrative_beat"),
                    "starting_image_description": scene.get("starting_image", {}).get("description"),
                    "scene_intent": scene.get("scene_intent"),
                    "text_overlay": scene.get("text_overlay"),
                    "continuity": scene.get("continuity"),
                    "reference_image_path": reference_image_path,
                }
            )

        return scene_briefs, reference_paths_by_scene_id

    @staticmethod
    def _validate_scene_coverage(
        *,
        actual_scene_ids: set[str],
        expected_scene_ids: set[str],
    ) -> None:
        if actual_scene_ids == expected_scene_ids:
            return

        missing = sorted(expected_scene_ids - actual_scene_ids)
        extra = sorted(actual_scene_ids - expected_scene_ids)
        raise ServiceRunError(
            "Image prompt response did not match storyboard scenes. "
            f"Missing: {missing or 'none'}; extra: {extra or 'none'}."
        )
