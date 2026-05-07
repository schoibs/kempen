from __future__ import annotations

import os
from typing import Any

from agents import function_tool


class TinyFishSearchError(RuntimeError):
    """Raised when TinyFish web search cannot be executed."""


@function_tool
def tinyfish_web_search(
    query: str,
    max_results: int = 5,
    location: str = "US",
    language: str = "en",
) -> dict[str, Any]:
    """Search the web for current public information using TinyFish Search API."""
    
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty.")
    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    search_client = _build_tinyfish_client()
    response = search_client.search.query(
        query=normalized_query,
        location=location,
        language=language
    )
    results = [_format_result(item) for item in _get(response, "results", [])]

    return {
        "query": _get(response, "query", normalized_query),
        "results": results[:max_results],
        "total_results": _get(response, "total_results", len(results)),
    }


def _build_tinyfish_client() -> Any:
    if not os.getenv("TINYFISH_API_KEY"):
        raise TinyFishSearchError("TINYFISH_API_KEY is required for TinyFish web search.")

    try:
        from tinyfish import TinyFish
    except ImportError as exc:
        raise TinyFishSearchError(
            "The tinyfish package is required for TinyFish web search."
        ) from exc

    return TinyFish()


def _format_result(item: Any) -> dict[str, Any]:
    return {
        "position": _get(item, "position", None),
        "site_name": _get(item, "site_name", ""),
        "title": _get(item, "title", ""),
        "snippet": _get(item, "snippet", ""),
        "url": _get(item, "url", ""),
    }


def _get(item: Any, key: str, default: Any) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)
