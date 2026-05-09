from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel


ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class LLMClientError(RuntimeError):
    """Raised when the OpenAI-compatible LLM endpoint returns an error."""
    pass


@dataclass
class LLMClient:
    """Chat Completions client that returns parsed Pydantic structured output."""

    model: str
    base_url: str | None = None
    api_key: str | None = None
    timeout: float | None = 120
    extra_headers: dict[str, str] = field(default_factory=dict)
    _client: OpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self._normalize_base_url(self.base_url or os.getenv("LLM_BASE_URL"))
        self.api_key = self.api_key or os.getenv("LLM_API_KEY")

        if not self.api_key or not self.base_url:
            raise ValueError("Both api_key and base_url are required for LLMClient.")

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
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
                raise LLMClientError("LLM endpoint response did not contain choices.")

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
                    "LLM endpoint response did not contain parsed structured output."
                )

            return response_model.model_validate(message.parsed)

        except LLMClientError:
            raise
        except Exception as exc:
            raise LLMClientError(f"LLM client failed: {exc}") from exc

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str | None:
        if base_url is None:
            return None

        normalized = base_url.rstrip("/")
        chat_completions_suffix = "/chat/completions"
        if normalized.endswith(chat_completions_suffix):
            normalized = normalized[: -len(chat_completions_suffix)]
        return normalized
