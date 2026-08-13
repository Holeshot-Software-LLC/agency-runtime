"""Atomic replay guards for inference-owned native-child launches."""

from __future__ import annotations

import json
from collections.abc import Callable
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
    task_sha256 = delivery.get("task_sha256", "") if isinstance(delivery, dict) else ""
    nonce = delivery.get("nonce", "") if isinstance(delivery, dict) else ""
    context_fingerprint = _digest(f"context:{nonce}")
    return {
        "status": "applied",
        "semantic_status": "applied",
        "source": "native_child_inference",
        "selected_ids": ["security-reviewer"],
        "semantic_ids": ["security-reviewer"],
        "companion_ids": [],
        "available_companion_ids": [],
        "unavailable_companion_ids": [],
        "confidence": 0.9,
        "latency_ms": 12,
        "provider": "selector",
        "candidate_count": 1,
        "top_score": 0.0,
        "native_child_reason": "applied",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": "inferred",
        "source_message_hash": task_sha256,
        "query_hash": task_sha256,
        "context_fingerprint": context_fingerprint,
        "native_child_delivery": delivery,
    }


def _record(
    store: Store,
    delivery: dict[str, Any],
    *,
    final_delivery_validator: Callable[[], bool] | None = None,
) -> str:
    options: dict[str, Any] = {}
    if final_delivery_validator is not None:
        options = {
            "require_open_run": True,
            "final_delivery_validator": final_delivery_validator,
        }
    return store.record_routing_decision(
        trace_id=delivery["parent_trace_id"],
        session_id=delivery["parent_session_id"],
        query_hash=delivery["task_sha256"],
        context_fingerprint=_digest(f"context:{delivery['nonce']}"),
        decision=_routing(delivery),
        **options,
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


def _applied_native_child_count(store: Store) -> int:
    conn = store._connect()
    try:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM routing_decisions "
                "WHERE source = 'native_child_inference' AND status = 'applied'"
            ).fetchone()[0]
        )
    finally:
        conn.close()


