"""Delegation suggestion and execution event helpers.

The selector can only detect independent work. These helpers make that
suggestion auditable and connect later tool calls to the suggested units.
"""

from __future__ import annotations

from typing import Any

from agency_runtime.core.resident_managers import is_resident_manager_slug
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import (
    MAX_AGENT_SLUG_CHARS,
    MAX_SUGGESTED_WORK_UNITS,
    MAX_WORK_UNIT_CHARS,
    UNIT_AGENT_ASSIGNMENT_VERSION,
    build_unit_agent_plan,
    work_unit_id_from_text,
)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def suggested_delegations(
    store: Store,
    session_id: str,
    *,
    trace_id: str = "",
) -> list[dict[str, Any]]:
    """Return open suggestions for exactly one correlated turn."""
    if not session_id or not trace_id:
        return []
    result: list[dict[str, Any]] = []
    for row in store.get_delegations(trace_id):
        if row.get("status") == "suggested" and _clean(row.get("session_id")) == session_id:
            result.append(row)
            if len(result) >= MAX_SUGGESTED_WORK_UNITS:
                break
    return result


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
    normalized_session = _clean(session_id)
    if not normalized_session:
        return 0
    work_units = routing.get("work_units") if isinstance(routing.get("work_units"), dict) else {}
    try:
        work_unit_count = int(work_units.get("count") or 1)
    except (TypeError, ValueError, OverflowError):
        return 0
    if not work_units.get("delegate") or work_unit_count < 2:
        return 0

    trace_id = _clean(routing.get("trace_id"))
    if not trace_id:
        return 0
    suggestions = build_unit_agent_plan(routing)

    if not suggestions:
        return 0

    batch_recorder = getattr(store, "record_suggested_delegations_batch", None)
    if callable(batch_recorder):
        recorded = int(
            batch_recorder(
                trace_id=trace_id,
                session_id=normalized_session,
                host=host,
                suggestions=suggestions,
            )
        )
        return max(0, min(recorded, len(suggestions)))

    # Compatibility stores remain strictly bounded. Production Store exposes
    # the transactional batch API above.
    existing = {row.get("work_unit_id") for row in store.get_delegations(trace_id)}
    recorded = 0
    for suggestion in suggestions:
        if suggestion["work_unit_id"] in existing:
            continue
        store.record_delegation(
            trace_id=trace_id,
            session_id=normalized_session,
            host=host,
            work_unit_id=suggestion["work_unit_id"],
            recommended_agent=suggestion["recommended_agent"],
            status="suggested",
            backend="",
        )
        existing.add(suggestion["work_unit_id"])
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
    executed_worker_kind: str = "",
    executed_worker_id: str = "",
    native_run_id: str = "",
) -> int:
    """Mark one or more suggested work units as delegated.

    If no suggestion exists, still record the explicit delegation tool use so
    the response header can truthfully report that delegation happened.
    """
    session_id = _clean(session_id)
    trace_id = _clean(trace_id)
    if not session_id or not trace_id:
        return 0
    missing = [
        name
        for name, value in (
            ("backend", backend),
            ("executed_worker_kind", executed_worker_kind),
            ("executed_worker_id", executed_worker_id),
            ("native_run_id", native_run_id),
        )
        if not _clean(value)
    ]
    if missing:
        return mark_delegation_skipped(
            store,
            session_id=session_id,
            host=host,
            backend=backend,
            agent=agent,
            goal=goal,
            work_unit_id=work_unit_id,
            trace_id=trace_id,
            count=count,
            executed_worker_kind=executed_worker_kind,
            executed_worker_id=executed_worker_id,
            native_run_id=native_run_id,
            reason=("delegation execution correlation incomplete: missing " + ", ".join(missing)),
        )
    all_rows = [
        row
        for row in store.get_delegations(trace_id)
        if _clean(row.get("session_id")) == session_id
    ]
    open_rows = [row for row in all_rows if row.get("status") == "suggested"]
    matched_rows = _matching_work_unit_identity(
        all_rows,
        work_unit_id=work_unit_id,
        goal=goal,
        count=count,
    )
    if not matched_rows:
        matched_rows = _matching_suggestions(
            open_rows,
            agent=agent,
            count=count,
        )
    chosen_agent = _clean(agent) or (
        _clean(matched_rows[0].get("recommended_agent")) if matched_rows else ""
    )
    if is_resident_manager_slug(chosen_agent):
        return 0
    updated = 0

    for row in matched_rows:
        store.update_delegation(
            row["id"],
            status="delegated",
            backend=backend,
            executed_worker_kind=executed_worker_kind,
            executed_worker_id=executed_worker_id,
            native_run_id=native_run_id,
            host=host,
        )
        updated += 1

    if updated:
        return updated

    derived_work_unit = _clean(work_unit_id) or work_unit_id_from_text(
        goal or chosen_agent or backend
    )
    duplicate = any(
        _clean(row.get("session_id")) == session_id
        and _clean(row.get("work_unit_id")) == derived_work_unit
        and _clean(row.get("executed_worker_kind")) == _clean(executed_worker_kind)
        and _clean(row.get("executed_worker_id")) == _clean(executed_worker_id)
        and _clean(row.get("backend")) == _clean(backend)
        and _clean(row.get("status")) in {"started", "running", "delegated", "completed"}
        for row in all_rows
    )
    if duplicate:
        return 0

    store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host=host,
        work_unit_id=derived_work_unit,
        # Preserve a declared recommendation as planning evidence without
        # projecting it as the executor.  Execution identity is carried only
        # by executed_worker_kind / worker ID / native run ID.
        recommended_agent=chosen_agent,
        status="delegated",
        backend=backend,
        executed_worker_kind=executed_worker_kind,
        executed_worker_id=executed_worker_id,
        native_run_id=native_run_id,
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
    executed_worker_kind: str = "",
    executed_worker_id: str = "",
    native_run_id: str = "",
) -> int:
    """Mark suggested work units as skipped, or record an explicit blocker."""
    session_id = _clean(session_id)
    trace_id = _clean(trace_id)
    if not session_id or not trace_id:
        return 0
    all_rows = [
        row
        for row in store.get_delegations(trace_id)
        if _clean(row.get("session_id")) == session_id
    ]
    open_rows = [row for row in all_rows if row.get("status") == "suggested"]
    matched_rows = _matching_work_unit_identity(
        all_rows,
        work_unit_id=work_unit_id,
        goal=goal,
        count=count,
    )
    if not matched_rows:
        matched_rows = _matching_suggestions(
            open_rows,
            agent=agent,
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
            executed_worker_kind=executed_worker_kind,
            executed_worker_id=executed_worker_id,
            native_run_id=native_run_id,
            host=host,
            skip_reason=skip_reason,
        )
        updated += 1

    if updated:
        return updated

    store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host=host,
        work_unit_id=_clean(work_unit_id)
        or work_unit_id_from_text(goal or chosen_agent or backend or skip_reason),
        recommended_agent=chosen_agent,
        status="skipped",
        backend=backend,
        executed_worker_kind=executed_worker_kind,
        executed_worker_id=executed_worker_id,
        native_run_id=native_run_id,
        skip_reason=skip_reason,
    )
    return 1


