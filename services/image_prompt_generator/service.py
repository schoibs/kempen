from __future__ import annotations

import logging
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


logger = logging.getLogger(__name__)


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
        return {'image_prompts': [{'scene_id': 'scene_01', 'reference_image_path': 'assets/prime.png', 'prompt': "A 9:16 commercial product shot of the PRIME Hydration Lemonade bottle centered on a pure white background. The tall plastic bottle has a bright yellow label with visible text: 'PRIME', 'HYDRATION', 'LEMONADE', 'FLAVOUR', and '500 mL'. The cap is yellow. Crisp studio lighting, high contrast, minimal premium product ad style. No other objects, text overlays, or backgrounds."}, {'scene_id': 'scene_02', 'reference_image_path': 'assets/prime.png', 'prompt': "A closer 9:16 product shot of the same PRIME Hydration Lemonade bottle, still centered on pure white. The frame emphasizes the label area, making the 'LEMONADE' branding and PRIME wordmark clearly visible. The label colors, cap, and all text remain exactly as in the reference. Crisp macro-style studio lighting, no additional objects, pure white background."}, {'scene_id': 'scene_03', 'reference_image_path': 'assets/prime.png', 'prompt': "A 9:16 full-frame hero shot of the PRIME Hydration Lemonade bottle centered on pure white. The composition is exactly like the reference, with all label details preserved: 'LEMONADE', 'FLAVOUR', 'PRIME', 'HYDRATION', '500 mL', and yellow cap. Premium social ad end card style, strong product clarity, clean white background. No text overlay included in the image generation."}]}


        scene_briefs, reference_paths_by_scene_id = self._scene_briefs(
            storyboard=storyboard,
            product_image_path=product_image_path,
        )
        expected_scene_ids = set(reference_paths_by_scene_id)
        payload = {
            "service_goal": "Generate image edit prompts for storyboard start frames.",
            "scenes": scene_briefs,
        }

        output = self._run_structured_model(payload)
        self._validate_scene_coverage(
            actual_scene_ids={item.scene_id for item in output.image_prompts},
            expected_scene_ids=expected_scene_ids,
        )

        for item in output.image_prompts:
            item.reference_image_path = reference_paths_by_scene_id[item.scene_id]

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
