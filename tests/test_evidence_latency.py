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

from agency_runtime.cli.evidence_commands import cmd_evidence_latency
from agency_runtime.core.routing_latency import (
    DEFAULT_ROUTING_LATENCY_BUDGET_MS,
    latency_summary,
    nearest_rank_percentile,
    routing_latency_projection,
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
    assert nearest_rank_percentile(sorted(values), percentile) == expected


def test_summary_of_nothing_is_zero_not_an_error() -> None:
    assert latency_summary([]) == {
        "count": 0,
        "min_ms": 0,
        "p50_ms": 0,
        "p95_ms": 0,
        "max_ms": 0,
    }


def test_shared_projection_preserves_operator_latency_semantics() -> None:
    rows = [
        {"latency_ms": 0, "provider_ms": 0, "provider_calls": 0, "source": "computed"},
        {"latency_ms": -1, "provider_ms": 0, "provider_calls": 0, "source": "computed"},
        {"latency_ms": 10_000, "provider_ms": 7_000, "provider_calls": 2, "source": "cache"},
        {"latency_ms": 15_000, "provider_ms": 0, "provider_calls": 1, "source": "computed"},
    ]

    projection = routing_latency_projection(rows)

    assert projection["budget_ms"] == DEFAULT_ROUTING_LATENCY_BUDGET_MS
    assert projection["overall"] == {
        "count": 2,
        "min_ms": 10_000,
        "p50_ms": 10_000,
        "p95_ms": 15_000,
        "max_ms": 15_000,
    }
    assert projection["over_budget"] is False
    assert projection["by_source"] == {
        "cache": {
            "count": 1,
            "min_ms": 10_000,
            "p50_ms": 10_000,
            "p95_ms": 10_000,
            "max_ms": 10_000,
        },
        "computed": {
            "count": 1,
            "min_ms": 15_000,
            "p50_ms": 15_000,
            "p95_ms": 15_000,
            "max_ms": 15_000,
        },
    }
    assert projection["split"]["decisions"] == 1
    assert projection["split"]["unattributed_decisions"] == 1
    assert projection["split"]["provider_ms"]["p50_ms"] == 7_000
    assert projection["split"]["agency_ms"]["p50_ms"] == 3_000
    assert projection["split"]["calls_per_decision"] == 2.0
    assert projection["slowest"] == [rows[3], rows[2]]


def test_shared_projection_fails_only_when_p95_exceeds_budget() -> None:
    rows = [{"latency_ms": 15_001, "provider_ms": 1, "provider_calls": 1, "source": "computed"}]

    assert routing_latency_projection(rows)["over_budget"] is True
    assert routing_latency_projection(rows, budget_ms=15_001)["over_budget"] is False


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


def test_an_existing_database_gains_the_latency_column(tmp_path: Path) -> None:
    """A column in the DDL but not the staleness predicate never lands.

    A database already stamped at the current schema version only migrates when
    startup calls it stale, and that predicate derives its required columns from
    MODEL_RECEIPT_MIGRATED_COLUMNS. Declaring the column in the CREATE TABLE
    alone would leave every existing install stamped current, skip the migration,
    and fail at query time on exactly the installs that needed it -- while a
    fresh test database, built from the full DDL, passed.
    """

    import sqlite3

    from agency_runtime.core.store.schema import MODEL_RECEIPT_MIGRATED_COLUMNS
    from agency_runtime.core.store.sqlite import _v20_receipt_schema_is_current

    db = tmp_path / "agency.db"
    Store(str(db))

    for column, _definition in MODEL_RECEIPT_MIGRATED_COLUMNS:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            columns = [
                row["name"]
                for row in conn.execute("PRAGMA table_info(model_receipts)")
                if row["name"] != column
            ]
            joined = ", ".join(columns)
            conn.executescript(
                "PRAGMA foreign_keys=OFF;\n"
                "BEGIN;\n"
                f"CREATE TABLE model_receipts_old AS SELECT {joined} FROM model_receipts;\n"
                "DROP TABLE model_receipts;\n"
                "ALTER TABLE model_receipts_old RENAME TO model_receipts;\n"
                "COMMIT;"
            )
            assert not _v20_receipt_schema_is_current(conn), (
                f"the staleness predicate does not require {column}, so no existing "
                "database would ever be migrated to add it"
            )
        finally:
            conn.close()

        # Reopening runs the migration that the predicate just demanded.
        Store(str(db))
        conn = sqlite3.connect(db)
        try:
            present = {row[1] for row in conn.execute("PRAGMA table_info(model_receipts)")}
        finally:
            conn.close()
        assert column in present


def test_the_split_is_read_back_from_receipts_not_modelled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Provider time comes from the calls; Agency's share is the remainder."""

    db = tmp_path / "agency.db"
    store = Store(str(db))
    _decision(store, 1, latency_ms=40_000)
    for _ in range(2):
        store.record_model_receipt(
            trace_id=_trace(1),
            session_id=SESSION,
            host="claude",
            resolved_model="sonnet",
            source="wrapper",
            latency_ms=15_000,
            status="success",
        )

    cmd_evidence_latency(_args(db))
    payload = json.loads(capsys.readouterr().out)

    split = payload["split"]
    assert split["decisions"] == 1
    assert split["calls_per_decision"] == 2.0
    assert split["provider_ms"]["p50_ms"] == 30_000
    assert split["agency_ms"]["p50_ms"] == 10_000


def test_decisions_whose_receipts_predate_the_column_are_not_blamed_on_agency(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A 0 receipt means unreported, never a free provider call.

    Treating it as zero provider time would attribute an entire turn to Agency's
    own work and point any optimisation at the wrong place.
    """

    db = tmp_path / "agency.db"
    store = Store(str(db))
    _decision(store, 1, latency_ms=40_000)
    store.record_model_receipt(
        trace_id=_trace(1),
        session_id=SESSION,
        host="claude",
        resolved_model="sonnet",
        source="wrapper",
        status="success",
    )

    cmd_evidence_latency(_args(db))
    payload = json.loads(capsys.readouterr().out)

    assert payload["split"]["decisions"] == 0
    assert payload["split"]["unattributed_decisions"] == 1
    assert payload["split"]["agency_ms"]["p50_ms"] == 0


def test_mixed_timed_and_legacy_receipts_remain_unattributed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One timed call cannot make an unknown sibling call attributable."""

    db = tmp_path / "agency.db"
    store = Store(str(db))
    _decision(store, 1, latency_ms=40_000)
    for latency_ms in (0, 15_000):
        store.record_model_receipt(
            trace_id=_trace(1),
            session_id=SESSION,
            host="claude",
            resolved_model="sonnet",
            source="wrapper",
            latency_ms=latency_ms,
            status="success",
        )

    cmd_evidence_latency(_args(db))
    payload = json.loads(capsys.readouterr().out)

    assert payload["split"]["decisions"] == 0
    assert payload["split"]["unattributed_decisions"] == 1
    assert payload["split"]["provider_ms"]["p50_ms"] == 0
    assert payload["split"]["agency_ms"]["p50_ms"] == 0
