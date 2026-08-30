"""AR-252: what may count as one accepted outcome, and what promotion does with it.

ADR-0157 makes automatic promotion part of the default contractor lifecycle, so
the question these cases answer is narrow and load-bearing: which evidence turns
into a durable employment-class change without any operator action, and which
evidence is refused with a bounded reason and leaves nothing behind.

Every refusal case below asserts the *specific* reason rather than "not
accepted", because a rule that refuses everything would also pass a weaker
assertion.
"""

from __future__ import annotations

import threading
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.roster.revisions import content_digest_identity
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.acceptance import (
    ACCEPTANCE_ENVELOPE_SCHEMA,
    ACCEPTANCE_REASONS,
    HOST_CHILD_PROOF_SCHEMA,
    accepted_outcome_manifest,
    evaluate_acceptance,
)
from agency_runtime.core.workforce.known_installer import install_known_contractors
from agency_runtime.core.workforce.promotion import promotion_readiness

CONTRACTOR_SLUG = "typescript-application-engineer"
CONTRACTOR_CARD = (CONTRACTOR_SLUG, "1.0.0", "a" * 64)
VERIFIER_CARD = ("code-reviewer", "2.0.0", "b" * 64)
ARTIFACT = "c" * 64
VERIFIER_ARTIFACT = "d" * 64
PAIR_ID = "1" * 32


def _card(entry: tuple[str, str, str]) -> dict[str, str]:
    slug, version, prompt_hash = entry
    return {
        "specialist_slug": slug,
        "specialist_version": version,
        "specialist_prompt_hash": prompt_hash,
    }


def _proof(
    *,
    child_id: str,
    decision_id: str,
    cards: tuple[tuple[str, str, str], ...],
    artifact_digest: str = "",
    host: str = "claude",
    **overrides: Any,
) -> dict[str, Any]:
    """One sealed host-child delivery proof, the only thing the rule accepts."""

    proof: dict[str, Any] = {
        "schema": HOST_CHILD_PROOF_SCHEMA,
        "verified_delivery": True,
        "host": host,
        "child_id": child_id,
        "decision_id": decision_id,
        "artifact_digest": artifact_digest,
        "cards": [_card(entry) for entry in cards],
    }
    proof.update(overrides)
    return proof


def _envelope(
    *,
    contractor_card: tuple[str, str, str] = CONTRACTOR_CARD,
    artifact: str = ARTIFACT,
    producer_child_id: str = "child-producer",
    verdict_id: str = "verdict-1",
    **overrides: Any,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "schema": ACCEPTANCE_ENVELOPE_SCHEMA,
        "contractor_worker_id": "worker-contractor",
        "contractor_card": _card(contractor_card),
        "producer": _proof(
            child_id=producer_child_id,
            decision_id="decision-producer",
            cards=(contractor_card,),
            artifact_digest=artifact,
        ),
        "verifier": _proof(
            child_id="child-verifier",
            decision_id="decision-verifier",
            cards=(VERIFIER_CARD,),
            artifact_digest=VERIFIER_ARTIFACT,
        ),
        "verdict": {
            "verdict_id": verdict_id,
            "semantic": {
                "authority": "verifier-host-artifact",
                "artifact_digest": VERIFIER_ARTIFACT,
                "record_index": 7,
                "pair_id": PAIR_ID,
                "decision": "accepted",
            },
            "binding": {
                "authority": "collector",
                "producer_artifact_digest": artifact,
                "verifier_child_id": "child-verifier",
                "pair_id": PAIR_ID,
            },
        },
    }
    envelope.update(overrides)
    return envelope


