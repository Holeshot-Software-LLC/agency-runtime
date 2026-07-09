"""Compatibility shim for wiring live Hermes plugin and LiteLLM callback
into the portable agency_runtime package.

This module provides the function signatures that the live system expects
(record_model_route, record_skill_loaded, ensure_agency_header_fields, etc.)
backed by the portable Store and header contract implementations.

Usage in live files:
    try:
        from agency_runtime.adapters.hermes.compat import (
            record_model_route, record_skill_loaded, record_specialist_loaded,
            ensure_agency_header_fields, query_recent_litellm_route,
        )
    except ImportError:
        # Fall back to existing live implementations
        ...
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.header.contract import (
    fill_header_fields,
    format_header,
    _starts_with_header,
    _split_header_body,
    validate_header,
)

logger = logging.getLogger("agency_runtime.compat")

# Singleton store — matches the live system's pattern
_store: Store | None = None


def _get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store


def record_model_route(
    session_id: str,
    *,
    requested_model: str = "",
    actual_model: str = "",
    model_group: str = "",
    provider: str = "",
    model_id: str = "",
    api_base: str = "",
    attempted_fallbacks: int = 0,
) -> None:
    """Record a model routing decision into the portable Store.

    Replaces the live agency_preflight.record_model_route which writes to
    a legacy SQLite DB. This writes to the canonical agency_runtime DB.
    """
    store = _get_store()
    # Split provider/model from the actual model string
    resolved_provider = provider
    resolved_model = actual_model
    if not resolved_provider and "/" in actual_model:
        parts = actual_model.split("/", 1)
        resolved_provider = parts[0]
        resolved_model = parts[1]

    store.record_model_receipt(
        trace_id=str(uuid.uuid4()),
        session_id=session_id,
        host="hermes",
        requested_model=requested_model,
        model_group=model_group or requested_model,
        resolved_provider=resolved_provider,
        resolved_model=resolved_model,
        api_base=api_base,
        attempted_fallbacks=int(attempted_fallbacks or 0),
        model_id=model_id,
        source="host",
        status="success" if resolved_model else "unknown",
    )


def record_skill_loaded(session_id: str, skill_name: str) -> None:
    """Record a skill load into the portable Store."""
    store = _get_store()
    store.record_skill_loaded(session_id, skill_name)


def record_specialist_loaded(session_id: str, agent_slug: str) -> None:
    """Record a specialist load into the portable Store."""
    store = _get_store()
    store.record_specialist_loaded(session_id, agent_slug)


def ensure_agency_header_fields(
    response_text: str,
    *,
    session_id: str = "",
    model: str = "",
) -> str:
    """Ensure response_text has a complete Agency header.

    Drop-in replacement for agency_preflight.ensure_agency_header_fields.
    Uses the portable header contract's fill_header_fields + format_header.
    """
    store = _get_store()
    valid, _ = validate_header(response_text)
    has_header = _starts_with_header(response_text)
    _, body = _split_header_body(response_text) if has_header else ([], response_text.lstrip("\n"))
    if not has_header and not valid:
        body = response_text.lstrip("\n")
    fields = fill_header_fields({}, session_id, store, model)
    header = format_header(fields)
    return f"{header}\n\n{body}" if body else header


def query_recent_litellm_route(
    *,
    requested_model: str = "",
    started_at: float | None = None,
    ended_at: float | None = None,
) -> dict[str, Any]:
    """No-op stub — the portable package does NOT query SpendLogs.

    The live plugin's post_api_request handler calls this, but the portable
    package reads the model from response["model"] directly. This stub exists
    so the import doesn't break. It returns empty, which causes the caller to
    fall back to response data — which is exactly what we want.
    """
    return {}


# ─── Post-tool-call handler (specialist + skill tracking) ──────────────


def on_post_tool_call(**kwargs: Any) -> None:
    """Record skills and specialists loaded via tool calls.

    Replaces the live _on_post_tool_call which only tracked skill_view.
    """
    tool_name = kwargs.get("tool_name") or ""
    args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
    session_id = kwargs.get("session_id") or ""

    if tool_name == "skill_view":
        skill_name = args.get("name") or ""
        if skill_name:
            record_skill_loaded(session_id, skill_name)

    elif tool_name in ("agency_agents_load", "agency_agents_inspect"):
        agent = args.get("agent") or args.get("slug") or ""
        if agent:
            record_specialist_loaded(session_id, agent)

    elif tool_name in ("agency_agents_delegate", "delegate_task"):
        agent = args.get("agent") or args.get("slug") or ""
        if agent:
            record_specialist_loaded(session_id, agent)


# ─── Post-API-request handler (model receipt from response) ────────────


def on_post_api_request(**kwargs: Any) -> None:
    """Capture model receipt from the actual API response.

    Replaces the live _on_post_api_request which queried SpendLogs.
    Reads response["model"] directly — no SpendLog dependency.
    """
    response = kwargs.get("response") if isinstance(kwargs.get("response"), dict) else {}
    requested_model = kwargs.get("model") or ""
    session_id = kwargs.get("session_id") or ""

    # The resolved model is in the response body
    resolved_model = str(
        kwargs.get("response_model")
        or response.get("model")
        or ""
    ).strip()

    if not resolved_model:
        return

    record_model_route(
        session_id,
        requested_model=requested_model,
        actual_model=resolved_model,
        model_group=requested_model,
    )


__all__ = [
    "record_model_route",
    "record_skill_loaded",
    "record_specialist_loaded",
    "ensure_agency_header_fields",
    "query_recent_litellm_route",
    "on_post_tool_call",
    "on_post_api_request",
]
