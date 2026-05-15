from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMClientError(RuntimeError):
    """Raised when the OpenAI API returns an error."""
    pass


@dataclass
class LLMClient:
    """Chat Completions client that returns parsed Pydantic structured output."""

    model: str
    api_key: str | None = None
    timeout: float | None = 120
    extra_headers: dict[str, str] = field(default_factory=dict)
    _client: OpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for LLMClient.")

        self._client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout,
            default_headers=self.extra_headers,
        )

    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: type[ResponseModelT],
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> ResponseModelT:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": response_model,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_completion_tokens"] = max_tokens
        if extra_body is not None:
            payload["extra_body"] = extra_body

        try:
            completion = self._client.chat.completions.parse(**payload)
            if not completion.choices:
                raise LLMClientError("OpenAI response did not contain choices.")

            choice = completion.choices[0]
            finish_reason = choice.finish_reason
            if finish_reason in {"length", "content_filter"}:
                raise LLMClientError(
                    f"LLM structured output did not complete: finish_reason={finish_reason}."
                )

            message = choice.message
            if message.refusal:
                raise LLMClientError(f"LLM refused structured output: {message.refusal}")

            if message.parsed is None:
                raise LLMClientError(
                    "OpenAI response did not contain parsed structured output."
                )

            return response_model.model_validate(message.parsed)

        except LLMClientError:
            raise
        except Exception as exc:
            raise LLMClientError(f"LLM client failed: {exc}") from exc
