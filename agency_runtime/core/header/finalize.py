"""Finalization gate for Agency Runtime responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from .contract import (
    HEADER_FIELDS,
    fill_header_fields,
    format_header,
    parse_header,
    validate_header,
)


class FinalizationResult(TypedDict):
    action: str
    text: str
    missing: list[str]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _metadata_value(metadata: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return _clean(value)
    return default


def _starts_with_header(text: str) -> bool:
    lines = text.splitlines()
    return len(lines) >= len(HEADER_FIELDS) and all(
        lines[index].startswith(f"{label}:") for index, (_key, label) in enumerate(HEADER_FIELDS)
    )


def _body_after_possible_header(text: str) -> str:
    if not _starts_with_header(text):
        return text.strip()
    return "\n".join(text.splitlines()[6:]).strip()


def finalize_response(
    draft_text: str,
    trace_metadata: Mapping[str, Any] | None = None,
    store: Any | None = None,
    model: str = "",
) -> FinalizationResult:
    """Apply the Agency header finalization gate.

    Returns ``action='accept'`` when the response is finalizable, ``rewrite``
    when any of the six required header fields remain missing after attempted
    auto-fill, and ``continue`` when there is no substantive draft body yet.
    """
    metadata = dict(trace_metadata or {})
    session_id = _metadata_value(metadata, "session_id", "session", default="")
    trace_id = _metadata_value(metadata, "trace_id", "trace", default="")
    host = _metadata_value(metadata, "host", "runtime", default="unknown") or "unknown"
    requested_model = model or _metadata_value(metadata, "requested_model", "model", default="")

    if not _clean(draft_text):
        result: FinalizationResult = {
            "action": "continue",
            "text": draft_text,
            "missing": ["draft_text"],
        }
        _record_finalization(store, trace_id, host, result["action"], result["missing"])
        return result

    parsed = parse_header(draft_text) if _starts_with_header(draft_text) else {}
    has_header = bool(parsed)
    body = _body_after_possible_header(draft_text)
    fields = fill_header_fields(parsed, session_id, store, requested_model)
    header = format_header(fields)
    text = f"{header}\n\n{body}" if body else header

    valid, missing = validate_header(text)
    action = "accept" if valid else "rewrite"
    if not body:
        action = "continue"
        missing = missing or ["response_body"]
    elif not has_header:
        # Missing header was fully auto-filled.  The returned text is the
        # rewrite the caller should emit, but no fields remain missing.
        action = "accept" if valid else "rewrite"

    result = {"action": action, "text": text, "missing": missing}
    _record_finalization(store, trace_id, host, action, missing)
    return result


def finalize(
    draft_text: str,
    trace_metadata: Mapping[str, Any] | None = None,
    store: Any | None = None,
    model: str = "",
) -> FinalizationResult:
    """Backward-compatible short alias for ``finalize_response``."""
    return finalize_response(draft_text, trace_metadata=trace_metadata, store=store, model=model)


def _record_finalization(
    store: Any, trace_id: str, host: str, action: str, missing: list[str]
) -> None:
    recorder = getattr(store, "record_finalization", None)
    if not callable(recorder) or not trace_id:
        return
    try:
        recorder(trace_id=trace_id, host=host, action=action, missing=missing)
    except Exception:
        # Finalization should not fail the user response because event logging is
        # unavailable.  The action/text result remains authoritative.
        return


__all__ = ["FinalizationResult", "finalize", "finalize_response"]