def test_host_evidenced_producer_verifier_and_verdict_record_one_acceptance() -> None:
    outcome = evaluate_acceptance(_envelope())

    assert outcome.accepted is True
    assert outcome.reason == "accepted"
    assert outcome.artifact_digest == ARTIFACT
    assert outcome.contractor_worker_id == "worker-contractor"
    assert outcome.manifest["contractor_prompt_hash"] == CONTRACTOR_CARD[2]
    assert outcome.manifest["producer_child_id"] == "child-producer"
    assert outcome.manifest["verifier_child_id"] == "child-verifier"
    assert outcome.manifest["verifier_decision_id"] == "decision-verifier"
    assert outcome.manifest["verifier_artifact_digest"] == VERIFIER_ARTIFACT
    assert outcome.manifest["verdict_semantic_record_index"] == 7
    assert outcome.manifest["verdict_semantic_pair_id"] == PAIR_ID
    assert outcome.manifest["verdict_binding_authority"] == "collector"
    assert outcome.manifest["acceptance_validated"] is True


def test_the_same_evidence_always_yields_the_same_replay_identity() -> None:
    """The outcome key is what makes a replay resolve to the first event."""

    first = evaluate_acceptance(_envelope())
    second = evaluate_acceptance(_envelope())
    other_artifact = evaluate_acceptance(_envelope(artifact="d" * 64))
    other_verifier_artifact_envelope = _envelope()
    other_verifier_artifact_envelope["verifier"] = {
        **other_verifier_artifact_envelope["verifier"],
        "artifact_digest": "e" * 64,
    }
    other_verifier_artifact_envelope["verdict"] = {
        **other_verifier_artifact_envelope["verdict"],
        "semantic": {
            **other_verifier_artifact_envelope["verdict"]["semantic"],
            "artifact_digest": "e" * 64,
        },
    }
    other_verifier_artifact = evaluate_acceptance(other_verifier_artifact_envelope)
    other_record_envelope = _envelope()
    other_record_envelope["verdict"] = {
        **other_record_envelope["verdict"],
        "semantic": {
            **other_record_envelope["verdict"]["semantic"],
            "record_index": 8,
        },
    }
    other_record = evaluate_acceptance(other_record_envelope)

    assert first.outcome_key == second.outcome_key
    assert first.outcome_key != other_artifact.outcome_key
    assert first.outcome_key != other_verifier_artifact.outcome_key
    assert first.outcome_key != other_record.outcome_key


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ({"producer": None}, "producer_evidence_missing"),
        ({"verifier": None}, "verifier_evidence_missing"),
        ({"verdict": None}, "verdict_missing"),
        ({"schema": "agency.accepted-outcome.v1"}, "envelope_malformed"),
        ({"contractor_worker_id": ""}, "envelope_malformed"),
    ],
)
def test_missing_evidence_refuses_with_its_own_reason(
    mutation: dict[str, Any],
    reason: str,
) -> None:
    outcome = evaluate_acceptance(_envelope(**mutation))

    assert outcome.accepted is False
    assert outcome.reason == reason
    assert outcome.outcome_key == ""


@pytest.mark.parametrize(
    "card",
    [
        {"specialist_slug": CONTRACTOR_SLUG},
        {"specialist_slug": CONTRACTOR_SLUG, "specialist_version": "1.0.0"},
        {**{"specialist_slug": "", "specialist_version": "1.0.0"}, "specialist_prompt_hash": "a"},
        "typescript-application-engineer",
    ],
)
def test_a_partial_contractor_card_names_no_identity_to_credit(card: object) -> None:
    envelope = _envelope()
    envelope["contractor_card"] = card

    assert evaluate_acceptance(envelope).reason == "envelope_malformed"


@pytest.mark.parametrize("role", ["producer", "verifier"])
def test_an_agency_authored_row_cannot_stand_in_for_a_host_artifact(role: str) -> None:
    """An Agency lifecycle row carries no host-proof schema, so it is not evidence."""

    agency_row = {
        "worker_id": "worker-contractor",
        "event_type": "assignment",
        "outcome": "passed",
        "child_id": "child-producer",
        "decision_id": "decision-producer",
        "artifact_digest": ARTIFACT,
        "cards": [_card(CONTRACTOR_CARD)],
        "verified_delivery": True,
    }
    outcome = evaluate_acceptance(_envelope(**{role: agency_row}))

    assert outcome.reason == "agency_only_evidence"


