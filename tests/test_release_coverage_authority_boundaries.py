"""Release coverage for security-relevant authority and persistence boundaries."""

from __future__ import annotations

import sqlite3
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.store import finalization_batch as finalization
from agency_runtime.core.store import maintenance, observed_sqlite
from agency_runtime.core.store.projections import DELEGATION_DETAIL_LIMIT
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import mcp_tools


class _Rows:
    def __init__(self, row: Any = None, *, rows: list[Any] | None = None) -> None:
        self._row = row
        self._rows = [] if rows is None else rows

    def fetchone(self) -> Any:
        return self._row

    def fetchall(self) -> list[Any]:
        return self._rows


def _delegation(**updates: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "agent": "reviewer",
        "status": "skipped",
        "backend": "native",
        "work_unit_id": "unit",
    }
    value.update(updates)
    return value


@pytest.mark.parametrize(
    ("skills", "delegations", "message"),
    [
        ([" leading"], [], "canonical single-line"),
        ([""], [], "is required"),
        ([], [_delegation(skip_reason=7)], "must be a string"),
        ([], [_delegation(error="bad\x00detail")], "bounded text contract"),
        ([], [42], "must be an object"),
        (
            [],
            [{**_delegation(), "recommended_agent": "reviewer"}],
            "exactly one of agent or recommended_agent",
        ),
        ([], [{"agent": "reviewer", "status": "skipped"}], "work_unit_id"),
        ([], [_delegation(agent="agency-steward")], "parent-only"),
        ([], [_delegation(status="completed")], "positive delegations require"),
        (
            [],
            [_delegation(executed_worker_kind="generic-worker")],
            "execution identity must be complete",
        ),
        ((), [], "skills_loaded must be a list"),
        ([], (), "delegations must be a list"),
        (["skill"] * 129, [], "skills_loaded exceeds"),
        ([], [_delegation()] * 129, "delegations exceeds"),
        (["skill"] * 64, [{}] * 65, "finalization evidence exceeds the item limit"),
    ],
)
def test_finalization_validation_rejects_each_authority_boundary(
    skills: object,
    delegations: object,
    message: str,
) -> None:
    with pytest.raises(finalization.FinalizationEvidenceError, match=message):
        finalization.validate_finalization_evidence_items(
            skills_loaded=skills,
            delegations=delegations,
        )


def test_finalization_batch_rejects_bad_correlation_and_encoded_overflow() -> None:
    with pytest.raises(finalization.FinalizationEvidenceError, match="session_id"):
        finalization.validate_finalization_evidence_batch(
            session_id=" ",
            trace_id="trace",
            skills_loaded=[],
            delegations=[],
        )
    oversized = [
        _delegation(work_unit_id=f"unit-{index}", error="x" * DELEGATION_DETAIL_LIMIT)
        for index in range(finalization.MAX_FINALIZATION_EVIDENCE_ITEMS)
    ]
    with pytest.raises(finalization.FinalizationEvidenceError, match="byte limit"):
        finalization.validate_finalization_evidence_batch(
            session_id="session",
            trace_id="trace",
            skills_loaded=[],
            delegations=oversized,
        )


class _TransactionDelegate:
    marker = "delegate"

    def execute(self, sql: str, parameters: object = ()) -> tuple[object, ...]:
        return ("execute", sql, parameters)

    def executemany(self, sql: str, parameters: object) -> tuple[object, ...]:
        return ("executemany", sql, parameters)


def test_bound_transaction_proxy_blocks_work_after_rollback() -> None:
    state = finalization._BoundTransactionState()
    proxy = finalization._BoundTransactionConnection(_TransactionDelegate(), state)

    ignored = proxy.execute("BEGIN IMMEDIATE")
    assert ignored.fetchone() is None
    assert ignored.fetchall() == []
    assert proxy.execute("SELECT 1")[:2] == ("execute", "SELECT 1")
    assert proxy.executemany("SELECT ?", [(1,)])[:2] == ("executemany", "SELECT ?")
    assert proxy.marker == "delegate"
    assert proxy.close() is None

    proxy.rollback()
    with pytest.raises(RuntimeError, match="requested rollback"):
        proxy.execute("SELECT 1")
    with pytest.raises(RuntimeError, match="requested rollback"):
        proxy.executemany("SELECT ?", [(1,)])
    with pytest.raises(RuntimeError, match="requested rollback"):
        proxy.commit()


