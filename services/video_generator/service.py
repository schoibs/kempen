from __future__ import annotations

import logging
import time

from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from httpx import request

from app_config import get_settings
from clients import (
    VideoGenerationClient,
    VideoGenerationClientError,
    VideoGenerationPollOutput,
    VideoGenerationSubmission,
)

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
    provider_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class VideoGeneratorServiceSubmissionOutput:
    request_id: str


@dataclass(frozen=True)
class VideoGeneratorServicePollOutput:
    request_id: str
    status: str
    provider_metadata: dict[str, Any]


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
        submission = self.submit(
            storyboard_image_path=storyboard_image_path,
            product_image_path=product_image_path,
            product_analysis=product_analysis,
            campaign_input=campaign_input,
        )
        while True:
            poll = self.poll(request_id=submission.request_id)
            if poll.status == "completed":
                break
            time.sleep(self._video_client().status_poll_interval)
        return self.finalize(
            request_id=submission.request_id,
            output_path=output_path or self.default_output_path,
        )

    def submit(
        self,
        *,
        storyboard_image_path: str | Path,
        product_image_path: str | Path,
        product_analysis: dict[str, Any],
        campaign_input: Any,
    ) -> VideoGeneratorServiceSubmissionOutput:
        campaign_input_dict = self._campaign_input_to_dict(campaign_input)
        duration, aspect_ratio = self._validate_settings(campaign_input_dict)
        prompt = build_video_prompt(
            product_analysis=product_analysis,
            campaign_input=campaign_input_dict,
        )

        logger.info("Submitting campaign video generation request.")
        try:
            submission: VideoGenerationSubmission = self._video_client().submit_from_references(
                storyboard_image_path=storyboard_image_path,
                product_image_path=product_image_path,
                prompt=prompt,
                resolution=self.resolution,
                duration=duration,
                aspect_ratio=aspect_ratio,
                generate_audio=self.generate_audio,
            )
        except (VideoGenerationClientError, OSError, ValueError) as exc:
            raise VideoGeneratorServiceError(f"Video submission failed: {exc}") from exc
        return VideoGeneratorServiceSubmissionOutput(request_id=submission.request_id)

    def poll(self, *, request_id: str) -> VideoGeneratorServicePollOutput:
        try:
            poll: VideoGenerationPollOutput = self._video_client().poll_request(
                request_id=request_id,
            )
        except VideoGenerationClientError as exc:
            raise VideoGeneratorServiceError(f"Video status request failed: {exc}") from exc
        return VideoGeneratorServicePollOutput(
            request_id=poll.request_id,
            status=poll.status,
            provider_metadata=poll.provider_metadata,
        )

    def finalize(
        self,
        *,
        request_id: str,
        output_path: str | Path,
    ) -> VideoGeneratorServiceOutput:
        logger.info("Finalizing campaign video artifact.")
        try:
            generated_video = self._video_client().finalize_request(
                request_id=request_id,
                output_path=output_path,
            )
        except (VideoGenerationClientError, OSError, ValueError) as exc:
            raise VideoGeneratorServiceError(f"Video finalization failed: {exc}") from exc
        return VideoGeneratorServiceOutput(
            video_path=generated_video.video_path,
            video_url=generated_video.video_url,
            seed=generated_video.seed,
            request_id=generated_video.request_id,
            provider_metadata=generated_video.provider_metadata,
        )

    def cancel(self, *, request_id: str) -> None:
        try:
            self._video_client().cancel_request(request_id=request_id)
        except VideoGenerationClientError as exc:
            raise VideoGeneratorServiceError("Video cancellation failed.") from exc

    def _video_client(self) -> VideoGenerationClient:
        if self.video_client is None:
            self.video_client = VideoGenerationClient(
                model_endpoint=self.model_endpoint,
                max_download_bytes=get_settings().max_generated_video_bytes,
            )
        return self.video_client

    def _validate_settings(
        self,
        campaign_input_dict: dict[str, Any],
    ) -> tuple[str, str]:
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
        return duration, aspect_ratio


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