@pytest.mark.parametrize(
    ("role", "mutation", "reason"),
    [
        ("producer", {"verified_delivery": False}, "producer_not_host_proven"),
        ("producer", {"cards": []}, "producer_not_host_proven"),
        ("producer", {"child_id": ""}, "producer_not_host_proven"),
        ("verifier", {"verified_delivery": False}, "verifier_not_host_proven"),
        ("verifier", {"cards": []}, "verifier_not_host_proven"),
        ("verifier", {"host": ""}, "verifier_not_host_proven"),
    ],
)
def test_an_unverified_delivery_proof_is_refused(
    role: str,
    mutation: dict[str, Any],
    reason: str,
) -> None:
    envelope = _envelope()
    envelope[role] = {**envelope[role], **mutation}

    assert evaluate_acceptance(envelope).reason == reason


def test_a_producer_without_an_artifact_digest_has_nothing_to_accept() -> None:
    envelope = _envelope()
    envelope["producer"] = {**envelope["producer"], "artifact_digest": ""}

    assert evaluate_acceptance(envelope).reason == "producer_artifact_digest_missing"


def test_a_verifier_without_an_artifact_digest_cannot_author_the_semantic_verdict() -> None:
    envelope = _envelope()
    envelope["verifier"] = {**envelope["verifier"], "artifact_digest": ""}

    assert evaluate_acceptance(envelope).reason == "verifier_artifact_digest_missing"


def test_two_revisions_of_one_specialist_make_attribution_ambiguous() -> None:
    """Promotion changes one immutable identity, so which card worked must be exact."""

    envelope = _envelope()
    envelope["producer"] = _proof(
        child_id="child-producer",
        decision_id="decision-producer",
        cards=(CONTRACTOR_CARD, (CONTRACTOR_SLUG, "1.1.0", "e" * 64)),
        artifact_digest=ARTIFACT,
    )

    assert evaluate_acceptance(envelope).reason == "producer_attribution_ambiguous"


@pytest.mark.parametrize(
    "delivered",
    [
        (VERIFIER_CARD,),
        ((CONTRACTOR_SLUG, "9.9.9", CONTRACTOR_CARD[2]),),
        ((CONTRACTOR_SLUG, CONTRACTOR_CARD[1], "f" * 64),),
    ],
)
def test_an_outcome_is_refused_unless_the_contractors_own_card_was_delivered(
    delivered: tuple[tuple[str, str, str], ...],
) -> None:
    envelope = _envelope()
    envelope["producer"] = _proof(
        child_id="child-producer",
        decision_id="decision-producer",
        cards=delivered,
        artifact_digest=ARTIFACT,
    )

    assert evaluate_acceptance(envelope).reason == "contractor_card_not_delivered"


def test_a_child_cannot_verify_itself() -> None:
    envelope = _envelope()
    envelope["verifier"] = {**envelope["verifier"], "child_id": "child-producer"}
    envelope["verdict"] = {
        **envelope["verdict"],
        "binding": {
            **envelope["verdict"]["binding"],
            "verifier_child_id": "child-producer",
        },
    }

    assert evaluate_acceptance(envelope).reason == "shared_producer_verifier_identity"


def test_the_same_specialist_running_twice_is_not_an_independent_verifier() -> None:
    envelope = _envelope()
    envelope["verifier"] = _proof(
        child_id="child-verifier",
        decision_id="decision-verifier",
        cards=(CONTRACTOR_CARD,),
        artifact_digest=VERIFIER_ARTIFACT,
    )

    assert evaluate_acceptance(envelope).reason == "shared_producer_verifier_identity"