def _batch() -> finalization.ValidatedFinalizationEvidenceBatch:
    return finalization.ValidatedFinalizationEvidenceBatch(
        session_id="session",
        trace_id="trace",
        skills=(),
        delegations=(),
        encoded_bytes=0,
    )


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (None, "existing active turn"),
        (
            {
                "session_id": "other",
                "status": "active",
                "ended_at": None,
                "terminal_finalization_id": None,
                "preflight_state": "ready",
                "host": "codex",
            },
            "does not belong",
        ),
        (
            {
                "session_id": "session",
                "status": "active",
                "ended_at": "now",
                "terminal_finalization_id": None,
                "preflight_state": "ready",
                "host": "codex",
            },
            "inconsistent terminal state",
        ),
        (
            {
                "session_id": "session",
                "status": "completed",
                "ended_at": None,
                "terminal_finalization_id": "event",
                "preflight_state": "ready",
                "host": "codex",
            },
            "incomplete finalization state",
        ),
        (
            {
                "session_id": "session",
                "status": "evidence_only",
                "ended_at": None,
                "terminal_finalization_id": None,
                "preflight_state": "ready",
                "host": "codex",
            },
            "not completed preflight",
        ),
        (
            {
                "session_id": "session",
                "status": "active",
                "ended_at": None,
                "terminal_finalization_id": None,
                "preflight_state": "planned",
                "host": "codex",
            },
            "not completed preflight",
        ),
    ],
)
def test_batch_run_loading_fails_closed_for_inconsistent_authority(
    row: Any,
    message: str,
) -> None:
    connection = SimpleNamespace(execute=lambda *_args, **_kwargs: _Rows(row))
    with pytest.raises(finalization.FinalizationEvidenceConflictError, match=message):
        finalization._load_batch_run(connection, _batch())


def test_existing_delegation_must_belong_to_batch_session() -> None:
    item = finalization._validate_delegation(_delegation(), index=0)
    with pytest.raises(finalization.FinalizationEvidenceConflictError, match="authoritative"):
        finalization._validate_persisted_delegations(
            object(),
            batch=_batch(),
            delegations=(item,),
            existing_by_unit={"unit": {"session_id": "other"}},
            authoritative_host="codex",
            now="now",
        )


def test_existing_delegation_merge_reuses_authoritative_event_identity() -> None:
    item = finalization._validate_delegation(_delegation(), index=0)
    observed: dict[str, Any] = {}

    def merge(_conn: Any, existing: Any, **kwargs: Any) -> None:
        observed.update(existing=existing, **kwargs)

    existing = {"id": "event", "session_id": "session"}
    store = SimpleNamespace(_uuid=lambda: "new", _merge_delegation_transition=merge)
    skills, delegation_ids = finalization._write_batch_evidence(
        store,
        object(),
        batch=_batch(),
        delegations=(item,),
        existing_by_unit={"unit": existing},
        authoritative_host="codex",
        now="now",
    )

    assert skills == []
    assert delegation_ids == ["event"]
    assert observed["existing"] is existing
    assert observed["status"] == "skipped"


def test_finalizer_and_receipt_helpers_fail_closed_on_incomplete_contracts() -> None:
    with pytest.raises(RuntimeError, match="invalid result contract"):
        finalization._run_bound_finalizer(
            SimpleNamespace(),
            object(),
            authoritative_host="codex",
            finalizer=lambda *_args: {},
        )
    connection = SimpleNamespace(execute=lambda *_args, **_kwargs: _Rows(rows=[]))
    with pytest.raises(RuntimeError, match="completeness"):
        finalization._load_delegation_receipts(connection, ["missing"])
    assert finalization._persistence_failure({"text": "draft"}) == {
        "finalization": {
            "action": "continue",
            "text": "draft",
            "missing": ["evidence_persistence"],
        },
        "receipt": None,
    }


def test_batch_coordinator_rejects_invalid_finalizer_and_projected_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(finalization.FinalizationEvidenceError, match="must be callable"):
        finalization.FinalizationBatchStoreMixin.finalize_evidence_batch(
            SimpleNamespace(),
            session_id="session",
            trace_id="trace",
            skills_loaded=[],
            delegations=[],
            finalizer=None,  # type: ignore[arg-type]
        )

    encoded_sizes = iter((0, finalization.MAX_FINALIZATION_EVIDENCE_BYTES + 1))
    monkeypatch.setattr(
        finalization,
        "_encoded_batch_bytes",
        lambda **_kwargs: next(encoded_sizes),
    )
    store = SimpleNamespace(_capture_content_enabled=lambda: False)
    with pytest.raises(finalization.FinalizationEvidenceError, match="byte limit"):
        finalization.FinalizationBatchStoreMixin.finalize_evidence_batch(
            store,
            session_id="session",
            trace_id="trace",
            skills_loaded=[],
            delegations=[],
            finalizer=lambda *_args: {},
        )


