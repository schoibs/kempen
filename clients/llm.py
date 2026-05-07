from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import requests

class LLMClientError(RuntimeError):
    """Raised when the OpenAI-compatible LLM endpoint returns an error."""
    pass


@dataclass
class LLMClient:
    """Chat Completions client for OpenAI-compatible endpoints.
    """

    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    timeout: float | None = 120
    extra_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = self.base_url or os.getenv("LLM_BASE_URL")
        self.api_key = self.api_key or os.getenv("LLM_API_KEY")
        self.model = self.model or os.getenv("LLM_MODEL", "gpt-5.4-mini")
        
        if not self.api_key or not self.base_url:
            raise ValueError("Both api_key and base_url are required for LLMClient.")

    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra_body:
            payload.update(extra_body)

        try:
            response = requests.post(
                url=self.base_url,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        
            data = response.json()

            if response.status_code >= 400:
                message = data.get("error", {}).get("message") or response.text[:500]
                raise LLMClientError(f"LLM endpoint returned HTTP {response.status_code}: {message}")

            content = data.get("choices")[0].get("message").get("content")

            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                text_parts = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
                ]
                if text_parts:
                    return "\n".join(text_parts)
            else:
                raise LLMClientError("LLM endpoint response did not contain text content.")

        except Exception as exc:
            raise LLMClientError(f"LLM Client faces error: {exc}") from exc

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers
        }
        return headers
