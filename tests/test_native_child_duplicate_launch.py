"""Atomic replay guards for inference-owned native-child launches."""

from __future__ import annotations

import json
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
from agency_runtime.core.store.sqlite import Store


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _delivery(
    *,
    host: str = "claude",
    session_id: str = "parent-session",
    trace_id: str = "parent-trace",
    launch_id: str = "launch-1",
    nonce: str = "nonce-1",
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
            "specialist_slug": "security-reviewer",
            "specialist_version": "1.0.0",
            "specialist_prompt_hash": _digest("prompt"),
            "body_character_length": 6,
        }
    ]
    return {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": host,
        "parent_session_id": session_id,
        "parent_trace_id": trace_id,
        "launch_id": launch_id,
        "binding_kind": "launch_id",
        "binding_id": launch_id,
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


def _routing(delivery: object) -> dict[str, Any]:
    return {
        "status": "applied",
        "semantic_status": "applied",
        "source": "native_child_inference",
        "selected_ids": ["security-reviewer"],
        "semantic_ids": ["security-reviewer"],
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
        "native_child_delivery": delivery,
    }


def _record(store: Store, delivery: dict[str, Any]) -> str:
    return store.record_routing_decision(
        trace_id=delivery["parent_trace_id"],
        session_id=delivery["parent_session_id"],
        query_hash=delivery["task_sha256"],
        context_fingerprint=_digest(f"context:{delivery['nonce']}"),
        decision=_routing(delivery),
    )


def _create_parent(store: Store, delivery: dict[str, Any]) -> None:
    store.create_run(
        session_id=delivery["parent_session_id"],
        trace_id=delivery["parent_trace_id"],
        host=delivery["host"],
        user_message="Parent request",
    )


def _routing_count(store: Store) -> int:
    conn = store._connect()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM routing_decisions").fetchone()[0])
    finally:
        conn.close()


def test_sequential_native_child_launch_replay_is_rejected(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    first = _delivery()
    _create_parent(store, first)
    _record(store, first)

    replay = _delivery(nonce="nonce-replay")
    with pytest.raises(
        ValueError,
        match="native_child launch already has a successful routing decision",
    ):
        _record(store, replay)

    assert _routing_count(store) == 1


def test_concurrent_native_child_launch_has_exactly_one_winner(tmp_path: Path) -> None:
    db_path = tmp_path / "agency.db"
    bootstrap = Store(db_path)
    _create_parent(bootstrap, _delivery())
    stores = (Store(db_path), Store(db_path))
    barrier = Barrier(2)

    def attempt(index: int) -> tuple[str, str]:
        barrier.wait(timeout=5)
        try:
            return "recorded", _record(stores[index], _delivery(nonce=f"nonce-{index}"))
        except ValueError as exc:
            return "rejected", str(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, range(2)))

    assert sorted(outcome for outcome, _detail in outcomes) == ["recorded", "rejected"]
    assert [detail for outcome, detail in outcomes if outcome == "rejected"] == [
        "native_child launch already has a successful routing decision"
    ]
    assert _routing_count(bootstrap) == 1


@pytest.mark.parametrize(
    "replacement",
    [
        {"host": "codex"},
        {"launch_id": "launch-2"},
        {"trace_id": "parent-trace-2"},
        {"session_id": "parent-session-2", "trace_id": "parent-trace-2"},
    ],
)
def test_distinct_native_child_launch_scopes_are_accepted(
    tmp_path: Path,
    replacement: dict[str, str],
) -> None:
    store = Store(tmp_path / "agency.db")
    first = _delivery()
    _create_parent(store, first)
    first_id = _record(store, first)
    second = _delivery(nonce="nonce-2", **replacement)
    if second["parent_trace_id"] != first["parent_trace_id"]:
        _create_parent(store, second)

    second_id = _record(store, second)

    assert second_id != first_id
    assert _routing_count(store) == 2


def test_malformed_native_child_delivery_is_rejected(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _delivery()
    _create_parent(store, expected)

    with pytest.raises(
        ValueError,
        match="native_child_inference requires a valid native_child_delivery",
    ):
        store.record_routing_decision(
            trace_id=expected["parent_trace_id"],
            session_id=expected["parent_session_id"],
            query_hash=expected["task_sha256"],
            context_fingerprint=_digest("malformed-context"),
            decision=_routing({"schema": "invalid"}),
        )

    assert _routing_count(store) == 0


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("parent_session_id", "different-session"),
        ("parent_trace_id", "different-trace"),
    ],
)
def test_delivery_must_match_outer_routing_scope(
    tmp_path: Path,
    field: str,
    replacement: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _delivery()
    _create_parent(store, expected)
    mismatched = deepcopy(expected)
    mismatched[field] = replacement

    with pytest.raises(
        ValueError,
        match="native_child_delivery does not match routing session and trace",
    ):
        store.record_routing_decision(
            trace_id=expected["parent_trace_id"],
            session_id=expected["parent_session_id"],
            query_hash=expected["task_sha256"],
            context_fingerprint=_digest(f"mismatch:{field}"),
            decision=_routing(mismatched),
        )

    assert _routing_count(store) == 0


def test_general_and_failed_native_child_routing_remain_repeatable(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    common = {
        "trace_id": "general-trace",
        "session_id": "general-session",
        "query_hash": _digest("query"),
        "context_fingerprint": _digest("context"),
    }
    computed = {"status": "applied", "source": "computed"}
    failures = {"status": "inference_invalid", "source": "native_child_inference_failure"}

    ids = [
        store.record_routing_decision(**common, decision=computed),
        store.record_routing_decision(**common, decision=computed),
        store.record_routing_decision(**common, decision=failures),
        store.record_routing_decision(**common, decision=failures),
    ]

    assert len(set(ids)) == 4
    assert _routing_count(store) == 4
