"""LRU cache with TTL for routing decisions.

Ported from ~/.litellm/agency_preflight.py.
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import OrderedDict
from typing import Any

_CACHE_TTL_SECONDS = float(600)
_CACHE_MAX_ENTRIES = int(128)

_ROUTING_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()


def cache_key(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def cache_get(key: str, ttl: float = _CACHE_TTL_SECONDS) -> dict[str, Any] | None:
    if key not in _ROUTING_CACHE:
        return None
    entry = _ROUTING_CACHE[key]
    age = time.monotonic() - entry["_ts"]
    if age > ttl:
        del _ROUTING_CACHE[key]
        return None
    _ROUTING_CACHE.move_to_end(key)
    result = {k: v for k, v in entry.items() if not k.startswith("_")}
    result["cache_hit"] = True
    return result


def cache_put(key: str, value: dict[str, Any], max_entries: int = _CACHE_MAX_ENTRIES) -> None:
    _ROUTING_CACHE[key] = {**value, "_ts": time.monotonic()}
    _ROUTING_CACHE.move_to_end(key)
    while len(_ROUTING_CACHE) > max_entries:
        _ROUTING_CACHE.popitem(last=False)


def clear_cache() -> None:
    _ROUTING_CACHE.clear()
