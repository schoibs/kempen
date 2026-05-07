"""Tools available to campaign agents."""

from .web_search import TinyFishSearchError, search_web, tinyfish_web_search

__all__ = [
    "TinyFishSearchError",
    "search_web",
    "tinyfish_web_search",
]
