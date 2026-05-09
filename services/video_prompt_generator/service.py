from __future__ import annotations

import json
import logging
from typing import Any, Literal

from clients import LLMClient
from pydantic import ValidationError

from .prompt import SYSTEM_PROMPT
from .schema import (
    ElementBinding,
    KlingScenePromptPayload,
    SceneVideoPrompt,
    TextOverlayInstruction,
    VideoPromptDraftOutput,
    VideoPromptGeneratorOutput,
)


logger = logging.getLogger(__name__)

PromptMode = Literal["auto", "single", "multi"]

DEFAULT_NEGATIVE_PROMPT = (
    "blur, distort, low quality, warped product packaging, unreadable or misspelled "
    "label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, "
    "flicker, abrupt random cuts, random text overlays, subtitles, watermarks"
)

class VideoPromptGeneratorServiceError(RuntimeError):
    """Raised when a service cannot produce usable structured output."""


class VideoPromptGeneratorService:
    """Generate validated Kling image-to-video prompt payloads from storyboard scenes."""

    default_temperature = 0.3
    default_max_tokens = 6000

    def __init__(
        self,
        model: str = "gpt-5.4-mini",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.llm_client = LLMClient(model=model)
        self.temperature = self.default_temperature if temperature is None else temperature
        self.max_tokens = max_tokens or self.default_max_tokens

    def run(
        self,
        storyboard: dict[str, Any],
        prompt_mode: PromptMode = "auto",
    ) -> dict[str, Any]:
        return {'aspect_ratio': '9:16', 'element_bindings': [{'storyboard_ref': '@subject_id_0', 'kling_ref': '@Element0', 'description': 'PRIME Hydration Lemonade bottle: bright yellow 500 mL single-serve plastic bottle with yellow cap, minimal white label, large vertical black PRIME lettering with white outline, Lemonade flavor, HYDRATION near the bottom, sun-bright summer icon.'}, {'storyboard_ref': '@subject_id_1', 'kling_ref': '@Element1', 'description': 'Young adult summer crew: diverse stylish friends in festival-ready beachwear, sweaty, playful, cool, socially magnetic, moving from beach to festival to club.'}], 'scene_prompts': [{'scene_id': 'scene_1', 'duration_sec': 5.0, 'prompt_mode': 'multi', 'start_image_strategy': 'Use the generated campaign starting frame based on storyboard.starting_frame_description.', 'element_refs': ['@Element0', '@Element1'], 'text_overlay': {'required': True, 'copy_text': 'Bright by day.', 'safe_area': 'Center-lower safe area, leaving bottle label unobstructed', 'render_in_video_model': False}, 'payload': {'prompt': None, 'multi_prompt': [{'prompt': 'Vertical 9:16, start from the sunrise beach hero frame: @Element0, a bright yellow 500 mL PRIME Hydration Lemonade bottle with yellow cap and minimal white label, lands in slow motion at center frame on hot sand like a tiny sun, slightly tilted then rotating upright so the tall vertical black PRIME lettering with white outline, Lemonade flavor, and HYDRATION near the bottom become perfectly legible. Extreme close-up, low angle, slow-motion push-in with slight handheld tremble. Sand grains burst outward in a glowing halo, heat shimmer ripples across the frame, and the impact flash drives a smash-cut energy into the next beat. Preserve crisp product identity, exact colors, clean white negative space, and cinematic sun-soaked contrast.', 'duration': 2}, {'prompt': 'Vertical 9:16, continue from the beach impact into a wide vertical tableau: @Element0 remains the bright yellow hero centerpiece while @Element1, a diverse stylish young adult summer crew in festival-ready beachwear, gathers around it on the shoreline. Slow orbit around the group and bottle centerpiece. One person twists the cap, another takes the first sip and smiles with instant relief, while towels snap open, a beach umbrella pops up, sunglasses flash, and seagulls streak by as graphic accents. Keep the bottle label facing camera and fully legible, with the same exact yellow, white, and black product colors, and end on a match cut feeling anchored to the yellow label.', 'duration': 3}], 'duration': 5, 'shot_type': 'customize', 'negative_prompt': 'blur, distort, low quality, warped product packaging, unreadable or misspelled label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, flicker, abrupt random cuts, random text overlays, subtitles, watermarks'}}, {'scene_id': 'scene_2', 'duration_sec': 5.0, 'prompt_mode': 'multi', 'start_image_strategy': "Use the previous generated scene's final frame as this scene's start frame.", 'element_refs': ['@Element0', '@Element1'], 'text_overlay': {'required': True, 'copy_text': 'Ready by night.', 'safe_area': 'Upper-middle safe area, avoiding faces and bottle label', 'render_in_video_model': False}, 'payload': {'prompt': None, 'multi_prompt': [{'prompt': "Vertical 9:16, start from the previous scene's final frame and move into a medium tracking shot through a crowded festival lane: @Element1 walks in sync through the crowd, one hand always holding @Element0 at chest height like a bright yellow totem. Fast lateral dolly with whip-pan accents. Flags, LED screens, confetti, and saturated bodies streak past in rhythmic motion while the crew stays cool and composed. Preserve the bottle's exact bright yellow body, yellow cap, minimal white label, and readable PRIME branding as it stays centered in the action, with the crowd and environment swirling around it.", 'duration': 2}, {'prompt': 'Vertical 9:16, continue into a close-up hero shot of @Element0 against neon festival lights. Micro push-in with subtle tilt-up. The bottle rotates slowly with condensation sparkling, label perfectly legible, while a friend from @Element1 takes a quick sip and passes it on. Laser beams and crowd silhouettes form a graphic halo, with sweat, light, and motion stylized and clean rather than messy. Maintain exact product colors and continuity, and end with a neon flare dissolve feeling that carries into the night energy.', 'duration': 3}], 'duration': 5, 'shot_type': 'customize', 'negative_prompt': 'blur, distort, low quality, warped product packaging, unreadable or misspelled label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, flicker, abrupt random cuts, random text overlays, subtitles, watermarks'}}, {'scene_id': 'scene_3', 'duration_sec': 5.0, 'prompt_mode': 'multi', 'start_image_strategy': "Use the previous generated scene's final frame as this scene's start frame.", 'element_refs': ['@Element0', '@Element1'], 'text_overlay': {'required': True, 'copy_text': 'Grab a PRIME Lemonade and keep your summer on.', 'safe_area': 'Lower-third safe area, centered, with bottle visible above text', 'render_in_video_model': False}, 'payload': {'prompt': None, 'multi_prompt': [{'prompt': "Vertical 9:16, start from the previous scene's final frame and reveal a stylized neon club close-up: @Element0 sits upright on the bar under blacklight, condensation shining like chrome, still bright yellow with the minimal white label and bold black PRIME lettering clearly visible. Slow deliberate push-in with a slight dutch angle. Laser grids sweep across mirrored surfaces and club smoke drifts in ribbons, while the bottle remains the calm, iconic center of the scene. Preserve exact product identity, label legibility, and the contrast between the glowing bottle and dark club environment, ending on a cut-on-bass-hit feeling.", 'duration': 2}, {'prompt': 'Vertical 9:16, continue into a vertical medium-wide dance shot with @Element1 moving through the club around @Element0. Circular handheld orbit around the crew. @Element1 dances, then takes a final sip and re-enters the crowd with effortless composure, while strobe flashes, silhouettes, floating confetti, and smoke create a surreal day-to-night continuity. Keep the bottle present as the hero object with exact colors and readable label, and finish on a final freeze feeling that locks the bottle into a confident hero pose.', 'duration': 3}], 'duration': 5, 'shot_type': 'customize', 'negative_prompt': 'blur, distort, low quality, warped product packaging, unreadable or misspelled label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, flicker, abrupt random cuts, random text overlays, subtitles, watermarks'}}]}
        
        if prompt_mode not in {"auto", "single", "multi"}:
            raise VideoPromptGeneratorServiceError("prompt_mode must be one of: auto, single, multi.")

        scenes = storyboard.get("scenes")
        scene_ids = [scene.get("id") for scene in scenes]
        element_bindings = self._build_element_bindings(storyboard=storyboard)
        scene_briefs, expected_prompt_modes = self._scene_briefs(
            scenes=scenes,
            element_bindings=element_bindings,
            prompt_mode=prompt_mode,
        )

        user_payload = {
            "service_goal": "Generate Kling v3 image-to-video positive prompts for each storyboard scene.",
            "aspect_ratio": storyboard.get("aspect_ratio", "9:16"),
            "element_bindings": [
                binding.model_dump(mode="json") for binding in element_bindings
            ],
            "starting_frame_description": storyboard.get("starting_frame_description"),
            "scenes": scene_briefs,
            "output_requirements": [
                "Return one scene_prompts item for every scene, and no extras.",
                "Return only scene_id, prompt_mode, element_refs, prompt, and multi_prompt fields.",
                "For single mode, set prompt to text and multi_prompt to null.",
                "For multi mode, set prompt to null and multi_prompt to one item per storyboard shot.",
                "Never include overlay copy or API settings in the prompt text.",
            ],
        }

        draft_output = self._run_structured_model(user_payload)
        self._validate_draft_output(
            draft_output=draft_output,
            expected_scene_ids=scene_ids,
            expected_prompt_modes=expected_prompt_modes,
        )
        output = self._build_output(
            draft_output=draft_output,
            aspect_ratio=str(storyboard.get("aspect_ratio", "9:16")),
            element_bindings=element_bindings,
            scene_briefs_by_id={scene["scene_id"]: scene for scene in scene_briefs},
        )
        return output.model_dump(mode="json")

    def _build_element_bindings(
        self,
        storyboard: dict[str, Any],
    ) -> list[ElementBinding]:
        bindings: list[ElementBinding] = []

        for subject in storyboard.get("subjects") or []:
            if not isinstance(subject, dict):
                continue

            subject_id = subject.get("subject_id")
            subject_description = str(subject.get("subject_description") or "").strip()
            if (
                not isinstance(subject_id, int)
                or isinstance(subject_id, bool)
                or not subject_description
            ):
                continue

            bindings.append(
                ElementBinding(
                    storyboard_ref=f"@subject_id_{subject_id}",
                    kling_ref=f"@Element{subject_id}",
                    description=subject_description,
                )
            )

        return bindings

    def _scene_briefs(
        self,
        scenes: list[dict[str, Any]],
        element_bindings: list[ElementBinding],
        prompt_mode: PromptMode,
    ) -> tuple[list[dict[str, Any]], dict[str, str]]:
        scene_briefs: list[dict[str, Any]] = []
        expected_prompt_modes: dict[str, str] = {}

        for index, scene in enumerate(scenes):
            scene_id = scene.get("id")
            duration = int(scene.get("duration_sec"))
            requested_prompt_mode = self._resolve_scene_prompt_mode(
                scene=scene,
                scene_id=scene_id,
                scene_duration=duration,
                prompt_mode=prompt_mode,
            )
            expected_prompt_modes[scene_id] = requested_prompt_mode

            scene_briefs.append(
                {
                    "scene_id": scene_id,
                    "duration_sec": duration,
                    "prompt_mode": requested_prompt_mode,
                    "start_image_strategy": self._start_image_strategy(index),
                    "element_refs": self._scene_element_refs(
                        scene=scene,
                        element_bindings=element_bindings,
                    ),
                    "text_overlay": self._text_overlay_instruction(scene).model_dump(
                        mode="json"
                    ),
                    "scene_description": scene.get("scene_description"),
                    "shot_sequence": scene.get("shot_sequence"),
                    "audio_direction": scene.get("audio_direction"),
                    "transition_notes": self._transition_notes(scene),
                }
            )

        return scene_briefs, expected_prompt_modes

    def _resolve_scene_prompt_mode(
        self,
        *,
        scene: dict[str, Any],
        scene_id: str,
        scene_duration: int,
        prompt_mode: PromptMode,
    ) -> Literal["single", "multi"]:
        if prompt_mode == "single":
            return "single"

        can_use_multi = self._can_use_multi_prompt(
            scene=scene,
            scene_id=scene_id,
            scene_duration=scene_duration,
        )
        if prompt_mode == "auto":
            return "multi" if can_use_multi else "single"

        if not can_use_multi:
            raise VideoPromptGeneratorServiceError(
                f"Scene {scene_id} cannot use multi_prompt because its shots are not multiple whole-second shots."
            )
        return "multi"

    def _can_use_multi_prompt(
        self,
        *,
        scene: dict[str, Any],
        scene_id: str,
        scene_duration: int,
    ) -> bool:
        shot_sequence = scene.get("shot_sequence")
        if not isinstance(shot_sequence, list) or len(shot_sequence) <= 1:
            return False

        shot_durations: list[int] = []
        try:
            for shot in shot_sequence:
                if not isinstance(shot, dict):
                    return False
                shot_id = str(shot.get("shot_id") or "unknown")
                shot_durations.append(
                    self._format_shot_duration(
                        shot.get("duration_sec"),
                        scene_id=scene_id,
                        shot_id=shot_id,
                    )
                )
        except VideoPromptGeneratorServiceError:
            return False

        return sum(shot_durations) == scene_duration

    def _format_shot_duration(self, duration_sec: Any, *, scene_id: str, shot_id: str) -> int:
        if not isinstance(duration_sec, int | float) or isinstance(duration_sec, bool):
            raise VideoPromptGeneratorServiceError(f"Shot {shot_id} in scene {scene_id} needs numeric duration_sec.")
        if duration_sec < 1 or duration_sec > 15:
            raise VideoPromptGeneratorServiceError(f"Shot {shot_id} in scene {scene_id} must be 1-15 seconds.")
        if isinstance(duration_sec, float) and not duration_sec.is_integer():
            raise VideoPromptGeneratorServiceError(
                f"Shot {shot_id} in scene {scene_id} must be a whole number for multi_prompt."
            )
        return int(duration_sec)

    def _start_image_strategy(self, scene_index: int) -> str:
        if scene_index == 0:
            return (
                "Use the generated campaign starting frame based on storyboard.starting_frame_description."
            )
        return "Use the previous generated scene's final frame as this scene's start frame."

    def _scene_element_refs(
        self,
        scene: dict[str, Any],
        element_bindings: list[ElementBinding],
    ) -> list[str]:
        scene_text = json.dumps(scene, ensure_ascii=False)
        refs = [
            binding.kling_ref
            for binding in element_bindings
            if binding.storyboard_ref in scene_text
        ]
        if not refs:
            refs = [element_bindings[0].kling_ref]
        return refs

    def _text_overlay_instruction(self, scene: dict[str, Any]) -> TextOverlayInstruction:
        text_overlay = scene.get("text_overlay") or {}
        copy_text = text_overlay.get("copy_text")
        if copy_text is None:
            copy_text = text_overlay.get("copy")

        return TextOverlayInstruction(
            required=bool(text_overlay.get("required", False)),
            copy_text=copy_text,
            safe_area=str(text_overlay.get("safe_area") or "No overlay safe area provided."),
            render_in_video_model=False,
        )

    def _transition_notes(self, scene: dict[str, Any]) -> list[str]:
        transitions: list[str] = []
        for shot in scene.get("shot_sequence") or []:
            if isinstance(shot, dict) and shot.get("transition"):
                transitions.append(str(shot["transition"]))
        return transitions

    def _run_structured_model(
        self,
        user_payload: dict[str, Any],
    ) -> VideoPromptDraftOutput:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Create structured JSON for this video prompt generation brief. "
                    "Return only JSON, with no markdown or prose.\n"
                    f"{json.dumps(user_payload, indent=2)}"
                ),
            },
        ]

        try:
            draft_output = self.llm_client.chat(
                messages=messages,
                response_model=VideoPromptDraftOutput,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            raise VideoPromptGeneratorServiceError(f"LLM video prompt generation failed: {exc}") from exc

        if not isinstance(draft_output, VideoPromptDraftOutput):
            raise VideoPromptGeneratorServiceError("LLM response was not a VideoPromptDraftOutput.")
        return draft_output

    def _validate_draft_output(
        self,
        draft_output: VideoPromptDraftOutput,
        expected_scene_ids: list[str],
        expected_prompt_modes: dict[str, str],
    ) -> None:
        actual_scene_ids = [scene.scene_id for scene in draft_output.scene_prompts]
        if actual_scene_ids != expected_scene_ids:
            raise VideoPromptGeneratorServiceError(
                "Video prompt response did not match storyboard scene order. "
                f"Expected {expected_scene_ids}; got {actual_scene_ids}."
            )

        for scene_prompt_draft in draft_output.scene_prompts:
            expected_mode = expected_prompt_modes[scene_prompt_draft.scene_id]
            if scene_prompt_draft.prompt_mode != expected_mode:
                raise VideoPromptGeneratorServiceError(
                    f"Scene {scene_prompt_draft.scene_id} should use {expected_mode} prompt mode."
                )

    def _build_output(
        self,
        draft_output: VideoPromptDraftOutput,
        aspect_ratio: str,
        element_bindings: list[ElementBinding],
        scene_briefs_by_id: dict[str, dict[str, Any]],
    ) -> VideoPromptGeneratorOutput:
        try:
            scene_prompts: list[SceneVideoPrompt] = []

            for scene_prompt_draft in draft_output.scene_prompts:
                scene_brief = scene_briefs_by_id[scene_prompt_draft.scene_id]
                is_multi_prompt = bool(scene_prompt_draft.multi_prompt)
                payload = KlingScenePromptPayload(
                    prompt=scene_prompt_draft.prompt,
                    multi_prompt=scene_prompt_draft.multi_prompt,
                    duration=scene_brief["duration_sec"],
                    shot_type="customize" if is_multi_prompt else None,
                    negative_prompt=DEFAULT_NEGATIVE_PROMPT,
                )

                scene_prompts.append(
                    SceneVideoPrompt(
                        scene_id=scene_prompt_draft.scene_id,
                        duration_sec=scene_brief["duration_sec"],
                        prompt_mode=scene_prompt_draft.prompt_mode,
                        start_image_strategy=scene_brief["start_image_strategy"],
                        element_refs=scene_prompt_draft.element_refs,
                        text_overlay=TextOverlayInstruction.model_validate(
                            scene_brief["text_overlay"]
                        ),
                        payload=payload,
                    )
                )

            return VideoPromptGeneratorOutput(
                aspect_ratio=aspect_ratio,
                element_bindings=element_bindings,
                scene_prompts=scene_prompts,
            )
        except ValidationError as exc:
            raise VideoPromptGeneratorServiceError(f"Final video prompt output failed validation: {exc}") from exc
