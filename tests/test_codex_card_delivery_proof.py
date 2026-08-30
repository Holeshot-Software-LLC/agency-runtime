"""Direct coverage for Codex host-authored child card-delivery proof.

The Store, stdout, and collaboration projections are Agency or harness authored.
They can prove routing and lifecycle, but only a verified bounded projection of
the host-written child artifact can prove that the exact card reached the child
before it spoke.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

import pytest

from agency_runtime.core.canary_proof import (
    _codex_host_child_delivery_failures,
    codex_activation_failures,
)
from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)

RESPONSE = "Agency/Agencies loaded: code-reviewer"
RESPONSE_HASH = hashlib.sha256(RESPONSE.encode("utf-8")).hexdigest()
SESSION = PARENT = "parent-thread"
TRACE = "canary-trace"
QUERY_HASH = "a" * 64
RECEIVER = "019fb000-1111-7222-8333-444455556666"
PROMPT_HASH = "b" * 64
RUNTIME_DIGEST = "c" * 64
BUNDLE_DIGEST = "d" * 64
ARTIFACT_DIGEST = "e" * 64
PARENT_DECISION_ID = "decision-canary-parent"
DECISION_ID = "decision-inference-child"
LAUNCH_ID = "launch-child-1"
NONCE = "nonce-1"
PROVIDER_ATTEMPTS = [
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
PROVIDER_DIGEST = canonical_native_child_provider_receipt_digest(PROVIDER_ATTEMPTS)
assert PROVIDER_DIGEST is not None


def _result() -> dict[str, Any]:
    """One direct spawn plus one completed wait -- lifecycle, not delivery."""

    return {
        "collaboration": {
            "unexpected_item_count": 0,
            "unexpected_item_types": [],
            "calls": [
                {
                    "tool": "spawn_agent",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": PARENT,
                    "receiver_thread_ids": [RECEIVER],
                    "execution_delivery": {"native_task_name": "agency_task"},
                },
                {
                    "tool": "wait",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": PARENT,
                    "receiver_thread_ids": [RECEIVER],
                    "agents_states": {RECEIVER: "completed"},
                },
            ],
        }
    }


def _team_digest(cards: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(
            cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _host_child_delivery() -> dict[str, Any]:
    cards = [
        {
            "specialist_slug": "code-reviewer",
            "specialist_version": "v1",
            "specialist_prompt_hash": PROMPT_HASH,
            "body_character_length": 1024,
        }
    ]
    # Unit tests exercise the bounded projection validator directly. Production
    # canary evaluation accepts this shape only after a sealed collector
    # capability has projected it; putting the same mapping in Store evidence
    # is deliberately non-authoritative.
    return {
        "schema": "agency.host-child-delivery-proof.v1",
        "verified_delivery": True,
        "host": "codex",
        "parent_session_id": PARENT,
        "parent_trace_id": TRACE,
        "launch_id": LAUNCH_ID,
        "child_id": RECEIVER,
        "pre_speech": True,
        "cards": cards,
        "artifact_digest": ARTIFACT_DIGEST,
        "decision_id": DECISION_ID,
        "provider_receipt_digest": PROVIDER_DIGEST,
        "task_sha256": QUERY_HASH,
        "team_digest": _team_digest(cards),
        "candidate_digest": RUNTIME_DIGEST,
        "runtime_digest": RUNTIME_DIGEST,
        "install_id": "codex-install-1",
        "bundle_digest": BUNDLE_DIGEST,
        "issued_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:05:00Z",
        "nonce": NONCE,
        "binding_kind": "child_id",
        "binding_id": RECEIVER,
    }


def _native_child_route() -> dict[str, Any]:
    proof = _host_child_delivery()
    return {
        "decision_id": DECISION_ID,
        "trace_id": TRACE,
        "session_id": SESSION,
        "query_hash": QUERY_HASH,
        "context_fingerprint": "f" * 64,
        "created_at": "2026-08-09T00:00:00Z",
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "codex",
        "parent_session_id": SESSION,
        "parent_trace_id": TRACE,
        "launch_id": LAUNCH_ID,
        "binding_kind": "child_id",
        "binding_id": RECEIVER,
        "provider_attempts": PROVIDER_ATTEMPTS,
        "provider_receipt_digest": PROVIDER_DIGEST,
        "task_sha256": QUERY_HASH,
        "team_digest": proof["team_digest"],
        "candidate_digest": RUNTIME_DIGEST,
        "runtime_digest": RUNTIME_DIGEST,
        "install_id": "codex-install-1",
        "bundle_digest": BUNDLE_DIGEST,
        "issued_at": "2026-08-09T00:00:00Z",
        "expires_at": "2026-08-09T00:05:00Z",
        "nonce": NONCE,
        "cards": proof["cards"],
    }


def _native_child_delivery() -> dict[str, Any]:
    return {
        "decision_id": DECISION_ID,
        "nonce": NONCE,
        "artifact_digest": ARTIFACT_DIGEST,
        "host": "codex",
        "parent_session_id": SESSION,
        "parent_trace_id": TRACE,
        "launch_id": LAUNCH_ID,
        "binding_kind": "child_id",
        "binding_id": RECEIVER,
        "child_id": RECEIVER,
        "verified_at": "2026-08-09T00:00:01Z",
        "verified_delivery": True,
    }


def _evidence(**overrides: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "agency.canary-activation-evidence.v1",
        "proven": True,
        "session_id": SESSION,
        "trace_id": TRACE,
        "query_hash": QUERY_HASH,
        "cardinalities": {
            "routes": 1,
            "native_child_routes": 1,
            "native_child_deliveries": 1,
            "runs": 1,
            "traces": 1,
            "worker_runs": 1,
            "specialist_loads": 1,
            "finalizations": 1,
        },
        "run": {
            "status": "completed",
            "ended_at": "2026-08-09T00:00:01+00:00",
            "terminal_finalization_id": "final-1",
        },
        "route": {
            "id": PARENT_DECISION_ID,
            "session_id": SESSION,
            "trace_id": TRACE,
            "selected_ids": ["code-reviewer"],
            "companion_ids": [],
            "query_hash": QUERY_HASH,
        },
        "native_child_route": _native_child_route(),
        "native_child_delivery": _native_child_delivery(),
        "worker_runs": [
            {
                "worker_id": RECEIVER,
                "native_run_id": f"codex-agent:{RECEIVER}",
                "backend": "spawn_agent",
                "host": "codex",
                "started_at": "2026-08-09T00:00:00+00:00",
                "ended_at": "2026-08-09T00:00:01+00:00",
            }
        ],
        # This Agency-authored row is diagnostic and deliberately non-authoritative.
        "specialist_loads": [
            {"agent_slug": "code-reviewer", "session_id": SESSION, "trace_id": TRACE}
        ],
        "finalizations": [
            {
                "id": "final-1",
                "action": "accept",
                "terminal_status": "completed",
                "response_hash": RESPONSE_HASH,
            }
        ],
    }
    evidence.update(overrides)
    return evidence


def _failures(**overrides: Any) -> tuple[str, ...]:
    host_child_delivery = overrides.pop("host_child_delivery", _host_child_delivery())
    return codex_activation_failures(
        result=_result(),
        evidence=_evidence(**overrides),
        response_hash=RESPONSE_HASH,
        host_child_delivery=host_child_delivery,
    )


def _card(slug: str, *, prompt_hash: str = PROMPT_HASH) -> dict[str, Any]:
    return {
        "specialist_slug": slug,
        "specialist_version": "v1",
        "specialist_prompt_hash": prompt_hash,
        "body_character_length": 1024,
    }


def _host_join_failures(
    *,
    parent_selected: list[str],
    parent_companions: list[str],
    native_cards: list[dict[str, Any]],
) -> tuple[str, ...]:
    proof = _host_child_delivery()
    proof["cards"] = deepcopy(native_cards)
    proof["team_digest"] = _team_digest(native_cards)
    native_route = _native_child_route()
    native_route["cards"] = deepcopy(native_cards)
    native_route["team_digest"] = _team_digest(native_cards)
    evidence = _evidence(native_child_route=native_route)
    parent_route = deepcopy(evidence["route"])
    parent_route["selected_ids"] = parent_selected
    parent_route["companion_ids"] = parent_companions
    spawn = _result()["collaboration"]["calls"][0]
    return _codex_host_child_delivery_failures(
        evidence=evidence,
        host_child_delivery=proof,
        parent_route=parent_route,
        spawn=spawn,
        receiver_id=RECEIVER,
    )


def test_verified_host_child_delivery_proves_the_canary() -> None:
    assert _failures() == ()
    proof = _host_child_delivery()
    assert "launch_id" in proof
    assert "tool_use_id" not in proof


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("native_child_routes", 0),
        ("native_child_routes", 2),
        ("native_child_deliveries", 0),
        ("native_child_deliveries", 2),
    ],
)
def test_canary_requires_exactly_one_child_route_and_verified_delivery(
    field: str,
    value: int,
) -> None:
    evidence = _evidence()
    evidence["cardinalities"][field] = value

    failures = codex_activation_failures(
        result=_result(),
        evidence=evidence,
        response_hash=RESPONSE_HASH,
        host_child_delivery=_host_child_delivery(),
    )

    assert "Codex canary required one complete first-pass card delivery without correction" in (
        failures
    )


@pytest.mark.parametrize(
    "field",
    ["native_child_route", "native_child_delivery", "host_child_delivery"],
)
def test_canary_refuses_a_missing_child_join_projection(field: str) -> None:
    assert "verified host-authored Codex child card delivery was not proven" in _failures(
        **{field: None}
    )


def test_parent_canary_route_is_checked_separately_from_the_child_route() -> None:
    parent_route = deepcopy(_evidence()["route"])
    parent_route["selected_ids"] = ["technical-writer"]

    failures = _failures(route=parent_route)

    assert "the sole routed canary unit was not the expected code-reviewer" in failures


def test_parent_route_cannot_be_inversely_spliced_to_another_valid_child_team() -> None:
    failures = _host_join_failures(
        parent_selected=["code-reviewer"],
        parent_companions=[],
        native_cards=[_card("technical-writer")],
    )

    assert failures == (
        "the inference-owned parent route did not match the exact ordered native child card team",
    )


def test_parent_route_joins_the_complete_multi_card_child_team() -> None:
    cards = [
        _card("code-reviewer"),
        _card("technical-writer", prompt_hash="0" * 64),
    ]

    assert (
        _host_join_failures(
            parent_selected=["code-reviewer"],
            parent_companions=["technical-writer"],
            native_cards=cards,
        )
        == ()
    )


def test_parent_route_rejects_a_reordered_multi_card_child_team() -> None:
    cards = [
        _card("code-reviewer"),
        _card("technical-writer", prompt_hash="0" * 64),
    ]

    failures = _host_join_failures(
        parent_selected=["technical-writer"],
        parent_companions=["code-reviewer"],
        native_cards=cards,
    )

    assert failures == (
        "the inference-owned parent route did not match the exact ordered native child card team",
    )


def test_parent_canary_route_cannot_be_spliced_from_another_session() -> None:
    parent_route = deepcopy(_evidence()["route"])
    parent_route["session_id"] = "other-parent"

    failures = _failures(route=parent_route)

    assert "host-authored Codex child delivery did not match the exact parent and child" in failures


def test_verified_receipt_cannot_be_joined_to_the_wrong_child_route() -> None:
    child_route = _native_child_route()
    child_route["decision_id"] = "other-child-decision"

    failures = _failures(native_child_route=child_route)

    assert "host-authored Codex child proof and receipt bindings did not match" in failures


@pytest.mark.parametrize(
    "field",
    [
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "child_id",
        "decision_id",
        "nonce",
        "artifact_digest",
    ],
)
def test_proof_must_match_the_raw_immutable_delivery_receipt(field: str) -> None:
    receipt = _native_child_delivery()
    receipt[field] = "0" * 64 if field == "artifact_digest" else f"wrong-{field}"

    failures = _failures(native_child_delivery=receipt)

    assert "host-authored Codex child proof and receipt bindings did not match" in failures


def test_store_load_stdout_and_collaboration_alone_cannot_prove_delivery() -> None:
    """Reverse the old synthetic green: every Agency-owned projection still exists."""

    failures = _failures(host_child_delivery=None)

    assert "verified host-authored Codex child card delivery was not proven" in failures


def test_store_evidence_mapping_cannot_self_certify_host_delivery() -> None:
    evidence = _evidence(host_child_delivery=_host_child_delivery())

    failures = codex_activation_failures(
        result=_result(),
        evidence=evidence,
        response_hash=RESPONSE_HASH,
    )

    assert "verified host-authored Codex child card delivery was not proven" in failures


def test_store_specialist_load_is_not_required_or_authoritative() -> None:
    evidence = _evidence()
    evidence["specialist_loads"] = []
    evidence["cardinalities"]["specialist_loads"] = 0

    assert (
        codex_activation_failures(
            result=_result(),
            evidence=evidence,
            response_hash=RESPONSE_HASH,
            host_child_delivery=_host_child_delivery(),
        )
        == ()
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("schema", "agency.host-child-delivery-proof.v0", "not verified"),
        ("verified_delivery", False, "not verified"),
        ("host", "claude", "not verified"),
        ("parent_session_id", "other-parent", "exact parent and child"),
        ("parent_trace_id", "other-trace", "exact parent and child"),
        ("launch_id", "", "identity bindings"),
        ("child_id", "other-child", "exact parent and child"),
        ("pre_speech", False, "not verified"),
        ("cards", [], "bounded card team"),
        ("artifact_digest", "not-a-digest", "identity bindings"),
        ("decision_id", "other-decision", "proof and receipt bindings"),
        ("provider_receipt_digest", "not-a-digest", "identity bindings"),
        ("task_sha256", "not-a-digest", "identity bindings"),
        ("team_digest", "0" * 64, "identity bindings"),
        ("candidate_digest", "0" * 64, "identity bindings"),
        ("runtime_digest", "not-a-digest", "identity bindings"),
        ("install_id", "", "identity bindings"),
        ("bundle_digest", "not-a-digest", "identity bindings"),
        ("issued_at", "not-a-time", "identity bindings"),
        ("expires_at", "2026-08-08T23:59:00Z", "identity bindings"),
        ("nonce", "", "identity bindings"),
        ("binding_kind", "tool_use_id", "correlation bindings"),
        ("binding_id", "other-child", "correlation bindings"),
    ],
)
def test_host_delivery_field_tampering_fails(
    field: str,
    value: object,
    expected: str,
) -> None:
    proof = _host_child_delivery()
    proof[field] = value

    assert any(expected in failure for failure in _failures(host_child_delivery=proof))


def test_host_delivery_rejects_extra_unvalidated_fields() -> None:
    proof = _host_child_delivery()
    proof["trusted_because"] = "Agency said so"

    assert any("invalid contract" in failure for failure in _failures(host_child_delivery=proof))


@pytest.mark.parametrize(
    "mutation",
    [
        {"specialist_slug": "technical-writer"},
        {"specialist_slug": "bad\nslug"},
        {"specialist_version": ""},
        {"specialist_prompt_hash": "0" * 63},
        {"body_character_length": 0},
        {"unexpected": "field"},
    ],
)
def test_host_delivery_rejects_tampered_exact_card_identity(
    mutation: dict[str, str],
) -> None:
    proof = deepcopy(_host_child_delivery())
    proof["cards"][0].update(mutation)

    assert _failures(host_child_delivery=proof)


def test_host_delivery_cards_must_match_route_order_exactly() -> None:
    proof = _host_child_delivery()
    proof["cards"] = [
        *proof["cards"],
        {
            "specialist_slug": "technical-writer",
            "specialist_version": "v1",
            "specialist_prompt_hash": "0" * 64,
            "body_character_length": 2048,
        },
    ]
    proof["team_digest"] = _team_digest(proof["cards"])

    failures = _failures(host_child_delivery=proof)

    assert "host-authored Codex child delivery did not match the exact ordered route" in failures


def test_proof_requires_the_child_lifecycle() -> None:
    failures = _failures(
        worker_runs=[
            {
                "worker_id": RECEIVER,
                "native_run_id": f"codex-agent:{RECEIVER}",
                "backend": "spawn_agent",
                "host": "codex",
                "started_at": "2026-08-09T00:00:00+00:00",
                "ended_at": "",
            }
        ]
    )

    assert "SubagentStart and SubagentStop did not prove the Codex child lifecycle" in failures


@pytest.mark.parametrize("field", ["schema", "proven"])
def test_proof_refuses_evidence_that_is_not_the_exact_contract(field: str) -> None:
    failures = _failures(**{field: "tampered" if field == "schema" else False})

    assert len(failures) == 1
    assert "exact Codex activation evidence" in failures[0]


def test_proof_does_not_demand_retired_plan_delegation_or_grant() -> None:
    evidence = _evidence()
    for retired in (
        "unit_agent_plan",
        "delegations",
        "activation_grants",
        "activation_consumptions",
    ):
        assert retired not in evidence["cardinalities"]

    assert (
        codex_activation_failures(
            result=_result(),
            evidence=evidence,
            response_hash=RESPONSE_HASH,
            host_child_delivery=_host_child_delivery(),
        )
        == ()
    )
