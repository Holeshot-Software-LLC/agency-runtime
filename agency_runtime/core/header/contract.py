"""Agency response header contract.

Every finalized Agency Runtime answer begins with six auditable lines that make
specialist use, delegation, skill context, and actual model selection explicit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

HEADER_FIELDS: tuple[tuple[str, str], ...] = (
    ("agencies_loaded", "Agency/Agencies loaded"),
    ("agencies_delegated", "Agency/Agencies delegated"),
    ("skills_loaded", "Skills loaded"),
    ("actual_model_selected", "Actual Model selected"),
    ("why", "Why"),
    ("how_it_shaped_outcome", "How it shaped outcome"),
)

_REQUIRED_KEYS = tuple(key for key, _ in HEADER_FIELDS)
_LABEL_TO_KEY = {label.lower(): key for key, label in HEADER_FIELDS}
_KEY_TO_LABEL = dict(HEADER_FIELDS)

_EMPTY_VALUES = {
    "",
    "<none>",
    "<none | agent-id[, agent-id...]>",
    "<none | skill-id[, skill-id...]>",
    "<one line>",
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    # Header values are intentionally one line.  Preserve words, remove line
    # breaks that would violate the six-line contract.
    return " ".join(text.splitlines()).strip()


def _is_present(value: Any) -> bool:
    text = _clean(value)
    return bool(text) and text.lower() not in _EMPTY_VALUES


def _starts_with_header(response_text: str) -> bool:
    lines = response_text.splitlines()
    return len(lines) >= len(HEADER_FIELDS) and all(
        lines[index].startswith(f"{label}:") for index, (_key, label) in enumerate(HEADER_FIELDS)
    )


def _split_header_body(response_text: str) -> tuple[list[str], str]:
    lines = response_text.splitlines()
    header_lines = lines[: len(HEADER_FIELDS)]
    body = (
        "\n".join(lines[len(HEADER_FIELDS) :]).lstrip("\n")
        if len(lines) > len(HEADER_FIELDS)
        else ""
    )
    return header_lines, body


def parse_header(response_text: str) -> dict[str, str]:
    """Parse the six-line Agency header from the beginning of response_text.

    Missing or malformed lines are omitted from the returned mapping.
    """
    parsed: dict[str, str] = {}
    for line in response_text.splitlines()[: len(HEADER_FIELDS)]:
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        key = _LABEL_TO_KEY.get(label.strip().lower())
        if key:
            parsed[key] = value.strip()
    return parsed


def format_header(fields: Mapping[str, Any]) -> str:
    """Format fields as the exact six-line Agency header."""
    return "\n".join(f"{label}: {_clean(fields.get(key, ''))}" for key, label in HEADER_FIELDS)


def validate_header(response_text: str) -> tuple[bool, list[str]]:
    """Validate that response_text starts with all six non-empty header fields."""
    lines = response_text.splitlines()
    missing: list[str] = []
    if len(lines) < len(HEADER_FIELDS):
        # Continue checking available lines so callers get specific diagnostics.
        pass

    parsed = parse_header(response_text)
    for index, (key, label) in enumerate(HEADER_FIELDS):
        if index >= len(lines):
            missing.append(key)
            continue
        line = lines[index]
        expected_prefix = f"{label}:"
        if not line.startswith(expected_prefix):
            missing.append(key)
            continue
        if not _is_present(parsed.get(key, "")):
            missing.append(key)
    return (not missing, missing)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _get_loaded_specialists(store: Any, session_id: str) -> list[str]:
    if not store or not session_id:
        return []
    getter = getattr(store, "get_specialists_for_session", None)
    if callable(getter):
        try:
            return _dedupe(list(getter(session_id)))
        except Exception:
            return []
    connect = getattr(store, "_connect", None)
    if not callable(connect):
        return []
    try:
        conn = connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return _dedupe(
                [row["agent_slug"] if hasattr(row, "keys") else row[0] for row in cur.fetchall()]
            )
        finally:
            conn.close()
    except Exception:
        return []


def _get_delegations(store: Any, session_id: str) -> list[dict[str, Any]]:
    if not store or not session_id:
        return []
    connect = getattr(store, "_connect", None)
    if not callable(connect):
        return []
    try:
        conn = connect()
        try:
            cur = conn.execute(
                "SELECT recommended_agent, backend, status, skip_reason, error "
                "FROM delegation_events WHERE session_id = ? ORDER BY started_at",
                (session_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
    except Exception:
        return []


def _get_skills(store: Any, session_id: str) -> list[str]:
    if not store or not session_id:
        return []
    getter = getattr(store, "get_skills_for_session", None)
    if not callable(getter):
        return []
    try:
        return _dedupe(list(getter(session_id)))
    except Exception:
        return []


def _latest_model_receipt(store: Any, session_id: str) -> dict[str, Any] | None:
    if not store or not session_id:
        return None
    connect = getattr(store, "_connect", None)
    if not callable(connect):
        return None
    try:
        conn = connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE session_id = ? ORDER BY ended_at DESC, started_at DESC, id DESC LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    except Exception:
        return None


_MODEL_GROUP_COMPLEXITY: dict[str, str] = {
    "task-chunk-planner": "planner",
    "task-general": "general",
    "task-implementation": "implementation",
    "task-agency-router": "router",
}


def _complexity_for_model_group(model_group: str) -> str:
    """Return a human-readable complexity tier for a LiteLLM model group."""
    return _MODEL_GROUP_COMPLEXITY.get(_clean(model_group), "")


def _model_line(receipt: Mapping[str, Any] | None, requested_model: str) -> str:
    requested = (
        _clean((receipt or {}).get("requested_model")) or _clean(requested_model) or "unknown"
    )
    tier = _complexity_for_model_group(requested)
    tier_prefix = f"[{tier}] " if tier else ""
    if not receipt:
        return f"{tier_prefix}{requested} -> unavailable - no model receipt recorded"

    resolved_model = _clean(receipt.get("resolved_model"))
    resolved_provider = _clean(receipt.get("resolved_provider"))
    source = _clean(receipt.get("source")) or "unknown"
    status = _clean(receipt.get("status"))
    model_group = _clean(receipt.get("model_group"))

    if not resolved_model or resolved_model == "unavailable":
        reason = (
            status
            if status and status not in {"success", "unknown"}
            else "unavailable - no resolved model telemetry"
        )
        return f"{tier_prefix}{requested} -> {reason}"

    target = f"{resolved_provider}/{resolved_model}" if resolved_provider else resolved_model
    if model_group and model_group != resolved_model:
        target = f"{target} via {model_group}"
    target = f"{target} ({source})"
    return f"{tier_prefix}{requested} -> {target}"


def _delegation_line(delegations: list[dict[str, Any]]) -> str:
    if not delegations:
        return "none"
    completed: list[str] = []
    reasons: list[str] = []
    for event in delegations:
        agent = _clean(event.get("recommended_agent"))
        backend = _clean(event.get("backend"))
        status = _clean(event.get("status"))
        skip_reason = _clean(event.get("skip_reason")) or _clean(event.get("error"))
        if agent and status in {"completed", "running", "started", "delegated"}:
            completed.append(f"{agent} via {backend or 'unknown backend'}")
        elif skip_reason:
            reasons.append(skip_reason)
    if completed:
        return ", ".join(_dedupe(completed))
    if reasons:
        return f"none - {_dedupe(reasons)[0]}"
    return "none - delegation suggested but not executed"


def fill_header_fields(
    fields: Mapping[str, Any] | None, session_id: str, store: Any, model: str = ""
) -> dict[str, str]:
    """Reconcile header fields with authoritative store/session evidence.

    Specialist, delegation, and model claims are evidence fields: authored
    values never outrank runtime records.  The remaining explanatory fields
    retain authored content and receive safe defaults only when absent.
    """
    filled = {key: _clean((fields or {}).get(key, "")) for key in _REQUIRED_KEYS}

    agents = _get_loaded_specialists(store, session_id)
    filled["agencies_loaded"] = ", ".join(agents) if agents else "none"

    delegations = _get_delegations(store, session_id)
    filled["agencies_delegated"] = _delegation_line(delegations)

    skills = _get_skills(store, session_id)
    filled["skills_loaded"] = ", ".join(skills) if skills else "none"

    filled["actual_model_selected"] = _model_line(_latest_model_receipt(store, session_id), model)

    if not _is_present(filled["why"]):
        filled["why"] = "Required for Agency Runtime auditability."

    if not _is_present(filled["how_it_shaped_outcome"]):
        filled["how_it_shaped_outcome"] = (
            "Made runtime context explicit without changing the substantive answer."
        )

    return filled


def finalize_header(response_text: str, session_id: str, store: Any, model: str) -> str:
    """Ensure response_text starts with a complete Agency header.

    Evidence fields are overwritten from the SQLite Store.  Explanatory fields
    are preserved when present and otherwise receive honest defaults.
    """
    valid, _ = validate_header(response_text)
    has_header = _starts_with_header(response_text)
    existing = parse_header(response_text) if has_header else {}
    _, body = _split_header_body(response_text) if has_header else ([], response_text.lstrip("\n"))
    if not has_header and not valid:
        body = response_text.lstrip("\n")
    fields = fill_header_fields(existing, session_id, store, model)
    header = format_header(fields)
    return f"{header}\n\n{body}" if body else header


__all__ = [
    "HEADER_FIELDS",
    "fill_header_fields",
    "finalize_header",
    "format_header",
    "parse_header",
    "validate_header",
]
