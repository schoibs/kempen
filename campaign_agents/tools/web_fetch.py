from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import urlparse

from agents import function_tool

FetchFormat = Literal["markdown", "html", "json"]

_MAX_URLS = 10
_VALID_FORMATS = {"markdown", "html", "json"}


class TinyFishFetchError(RuntimeError):
    """Raised when TinyFish web fetch cannot be executed."""


@function_tool
def web_fetch(
    urls: list[str],
    format: FetchFormat = "markdown",
    include_links: bool = False,
    include_image_links: bool = False,
    max_chars_per_page: int = 12000,
) -> dict[str, Any]:
    """Fetch clean page content for http/https URLs using TinyFish Fetch API."""

    return _fetch_contents(
        urls=urls,
        format=format,
        include_links=include_links,
        include_image_links=include_image_links,
        max_chars_per_page=max_chars_per_page,
    )


def _fetch_contents(
    *,
    urls: list[str],
    format: FetchFormat = "markdown",
    include_links: bool = False,
    include_image_links: bool = False,
    max_chars_per_page: int = 12000,
) -> dict[str, Any]:
    normalized_urls = _validate_urls(urls)
    _validate_format(format)
    if not isinstance(max_chars_per_page, int) or isinstance(max_chars_per_page, bool):
        raise ValueError("max_chars_per_page must be an integer.")
    if max_chars_per_page < 1:
        raise ValueError("max_chars_per_page must be at least 1.")

    fetch_client = _build_tinyfish_client()
    response = fetch_client.fetch.get_contents(
        urls=normalized_urls,
        format=format,
        links=include_links,
        image_links=include_image_links,
    )

    return {
        "urls": normalized_urls,
        "format": format,
        "results": [
            _format_result(
                item,
                include_links=include_links,
                include_image_links=include_image_links,
                max_chars_per_page=max_chars_per_page,
            )
            for item in _get(response, "results", [])
        ],
        "errors": [_format_error(item) for item in _get(response, "errors", [])],
    }


def _build_tinyfish_client() -> Any:
    if not os.getenv("TINYFISH_API_KEY"):
        raise TinyFishFetchError("TINYFISH_API_KEY is required for TinyFish web fetch.")

    try:
        from tinyfish import TinyFish
    except ImportError as exc:
        raise TinyFishFetchError(
            "The tinyfish package is required for TinyFish web fetch."
        ) from exc

    return TinyFish()


def _validate_urls(urls: list[str]) -> list[str]:
    if not isinstance(urls, list):
        raise ValueError("urls must be a list of URL strings.")
    if not urls:
        raise ValueError("urls must contain at least one URL.")
    if len(urls) > _MAX_URLS:
        raise ValueError(f"urls must contain at most {_MAX_URLS} URLs.")

    normalized_urls = []
    for raw_url in urls:
        if not isinstance(raw_url, str):
            raise ValueError("urls must contain only strings.")

        normalized_url = raw_url.strip()
        if not normalized_url:
            raise ValueError("urls must not include empty URLs.")

        parsed_url = urlparse(normalized_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("urls must use absolute http or https URLs.")

        normalized_urls.append(normalized_url)

    return normalized_urls


def _validate_format(format: str) -> None:
    if format not in _VALID_FORMATS:
        valid_formats = ", ".join(sorted(_VALID_FORMATS))
        raise ValueError(f"format must be one of: {valid_formats}.")


def _format_result(
    item: Any,
    *,
    include_links: bool,
    include_image_links: bool,
    max_chars_per_page: int,
) -> dict[str, Any]:
    text = _get(item, "text", "") or ""
    text_truncated = len(text) > max_chars_per_page
    if text_truncated:
        text = text[:max_chars_per_page]

    result = {
        "url": _get(item, "url", ""),
        "final_url": _get(item, "final_url", None),
        "title": _get(item, "title", ""),
        "description": _get(item, "description", ""),
        "language": _get(item, "language", ""),
        "author": _get(item, "author", ""),
        "published_date": _get(item, "published_date", ""),
        "format": _get(item, "format", ""),
        "latency_ms": _get(item, "latency_ms", None),
        "text": text,
        "text_truncated": text_truncated,
    }

    if include_links:
        result["links"] = _get(item, "links", [])
    if include_image_links:
        result["image_links"] = _get(item, "image_links", [])

    return result


def _format_error(item: Any) -> dict[str, Any]:
    return {
        "url": _get(item, "url", ""),
        "error": _get(item, "error", ""),
    }


def _get(item: Any, key: str, default: Any) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)
