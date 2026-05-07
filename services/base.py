from __future__ import annotations

import json
from typing import Any

from clients import LLMClient
from pydantic import BaseModel, ValidationError


class ServiceRunError(RuntimeError):
    """Raised when a prompt service cannot produce usable structured output."""


class BasePromptService:
    """Shared structured-output wrapper for LLM-backed prompt services."""

    output_type: type[BaseModel] | None = None
    response_schema_name = "prompt_service_output"
    system_prompt = ""
    default_temperature = 0.3
    default_max_tokens = 4000

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        if self.output_type is None:
            raise TypeError(f"{type(self).__name__} must define output_type.")

        self.llm_client = llm_client
        self.temperature = self.default_temperature if temperature is None else temperature
        self.max_tokens = max_tokens or self.default_max_tokens

    def _run_structured_model(self, user_payload: dict[str, Any]) -> BaseModel:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    "Create structured JSON for this brief. Return only JSON, "
                    "with no markdown or prose.\n"
                    f"{json.dumps(user_payload, indent=2)}"
                ),
            },
        ]

        try:
            response_text = self.llm_client.chat(
                messages=messages,
                response_format=self._response_format(),
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            raise ServiceRunError(f"LLM prompt service call failed: {exc}") from exc

        data = self._load_json(response_text)

        try:
            return self.output_type.model_validate(data)
        except ValidationError as exc:
            raise ServiceRunError(f"LLM response failed schema validation: {exc}") from exc

    def _run_structured(self, user_payload: dict[str, Any]) -> dict[str, Any]:
        return self._run_structured_model(user_payload).model_dump(mode="json", by_alias=True)

    def _response_format(self) -> dict[str, Any]:
        if self.output_type is None:
            raise TypeError(f"{type(self).__name__} must define output_type.")

        return {
            "type": "json_schema",
            "json_schema": {
                "name": self.response_schema_name,
                "schema": self.output_type.model_json_schema(),
                "strict": True,
            },
        }

    @staticmethod
    def _load_json(response_text: str) -> Any:
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = BasePromptService._strip_markdown_fence(cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or start >= end:
                raise ServiceRunError("LLM response was not valid JSON.")

            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise ServiceRunError("LLM response was not valid JSON.") from exc

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        lines = text.splitlines()
        if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
        return text
