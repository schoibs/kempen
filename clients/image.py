from __future__ import annotations

import base64
import os

from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI


class ImageGenerationClientError(RuntimeError):
    """Raised when image generation fails or returns unusable output."""


@dataclass
class ImageGenerationClient:
    """OpenAI Image API client for reference-guided image generation."""

    model: str = "gpt-image-2"
    api_key: str | None = None
    timeout: float | None = 180
    _client: OpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for ImageGenerationClient.")

        self._client = OpenAI(api_key=self.api_key, timeout=self.timeout)

    def edit_with_reference(
        self,
        *,
        reference_image_path: str | Path,
        prompt: str,
        output_path: str | Path,
        size: str = "1152x2048",
        quality: str = "medium",
        output_format: str = "png",
    ) -> Path:
        image_path = Path(reference_image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Reference image not found: {image_path}")

        destination_path = Path(output_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with image_path.open("rb") as image_file:
                response = self._client.images.edit(
                    model=self.model,
                    image=image_file,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    output_format=output_format,
                    response_format="b64_json",
                )
        except Exception as exc:
            raise ImageGenerationClientError(f"OpenAI image edit request failed: {exc}") from exc

        if not response.data:
            raise ImageGenerationClientError("OpenAI image edit response did not contain image data.")

        image_data = response.data[0].b64_json
        if not image_data:
            raise ImageGenerationClientError("OpenAI image edit response did not contain base64 image data.")

        try:
            destination_path.write_bytes(base64.b64decode(image_data))
        except Exception as exc:
            raise ImageGenerationClientError(f"Could not write generated image: {exc}") from exc

        return destination_path
