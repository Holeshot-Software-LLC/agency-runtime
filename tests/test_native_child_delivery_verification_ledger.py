"""Adversarial tests for the durable one-use native-child proof ledger."""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest

from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)
from agency_runtime.core.store.schema import (
    NATIVE_CHILD_DELIVERY_VERIFICATION_TRIGGER_SQL,
    SCHEMA_VERSION,
)
from agency_runtime.core.store.sqlite import (
    Store,
    _native_child_delivery_verification_schema_is_current,
)


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _decision(
    *,
    host: str = "claude",
    session_id: str = "parent-session",
    trace_id: str = "parent-trace",
    launch_id: str = "tool-use-1",
    binding_kind: str = "launch_id",
    binding_id: str | None = None,
    nonce: str = "nonce-1",
    slug: str = "security-reviewer",
) -> dict[str, Any]:
    issued = datetime(2026, 8, 12, 17, 0, tzinfo=timezone.utc)
    attempts = [
        {
            "provider_name": "selector",
            "provider_type": "openai",
            "requested_model": "gpt-test",
            "model_group": "",
            "actual_model": "",
            "model_receipt_source": "unavailable",
            "status": "applied",
            "reason_code": "",
        }
    ]
    cards = [
        {
            "specialist_slug": slug,
            "specialist_version": "1.0.0",
            "specialist_prompt_hash": _digest(f"prompt:{slug}"),
            "body_character_length": 6,
        }
    ]
    return {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": host,
        "parent_session_id": session_id,
        "parent_trace_id": trace_id,
        "launch_id": launch_id,
        "binding_kind": binding_kind,
        "binding_id": launch_id if binding_id is None else binding_id,
        "provider_attempts": attempts,
        "provider_receipt_digest": canonical_native_child_provider_receipt_digest(attempts),
        "task_sha256": _digest(f"task:{trace_id}:{launch_id}:{nonce}"),
        "team_digest": _digest(
            json.dumps(
                cards,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        ),
        "candidate_digest": _digest("runtime"),
        "runtime_digest": _digest("runtime"),
        "install_id": "install-1",
        "bundle_digest": _digest("bundle"),
        "issued_at": issued.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": (issued + timedelta(seconds=60))
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "nonce": nonce,
        "cards": cards,
    }


def _record_decision(store: Store, expected: dict[str, Any]) -> tuple[str, str]:
    run_id = store.create_run(
        session_id=expected["parent_session_id"],
        trace_id=expected["parent_trace_id"],
        host=expected["host"],
        user_message="Parent request",
    )
    slugs = [card["specialist_slug"] for card in expected["cards"]]
    decision_id = store.record_routing_decision(
        trace_id=expected["parent_trace_id"],
        session_id=expected["parent_session_id"],
        query_hash=expected["task_sha256"],
        context_fingerprint=_digest(f"context:{expected['parent_trace_id']}"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": slugs,
            "semantic_ids": slugs,
            "companion_ids": [],
            "available_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "native_child_delivery": expected,
        },
    )
    return run_id, decision_id


def _proof(
    expected: dict[str, Any],
    decision_id: str,
    *,
    artifact_digest: str | None = None,
    child_id: str = "child-1",
) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "nonce": expected["nonce"],
        "artifact_digest": artifact_digest or _digest(f"artifact:{decision_id}"),
        "host": expected["host"],
        "parent_session_id": expected["parent_session_id"],
        "parent_trace_id": expected["parent_trace_id"],
        "launch_id": expected["launch_id"],
        "binding_kind": expected["binding_kind"],
        "binding_id": expected["binding_id"],
        "child_id": child_id,
        "cards": deepcopy(expected["cards"]),
    }


def _bind_launch(
    store: Store,
    expected: dict[str, Any],
    *,
    child_id: str = "child-1",
) -> None:
    native_run_id = f"claude-agent:{child_id}"
    store.record_native_child_started(
        host=expected["host"],
        backend="delegate_task",
        session_id=expected["parent_session_id"],
        trace_id=expected["parent_trace_id"],
        worker_id=child_id,
        native_run_id=native_run_id,
    )
    assert (
        store.bind_native_child_launch(
            host=expected["host"],
            session_id=expected["parent_session_id"],
            trace_id=expected["parent_trace_id"],
            worker_id=child_id,
            native_run_id=native_run_id,
            launch_id=expected["launch_id"],
        )
        is True
    )


