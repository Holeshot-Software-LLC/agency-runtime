from __future__ import annotations

import pytest

from agency_runtime.core.evals.product_scenarios import (
    PRODUCT_SCENARIO_SCHEMA_VERSION,
    PRODUCT_SCENARIOS,
    product_scenario,
)


def test_product_suite_has_six_distinct_complete_application_contracts() -> None:
    assert PRODUCT_SCENARIO_SCHEMA_VERSION == 1
    assert [item.scenario_id for item in PRODUCT_SCENARIOS] == [
        "python-cli-service",
        "typescript-node-application",
        "python-api-typescript-dashboard",
        "cross-platform-installer-config",
        "authenticated-data-application",
        "observability-failure-recovery",
    ]
    assert all(item.platforms == ("windows", "linux") for item in PRODUCT_SCENARIOS)
    assert all(len(item.files) >= 3 and len(item.acceptance) >= 4 for item in PRODUCT_SCENARIOS)
    assert len({check.check_id for item in PRODUCT_SCENARIOS for check in item.acceptance}) == sum(
        len(item.acceptance) for item in PRODUCT_SCENARIOS
    )


def test_product_contracts_are_portable_bounded_and_do_not_preselect_workers() -> None:
    forbidden = {
        "code-reviewer",
        "technical-writer",
        "software-test-engineer",
        "agents-orchestrator",
        "chief-of-staff",
    }
    for scenario in PRODUCT_SCENARIOS:
        paths = [item.path for item in scenario.files]
        assert len(paths) == len(set(paths))
        assert all(
            "\\" not in path and not path.startswith("/") and ".." not in path for path in paths
        )
        prompt = scenario.prompt(trial_id="trial-01")
        assert len(prompt.encode("utf-8")) < 16 * 1024
        assert "trial-01" in prompt
        assert not forbidden.intersection(prompt.casefold().split())
        assert "Do not use network access" in prompt


def test_product_scenario_lookup_is_normalized_and_closed() -> None:
    assert product_scenario("  PYTHON-CLI-SERVICE ") is PRODUCT_SCENARIOS[0]
    with pytest.raises(ValueError, match="unknown product evaluation scenario"):
        product_scenario("invented")