@pytest.mark.parametrize("decision_id", ["", "decision-producer"])
def test_a_verifier_without_its_own_inference_decision_is_refused(decision_id: str) -> None:
    """ADR-0118: the decision id is the recorded inference staffing identity."""

    envelope = _envelope()
    envelope["verifier"] = {**envelope["verifier"], "decision_id": decision_id}

    assert evaluate_acceptance(envelope).reason == "verifier_not_inference_selected"


@pytest.mark.parametrize(
    ("component", "mutation", "reason"),
    [
        (
            "binding",
            {"verifier_child_id": "child-somebody-else"},
            "verdict_not_bound_to_verifier",
        ),
        ("semantic", {"artifact_digest": "9" * 64}, "verdict_semantic_origin_mismatch"),
        ("semantic", {"artifact_digest": ""}, "verdict_semantic_origin_mismatch"),
        ("semantic", {"authority": "collector"}, "verdict_semantic_origin_mismatch"),
        ("semantic", {"record_index": -1}, "verdict_semantic_missing"),
        ("semantic", {"record_index": 65_536}, "verdict_semantic_missing"),
        ("semantic", {"record_index": True}, "verdict_semantic_missing"),
        ("semantic", {"pair_id": "not-a-pair"}, "verdict_semantic_missing"),
        ("binding", {"producer_artifact_digest": "9" * 64}, "verdict_binding_mismatch"),
        ("binding", {"producer_artifact_digest": ""}, "verdict_binding_mismatch"),
        ("binding", {"authority": "verifier"}, "verdict_binding_mismatch"),
        ("binding", {"pair_id": "2" * 32}, "verdict_binding_mismatch"),
        ("semantic", {"decision": "rejected"}, "verdict_rejected"),
        ("semantic", {"decision": "inconclusive"}, "verdict_rejected"),
        ("verdict", {"verdict_id": ""}, "verdict_missing"),
    ],
)
def test_the_verdict_must_accept_this_exact_artifact_from_this_exact_verifier(
    component: str,
    mutation: dict[str, Any],
    reason: str,
) -> None:
    envelope = _envelope()
    if component == "verdict":
        envelope["verdict"] = {**envelope["verdict"], **mutation}
    else:
        envelope["verdict"] = {
            **envelope["verdict"],
            component: {**envelope["verdict"][component], **mutation},
        }

    assert evaluate_acceptance(envelope).reason == reason


@pytest.mark.parametrize("component", ["semantic", "binding"])
def test_both_joint_verdict_halves_are_required(component: str) -> None:
    envelope = _envelope()
    envelope["verdict"] = {**envelope["verdict"], component: None}

    expected = f"verdict_{component}_missing"
    assert evaluate_acceptance(envelope).reason == expected


@pytest.mark.parametrize("envelope", [None, "accepted", 7, [], {"schema": None}])
def test_a_non_envelope_is_malformed_rather_than_an_exception(envelope: object) -> None:
    assert evaluate_acceptance(envelope).reason == "envelope_malformed"


def test_every_refusal_uses_the_bounded_vocabulary() -> None:
    """A reason travels into evidence, so it may never be free text."""

    mutations: list[dict[str, Any]] = [
        {"producer": None},
        {"verifier": None},
        {"verdict": None},
        {"schema": "wrong"},
        {"producer": {"schema": "agency.worker-event.v1"}},
        {"verdict": {"verdict_id": "v", "decision": "rejected"}},
    ]
    reasons = {evaluate_acceptance(_envelope(**item)).reason for item in mutations}

    assert reasons <= ACCEPTANCE_REASONS
    assert "accepted" not in reasons


