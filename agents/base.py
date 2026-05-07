from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

from clients import LLMClient


class AgentRunError(RuntimeError):
    """Raised when an agent cannot produce usable structured output."""


class BaseAgent(ABC):
    """Base class for agents that return JSON through an OpenAI-compatible API."""

    name = "base_agent"
    schema_name = "base_agent_output"
    output_schema: dict[str, Any] = {}
    system_prompt = ""
    default_temperature = 0.3

    def __init__(
        self,
        client: LLMClient | None = None,
        response_format_mode: str | None = "json_schema",
    ) -> None:
        self.client = client
        self.response_format_mode = response_format_mode.strip()

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent and return parsed JSON."""

    def _call_json(
        self,
        user_content: str | list[dict[str, Any]],
        extra_messages: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
        ]
        if extra_messages:
            messages.extend(extra_messages)
        messages.append({"role": "user", "content": user_content})

        content = self.client.chat(
            messages=messages,
            response_format=self._response_format(),
            temperature=self.default_temperature if temperature is None else temperature,
            max_tokens=max_tokens,
        )
        return self._parse_json(content)

    def _response_format(self) -> dict[str, Any] | None:
        if self.response_format_mode in {"", "none", "off", "disabled"}:
            return None
        if self.response_format_mode == "json_object":
            return {"type": "json_object"}
        if self.response_format_mode == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": self.schema_name,
                    "strict": True,
                    "schema": self.output_schema,
                },
            }
        raise ValueError(
            "OPENAI_RESPONSE_FORMAT must be one of: json_schema, json_object, none"
        )

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = BaseAgent._parse_json_from_loose_content(content)

        if not isinstance(parsed, dict):
            raise AgentRunError("Agent response must be a JSON object.")
        return parsed

    @staticmethod
    def _parse_json_from_loose_content(content: str) -> Any:
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except json.JSONDecodeError:
                pass

        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError as exc:
                raise AgentRunError(
                    "Agent returned text that looked like JSON but could not be parsed."
                ) from exc

        raise AgentRunError("Agent did not return parseable JSON.")
