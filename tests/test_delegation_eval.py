"""Tests for deterministic delegation evaluation harness."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from agency_runtime.cli.main import main
from agency_runtime.core.evals import delegation as delegation_eval
from agency_runtime.core.evals.delegation import _require, run_delegation_eval


def test_delegation_eval_harness_passes_core_contracts() -> None:
    report = run_delegation_eval()

    assert report["suite"] == "delegation"
    assert report["passed"] is True
    names = {case["name"] for case in report["cases"]}
    assert {
        "detect_numbered_list",
        "detect_status_query_no_delegate",
        "all_adapters_track_evidence",
        "all_adapters_capture_model_receipts",
    } <= names


def test_cli_eval_delegation_json(capsys) -> None:
    code = main(["eval", "delegation", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["suite"] == "delegation"
    assert payload["passed"] is True


def test_eval_requirement_is_not_an_optimization_sensitive_assert() -> None:
    with pytest.raises(AssertionError, match="durable check"):
        _require(False, "durable check")


def test_eval_helpers_cover_authoritative_default_and_case_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fields = {
        "agencies_loaded": "none",
        "agencies_delegated": "none",
        "skills_loaded": "none",
        "actual_model_selected": "unknown -> unavailable - no model receipt recorded",
        "why": "reason_codes=test",
        "how_it_shaped_outcome": "effect_codes=test",
    }
    monkeypatch.setattr(
        delegation_eval,
        "fill_header_fields",
        lambda *_args, **_kwargs: dict(fields),
    )
    assert delegation_eval._header(object()) == delegation_eval.format_header(fields)

    failed = delegation_eval._run_case(
        "expected-failure",
        lambda: _require(False, "bounded failure"),
    )
    assert failed == {
        "name": "expected-failure",
        "passed": False,
        "error": "bounded failure",
    }


def test_model_receipt_eval_fails_when_adapter_records_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delegation_eval.Store, "get_model_receipt", lambda *_args: None)

    with pytest.raises(AssertionError, match="model receipt is missing"):
        delegation_eval._case_all_adapters_capture_model_receipts()


def test_eval_requirement_survives_real_optimized_interpreter() -> None:
    script = """
from agency_runtime.core.evals.delegation import _require

try:
    _require(False, "durable optimized check")
except AssertionError:
    raise SystemExit(0)
raise SystemExit(17)
"""
    # Fixed local interpreter and static source; no shell or caller input.
    completed = subprocess.run(
        [sys.executable, "-O", "-c", script],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
