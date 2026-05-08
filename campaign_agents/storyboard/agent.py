from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..base import BaseAgent
from ..tools import tinyfish_web_search, web_fetch
from .prompt import SYSTEM_PROMPT
from .schema import StoryboardOutput


class StoryboardAgent(BaseAgent):
    """Plan video scenes and shot sequences from a narrative strategy."""

    name = "storyboard_agent"
    output_type = StoryboardOutput
    tools = [tinyfish_web_search, web_fetch]
    system_prompt = SYSTEM_PROMPT
    default_temperature = 0.4

    def run(
        self,
        *,
        product_analysis: dict[str, Any],
        narrative_strategy: dict[str, Any],
        product_image_path: str | Path,
        target_duration_sec: int = 15,
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
    ) -> dict[str, Any]:
        return {'total_duration_sec': 15.0, 'aspect_ratio': '9:16', 'scenes': [{'id': 'scene_01', 'duration_sec': 5.0, 'visual_purpose': 'Establish the product hero in a clean, premium product spotlight.', 'narrative_beat': 'The bottle appears as a bold summer signal: instantly recognizable, centered, and bright.', 'starting_image': {'image_path': 'assets/prime.png', 'description': 'Reference image of the PRIME Hydration Lemonade flavour bottle on a clean white background, centered single-product composition.'}, 'scene_intent': {'audience_feeling': 'Immediate curiosity and sunny, upbeat energy.', 'cinematic_style': 'Minimal premium product ad with crisp studio lighting and high contrast on white.', 'pace': 'Slow, confident reveal.'}, 'shot_sequence': [{'shot_id': 's1_shot1', 'duration_sec': 5.0, 'framing': 'Full product centered in vertical frame, leaving generous white space around the bottle.', 'camera_motion': 'Very subtle push-in with no rotation.', 'subject_motion': 'Bottle remains perfectly still and centered.', 'environment_motion': 'None; clean white background stays static.', 'transition': 'Hard cut in from black or white flash into the product hero.'}], 'audio_direction': {'generate_audio': True, 'mode': 'music_plus_minimal_sfx', 'ambience': 'Bright, airy, clean studio atmosphere with a sunny pop beat.', 'sfx_timeline': [{'at_sec': 0.5, 'cue': 'Soft whoosh reveal', 'linked_visual_action': 'The bottle settles into the center hero position.'}], 'dialogue': []}, 'text_overlay': {'enabled': False, 'copy': None, 'safe_area': 'Center-safe, leaving the bottle unobstructed.'}, 'continuity': {'previous_scene_transition': 'N/A', 'next_scene_transition': 'Cut to a slightly closer product view while preserving exact bottle design and white background.', 'continuity_requirements': ['Keep the tall plastic bottle shape, yellow cap, and all visible text exactly as shown.', 'Maintain a clean white background with a single centered product and no added objects.']}}, {'id': 'scene_02', 'duration_sec': 5.0, 'visual_purpose': 'Highlight the label and bright yellow color as the core visual hook.', 'narrative_beat': 'The camera moves closer so the lemonade branding and PRIME wordmark become the focus.', 'starting_image': {'image_path': 'assets/prime.png', 'description': 'Same PRIME Hydration Lemonade bottle reference on white, used as the starting frame for a closer product emphasis.'}, 'scene_intent': {'audience_feeling': 'Freshness, clarity, and premium simplicity.', 'cinematic_style': 'Clean macro-style product showcase with smooth studio motion.', 'pace': 'Measured and polished.'}, 'shot_sequence': [{'shot_id': 's2_shot1', 'duration_sec': 3.0, 'framing': 'Medium-close product framing, bottle still centered with label clearly readable.', 'camera_motion': 'Slow push-in toward the label area.', 'subject_motion': 'Bottle remains static.', 'environment_motion': 'None.', 'transition': 'Smooth cut from the previous hero shot.'}, {'shot_id': 's2_shot2', 'duration_sec': 2.0, 'framing': 'Tighter close-up while keeping the full bottle shape visible enough to preserve recognition.', 'camera_motion': 'Gentle continued push-in, then hold.', 'subject_motion': 'No movement.', 'environment_motion': 'None.', 'transition': 'Natural continuation within the same scene.'}], 'audio_direction': {'generate_audio': True, 'mode': 'music_plus_minimal_sfx', 'ambience': 'Bright pop rhythm with a crisp, refreshing feel.', 'sfx_timeline': [{'at_sec': 1.0, 'cue': 'Light shimmer accent', 'linked_visual_action': 'The label area comes into clearer focus.'}, {'at_sec': 3.2, 'cue': 'Soft bass pulse', 'linked_visual_action': 'The camera reaches the tighter product framing.'}], 'dialogue': []}, 'text_overlay': {'enabled': False, 'copy': None, 'safe_area': 'Lower third kept clear, though no overlay is used.'}, 'continuity': {'previous_scene_transition': 'Continue the clean product spotlight with a closer framing.', 'next_scene_transition': 'Cut back to a full-product centered view for the final CTA beat.', 'continuity_requirements': ['Do not alter the bottle color, cap color, or label text layout.', 'Keep the background pure white and free of props or scenery.']}}, {'id': 'scene_03', 'duration_sec': 5.0, 'visual_purpose': 'Deliver the final brand impression and CTA with the product still as the only subject.', 'narrative_beat': 'The bottle returns to a clean full-frame hero, ending on the simple summer mood and call to action.', 'starting_image': {'image_path': 'assets/prime.png', 'description': 'Reference product image of the PRIME Hydration Lemonade bottle on white, centered and unchanged for the final CTA beat.'}, 'scene_intent': {'audience_feeling': 'Confident, energized, and ready to act.', 'cinematic_style': 'Premium social ad end card with minimal motion and strong product clarity.', 'pace': 'Clean finish with a slight lift in energy.'}, 'shot_sequence': [{'shot_id': 's3_shot1', 'duration_sec': 3.0, 'framing': 'Full bottle centered again, with the label and yellow body clearly visible.', 'camera_motion': 'Very subtle pull-back to restore breathing room around the product.', 'subject_motion': 'Bottle remains fixed.', 'environment_motion': 'None.', 'transition': 'Cut from the tighter label view back to the full hero composition.'}, {'shot_id': 's3_shot2', 'duration_sec': 2.0, 'framing': 'Hold on the centered product for the CTA moment.', 'camera_motion': 'Static hold.', 'subject_motion': 'No movement.', 'environment_motion': 'None.', 'transition': 'Fade out to white at the end.'}], 'audio_direction': {'generate_audio': True, 'mode': 'music_plus_minimal_sfx', 'ambience': 'Upbeat sunny groove with a clean finish.', 'sfx_timeline': [{'at_sec': 0.8, 'cue': 'Soft rise', 'linked_visual_action': 'The product settles into the final centered hero hold.'}, {'at_sec': 3.8, 'cue': 'Gentle hit for CTA emphasis', 'linked_visual_action': 'The final hold lands before fade out.'}], 'dialogue': ['Spot the yellow. Grab the vibe.']}, 'text_overlay': {'enabled': True, 'copy': 'Spot the yellow. Grab the vibe.', 'safe_area': 'Lower third, with the bottle kept fully unobstructed in the center.'}, 'continuity': {'previous_scene_transition': 'Return to the full product hero without changing any visible packaging details.', 'next_scene_transition': 'Fade out on white after the CTA hold.', 'continuity_requirements': ['Preserve the exact visible text: LEMONADE, FLAVOUR, PRIME, HYDRATION, and 500 mL.', 'Keep the composition centered, minimal, and free of any additional objects or background elements.']}}]}
        storyboard_brief = {
            "product_analysis": product_analysis,
            "narrative_strategy": narrative_strategy,
            "product_image_path": str(product_image_path),
            "target_duration_sec": target_duration_sec,
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio,
            "scene_guidance": (
                "Ensure that the total durations of all scenes add up to the target_duration_sec value."
                "Use the provided product image path as the reference image path "
                "for starting images unless a later generated start frame is "
                "explicitly needed."
            ),
        }
        return self._run_sdk(
            user_input=f"Create the storyboard from this brief:\n {json.dumps(storyboard_brief, indent=2)}"
        )
