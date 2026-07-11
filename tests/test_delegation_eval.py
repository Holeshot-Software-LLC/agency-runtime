"""Tests for deterministic delegation evaluation harness."""

from __future__ import annotations

import json

from agency_runtime.cli.main import main
from agency_runtime.core.evals.delegation import run_delegation_eval


def test_delegation_eval_harness_passes_core_contracts() -> None:
    report = run_delegation_eval()

    assert report["suite"] == "delegation"
    assert report["passed"] is True
    names = {case["name"] for case in report["cases"]}
    assert {
        "detect_numbered_list",
        "detect_status_query_no_delegate",
        "context_shows_opportunity_without_specialist_match",
        "all_adapters_track_evidence",
        "all_adapters_capture_model_receipts",
        "suggestions_are_persisted",
        "pre_verify_blocks_open_suggestions",
        "delegate_task_promotes_suggestion",
        "agency_agents_delegate_records_event",
        "recorded_delegation_blocker_is_accepted",
        "skipped_blocker_renders_in_header",
        "generated_no_delegation_explanation_is_rejected",
    } <= names


def test_cli_eval_delegation_json(capsys) -> None:
    code = main(["eval", "delegation", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["suite"] == "delegation"
    assert payload["passed"] is True
