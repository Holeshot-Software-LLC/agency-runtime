"""Compact intent compilation and deterministic assurance tests."""

from __future__ import annotations

import pytest

from agency_runtime.core.workforce.intent import (
    COMPACT_INTENT_RESPONSE_SCHEMA,
    compact_intent_taxonomy,
    compile_intent_plan,
    enrich_intent_plan,
)
from agency_runtime.core.workforce.plan_policy import plan_policy_violations
from agency_runtime.core.workforce.staffing_verifier import StaffingContext


def _context() -> StaffingContext:
    return StaffingContext(
        host="codex",
        platform="windows",
        available_tools=frozenset(
            {
                "code-execution",
                "repository-read",
                "repository-write",
                "test-execution",
            }
        ),
        roster_generation=7,
    )


def _intent(
    *,
    artifact: str = "implementation-change",
    domains: list[str] | None = None,
    stacks: list[str] | None = None,
    capabilities: list[str] | None = None,
    novel: str = "",
) -> dict[str, object]:
    return {
        "request_summary": "Implement the requested production change.",
        "units": [
            {
                "unit_id": "unit-primary",
                "outcome": "Implement a portable async Python command-line service",
                "artifact_kind": artifact,
                "domains": domains or ["python-cli"],
                "stacks": stacks or ["python", "cli", "en"],
                "capability_ids": capabilities or ["implementation"],
                "novel_capability": novel,
                "depends_on": [],
            }
        ],
    }


def _compile(value: dict[str, object]):
    return compile_intent_plan(
        value,
        request="Implement a portable async Python command-line service.",
        context=_context(),
        known_domains=("software-engineering", "security", "quality-assurance"),
        known_stacks=("python", "typescript", "javascript"),
        known_capability_ids=(
            "analysis",
            "implementation",
            "review",
            "risk-analysis",
            "testing",
            "verification",
        ),
    )


def test_compact_schema_requires_controlled_capabilities_and_explicit_gap() -> None:
    fields = COMPACT_INTENT_RESPONSE_SCHEMA["properties"]["units"]["items"]

    assert fields["additionalProperties"] is False
    assert "capability_ids" in fields["required"]
    assert "novel_capability" in fields["required"]
    assert fields["properties"]["capability_ids"]["maxItems"] == 3
    assert compact_intent_taxonomy(
        ("security", "security"),
        ("python",),
        ("review", "analysis", "review"),
    ) == {
        "known_domains": ["security"],
        "known_stacks": ["python"],
        "known_capability_ids": ["analysis", "review"],
    }


def test_compiler_canonicalizes_noise_without_erasing_specialist_need() -> None:
    value = _intent(capabilities=["implementation", "risk-analysis"])

    plan = _compile(value)
    unit = plan.units[0]

    assert unit.domains == ("software-engineering",)
    assert unit.languages == ("python",)
    assert unit.frameworks == ()
    assert unit.required_capabilities == ("implementation", "risk-analysis")
    assert unit.lifecycle_phase == "implementation"
    assert unit.authority == "modify"
    assert unit.mutation_scope == "workspace_write"
    assert unit.required_tools == (
        "repository-read",
        "repository-write",
        "code-execution",
    )


def test_compiler_separates_known_capabilities_from_a_real_novel_gap() -> None:
    plan = _compile(_intent(novel="quantum-build-orchestration"))

    assert plan.units[0].required_capabilities == (
        "implementation",
        "quantum-build-orchestration",
    )

    with pytest.raises(ValueError, match="already exists"):
        _compile(_intent(novel="risk-analysis"))
    with pytest.raises(ValueError, match="current workforce ontology"):
        _compile(_intent(capabilities=["unknown-capability"]))


def test_code_intent_is_enriched_with_ordered_assurance_without_losing_capabilities() -> None:
    request = (
        "Implement a production Python service, add security hardening, and verify the "
        "Windows and Linux release."
    )
    primary = _compile(_intent(capabilities=["implementation", "risk-analysis"]))

    plan = enrich_intent_plan(primary, request=request, context=_context())
    by_id = {unit.unit_id: unit for unit in plan.units}

    assert by_id["unit-primary"].required_capabilities == (
        "implementation",
        "risk-analysis",
    )
    assert {
        "unit-primary",
        "unit-tests",
        "unit-code-review",
        "unit-test-results",
        "unit-security-review",
        "unit-release-verification",
    } <= set(by_id)
    assert by_id["unit-tests"].depends_on == ("unit-primary",)
    assert by_id["unit-release-verification"].depends_on == (
        "unit-code-review",
        "unit-test-results",
        "unit-security-review",
    )
    assert plan_policy_violations(request, plan) == ()


def test_documentation_intent_inherits_subject_domain_for_independent_review() -> None:
    value = _intent(
        artifact="documentation",
        domains=["marketing"],
        stacks=[],
        capabilities=["documentation"],
    )
    primary = compile_intent_plan(
        value,
        request="Write and update the marketing launch guide.",
        context=_context(),
        known_domains=("marketing", "software-engineering"),
        known_stacks=(),
        known_capability_ids=("documentation", "review"),
    )

    plan = enrich_intent_plan(
        primary,
        request="Write and update the marketing launch guide.",
        context=_context(),
    )
    review = next(unit for unit in plan.units if unit.unit_id == "unit-documentation-review")

    assert review.domains == ("marketing",)
    assert review.depends_on == ("unit-primary",)


def test_compiler_rejects_forward_dependencies_before_plan_hashing() -> None:
    value = _intent()
    value["units"][0]["depends_on"] = ["unit-later"]  # type: ignore[index]

    with pytest.raises(ValueError, match="dependencies must reference earlier units"):
        _compile(value)
