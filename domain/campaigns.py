from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CampaignInput:
    """Internal campaign brief after its input image has been resolved locally."""

    product_image_path: str
    campaign_theme: str
    target_audience: str
    target_duration_sec: int = 15
    aspect_ratio: str = "9:16"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
