"""Deterministic completeness policy for inference-produced work plans."""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass

from agency_runtime.core.workforce.planning_contracts import WorkUnit, WorkUnitPlan

_TOKENS = re.compile(r"[a-z0-9]+")
_NEGATED_SCOPE = re.compile(
    r"\b(?:do\s+not|don't|must\s+not|never|without)\b[^.;\n]*",
    re.IGNORECASE,
)
_NEGATED_EVIDENCE_SCOPE = re.compile(
    r"\b(?:do(?:es)?\s+not|don't|doesn't|must\s+not|never|nothing|without)\b[^.;,\n]*",
    re.IGNORECASE,
)
# "before"/"prior to"/"without"/"then" split because they scope the
# verification away from the operation (earlier state, or merely performing
# the operation next). "after"/"following"/"once" deliberately do NOT split:
# verifying behavior after the install/deploy IS release evidence (AR-345
# review).
_VERIFICATION_CLAUSE_BOUNDARY = re.compile(
    r"(?:[.;,\n]|\b(?:before|prior\s+to|then|without)\b)",
    re.IGNORECASE,
)
_MUTATION = frozenset(
    {
        "add",
        "build",
        "change",
        "create",
        "debug",
        "edit",
        "fix",
        "implement",
        "improve",
        "optimize",
        "refactor",
        "remove",
        "repair",
        "revise",
        "rewrite",
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
_RELEASE_OPERATIONS = {
    "deployment": frozenset({"deploy", "deployed", "deploying", "deployment", "deployments"}),
    "installation": frozenset(
        {
            "install",
            "installation",
            "installations",
            "installed",
            "installer",
            "installers",
            "installing",
            "reinstall",
            "reinstallation",
            "reinstalled",
            "reinstalling",
            "reinstalls",
            "uninstall",
            "uninstallation",
            "uninstalled",
            "uninstalling",
            "uninstalls",
        }
    ),
    "release": frozenset(
        {"release", "released", "releases", "releasing", "ship", "shipped", "shipping", "ships"}
    ),
}
# Request-shaping tokens are exactly the union of the per-operation
# vocabularies; deriving it keeps the two views from desynchronizing, and
# RELEASE_OPERATION_TOKENS is the public constant other planners (the
# deterministic fallback) source instead of keeping a divergent copy.
_RELEASE = frozenset().union(*_RELEASE_OPERATIONS.values())
RELEASE_OPERATION_TOKENS = _RELEASE
_POSITIVE_VERIFICATION = frozenset(
    {
        "confirm",
        "confirmed",
        "confirming",
        "confirms",
        "evidence",
        "prove",
        "proven",
        "proves",
        "proving",
        "test",
        "tested",
        "testing",
        "tests",
        "validate",
        "validated",
        "validates",
        "validating",
        "validation",
        "verification",
        "verified",
        "verifies",
        "verify",
        "verifying",
    }
)
_ASSURANCE_TERMS = frozenset(
    {
        "assurance",
        "audit",
        "compliance",
        "compliant",
        "conformance",
        "conformant",
        "certification",
        "certified",
        "certify",
    }
)
_HIGH_ASSURANCE_CONTEXT = frozenset(
    {
        "airborne",
        "airworthiness",
        "aerospace",
        "automotive",
        "aviation",
        "avionics",
        "flight",
        "medical",
        "nuclear",
        "rail",
        "regulated",
        "regulatory",
        "safety",
    }
)
_INTRINSICALLY_REGULATED_PREFIXES = frozenset({"arp", "cfr", "do", "rtca"})
_KNOWN_HIGH_ASSURANCE_STANDARDS = frozenset(
    {
        ("iec", "61508"),
        ("iec", "62304"),
        ("iso", "26262"),
        ("nist", "800-53"),
        ("soc", "2"),
    }
)
_NAMED_STANDARD = re.compile(
    r"\b(?P<prefix>do|iso|iec|nist|rtca|mil|en|soc|cfr)\s*(?:-|\s)\s*"
    r"(?P<identifier>\d{1,6}[a-z]?(?:[-./:]\d+[a-z]?)*)\b"
    r"|\b(?P<arp_prefix>arp)\s*-?\s*(?P<arp_identifier>\d{3,6}[a-z]?)\b",
    re.IGNORECASE,
)

_PLAN_REPAIR_REQUIREMENTS = {
    "plan_missing_implementation": (
        "Add at least one implementation-change unit for the requested code mutation."
    ),
    "plan_missing_test_implementation": (
        "Add a distinct test-code unit that authors or changes the tests."
    ),
    "plan_missing_independent_review": (
        "Add a distinct review-report unit for independent artifact correctness review."
    ),
    "plan_missing_test_evidence_review": (
        "Add a distinct test-evidence unit that independently runs or interprets test results."
    ),
    "plan_tests_not_ordered_after_implementation": (
        "Place each test-code unit after its implementation-change dependency and reference that "
        "earlier unit through depends_on."
    ),
    "plan_review_not_ordered_after_artifact": (
        "Place an independent review-report after the implementation or test artifact it reviews "
        "and reference that earlier unit through depends_on."
    ),
    "plan_test_evidence_not_ordered_after_tests": (
        "Place the test-evidence unit after test-code and reference the earlier test-code unit "
        "through depends_on."
    ),
    "plan_missing_security_review": (
        "Add a separate security-domain review-report for the security-sensitive code."
    ),
    "plan_missing_code_correctness_review": (
        "Add a non-security software-engineering review-report for code correctness; keep it "
        "distinct from the security review."
    ),
    "plan_missing_release_verification": (
        "Add downstream test-evidence whose outcome names the requested operation "
        "(install/deploy/release words) in the same clause as a verification word "
        '(verify/confirm/validate/test/evidence), e.g. "Confirm the plugin is '
        'installed and loaded".'
    ),
    "plan_missing_documentation_change": (
        "Add a documentation unit for the requested prose or documentation mutation."
    ),
    "plan_missing_documentation_review": (
        "Add a downstream review-report for the requested documentation change."
    ),
    "plan_missing_codebase_discovery": (
        "Add an earlier read-only discovery unit in the built-in codebase-discovery or "
        "software-engineering domain whose outcome maps the relevant repository code paths."
    ),
    "plan_missing_regulated_assurance_review": (
        "Add an independent review-report for the named regulated assurance work."
    ),
    "plan_missing_regulated_assurance_requirement": (
        "Include every named regulated-assurance capability in an independent review-report."
    ),
    "plan_external_write_requires_separate_authorization": (
        "Remove external-write authority from this plan; it requires a separate authorized turn."
    ),
    "plan_capability_ids_outside_ontology": (
        "Replace every capability_ids entry with an exact identifier from "
        "planning_taxonomy.known_capability_ids."
    ),
    "plan_dependency_not_earlier": (
        "Topologically order the complete plan and allow each depends_on entry to reference "
        "only an exact unit ID that appears earlier."
    ),
    "plan_unit_required_tools_unproven": (
        "Use only exact values from host_context.available_tools for required_tools. Remove or "
        "replace every tool this host has not proven; a unit that demands an unproven tool "
        "cannot be staffed by any worker, however well the plan reads."
    ),
}

PLAN_RESPONSE_SEMANTIC_INVALID = "plan_response_semantic_invalid"
PLAN_POLICY_VIOLATION_CODES = frozenset(_PLAN_REPAIR_REQUIREMENTS)
PLAN_VALIDATION_REASON_CODES = frozenset(
    (*PLAN_POLICY_VIOLATION_CODES, PLAN_RESPONSE_SEMANTIC_INVALID)
)


def planner_acceptance_contract() -> dict[str, object]:
    """Describe deterministic plan vetoes without creating a plan for inference."""

    return {
        "code_mutation": {
            "required_artifact_kinds": [
                "implementation-change",
                "test-code",
                "review-report",
                "test-evidence",
            ],
            "required_dependency_paths": [
                "implementation-change -> test-code",
                "implementation-change or test-code -> review-report",
                "test-code -> test-evidence",
            ],
            "test_code_and_test_evidence_are_distinct": True,
        },
        "security_sensitive_code": {
            "required_distinct_reviews": [
                "software-engineering correctness review-report without security domain",
                "security-domain exploitability review-report",
            ]
        },
        "repository_security_or_code_path_mapping": {
            "required_predecessor": "software-engineering analysis that maps repository code paths"
        },
        "documentation_mutation": {"required_artifact_kinds": ["documentation", "review-report"]},
        "install_deploy_or_release": {
            "required_downstream_artifact": (
                "test-evidence whose outcome names the install/deploy/release operation in "
                "the same clause as a verification word"
            )
        },
        "ordering": "Every depends_on ID must name an earlier unit in the same response.",
    }


def plan_semantic_validation_reason_codes(error: BaseException) -> tuple[str, ...]:
    """Map stable compact-plan parser failures onto the closed receipt vocabulary."""

    code = {
        "capability_ids must use the current workforce ontology": (
            "plan_capability_ids_outside_ontology"
        ),
        "work-unit dependencies must reference earlier units": ("plan_dependency_not_earlier"),
    }.get(str(error))
    return (code or PLAN_RESPONSE_SEMANTIC_INVALID,)


def plan_policy_repair_guidance(violations: Sequence[str]) -> tuple[dict[str, str], ...]:
    """Return bounded, allowlisted corrections for deterministic policy violations."""

    return tuple(
        {
            "code": code,
            "required_correction": _PLAN_REPAIR_REQUIREMENTS.get(
                code,
                "Rewrite the complete plan so it satisfies this deterministic safety invariant.",
            ),
        }
        for code in dict.fromkeys(violations)
    )


def regulated_assurance_requirements(request: str) -> tuple[str, ...]:
    """Return canonical named-standard requirements for high-assurance work."""

    actionable = _NEGATED_SCOPE.sub(" ", request).casefold()
    tokens = frozenset(_TOKENS.findall(actionable))
    if not tokens & _ASSURANCE_TERMS:
        return ()
    standards: list[tuple[str, str]] = []
    for match in _NAMED_STANDARD.finditer(actionable):
        prefix = (match.group("prefix") or match.group("arp_prefix")).casefold()
        identifier = (match.group("identifier") or match.group("arp_identifier")).casefold()
        standards.append((prefix, identifier))
    if not standards:
        return ()
    high_assurance = bool(tokens & _HIGH_ASSURANCE_CONTEXT) or any(
        prefix in _INTRINSICALLY_REGULATED_PREFIXES
        or (prefix, identifier) in _KNOWN_HIGH_ASSURANCE_STANDARDS
        for prefix, identifier in standards
    )
    if not high_assurance:
        return ()
    return tuple(
        dict.fromkeys(
            "regulated-assurance-" + re.sub(r"[^a-z0-9]+", "-", f"{prefix}-{identifier}").strip("-")
            for prefix, identifier in standards
        )
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


def _outcome_verifies_operation(outcome: str, vocabulary: frozenset[str]) -> bool:
    """Return whether one clause both verifies and names the operation.

    Negated scopes are stripped first, and clause boundaries (punctuation and
    temporal words) keep "verify the tests before deployment" from counting as
    deployment verification. Within a surviving clause, a verification token
    plus an operation token is the signal; demanding a fixed filler-only token
    window between them rejected most natural planner phrasings ("Verify the
    plugin was installed") and made release-shaped requests deterministically
    unstaffable (AR-345).
    """

    actionable = _NEGATED_EVIDENCE_SCOPE.sub(" ", outcome).casefold()
    for clause in _VERIFICATION_CLAUSE_BOUNDARY.split(actionable):
        tokens = frozenset(_TOKENS.findall(clause))
        if tokens & _POSITIVE_VERIFICATION and tokens & vocabulary:
            return True
    return False


def _release_verification_covers_request(
    request_tokens: frozenset[str],
    plan: WorkUnitPlan,
) -> bool:
    requested_operations = tuple(
        operation
        for operation, vocabulary in _RELEASE_OPERATIONS.items()
        if request_tokens & vocabulary
    )
    evidence_outcomes = tuple(
        item.outcome
        for item in plan.units
        if item.artifact_kind == "test-evidence" and item.authority == "review"
    )
    return bool(requested_operations) and all(
        any(
            _outcome_verifies_operation(outcome, _RELEASE_OPERATIONS[operation])
            for outcome in evidence_outcomes
        )
        for operation in requested_operations
    )


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
                # The deterministic planning oracle emits its codebase
                # discovery unit as a discovery-phase review-report while
                # inference planners emit analysis; both are read-only
                # repository mapping and must satisfy the same predecessor
                # invariant (AR-331).
                if item.artifact_kind in {"analysis", "review-report"}
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
    if tokens & _RELEASE and not _release_verification_covers_request(tokens, plan):
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
        and bool({"codebase-discovery", "software-engineering"}.intersection(item.domains))
        for item in inventory.discoveries
    )


def plan_policy_violations(
    request: str,
    plan: WorkUnitPlan,
    *,
    explicit_indivisible_unit: bool = False,
    available_tools: Collection[str] | None = None,
) -> tuple[str, ...]:
    """Reject incomplete plans while preserving an explicit one-unit topology."""

    actionable_request = _NEGATED_SCOPE.sub(" ", request)
    tokens = frozenset(_TOKENS.findall(actionable_request.casefold()))
    docs_mutation = bool(
        tokens & _MUTATION
        and tokens & _DOCS
        and not tokens & _CODE.difference({"repo", "repository"})
    )
    code_mutation = bool(tokens & _MUTATION and tokens & _CODE and not docs_mutation)
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
    if not explicit_indivisible_unit:
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
        assurance_requirements = regulated_assurance_requirements(request)
        if assurance_requirements:
            if not inventory.reviews:
                codes.append("plan_missing_regulated_assurance_review")
            else:
                review_capabilities = {
                    capability
                    for unit in inventory.reviews
                    for capability in unit.required_capabilities
                }
                if any(
                    requirement not in review_capabilities for requirement in assurance_requirements
                ):
                    codes.append("plan_missing_regulated_assurance_requirement")
    # AR-374: the planner is told to draw required_tools from
    # host_context.available_tools and nothing used to enforce it. One
    # unproven tool fails the unit-scoped eligibility gate against every
    # worker at once, so staffing abstains with agent_tools_missing and the
    # receipt reads as a roster problem rather than a plan defect. An empty
    # proven set means the host proved nothing rather than that it can do
    # nothing, so it cannot distinguish a bad plan and is left to the
    # downstream staffing gate.
    if available_tools and any(
        tool not in available_tools for unit in plan.units for tool in unit.required_tools
    ):
        codes.append("plan_unit_required_tools_unproven")
    if any(item.mutation_scope == "external_write" for item in plan.units):
        codes.append("plan_external_write_requires_separate_authorization")
    return tuple(dict.fromkeys(codes))


__all__ = [
    "PLAN_POLICY_VIOLATION_CODES",
    "PLAN_RESPONSE_SEMANTIC_INVALID",
    "PLAN_VALIDATION_REASON_CODES",
    "plan_policy_repair_guidance",
    "plan_policy_violations",
    "plan_semantic_validation_reason_codes",
    "planner_acceptance_contract",
    "regulated_assurance_requirements",
]
