"""Shared projection for the two observable sides of Rule 8."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from agency_runtime.core.store.evidence import (
    PUBLISHED_ANYWAY_RUN_STATUSES,
    WITHHELD_RUN_STATUSES,
)

MAX_RULE8_EVIDENCE_ROWS: Final[int] = 500
AGENCY_BLIND_RUN_STATUSES: Final[frozenset[str]] = PUBLISHED_ANYWAY_RUN_STATUSES

FAIL_OPEN_RUN_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "abandoned",
        "canary_failed",
        "interrupted",
        "preflight_failed",
        "preflight_skipped",
        "verification_failed",
    }
)


def turn_closed_without_bound_response(
    store: Any,
    session_id: str,
    trace_id: str,
) -> bool:
    """Return whether this turn ended before any response was bound to it.

    A run that Agency's own lifecycle closed (fail-open: ``preflight_failed``
    and kin) has no accepted response an evaluated rejection could be
    defending; withholding the host's draft there is Agency punishing its own
    failure (Rule 8). A run bearing a response verdict (``completed``,
    ``response_invalid``, ``delegation_declined``) keeps its withhold/replay
    semantics.

    A live fail-open turn usually cannot name its own run: the authoritative
    composite trace is minted inside preflight and only returned to the host
    wiring on success, so a rejected turn correlates with the host's raw
    trace or with nothing (AR-365, measured 2026-09-01). After the exact
    lookup, fall back to the session's latest turn parent, bound to the
    provided trace when one exists.
    """

    if not session_id:
        return False
    run: Mapping[str, Any] | None = None
    getter = getattr(store, "get_run", None)
    if callable(getter) and trace_id:
        try:
            candidate = getter(trace_id)
        except Exception:
            candidate = None
        if isinstance(candidate, Mapping) and str(candidate.get("session_id") or "") == session_id:
            run = candidate
    if run is None:
        latest = getattr(store, "get_latest_run_for_session", None)
        if not callable(latest):
            return False
        try:
            candidate = latest(session_id)
        except Exception:
            return False
        if (
            not isinstance(candidate, Mapping)
            or str(candidate.get("session_id") or "") != session_id
        ):
            return False
        stored_trace = str(candidate.get("trace_id") or "")
        if (
            trace_id
            and stored_trace != trace_id
            and not stored_trace.startswith(f"{session_id}:{trace_id}:")
        ):
            return False
        run = candidate
    return str(run.get("status") or "") in FAIL_OPEN_RUN_STATUSES


def turn_never_received_staffing_contract(
    store: Any,
    session_id: str,
    trace_id: str,
) -> bool:
    """Return whether the judged response raced its own staffing delivery.

    ``preflight_state == "ready"`` is the store's record that this turn's
    staffing capsule and evidence contract were delivered to the model, and
    ``"in_progress"`` that a preflight attempt is still running. A response
    evaluated while the run is ``active`` with preflight ``in_progress`` was
    authored by a model that never saw the requirements it is being judged
    against — rejecting it withholds a finished answer because Agency was
    slow, not because the host misbehaved (AR-366, measured 2026-09-01: an
    owner reply arrived two seconds into a turn whose preflight was still
    ``in_progress`` and was withheld with every header field "missing").

    Deliberately narrow: only an exact run lookup with a matching session and
    an explicit in-flight preflight counts — a misbound trace or a run that
    never entered preflight must not grant a bypass.
    """

    if not session_id or not trace_id:
        return False
    getter = getattr(store, "get_run", None)
    if not callable(getter):
        return False
    try:
        run = getter(trace_id)
    except Exception:
        return False
    if not isinstance(run, Mapping) or str(run.get("session_id") or "") != session_id:
        return False
    if str(run.get("status") or "") != "active":
        return False
    return str(run.get("preflight_state") or "") == "in_progress"


def bounded_rule8_limit(limit: int) -> int:
    """Validate the public Rule-8 evidence window."""

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_RULE8_EVIDENCE_ROWS
    ):
        raise ValueError(f"Rule-8 evidence limit must be between 1 and {MAX_RULE8_EVIDENCE_ROWS}")
    return limit


def rule8_evidence_projection(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    host: str = "",
) -> dict[str, Any]:
    """Partition a bounded exceptional-run window without inferring publication.

    ``AGENCY_BLIND_RUN_STATUSES`` says only that Agency could not verify or
    persist its evidence. Historical rows can predate Rule 8, so the projection
    deliberately does not claim that those host turns were published.
    """

    bounded = bounded_rule8_limit(limit)
    window = [dict(row) for row in rows[:bounded]]
    exceptional = WITHHELD_RUN_STATUSES | AGENCY_BLIND_RUN_STATUSES
    unexpected = sorted({str(row.get("status") or "") for row in window} - exceptional)
    if unexpected:
        raise ValueError("Rule-8 evidence contains a non-exceptional run status")
    withheld = [row for row in window if row.get("status") in WITHHELD_RUN_STATUSES]
    agency_blind = [row for row in window if row.get("status") in AGENCY_BLIND_RUN_STATUSES]
    returned = len(window)
    if len(withheld) + len(agency_blind) != returned:
        raise ValueError("Rule-8 evidence partition is incomplete")
    normalized_host = str(host or "").strip().casefold()
    return {
        "window": {
            "kind": "most_recent_matching_exceptional_runs",
            "host": normalized_host or None,
            "limit": bounded,
            "returned": returned,
        },
        "counts": {
            "matching_exceptional_runs": returned,
            "withheld": len(withheld),
            "agency_blind": len(agency_blind),
        },
        "withheld_statuses": sorted(WITHHELD_RUN_STATUSES),
        "agency_blind_statuses": sorted(AGENCY_BLIND_RUN_STATUSES),
        "withheld": withheld,
        "agency_blind": agency_blind,
    }


__all__ = [
    "AGENCY_BLIND_RUN_STATUSES",
    "MAX_RULE8_EVIDENCE_ROWS",
    "bounded_rule8_limit",
    "rule8_evidence_projection",
]
