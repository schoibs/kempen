from __future__ import annotations

import base64
import json
import shutil
import time
import uuid

from pathlib import Path
from typing import Any

from app_config import get_settings
from campaign_agents import NarrativeStrategistAgent, ProductAnalysisAgent
from services import StoryboardGeneratorService, VideoGeneratorService

from .campaigns import CampaignInput


# One-frame H.264 MP4 used only for deterministic fake-provider output.
_FAKE_VIDEO_BASE64 = (
    "AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAAAr9tZGF0AAACoAYF//+c3EXpvebZSLeWLNgg2SPu73gyNjQgLSBjb3JlIDEyNSAtIEguMjY0L01QRUctNCBBVkMgY29kZWMgLSBDb3B5bGVmdCAyMDAzLTIwMTIgLSBodHRwOi8vd3d3LnZpZGVvbGFuLm9yZy94MjY0Lmh0bWwgLSBvcHRpb25zOiBjYWJhYz0xIHJlZj0zIGRlYmxvY2s9MTowOjAgYW5hbHlzZT0weDM6MHgxMTMgbWU9aGV4IHN1Ym1lPTcgcHN5PTEgcHN5X3JkPTEuMDA6MC4wMiBtaXhlZF9yZWY9MSBtZV9yYW5nZT0xNiBjaHJvbWFfbWU9MSB0cmVsbGlzPTEgOHg4ZGN0PTEgY3FtPTAgZGVhZHpvbmU9MjEsMTEgZmFzdF9wc2tpcD0xIGNocm9tYV9xcF9vZmZzZXQ9LTIgdGhyZWFkcz02IGxvb2thaGVhZF90aHJlYWRzPTEgc2xpY2VkX3RocmVhZHM9MCBucj0wIGRlY2ltYXRlPTEgaW50ZXJsYWNlZD0wIGJsdXJheV9jb21wYXQ9MCBjb25zdHJhaW5lZF9pbnRyYT0wIGJmcmFtZXM9MyBiX3B5cmFtaWQ9MiBiX2FkYXB0PTEgYl9iaWFzPTAgZGlyZWN0PTEgd2VpZ2h0Yj0xIG9wZW5fZ29wPTAgd2VpZ2h0cD0yIGtleWludD0yNTAga2V5aW50X21pbj0yNCBzY2VuZWN1dD00MCBpbnRyYV9yZWZyZXNoPTAgcmNfbG9va2FoZWFkPTQwIHJjPWNyZiBtYnRyZWU9MSBjcmY9MjMuMCBxY29tcD0wLjYwIHFwbWluPTAgcXBtYXg9NjkgcXBzdGVwPTQgaXBfcmF0aW89MS40MCBhcT0xOjEuMDAAgAAAAA9liIQAV/0TAAYdeBTXzg8AAALvbW9vdgAAAGxtdmhkAAAAAAAAAAAAAAAAAAAD6AAAACoAAQAAAQAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAhl0cmFrAAAAXHRraGQAAAAPAAAAAAAAAAAAAAABAAAAAAAAACoAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAABAAAAAAAgAAAAIAAAAAAAkZWR0cwAAABxlbHN0AAAAAAAAAAEAAAAqAAAAAAABAAAAAAGRbWRpYQAAACBtZGhkAAAAAAAAAAAAAAAAAAAwAAAAAgBVxAAAAAAALWhkbHIAAAAAAAAAAHZpZGUAAAAAAAAAAAAAAABWaWRlb0hhbmRsZXIAAAABPG1pbmYAAAAUdm1oZAAAAAEAAAAAAAAAAAAAACRkaW5mAAAAHGRyZWYAAAAAAAAAAQAAAAx1cmwgAAAAAQAAAPxzdGJsAAAAmHN0c2QAAAAAAAAAAQAAAIhhdmMxAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAgACABIAAAASAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGP//AAAAMmF2Y0MBZAAK/+EAGWdkAAqs2V+WXAWyAAADAAIAAAMAYB4kSywBAAZo6+PLIsAAAAAYc3R0cwAAAAAAAAABAAAAAQAAAgAAAAAcc3RzYwAAAAAAAAABAAAAAQAAAAEAAAABAAAAFHN0c3oAAAAAAAACtwAAAAEAAAAUc3RjbwAAAAAAAAABAAAAMAAAAGJ1ZHRhAAAAWm1ldGEAAAAAAAAAIWhkbHIAAAAAAAAAAG1kaXJhcHBsAAAAAAAAAAAAAAAALWlsc3QAAAAlqXRvbwAAAB1kYXRhAAAAAQAAAABMYXZmNTQuNjMuMTA0"
)


