"""What does Agency's own routing cost a turn?

`routing_decisions.latency_ms` was the only timing column in the schema and
nothing read it, so the cost of an eligible turn was invisible unless someone
opened the database by hand. These tests pin the two things that decide whether
the number means anything: which rows are counted, and where the budget line
falls.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from agency_runtime.cli.evidence_commands import (
    _latency_summary,
    _percentile,
    cmd_evidence_latency,
)
from agency_runtime.core.store.sqlite import Store

SESSION = "33333333-3333-4333-8333-333333333333"
_HASH = "a" * 64


def _trace(index: int) -> str:
    return f"44444444-4444-4444-8444-{index:012d}"


def _decision(store: Store, index: int, *, latency_ms: int, cache_hit: bool = False) -> None:
    """Record one decision.

    ``source`` is a closed vocabulary derived by ``project_routing_decision``
    rather than a free string, so the only honest way to produce a second
    source here is to record an actual cache hit.
    """

    store.record_routing_decision(
        trace_id=_trace(index),
        session_id=SESSION,
        query_hash=_HASH,
        context_fingerprint=_HASH,
        decision={
            "status": "accepted",
            "selected_ids": [],
            "semantic_ids": [],
            "confidence": 0.9,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
        },
    )


def _args(db: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "db": str(db),
        "source": None,
        "limit": 200,
        "budget_ms": 15000,
        "json": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


@pytest.mark.parametrize(
    ("values", "percentile", "expected"),
    [
        ([10], 50, 10),
        ([10, 20], 50, 10),
        ([10, 20, 30, 40], 50, 20),
        ([10, 20, 30, 40], 95, 40),
        ([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95, 10),
        ([], 95, 0),
    ],
)
def test_percentile_uses_nearest_rank(values: list[int], percentile: int, expected: int) -> None:
    # Nearest-rank never interpolates a latency that was never observed, which
    # matters when the whole point is the tail an operator actually felt.
    assert _percentile(sorted(values), percentile) == expected


def test_summary_of_nothing_is_zero_not_an_error() -> None:
    assert _latency_summary([]) == {
        "count": 0,
        "min_ms": 0,
        "p50_ms": 0,
        "p95_ms": 0,
        "max_ms": 0,
    }


def test_zero_latency_decisions_are_not_counted_as_fast_turns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Both writers store 0 when no provider call was spent.

    Counting those would report Agency as cheap in exact proportion to how
    often it did nothing -- the one way this surface could lie in the
    reassuring direction.
    """

    db = tmp_path / "agency.db"
    store = Store(str(db))
    for index in range(8):
        _decision(store, index, latency_ms=0)
    _decision(store, 100, latency_ms=30_000)
    _decision(store, 101, latency_ms=40_000)

    exit_code = cmd_evidence_latency(_args(db))
    payload = json.loads(capsys.readouterr().out)

    # Eight of ten decisions cost nothing. Counting them would report p50 as 0
    # and pass the budget, which is the one way this surface could lie in the
    # reassuring direction.
    assert payload["overall"]["count"] == 2
    assert payload["overall"]["p50_ms"] == 30_000
    assert payload["by_source"]["computed"]["count"] == 2
    assert exit_code == 1


def test_exit_status_gates_on_the_budget(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "agency.db"
    store = Store(str(db))
    _decision(store, 1, latency_ms=9_000)
    _decision(store, 2, latency_ms=11_000)

    within = cmd_evidence_latency(_args(db, budget_ms=15_000))
    payload = json.loads(capsys.readouterr().out)
    assert within == 0
    assert payload["over_budget"] is False

    over = cmd_evidence_latency(_args(db, budget_ms=10_000))
    payload = json.loads(capsys.readouterr().out)
    assert over == 1
    assert payload["over_budget"] is True
    assert payload["budget_ms"] == 10_000


def test_sources_are_reported_separately(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # One slow source must not be hidden inside a healthy aggregate.
    db = tmp_path / "agency.db"
    store = Store(str(db))
    _decision(store, 1, latency_ms=1_000, cache_hit=True)
    _decision(store, 2, latency_ms=1_000, cache_hit=True)
    _decision(store, 3, latency_ms=90_000)

    cmd_evidence_latency(_args(db))
    payload = json.loads(capsys.readouterr().out)

    assert payload["by_source"]["cache"]["p95_ms"] == 1_000
    assert payload["by_source"]["computed"]["p95_ms"] == 90_000
    # A cheap cached path must not disguise an expensive computed one.
    assert payload["overall"]["p95_ms"] == 90_000


def test_an_empty_store_reports_nothing_rather_than_passing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No data must not read as a healthy zero."""

    db = tmp_path / "agency.db"
    Store(str(db))

    exit_code = cmd_evidence_latency(_args(db, json=False))
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "no routing decision has recorded a latency yet" in output
    assert "✅" not in output
