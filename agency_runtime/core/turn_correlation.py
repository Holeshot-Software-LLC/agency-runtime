"""Fail-closed validation for public turn-evidence mutation boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agency_runtime.core.correlation import validate_correlation_id

_PUBLIC_EVIDENCE_STATES = frozenset({"ready"})


def active_turn_error(store: Any, session_id: str, trace_id: str) -> str:
    """Return an error unless ``trace_id`` names this session's active turn.

    Native host callbacks may intentionally let the Store create a bounded
    evidence-only parent when a host delivers an observation before its prompt
    hook. Public mutation surfaces must not have that authority: callers first
    establish a turn through preflight, then attach evidence to that exact run.
    """

    try:
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    except ValueError as exc:
        return str(exc)

    getter = getattr(store, "get_run", None)
    if not callable(getter):
        return "active turn correlation could not be verified"
    try:
        run = getter(normalized_trace)
    except Exception:
        return "active turn correlation could not be verified"
    if not isinstance(run, Mapping):
        return "trace_id does not identify an existing active turn"
    if str(run.get("session_id") or "").strip() != normalized_session:
        return "trace_id already belongs to a different session"
    status = str(run.get("status") or "").strip()
    if status != "active" or run.get("ended_at") is not None:
        if status == "evidence_only" and run.get("ended_at") is None:
            return "trace_id has not completed preflight"
        return "trace_id belongs to a terminal turn"
    if str(run.get("preflight_state") or "").strip() not in _PUBLIC_EVIDENCE_STATES:
        return "trace_id has not completed preflight"
    return ""


__all__ = ["active_turn_error"]
