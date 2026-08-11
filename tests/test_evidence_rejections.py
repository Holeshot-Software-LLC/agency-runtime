"""Rule 8, made auditable: which turns did Agency withhold, and which was it blind for?

Rule 8 draws exactly one line. Agency may cost a user a turn only when its
verifier evaluated the response and rejected it; Agency being unable to verify
or persist its own evidence is not a finding about the response and must
publish. Both outcomes close a run with a distinguishable status, so the rule
can be read back off the store instead of being a claim about the code.

These tests pin the classification, because the whole value of the surface is
that a status lands on the correct side of that line.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from agency_runtime.cli.evidence_commands import cmd_evidence_rejections
from agency_runtime.core.store.evidence import (
    PUBLISHED_ANYWAY_RUN_STATUSES,
    WITHHELD_RUN_STATUSES,
)
from agency_runtime.core.store.sqlite import Store

SESSION = "11111111-1111-4111-8111-111111111111"


def _closed_run(store: Store, trace_id: str, *, status: str, host: str = "claude") -> None:
    store.create_run(trace_id=trace_id, session_id=SESSION, host=host)
    assert store.close_turn_evidence(SESSION, trace_id, status=status) == 1


def _trace(index: int) -> str:
    return f"22222222-2222-4222-8222-{index:012d}"


def _args(db: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "db": str(db),
        "host": None,
        "limit": 50,
        "json": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_the_two_status_sets_never_overlap() -> None:
    # The surface's entire meaning is the partition. An overlap would put one
    # run on both sides of rule 8's line and quietly make the count wrong.
    assert not (WITHHELD_RUN_STATUSES & PUBLISHED_ANYWAY_RUN_STATUSES)


def test_a_verifier_rejection_is_withheld_and_gates_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = Store(tmp_path / "rejections.db")
    _closed_run(store, _trace(1), status="response_invalid")

    exit_code = cmd_evidence_rejections(_args(tmp_path / "rejections.db"))

    payload = json.loads(capsys.readouterr().out)
    assert [row["status"] for row in payload["withheld"]] == ["response_invalid"]
    assert payload["published_anyway"] == []
    # Usable as a gate: a withheld turn is the exceptional outcome.
    assert exit_code == 1


def test_agency_being_blind_is_never_counted_as_a_rejection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # This is the distinction rule 8 turns on. `preflight_failed` and
    # `verification_failed` are Agency's own machinery failing -- reporting them
    # as rejections would recreate exactly the confusion that made an unfixed
    # fail-closed path look like a deliberate policy for a whole session.
    store = Store(tmp_path / "blind.db")
    _closed_run(store, _trace(2), status="preflight_failed")
    _closed_run(store, _trace(3), status="verification_failed")

    exit_code = cmd_evidence_rejections(_args(tmp_path / "blind.db"))

    payload = json.loads(capsys.readouterr().out)
    assert payload["withheld"] == []
    assert {row["status"] for row in payload["published_anyway"]} == {
        "preflight_failed",
        "verification_failed",
    }
    assert exit_code == 0


def test_a_completed_turn_appears_on_neither_side(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = Store(tmp_path / "completed.db")
    _closed_run(store, _trace(4), status="completed")

    exit_code = cmd_evidence_rejections(_args(tmp_path / "completed.db"))

    payload = json.loads(capsys.readouterr().out)
    assert payload["withheld"] == []
    assert payload["published_anyway"] == []
    assert exit_code == 0


def test_host_filter_reads_one_host_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = Store(tmp_path / "hosts.db")
    _closed_run(store, _trace(5), status="response_invalid", host="claude")
    _closed_run(store, _trace(6), status="response_invalid", host="codex")

    cmd_evidence_rejections(_args(tmp_path / "hosts.db", host="codex"))

    payload = json.loads(capsys.readouterr().out)
    assert [row["host"] for row in payload["withheld"]] == ["codex"]


def test_the_limit_is_bounded_rather_than_trusted(tmp_path: Path) -> None:
    # The store read is operator-facing, so an absurd limit must not become an
    # unbounded query.
    store = Store(tmp_path / "bounds.db")
    _closed_run(store, _trace(7), status="response_invalid")

    assert store.get_withheld_and_published_runs(limit=10**9)
    assert store.get_withheld_and_published_runs(limit=0)
    assert store.get_withheld_and_published_runs(limit=-5)


def test_text_output_does_not_claim_blind_turns_were_published(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Runs closed before the rule-8 fix were DENIED on this exact condition, so
    # the surface must not retroactively describe them as having gone out.
    store = Store(tmp_path / "wording.db")
    _closed_run(store, _trace(8), status="preflight_failed")

    cmd_evidence_rejections(_args(tmp_path / "wording.db", json=False))

    out = capsys.readouterr().out
    assert "withheld by Agency: none" in out
    assert "Agency was blind" in out
    assert "before the fix they were denied" in out
