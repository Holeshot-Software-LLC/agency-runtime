"""Direct coverage for the Codex card-delivery proof (rule 4's attestation).

Nothing called codex_activation_failures before this file. That is precisely why
44f83755 could empty the unit-agent plan and leave the canary demanding one, with
56 tests in test_codex_activation_canary.py / test_activation_canary_contract.py
staying green throughout -- see handoff §8 entry 15. These tests fail if the
proof stops requiring a card to have reached a harness-spawned child.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from agency_runtime.core.canary_proof import codex_activation_failures

RESPONSE = "Agency/Agencies loaded: code-reviewer"
RESPONSE_HASH = hashlib.sha256(RESPONSE.encode("utf-8")).hexdigest()
SESSION = "canary-session"
TRACE = "canary-trace"
QUERY_HASH = "a" * 64
RECEIVER = "019fb000-1111-7222-8333-444455556666"


def _result() -> dict[str, Any]:
    """One direct spawn plus one completed wait -- the harness spawning a child."""

    return {
        "collaboration": {
            "unexpected_item_count": 0,
            "unexpected_item_types": [],
            "calls": [
                {
                    "tool": "spawn_agent",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": "parent-thread",
                    "receiver_thread_ids": [RECEIVER],
                    "execution_delivery": {"native_task_name": "agency_task"},
                },
                {
                    "tool": "wait",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": "parent-thread",
                    "receiver_thread_ids": [RECEIVER],
                    "agents_states": {RECEIVER: "completed"},
                },
            ],
        }
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
            "selected_ids": ["code-reviewer"],
            "companion_ids": [],
            "query_hash": QUERY_HASH,
        },
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
        # The card landed: a specialist load inside this exact turn.
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
    return codex_activation_failures(
        result=_result(),
        evidence=_evidence(**overrides),
        response_hash=RESPONSE_HASH,
    )


def test_complete_card_delivery_graph_proves_the_canary() -> None:
    assert _failures() == ()


def test_proof_requires_a_specialist_load() -> None:
    """The card actually reaching the child is the whole claim."""

    failures = _failures(
        specialist_loads=[],
        cardinalities={
            "routes": 1,
            "runs": 1,
            "traces": 1,
            "worker_runs": 1,
            "specialist_loads": 0,
            "finalizations": 1,
        },
    )

    assert failures
    assert any("card delivery" in item or "incomplete" in item for item in failures)


def test_proof_rejects_a_load_from_a_different_turn() -> None:
    """No grant ties the load to the turn any more, so session/trace must."""

    failures = _failures(
        specialist_loads=[
            {"agent_slug": "code-reviewer", "session_id": SESSION, "trace_id": "other-trace"}
        ]
    )

    assert "the specialist load did not belong to the exact canary turn" in failures


def test_proof_rejects_a_specialist_the_route_did_not_select() -> None:
    failures = _failures(
        specialist_loads=[
            {"agent_slug": "technical-writer", "session_id": SESSION, "trace_id": TRACE}
        ]
    )

    assert "the sole routed canary unit was not the expected code-reviewer" in failures


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


def test_proof_no_longer_demands_a_plan_delegation_or_grant() -> None:
    """Rule 5: those are Job B. Their absence must not fail the proof.

    Pinned deliberately -- reintroducing any of them as a proof obligation would
    make the attestation claim something Agency no longer does.
    """

    evidence = _evidence()
    for retired in (
        "unit_agent_plan",
        "delegations",
        "activation_grants",
        "activation_consumptions",
    ):
        assert retired not in evidence["cardinalities"]

    assert (
        codex_activation_failures(result=_result(), evidence=evidence, response_hash=RESPONSE_HASH)
        == ()
    )
