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

class ServiceRunError(RuntimeError):
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
        product_analysis: dict[str, Any] | None = None,
        prompt_mode: PromptMode = "auto",
    ) -> dict[str, Any]:
        return {'aspect_ratio': '9:16', 'element_bindings': [{'storyboard_ref': '@main_subject', 'kling_ref': '@Element1', 'description': '@main_subject: PRIME Hydration Lemonade 500 mL bottle, bright yellow plastic bottle with yellow cap, minimal white label, large vertical black PRIME lettering with white outline, Lemonade flavor, HYDRATION near the bottom, single-serve sports hydration beverage, clean bold branding.'}, {'storyboard_ref': '@subject_id_2', 'kling_ref': '@Element2', 'description': 'Young adult summer crew, diverse friends in festival-ready beachwear, sun-kissed and stylish, playful expressions, moving as a tight social unit from beach to festival to club.'}, {'storyboard_ref': '@subject_id_3', 'kling_ref': '@Element3', 'description': 'Sun-bleached beach and festival environment that transforms through the day: hot sand, ocean glare, portable speakers, festival lights, neon club interior, heat haze, confetti, and surreal summer energy.'}], 'scene_prompts': [{'scene_id': 'scene_1', 'duration_sec': 5.0, 'prompt_mode': 'multi', 'start_image_strategy': 'Use the generated campaign starting frame based on storyboard.starting_frame_description.', 'element_refs': ['@Element1', '@Element2'], 'text_overlay': {'required': True, 'copy_text': 'Bright by day.', 'safe_area': 'Keep text centered in upper-middle vertical safe area, away from bottle label and lower-third sand texture.', 'render_in_video_model': False}, 'payload': {'prompt': None, 'multi_prompt': [{'prompt': 'Vertical 9:16 cinematic image-to-video starting from the sunrise beach ritual frame: @Element1, a bright yellow PRIME Hydration Lemonade 500 mL bottle with yellow cap and crisp minimal white label, large vertical black PRIME lettering with white outline and HYDRATION near the bottom, drops onto hot rippled sand in extreme close-up from a low angle, bounces once, then settles perfectly upright and centered like a tiny sun. Slow-motion push-in with a tiny vibration on impact, label staying sharp and legible, condensation visible, sand grains bursting outward, heat shimmer rippling behind it, peach-gold sunrise and calm shimmering ocean in the background, bold clean surreal iconic product hero composition, end on the cap glow for a match cut.', 'duration': 2}, {'prompt': 'Vertical 9:16 cinematic image-to-video continuing from the beach hero frame: medium vertical shot with @Element1 centered and monumental while @Element2, a diverse young adult summer crew in festival-ready beachwear, circle the bottle on the beach, lean in, grin, and pass it forward as if the bottle has summoned them. Gentle orbit around the bottle and crew, the bottle remaining the visual anchor with exact bright yellow color and legible label, sun flare blooming, a portable speaker waking up, towels fluttering like flags, sunglasses flashing, ocean sparkle intensifying, heat haze bending the horizon, lively but clean summer energy, end with a whip-pan into the next scene.', 'duration': 3}], 'duration': 5, 'shot_type': 'customize', 'negative_prompt': 'blur, distort, low quality, warped product packaging, unreadable or misspelled label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, flicker, abrupt random cuts, random text overlays, subtitles, watermarks'}}, {'scene_id': 'scene_2', 'duration_sec': 5.0, 'prompt_mode': 'multi', 'start_image_strategy': "Use the previous generated scene's final frame as this scene's start frame.", 'element_refs': ['@Element1', '@Element2'], 'text_overlay': {'required': True, 'copy_text': 'Ready by night.', 'safe_area': 'Upper third safe area, leaving the center clear for the bottle and crowd motion.', 'render_in_video_model': False}, 'payload': {'prompt': None, 'multi_prompt': [{'prompt': 'Vertical 9:16 cinematic image-to-video starting from the previous festival transition frame: tight handheld close-up of @Element1 in a hand with the label facing camera, the bright yellow PRIME Hydration Lemonade bottle staying steady and crisp while the hand threads through a packed daytime festival crowd. Fast forward glide through the crowd, bodies and wristbands streaking by, flags whipping in the wind, sun glare and heat haze intensifying, the bottle acting like a glowing talisman and visual anchor, exact colors preserved, no text overlays, end on a hard-cut bass-hit energy.', 'duration': 2}, {'prompt': 'Vertical 9:16 cinematic image-to-video continuing from the crowd glide: wide vertical reveal of @Element2 moving in sync through festival chaos while @Element1 remains bright and centered as the crew’s sacred anchor. Crane-up reveal from the bottle to the crowd canopy, the crew walking cool and collected, sipping and smiling without breaking stride, confetti bursting, LED panels flickering lemon-yellow, sun glare washing the lane, flags and fans blurring around them, surreal summer procession feel, exact bottle identity and label legibility preserved, end with a neon flicker dissolve.', 'duration': 3}], 'duration': 5, 'shot_type': 'customize', 'negative_prompt': 'blur, distort, low quality, warped product packaging, unreadable or misspelled label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, flicker, abrupt random cuts, random text overlays, subtitles, watermarks'}}, {'scene_id': 'scene_3', 'duration_sec': 5.0, 'prompt_mode': 'multi', 'start_image_strategy': "Use the previous generated scene's final frame as this scene's start frame.", 'element_refs': ['@Element1', '@Element2'], 'text_overlay': {'required': True, 'copy_text': 'PRIME Lemonade keeps the summer alive.', 'safe_area': 'Center-upper safe area, with final CTA reserved for the last beat and no text crowding the bottle.', 'render_in_video_model': False}, 'payload': {'prompt': None, 'multi_prompt': [{'prompt': 'Vertical 9:16 cinematic image-to-video starting from the club transformation frame: close-up of @Element1 on a glowing club table, the bright yellow PRIME Hydration Lemonade bottle unchanged and iconic under neon reflections, condensation dripping down the bottle, a hand reaching in to grab it. Slow lateral slide past the bottle, laser lines sweeping the background, ice bucket vapor curling upward, blacklight and glossy club reflections preserving the exact label colors and legibility, end on a glow wipe into the final hero shot.', 'duration': 2}, {'prompt': 'Vertical 9:16 cinematic image-to-video continuing from the club table glow: hero vertical shot of @Element2 in a neon club, under blacklight and laser haze, raising @Element1 toward camera in a confident final pose. Slow push-in with slight handheld swagger, the crew nodding and smiling, strobe flashes, confetti floating, silhouettes dancing in the background, the bottle remaining the bright yellow beacon with crisp label and exact branding, room pulsing around them, end on a freeze-frame end-card feeling.', 'duration': 3}], 'duration': 5, 'shot_type': 'customize', 'negative_prompt': 'blur, distort, low quality, warped product packaging, unreadable or misspelled label text, incorrect logo, extra brands, deformed hands, deformed faces, jitter, flicker, abrupt random cuts, random text overlays, subtitles, watermarks'}}]}
        if prompt_mode not in {"auto", "single", "multi"}:
            raise ServiceRunError("prompt_mode must be one of: auto, single, multi.")

        scenes = storyboard.get("scenes")
        scene_ids = [scene.get("id") for scene in scenes]
        element_bindings = self._build_element_bindings(
            storyboard=storyboard,
            product_analysis=product_analysis,
        )
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
        product_analysis: dict[str, Any] | None,
    ) -> list[ElementBinding]:
        bindings = [
            ElementBinding(
                storyboard_ref="@main_subject",
                kling_ref="@Element1",
                description=self._main_subject_description(
                    storyboard=storyboard,
                    product_analysis=product_analysis,
                ),
            )
        ]

        for subject in storyboard.get("subjects") or []:
            if not isinstance(subject, dict):
                continue

            subject_id = subject.get("subject_id")
            subject_description = str(subject.get("subject_description") or "").strip()
            if not isinstance(subject_id, int) or not subject_description:
                continue
            if "@main_subject" in subject_description:
                continue

            bindings.append(
                ElementBinding(
                    storyboard_ref=f"@subject_id_{subject_id}",
                    kling_ref=f"@Element{len(bindings) + 1}",
                    description=subject_description,
                )
            )

        return bindings

    def _main_subject_description(
        self,
        storyboard: dict[str, Any],
        product_analysis: dict[str, Any] | None,
    ) -> str:
        for subject in storyboard.get("subjects") or []:
            if not isinstance(subject, dict):
                continue
            subject_description = str(subject.get("subject_description") or "").strip()
            if "@main_subject" in subject_description:
                return subject_description

        if product_analysis:
            product_name = product_analysis.get("product_name")
            category = product_analysis.get("category")
            visible_facts = product_analysis.get("visible_facts") or []
            fact_text = "; ".join(str(fact) for fact in visible_facts[:6])
            description_parts = [
                str(part)
                for part in (product_name, category, fact_text)
                if part
            ]
            if description_parts:
                return "@main_subject: " + ". ".join(description_parts)

        return "@main_subject: main campaign subject from the supplied product image."

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
            raise ServiceRunError(
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
        except ServiceRunError:
            return False

        return sum(shot_durations) == scene_duration

    def _format_shot_duration(self, duration_sec: Any, *, scene_id: str, shot_id: str) -> int:
        if not isinstance(duration_sec, int | float) or isinstance(duration_sec, bool):
            raise ServiceRunError(f"Shot {shot_id} in scene {scene_id} needs numeric duration_sec.")
        if duration_sec < 1 or duration_sec > 15:
            raise ServiceRunError(f"Shot {shot_id} in scene {scene_id} must be 1-15 seconds.")
        if isinstance(duration_sec, float) and not duration_sec.is_integer():
            raise ServiceRunError(
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
            raise ServiceRunError(f"LLM video prompt generation failed: {exc}") from exc

        if not isinstance(draft_output, VideoPromptDraftOutput):
            raise ServiceRunError("LLM response was not a VideoPromptDraftOutput.")
        return draft_output

    def _validate_draft_output(
        self,
        draft_output: VideoPromptDraftOutput,
        expected_scene_ids: list[str],
        expected_prompt_modes: dict[str, str],
    ) -> None:
        actual_scene_ids = [scene.scene_id for scene in draft_output.scene_prompts]
        if actual_scene_ids != expected_scene_ids:
            raise ServiceRunError(
                "Video prompt response did not match storyboard scene order. "
                f"Expected {expected_scene_ids}; got {actual_scene_ids}."
            )

        for scene_prompt_draft in draft_output.scene_prompts:
            expected_mode = expected_prompt_modes[scene_prompt_draft.scene_id]
            if scene_prompt_draft.prompt_mode != expected_mode:
                raise ServiceRunError(
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
            raise ServiceRunError(f"Final video prompt output failed validation: {exc}") from exc
