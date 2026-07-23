"""Deterministic completeness policy for inference-produced work plans."""

from __future__ import annotations

import re
from dataclasses import dataclass

from agency_runtime.core.workforce.planning_contracts import WorkUnit, WorkUnitPlan

_TOKENS = re.compile(r"[a-z0-9]+")
_MUTATION = frozenset(
    {
        "add",
        "build",
        "change",
        "create",
        "debug",
        "fix",
        "implement",
        "improve",
        "optimize",
        "refactor",
        "remove",
        "repair",
        "update",
    }
)
_CODE = frozenset(
    {
        "api",
        "app",
        "application",
        "backend",
        "bug",
        "cli",
        "code",
        "dashboard",
        "database",
        "frontend",
        "function",
        "installer",
        "library",
        "package",
        "repo",
        "repository",
        "runtime",
        "service",
        "ui",
    }
)
_DOCS = frozenset(
    {"comment", "comments", "documentation", "docs", "guide", "markdown", "prose", "readme"}
)
_SECURITY = frozenset(
    {
        "auth",
        "authentication",
        "authorization",
        "credential",
        "exploit",
        "exploitability",
        "security",
        "threat",
        "vulnerability",
        "vulnerabilities",
    }
)
_RELEASE = frozenset(
    {"deploy", "deployment", "install", "installer", "production", "release", "ship"}
)


def _ancestors(plan: WorkUnitPlan, unit_id: str) -> frozenset[str]:
    units = {item.unit_id: item for item in plan.units}
    found: set[str] = set()
    pending = list(units[unit_id].depends_on)
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(units[current].depends_on)
    return frozenset(found)


def _unit_tokens(unit: object) -> frozenset[str]:
    values = [str(getattr(unit, "outcome", ""))]
    values.extend(str(item) for item in getattr(unit, "claims", ()))
    return frozenset(_TOKENS.findall(" ".join(values).casefold()))


@dataclass(frozen=True, slots=True)
class _PlanInventory:
    implementation: tuple[WorkUnit, ...]
    tests: tuple[WorkUnit, ...]
    reviews: tuple[WorkUnit, ...]
    discoveries: tuple[WorkUnit, ...]
    test_evidence: tuple[WorkUnit, ...]
    documentation: tuple[WorkUnit, ...]

    @classmethod
    def from_plan(cls, plan: WorkUnitPlan) -> _PlanInventory:
        return cls(
            implementation=tuple(
                item
                for item in plan.units
                if item.artifact_kind == "implementation-change"
                and item.lifecycle_phase == "implementation"
                and item.mutation_scope == "workspace_write"
            ),
            tests=tuple(
                item
                for item in plan.units
                if item.artifact_kind == "test-code"
                and item.lifecycle_phase == "testing"
                and item.mutation_scope == "workspace_write"
            ),
            reviews=tuple(
                item
                for item in plan.units
                if item.artifact_kind == "review-report"
                and item.lifecycle_phase == "review"
                and item.authority == "review"
                and item.mutation_scope == "read_only"
            ),
            discoveries=tuple(
                item
                for item in plan.units
                if item.artifact_kind == "analysis"
                and item.lifecycle_phase == "discovery"
                and item.mutation_scope == "read_only"
            ),
            test_evidence=tuple(
                item
                for item in plan.units
                if item.artifact_kind == "test-evidence"
                and item.lifecycle_phase == "testing"
                and item.authority == "review"
                and item.mutation_scope == "read_only"
            ),
            documentation=tuple(
                item
                for item in plan.units
                if item.artifact_kind == "documentation"
                and item.mutation_scope == "workspace_write"
            ),
        )


def _code_mutation_violations(
    tokens: frozenset[str],
    plan: WorkUnitPlan,
    inventory: _PlanInventory,
) -> list[str]:
    codes: list[str] = []
    if not inventory.implementation:
        codes.append("plan_missing_implementation")
    if not inventory.tests:
        codes.append("plan_missing_test_implementation")
    if not inventory.reviews:
        codes.append("plan_missing_independent_review")
    if not inventory.test_evidence:
        codes.append("plan_missing_test_evidence_review")
    implementation_ids = {item.unit_id for item in inventory.implementation}
    test_ids = {item.unit_id for item in inventory.tests}
    if (
        inventory.implementation
        and inventory.tests
        and not any(implementation_ids & _ancestors(plan, item.unit_id) for item in inventory.tests)
    ):
        codes.append("plan_tests_not_ordered_after_implementation")
    if (
        inventory.implementation
        and inventory.reviews
        and not any(
            (implementation_ids | test_ids) & _ancestors(plan, item.unit_id)
            for item in inventory.reviews
        )
    ):
        codes.append("plan_review_not_ordered_after_artifact")
    if (
        inventory.tests
        and inventory.test_evidence
        and not any(test_ids & _ancestors(plan, item.unit_id) for item in inventory.test_evidence)
    ):
        codes.append("plan_test_evidence_not_ordered_after_tests")
    if tokens & _SECURITY and not any("security" in item.domains for item in inventory.reviews):
        codes.append("plan_missing_security_review")
    if tokens & _RELEASE and not any(
        item.lifecycle_phase == "release"
        and item.artifact_kind == "test-evidence"
        and item.authority == "review"
        for item in plan.units
    ):
        codes.append("plan_missing_release_verification")
    return codes


def _security_review_violations(inventory: _PlanInventory) -> list[str]:
    codes: list[str] = []
    if not any(
        "software-engineering" in item.domains and "security" not in item.domains
        for item in inventory.reviews
    ):
        codes.append("plan_missing_code_correctness_review")
    if not any("security" in item.domains for item in inventory.reviews):
        codes.append("plan_missing_security_review")
    return codes


def _has_codebase_discovery(inventory: _PlanInventory) -> bool:
    return any(
        (
            bool(_unit_tokens(item) & {"codebase", "repo", "repository"})
            or {"code", "path"} <= _unit_tokens(item)
        )
        and "software-engineering" in item.domains
        for item in inventory.discoveries
    )


def plan_policy_violations(request: str, plan: WorkUnitPlan) -> tuple[str, ...]:
    """Reject plans that omit assurance entailed by the requested outcome."""

    tokens = frozenset(_TOKENS.findall(request.casefold()))
    code_mutation = bool(tokens & _MUTATION and tokens & _CODE)
    docs_mutation = bool(tokens & _MUTATION and tokens & _DOCS and not tokens & _CODE)
    inventory = _PlanInventory.from_plan(plan)
    codes: list[str] = []
    security_code_review = bool(
        tokens & _SECURITY and tokens & _CODE and (code_mutation or tokens & {"audit", "review"})
    )
    repository_security_review = bool(
        security_code_review and tokens & {"codebase", "repo", "repository"}
    )
    code_path_map_requested = bool(
        "map" in tokens and tokens & {"codebase", "path", "paths", "repo", "repository"}
    )
    if code_mutation:
        codes.extend(_code_mutation_violations(tokens, plan, inventory))
    if docs_mutation:
        if not inventory.documentation:
            codes.append("plan_missing_documentation_change")
        if not inventory.reviews:
            codes.append("plan_missing_documentation_review")
    if security_code_review:
        codes.extend(_security_review_violations(inventory))
    if (repository_security_review or code_path_map_requested) and not _has_codebase_discovery(
        inventory
    ):
        codes.append("plan_missing_codebase_discovery")
    if any(item.mutation_scope == "external_write" for item in plan.units):
        codes.append("plan_external_write_requires_separate_authorization")
    return tuple(dict.fromkeys(codes))


__all__ = ["plan_policy_violations"]