def _matching_suggestions(
    rows: list[dict[str, Any]],
    *,
    agent: str,
    count: int,
) -> list[dict[str, Any]]:
    """Return suggestions that can be correlated without relying on row order.

    Stable work-unit identity is resolved before this compatibility fallback.
    An agent can disambiguate a unique suggestion. A sole open suggestion is
    also safe; multiple ambiguous suggestions are never matched by row order.
    """
    if not rows:
        return []

    limit = max(1, int(count or 1))
    chosen_agent = _clean(agent)
    if chosen_agent:
        agent_matches = [
            row for row in rows if _clean(row.get("recommended_agent")) == chosen_agent
        ]
        if len(agent_matches) == 1:
            return agent_matches
        if len(agent_matches) > 1 and limit > 1:
            return agent_matches[:limit]

    return rows if len(rows) == 1 else []


def _matching_work_unit_identity(
    rows: list[dict[str, Any]],
    *,
    work_unit_id: str,
    goal: str,
    count: int,
) -> list[dict[str, Any]]:
    """Match stable IDs, including a task hash behind a native response ID."""
    if not rows:
        return []
    limit = max(1, int(count or 1))
    explicit_id = _clean(work_unit_id)
    if explicit_id:
        explicit_matches = [row for row in rows if _clean(row.get("work_unit_id")) == explicit_id]
        if explicit_matches:
            return explicit_matches[:limit]

    task = _clean(goal)
    if not task:
        return []
    task_id = work_unit_id_from_text(task)
    return [row for row in rows if _clean(row.get("work_unit_id")) == task_id][:limit]


__all__ = [
    "MAX_AGENT_SLUG_CHARS",
    "MAX_SUGGESTED_WORK_UNITS",
    "MAX_WORK_UNIT_CHARS",
    "UNIT_AGENT_ASSIGNMENT_VERSION",
    "build_unit_agent_plan",
    "mark_delegation_executed",
    "mark_delegation_skipped",
    "record_suggested_delegations",
    "suggested_delegations",
    "work_unit_id_from_text",
]
