"""AR-266 shadow-value matrix contracts."""

from __future__ import annotations

from agency_runtime.core.evals.workforce_recall_shadow import (
    SHADOW_CASES,
    SHADOW_HOSTS,
    _grade_shadow_matrix,
)


def test_shadow_matrix_is_predeclared_identity_free_and_cross_host() -> None:
    assert SHADOW_HOSTS == ("codex", "claude", "hermes", "openclaw")
    assert [case.case_id for case in SHADOW_CASES] == [
        "facility-coordinate-integration",
        "aerial-surface-reconstruction",
        "speaker-attributed-transcript",
        "incremental-symbol-graph",
    ]
    assert len({case.category for case in SHADOW_CASES}) == len(SHADOW_CASES)
    assert len({case.target_worker for case in SHADOW_CASES}) == len(SHADOW_CASES)
    for case in SHADOW_CASES:
        assert case.target_worker not in case.outcome.casefold()
        assert case.target_worker not in case.case_id
        assert case.forbidden_workers


def test_shadow_matrix_grader_requires_every_safety_and_value_gate() -> None:
    cells = [
        {
            "host": host,
            "case_id": case.case_id,
            "category": case.category,
            "baseline_retained": True,
            "category_recall_regressed": False,
            "target_was_baseline": False,
            "target_recovered": case is SHADOW_CASES[0],
            "forbidden_activation_count": 0,
            "ineligible_activation_count": 0,
            "shadow_card_delta_count": 0,
        }
        for host in SHADOW_HOSTS
        for case in SHADOW_CASES
    ]
    report = _grade_shadow_matrix(
        cells,
        host_receipts=[
            {
                "host": host,
                "embedding_applied": True,
                "reranker_applied": True,
                "provider_fallback_count": 0,
                "roster_count": 278,
                "expected_roster_count": 278,
                "catalog_identity": "catalog-a",
                "catalog_cache_hit": ordinal > 0,
            }
            for ordinal, host in enumerate(SHADOW_HOSTS)
        ],
        stale_check={
            "catalog_identity_changed": True,
            "catalog_cache_hit": False,
            "disabled_activation_count": 0,
        },
    )

    assert report["passed"] is True
    assert report["metrics"]["baseline_retention_rate"] == 1.0
    assert report["metrics"]["recovered_vocabulary_gap_count"] == 1
    assert all(gate["passed"] for gate in report["gates"])

    broken = [dict(item) for item in cells]
    broken[0]["forbidden_activation_count"] = 1
    failed = _grade_shadow_matrix(
        broken,
        host_receipts=[
            {
                "host": host,
                "embedding_applied": True,
                "reranker_applied": True,
                "provider_fallback_count": 0,
                "roster_count": 278,
                "expected_roster_count": 278,
                "catalog_identity": "catalog-a",
                "catalog_cache_hit": ordinal > 0,
            }
            for ordinal, host in enumerate(SHADOW_HOSTS)
        ],
        stale_check={
            "catalog_identity_changed": True,
            "catalog_cache_hit": False,
            "disabled_activation_count": 0,
        },
    )
    assert failed["passed"] is False
    assert (
        next(gate for gate in failed["gates"] if gate["metric"] == "forbidden_activation_count")[
            "passed"
        ]
        is False
    )