def _ledger_count(store: Store) -> int:
    conn = store._connect()
    try:
        return int(
            conn.execute("SELECT COUNT(*) FROM native_child_delivery_verifications").fetchone()[0]
        )
    finally:
        conn.close()


def test_current_schema_has_only_bounded_identity_and_one_use_guards(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    conn = store._connect()
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 45
        assert SCHEMA_VERSION == 45
        assert _native_child_delivery_verification_schema_is_current(conn) is True
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(native_child_delivery_verifications)")
        }
        assert columns == {
            "decision_id",
            "nonce",
            "artifact_digest",
            "host",
            "parent_session_id",
            "parent_trace_id",
            "launch_id",
            "binding_kind",
            "binding_id",
            "child_id",
            "verified_at",
        }
        unique_sets = {
            tuple(column["name"] for column in conn.execute(f"PRAGMA index_info({index['name']})"))
            for index in conn.execute("PRAGMA index_list(native_child_delivery_verifications)")
            if index["unique"] == 1
        }
        assert {
            ("nonce",),
            ("artifact_digest",),
            (
                "host",
                "parent_session_id",
                "parent_trace_id",
                "launch_id",
                "binding_kind",
                "binding_id",
            ),
            ("host", "child_id"),
        } <= unique_sets
        triggers = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                "AND tbl_name = 'native_child_delivery_verifications'"
            )
        }
        assert triggers == set(NATIVE_CHILD_DELIVERY_VERIFICATION_TRIGGER_SQL)
        foreign_keys = {
            (row["from"], row["table"], row["to"], row["on_delete"].casefold())
            for row in conn.execute("PRAGMA foreign_key_list(native_child_delivery_verifications)")
        }
        assert ("decision_id", "routing_decisions", "id", "cascade") in foreign_keys
    finally:
        conn.close()


@pytest.mark.parametrize("prior_version", [44, 45])
def test_migration_and_current_schema_repair_restore_the_ledger(
    tmp_path: Path,
    prior_version: int,
) -> None:
    db_path = tmp_path / f"agency-{prior_version}.db"
    store = Store(db_path)
    conn = store._connect()
    try:
        conn.execute("DROP TABLE native_child_delivery_verifications")
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (prior_version,))
        conn.commit()
    finally:
        conn.close()

    repaired = Store(db_path)
    conn = repaired._connect()
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 45
        assert _native_child_delivery_verification_schema_is_current(conn) is True
    finally:
        conn.close()


