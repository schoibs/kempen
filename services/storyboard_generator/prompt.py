from __future__ import annotations

from typing import Any


def build_storyboard_prompt(
    product_analysis: dict[str, Any],
    narrative_strategy: dict[str, Any],
    campaign_input: dict[str, Any],
) -> str:
    product_name = product_analysis.get("product_name", "the campaign product")
    product_category = product_analysis.get("category", "consumer product")

    aspect_ratio = campaign_input.get("aspect_ratio", "9:16")
    target_duration_sec = campaign_input.get("target_duration_sec", 15)
    tone = narrative_strategy.get("tone") or []
    tone_text = ", ".join(str(item) for item in tone) if tone else "cinematic, branded, energetic"

    return f"""Generate a hyper-realistic 9-panel cinematic storyboard sheet for a {target_duration_sec}-second social media campaign ad ({aspect_ratio} aspect ratio) using the attached reference image.

The attached reference image is the product called: {product_name}. Its category is {product_category}.

For the campaign ad, here is the rough outline of the video:
1. story_premise: "{narrative_strategy.get('story_premise', '')}"
2. hook: "{narrative_strategy.get('hook', '')}"
3. conflict: "{narrative_strategy.get('conflict', '')}"
4. concept: "{narrative_strategy.get('concept', '')}"
5. tone: {tone_text}

Storyboard sheet requirements:
- Show 9 numbered cinematic panels, each a distinct keyframe from the ad.
- Each storyboard panel must be a {aspect_ratio} panel.
- Avoid distorted objects, misspelled label text, unreadable product text, warped hands, warped faces, duplicate limbs, and random objects.

The finished image should feel like a polished agency storyboard board and ready to guide image-to-video generation."""
