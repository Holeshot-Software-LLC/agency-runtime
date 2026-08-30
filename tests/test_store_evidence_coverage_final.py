"""Exact branch coverage for correlated runtime evidence persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.store import evidence as evidence_module
from agency_runtime.core.store.sqlite import Store


class _HostControlCasLossConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Rows:
        if "SELECT host, enabled, generation" in sql:
            return _Rows(
                row={
                    "host": "codex",
                    "enabled": 1,
                    "generation": 0,
                    "updated_at": "2026-07-16T00:00:00Z",
                    "source": "first-writer",
                }
            )
        if "UPDATE host_controls SET enabled" in sql:
            return _Rows(rowcount=0)
        return _Rows()

    def commit(self) -> None:
        raise AssertionError("a lost compare-and-swap must not commit")

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_create_run_rejects_a_conflicting_active_request_fingerprint(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        metadata={"request_fingerprint": "a" * 64},
    )
    with pytest.raises(ValueError, match="different preflight request"):
        store.create_run(
            trace_id="turn",
            session_id="session",
            metadata={"request_fingerprint": "b" * 64},
        )


def test_reservation_defends_against_empty_normalized_correlation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    monkeypatch.setattr(evidence_module, "validate_correlation_id", lambda *_args, **_kwargs: "")
    with pytest.raises(ValueError, match="required to reserve"):
        store.reserve_session_turn(session_id="session", trace_id="turn")


def test_reservation_rejects_cross_session_and_terminal_trace_reuse(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="cross-session", session_id="first")
    with pytest.raises(ValueError, match="different session"):
        store.reserve_session_turn(session_id="second", trace_id="cross-session")

    run_id = store.create_run(trace_id="terminal", session_id="session")
    store.complete_run(run_id)
    with pytest.raises(ValueError, match="terminal turn"):
        store.reserve_session_turn(session_id="session", trace_id="terminal")


def test_repeated_reservation_reuses_the_exact_receipt(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    first = store.reserve_session_turn(session_id="session", trace_id="turn")
    second = store.reserve_session_turn(session_id="session", trace_id="turn")
    assert first["reservation_token"]
    assert second == {
        "trace_id": "turn",
        "created": False,
        "abandoned": [],
        "reservation_token": first["reservation_token"],
    }


class _Rows:
    def __init__(
        self,
        *,
        row: Any = None,
        rows: list[Any] | None = None,
        rowcount: int = 1,
    ) -> None:
        self._row = row
        self._rows = [] if rows is None else rows
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self._row

    def fetchall(self) -> list[Any]:
        return self._rows


def test_host_control_rolls_back_when_update_compare_and_swap_is_lost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.host_control import HostControlConflictError

    store = Store(tmp_path / "agency.db")
    connection = _HostControlCasLossConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)

    with pytest.raises(HostControlConflictError, match="changed during update"):
        store.set_host_control(
            "codex",
            enabled=False,
            expected_generation=0,
            source="second-writer",
        )

    assert connection.rolled_back is True
    assert connection.closed is True


class _AbandonCasConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Rows:
        if "SELECT id, session_id, status" in sql:
            return _Rows(row=None)
        if "SELECT trace_id FROM runs" in sql:
            return _Rows(rows=[{"trace_id": "older"}])
        if "UPDATE runs SET ended_at" in sql:
            return _Rows(rowcount=0)
        return _Rows()

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_reservation_rolls_back_on_abandoned_turn_compare_and_swap_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _AbandonCasConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)
    with pytest.raises(RuntimeError, match="compare-and-swap"):
        store.reserve_session_turn(session_id="session", trace_id="turn")
    assert connection.rolled_back is True
    assert connection.closed is True


def test_missing_run_completion_and_empty_evidence_queries_are_noops(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.complete_run("missing")
    store.record_skill_loaded("", "skill")
    store.record_skill_loaded("session", "")
    assert store.get_skills_for_trace("", "turn") == []
    assert store.get_active_specialists_for_trace("session", "") == []
    assert store.get_specialists_for_trace("", "turn") == []
    assert store.close_turn_evidence("", "turn") == 0
    assert store.get_open_traces_for_session("") == []


def test_delegation_updates_require_a_live_correlated_event(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="event id is invalid"):
        store.update_delegation("", status="delegated")
    with pytest.raises(ValueError, match="no correlated run"):
        store.update_delegation("missing", status="delegated")

    store.create_run(trace_id="turn", session_id="session")
    event_id = store.record_delegation(
        trace_id="turn",
        session_id="session",
        host="codex",
        work_unit_id="unit-0000000000",
        recommended_agent="reviewer",
        status="suggested",
        backend="",
    )
    assert store.close_turn_evidence("session", "turn") == 1
    with pytest.raises(ValueError, match="terminal turn"):
        store.update_delegation(event_id, status="delegated")