def test_store_consumes_exact_proof_once_and_returns_explicit_success(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    _bind_launch(store, expected)
    proof = _proof(expected, decision_id)

    receipt = store._record_native_child_delivery_verification(**proof)

    assert receipt["verified_delivery"] is True
    assert receipt["decision_id"] == decision_id
    assert receipt["nonce"] == expected["nonce"]
    assert receipt["artifact_digest"] == proof["artifact_digest"]
    assert receipt["verified_at"].endswith("+00:00")
    assert set(receipt) == {
        "decision_id",
        "nonce",
        "artifact_digest",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "binding_kind",
        "binding_id",
        "child_id",
        "verified_at",
        "verified_delivery",
    }
    assert _ledger_count(store) == 1
    assert "verified_delivery" not in store.get_native_child_staffing_decision(decision_id)

    with pytest.raises(ValueError, match="already consumed"):
        store._record_native_child_delivery_verification(**proof)
    assert _ledger_count(store) == 1


def test_store_exposes_bounded_read_only_receipt_queries(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    _bind_launch(store, expected)
    recorded = store._record_native_child_delivery_verification(**_proof(expected, decision_id))

    assert not hasattr(store, "record_native_child_delivery_verification")
    assert store.get_native_child_delivery_verification(decision_id) == recorded
    assert store.get_native_child_delivery_verification("missing-decision") is None
    assert store.list_native_child_delivery_verifications(limit=1) == [recorded]
    assert store.list_native_child_delivery_verifications(host="claude", limit=1) == [recorded]
    assert store.list_native_child_delivery_verifications(host="zcode", limit=1) == []
    for invalid in (0, 4_097, True):
        with pytest.raises(ValueError, match="between 1 and 4096"):
            store.list_native_child_delivery_verifications(limit=invalid)  # type: ignore[arg-type]


def test_launch_binding_must_join_the_exact_host_reported_child(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    proof = _proof(expected, decision_id)

    with pytest.raises(ValueError, match="host launch binding is unavailable"):
        store._record_native_child_delivery_verification(**proof)

    _bind_launch(store, expected)
    swapped = {**proof, "child_id": "other-child"}
    with pytest.raises(ValueError, match="host launch binding is unavailable"):
        store._record_native_child_delivery_verification(**swapped)

    assert store._record_native_child_delivery_verification(**proof)["verified_delivery"] is True


def test_host_launch_binding_is_idempotent_but_conflicts_fail(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _record_decision(store, expected)
    _bind_launch(store, expected)

    assert (
        store.bind_native_child_launch(
            host="claude",
            session_id=expected["parent_session_id"],
            trace_id=expected["parent_trace_id"],
            worker_id="child-1",
            native_run_id="claude-agent:child-1",
            launch_id=expected["launch_id"],
        )
        is True
    )
    assert (
        store.bind_native_child_launch(
            host="claude",
            session_id=expected["parent_session_id"],
            trace_id=expected["parent_trace_id"],
            worker_id="child-1",
            native_run_id="claude-agent:child-1",
            launch_id="different-launch",
        )
        is False
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("decision_id", "missing-decision"),
        ("nonce", "wrong-nonce"),
        ("artifact_digest", "A" * 64),
        ("host", "zcode"),
        ("parent_session_id", "wrong-session"),
        ("parent_trace_id", "wrong-trace"),
        ("launch_id", "wrong-launch"),
        ("binding_kind", "child_id"),
        ("binding_id", "wrong-binding"),
        ("child_id", True),
    ],
)
def test_store_rejects_missing_or_mismatched_scalar_identity(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    proof = _proof(expected, decision_id)
    proof[field] = replacement

    with pytest.raises(ValueError):
        store._record_native_child_delivery_verification(**proof)
    assert _ledger_count(store) == 0


def test_store_rejects_tampered_route_and_exact_card_descriptor(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE routing_decisions SET selected_ids = '[\"different\"]' WHERE id = ?",
            (decision_id,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="identity does not match"):
        store._record_native_child_delivery_verification(**_proof(expected, decision_id))
    assert _ledger_count(store) == 0

    second = _decision(trace_id="parent-trace-2", nonce="nonce-2", launch_id="tool-use-2")
    _, second_id = _record_decision(store, second)
    proof = _proof(second, second_id, child_id="child-2")
    proof["cards"][0]["body_character_length"] = 5
    with pytest.raises(ValueError, match="card identity"):
        store._record_native_child_delivery_verification(**proof)
    assert _ledger_count(store) == 0


def test_store_accepts_exact_proof_after_normal_parent_completion(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    terminal = _decision()
    _, decision_id = _record_decision(store, terminal)
    _bind_launch(store, terminal)
    revision = store.get_completion_evidence_snapshot(
        "parent-session",
        "parent-trace",
    )["evidence_revision"]
    finalized = store.commit_terminal_finalization(
        session_id="parent-session",
        trace_id="parent-trace",
        host="claude",
        action="accept",
        response_hash=_digest("response"),
        status="completed",
        expected_evidence_revision=revision,
    )
    assert finalized["authoritative"] is True

    receipt = store._record_native_child_delivery_verification(**_proof(terminal, decision_id))

    assert receipt["verified_delivery"] is True
    assert _ledger_count(store) == 1


def test_store_rejects_a_route_projected_after_terminal_completion(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    terminal = _decision()
    _, decision_id = _record_decision(store, terminal)
    assert store.close_turn_evidence("parent-session", "parent-trace") == 1
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE routing_decisions SET created_at = '2100-01-01T00:00:00+00:00' WHERE id = ?",
            (decision_id,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="identity does not match"):
        store._record_native_child_delivery_verification(**_proof(terminal, decision_id))
    assert _ledger_count(store) == 0


def test_store_rejects_missing_parent_correlation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    missing = _decision(trace_id="missing-trace", launch_id="tool-use-2", nonce="nonce-2")
    _, missing_id = _record_decision(store, missing)
    raw = sqlite3.connect(store.db_path)
    try:
        raw.execute("PRAGMA foreign_keys = OFF")
        raw.execute("DELETE FROM runs WHERE trace_id = ?", (missing["parent_trace_id"],))
        raw.commit()
    finally:
        raw.close()
    with pytest.raises(ValueError, match="identity does not match"):
        store._record_native_child_delivery_verification(**_proof(missing, missing_id))
    assert _ledger_count(store) == 0


@pytest.mark.parametrize("collision", ["nonce", "artifact", "launch_binding", "child"])
def test_store_rejects_every_cross_decision_replay_identity(
    tmp_path: Path,
    collision: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    first = _decision()
    _, first_id = _record_decision(store, first)
    _bind_launch(store, first)
    first_proof = _proof(first, first_id, artifact_digest=_digest("artifact-1"), child_id="child-1")
    store._record_native_child_delivery_verification(**first_proof)

    second_kwargs: dict[str, Any] = {
        "session_id": "parent-session-2",
        "trace_id": "parent-trace-2",
        "launch_id": "tool-use-2",
        "binding_id": "tool-use-2",
        "nonce": "nonce-2",
    }
    if collision == "nonce":
        second_kwargs["nonce"] = first["nonce"]
    elif collision == "launch_binding":
        second_kwargs.update(
            session_id=first["parent_session_id"],
            trace_id=first["parent_trace_id"],
            launch_id=first["launch_id"],
            binding_id=first["binding_id"],
        )
    second = _decision(**second_kwargs)
    if collision == "launch_binding":
        with pytest.raises(
            ValueError,
            match="native_child launch already has a successful routing decision",
        ):
            _record_decision(store, second)
        assert _ledger_count(store) == 1
        return
    _, second_id = _record_decision(store, second)
    if collision not in {"launch_binding", "child"}:
        _bind_launch(store, second, child_id="child-2")
    second_proof = _proof(
        second,
        second_id,
        artifact_digest=(
            first_proof["artifact_digest"] if collision == "artifact" else _digest("artifact-2")
        ),
        child_id="child-1" if collision == "child" else "child-2",
    )

    with pytest.raises(ValueError):
        store._record_native_child_delivery_verification(**second_proof)
    assert _ledger_count(store) == 1


def test_child_id_binding_must_equal_the_host_child_identity(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision(
        binding_kind="child_id",
        binding_id="bound-child",
    )
    _, decision_id = _record_decision(store, expected)

    with pytest.raises(ValueError, match="child binding"):
        store._record_native_child_delivery_verification(
            **_proof(expected, decision_id, child_id="different-child")
        )
    receipt = store._record_native_child_delivery_verification(
        **_proof(expected, decision_id, child_id="bound-child")
    )
    assert receipt["verified_delivery"] is True


def test_caller_boolean_cannot_establish_or_consume_delivery(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    _bind_launch(store, expected)
    proof = _proof(expected, decision_id)

    with pytest.raises(TypeError):
        store._record_native_child_delivery_verification(  # type: ignore[call-arg]
            **proof,
            verified_delivery=True,
        )
    assert _ledger_count(store) == 0


def test_concurrent_consumers_have_exactly_one_winner(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    _bind_launch(store, expected)
    proof = _proof(expected, decision_id)
    barrier = Barrier(2)

    def consume() -> object:
        barrier.wait()
        try:
            return store._record_native_child_delivery_verification(**proof)
        except ValueError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: consume(), range(2)))

    assert sum(isinstance(item, dict) for item in outcomes) == 1
    assert sum(isinstance(item, ValueError) for item in outcomes) == 1
    assert _ledger_count(store) == 1


def test_ledger_update_is_rejected_and_route_deletion_cascades(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    _bind_launch(store, expected)
    store._record_native_child_delivery_verification(**_proof(expected, decision_id))
    conn = store._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE native_child_delivery_verifications SET child_id = 'other'")
        conn.rollback()
        conn.execute("DELETE FROM routing_decisions WHERE id = ?", (decision_id,))
        conn.commit()
    finally:
        conn.close()
    assert _ledger_count(store) == 0


def test_runtime_trim_removes_delivery_audit_with_its_routing_decision(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    _, decision_id = _record_decision(store, expected)
    _bind_launch(store, expected)
    assert store.close_turn_evidence("parent-session", "parent-trace") == 1
    store._record_native_child_delivery_verification(**_proof(expected, decision_id))

    report = store.trim_runtime_tables(keep_last=0, vacuum=False)

    assert report["tables"]["routing_decisions"]["deleted"] == 1
    assert _ledger_count(store) == 0
