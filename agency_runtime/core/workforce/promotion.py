"""Evidence rules for human and policy-driven contractor promotion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_SUCCESS_OUTCOMES = frozenset({"accepted", "completed", "passed", "succeeded", "success"})


def _independent_success_units(
    outcomes: Sequence[Mapping[str, Any]],
    *,
    worker_id: str,
) -> tuple[str, ...]:
    units: set[str] = set()
    for item in outcomes:
        refs = item.get("evidence_refs")
        if not isinstance(refs, Mapping):
            continue
        verifier = str(refs.get("independent_verifier_worker_id") or "").strip()
        receipt = str(refs.get("independent_verification_receipt_id") or "").strip()
        unit = str(item.get("work_unit_id") or "").strip()
        if (
            str(item.get("event_type") or "").casefold() == "acceptance"
            and str(item.get("outcome") or "").casefold() in _SUCCESS_OUTCOMES
            and str(item.get("activation_receipt_id") or "").strip()
            and unit
            and verifier
            and verifier != worker_id
            and receipt
            and refs.get("independent_verification_validated") is True
        ):
            units.add(unit)
    return tuple(sorted(units))


def promotion_readiness(
    worker: Mapping[str, Any],
    outcomes: Sequence[Mapping[str, Any]],
    *,
    required_successes: int,
) -> dict[str, Any]:
    """Project strict promotion evidence without performing a lifecycle mutation."""

    if (
        isinstance(required_successes, bool)
        or not isinstance(required_successes, int)
        or required_successes < 0
    ):
        raise ValueError("required promotion successes must be a non-negative integer")
    worker_id = str(worker.get("worker_id") or "")
    state = str(worker.get("state") or "").casefold()
    units = _independent_success_units(outcomes, worker_id=worker_id)
    policy_enabled = required_successes > 0
    contractor = state == "contractor"
    eligible = contractor and policy_enabled and len(units) >= required_successes
    reasons: list[str] = []
    if not contractor:
        reasons.append("Only an active contractor can be promoted.")
    if not policy_enabled:
        reasons.append("Automatic promotion is off; promotion requires an operator.")
    elif len(units) < required_successes:
        remaining = required_successes - len(units)
        reasons.append(
            f"{remaining} more independently verified successful "
            f"{'assignment is' if remaining == 1 else 'assignments are'} required."
        )
    if eligible:
        reasons.append("The configured automatic-promotion evidence threshold is satisfied.")
    return {
        "state": state,
        "human_promotion_available": contractor,
        "automatic_policy_enabled": policy_enabled,
        "eligible_for_automatic_promotion": eligible,
        "required_successes": required_successes,
        "verified_successes": len(units),
        "remaining_successes": max(0, required_successes - len(units)),
        "verified_work_units": list(units),
        "evidence_rule": (
            "Distinct accepted work units with an activation receipt and a receipt from "
            "a different verifying worker."
        ),
        "reasons": reasons,
    }


__all__ = ["promotion_readiness"]
