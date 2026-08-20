"""AR-252: collect one Claude producer/verifier pair without widening authority.

These cases exercise the private in-lifetime collector rather than handing an
acceptance envelope to the Store directly.  Both children must independently
prove pre-speech card delivery in host-written artifacts, the verifier's own
artifact must carry the semantic decision, and the two sealed capabilities may
only cross the Store boundary together.
"""

from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import child_delivery_evidence as subject
from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)
from agency_runtime.core.native_child_prompt_delivery import (
    InferenceTeamCard,
    inference_team_digest,
    render_inference_team_delivery,
)
from agency_runtime.core.private_paths import _private_temporary_directory_lease
from agency_runtime.core.roster.bundled import bundled_roster
from agency_runtime.core.roster.revisions import content_digest, content_digest_identity
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import (
    install_known_contractors,
    known_contractor_agent,
)

PARENT_SESSION = "47a4776a-92f4-4fe8-b2fe-926652d70225"
PARENT_TRACE = "trace-accepted-outcome-pair"
PAIR_ID = "7" * 32
CONTRACTOR_SLUG = "typescript-application-engineer"
PRODUCER_CHILD = "a19cc709eae42e601"
VERIFIER_CHILD = "a19cc709eae42e602"
EXTRA_CHILD = "a19cc709eae42e603"
RUNTIME_DIGEST = content_digest("accepted-outcome-runtime")
PROVIDER_ATTEMPTS = (
    {
        "provider_name": "claude-subscription",
        "provider_type": "anthropic",
        "requested_model": "sonnet",
        "model_group": "",
        "actual_model": "claude-sonnet",
        "model_receipt_source": "wrapper",
        "status": "applied",
        "reason_code": "",
    },
)
PROVIDER_DIGEST = canonical_native_child_provider_receipt_digest(PROVIDER_ATTEMPTS)
assert PROVIDER_DIGEST is not None


@pytest.fixture
def private_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model the allocator-owned Windows directory's trusted ACL boundary."""

    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: True)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds").replace("+00:00", "Z")


def _team_card(agent: dict[str, Any]) -> InferenceTeamCard:
    prompt_hash = content_digest_identity(agent["hash"])
    assert prompt_hash is not None
    return InferenceTeamCard(
        specialist_slug=str(agent["slug"]),
        specialist_version=str(agent["version"]),
        specialist_prompt_hash=prompt_hash,
        prompt_body=str(agent["prompt_body"]),
    )


def _card_projection(card: InferenceTeamCard) -> dict[str, object]:
    return {
        "specialist_slug": card.specialist_slug,
        "specialist_version": card.specialist_version,
        "specialist_prompt_hash": card.specialist_prompt_hash,
        "body_character_length": len(card.prompt_body),
    }


def _record_delivery_decision(
    store: Store,
    *,
    task: str,
    team: tuple[InferenceTeamCard, ...],
    child_id: str,
    launch_id: str,
    nonce: str,
    issued_at: str,
    expires_at: str,
) -> str:
    task_digest = content_digest(task)
    decision_payload = {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "claude",
        "parent_session_id": PARENT_SESSION,
        "parent_trace_id": PARENT_TRACE,
        "launch_id": launch_id,
        "binding_kind": "child_id",
        "binding_id": child_id,
        "provider_attempts": list(PROVIDER_ATTEMPTS),
        "provider_receipt_digest": PROVIDER_DIGEST,
        "task_sha256": task_digest,
        "team_digest": inference_team_digest(team),
        "candidate_digest": RUNTIME_DIGEST,
        "runtime_digest": RUNTIME_DIGEST,
        "install_id": "install-outcome-pair",
        "bundle_digest": content_digest("accepted-outcome-bundle"),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "cards": [_card_projection(card) for card in team],
    }
    return store.record_routing_decision(
        trace_id=PARENT_TRACE,
        session_id=PARENT_SESSION,
        query_hash=task_digest,
        context_fingerprint=content_digest(f"context:{task}"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": [card.specialist_slug for card in team],
            "semantic_ids": [card.specialist_slug for card in team],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "claude-subscription",
            "candidate_count": len(team),
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": task_digest,
            "query_hash": task_digest,
            "context_fingerprint": content_digest(f"context:{task}"),
            "native_child_delivery": decision_payload,
        },
    )


