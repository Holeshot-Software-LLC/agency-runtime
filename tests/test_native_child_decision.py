"""Fail-closed tests for durable native-child staffing decision projections."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
    project_native_child_staffing_decision,
    project_native_child_success_route,
)
from agency_runtime.core.store.sqlite import Store


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _decision() -> dict[str, object]:
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
    team_digest = _digest(
        json.dumps(cards, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    )
    return {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "claude",
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "launch_id": "tool-use-1",
        "binding_kind": "tool_use_id",
        "binding_id": "tool-use-1",
        "provider_attempts": attempts,
        "provider_receipt_digest": canonical_native_child_provider_receipt_digest(attempts),
        "task_sha256": _digest("task"),
        "team_digest": team_digest,
        "candidate_digest": _digest("runtime"),
        "runtime_digest": _digest("runtime"),
        "install_id": "install-1",
        "bundle_digest": _digest("bundle"),
        "issued_at": issued.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": (issued + timedelta(seconds=60))
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "nonce": "nonce-1",
        "cards": cards,
    }


def _success_route(expected: dict[str, object]) -> dict[str, object]:
    cards = expected["cards"]
    assert isinstance(cards, list)
    slugs = [str(card["specialist_slug"]) for card in cards]
    return {
        "status": "applied",
        "semantic_status": "applied",
        "source": "native_child_inference",
        "selected_ids": slugs,
        "semantic_ids": slugs,
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
        "source_message_hash": str(expected["task_sha256"]),
        "query_hash": str(expected["task_sha256"]),
        "context_fingerprint": _digest("context"),
        "native_child_delivery": expected,
    }


def test_projection_preserves_the_exact_content_free_decision() -> None:
    value = _decision()

    assert project_native_child_staffing_decision(value) == value


def test_success_route_requires_neutral_work_units() -> None:
    expected = _decision()
    route = _success_route(expected)
    route["work_units"] = {}
    arguments = {
        "session_id": str(expected["parent_session_id"]),
        "trace_id": str(expected["parent_trace_id"]),
        "query_hash": str(expected["task_sha256"]),
        "context_fingerprint": _digest("context"),
        "host": str(expected["host"]),
    }

    assert project_native_child_success_route(route, **arguments) == expected

    route["work_units"] = {"delegate": True}
    assert project_native_child_success_route(route, **arguments) is None


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("schema", "legacy"),
        ("host", "unknown"),
        ("parent_session_id", ""),
        ("launch_id", "bad\nid"),
        ("binding_kind", "Bad-Kind"),
        ("provider_receipt_digest", "0" * 64),
        ("task_sha256", "not-a-digest"),
        ("team_digest", "1" * 64),
        ("runtime_digest", "2" * 64),
        ("install_id", ""),
        ("bundle_digest", "bad"),
        ("nonce", ""),
    ],
)
def test_projection_rejects_each_tampered_binding(field: str, replacement: object) -> None:
    value = _decision()
    value[field] = replacement

    assert project_native_child_staffing_decision(value) is None


def test_projection_rejects_missing_extra_duplicate_and_partial_cards() -> None:
    value = _decision()
    value["extra"] = True
    assert project_native_child_staffing_decision(value) is None

    value = _decision()
    value["cards"] = []
    assert project_native_child_staffing_decision(value) is None

    value = _decision()
    cards = deepcopy(value["cards"])
    assert isinstance(cards, list)
    cards.append(deepcopy(cards[0]))
    value["cards"] = cards
    assert project_native_child_staffing_decision(value) is None

    value = _decision()
    cards = deepcopy(value["cards"])
    assert isinstance(cards, list)
    cards[0]["body_character_length"] = 5
    value["cards"] = cards
    assert project_native_child_staffing_decision(value) is None


def test_projection_rejects_no_multiple_or_nonterminal_applied_provider_receipts() -> None:
    for attempts in (
        [],
        [{"provider_name": "one", "status": "failed"}],
        [
            {"provider_name": "one", "status": "applied"},
            {"provider_name": "two", "status": "applied"},
        ],
        [
            {"provider_name": "one", "status": "applied"},
            {"provider_name": "two", "status": "failed"},
        ],
    ):
        value = _decision()
        value["provider_attempts"] = attempts
        value["provider_receipt_digest"] = canonical_native_child_provider_receipt_digest(attempts)
        assert project_native_child_staffing_decision(value) is None


def test_projection_rejects_noncanonical_or_overlong_validity_windows() -> None:
    value = _decision()
    value["issued_at"] = "2026-08-12T17:00:00+00:00"
    assert project_native_child_staffing_decision(value) is None

    value = _decision()
    value["expires_at"] = "2026-08-12T17:06:00Z"
    assert project_native_child_staffing_decision(value) is None


def test_store_resolves_the_exact_decision_without_calling_it_delivery(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    store.create_run(
        session_id=str(expected["parent_session_id"]),
        trace_id=str(expected["parent_trace_id"]),
        host=str(expected["host"]),
        user_message="Parent request",
    )
    decision_id = store.record_routing_decision(
        trace_id=str(expected["parent_trace_id"]),
        session_id=str(expected["parent_session_id"]),
        query_hash=str(expected["task_sha256"]),
        context_fingerprint=_digest("context"),
        decision=_success_route(expected),
    )

    resolved = store.get_native_child_staffing_decision(decision_id)

    assert resolved is not None
    assert resolved["decision_id"] == decision_id
    assert resolved["cards"] == expected["cards"]
    assert "verified_delivery" not in resolved


@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        ("selected_ids", '["different"]'),
        ("confidence", 0.1),
        ("latency_ms", 999),
        ("provider", "different-provider"),
        ("created_at", ""),
        ("created_at", "bogus"),
        ("created_at", " "),
        ("created_at", "!"),
        ("created_at", "9999-99-99T99:99:99.999000+00:00"),
        ("created_at", "2026-08-13T00:00:00.123456+00:00"),
    ],
)
def test_store_rejects_a_route_column_that_no_longer_matches_its_decision(
    tmp_path: Path,
    column: str,
    replacement: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    store.create_run(
        session_id=str(expected["parent_session_id"]),
        trace_id=str(expected["parent_trace_id"]),
        host=str(expected["host"]),
        user_message="Parent request",
    )
    decision_id = store.record_routing_decision(
        trace_id=str(expected["parent_trace_id"]),
        session_id=str(expected["parent_session_id"]),
        query_hash=str(expected["task_sha256"]),
        context_fingerprint=_digest("context"),
        decision=_success_route(expected),
    )
    conn = store._connect()
    try:
        statement = {
            "selected_ids": "UPDATE routing_decisions SET selected_ids = ? WHERE id = ?",
            "confidence": "UPDATE routing_decisions SET confidence = ? WHERE id = ?",
            "latency_ms": "UPDATE routing_decisions SET latency_ms = ? WHERE id = ?",
            "provider": "UPDATE routing_decisions SET provider = ? WHERE id = ?",
            "created_at": "UPDATE routing_decisions SET created_at = ? WHERE id = ?",
        }[column]
        conn.execute(statement, (replacement, decision_id))
        conn.commit()
    finally:
        conn.close()

    assert store.get_native_child_staffing_decision(decision_id) is None


@pytest.mark.parametrize("tamper", ["extra-field", "work-units"])
def test_store_rejects_nonexact_native_child_success_rows(
    tmp_path: Path,
    tamper: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    expected = _decision()
    store.create_run(
        session_id=str(expected["parent_session_id"]),
        trace_id=str(expected["parent_trace_id"]),
        host=str(expected["host"]),
        user_message="Parent request",
    )
    decision_id = store.record_routing_decision(
        trace_id=str(expected["parent_trace_id"]),
        session_id=str(expected["parent_session_id"]),
        query_hash=str(expected["task_sha256"]),
        context_fingerprint=_digest("context"),
        decision=_success_route(expected),
    )
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT decision FROM routing_decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()
        assert row is not None
        persisted = json.loads(row["decision"])
        work_units = "{}"
        if tamper == "extra-field":
            persisted["fallback_applied"] = True
        else:
            persisted["work_units"] = {
                "delegate": True,
                "count": 1,
                "confidence": "high",
                "source": "test",
            }
            work_units = json.dumps(persisted["work_units"])
        conn.execute(
            "UPDATE routing_decisions SET decision = ?, work_units = ? WHERE id = ?",
            (json.dumps(persisted, sort_keys=True), work_units, decision_id),
        )
        conn.commit()
    finally:
        conn.close()

    assert store.get_native_child_staffing_decision(decision_id) is None
