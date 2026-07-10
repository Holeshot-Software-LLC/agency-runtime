"""Session-based routing stickiness — reuse recent selections within a session."""

from __future__ import annotations

import time
from typing import Any

from agency_runtime.core.selector.candidate_narrow import tokenize

_SESSION_STICKY_THRESHOLD = float(0.6)
_SESSION_STICKY_MAX_AGE = float(300)

_SESSION_ROUTING: dict[str, dict[str, Any]] = {}


def session_check(
    session_id: str,
    query: str,
    threshold: float = _SESSION_STICKY_THRESHOLD,
    max_age: float = _SESSION_STICKY_MAX_AGE,
) -> dict[str, Any] | None:
    if not session_id:
        return None
    entry = _SESSION_ROUTING.get(session_id)
    if not entry:
        return None
    age = time.monotonic() - entry["_ts"]
    if age > max_age:
        del _SESSION_ROUTING[session_id]
        return None
    prev_tokens = entry["_tokens"]
    curr_tokens = tokenize(query)
    if not prev_tokens or not curr_tokens:
        return None
    overlap = len(prev_tokens & curr_tokens)
    union = len(prev_tokens | curr_tokens)
    if union == 0:
        return None
    jaccard = overlap / union
    if jaccard >= threshold:
        result = {k: v for k, v in entry.items() if not k.startswith("_")}
        result["session_reused"] = True
        return result
    return None


def session_put(session_id: str, query: str, routing: dict[str, Any]) -> None:
    if not session_id:
        return
    _SESSION_ROUTING[session_id] = {
        **routing,
        "_ts": time.monotonic(),
        "_tokens": tokenize(query),
    }


def clear_session_routing() -> None:
    _SESSION_ROUTING.clear()