class _CoordinatorConnection:
    def __init__(self) -> None:
        self.rollbacks = 0
        self.closed = False

    def execute(self, *_args: Any, **_kwargs: Any) -> _Rows:
        return _Rows()

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_batch_coordinator_rolls_back_when_terminal_receipt_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _CoordinatorConnection()
    store = SimpleNamespace(
        _capture_content_enabled=lambda: False,
        _connect=lambda: connection,
        _now=lambda: "now",
    )
    monkeypatch.setattr(
        finalization,
        "_load_batch_run",
        lambda *_args: ({}, False, "codex"),
    )
    monkeypatch.setattr(finalization, "_load_existing_delegations", lambda *_a, **_kw: {})
    monkeypatch.setattr(finalization, "_validate_persisted_delegations", lambda *_a, **_kw: None)
    monkeypatch.setattr(finalization, "_write_batch_evidence", lambda *_a, **_kw: ([], []))
    monkeypatch.setattr(
        finalization,
        "_run_bound_finalizer",
        lambda *_a, **_kw: (
            {"action": "accept", "text": "answer", "missing": []},
            finalization._BoundTransactionState(),
        ),
    )
    monkeypatch.setattr(finalization, "_terminal_receipt_row", lambda *_a, **_kw: None)

    result = finalization.FinalizationBatchStoreMixin.finalize_evidence_batch(
        store,
        session_id="session",
        trace_id="trace",
        skills_loaded=[],
        delegations=[],
        finalizer=lambda *_args: {},
    )

    assert result["receipt"] is None
    assert result["finalization"]["missing"] == ["evidence_persistence"]
    assert connection.rollbacks == 1
    assert connection.closed is True


def test_observed_sqlite_cursor_and_connection_preserve_success_and_errors() -> None:
    connection = sqlite3.connect(":memory:", factory=observed_sqlite.ObservedSQLiteConnection)
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE values_table (value INTEGER)")
    cursor.executemany("INSERT INTO values_table(value) VALUES (?)", [(1,), (2,)])
    assert cursor.execute("SELECT COUNT(*) FROM values_table").fetchone()[0] == 2
    with pytest.raises(sqlite3.Error):
        cursor.execute("SELECT * FROM missing_table")
    with pytest.raises(sqlite3.Error):
        cursor.executemany("INSERT INTO missing_table(value) VALUES (?)", [(1,)])
    with pytest.raises(sqlite3.Error):
        connection.executemany("INSERT INTO missing_table(value) VALUES (?)", [(1,)])
    with pytest.raises(sqlite3.Error):
        connection.executescript("CREATE TABLE broken (")
    connection.close()
    with pytest.raises(sqlite3.Error):
        connection.commit()
    with pytest.raises(sqlite3.Error):
        connection.rollback()


def test_maintenance_empty_pages_validate_and_preserve_keyset_contracts(tmp_path: Any) -> None:
    assert maintenance._activity_cursor_time("runs", {"started_at": "start"}) == "start"
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="collection is invalid"):
        store.dashboard_activity_page("unknown")
    with pytest.raises(ValueError, match="cursor is incomplete"):
        store.dashboard_activity_page("runs", after_time="time")
    assert store.dashboard_activity_page("runs", limit=1)["rows"] == []
    assert (
        store.dashboard_activity_page(
            "runs",
            limit=1,
            after_time="2026-01-01T00:00:00Z",
            after_id="run",
        )["rows"]
        == []
    )

    with pytest.raises(ValueError, match="snapshot cursor is incomplete"):
        store.roster_snapshot_page(after_snapshot_id="snapshot")
    snapshot_page = store.roster_snapshot_page(limit=1)
    assert snapshot_page["rows"] == []
    assert len(snapshot_page["collection_revision"]) == 64
    assert (
        store.roster_snapshot_page(
            limit=1,
            after_created_at="2026-01-01T00:00:00Z",
            after_snapshot_id="snapshot",
        )["rows"]
        == []
    )