def test_a_manifest_whose_key_was_edited_afterwards_stops_counting() -> None:
    """The stored key is derived from the stored identities, so it can be rechecked."""

    manifest = dict(evaluate_acceptance(_envelope()).manifest)
    assert accepted_outcome_manifest(manifest) is not None

    forged = {**manifest, "producer_artifact_digest": "1" * 64}

    assert accepted_outcome_manifest(forged) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("verifier_artifact_digest", "1" * 64),
        ("verdict_semantic_authority", "collector"),
        ("verdict_semantic_artifact_digest", "1" * 64),
        ("verdict_semantic_record_index", -1),
        ("verdict_semantic_pair_id", "2" * 32),
        ("verdict_binding_authority", "verifier-host-artifact"),
        ("verdict_binding_producer_artifact_digest", "1" * 64),
        ("verdict_binding_verifier_child_id", "child-somebody-else"),
        ("verdict_binding_pair_id", "2" * 32),
    ],
)
def test_a_manifest_with_edited_joint_verdict_attribution_stops_counting(
    field: str,
    value: object,
) -> None:
    manifest = dict(evaluate_acceptance(_envelope()).manifest)

    assert accepted_outcome_manifest({**manifest, field: value}) is None


def test_readiness_counts_distinct_artifacts_not_distinct_rows() -> None:
    """Two verdicts on one artifact are one piece of accepted work."""

    first = evaluate_acceptance(_envelope(verdict_id="verdict-1"))
    again = evaluate_acceptance(_envelope(verdict_id="verdict-2"))
    other = evaluate_acceptance(_envelope(artifact="d" * 64, producer_child_id="child-other"))
    rows = [
        {"event_type": "acceptance", "outcome": "accepted", "evidence_refs": dict(item.manifest)}
        for item in (first, again, other)
    ]

    readiness = promotion_readiness(
        {"worker_id": "worker-contractor", "state": "contractor"},
        rows,
        required_successes=2,
    )

    assert first.outcome_key != again.outcome_key
    assert readiness["verified_successes"] == 2
    assert readiness["verified_artifacts"] == sorted({ARTIFACT, "d" * 64})
    assert readiness["eligible_for_automatic_promotion"] is True


def _contractor(store: Store) -> dict[str, Any]:
    install_known_contractors(store)
    return dict(store.get_workforce_worker(CONTRACTOR_SLUG, disabled_agents=()))


def _store_envelope(worker: dict[str, Any], *, index: int) -> dict[str, Any]:
    """One envelope whose contractor card is this worker's real active identity."""

    prompt_hash = content_digest_identity(worker["current_hash"])
    assert prompt_hash is not None
    card = (CONTRACTOR_SLUG, str(worker["current_version"]), prompt_hash)
    return _envelope(
        contractor_worker_id=str(worker["worker_id"]),
        contractor_card=card,
        artifact=f"{index:064x}",
        producer_child_id=f"child-producer-{index}",
        verdict_id=f"verdict-{index}",
    )


def _age_worker(store: Store, worker_id: str, *, created_at: str) -> None:
    with closing(store._connect()) as conn, conn:
        conn.execute(
            "UPDATE agent_workers SET created_at = ? WHERE worker_id = ?",
            (created_at, worker_id),
        )


def _readiness(
    store: Store,
    worker_id: str,
    *,
    required_successes: int = 3,
    review_window_days: int = 7,
) -> dict[str, Any]:
    """Readiness as the CLI and dashboard compute it: from the recorded rows."""

    detail = store.get_workforce_worker_detail(worker_id, disabled_agents=())
    return promotion_readiness(
        {
            "worker_id": worker_id,
            "state": detail["worker"]["state"],
            "created_at": detail["worker"]["created_at"],
        },
        detail["outcomes"],
        required_successes=required_successes,
        review_window_days=review_window_days,
    )


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


