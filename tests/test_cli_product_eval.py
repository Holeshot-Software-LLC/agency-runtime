from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

from agency_runtime.cli import eval_commands


def _args(tmp_path: Path, *, json_output: bool) -> argparse.Namespace:
    return argparse.Namespace(
        scenario="python-cli-service",
        trial_id="trial-01",
        host="codex",
        mode="agency",
        workspace=str(tmp_path),
        timeout=600.0,
        model="gpt-test",
        confirm_live_product_eval=("RUN LIVE PRODUCT EVAL python-cli-service codex agency"),
        json=json_output,
    )


def _report(*, passed: bool):
    payload = {
        "host_execution": {
            "status": "completed",
            "runtime_contract_passed": passed,
            "duration_ms": 12.5,
        },
        "validation": {
            "passed": passed,
            "workspace_digest": "sha256:artifact",
        },
        "claim_boundary": "one exact trial only",
        "passed": passed,
    }
    return SimpleNamespace(
        scenario_id="python-cli-service",
        trial_id="trial-01",
        host="codex",
        mode="agency",
        passed=passed,
        as_dict=lambda: payload,
    )


def test_product_eval_cli_passes_every_explicit_live_boundary(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    observed = {}

    def run(scenario, **kwargs):
        observed["scenario"] = scenario.scenario_id
        observed.update(kwargs)
        return _report(passed=True)

    monkeypatch.setattr(eval_commands, "run_product_trial", run)

    assert eval_commands.cmd_eval_product(_args(tmp_path, json_output=False)) == 0
    assert observed == {
        "scenario": "python-cli-service",
        "trial_id": "trial-01",
        "host": "codex",
        "mode": "agency",
        "workspace": tmp_path,
        "timeout": 600.0,
        "confirm": "RUN LIVE PRODUCT EVAL python-cli-service codex agency",
        "model": "gpt-test",
    }
    output = capsys.readouterr().out
    assert "product eval passed" in output
    assert "one exact trial only" in output


def test_product_eval_cli_returns_failure_for_failed_evidence(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        eval_commands,
        "run_product_trial",
        lambda *_args, **_kwargs: _report(passed=False),
    )

    assert eval_commands.cmd_eval_product(_args(tmp_path, json_output=True)) == 1
    assert '"passed": false' in capsys.readouterr().out
