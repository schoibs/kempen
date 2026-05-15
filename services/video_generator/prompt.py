from __future__ import annotations

from typing import Any


def build_video_prompt(
    product_analysis: dict[str, Any],
    campaign_input: dict[str, Any],
) -> str:
    product_name = product_analysis.get("product_name", "the campaign product")
    aspect_ratio = campaign_input.get("aspect_ratio", "9:16")
    target_duration_sec = campaign_input.get("target_duration_sec", 15)

    return f"""Generate a {aspect_ratio} video using the provided storyboard sheet (@Image1) as the direct sequential visual keyframe reference for the entire video.

The video is a {target_duration_sec}-second campaign advertisement video about a product called {product_name} (@Image2).

Use @Image1 as the scene-by-scene structure, pacing, composition, and keyframe guide. Use @Image2 as the exact product identity reference whenever the product appears.

Make it feel like a polished, story-rich social campaign ad with coherent transitions, stable product continuity, realistic motion, and high-energy cinematic rhythm."""