def test_final_delivery_validation_rolls_back_and_exact_launch_can_retry(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    callback_observations: list[int] = []

    def reject_before_commit() -> bool:
        callback_observations.append(_applied_native_child_count(store))
        return False

    with pytest.raises(
        ValueError,
        match="final native-child delivery validation failed",
    ):
        _record(
            store,
            delivery,
            final_delivery_validator=reject_before_commit,
        )

    assert callback_observations == [0]
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0

    retry_id = _record(
        store,
        delivery,
        final_delivery_validator=lambda: True,
    )

    assert retry_id
    assert _routing_count(store) == 1
    assert _applied_native_child_count(store) == 1


@pytest.mark.parametrize("invalid_result", [None, 1, "true"])
def test_final_delivery_validation_requires_literal_true_and_rolls_back(
    tmp_path: Path,
    invalid_result: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)

    with pytest.raises(
        ValueError,
        match="final native-child delivery validation failed",
    ):
        _record(
            store,
            delivery,
            final_delivery_validator=lambda: invalid_result,  # type: ignore[return-value]
        )

    assert _applied_native_child_count(store) == 0


def test_final_delivery_validation_exception_rolls_back(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)

    def fail_validation() -> bool:
        raise RuntimeError("transcript changed")

    with pytest.raises(RuntimeError, match="transcript changed"):
        _record(
            store,
            delivery,
            final_delivery_validator=fail_validation,
        )

    assert _applied_native_child_count(store) == 0


def test_exact_inserted_route_readback_mismatch_rolls_back_before_callback(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=_digest("mismatched-task"),
            context_fingerprint=_digest("mismatched-route-context"),
            decision=_routing(delivery),
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("semantic_status", "inference_invalid"),
        ("native_child_reason", "native_child_delivery_invalid"),
        ("inference_configured", False),
        ("inference_required", False),
        ("inference_attempted", False),
        ("inference_mode", "unavailable"),
        ("selected_ids", ["different-specialist"]),
        ("semantic_ids", ["different-specialist"]),
        ("companion_ids", ["invented-companion"]),
        ("available_companion_ids", ["invented-companion"]),
        ("unavailable_companion_ids", ["invented-companion"]),
    ],
)
def test_contradictory_native_child_success_projection_rolls_back_before_callback(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    decision = _routing(delivery)
    decision[field] = replacement
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=delivery["task_sha256"],
            context_fingerprint=_digest(f"context:{delivery['nonce']}"),
            decision=decision,
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0


@pytest.mark.parametrize(
    "field",
    ["source_message_hash", "query_hash", "context_fingerprint"],
)
def test_native_child_inner_digest_mismatch_rolls_back_before_callback(
    tmp_path: Path,
    field: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    decision = _routing(delivery)
    decision[field] = _digest(f"contradictory:{field}")
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=delivery["task_sha256"],
            context_fingerprint=_digest(f"context:{delivery['nonce']}"),
            decision=decision,
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0


def test_route_provider_must_match_applied_attempt_and_exact_launch_can_retry(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    decision = _routing(delivery)
    decision["provider"] = "contradictory-provider"
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=delivery["task_sha256"],
            context_fingerprint=_digest(f"context:{delivery['nonce']}"),
            decision=decision,
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0

    retried = _record(
        store,
        delivery,
        final_delivery_validator=lambda: True,
    )
    assert retried
    assert _routing_count(store) == 1
    assert _applied_native_child_count(store) == 1


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("confidence", -1.0),
        ("confidence", 2.0),
        ("candidate_count", 0),
        ("top_score", -0.1),
        ("top_score", 0.9),
    ],
)
def test_native_child_success_numeric_contract_rolls_back_and_retries(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    decision = _routing(delivery)
    decision[field] = replacement
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=delivery["task_sha256"],
            context_fingerprint=_digest(f"context:{delivery['nonce']}"),
            decision=decision,
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0
    assert _record(store, delivery, final_delivery_validator=lambda: True)


def test_exact_native_child_success_projection_reaches_callback_and_commits(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    callback_calls = 0

    def final_validator() -> bool:
        nonlocal callback_calls
        callback_calls += 1
        return True

    decision_id = _record(
        store,
        delivery,
        final_delivery_validator=final_validator,
    )

    assert decision_id
    assert callback_calls == 1
    assert _routing_count(store) == 1
    assert _applied_native_child_count(store) == 1


def test_concurrent_validated_native_child_launch_has_exactly_one_winner(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "agency.db"
    bootstrap = Store(db_path)
    _create_parent(bootstrap, _delivery(host="codex"))
    stores = (Store(db_path), Store(db_path))
    barrier = Barrier(2)
    validation_calls: list[int] = []

    def attempt(index: int) -> tuple[str, str]:
        barrier.wait(timeout=5)

        def validate() -> bool:
            validation_calls.append(index)
            return True

        try:
            decision_id = _record(
                stores[index],
                _delivery(host="codex", nonce=f"nonce-{index}"),
                final_delivery_validator=validate,
            )
            return "recorded", decision_id
        except ValueError as exc:
            return "rejected", str(exc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, range(2)))

    assert sorted(outcome for outcome, _detail in outcomes) == ["recorded", "rejected"]
    assert [detail for outcome, detail in outcomes if outcome == "rejected"] == [
        "native_child launch already has a successful routing decision"
    ]
    assert len(validation_calls) == 1
    assert _applied_native_child_count(bootstrap) == 1


def test_final_delivery_validator_is_restricted_to_open_native_child_routes(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    common = {
        "trace_id": delivery["parent_trace_id"],
        "session_id": delivery["parent_session_id"],
        "query_hash": delivery["task_sha256"],
        "context_fingerprint": _digest("restricted-callback"),
        "final_delivery_validator": lambda: True,
    }

    with pytest.raises(
        ValueError,
        match="final_delivery_validator requires open native-child inference",
    ):
        store.record_routing_decision(
            **common,
            require_open_run=True,
            decision={"status": "applied", "source": "computed"},
        )
    with pytest.raises(
        ValueError,
        match="final_delivery_validator requires open native-child inference",
    ):
        store.record_routing_decision(
            **common,
            require_open_run=False,
            decision=_routing(delivery),
        )

    assert _routing_count(store) == 0


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
        {
            "host": "codex",
            "session_id": "parent-session-codex",
            "trace_id": "parent-trace-codex",
        },
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


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("fallback_applied", True),
        ("fallback_companion_ids", ["invented-fallback"]),
        ("companion_actions", ["invented-action"]),
        ("continuation_reused", True),
        ("origin_trace_id", "contradictory-origin"),
        ("origin_query_hash", "0" * 64),
        ("origin_context_fingerprint", "1" * 64),
        ("trace_id", "contradictory-inner-trace"),
        (
            "work_units",
            {"delegate": True, "count": 1, "confidence": "high", "source": "test"},
        ),
    ],
)
def test_extra_native_child_success_projection_rolls_back_before_callback(
    tmp_path: Path,
    field: str,
    replacement: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    _create_parent(store, delivery)
    decision = _routing(delivery)
    decision[field] = replacement
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=delivery["task_sha256"],
            context_fingerprint=_digest(f"context:{delivery['nonce']}"),
            decision=decision,
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0


def test_native_child_delivery_host_must_match_open_parent_before_callback(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    delivery = _delivery(host="codex")
    store.create_run(
        session_id=delivery["parent_session_id"],
        trace_id=delivery["parent_trace_id"],
        host="claude",
        user_message="Parent request",
    )
    callback_called = False

    def final_validator() -> bool:
        nonlocal callback_called
        callback_called = True
        return True

    with pytest.raises(
        RuntimeError,
        match="native-child routing projection failed transactional readback",
    ):
        store.record_routing_decision(
            trace_id=delivery["parent_trace_id"],
            session_id=delivery["parent_session_id"],
            query_hash=delivery["task_sha256"],
            context_fingerprint=_digest(f"context:{delivery['nonce']}"),
            decision=_routing(delivery),
            require_open_run=True,
            final_delivery_validator=final_validator,
        )

    assert callback_called is False
    assert _routing_count(store) == 0
    assert _applied_native_child_count(store) == 0


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
