from __future__ import annotations

import logging
import os
import time
import fal_client

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


logger = logging.getLogger(__name__)


class VideoGenerationClientError(RuntimeError):
    """Raised when video generation fails or returns unusable output."""


@dataclass(frozen=True)
class VideoGenerationClientOutput:
    video_path: str
    video_url: str
    seed: int | None = None
    request_id: str | None = None
    provider_metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class VideoGenerationSubmission:
    request_id: str


@dataclass(frozen=True)
class VideoGenerationPollOutput:
    request_id: str
    status: str
    provider_metadata: dict[str, Any]


@dataclass
class VideoGenerationClient:
    """fal.ai Reference-to-Video client for Seedance campaign video generation."""

    model_endpoint: str = "bytedance/seedance-2.0/reference-to-video"
    api_key: str | None = None
    fal_client: Any | None = None
    status_poll_interval: float = 2.0
    start_timeout: int | float | None = None
    download_timeout: int | float | None = 300
    max_download_bytes: int = 500 * 1024 * 1024

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY is required for VideoGenerationClient.")

        os.environ["FAL_KEY"] = self.api_key

    def generate_from_references(
        self,
        storyboard_image_path: str | Path,
        product_image_path: str | Path,
        prompt: str,
        output_path: str | Path,
        resolution: str = "720p",
        duration: str = "15",
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
    ) -> VideoGenerationClientOutput:
        submission = self.submit_from_references(
            storyboard_image_path=storyboard_image_path,
            product_image_path=product_image_path,
            prompt=prompt,
            resolution=resolution,
            duration=duration,
            aspect_ratio=aspect_ratio,
            generate_audio=generate_audio,
        )
        while True:
            poll = self.poll_request(request_id=submission.request_id)
            if poll.status == "completed":
                return self.finalize_request(
                    request_id=submission.request_id,
                    output_path=output_path,
                )
            time.sleep(self.status_poll_interval)

    def submit_from_references(
        self,
        *,
        storyboard_image_path: str | Path,
        product_image_path: str | Path,
        prompt: str,
        resolution: str = "720p",
        duration: str = "15",
        aspect_ratio: str = "9:16",
        generate_audio: bool = True,
    ) -> VideoGenerationSubmission:
        storyboard_path = self._validate_file_path(storyboard_image_path, "Storyboard image")
        product_path = self._validate_file_path(product_image_path, "Product image")

        fal = self._fal_client()

        try:
            logger.info("Uploading storyboard image to fal CDN.")
            storyboard_url = fal.upload_file(str(storyboard_path))
            logger.info("Uploading product image to fal CDN.")
            product_url = fal.upload_file(str(product_path))

            arguments = {
                "prompt": prompt,
                "image_urls": [storyboard_url, product_url],
                "resolution": resolution,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "generate_audio": generate_audio,
            }

            logger.info("Submitting Seedance reference-to-video request to fal.")
            submit_kwargs: dict[str, Any] = {"arguments": arguments}
            if self.start_timeout is not None:
                submit_kwargs["start_timeout"] = self.start_timeout
            handler = fal.submit(self.model_endpoint, **submit_kwargs)
            request_id = getattr(handler, "request_id", None)
            if not isinstance(request_id, str) or not request_id:
                raise VideoGenerationClientError(
                    "fal video submission did not return a request ID."
                )
            logger.info("fal video request submitted: request_id=%s", request_id)
        except Exception as exc:
            raise VideoGenerationClientError(f"fal video submission failed: {exc}") from exc

        return VideoGenerationSubmission(request_id=request_id)

    def poll_request(self, *, request_id: str) -> VideoGenerationPollOutput:
        try:
            provider_status = self._fal_client().status(
                self.model_endpoint,
                request_id,
                with_logs=False,
            )
        except Exception as exc:
            raise VideoGenerationClientError(f"fal video status request failed: {exc}") from exc

        status_name = type(provider_status).__name__.lower()
        status = {
            "queued": "queued",
            "inprogress": "in_progress",
            "completed": "completed",
        }.get(status_name, status_name)
        provider_metadata: dict[str, Any] = {}
        position = getattr(provider_status, "position", None)
        if isinstance(position, int):
            provider_metadata["queue_position"] = position
        metrics = getattr(provider_status, "metrics", None)
        if isinstance(metrics, dict):
            provider_metadata["metrics"] = metrics
        logger.info("fal video request polled: request_id=%s status=%s", request_id, status)
        return VideoGenerationPollOutput(
            request_id=request_id,
            status=status,
            provider_metadata=provider_metadata,
        )

    def finalize_request(
        self,
        *,
        request_id: str,
        output_path: str | Path,
    ) -> VideoGenerationClientOutput:
        destination_path = Path(output_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = self._fal_client().result(self.model_endpoint, request_id)
        except Exception as exc:
            raise VideoGenerationClientError(f"fal video result request failed: {exc}") from exc

        video_url = self._extract_video_url(result)
        seed = result.get("seed") if isinstance(result, dict) else None
        provider_metadata: dict[str, Any] = {}
        if isinstance(result, dict) and isinstance(result.get("usage"), dict):
            provider_metadata["usage"] = result["usage"]
        self._download_video(video_url=video_url, output_path=destination_path)

        return VideoGenerationClientOutput(
            video_path=str(destination_path),
            video_url=video_url,
            seed=seed if isinstance(seed, int) else None,
            request_id=request_id,
            provider_metadata=provider_metadata,
        )

    def cancel_request(self, *, request_id: str) -> None:
        """Best-effort cancellation for a durable fal request ID."""

        try:
            self._fal_client().cancel(self.model_endpoint, request_id)
        except Exception as exc:
            raise VideoGenerationClientError("fal video cancellation failed.") from exc
        logger.info("fal video cancellation requested: request_id=%s", request_id)

    def _fal_client(self) -> Any:
        if self.fal_client is not None:
            return self.fal_client

        self.fal_client = fal_client
        return self.fal_client

    @staticmethod
    def _validate_file_path(path: str | Path, label: str) -> Path:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"{label} not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"{label} must be a file: {file_path}")
        return file_path

    @staticmethod
    def _extract_video_url(result: Any) -> str:
        if not isinstance(result, dict):
            raise VideoGenerationClientError(
                f"fal video response must be a dict, got {type(result).__name__}."
            )

        video = result.get("video")
        if not isinstance(video, dict):
            raise VideoGenerationClientError("fal video response did not contain a video object.")

        video_url = video.get("url")
        if not isinstance(video_url, str) or not video_url:
            raise VideoGenerationClientError("fal video response did not contain video.url.")

        return video_url

    def _download_video(self, *, video_url: str, output_path: Path) -> None:
        try:
            with requests.get(video_url, stream=True, timeout=self.download_timeout) as response:
                response.raise_for_status()
                with output_path.open("wb") as video_file:
                    total_bytes = 0
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            total_bytes += len(chunk)
                            if total_bytes > self.max_download_bytes:
                                raise VideoGenerationClientError(
                                    "Generated video exceeds the configured size limit."
                                )
                            video_file.write(chunk)
                if total_bytes == 0:
                    raise VideoGenerationClientError("Generated video download was empty.")
        except VideoGenerationClientError:
            raise
        except Exception as exc:
            raise VideoGenerationClientError(f"Could not download generated video: {exc}") from exc