def test_one_accepted_envelope_records_exactly_one_acceptance(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)

    result = store.record_accepted_outcome(
        envelope=_store_envelope(worker, index=1),
        auto_promote_successes=3,
        disabled_agents=(),
    )
    rows = _acceptance_rows(store, str(worker["worker_id"]))

    assert result["recorded"] is True
    assert result["reason"] == "accepted"
    assert result["promoted"] is False
    assert len(rows) == 1
    assert rows[0]["idempotency_key"] == result["accepted_outcome_key"]
    assert rows[0]["work_unit_id"] == ""
    assert rows[0]["activation_receipt_id"] == ""


def test_replaying_the_same_evidence_adds_no_second_success(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)
    envelope = _store_envelope(worker, index=1)

    first = store.record_accepted_outcome(
        envelope=envelope, auto_promote_successes=3, disabled_agents=()
    )
    replay = store.record_accepted_outcome(
        envelope=envelope, auto_promote_successes=3, disabled_agents=()
    )

    assert replay["recorded"] is False
    assert replay["reason"] == "replayed"
    assert replay["event_id"] == first["event_id"]
    assert len(_acceptance_rows(store, str(worker["worker_id"]))) == 1


def test_concurrent_finalization_of_one_envelope_cannot_duplicate(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)
    envelope = _store_envelope(worker, index=1)
    start = threading.Barrier(4)
    results: list[dict[str, Any]] = []
    lock = threading.Lock()

    def finalize() -> None:
        start.wait(timeout=10)
        outcome = store.record_accepted_outcome(
            envelope=envelope, auto_promote_successes=3, disabled_agents=()
        )
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=finalize) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len(results) == 4
    assert sum(1 for item in results if item["recorded"]) == 1
    assert all(item["reason"] in {"accepted", "replayed"} for item in results)
    assert len(_acceptance_rows(store, str(worker["worker_id"]))) == 1


def test_three_distinct_accepted_outcomes_promote_without_an_operator(
    tmp_path: Path,
) -> None:
    """The governed default policy: three successes, seven-day window, no operator."""

    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)
    worker_id = str(worker["worker_id"])
    _age_worker(store, worker_id, created_at="2026-01-01T00:00:00+00:00")

    results = [
        store.record_accepted_outcome(envelope=_store_envelope(worker, index=index))
        for index in (1, 2, 3)
    ]
    detail = store.get_workforce_worker_detail(worker_id, disabled_agents=())
    promotion = next(item for item in detail["events"] if item["event_type"] == "promote")

    assert [item["reason"] for item in results] == ["accepted"] * 3
    assert [item["promoted"] for item in results] == [False, False, True]
    assert detail["worker"]["state"] == "employee"
    assert promotion["actor"] == "promotion-policy"
    assert len(promotion["evidence"]["verified_artifacts"]) == 3


def test_a_contractor_inside_its_review_window_is_not_promoted(tmp_path: Path) -> None:
    """AR-242: three successes are not enough while the window is open."""

    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)
    worker_id = str(worker["worker_id"])

    results = [
        store.record_accepted_outcome(envelope=_store_envelope(worker, index=index))
        for index in (1, 2, 3)
    ]
    detail = store.get_workforce_worker_detail(worker_id, disabled_agents=())

    readiness = _readiness(store, worker_id)

    assert all(item["recorded"] for item in results)
    assert not any(item["promoted"] for item in results)
    assert detail["worker"]["state"] == "contractor"
    assert readiness["verified_successes"] == 3
    assert readiness["in_review_window"] is True
    assert readiness["eligible_for_automatic_promotion"] is False