def _render_delivery(
    *,
    task: str,
    team: tuple[InferenceTeamCard, ...],
    child_id: str,
    launch_id: str,
    nonce: str,
    decision_id: str,
    issued_at: str,
    expires_at: str,
) -> str:
    return render_inference_team_delivery(
        task,
        team,
        host="claude",
        parent_session_id=PARENT_SESSION,
        parent_trace_id=PARENT_TRACE,
        launch_id=launch_id,
        decision_id=decision_id,
        provider_receipt_digest=PROVIDER_DIGEST,
        candidate_digest=RUNTIME_DIGEST,
        install_id="install-outcome-pair",
        bundle_digest=content_digest("accepted-outcome-bundle"),
        runtime_digest=RUNTIME_DIGEST,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
        binding_kind="child_id",
        binding_id=child_id,
    )


def _record(
    *,
    child_id: str,
    record_type: str,
    role: str,
    content: str,
    timestamp: str,
) -> dict[str, object]:
    return {
        "parentUuid": None,
        "isSidechain": True,
        "agentId": child_id,
        "type": record_type,
        "message": {"role": role, "content": content},
        "sessionId": PARENT_SESSION,
        "timestamp": timestamp,
    }


def _write_artifact(
    root: Path,
    *,
    child_id: str,
    delivery: str,
    timestamp: str,
    response: str = "",
) -> Path:
    records = [
        _record(
            child_id=child_id,
            record_type="user",
            role="user",
            content=delivery,
            timestamp=timestamp,
        )
    ]
    if response:
        records.append(
            _record(
                child_id=child_id,
                record_type="assistant",
                role="assistant",
                content=response,
                timestamp=timestamp,
            )
        )
    path = root / "project" / PARENT_SESSION / "subagents" / f"agent-{child_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


def _acceptance_rows(store: Store, worker_id: str) -> list[dict[str, Any]]:
    with closing(store._connect()) as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM agent_performance_events "
                "WHERE worker_id = ? AND event_type = 'acceptance'",
                (worker_id,),
            ).fetchall()
        ]


