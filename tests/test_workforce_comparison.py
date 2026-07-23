"""Read-only duplicate and consolidation evidence tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agency_runtime.core.workforce.comparison import (
    compare_workers,
    consolidation_candidates,
    nearest_workers,
)
from agency_runtime.core.workforce.contract import CompositionContract
from agency_runtime.core.workforce.known_installer import known_contractor_package


def _typescript():
    return known_contractor_package("typescript-application-engineer").workforce_contract


def test_nearest_workers_keep_language_specialists_distinct() -> None:
    typescript = _typescript()
    python = known_contractor_package("python-application-engineer").workforce_contract
    backend = known_contractor_package("backend-service-engineer").workforce_contract

    rows = nearest_workers(typescript, (typescript, python, backend), limit=2)

    assert [item.right for item in rows] == [
        "python-application-engineer",
        "backend-service-engineer",
    ]
    assert all(item.recommendation == "keep_distinct" for item in rows)
    assert all("different stack ownership" in item.reasons for item in rows)


def test_exact_agency_overlap_is_only_a_human_merge_review_candidate() -> None:
    left = _typescript()
    right = replace(
        left,
        worker_id="worker:typescript-build-contractor",
        agent_id="typescript-build-contractor",
        display_name="TypeScript Build Contractor",
    )

    comparison = compare_workers(left, right)
    candidates = consolidation_candidates((left, right))

    assert comparison.score == 1.0
    assert comparison.recommendation == "review_merge"
    assert comparison.coherent_amendment is True
    assert comparison.merge_review_candidate is True
    assert candidates == (comparison,)
    assert comparison.as_dict()["recommendation"] == "review_merge"


def test_conflicts_residents_and_invalid_bounds_never_become_merge_authority() -> None:
    left = _typescript()
    conflicted = replace(
        left,
        worker_id="worker:conflicted",
        agent_id="conflicted",
        composition=CompositionContract(same_context_conflicts=(left.agent_id,)),
    )
    conflict = compare_workers(left, conflicted)
    resident = compare_workers(
        replace(left, worker_id="worker:resident", agent_id="chief-of-staff"),
        replace(left, worker_id="worker:peer", agent_id="peer"),
    )

    assert conflict.recommendation == "keep_distinct"
    assert "typed conflict requires separation" in conflict.reasons
    assert resident.recommendation == "keep_distinct"
    assert "resident managers are protected" in resident.reasons
    with pytest.raises(ValueError, match="distinct workers"):
        compare_workers(left, left)
    for invalid in (True, 0, 101):
        with pytest.raises(ValueError, match="from 1 through 100"):
            nearest_workers(left, (left,), limit=invalid)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="from 1 through 100"):
            consolidation_candidates((left,), limit=invalid)  # type: ignore[arg-type]
