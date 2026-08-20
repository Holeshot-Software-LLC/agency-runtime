"""Strict evidence coverage for contractor promotion readiness.

The evidence rule itself lives in ``tests/test_accepted_outcomes.py``. These
cases cover the policy laid over it -- threshold, review window, and who may be
promoted at all -- so they build their evidence by running the real rule rather
than by hand-writing a manifest it would have refused.
"""

from __future__ import annotations

import hashlib

import pytest

from agency_runtime.core.workforce.acceptance import (
    ACCEPTANCE_ENVELOPE_SCHEMA,
    HOST_CHILD_PROOF_SCHEMA,
    evaluate_acceptance,
)
from agency_runtime.core.workforce.promotion import promotion_readiness

_CONTRACTOR_CARD = {
    "specialist_slug": "typescript-application-engineer",
    "specialist_version": "1.0.0",
    "specialist_prompt_hash": "a" * 64,
}
_VERIFIER_CARD = {
    "specialist_slug": "code-reviewer",
    "specialist_version": "2.0.0",
    "specialist_prompt_hash": "b" * 64,
}


def _proof(child_id: str, decision_id: str, card: dict[str, str], digest: str) -> dict[str, object]:
    return {
        "schema": HOST_CHILD_PROOF_SCHEMA,
        "verified_delivery": True,
        "host": "claude",
        "child_id": child_id,
        "decision_id": decision_id,
        "artifact_digest": digest,
        "cards": [card],
    }


def _outcome(unit: str, *, verifier_child_id: str = "child-verifier") -> dict[str, object]:
    """One recorded acceptance for a distinct produced artifact."""

    digest = hashlib.sha256(unit.encode("utf-8")).hexdigest()
    verifier_digest = hashlib.sha256(f"verifier:{unit}".encode()).hexdigest()
    outcome = evaluate_acceptance(
        {
            "schema": ACCEPTANCE_ENVELOPE_SCHEMA,
            "contractor_worker_id": "worker-contractor",
            "contractor_card": _CONTRACTOR_CARD,
            "producer": _proof(f"child-{unit}", "decision-producer", _CONTRACTOR_CARD, digest),
            "verifier": _proof(
                verifier_child_id,
                "decision-verifier",
                _VERIFIER_CARD,
                verifier_digest,
            ),
            "verdict": {
                "verdict_id": f"verdict-{unit}",
                "semantic": {
                    "authority": "verifier-host-artifact",
                    "artifact_digest": verifier_digest,
                    "record_index": 1,
                    "pair_id": "1" * 32,
                    "decision": "accepted",
                },
                "binding": {
                    "authority": "collector",
                    "producer_artifact_digest": digest,
                    "verifier_child_id": verifier_child_id,
                    "pair_id": "1" * 32,
                },
            },
        }
    )
    assert outcome.accepted, outcome.reason
    return {
        "event_type": "acceptance",
        "outcome": "accepted",
        "evidence_refs": dict(outcome.manifest),
    }


def test_promotion_requires_distinct_host_evidenced_acceptances() -> None:
    """Only distinct artifacts count, and only from an intact acceptance manifest."""

    worker = {"worker_id": "worker-contractor", "state": "contractor"}
    tampered = _outcome("unit-tampered")
    tampered["evidence_refs"] = {
        **tampered["evidence_refs"],
        "verifier_child_id": "child-somebody-else",
    }
    result = promotion_readiness(
        worker,
        [
            _outcome("unit-1"),
            _outcome("unit-1"),
            _outcome("unit-2"),
            tampered,
            {**_outcome("unit-not-an-acceptance"), "event_type": "assignment"},
            {"event_type": "acceptance", "outcome": "accepted", "evidence_refs": {}},
        ],
        required_successes=2,
    )

    assert result["verified_artifacts"] == sorted(
        hashlib.sha256(unit.encode("utf-8")).hexdigest() for unit in ("unit-1", "unit-2")
    )
    assert result["verified_successes"] == 2
    assert result["eligible_for_automatic_promotion"] is True


def test_manual_policy_and_non_contractor_never_claim_automatic_readiness() -> None:
    manual = promotion_readiness(
        {"worker_id": "worker-contractor", "state": "contractor"},
        [_outcome("unit-1")],
        required_successes=0,
    )
    employee = promotion_readiness(
        {"worker_id": "worker-employee", "state": "employee"},
        [_outcome("unit-1")],
        required_successes=1,
    )

    assert manual["human_promotion_available"] is True
    assert manual["automatic_policy_enabled"] is False
    assert manual["eligible_for_automatic_promotion"] is False
    assert employee["human_promotion_available"] is False
    assert employee["eligible_for_automatic_promotion"] is False


@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_promotion_threshold_is_bounded_to_non_negative_integers(value: object) -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        promotion_readiness({}, [], required_successes=value)  # type: ignore[arg-type]


def test_review_window_suppresses_auto_promotion_for_young_contractor() -> None:
    """AR-242: a contractor younger than the review window is not auto-promoted
    even when the success threshold is met."""

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=2)).isoformat()
    worker = {
        "worker_id": "worker-contractor",
        "state": "contractor",
        "created_at": recent,
    }
    result = promotion_readiness(
        worker,
        [_outcome("unit-1"), _outcome("unit-2"), _outcome("unit-3")],
        required_successes=3,
        review_window_days=7,
        now=now,
    )

    assert result["verified_successes"] == 3
    assert result["in_review_window"] is True
    assert result["eligible_for_automatic_promotion"] is False
    assert any("review window" in reason for reason in result["reasons"])


def test_review_window_releases_after_expiry() -> None:
    """AR-242: once the review window expires, auto-promotion proceeds."""

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=30)).isoformat()
    worker = {
        "worker_id": "worker-contractor",
        "state": "contractor",
        "created_at": old,
    }
    result = promotion_readiness(
        worker,
        [_outcome("unit-1"), _outcome("unit-2"), _outcome("unit-3")],
        required_successes=3,
        review_window_days=7,
        now=now,
    )

    assert result["in_review_window"] is False
    assert result["eligible_for_automatic_promotion"] is True