def _collect_pair(
    tmp_path: Path,
    *,
    producer_pair_id: str = PAIR_ID,
    verifier_pair_id: str = PAIR_ID,
    verifier_response: str | None = None,
    producer_response: str = "Implemented the bounded TypeScript result.",
    producer_extra_card: bool = False,
    auto_promote_successes: int = 3,
    inspect_capabilities: dict[str, object] | None = None,
    repeat: bool = False,
    extra_artifact: bool = False,
    expected_provider: str | None = None,
) -> tuple[subject._HostAcceptedOutcomeCollection, Store, dict[str, Any]]:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    worker = dict(store.get_workforce_worker(CONTRACTOR_SLUG, disabled_agents=()))
    contractor = known_contractor_agent(KNOWN_CONTRACTORS_BY_SLUG[CONTRACTOR_SLUG])
    verifier_agent = next(agent for agent in bundled_roster() if agent["slug"] == "code-reviewer")
    contractor_card = _team_card(contractor)
    verifier_card = _team_card(verifier_agent)
    producer_team = (contractor_card, verifier_card) if producer_extra_card else (contractor_card,)
    verifier_team = (verifier_card,)
    producer_task = (
        "Produce the bounded implementation result.\n"
        + subject._outcome_pair_role_marker(pair_id=producer_pair_id, role="producer")
    )
    verifier_task = (
        "Verify the paired implementation result.\n"
        + subject._outcome_pair_role_marker(pair_id=verifier_pair_id, role="verifier")
    )
    issued = datetime.now(timezone.utc) - timedelta(seconds=1)
    issued_at = _iso(issued)
    expires_at = _iso(issued + timedelta(minutes=5))
    store.create_run(
        session_id=PARENT_SESSION,
        trace_id=PARENT_TRACE,
        host="claude",
        user_message="Collect one producer/verifier accepted outcome pair.",
    )
    producer_decision = _record_delivery_decision(
        store,
        task=producer_task,
        team=producer_team,
        child_id=PRODUCER_CHILD,
        launch_id="launch-accepted-producer",
        nonce="nonce-accepted-producer",
        issued_at=issued_at,
        expires_at=expires_at,
    )
    verifier_decision = _record_delivery_decision(
        store,
        task=verifier_task,
        team=verifier_team,
        child_id=VERIFIER_CHILD,
        launch_id="launch-accepted-verifier",
        nonce="nonce-accepted-verifier",
        issued_at=issued_at,
        expires_at=expires_at,
    )
    producer_delivery = _render_delivery(
        task=producer_task,
        team=producer_team,
        child_id=PRODUCER_CHILD,
        launch_id="launch-accepted-producer",
        nonce="nonce-accepted-producer",
        decision_id=producer_decision,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    verifier_delivery = _render_delivery(
        task=verifier_task,
        team=verifier_team,
        child_id=VERIFIER_CHILD,
        launch_id="launch-accepted-verifier",
        nonce="nonce-accepted-verifier",
        decision_id=verifier_decision,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    if verifier_response is None:
        verifier_response = (
            "The paired work satisfies the bounded contract.\n"
            + subject._verifier_semantic_marker(pair_id=verifier_pair_id, decision="accepted")
        )

    with _private_temporary_directory_lease(prefix="accepted-outcome-test") as lease:
        collection = subject._begin_private_host_artifact_collection(lease, host="claude")
        invocation_start = subject._start_private_host_invocation(collection)
        observed_at = _iso(datetime.now(timezone.utc))
        _write_artifact(
            collection.root,
            child_id=PRODUCER_CHILD,
            delivery=producer_delivery,
            timestamp=observed_at,
            response=producer_response,
        )
        _write_artifact(
            collection.root,
            child_id=VERIFIER_CHILD,
            delivery=verifier_delivery,
            timestamp=observed_at,
            response=verifier_response,
        )
        if extra_artifact:
            _write_artifact(
                collection.root,
                child_id=EXTRA_CHILD,
                delivery="Unrelated child without an Agency card.",
                timestamp=observed_at,
            )
        invocation = subject._finish_private_host_invocation(invocation_start)
        if inspect_capabilities is None:
            result = subject._collect_private_host_accepted_outcome(
                collection,
                invocation=invocation,
                store=store,
                auto_promote_successes=auto_promote_successes,
                disabled_agents=frozenset(),
                expected_provider=expected_provider,
            )
        else:
            original = subject._record_verified_host_child_pair_outcome

            def inspect_pair(capabilities, **kwargs):
                inspect_capabilities["single_consumptions"] = tuple(
                    subject._consume_verified_host_child_delivery(value) for value in capabilities
                )
                inspect_capabilities["identities"] = tuple(id(value) for value in capabilities)
                return original(capabilities, **kwargs)

            subject._record_verified_host_child_pair_outcome = inspect_pair
            try:
                result = subject._collect_private_host_accepted_outcome(
                    collection,
                    invocation=invocation,
                    store=store,
                    auto_promote_successes=auto_promote_successes,
                    disabled_agents=frozenset(),
                    expected_provider=expected_provider,
                )
            finally:
                subject._record_verified_host_child_pair_outcome = original
            inspect_capabilities["registered_after"] = tuple(
                identity in subject._VERIFIED_DELIVERY_IDENTITIES
                for identity in inspect_capabilities["identities"]
            )
        if repeat:
            result = subject._collect_private_host_accepted_outcome(
                collection,
                invocation=invocation,
                store=store,
                auto_promote_successes=auto_promote_successes,
                disabled_agents=frozenset(),
                expected_provider=expected_provider,
            )
        assert result.producer_decision_id in {"", producer_decision}
        assert result.verifier_decision_id in {"", verifier_decision}
    return result, store, worker


def test_exact_pair_records_and_promotes_from_two_host_artifacts(
    tmp_path: Path,
    private_root: None,
) -> None:
    inspected: dict[str, object] = {}
    result, store, worker = _collect_pair(
        tmp_path,
        auto_promote_successes=1,
        inspect_capabilities=inspected,
        expected_provider="claude-subscription",
    )

    assert result.reason == "accepted", (
        result,
        worker["current_version"],
        worker["current_hash"],
    )
    assert result.pair_id == PAIR_ID
    assert result.result is not None and result.result["recorded"] is True
    assert result.result["promoted"] is True
    detail = store.get_workforce_worker_detail(str(worker["worker_id"]), disabled_agents=())
    promotion = next(event for event in detail["events"] if event["event_type"] == "promote")
    assert inspected["single_consumptions"] == (None, None)
    assert inspected["registered_after"] == (False, False)
    assert len(_acceptance_rows(store, str(worker["worker_id"]))) == 1
    assert detail["worker"]["state"] == "employee"
    assert promotion["actor"] == "promotion-policy"


def test_rejected_verifier_semantic_records_no_acceptance(
    tmp_path: Path,
    private_root: None,
) -> None:
    response = (
        "The paired work does not satisfy the bounded contract.\n"
        + subject._verifier_semantic_marker(pair_id=PAIR_ID, decision="rejected")
    )
    result, store, worker = _collect_pair(tmp_path, verifier_response=response)

    assert result.reason == "verdict_rejected"
    assert result.result is not None and result.result["recorded"] is False
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_mismatched_pair_identity_never_reaches_acceptance(
    tmp_path: Path,
    private_root: None,
) -> None:
    result, store, worker = _collect_pair(tmp_path, verifier_pair_id="8" * 32)

    assert result.reason == "pair_identity_mismatch"
    assert result.result is None
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        ("No machine-readable decision was written.", "verifier_semantic_missing"),
        (
            subject._verifier_semantic_marker(pair_id=PAIR_ID, decision="accepted")
            + "\n"
            + subject._verifier_semantic_marker(pair_id=PAIR_ID, decision="accepted"),
            "verifier_semantic_ambiguous",
        ),
        (
            json.dumps(
                {
                    "decision": "accepted",
                    "pair_id": "9" * 32,
                    "schema": "agency.verifier-semantic.v1",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "verifier_semantic_invalid",
        ),
    ],
)
def test_missing_ambiguous_or_unbound_semantics_are_refused(
    tmp_path: Path,
    private_root: None,
    response: str,
    reason: str,
) -> None:
    result, store, worker = _collect_pair(tmp_path, verifier_response=response)

    assert result.reason == reason
    assert result.result is None
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_multi_card_producer_is_refused_before_outcome_recording(
    tmp_path: Path,
    private_root: None,
) -> None:
    result, store, worker = _collect_pair(tmp_path, producer_extra_card=True)

    assert result.reason == "producer_cardinality_invalid"
    assert result.result is None
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_producer_without_host_written_output_is_not_an_outcome(
    tmp_path: Path,
    private_root: None,
) -> None:
    result, store, worker = _collect_pair(tmp_path, producer_response="")

    assert result.reason == "producer_output_missing"
    assert result.result is None
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_more_than_exactly_two_child_artifacts_is_refused(
    tmp_path: Path,
    private_root: None,
) -> None:
    result, store, worker = _collect_pair(tmp_path, extra_artifact=True)

    assert result.reason == "expected_two_child_artifacts"
    assert result.result is None
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_expected_provider_mismatch_is_refused_before_outcome_recording(
    tmp_path: Path,
    private_root: None,
) -> None:
    result, store, worker = _collect_pair(
        tmp_path,
        expected_provider="not-the-answering-provider",
    )

    assert result.reason == "provider_pin_mismatch"
    assert result.result is None
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_recollecting_the_same_pair_is_an_idempotent_replay(
    tmp_path: Path,
    private_root: None,
) -> None:
    result, store, worker = _collect_pair(tmp_path, repeat=True)

    assert result.reason == "replayed"
    assert result.result is not None and result.result["recorded"] is False
    assert len(_acceptance_rows(store, str(worker["worker_id"]))) == 1


def test_pair_collector_authority_is_not_public() -> None:
    assert {
        "_collect_private_host_accepted_outcome",
        "_record_verified_host_child_pair_outcome",
        "_HostAcceptedOutcomeCollection",
        "_outcome_pair_role_marker",
        "_verifier_semantic_marker",
    }.isdisjoint(subject.__all__)
