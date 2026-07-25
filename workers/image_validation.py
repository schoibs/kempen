from __future__ import annotations

import hashlib
import warnings

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app_config import Settings
from persistence.models import Asset
from storage import ObjectStorage


class InputImageValidationError(RuntimeError):
    """Raised before any paid stage when an input asset is not a safe image."""


@dataclass(frozen=True)
class ValidatedImage:
    content_type: str
    width: int
    height: int
    sha256: str
    size_bytes: int
    local_path: str


FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def download_and_validate_product_image(
    *,
    storage: ObjectStorage,
    asset: Asset,
    output_path: str | Path,
    settings: Settings,
) -> ValidatedImage:
    """Bound, decode, normalize, and verify a ready product image for a worker."""

    if asset.status != "ready":
        raise InputImageValidationError("Input asset is not ready.")

    image_bytes = storage.download_bytes(
        object_key=asset.object_key,
        max_bytes=settings.max_upload_bytes,
    )
    if not image_bytes:
        raise InputImageValidationError("Input image is empty.")
    if len(image_bytes) != asset.size_bytes:
        raise InputImageValidationError("Input image size does not match asset metadata.")

    checksum = hashlib.sha256(image_bytes).hexdigest()
    if asset.sha256 and checksum != asset.sha256:
        raise InputImageValidationError("Input image checksum does not match asset metadata.")

    image_format, width, height = _inspect_image(image_bytes=image_bytes, settings=settings)
    content_type = FORMAT_CONTENT_TYPES[image_format]
    if not _has_valid_container(image_bytes=image_bytes, image_format=image_format):
        raise InputImageValidationError("Input image contains trailing or invalid container data.")
    if content_type != asset.content_type:
        raise InputImageValidationError("Input image bytes do not match the declared content type.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _write_normalized_image(
        image_bytes=image_bytes,
        image_format=image_format,
        destination=destination,
    )
    return ValidatedImage(
        content_type=content_type,
        width=width,
        height=height,
        sha256=checksum,
        size_bytes=len(image_bytes),
        local_path=str(destination),
    )


def _inspect_image(*, image_bytes: bytes, settings: Settings) -> tuple[str, int, int]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as image:
                image.verify()
            with Image.open(BytesIO(image_bytes)) as image:
                image_format = image.format
                if image_format not in FORMAT_CONTENT_TYPES:
                    raise InputImageValidationError("Input image format is not supported.")
                if bool(getattr(image, "is_animated", False)) or getattr(image, "n_frames", 1) != 1:
                    raise InputImageValidationError("Animated images are not supported.")
                width, height = image.size
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError) as exc:
        raise InputImageValidationError("Input bytes are not a valid image.") from exc

    if width > settings.max_image_width or height > settings.max_image_height:
        raise InputImageValidationError("Input image dimensions exceed the configured limit.")
    if width * height > settings.max_image_pixels:
        raise InputImageValidationError("Input image has too many pixels.")
    return image_format, width, height


def _write_normalized_image(
    *,
    image_bytes: bytes,
    image_format: str,
    destination: Path,
) -> None:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            normalized = ImageOps.exif_transpose(image)
            if image_format == "JPEG" and normalized.mode not in {"RGB", "L"}:
                normalized = normalized.convert("RGB")
            normalized.save(destination, format=image_format)
    except (OSError, ValueError) as exc:
        raise InputImageValidationError("Input image could not be normalized.") from exc


def _has_valid_container(*, image_bytes: bytes, image_format: str) -> bool:
    if image_format == "PNG":
        return image_bytes.startswith(b"\x89PNG\r\n\x1a\n") and image_bytes.endswith(
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
    if image_format == "JPEG":
        return image_bytes.startswith(b"\xff\xd8") and image_bytes.endswith(b"\xff\xd9")
    if image_format == "WEBP":
        return (
            image_bytes.startswith(b"RIFF")
            and image_bytes[8:12] == b"WEBP"
            and len(image_bytes) >= 12
            and int.from_bytes(image_bytes[4:8], "little") + 8 == len(image_bytes)
        )
    return False
