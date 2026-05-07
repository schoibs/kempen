from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

from agents import Agent as OpenAIAgent
from agents import ModelSettings, OpenAIProvider, RunConfig, Runner
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class AgentRunError(RuntimeError):
    """Raised when an agent cannot produce usable structured output."""


class BaseAgent(ABC):
    """Base class for campaign agents backed by the OpenAI Agents SDK."""

    name = "base_agent"
    output_type: type[BaseModel] | None = None
    system_prompt = ""
    tools: list[Any] | None = None
    default_temperature = 0.3
    default_max_turns = 4

    def __init__(
        self,
        model: str,
        max_turns: int | None = None,
    ) -> None:
        if self.output_type is None:
            raise TypeError(f"{type(self).__name__} must define output_type.")

        self.model = model
        self.max_turns = max_turns or self.default_max_turns
        self.sdk_agent = self._build_sdk_agent()

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent and return a JSON-like dict."""

    def _build_sdk_agent(self) -> OpenAIAgent:
        agent_kwargs: dict[str, Any] = {
            "name": self.name,
            "instructions": self.system_prompt,
            "tools": self.tools or [],
            "output_type": self.output_type,
            "model": self.model,
            "model_settings": ModelSettings(temperature=self.default_temperature),
        }
        return OpenAIAgent(**agent_kwargs)

    def _run_sdk(
        self,
        user_input: str | list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = Runner.run_sync(
            self.sdk_agent,
            user_input,
            max_turns=self.max_turns,
        )
        final_output = self._final_output_to_dict(result.final_output)
        return final_output

    @staticmethod
    def _final_output_to_dict(final_output: Any) -> dict[str, Any]:
        if isinstance(final_output, BaseModel):
            return final_output.model_dump(mode="json", by_alias=True)
        if isinstance(final_output, dict):
            return final_output
        raise AgentRunError(
            f"Agent final output must be a Pydantic model or dict, got {type(final_output).__name__}."
        )
