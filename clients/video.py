from __future__ import annotations

import logging
import os
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


@dataclass
class VideoGenerationClient:
    """fal.ai Reference-to-Video client for Seedance campaign video generation."""

    model_endpoint: str = "bytedance/seedance-2.0/reference-to-video"
    api_key: str | None = None
    fal_client: Any | None = None
    status_poll_interval: float = 2.0
    start_timeout: int | float | None = None
    download_timeout: int | float | None = 300

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
        storyboard_path = self._validate_file_path(storyboard_image_path, "Storyboard image")
        product_path = self._validate_file_path(product_image_path, "Product image")
        destination_path = Path(output_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        fal = self._fal_client()

        try:
            logger.info(f"Uploading storyboard image to fal CDN: {storyboard_path}")
            storyboard_url = fal.upload_file(str(storyboard_path))
            logger.info(f"Uploading product image to fal CDN: {product_path}")
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
            if request_id:
                logger.info(f"fal video request submitted: {request_id}")

            for event in handler.iter_events(
                with_logs=True,
                interval=self.status_poll_interval,
            ):
                self._log_queue_event(event)

            result = handler.get()
        except Exception as exc:
            raise VideoGenerationClientError(f"fal video generation request failed: {exc}") from exc

        video_url = self._extract_video_url(result)
        seed = result.get("seed") if isinstance(result, dict) else None
        self._download_video(video_url=video_url, output_path=destination_path)

        return VideoGenerationClientOutput(
            video_path=str(destination_path),
            video_url=video_url,
            seed=seed if isinstance(seed, int) else None,
            request_id=request_id,
        )

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
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            video_file.write(chunk)
        except Exception as exc:
            raise VideoGenerationClientError(f"Could not download generated video: {exc}") from exc

    @staticmethod
    def _log_queue_event(event: Any) -> None:
        event_name = type(event).__name__
        position = getattr(event, "position", None)
        if position is not None:
            logger.info(f"fal request queued: position={position}")
            return

        logs = getattr(event, "logs", None) or []
        if logs:
            for log in logs:
                message = log.get("message") if isinstance(log, dict) else str(log)
                logger.info(f"fal {event_name}: {message}")
            return

        logger.info(f"fal request status: {event_name}")