def test_two_verdicts_on_one_artifact_are_one_success(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)
    worker_id = str(worker["worker_id"])
    _age_worker(store, worker_id, created_at="2026-01-01T00:00:00+00:00")
    envelope = _store_envelope(worker, index=1)

    for verdict_id in ("verdict-a", "verdict-b", "verdict-c"):
        store.record_accepted_outcome(
            envelope={
                **envelope,
                "verdict": {**envelope["verdict"], "verdict_id": verdict_id},
            }
        )
    detail = store.get_workforce_worker_detail(worker_id, disabled_agents=())

    assert len(_acceptance_rows(store, worker_id)) == 3
    assert _readiness(store, worker_id)["verified_successes"] == 1
    assert detail["worker"]["state"] == "contractor"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (
            {
                "verdict": {
                    "verdict_id": "verdict-1",
                    "semantic": {
                        "authority": "verifier-host-artifact",
                        "artifact_digest": VERIFIER_ARTIFACT,
                        "record_index": 7,
                        "pair_id": PAIR_ID,
                        "decision": "rejected",
                    },
                    "binding": {
                        "authority": "collector",
                        "producer_artifact_digest": f"{1:064x}",
                        "verifier_child_id": "child-verifier",
                        "pair_id": PAIR_ID,
                    },
                }
            },
            "verdict_rejected",
        ),
        ({"producer": None}, "producer_evidence_missing"),
        ({"verifier": None}, "verifier_evidence_missing"),
    ],
)
def test_refused_evidence_leaves_no_row_behind(
    tmp_path: Path,
    mutation: dict[str, Any],
    reason: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)

    result = store.record_accepted_outcome(
        envelope={**_store_envelope(worker, index=1), **mutation},
        auto_promote_successes=1,
        disabled_agents=(),
    )

    assert result["recorded"] is False
    assert result["reason"] == reason
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


def test_an_outcome_credited_to_the_wrong_worker_is_refused(tmp_path: Path) -> None:
    """The delivered card has to be the credited worker's own specialist."""

    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)

    result = store.record_accepted_outcome(
        envelope=_envelope(
            contractor_worker_id=str(worker["worker_id"]),
            contractor_card=("python-backend-engineer", "1.0.0", "e" * 64),
            producer_child_id="child-producer-1",
        ),
        auto_promote_successes=1,
        disabled_agents=(),
    )

    assert result["recorded"] is False
    assert result["reason"] == "contractor_identity_mismatch"
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


@pytest.mark.parametrize("revision_field", ["version", "hash"])
def test_an_outcome_for_another_worker_revision_is_refused(
    tmp_path: Path,
    revision_field: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)
    version = str(worker["current_version"])
    prompt_hash = content_digest_identity(worker["current_hash"])
    assert prompt_hash is not None
    if revision_field == "version":
        version = "contractor-other-version"
    else:
        prompt_hash = "e" * 64

    result = store.record_accepted_outcome(
        envelope=_envelope(
            contractor_worker_id=str(worker["worker_id"]),
            contractor_card=(CONTRACTOR_SLUG, version, prompt_hash),
            producer_child_id="child-producer-1",
        ),
        auto_promote_successes=1,
        disabled_agents=(),
    )

    assert result["recorded"] is False
    assert result["reason"] == "contractor_identity_mismatch"
    assert _acceptance_rows(store, str(worker["worker_id"])) == []


@pytest.mark.parametrize(
    ("evidence_refs", "message"),
    [
        (
            {
                "independent_verifier_worker_id": "worker-verifier",
                "independent_verification_receipt_id": "receipt",
            },
            "retired by AR-252",
        ),
        (
            {"acceptance_validated": True, "accepted_outcome_key": "0" * 64},
            "only be recorded from host artifacts",
        ),
    ],
)
def test_promotion_evidence_cannot_be_hand_written_through_the_generic_recorder(
    tmp_path: Path,
    evidence_refs: dict[str, Any],
    message: str,
) -> None:
    """The only writer of a countable acceptance is the host-artifact path."""

    store = Store(tmp_path / "agency.db")
    worker = _contractor(store)

    with pytest.raises(ValueError, match=message):
        store.record_workforce_outcome(
            str(worker["worker_id"]),
            idempotency_key="c" * 64,
            event_type="review",
            outcome="passed",
            evidence_hash="d" * 64,
            evidence_refs=evidence_refs,
            auto_promote_successes=1,
            disabled_agents=(),
        )
