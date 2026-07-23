"""Strict evidence coverage for contractor promotion readiness."""

from __future__ import annotations

import pytest

from agency_runtime.core.workforce.promotion import promotion_readiness


def _outcome(
    unit: str,
    *,
    worker_id: str = "worker-verifier",
    receipt: str = "review-receipt",
) -> dict[str, object]:
    return {
        "event_type": "acceptance",
        "outcome": "passed",
        "work_unit_id": unit,
        "activation_receipt_id": f"activation-{unit}",
        "evidence_refs": {
            "independent_verifier_worker_id": worker_id,
            "independent_verification_receipt_id": receipt,
            "independent_verification_validated": True,
        },
    }


def test_promotion_requires_distinct_independently_verified_assignments() -> None:
    worker = {"worker_id": "worker-contractor", "state": "contractor"}
    result = promotion_readiness(
        worker,
        [
            _outcome("unit-1"),
            _outcome("unit-1"),
            _outcome("unit-2"),
            _outcome("unit-self", worker_id="worker-contractor"),
            {**_outcome("unit-no-receipt"), "activation_receipt_id": ""},
        ],
        required_successes=2,
    )

    assert result["verified_work_units"] == ["unit-1", "unit-2"]
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
