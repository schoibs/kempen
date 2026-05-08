"""Tools available to campaign agents."""

from .web_fetch import TinyFishFetchError, web_fetch
from .web_search import TinyFishSearchError, tinyfish_web_search

__all__ = [
    "TinyFishFetchError",
    "TinyFishSearchError",
    "tinyfish_web_search",
    "web_fetch",
]
