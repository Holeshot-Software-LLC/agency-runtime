"""Delegation suggestion and execution event helpers.

The selector can only detect independent work. These helpers make that
suggestion auditable and connect later tool calls to the suggested units.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from agency_runtime.core.store.sqlite import Store


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def work_unit_id_from_text(text: str) -> str:
    """Return a stable ID for a detected work-unit description."""
    digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:10]
    return f"unit-{digest}"


def suggested_delegations(
    store: Store,
    session_id: str,
    *,
    trace_id: str = "",
) -> list[dict[str, Any]]:
    """Return open delegation suggestions for a session."""
    if trace_id:
        return [
            row
            for row in store.get_delegations(trace_id)
            if row.get("status") == "suggested"
        ]
    return store.get_delegations_for_session(session_id, statuses=("suggested",))


def record_suggested_delegations(
    store: Store,
    *,
    session_id: str,
    host: str,
    routing: dict[str, Any],
) -> int:
    """Persist detected independent work units as suggested delegations.

    Repeated pre-LLM hook calls can see the same user message again. Existing
    session/work-unit rows are kept instead of duplicating suggestions.
    """
    work_units = routing.get("work_units") if isinstance(routing.get("work_units"), dict) else {}
    if not work_units.get("delegate") or int(work_units.get("count") or 1) < 2:
        return 0

    selected = routing.get("selected_ids") if isinstance(routing.get("selected_ids"), list) else []
    recommended_agent = _clean(selected[0]) if selected else ""
    trace_id = _clean(routing.get("trace_id")) or str(uuid.uuid4())
    existing = {
        row.get("work_unit_id")
        for row in store.get_delegations(trace_id)
    }
    recorded = 0

    for unit in work_units.get("units") or []:
        description = _clean(unit)
        if not description:
            continue
        work_unit_id = work_unit_id_from_text(description)
        if work_unit_id in existing:
            continue
        store.record_delegation(
            trace_id=trace_id,
            session_id=session_id,
            host=host,
            work_unit_id=work_unit_id,
            recommended_agent=recommended_agent,
            status="suggested",
            backend="",
        )
        existing.add(work_unit_id)
        recorded += 1
    return recorded


def mark_delegation_executed(
    store: Store,
    *,
    session_id: str,
    host: str,
    backend: str,
    agent: str = "",
    goal: str = "",
    work_unit_id: str = "",
    trace_id: str = "",
    count: int = 1,
) -> int:
    """Mark one or more suggested work units as delegated.

    If no suggestion exists, still record the explicit delegation tool use so
    the response header can truthfully report that delegation happened.
    """
    open_rows = suggested_delegations(store, session_id, trace_id=trace_id)
    matched_rows = _matching_suggestions(
        open_rows,
        work_unit_id=work_unit_id,
        agent=agent,
        goal=goal,
        count=count,
    )
    chosen_agent = _clean(agent) or (
        _clean(matched_rows[0].get("recommended_agent")) if matched_rows else ""
    )
    updated = 0

    for row in matched_rows:
        store.update_delegation(
            row["id"],
            status="delegated",
            backend=backend,
            recommended_agent=chosen_agent or _clean(row.get("recommended_agent")),
            host=host,
        )
        updated += 1

    if updated:
        return updated

    store.record_delegation(
        trace_id=_clean(trace_id) or str(uuid.uuid4()),
        session_id=session_id,
        host=host,
        work_unit_id=_clean(work_unit_id) or work_unit_id_from_text(goal or chosen_agent or backend),
        recommended_agent=chosen_agent,
        status="delegated",
        backend=backend,
    )
    return 1


def mark_delegation_skipped(
    store: Store,
    *,
    session_id: str,
    host: str,
    backend: str,
    reason: str,
    agent: str = "",
    goal: str = "",
    work_unit_id: str = "",
    trace_id: str = "",
    count: int = 1,
) -> int:
    """Mark suggested work units as skipped, or record an explicit blocker."""
    open_rows = suggested_delegations(store, session_id, trace_id=trace_id)
    matched_rows = _matching_suggestions(
        open_rows,
        work_unit_id=work_unit_id,
        agent=agent,
        goal=goal,
        count=count,
    )
    chosen_agent = _clean(agent) or (
        _clean(matched_rows[0].get("recommended_agent")) if matched_rows else ""
    )
    skip_reason = _clean(reason) or "delegation failed"
    updated = 0

    for row in matched_rows:
        store.update_delegation(
            row["id"],
            status="skipped",
            backend=backend,
            recommended_agent=chosen_agent or _clean(row.get("recommended_agent")),
            host=host,
            skip_reason=skip_reason,
        )
        updated += 1

    if updated:
        return updated

    store.record_delegation(
        trace_id=_clean(trace_id) or str(uuid.uuid4()),
        session_id=session_id,
        host=host,
        work_unit_id=_clean(work_unit_id) or work_unit_id_from_text(goal or chosen_agent or backend or skip_reason),
        recommended_agent=chosen_agent,
        status="skipped",
        backend=backend,
        skip_reason=skip_reason,
    )
    return 1


def _matching_suggestions(
    rows: list[dict[str, Any]],
    *,
    work_unit_id: str,
    agent: str,
    goal: str,
    count: int,
) -> list[dict[str, Any]]:
    """Return suggestions that can be correlated without relying on row order.

    An explicit work-unit ID is authoritative.  A task description uses the
    same stable ID as preflight detection, and an agent can disambiguate when
    it identifies a unique suggestion.  A sole open suggestion is safe as a
    compatibility fallback; with multiple ambiguous suggestions, the caller
    records a separate explicit event instead of mutating an arbitrary row.
    """
    if not rows:
        return []

    limit = max(1, int(count or 1))
    explicit_id = _clean(work_unit_id)
    if explicit_id:
        return [row for row in rows if _clean(row.get("work_unit_id")) == explicit_id][:limit]

    task = _clean(goal)
    if task:
        task_id = work_unit_id_from_text(task)
        task_matches = [row for row in rows if _clean(row.get("work_unit_id")) == task_id]
        if task_matches:
            return task_matches[:limit]

    chosen_agent = _clean(agent)
    if chosen_agent:
        agent_matches = [
            row for row in rows
            if _clean(row.get("recommended_agent")) == chosen_agent
        ]
        if len(agent_matches) == 1:
            return agent_matches
        if len(agent_matches) > 1 and limit > 1:
            return agent_matches[:limit]

    return rows if len(rows) == 1 else []


__all__ = [
    "mark_delegation_executed",
    "mark_delegation_skipped",
    "record_suggested_delegations",
    "suggested_delegations",
    "work_unit_id_from_text",
]
