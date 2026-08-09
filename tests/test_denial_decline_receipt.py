"""PreToolUse denials record their own decline receipt."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.adapters.hooks import HookBridge

_SESSION = "s" * 32
_TRACE = "t" * 32


class _StubStore:
    """Minimal delegation surface used by mark_delegation_skipped."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows if rows is not None else []
        self.updates: list[dict[str, Any]] = []
        self.recorded: list[dict[str, Any]] = []

    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        return [dict(row) for row in self.rows if row.get("trace_id") == trace_id]

    def update_delegation(self, event_id: str, **fields: Any) -> None:
        self.updates.append({"id": event_id, **fields})
        for row in self.rows:
            if row.get("id") == event_id:
                row.update(fields)

    def record_delegation(self, **fields: Any) -> None:
        self.recorded.append(dict(fields))


class _ExplodingStore(_StubStore):
    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        raise RuntimeError("store is unavailable")


def _suggested_row() -> dict[str, Any]:
    return {
        "id": "event-1",
        "session_id": _SESSION,
        "trace_id": _TRACE,
        "work_unit_id": "unit-1",
        "recommended_agent": "technical-writer",
        "status": "suggested",
    }


def _bridge(store: _StubStore) -> HookBridge:
    return HookBridge("claude", store=store)


def _deny(bridge: HookBridge) -> dict[str, Any]:
    return bridge._denied_with_decline_receipt(
        "Agency refused this launch.",
        session_id=_SESSION,
        trace_id=_TRACE,
        work_unit_id="unit-1",
        agent="technical-writer",
        decline_reason="a one-use activation grant could not be issued",
    )


def test_denial_closes_the_work_unit_without_a_second_parent_call() -> None:
    store = _StubStore([_suggested_row()])

    result = _deny(_bridge(store))

    assert result  # still a denial
    assert len(store.updates) == 1
    assert store.updates[0]["status"] == "skipped"
    assert store.updates[0]["skip_reason"] == "a one-use activation grant could not be issued"


def test_denial_survives_a_store_that_cannot_record_the_receipt() -> None:
    """A missing receipt is an evidence gap; a permitted launch is worse."""

    denied = _deny(_bridge(_ExplodingStore()))

    assert denied
    assert denied == _bridge(_StubStore())._denied_with_decline_receipt(
        "Agency refused this launch.",
        session_id="",
        trace_id="",
        work_unit_id="",
        agent="",
        decline_reason="unused",
    )


@pytest.mark.parametrize(
    "session_id,trace_id,work_unit_id",
    [("", _TRACE, "unit-1"), (_SESSION, "", "unit-1"), (_SESSION, _TRACE, "")],
)
def test_incomplete_identity_records_nothing(
    session_id: str,
    trace_id: str,
    work_unit_id: str,
) -> None:
    store = _StubStore([_suggested_row()])

    assert _bridge(store)._denied_with_decline_receipt(
        "Agency refused this launch.",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=work_unit_id,
        agent="technical-writer",
        decline_reason="reason",
    )
    assert store.updates == []
    assert store.recorded == []


# The parent-side decline tests that lived here drove `agency.decline_delegation`,
# retired in eab8c085. The hook-side denial receipt above is unaffected: it is
# written by PreToolUse, not by a parent tool call.
