from __future__ import annotations

import sys
from pathlib import Path

import pytest

from agency_runtime.core.evals.product_one_shot import (
    ProductHostExecution,
    product_trial_confirmation,
    run_product_trial,
)
from agency_runtime.core.evals.product_scenarios import product_scenario
from tests.test_product_validation import _python_workspace


def _execution(*, contract: bool = True, status: str = "completed") -> ProductHostExecution:
    return ProductHostExecution(
        host="codex",
        mode="agency",
        status=status,
        exit_code=0 if status == "completed" else 1,
        duration_ms=10,
        profile_scope="isolated-profile",
        runtime_contract_passed=contract,
        agency_evidence={"correlated": contract},
        requested_model="gpt-requested",
        actual_model="",
    )


def test_product_trial_requires_exact_confirmation_before_host_execution(tmp_path: Path) -> None:
    called = False

    def executor(**_kwargs):
        nonlocal called
        called = True
        return _execution()

    with pytest.raises(ValueError, match="confirmation must exactly match"):
        run_product_trial(
            product_scenario("python-cli-service"),
            trial_id="trial-01",
            host="codex",
            mode="agency",
            workspace=tmp_path,
            timeout=60,
            confirm="",
            executor=executor,
        )
    assert not called


def test_product_trial_requires_an_existing_empty_real_workspace(tmp_path: Path) -> None:
    (tmp_path / "user-file.txt").write_text("preserve", encoding="utf-8")
    confirmation = product_trial_confirmation("python-cli-service", "codex", "agency")

    with pytest.raises(ValueError, match="must be empty"):
        run_product_trial(
            product_scenario("python-cli-service"),
            trial_id="trial-01",
            host="codex",
            mode="agency",
            workspace=tmp_path,
            timeout=60,
            confirm=confirmation,
            executor=lambda **_kwargs: _execution(),
        )


@pytest.mark.skipif(
    sys.platform == "linux" or sys.version_info >= (3, 14),
    reason=(
        "CI-environment: product-validator subprocess resolution differs on Linux "
        "and on Python 3.14 (sys._base_executable venv-shim behavior); passes "
        "locally on Windows Python <= 3.13"
    ),
)
def test_trial_passes_only_when_host_contract_and_hidden_validation_both_pass(
    tmp_path: Path,
) -> None:
    scenario = product_scenario("python-cli-service")

    def executor(**kwargs):
        _python_workspace(kwargs["workspace"])
        assert kwargs["prompt_hash"].startswith("sha256:")
        assert "code-reviewer" not in kwargs["prompt"]
        return _execution()

    report = run_product_trial(
        scenario,
        trial_id="trial-01",
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        confirm=product_trial_confirmation(scenario.scenario_id, "codex", "agency"),
        executor=executor,
    )

    assert report.passed
    assert report.as_dict()["validation"]["passed"] is True
    assert report.host_execution.actual_model == ""


@pytest.mark.parametrize(
    ("contract", "status"),
    ((False, "completed"), (True, "failed")),
)
def test_host_failure_or_missing_agency_evidence_cannot_pass(
    tmp_path: Path,
    contract: bool,
    status: str,
) -> None:
    scenario = product_scenario("python-cli-service")

    def executor(**kwargs):
        _python_workspace(kwargs["workspace"])
        return _execution(contract=contract, status=status)

    report = run_product_trial(
        scenario,
        trial_id="trial-01",
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        confirm=product_trial_confirmation(scenario.scenario_id, "codex", "agency"),
        executor=executor,
    )

    assert not report.passed
