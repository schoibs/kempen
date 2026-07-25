from __future__ import annotations

import secrets
import time


def new_resource_id(prefix: str) -> str:
    """Return an opaque identifier whose lexical order starts with creation time."""

    return f"{prefix}_{int(time.time() * 1000):012x}{secrets.token_hex(10)}"
