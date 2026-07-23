from __future__ import annotations

import importlib

from agency_runtime.core.evals.upstream_architecture import (
    CAPABILITIES,
    SCHEMA,
    UPSTREAM_REVISION,
    VERSION,
    run_upstream_architecture_comparison,
)


def test_upstream_architecture_comparison_is_pinned_and_truthful() -> None:
    report = run_upstream_architecture_comparison()

    assert report["schema"] == SCHEMA
    assert report["version"] == VERSION
    assert report["upstream"]["revision"] == UPSTREAM_REVISION
    assert report["upstream"]["executable_router_present"] is False
    assert report["result"] == {
        "evaluated_capability_count": len(CAPABILITIES),
        "agency_has_stronger_explicit_contract": True,
        "reason": (
            "Agency Runtime machine-enforces all evaluated routing and workforce contracts; "
            "the pinned upstream source leaves them unspecified or prompt-enforced."
        ),
    }
    assert report["evidence"]["superiority_claimed"] is False
    assert report["evidence"]["selection_outcomes_measured"] is False
    assert report["evidence"]["task_outcomes_measured"] is False


def test_upstream_architecture_capabilities_are_unique_and_evidence_backed() -> None:
    report = run_upstream_architecture_comparison()
    capabilities = report["comparison"]

    assert len(capabilities) == len({item["capability_id"] for item in capabilities})
    assert all(item["upstream_contract"] for item in capabilities)
    assert all(item["agency_contract"] for item in capabilities)
    assert all(len(item["agency_evidence"]) >= 2 for item in capabilities)
    assert {
        "per-ask-dynamic-planning",
        "whole-roster-capability-recall",
        "typed-composition-and-eligibility",
        "exact-version-activation",
        "native-child-reuse-and-budgets",
        "version-complete-caching",
    }.issubset({item["capability_id"] for item in capabilities})

    for item in capabilities:
        for reference in item["agency_evidence"]:
            module_name, attribute_path = reference.split(":", maxsplit=1)
            target = importlib.import_module(module_name)
            for attribute in attribute_path.split("."):
                target = getattr(target, attribute)
            assert target is not None
