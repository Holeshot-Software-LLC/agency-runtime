"""All-or-nothing finalization evidence transaction regressions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.header.finalize import finalize_response_batch
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.finalization_batch import (
    MAX_FINALIZATION_EVIDENCE_ITEMS,
    FinalizationEvidenceConflictError,
    FinalizationEvidenceError,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_origin import native_adapter_turn_origin


def _ready_store(tmp_path: Path, *, trace_id: str = "trace") -> Store:
    store = Store(tmp_path / f"{trace_id}.db")
    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="adapter_preflight",
        session_id="session",
        trace_id=trace_id,
    )
    result = run_preflight(
        store,
        session_id="session",
        trace_id=trace_id,
        user_message="thanks",
        host="codex",
        origin_receipt=origin_receipt,
    )
    assert result.trivial is True
    return store


def _delegation(work_unit_id: str, *, worker: str = "worker") -> dict[str, str]:
    return {
        "agent": "code-reviewer",
        "status": "completed",
        "backend": "spawn_agent",
        "work_unit_id": work_unit_id,
        "executed_worker_kind": "generic-worker",
        "executed_worker_id": worker,
        "native_run_id": f"native:{worker}",
    }


def _finalize(
    store: Store,
    *,
    trace_id: str = "trace",
    draft_text: str = "Answer.",
    skills: object = None,
    delegations: object = None,
) -> dict[str, Any]:
    return finalize_response_batch(
        draft_text,
        trace_metadata={
            "session_id": "session",
            "trace_id": trace_id,
            "host": "caller-spoofed-host",
        },
        store=store,
        skills_loaded=[] if skills is None else skills,
        delegations=[] if delegations is None else delegations,
    )


def _event_count(store: Store, table: str, trace_id: str = "trace") -> int:
    connection = store._connect()
    try:
        return int(
            connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE trace_id = ?",  # nosec B608
                (trace_id,),
            ).fetchone()[0]
        )
    finally:
        connection.close()


def test_maximum_batch_uses_one_connection_and_one_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _ready_store(tmp_path)
    original_connect = store._connect
    connections = 0
    statements: list[str] = []

    def observed_connect() -> Any:
        nonlocal connections
        connections += 1
        connection = original_connect()
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(store, "_connect", observed_connect)
    skills = [f"skill-{index:03d}" for index in range(MAX_FINALIZATION_EVIDENCE_ITEMS)]

    result = _finalize(store, skills=skills)

    receipt = result["evidence_receipt"]
    assert result["action"] == "accept"
    assert receipt["item_count"] == MAX_FINALIZATION_EVIDENCE_ITEMS
    assert receipt["skill_count"] == MAX_FINALIZATION_EVIDENCE_ITEMS
    assert [item["skill_name"] for item in receipt["skills"]] == skills
    assert receipt["host"] == "codex"
    assert connections == 1
    assert sum(sql.lstrip().upper().startswith("BEGIN") for sql in statements) == 1
    assert sum(sql.lstrip().upper().startswith("COMMIT") for sql in statements) == 1


def test_receipt_exactly_covers_every_committed_item(tmp_path: Path) -> None:
    store = _ready_store(tmp_path)
    submitted = [_delegation("unit-one", worker="one"), _delegation("unit-two", worker="two")]

    result = _finalize(
        store,
        skills=["security-review", "finalization"],
        delegations=submitted,
    )

    receipt = result["evidence_receipt"]
    assert result["action"] == "accept"
    assert receipt["item_count"] == 4
    assert receipt["skill_count"] == 2
    assert receipt["delegation_count"] == 2
    assert [item["skill_name"] for item in receipt["skills"]] == [
        "security-review",
        "finalization",
    ]
    assert [item["work_unit_id"] for item in receipt["delegations"]] == [
        "unit-one",
        "unit-two",
    ]
    assert [item["executed_worker_id"] for item in receipt["delegations"]] == [
        "one",
        "two",
    ]
    assert len({item["id"] for item in receipt["skills"]}) == 2
    assert len({item["id"] for item in receipt["delegations"]}) == 2
    assert receipt["finalization_event_id"]
    assert receipt["terminal_status"] == "completed"
    assert store.get_run("trace")["status"] == "completed"
    assert _event_count(store, "skills_loaded") == 2
    assert _event_count(store, "delegation_events") == 2
    assert _event_count(store, "finalization_events") == 1


def test_late_lineage_conflict_is_detected_before_any_batch_write(tmp_path: Path) -> None:
    store = _ready_store(tmp_path)
    original_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="codex",
        recommended_agent="code-reviewer",
        work_unit_id="unit-conflict",
        status="completed",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="original",
        native_run_id="native:original",
    )

    with pytest.raises(FinalizationEvidenceConflictError, match="authoritative evidence"):
        _finalize(
            store,
            skills=["must-roll-back"],
            delegations=[
                _delegation("unit-new", worker="new"),
                _delegation("unit-conflict", worker="conflicting"),
            ],
        )

    assert store.get_skills_for_trace("session", "trace") == []
    assert _event_count(store, "delegation_events") == 1
    [existing] = store.get_delegations("trace")
    assert existing["id"] == original_id
    assert existing["executed_worker_id"] == "original"
    assert _event_count(store, "finalization_events") == 0
    assert store.get_run("trace")["status"] == "active"


@pytest.mark.parametrize(
    ("skills", "delegations", "error"),
    [
        (["duplicate", "duplicate"], [], "duplicate identity"),
        (
            [],
            [_delegation("duplicate-unit"), _delegation("duplicate-unit", worker="other")],
            "duplicate work_unit_id",
        ),
        (
            [],
            [{**_delegation("wrong-type"), "executed_worker_id": 7}],
            "must be a string",
        ),
        (
            [],
            [{**_delegation("oversized"), "native_run_id": "n" * 257}],
            "maximum length",
        ),
        (
            [],
            [{**_delegation("unknown"), "caller_model": "spoofed"}],
            "unknown fields",
        ),
    ],
)
def test_invalid_or_duplicate_batch_is_rejected_before_database_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    skills: object,
    delegations: object,
    error: str,
) -> None:
    store = _ready_store(tmp_path)
    monkeypatch.setattr(
        store,
        "_connect",
        lambda: (_ for _ in ()).throw(AssertionError("database was accessed")),
    )

    with pytest.raises(FinalizationEvidenceError, match=error):
        _finalize(store, skills=skills, delegations=delegations)


def test_mid_batch_database_failure_rolls_back_every_item(tmp_path: Path) -> None:
    store = _ready_store(tmp_path)
    connection = store._connect()
    try:
        connection.execute(
            "CREATE TRIGGER reject_second_batch_skill "
            "BEFORE INSERT ON skills_loaded WHEN NEW.skill_name = 'skill-fail' "
            "BEGIN SELECT RAISE(ABORT, 'forced batch failure'); END"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="forced batch failure"):
        _finalize(store, skills=["skill-ok", "skill-fail"])

    assert store.get_skills_for_trace("session", "trace") == []
    assert _event_count(store, "delegation_events") == 0
    assert _event_count(store, "finalization_events") == 0
    assert store.get_run("trace")["status"] == "active"


def test_forced_terminal_failure_rolls_back_context_and_finalization_event(
    tmp_path: Path,
) -> None:
    store = _ready_store(tmp_path)
    connection = store._connect()
    try:
        connection.execute(
            "CREATE TRIGGER reject_batch_finalization BEFORE INSERT ON finalization_events "
            "BEGIN SELECT RAISE(ABORT, 'forced finalization failure'); END"
        )
        connection.commit()
    finally:
        connection.close()

    result = _finalize(
        store,
        skills=["must-roll-back"],
        delegations=[_delegation("must-roll-back")],
    )

    assert result["action"] == "continue"
    assert result["missing"] == ["evidence_persistence"]
    assert result["evidence_receipt"] is None
    assert store.get_skills_for_trace("session", "trace") == []
    assert _event_count(store, "delegation_events") == 0
    assert _event_count(store, "finalization_events") == 0
    assert store.get_run("trace")["status"] == "active"


def test_interrupted_finalizer_rolls_back_the_complete_batch(tmp_path: Path) -> None:
    store = _ready_store(tmp_path)

    def interrupted(_transaction_store: Store, _host: str) -> dict[str, Any]:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        store.finalize_evidence_batch(
            session_id="session",
            trace_id="trace",
            skills_loaded=["must-roll-back"],
            delegations=[_delegation("must-roll-back")],
            finalizer=interrupted,
        )

    assert store.get_skills_for_trace("session", "trace") == []
    assert _event_count(store, "delegation_events") == 0
    assert _event_count(store, "finalization_events") == 0
    assert store.get_run("trace")["status"] == "active"


def test_exact_empty_batch_replay_is_read_only_and_terminal_is_monotonic(tmp_path: Path) -> None:
    store = _ready_store(tmp_path)
    committed = _finalize(store, skills=["once"])
    before = store.runtime_table_counts()

    replay = _finalize(store, draft_text=committed["text"])

    assert replay["action"] == "accept"
    assert replay["evidence_receipt"]["outcome"] == "replay"
    assert replay["evidence_receipt"]["item_count"] == 0
    assert (
        replay["evidence_receipt"]["finalization_event_id"]
        == committed["evidence_receipt"]["finalization_event_id"]
    )
    assert store.runtime_table_counts() == before
    with pytest.raises(FinalizationEvidenceConflictError, match="terminal turns"):
        _finalize(store, draft_text=committed["text"], skills=["late"])
    assert store.runtime_table_counts() == before
