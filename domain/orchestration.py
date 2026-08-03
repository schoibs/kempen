from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from campaign_agents import NarrativeStrategistAgent, ProductAnalysisAgent
from services import StoryboardGeneratorService, VideoGeneratorService

from .campaigns import CampaignInput


class CampaignStageOperations:
    """Explicit, JSON-serializable operations for the fixed campaign pipeline."""

    def __init__(
        self,
        *,
        product_agent: ProductAnalysisAgent | None = None,
        narrative_agent: NarrativeStrategistAgent | None = None,
        storyboard_service: StoryboardGeneratorService | None = None,
        video_service: VideoGeneratorService | None = None,
    ) -> None:
        self._product_agent = product_agent
        self._narrative_agent = narrative_agent
        self._storyboard_service = storyboard_service
        self._video_service = video_service

    def analyze_product(self, *, product_image_path: str | Path) -> dict[str, Any]:
        image_path = self._require_file(product_image_path, "Product image")
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
