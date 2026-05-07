from __future__ import annotations

import base64
import mimetypes
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..base import BasePromptService, ServiceRunError
from ..utils import (
    model_to_dict,
    require_scene_id,
    require_starting_image_path,
    storyboard_scenes,
)
from .prompt import SYSTEM_PROMPT
from .schema import VideoPromptGeneratorOutput


logger = logging.getLogger(__name__)


class VideoPromptGeneratorService(BasePromptService):
    """Generate fal Kling image-to-video prompt payloads from storyboard scenes."""

    output_type = VideoPromptGeneratorOutput
    response_schema_name = "video_prompt_generator_output"
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.3

    def run(
        self,
        *,
        storyboard: dict[str, Any],
        product_analysis: dict[str, Any],
        narrative_strategy: dict[str, Any] | None = None,
        start_image_urls_by_scene_id: dict[str, str] | None = None,
        start_image_paths_by_scene_id: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {'video_prompts': [{'scene_id': 'scene_01', 'prompt': 'Create a 5-second premium product hero video from the provided start image. Keep the tall plastic bottle perfectly centered in a vertical frame with generous white space around it. Use a very subtle slow push-in only, with no rotation or tilt. The bottle must remain completely still and sharply in focus. Preserve the exact bottle design, yellow cap, yellow lemonade body, and all visible label text exactly as shown. Maintain a clean pure white studio background with no props, no scenery, no extra objects, and no added branding. Lighting should feel crisp, high-contrast, minimal, and premium, with a bright sunny product-ad look. Pace should be slow and confident, ending as a clean hero hold that feels like an elegant reveal.', 'negative_prompt': 'Do not change the bottle shape, cap color, label layout, or any visible text. No extra logos, no extra products, no hands, no people, no condensation changes, no warped packaging, no unreadable label, no background texture, no shadows that clutter the scene, no color shifts, no rotation, no dramatic camera shake, no zoom burst, no scene clutter, no text overlays, no subtitles, no dialogue visuals.'}, {'scene_id': 'scene_02', 'prompt': 'Create a 5-second clean macro-style product showcase from the provided start image. Begin with a medium-close centered view of the bottle and slowly push in toward the label area, keeping the product perfectly stable and fully recognizable. Continue into a tighter close-up while still preserving enough of the full bottle shape to maintain brand recognition. The camera motion should be smooth, measured, and polished, with no rotation or wobble. Keep the background pure white and static. Emphasize the bright yellow color and the label clarity, while preserving the exact bottle design, yellow cap, and all visible text exactly as shown. Maintain premium studio lighting, crisp focus, and a fresh, minimal ad aesthetic throughout.', 'negative_prompt': 'Do not alter the bottle color, cap color, label text, or packaging proportions. No extra objects, no props, no scenery, no hands, no people, no reflections that obscure the label, no warped or unreadable text, no added logos, no new flavors, no liquid motion, no condensation effects, no background movement, no camera shake, no dramatic parallax, no overlays, no subtitles, no dialogue visuals.'}, {'scene_id': 'scene_03', 'prompt': 'Create a 5-second premium social ad end-card video from the provided start image. Return to a full centered hero view of the bottle with the label and yellow body clearly visible. Use a very subtle pull-back to restore breathing room around the product, then hold static for the final CTA beat. The bottle must remain fixed, centered, and sharply in focus. Preserve the exact visible text and packaging details exactly as shown, including LEMONADE, FLAVOUR, PRIME, HYDRATION, and 500 mL. Keep the background pure white, minimal, and free of any additional objects or scenery. The finish should feel clean, confident, and slightly elevated in energy, ending with a simple fade to white.', 'negative_prompt': 'Do not change any visible text, label layout, bottle shape, cap color, or product color. No extra logos, no extra products, no people, no hands, no props, no scenery, no background texture, no clutter, no warped packaging, no unreadable label, no new claims, no motion blur, no camera shake, no rotation, no overlays that cover the bottle, no subtitles, no dialogue visuals.'}]}

        scene_briefs, video_settings_by_scene_id = self._scene_briefs(
            storyboard=storyboard,
            start_image_inputs_by_scene_id=(
                start_image_urls_by_scene_id
                or start_image_paths_by_scene_id
                or {}
            ),
        )
        expected_scene_ids = set(video_settings_by_scene_id)
        payload = {
            "service_goal": "Generate Kling image-to-video prompts for storyboard scenes.",
            "scenes": scene_briefs,
        }

        output = self._run_structured_model(payload)
        self._validate_scene_coverage(
            actual_scene_ids={item.scene_id for item in output.video_prompts},
            expected_scene_ids=expected_scene_ids,
        )

        return output.model_dump(mode="json", by_alias=True)

    @staticmethod
    def _scene_briefs(
        *,
        storyboard: dict[str, Any],
        start_image_inputs_by_scene_id: dict[str, str],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        scene_briefs: list[dict[str, Any]] = []
        video_settings_by_scene_id: dict[str, dict[str, Any]] = {}

        for scene in storyboard_scenes(storyboard):
            scene_id = require_scene_id(scene)
            start_image_input = (
                start_image_inputs_by_scene_id.get(scene_id)
                or require_starting_image_path(scene)
            )
            start_image_url = VideoPromptGeneratorService._resolve_start_image_url(
                start_image_input
            )
            brief_start_image_url = VideoPromptGeneratorService._brief_start_image_url(
                start_image_input=start_image_input,
                start_image_url=start_image_url,
            )
            duration = VideoPromptGeneratorService._format_duration(
                scene.get("duration_sec")
            )
            audio_direction = scene.get("audio_direction") or {}
            generate_audio = bool(audio_direction.get("generate_audio", False))
            video_settings_by_scene_id[scene_id] = {
                "start_image_url": start_image_url,
                "duration": duration,
                "generate_audio": generate_audio,
            }
            scene_briefs.append(
                {
                    "scene_id": scene_id,
                    "duration": duration,
                    "start_image_url": brief_start_image_url,
                    "generate_audio": generate_audio,
                    "visual_purpose": scene.get("visual_purpose"),
                    "narrative_beat": scene.get("narrative_beat"),
                    "scene_intent": scene.get("scene_intent"),
                    "shot_sequence": scene.get("shot_sequence"),
                    "audio_direction": audio_direction,
                    "text_overlay": scene.get("text_overlay"),
                    "continuity": scene.get("continuity"),
                }
            )

        return scene_briefs, video_settings_by_scene_id

    @staticmethod
    def _format_duration(duration_sec: Any) -> str:
        if not isinstance(duration_sec, int | float):
            raise ServiceRunError("Every storyboard scene must include numeric duration_sec.")
        if duration_sec < 3 or duration_sec > 15:
            raise ServiceRunError("Kling scene duration must be between 3 and 15 seconds.")
        if isinstance(duration_sec, float) and not duration_sec.is_integer():
            raise ServiceRunError("Kling scene duration must be a whole number of seconds.")
        return str(int(duration_sec))

    @staticmethod
    def _resolve_start_image_url(start_image_input: str) -> str:
        if not isinstance(start_image_input, str) or not start_image_input:
            raise ServiceRunError("Every video prompt needs a non-empty start image URL.")

        parsed = urlparse(start_image_input)
        if parsed.scheme in {"http", "https", "data"}:
            return start_image_input

        path = Path(start_image_input)
        if not path.exists():
            raise ServiceRunError(
                "Start image must be an http(s) URL, data URI, or existing local file."
            )

        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "image/png"

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _brief_start_image_url(*, start_image_input: str, start_image_url: str) -> str:
        if urlparse(start_image_url).scheme == "data":
            return f"service-populated data URI generated from {start_image_input}"
        return start_image_url

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
            "Video prompt response did not match storyboard scenes. "
            f"Missing: {missing or 'none'}; extra: {extra or 'none'}."
        )
