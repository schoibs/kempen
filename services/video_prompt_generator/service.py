from __future__ import annotations

import base64
import mimetypes
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
            "product_analysis": model_to_dict(product_analysis),
            "narrative_strategy": model_to_dict(narrative_strategy) if narrative_strategy else None,
            "output_requirements": {
                "provider": "fal_kling",
                "endpoint": "fal-ai/kling-video/v3/standard/image-to-video",
                "cfg_scale": 0.5,
                "use_start_image_url": True,
                "one_prompt_per_scene": True,
            },
            "scenes": scene_briefs,
        }

        output = self._run_structured_model(payload)
        self._validate_scene_coverage(
            actual_scene_ids={item.scene_id for item in output.video_prompts},
            expected_scene_ids=expected_scene_ids,
        )

        for item in output.video_prompts:
            settings = video_settings_by_scene_id[item.scene_id]
            item.provider = "fal_kling"
            item.endpoint = "fal-ai/kling-video/v3/standard/image-to-video"
            item.start_image_url = settings["start_image_url"]
            item.duration = settings["duration"]
            item.generate_audio = settings["generate_audio"]
            item.cfg_scale = 0.5

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
