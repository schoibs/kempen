from __future__ import annotations

import logging

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from httpx import request

from clients import VideoGenerationClient, VideoGenerationClientError

from .prompt import build_video_prompt


logger = logging.getLogger(__name__)


class VideoGeneratorServiceError(RuntimeError):
    """Raised when video generation cannot produce usable output."""


@dataclass(frozen=True)
class VideoGeneratorServiceOutput:
    video_path: str
    video_url: str
    seed: int | None = None
    request_id: str | None = None


class VideoGeneratorService:
    """Generate a final campaign video from storyboard and product references."""

    default_model_endpoint = "bytedance/seedance-2.0/reference-to-video"
    default_resolution = "720p"
    default_generate_audio = True
    default_output_path = Path("assets/generated/campaign_video.mp4")

    supported_durations = [str(duration) for duration in range(4, 16)]
    supported_aspect_ratios = ["auto", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]

    def __init__(
        self,
        model_endpoint: str = default_model_endpoint,
        resolution: str = default_resolution,
        generate_audio: bool = default_generate_audio,
        video_client: Any | None = None,
    ) -> None:
        self.model_endpoint = model_endpoint
        self.resolution = resolution
        self.generate_audio = generate_audio
        self.video_client = video_client

    def run(
        self,
        storyboard_image_path: str | Path,
        product_image_path: str | Path,
        product_analysis: dict[str, Any],
        campaign_input: Any,
        output_path: str | Path | None = None,
    ) -> VideoGeneratorServiceOutput:

        # TODO: to remove this comment
        # return VideoGeneratorServiceOutput(
        #     video_path="assets/generated/campaign_video.mp4",
        #     video_url="xxx",
        #     seed=67,
        #     request_id="xxx"
        # )

        campaign_input_dict = self._campaign_input_to_dict(campaign_input)
        output_path = Path(output_path or self.default_output_path)

        duration = str(campaign_input_dict.get("target_duration_sec", 15))
        aspect_ratio = str(campaign_input_dict.get("aspect_ratio", "9:16"))
        
        if duration not in self.supported_durations:
            raise ValueError(
                "Seedance reference-to-video duration must be an integer from 4 through 15 seconds, "
                f"got {duration!r}."
            )
        if aspect_ratio not in self.supported_aspect_ratios:
            supported = ", ".join(sorted(self.supported_aspect_ratios))
            raise ValueError(
                f"Seedance reference-to-video aspect_ratio must be one of {supported}, got {aspect_ratio}."
            )

        prompt = build_video_prompt(
            product_analysis=product_analysis,
            campaign_input=campaign_input_dict,
        )

        logger.info(f"Generating campaign video at {output_path}")
        try:
            generated_video = self._video_client().generate_from_references(
                storyboard_image_path=storyboard_image_path,
                product_image_path=product_image_path,
                prompt=prompt,
                output_path=output_path,
                resolution=self.resolution,
                duration=duration,
                aspect_ratio=aspect_ratio,
                generate_audio=self.generate_audio,
            )
        except (VideoGenerationClientError, Exception) as exc:
            raise VideoGeneratorServiceError(f"Video generation failed: {exc}") from exc

        return VideoGeneratorServiceOutput(
            video_path=generated_video.video_path,
            video_url=generated_video.video_url,
            seed=generated_video.seed,
            request_id=generated_video.request_id,
        )

    def _video_client(self) -> VideoGenerationClient:
        if self.video_client is None:
            self.video_client = VideoGenerationClient(model_endpoint=self.model_endpoint)
        return self.video_client


    @staticmethod
    def _campaign_input_to_dict(campaign_input: Any) -> dict[str, Any]:
        if isinstance(campaign_input, dict):
            return dict(campaign_input)
        if is_dataclass(campaign_input):
            return asdict(campaign_input)

        return {
            "product_image_path": getattr(campaign_input, "product_image_path", None),
            "campaign_theme": getattr(campaign_input, "campaign_theme", None),
            "target_audience": getattr(campaign_input, "target_audience", None),
            "target_duration_sec": getattr(campaign_input, "target_duration_sec", 15),
            "aspect_ratio": getattr(campaign_input, "aspect_ratio", "9:16"),
        }
