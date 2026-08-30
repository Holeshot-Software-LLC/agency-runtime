"""Exact branch coverage for SQLite lifecycle and integrity guards."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.store import sqlite as sqlite_store
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.trace_identity import correlation_digest

_RESPONSE_HASH = "a" * 64


class _Result:
    def __init__(self, row: Any = None, *, rowcount: int = 1) -> None:
        self._row = row
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self._row

    def __iter__(self) -> Iterator[Any]:
        # workforce_schema_is_current iterates PRAGMA table_info(...) results.
        return iter([self._row] if self._row is not None else [])


class _IntegrityConnection:
    def __init__(self, failure: str) -> None:
        self.failure = failure
        self.closed = False
        self.row_factory: Any = None

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
        if sql == "PRAGMA recursive_triggers":
            return _Result((1,))
        if sql == "PRAGMA journal_mode":
            return _Result(("wal",))
        if "sqlite_master" in sql:
            return _Result((1,))
        if "MAX(version)" in sql:
            return _Result({"version": sqlite_store._SCHEMA_VERSION})
        if "trace_digest IS NULL" in sql:
            return _Result((1,) if self.failure == "tombstone" else None)
        if "FROM runs WHERE typeof(turn_sequence)" in sql:
            return _Result((1,) if self.failure == "sequence" else None)
        if "typeof(evidence_revision)" in sql:
            return _Result((1,) if self.failure == "revision" else None)
        if "FROM store_counters" in sql:
            return _Result(
                None if self.failure == "counter" else {"value": 1, "value_type": "integer"}
            )
        if "SELECT MAX(sequence)" in sql:
            return _Result({"sequence": 1})
        return _Result()

    def close(self) -> None:
        self.closed = True


class _SnapshotBoundaryConnection:
    def __init__(self, connection: Any, on_counter_read: Callable[[], None]) -> None:
        self._connection = connection
        self._on_counter_read = on_counter_read
        self.triggered = False

    @property
    def row_factory(self) -> Any:
        return self._connection.row_factory

    @row_factory.setter
    def row_factory(self, value: Any) -> None:
        self._connection.row_factory = value

    @property
    def in_transaction(self) -> bool:
        return bool(self._connection.in_transaction)

    def execute(self, sql: str, *args: Any, **kwargs: Any) -> Any:
        result = self._connection.execute(sql, *args, **kwargs)
        if not self.triggered and "SELECT value, typeof(value)" in sql:
            buffered = _Result(result.fetchone())
            self.triggered = True
            self._on_counter_read()
            return buffered
        return result

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("sequence", "turn sequence integrity"),
        ("revision", "evidence revision integrity"),
        ("tombstone", "retired-trace barrier integrity"),
        ("counter", "turn sequence counter integrity"),
    ],
)
def test_current_schema_state_fails_closed_on_integrity_corruption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    message: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _IntegrityConnection(failure)
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(
        sqlite_store, "ensure_correlation_key_integrity", lambda *_args, **_kwargs: b"k" * 32
    )
    monkeypatch.setattr(sqlite_store, "_v20_receipt_schema_is_current", lambda _conn: True)
    monkeypatch.setattr(sqlite_store, "remediation_indexes_are_current", lambda _conn: True)
    monkeypatch.setattr(
        sqlite_store,
        "remediation_authority_schema_is_current",
        lambda _conn: True,
    )
    monkeypatch.setattr(
        sqlite_store,
        "agent_import_event_sequence_schema_is_current",
        lambda _conn: True,
    )
    monkeypatch.setattr(
        sqlite_store,
        "ensure_remediation_authority_key_integrity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(sqlite_store, "trace_tombstone_turn_sequence_is_unique", lambda _conn: True)
    monkeypatch.setattr(sqlite_store, "workforce_schema_is_current", lambda _conn: True)
    with pytest.raises(RuntimeError, match=message):
        store._current_schema_state()
    assert connection.closed is True


def test_current_schema_state_uses_one_snapshot_across_counter_and_maximum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    real_connect = sqlite_store.sqlite3.connect
    observed: list[_SnapshotBoundaryConnection] = []

    def commit_concurrent_turn() -> None:
        store.create_run(
            trace_id="concurrent-schema-inspection-turn",
            session_id="concurrent-schema-inspection-session",
        )

    def connect(database: Any, *args: Any, **kwargs: Any) -> Any:
        connection = real_connect(database, *args, **kwargs)
        if kwargs.get("uri") is True:
            wrapped = _SnapshotBoundaryConnection(connection, commit_concurrent_turn)
            observed.append(wrapped)
            return wrapped
        return connection

    monkeypatch.setattr(sqlite_store.sqlite3, "connect", connect)

    assert store._current_schema_state() == (True, True)
    assert len(observed) == 1
    assert observed[0].triggered is True
    assert store.get_run("concurrent-schema-inspection-turn") is not None


def test_ensure_and_require_open_run_cover_correlation_guards(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="active", session_id="session")
    conn = store._connect()
    try:
        with pytest.raises(ValueError, match="different session"):
            store._ensure_run(conn, trace_id="active", session_id="other")
        store._ensure_run(conn, trace_id="active", session_id=None)

        with pytest.raises(ValueError, match="does not exist"):
            store._require_open_run(conn, trace_id="missing")
        with pytest.raises(ValueError, match="different session"):
            store._require_open_run(conn, trace_id="active", session_id="other")
        run = store._require_open_run(
            conn,
            trace_id="active",
            session_id="session",
            touch=False,
        )
        assert run["status"] == "active"
        conn.commit()
    finally:
        conn.close()

    run_id = str(store.get_run("active")["id"])
    store.complete_run(run_id)
    conn = store._connect()
    try:
        with pytest.raises(ValueError, match="terminal turn"):
            store._require_open_run(conn, trace_id="active")
    finally:
        conn.close()


def test_finalization_receipt_and_snapshot_empty_or_invalid_paths(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="does not exist"):
        store.record_finalization(trace_id="missing", host="codex", action="continue")
    assert store.validate_pending_retry_receipt("", "receipt") is None
    assert store.validate_pending_retry_receipt("session", "") is None
    assert store.has_finalization_action("", "continue") is False
    assert store.has_finalization_action("turn", "") is False
    with pytest.raises(ValueError, match="boolean"):
        store.claim_continuation(
            session_id="session",
            trace_id="turn",
            host="codex",
            response_hash=_RESPONSE_HASH,
            retry_active=1,  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="does not exist"):
        store.claim_continuation(
            session_id="session",
            trace_id="turn",
            host="codex",
            response_hash=_RESPONSE_HASH,
        )
    with pytest.raises(ValueError, match="does not identify"):
        store.get_completion_evidence_snapshot("session", "missing")

    store.create_run(trace_id="active", session_id="session")
    with pytest.raises(ValueError, match="does not belong"):
        store.get_completion_evidence_snapshot("other", "active")
    store.record_finalization(
        trace_id="active",
        host="codex",
        action="continue",
        response_hash=_RESPONSE_HASH,
    )
    assert store.has_finalization_action(
        "active",
        "continue",
        response_hash=_RESPONSE_HASH,
    )


class _TerminalCasConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
        if "SELECT id, session_id, status" in sql:
            return _Result(
                {
                    "id": "run",
                    "session_id": "session",
                    "status": "active",
                    "ended_at": None,
                    "terminal_finalization_id": None,
                    "evidence_revision": 1,
                    "metadata": "{}",
                }
            )
        if "UPDATE runs SET ended_at" in sql:
            return _Result(rowcount=0)
        return _Result()

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_terminal_finalization_detects_compare_and_swap_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _TerminalCasConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)
    with pytest.raises(RuntimeError, match="compare-and-swap"):
        store.commit_terminal_finalization(
            session_id="session",
            trace_id="turn",
            host="codex",
            action="accept",
            response_hash=_RESPONSE_HASH,
            status="completed",
            expected_evidence_revision=1,
        )
    assert connection.rolled_back is True
    assert connection.closed is True


def test_authoritative_queries_reject_blank_identity_and_honor_tombstone_barrier(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    assert store.get_authoritative_finalization("", "turn") is None
    assert store.get_authoritative_finalization("session", "") is None

    store.create_run(trace_id="turn", session_id="session")
    conn = store._connect()
    try:
        latest = conn.execute("SELECT turn_sequence FROM runs WHERE trace_id = 'turn'").fetchone()
        digest = correlation_digest(conn, "session", domain="session")
        conn.execute(
            "INSERT INTO trace_tombstones "
            "(trace_digest, session_digest, turn_sequence, retired_at) VALUES (?, ?, ?, ?)",
            ("f" * 64, digest, int(latest["turn_sequence"]), "now"),
        )
        conn.commit()
    finally:
        conn.close()
    assert (
        store.find_authoritative_trace(
            "session",
            action="accept",
            response_hash=_RESPONSE_HASH,
        )
        is None
    )
