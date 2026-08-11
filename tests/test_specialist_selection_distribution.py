"""Persisted specialist-selection distribution contracts."""

from __future__ import annotations

from pathlib import Path

from agency_runtime.core.selection_distribution import specialist_selection_distribution
from agency_runtime.core.store.sqlite import Store

SESSION = "33333333-3333-4333-8333-333333333333"
HASH = "a" * 64


def _trace(index: int) -> str:
    return f"44444444-4444-4444-8444-{index:012d}"


def _record(store: Store, index: int, selected_ids: list[str]) -> None:
    store.record_routing_decision(
        trace_id=_trace(index),
        session_id=SESSION,
        query_hash=HASH,
        context_fingerprint=HASH,
        decision={
            "status": "accepted",
            "selected_ids": selected_ids,
            "semantic_ids": [],
            "confidence": 0.9,
        },
    )


def test_distribution_keeps_decision_and_occurrence_denominators_distinct() -> None:
    result = specialist_selection_distribution(
        (("alpha", "beta"), ("alpha",), (), ("beta", "gamma")),
        active_roster_size=9,
    )

    assert result["decisions_with_selections"] == 3
    assert result["selection_occurrences"] == 5
    assert result["distinct_selected_specialists"] == 3
    assert result["active_roster_size"] == 9
    assert result["top_10_selection_occurrences"] == 5
    assert result["top_10_share_of_selection_occurrences"] == 1.0
    assert result["top_specialists"] == [
        {
            "slug": "alpha",
            "decisions_containing_specialist": 2,
            "share_of_decisions_with_selections": 2 / 3,
            "selection_occurrences": 2,
            "share_of_selection_occurrences": 2 / 5,
        },
        {
            "slug": "beta",
            "decisions_containing_specialist": 2,
            "share_of_decisions_with_selections": 2 / 3,
            "selection_occurrences": 2,
            "share_of_selection_occurrences": 2 / 5,
        },
        {
            "slug": "gamma",
            "decisions_containing_specialist": 1,
            "share_of_decisions_with_selections": 1 / 3,
            "selection_occurrences": 1,
            "share_of_selection_occurrences": 1 / 5,
        },
    ]
    assert result["long_tail"] == {
        "specialist_count": 0,
        "decisions_containing_specialist": 0,
        "share_of_decisions_with_selections": 0.0,
        "selection_occurrences": 0,
        "share_of_selection_occurrences": 0.0,
    }


def test_distribution_bounds_the_top_list_and_aggregates_the_long_tail() -> None:
    result = specialist_selection_distribution(
        ((f"specialist-{index:03d}",) for index in range(51)),
        active_roster_size=51,
    )

    assert len(result["top_specialists"]) == 50
    assert result["top_specialists"][0]["slug"] == "specialist-000"
    assert result["top_10_selection_occurrences"] == 10
    assert result["top_10_share_of_selection_occurrences"] == 10 / 51
    assert result["long_tail"] == {
        "specialist_count": 1,
        "decisions_containing_specialist": 1,
        "share_of_decisions_with_selections": 1 / 51,
        "selection_occurrences": 1,
        "share_of_selection_occurrences": 1 / 51,
    }


def test_long_tail_decision_share_deduplicates_multi_specialist_decisions() -> None:
    result = specialist_selection_distribution(
        ((f"specialist-{index:03d}" for index in range(52)),),
        active_roster_size=52,
    )

    assert result["long_tail"] == {
        "specialist_count": 2,
        "decisions_containing_specialist": 1,
        "share_of_decisions_with_selections": 1.0,
        "selection_occurrences": 2,
        "share_of_selection_occurrences": 2 / 52,
    }


def test_store_distribution_reads_all_retained_routing_decisions(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    _record(store, 1, ["alpha", "beta"])
    _record(store, 2, ["alpha"])
    _record(store, 3, [])

    assert store.specialist_selection_distribution() == {
        "decisions_with_selections": 2,
        "distinct_selected_specialists": 2,
        "selection_occurrences": 3,
        "active_roster_size": 0,
        "selection_bearing_decision_scan_limit": 10_000,
        "selection_bearing_decision_scan_truncated": False,
        "top_10_selection_occurrences": 3,
        "top_10_share_of_selection_occurrences": 1.0,
        "top_specialists": [
            {
                "slug": "alpha",
                "decisions_containing_specialist": 2,
                "share_of_decisions_with_selections": 1.0,
                "selection_occurrences": 2,
                "share_of_selection_occurrences": 2 / 3,
            },
            {
                "slug": "beta",
                "decisions_containing_specialist": 1,
                "share_of_decisions_with_selections": 0.5,
                "selection_occurrences": 1,
                "share_of_selection_occurrences": 1 / 3,
            },
        ],
        "long_tail": {
            "specialist_count": 0,
            "decisions_containing_specialist": 0,
            "share_of_decisions_with_selections": 0.0,
            "selection_occurrences": 0,
            "share_of_selection_occurrences": 0.0,
        },
    }