class _ReadFailureConnection:
    def __init__(self) -> None:
        self.rollbacks = 0
        self.closed = False

    def execute(self, sql: str, _parameters: object = ()) -> _Rows:
        if sql == "BEGIN":
            return _Rows()
        raise RuntimeError("synthetic read failure")

    def commit(self) -> None:
        raise AssertionError("failed reads must not commit")

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    "operation",
    ("dashboard_activity_snapshot", "dashboard_activity_page", "roster_snapshot_page"),
)
def test_maintenance_snapshot_reads_rollback_and_close_on_failure(operation: str) -> None:
    connection = _ReadFailureConnection()
    store = SimpleNamespace(
        _connect=lambda: connection,
        _repair_storage_permissions=lambda: None,
    )

    with pytest.raises(RuntimeError, match="synthetic read failure"):
        if operation == "dashboard_activity_snapshot":
            maintenance.MaintenanceStoreMixin.dashboard_activity_snapshot(store, limit=1)
        elif operation == "dashboard_activity_page":
            maintenance.MaintenanceStoreMixin.dashboard_activity_page(store, "runs", limit=1)
        else:
            maintenance.MaintenanceStoreMixin.roster_snapshot_page(store, limit=1)

    assert connection.rollbacks == 1
    assert connection.closed is True


def _preflight_arguments(**updates: Any) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "session_id": "session",
        "trace_id": "trace",
        "host": "codex",
        "user_message": "review this",
        "parent_scope_token": "token",
    }
    arguments.update(updates)
    return arguments


def test_mcp_identifier_and_parent_scope_helpers_fail_closed() -> None:
    assert mcp_tools._correlation({"session_id": " session ", "trace_id": "trace"}) is None
    assert mcp_tools._noncanonical_identifier({"worker_id": 7}, "worker_id") == "worker_id"

    arguments = {
        "parent_scope_token": "token",
        "host": "codex",
        "session_id": "session",
        "trace_id": "trace",
    }
    assert mcp_tools._consume_parent_scope(SimpleNamespace(), **arguments)[1]
    non_mapping_store = SimpleNamespace(consume_native_child_parent_scope=lambda **_kwargs: [])
    assert mcp_tools._consume_parent_scope(non_mapping_store, **arguments)[1]
    assert mcp_tools._restore_parent_scope(SimpleNamespace(), **arguments) is False
    failing_restorer = SimpleNamespace(
        restore_native_child_parent_scope_after_failed_preflight=lambda **_kwargs: (
            _ for _ in ()
        ).throw(RuntimeError("restore failed"))
    )
    assert mcp_tools._restore_parent_scope(failing_restorer, **arguments) is False


def test_mcp_preflight_restoration_failure_preserves_exception_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scope_store = SimpleNamespace(
        consume_native_child_parent_scope=lambda **_kwargs: {
            "parent_session_id": "parent-session",
            "parent_trace_id": "parent-trace",
            "worker_id": "worker",
            "native_run_id": "run",
        }
    )
    assert (
        "user_message"
        in mcp_tools._preflight(
            _preflight_arguments(user_message=" "),
            scope_store,
        )["error"]
    )

    monkeypatch.setattr(
        "agency_runtime.core.preflight.run_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("preflight failed")),
    )
    assert mcp_tools._preflight(_preflight_arguments(), scope_store) == {
        "error": "native child parent scope retry is unavailable"
    }

    monkeypatch.setattr(
        "agency_runtime.core.preflight.run_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        mcp_tools._preflight(_preflight_arguments(), scope_store)

    monkeypatch.setattr(
        "agency_runtime.core.preflight.run_preflight",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("unscoped failure")),
    )
    with pytest.raises(RuntimeError, match="unscoped failure"):
        mcp_tools._preflight(
            _preflight_arguments(parent_scope_token=""),
            SimpleNamespace(),
        )


@pytest.mark.parametrize(
    ("handler", "arguments", "field"),
    [
        (
            mcp_tools._load_specialist,
            {"session_id": "session", "trace_id": "trace", "slug": " reviewer "},
            "slug",
        ),
    ],
)
def test_mcp_handlers_reject_noncanonical_identifiers_before_store_use(
    handler: Any,
    arguments: dict[str, Any],
    field: str,
) -> None:
    assert handler(arguments, SimpleNamespace()) == {
        "error": f"{field} must be an exact canonical identifier"
    }


def test_mcp_load_specialist_records_exact_ordinary_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[tuple[str, str, str]] = []
    monkeypatch.setattr(mcp_tools, "active_turn_error", lambda *_args: "")
    store = SimpleNamespace(
        get_specialist_prompt=lambda slug: {
            "prompt_body": "review carefully",
            "name": "Reviewer",
            "description": "Reviews changes",
            "version": "1",
            "prompt_hash": "hash",
        },
        record_specialist_loaded=lambda session, slug, *, trace_id: recorded.append(
            (session, slug, trace_id)
        ),
    )

    result = mcp_tools._load_specialist(
        {"session_id": "session", "trace_id": "trace", "slug": "reviewer"},
        store,
    )

    assert recorded == [("session", "reviewer", "trace")]
    assert result["prompt"] == "review carefully"
    assert result["prompt_truncated"] is False
