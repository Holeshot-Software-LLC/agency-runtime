"""The comparative outcome evaluator has a bounded CLI handoff."""

from __future__ import annotations

import argparse
import json

from agency_runtime.cli import eval_commands
from agency_runtime.cli.eval_commands import cmd_eval_compare, cmd_eval_full_roster


def _observation(mode: str, run_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "scenario_id": "scenario",
        "trial_id": "trial",
        "run_id": run_id,
        "host": "codex",
        "mode": mode,
        "evidence_kind": "simulated",
        "blinded_label": "A" if mode == "native_only" else "B",
        "completed": True,
        "quality_score": 0.8,
        "tests_total": 2,
        "tests_failed": 0,
        "escaped_defects": 0,
        "duration_ms": 100.0,
        "cost_usd": 0.01,
        "retries": 0,
        "duplicate_work": 0,
        "merge_conflicts": 0,
        "synthesis_failures": 0,
        "supervisor_interventions": 0,
        "delegated_units": 0 if mode == "native_only" else 1,
        "requested_model": "requested",
        "actual_model": "provider/model",
        "router": "",
    }


def test_cmd_eval_compare_prints_evidence_honest_report(tmp_path, capsys) -> None:
    source = tmp_path / "comparative.jsonl"
    rows = [
        _observation("native_only", "native-run"),
        _observation("agency_prefer", "agency-run"),
    ]
    source.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )

    assert cmd_eval_compare(argparse.Namespace(input=str(source))) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["observation_count"] == 2
    assert report["evidence_counts"]["simulated"] == 2
    assert report["modes"]["agency_prefer"]["all_evidence"]["pair_count"] == 1
    assert report["superiority_claimed"] is False


def test_cmd_eval_full_roster_prints_honest_summary(monkeypatch, capsys) -> None:
    report = {
        "passed": True,
        "roster": {
            "manifest_approved": 261,
            "manifest_quarantined": 2,
            "division_count": 17,
        },
        "gates": [
            {
                "metric": "target_candidate_recall",
                "value": 1.0,
                "operator": ">=",
                "threshold": 0.9,
                "passed": True,
            }
        ],
        "details": {"bounded": True},
    }
    monkeypatch.setattr(
        eval_commands,
        "run_full_roster_selection_eval",
        lambda *, candidate_limit: {**report, "candidate_limit": candidate_limit},
    )

    assert (
        cmd_eval_full_roster(argparse.Namespace(candidate_limit=40, json=False, no_details=False))
        == 0
    )
    output = capsys.readouterr().out
    assert "full-roster eval passed" in output
    assert "contract-only; no task-outcome or superiority claim" in output


def test_cmd_eval_full_roster_json_can_omit_details(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        eval_commands,
        "run_full_roster_selection_eval",
        lambda *, candidate_limit: {
            "passed": False,
            "roster": {},
            "gates": [],
            "details": {"candidate_limit": candidate_limit},
        },
    )

    assert (
        cmd_eval_full_roster(argparse.Namespace(candidate_limit=8, json=True, no_details=True)) == 1
    )
    assert "details" not in json.loads(capsys.readouterr().out)
