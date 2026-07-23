"""Compact intent compilation and deterministic assurance tests."""

from __future__ import annotations

import pytest

from agency_runtime.core.workforce.intent import (
    COMPACT_INTENT_RESPONSE_SCHEMA,
    COMPACT_INTENT_SYSTEM,
    compact_intent_taxonomy,
    compile_intent_plan,
    enrich_intent_plan,
)
from agency_runtime.core.workforce.lifecycle_roles import role_anchors
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


def _compile(
    value: dict[str, object],
    *,
    request: str = "Implement a portable async Python command-line service.",
):
    return compile_intent_plan(
        value,
        request=request,
        context=_context(),
        known_domains=("software-engineering", "security", "quality-assurance"),
        known_stacks=("python", "typescript", "javascript"),
        known_capability_ids=(
            "analysis",
            "architecture",
            "automation",
            "data-analysis",
            "design",
            "documentation",
            "governance",
            "ideation",
            "implementation",
            "operations",
            "planning",
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


def test_compact_system_preserves_evidence_before_operational_planning() -> None:
    assert "analysis/discovery unit distinct from the dependent plan" in COMPACT_INTENT_SYSTEM
    assert "both planning and operations" in COMPACT_INTENT_SYSTEM
    assert "Use threat-modeling only for prospective systems" in COMPACT_INTENT_SYSTEM


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


@pytest.mark.parametrize("surface", ["product", "accessibility"])
def test_compiler_does_not_turn_surface_label_into_code_authority(surface: str) -> None:
    value = _intent(
        domains=["software-engineering", surface],
        stacks=["python", "typescript"],
    )

    plan = _compile(
        value,
        request="Build a Python API and TypeScript product dashboard.",
    )

    assert plan.units[0].domains == ("software-engineering",)


@pytest.mark.parametrize(
    "generic_capability",
    ["analysis", "architecture", "design", "operations", "planning"],
)
def test_compiler_drops_redundant_generic_implementation_capability(
    generic_capability: str,
) -> None:
    plan = _compile(_intent(capabilities=["implementation", generic_capability]))

    assert plan.units[0].required_capabilities == ("implementation",)


def test_compiler_treats_research_as_a_method_within_a_subject_domain() -> None:
    value = _intent(
        artifact="analysis",
        domains=["healthcare", "research"],
        stacks=[],
        capabilities=["analysis", "research"],
    )
    value["units"][0]["outcome"] = "Summarize supplied clinical evidence and its limitations"

    plan = compile_intent_plan(
        value,
        request="Summarize the supplied clinical evidence and its limitations.",
        context=_context(),
        known_domains=("healthcare", "research"),
        known_stacks=(),
        known_capability_ids=("analysis", "research"),
    )

    assert plan.units[0].domains == ("healthcare",)
    assert plan.units[0].required_capabilities == ("analysis", "research")


def test_compiler_does_not_turn_software_diagnosis_into_incident_research() -> None:
    value = _intent(
        artifact="analysis",
        domains=["software-engineering", "research"],
        stacks=[],
        capabilities=["analysis", "investigation"],
    )
    value["units"][0]["outcome"] = "Diagnose runtime routing and response-header failures"

    plan = compile_intent_plan(
        value,
        request="Diagnose why a runtime hook failed to enforce its response header.",
        context=_context(),
        known_domains=("software-engineering", "research"),
        known_stacks=(),
        known_capability_ids=("analysis", "investigation"),
    )

    assert plan.units[0].domains == ("software-engineering",)
    assert plan.units[0].required_capabilities == ("analysis",)


def test_compiler_drops_a_domain_misplaced_as_a_capability() -> None:
    value = _intent(
        artifact="review-report",
        domains=["accessibility"],
        stacks=[],
        capabilities=["review", "accessibility"],
    )
    value["units"][0]["outcome"] = "Accessibility findings for the user interface"

    plan = compile_intent_plan(
        value,
        request="Review the user interface for accessibility issues.",
        context=_context(),
        known_domains=("accessibility",),
        known_stacks=(),
        known_capability_ids=("review",),
    )

    assert plan.units[0].domains == ("accessibility",)
    assert plan.units[0].required_capabilities == ("review",)


def test_compiler_keeps_accessibility_review_in_its_specialist_domain() -> None:
    value = _intent(
        artifact="review-report",
        domains=["accessibility", "software-engineering"],
        stacks=[],
        capabilities=["review"],
    )
    value["units"][0]["outcome"] = "Accessibility review findings"  # type: ignore[index]

    unit = _compile(
        value,
        request="Independently review the dashboard accessibility.",
    ).units[0]

    assert unit.domains == ("accessibility",)


def test_compiler_bounds_locally_derived_evidence_for_long_model_outcomes() -> None:
    value = _intent()
    value["units"][0]["outcome"] = "A" * 512  # type: ignore[index]

    unit = _compile(value).units[0]

    assert unit.acceptance_evidence == (
        "Evidence proves the requested implementation change outcome.",
    )
    assert len(unit.acceptance_evidence[0]) <= 128


def test_compiler_treats_a_prose_recovery_plan_as_a_plan_not_a_docs_mutation() -> None:
    value = _intent(
        artifact="documentation",
        domains=["security"],
        stacks=[],
        capabilities=["planning", "risk-analysis"],
    )
    value["units"][0]["outcome"] = (  # type: ignore[index]
        "Prepare a reversible recovery plan with rollback decision criteria"
    )

    unit = _compile(value).units[0]

    assert unit.artifact_kind == "plan"
    assert unit.lifecycle_phase == "planning"
    assert unit.authority == "plan"
    assert unit.mutation_scope == "read_only"
    assert unit.required_capabilities == ("planning", "risk-analysis")
    assert unit.required_tools == ("repository-read",)


def test_compiler_treats_brand_governance_guidance_as_a_design_plan() -> None:
    value = _intent(
        artifact="documentation",
        domains=["design", "marketing"],
        stacks=[],
        capabilities=["documentation", "governance"],
    )
    value["units"][0]["outcome"] = (  # type: ignore[index]
        "Brand-governance guidance defining identity principles and usage rules"
    )

    unit = _compile(value, request="Create brand-governance guidance.").units[0]

    assert unit.artifact_kind == "plan"
    assert unit.domains == ("design",)
    assert unit.authority == "plan"


def test_compiler_keeps_playful_interface_implementation_in_design_domain() -> None:
    value = _intent(
        domains=["design", "software-engineering"],
        stacks=[],
        capabilities=["design", "implementation"],
    )
    value["units"][0]["outcome"] = (  # type: ignore[index]
        "Implement bounded playful interface details"
    )

    unit = _compile(value, request="Add bounded playful interface details.").units[0]

    assert unit.domains == ("design",)
    assert unit.required_capabilities == ("implementation",)


def test_compiler_drops_redundant_data_analysis_from_analysis_artifact() -> None:
    value = _intent(
        artifact="analysis",
        domains=["finance"],
        stacks=[],
        capabilities=["analysis", "data-analysis"],
    )
    value["units"][0]["outcome"] = "Analyze supplied accounts-payable exceptions"  # type: ignore[index]

    unit = _compile(value, request="Analyze supplied accounts-payable exceptions.").units[0]

    assert unit.required_capabilities == ("analysis",)


def test_compiler_keeps_test_artifacts_in_the_quality_assurance_domain() -> None:
    value = _intent(
        artifact="test-code",
        domains=["software-engineering"],
        stacks=[],
        capabilities=["testing"],
    )

    unit = _compile(value).units[0]

    assert unit.domains == ("quality-assurance",)
    assert unit.lifecycle_phase == "testing"


def test_compiler_drops_ungrounded_automation_but_preserves_an_explicit_request() -> None:
    value = _intent(capabilities=["implementation", "automation"])

    inferred = _compile(value).units[0]
    requested = _compile(
        value,
        request="Automate the portable Python command-line workflow.",
    ).units[0]

    assert inferred.required_capabilities == ("implementation",)
    assert requested.required_capabilities == ("implementation", "automation")


def test_compiler_drops_a_concrete_stack_absent_from_the_request() -> None:
    value = _intent(stacks=["typescript"])

    unit = _compile(
        value,
        request="Implement cancellation-safe indexing in the language server.",
    ).units[0]

    assert unit.languages == ()
    assert unit.frameworks == ()


def test_compiler_routes_a_staffing_audit_to_workforce_governance() -> None:
    value = _intent(
        artifact="review-report",
        domains=["software-engineering"],
        stacks=[],
        capabilities=["review", "risk-analysis"],
    )
    value["units"][0]["outcome"] = "Audit the workforce staffing decision"  # type: ignore[index]

    unit = _compile(value).units[0]

    assert unit.domains == ("workforce-governance",)


def test_compiler_keeps_security_code_path_mapping_in_software_discovery() -> None:
    value = _intent(
        artifact="analysis",
        domains=["software-engineering", "security"],
        stacks=[],
        capabilities=["analysis"],
    )
    value["units"][0]["outcome"] = "Map the security patch's affected code path"  # type: ignore[index]

    unit = _compile(value).units[0]

    assert unit.domains == ("software-engineering",)


def test_compiler_keeps_runtime_agent_selection_diagnosis_in_software_discovery() -> None:
    value = _intent(
        artifact="analysis",
        domains=["workforce-governance"],
        stacks=[],
        capabilities=["analysis"],
    )
    value["units"][0]["outcome"] = (  # type: ignore[index]
        "Trace why runtime routing selected unrelated agents"
    )

    unit = _compile(value).units[0]

    assert unit.domains == ("software-engineering",)


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


def test_enrichment_keeps_integration_and_release_evidence_semantically_distinct() -> None:
    request = (
        "Build a production Python API with failure-path tests, independent integration "
        "verification, and installed Windows and Linux release evidence."
    )
    value = {
        "request_summary": request,
        "units": [
            {
                "unit_id": "unit-implementation",
                "outcome": "Build the production Python API",
                "artifact_kind": "implementation-change",
                "domains": ["software-engineering"],
                "stacks": ["python"],
                "capability_ids": ["implementation"],
                "novel_capability": "",
                "depends_on": [],
            },
            {
                "unit_id": "unit-tests",
                "outcome": "Add failure-path tests",
                "artifact_kind": "test-code",
                "domains": ["quality-assurance"],
                "stacks": [],
                "capability_ids": ["testing"],
                "novel_capability": "",
                "depends_on": ["unit-implementation"],
            },
            {
                "unit_id": "unit-installed-evidence",
                "outcome": "Evidence of installed releases on Windows and Linux",
                "artifact_kind": "test-evidence",
                "domains": ["quality-assurance"],
                "stacks": [],
                "capability_ids": ["verification"],
                "novel_capability": "",
                "depends_on": ["unit-tests"],
            },
        ],
    }
    primary = compile_intent_plan(
        value,
        request=request,
        context=_context(),
        known_domains=("quality-assurance", "software-engineering"),
        known_stacks=("python",),
        known_capability_ids=("implementation", "testing", "verification"),
    )

    plan = enrich_intent_plan(primary, request=request, context=_context())
    evidence_owners = {
        role_anchors(unit) for unit in plan.units if unit.artifact_kind == "test-evidence"
    }

    assert ("application-integration-verifier", "test-results-analyzer") in evidence_owners
    assert ("cross-platform-release-verifier", "test-results-analyzer") in evidence_owners


def test_enrichment_binds_early_assurance_to_later_local_test_artifacts() -> None:
    value = {
        "request_summary": "Implement and verify cancellation-safe indexing.",
        "units": [
            {
                "unit_id": "unit-implementation",
                "outcome": "Implement cancellation-safe indexing",
                "artifact_kind": "implementation-change",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["implementation"],
                "novel_capability": "",
                "depends_on": [],
            },
            {
                "unit_id": "unit-observability",
                "outcome": "Implement application observability",
                "artifact_kind": "implementation-change",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["implementation"],
                "novel_capability": "",
                "depends_on": ["unit-implementation"],
            },
            {
                "unit_id": "unit-evidence",
                "outcome": "Independently analyze completed test evidence",
                "artifact_kind": "test-evidence",
                "domains": ["quality-assurance"],
                "stacks": [],
                "capability_ids": ["testing"],
                "novel_capability": "",
                "depends_on": [],
            },
            {
                "unit_id": "unit-tests",
                "outcome": "Implement cancellation failure-path tests",
                "artifact_kind": "test-code",
                "domains": ["quality-assurance"],
                "stacks": [],
                "capability_ids": ["testing"],
                "novel_capability": "",
                "depends_on": ["unit-implementation"],
            },
            {
                "unit_id": "unit-review",
                "outcome": "Independently review the indexing change",
                "artifact_kind": "review-report",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["review"],
                "novel_capability": "",
                "depends_on": ["unit-implementation"],
            },
        ],
    }
    primary = compile_intent_plan(
        value,
        request="Implement cancellation-safe indexing with tests and review.",
        context=_context(),
        known_domains=("quality-assurance", "software-engineering"),
        known_stacks=(),
        known_capability_ids=("implementation", "review", "testing"),
    )

    plan = enrich_intent_plan(
        primary,
        request="Implement cancellation-safe indexing with tests and review.",
        context=_context(),
    )
    by_id = {unit.unit_id: unit for unit in plan.units}

    assert "unit-tests" in by_id["unit-evidence"].depends_on
    assert "unit-tests" in by_id["unit-review"].depends_on
    assert "unit-observability" in by_id["unit-evidence"].depends_on
    assert "unit-observability" in by_id["unit-review"].depends_on


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