class CampaignStageOperations:
    """Explicit, JSON-serializable operations for the fixed campaign pipeline."""

    def __init__(
        self,
        *,
        fake_provider_mode: bool | None = None,
        product_agent: ProductAnalysisAgent | None = None,
        narrative_agent: NarrativeStrategistAgent | None = None,
        storyboard_service: StoryboardGeneratorService | None = None,
        video_service: VideoGeneratorService | None = None,
    ) -> None:
        self.fake_provider_mode = (
            get_settings().fake_provider_mode
            if fake_provider_mode is None
            else fake_provider_mode
        )
        self._product_agent = product_agent
        self._narrative_agent = narrative_agent
        self._storyboard_service = storyboard_service
        self._video_service = video_service

    def analyze_product(self, *, product_image_path: str | Path) -> dict[str, Any]:
        image_path = self._require_file(product_image_path, "Product image")
        if self.fake_provider_mode:
            self._simulate_fake_provider("product_analysis")
            return {
                "product_name": image_path.stem.replace("_", " ").title(),
                "category": "Test product",
                "primary_colors": {"name": "Neutral", "hex": "#808080"},
                "visible_facts": ["Fake provider inspected the supplied product image."],
                "additional_facts": ["Fake provider mode does not perform web research."],
            }

        return self._json_object(
            self._product_analysis_agent().run(product_image_path=image_path),
            "Product analysis",
        )

    def build_narrative(
        self,
        *,
        product_analysis: dict[str, Any],
        campaign_input: CampaignInput,
    ) -> dict[str, Any]:
        product_analysis = self._json_object(product_analysis, "Product analysis")
        if self.fake_provider_mode:
            self._simulate_fake_provider("narrative_strategy")
            return {
                "concept": f"A concise campaign for {product_analysis['product_name']}.",
                "story_premise": campaign_input.campaign_theme,
                "hook": "The product enters the frame.",
                "conflict": "The audience needs a compelling reason to engage.",
                "tone": ["clear", "upbeat"],
            }

        return self._json_object(
            self._narrative_strategist_agent().run(
                product_analysis=product_analysis,
                campaign_theme=campaign_input.campaign_theme,
                target_audience=campaign_input.target_audience,
                target_duration_sec=campaign_input.target_duration_sec,
            ),
            "Narrative strategy",
        )

    def generate_storyboard(
        self,
        *,
        product_image_path: str | Path,
        product_analysis: dict[str, Any],
        narrative_strategy: dict[str, Any],
        campaign_input: CampaignInput,
        output_path: str | Path,
    ) -> dict[str, Any]:
        image_path = self._require_file(product_image_path, "Product image")
        destination_path = Path(output_path)
        if self.fake_provider_mode:
            self._simulate_fake_provider("storyboard_generation")
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(image_path, destination_path)
            return {"image_path": str(destination_path)}

        output = self._storyboard_generator_service().run(
            product_image_path=image_path,
            product_analysis=self._json_object(product_analysis, "Product analysis"),
            narrative_strategy=self._json_object(narrative_strategy, "Narrative strategy"),
            campaign_input=campaign_input,
            output_path=destination_path,
        )
        return self._json_object({"image_path": output.image_path}, "Storyboard output")

    def submit_video(
        self,
        *,
        storyboard_image_path: str | Path,
        product_image_path: str | Path,
        product_analysis: dict[str, Any],
        campaign_input: CampaignInput,
    ) -> dict[str, Any]:
        if self.fake_provider_mode:
            self._simulate_fake_provider("video_submission")
            self._require_file(storyboard_image_path, "Storyboard image")
            self._require_file(product_image_path, "Product image")
            return {
                "request_id": f"fake_{uuid.uuid4().hex}",
                "provider": "fake",
            }

        output = self._video_generator_service().submit(
            storyboard_image_path=storyboard_image_path,
            product_image_path=product_image_path,
            product_analysis=self._json_object(product_analysis, "Product analysis"),
            campaign_input=campaign_input,
        )
        return self._json_object(
            {"request_id": output.request_id, "provider": "fal"},
            "Video submission",
        )

    def poll_video(self, *, request_id: str) -> dict[str, Any]:
        if self.fake_provider_mode:
            self._simulate_fake_provider("video_poll")
            return {
                "request_id": request_id,
                "status": "completed",
                "provider_metadata": {},
            }

        output = self._video_generator_service().poll(request_id=request_id)
        return self._json_object(
            {
                "request_id": output.request_id,
                "status": output.status,
                "provider_metadata": output.provider_metadata,
            },
            "Video poll",
        )

    def finalize_video(
        self,
        *,
        request_id: str,
        output_path: str | Path,
    ) -> dict[str, Any]:
        destination_path = Path(output_path)
        if self.fake_provider_mode:
            self._simulate_fake_provider("video_finalize")
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(base64.b64decode(_FAKE_VIDEO_BASE64, validate=True))
            return {
                "video_path": str(destination_path),
                "video_url": f"fake://video/{request_id}",
                "seed": None,
                "request_id": request_id,
            }

        output = self._video_generator_service().finalize(
            request_id=request_id,
            output_path=destination_path,
        )
        return self._json_object(
            {
                "video_path": output.video_path,
                "video_url": output.video_url,
                "seed": output.seed,
                "request_id": output.request_id,
                "provider_metadata": output.provider_metadata or {},
            },
            "Video output",
        )

    def cancel_video(self, *, request_id: str) -> None:
        if self.fake_provider_mode:
            self._simulate_fake_provider("video_cancel")
            return
        self._video_generator_service().cancel(request_id=request_id)

    def _product_analysis_agent(self) -> ProductAnalysisAgent:
        if self._product_agent is None:
            self._product_agent = ProductAnalysisAgent(model="gpt-5.4-mini")
        return self._product_agent

    def _narrative_strategist_agent(self) -> NarrativeStrategistAgent:
        if self._narrative_agent is None:
            self._narrative_agent = NarrativeStrategistAgent(model="gpt-5.4-mini")
        return self._narrative_agent

    def _storyboard_generator_service(self) -> StoryboardGeneratorService:
        if self._storyboard_service is None:
            self._storyboard_service = StoryboardGeneratorService(model="gpt-image-2")
        return self._storyboard_service

    def _video_generator_service(self) -> VideoGeneratorService:
        if self._video_service is None:
            self._video_service = VideoGeneratorService()
        return self._video_service

    def _simulate_fake_provider(self, stage: str) -> None:
        """Make local asynchronous behaviour observable without provider calls."""

        settings = get_settings()
        if settings.fake_provider_latency_sec:
            time.sleep(settings.fake_provider_latency_sec)
        if settings.fake_provider_failure_stage == stage:
            raise RuntimeError(f"Fake provider configured to fail at {stage}.")

    @staticmethod
    def _require_file(path: str | Path, label: str) -> Path:
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"{label} not found: {file_path}")
        return file_path

    @staticmethod
    def _json_object(value: Any, label: str) -> dict[str, Any]:
        try:
            serialized = json.dumps(value, allow_nan=False)
            decoded = json.loads(serialized)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be JSON serializable.") from exc
        if not isinstance(decoded, dict):
            raise ValueError(f"{label} must be a JSON object.")
        return decoded
