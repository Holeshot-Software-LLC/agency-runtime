"""Session-based routing stickiness — reuse recent selections within a session."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from copy import deepcopy
from typing import Any

from agency_runtime.core.selector.candidate_narrow import tokenize

_SESSION_STICKY_THRESHOLD = 0.6
_SESSION_STICKY_MAX_AGE = float(300)
_SESSION_MAX_ENTRIES = 128

_SESSION_ROUTING: OrderedDict[str, dict[str, Any]] = OrderedDict()
_SESSION_LOCK = threading.RLock()


def session_check(
    session_id: str,
    query: str,
    threshold: float = _SESSION_STICKY_THRESHOLD,
    max_age: float = _SESSION_STICKY_MAX_AGE,
    *,
    context_fingerprint: str = "",
    valid_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    if not session_id:
        return None
    with _SESSION_LOCK:
        entry = _SESSION_ROUTING.get(session_id)
        if not entry:
            return None
        age = time.monotonic() - entry["_ts"]
        if age > max_age:
            del _SESSION_ROUTING[session_id]
            return None
        if context_fingerprint and entry.get("_context_fingerprint", "") != context_fingerprint:
            return None
        prev_tokens = entry["_tokens"]
        curr_tokens = tokenize(query)
        if not prev_tokens or not curr_tokens:
            return None
        overlap = len(prev_tokens & curr_tokens)
        union = len(prev_tokens | curr_tokens)
        jaccard = overlap / union
        if jaccard >= threshold:
            _SESSION_ROUTING.move_to_end(session_id)
            result = deepcopy({k: v for k, v in entry.items() if not k.startswith("_")})
            if valid_ids is not None:
                result["selected_ids"] = [
                    slug for slug in result.get("selected_ids", []) if str(slug) in valid_ids
                ]
            result["session_reused"] = True
            return result
    return None


def session_put(
    session_id: str,
    query: str,
    routing: dict[str, Any],
    *,
    context_fingerprint: str = "",
    max_entries: int = _SESSION_MAX_ENTRIES,
) -> None:
    if not session_id:
        return
    with _SESSION_LOCK:
        _SESSION_ROUTING[session_id] = {
            **deepcopy(routing),
            "_ts": time.monotonic(),
            "_tokens": tokenize(query),
            "_context_fingerprint": context_fingerprint,
        }
        _SESSION_ROUTING.move_to_end(session_id)
        while len(_SESSION_ROUTING) > max(0, max_entries):
            _SESSION_ROUTING.popitem(last=False)


def clear_session_routing() -> None:
    with _SESSION_LOCK:
        _SESSION_ROUTING.clear()
