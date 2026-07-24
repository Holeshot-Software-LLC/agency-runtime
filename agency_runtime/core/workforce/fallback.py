"""Conservative deterministic planning and recruitment when inference is absent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.workforce.capability_ontology import artifact_capability
from agency_runtime.core.workforce.contract import WorkforceContract
from agency_runtime.core.workforce.lifecycle_roles import role_anchors
from agency_runtime.core.workforce.planning_contracts import (
    WorkUnit,
    WorkUnitPlan,
    parse_work_unit_plan,
)
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingBudget,
    StaffingContext,
    StaffingDecision,
    build_deterministic_proposal,
    typed_staffing_coverage,
    typed_staffing_ineligibility,
    typed_staffing_requirements,
    verify_staffing,
)

if TYPE_CHECKING:
    from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
    from agency_runtime.core.workforce.planning_contracts import RecruiterProposal

_TOKENS = re.compile(r"[a-z0-9]+")
_NEGATED_SCOPE = re.compile(
    r"\b(?:do\s+not|don't|must\s+not|never|without)\b[^.;\n]*",
    re.IGNORECASE,
)
_TRIVIAL = frozenset({"hello", "hi", "hey", "thanks", "thank", "ok", "okay", "continue"})
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
        "async",
        "backend",
        "bug",
        "cli",
        "code",
        "codebase",
        "dashboard",
        "database",
        "frontend",
        "function",
        "installer",
        "library",
        "package",
        "patch",
        "repo",
        "repository",
        "runtime",
        "service",
        "ui",
    }
)
_REVIEWABLE_CODE_ARTIFACT = frozenset(
    {
        "bug",
        "code",
        "codebase",
        "diff",
        "file",
        "function",
        "patch",
        "pull",
        "repo",
        "repository",
        "runtime",
    }
)
_DOCS = frozenset(
    {
        "comment",
        "comments",
        "documentation",
        "document",
        "documenting",
        "docs",
        "guide",
        "issue",
        "markdown",
        "prose",
        "readme",
        "tutorial",
        "write",
        "writing",
    }
)
_DOCUMENT_MUTATION = frozenset({"document", "documenting", "write"})
_TEST = frozenset({"coverage", "e2e", "integration", "qa", "test", "tests", "testing"})
_REVIEW = frozenset({"audit", "inspect", "review", "validate", "verify"})
_SECURITY = frozenset(
    {"auth", "authentication", "authorization", "credential", "exploit", "security", "threat"}
)
_RELEASE = frozenset({"deploy", "deployment", "install", "installer", "package", "release", "ship"})
_ANALYSIS = frozenset(
    {"analyze", "assess", "diagnose", "evaluate", "explain", "investigate", "question", "why"}
)
_LANGUAGES: tuple[tuple[str, frozenset[str]], ...] = (
    ("typescript", frozenset({"typescript", "tsx"})),
    ("javascript", frozenset({"javascript", "node", "nodejs"})),
    ("python", frozenset({"python", "pytest"})),
    ("rust", frozenset({"rust", "cargo"})),
    ("go", frozenset({"golang"})),
    ("java", frozenset({"java", "spring"})),
    ("csharp", frozenset({"csharp", "dotnet"})),
)
_FRAMEWORKS: tuple[tuple[str, frozenset[str]], ...] = (
    ("react", frozenset({"react", "nextjs"})),
    ("vue", frozenset({"vue", "nuxt"})),
    ("fastapi", frozenset({"fastapi"})),
    ("django", frozenset({"django"})),
    ("flask", frozenset({"flask"})),
    ("laravel", frozenset({"laravel", "livewire"})),
)


@dataclass(frozen=True, slots=True)
class DeterministicWorkforceResult:
    plan: WorkUnitPlan | None
    proposal: RecruiterProposal | None
    staffing: StaffingDecision
    reason_codes: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.staffing.accepted


def _tokens(value: str) -> frozenset[str]:
    return frozenset(_TOKENS.findall(value.casefold()))


def _contains_any(tokens: frozenset[str], terms: frozenset[str]) -> bool:
    return bool(tokens & terms)


def _document_mutation_requested(request: str) -> bool:
    return bool(
        re.search(r"\b(?:write|writing)\b(?!\s+(?:query|statement|transaction)\b)", request, re.I)
        or re.search(r"\bdocumenting\b", request, re.I)
        or re.search(
            r"(?:^|[.;]\s*|\b(?:and|please|then|to)\s+)document\b",
            request,
            re.I,
        )
    )


def _detected_values(
    tokens: frozenset[str],
    vocabulary: tuple[tuple[str, frozenset[str]], ...],
) -> list[str]:
    return [canonical for canonical, aliases in vocabulary if tokens & aliases]


def _has_inline_code_context(request: str, tokens: frozenset[str]) -> bool:
    return bool(
        request.count(chr(96)) >= 3
        or {"return", "def", "class", "const", "let", "var"} & tokens
        or re.search(r"(^|\n)[+-]{1,3}\\s*\\S", request)
    )


def _has_reviewable_code_artifact(request: str, tokens: frozenset[str]) -> bool:
    return bool(tokens & _REVIEWABLE_CODE_ARTIFACT or _has_inline_code_context(request, tokens))


_TOOL_ALIASES = {
    "artifact-reader": "repository-read",
    "filesystem": "repository-read",
    "package-manager": "package-management",
    "repository": "repository-read",
    "security": "security-analysis",
    "shell": "shell-execution",
    "test-runner": "test-execution",
}


def _required_tools(context: StaffingContext, *preferred: str) -> list[str]:
    del context
    return list(dict.fromkeys(_TOOL_ALIASES.get(item, item) for item in preferred))


def _unit(
    unit_id: str,
    *,
    outcome: str,
    artifact: str,
    lifecycle: str,
    domains: tuple[str, ...],
    authority: str,
    mutation: str,
    context: StaffingContext,
    languages: tuple[str, ...] = (),
    frameworks: tuple[str, ...] = (),
    claims: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
    tools: tuple[str, ...] = (),
    parallelization: str = "unspecified",
) -> dict[str, object]:
    # ADR-0087: a unit's required capability is the governed broad task
    # capability for its artifact kind. The workforce contracts speak the
    # CORE_CAPABILITY_IDS vocabulary; bespoke per-unit capability strings must
    # not bypass the ontology (they match no contract and block acceptance).
    return {
        "unit_id": unit_id,
        "outcome": outcome,
        "artifact_kind": artifact,
        "lifecycle_phase": lifecycle,
        "domains": list(domains),
        "languages": list(languages),
        "frameworks": list(frameworks),
        "required_capabilities": [artifact_capability(artifact)],
        "authority": authority,
        "mutation_scope": mutation,
        "risks": ["regression"] if mutation != "read_only" else [],
        "trust_boundaries": ["repository"],
        "claims": list(claims),
        "depends_on": list(depends_on),
        "resources": ["request", "repository"],
        "required_tools": _required_tools(context, *tools),
        "platforms": [context.platform],
        "acceptance_evidence": [f"Evidence proves {outcome.casefold()}"],
        "parallelization": parallelization,
    }


def deterministic_work_plan(
    request: str,
    *,
    context: StaffingContext,
) -> tuple[WorkUnitPlan | None, tuple[str, ...]]:
    """Build only high-signal typed units; ambiguous work stays with resident managers."""

    actionable_request = _NEGATED_SCOPE.sub(" ", request)
    tokens = _tokens(actionable_request)
    if not tokens or tokens <= _TRIVIAL:
        return None, ("deterministic_request_trivial",)
    languages = tuple(_detected_values(tokens, _LANGUAGES))
    frameworks = tuple(_detected_values(tokens, _FRAMEWORKS))
    document_mutation = _document_mutation_requested(actionable_request)
    mutating = _contains_any(tokens, _MUTATION) or document_mutation
    docs = _contains_any(tokens, _DOCS - {"document", "write", "writing"}) or document_mutation
    code_terms = _CODE.difference({"repo", "repository"}) if docs else _CODE
    code = _contains_any(tokens, code_terms) or bool(languages or frameworks)
    tests = _contains_any(tokens, _TEST)
    review = _contains_any(tokens, _REVIEW)
    security = _contains_any(tokens, _SECURITY)
    release = _contains_any(tokens, _RELEASE)
    analysis = _contains_any(tokens, _ANALYSIS)
    normalized_request = actionable_request.casefold()
    review_position = min(
        (normalized_request.find(term) for term in _REVIEW if normalized_request.find(term) >= 0),
        default=len(normalized_request) + 1,
    )
    mutation_position = min(
        (
            normalized_request.find(term)
            for term in _MUTATION | _DOCUMENT_MUTATION
            if normalized_request.find(term) >= 0
        ),
        default=len(normalized_request) + 1,
    )
    review_before_mutation = review_position < mutation_position
    units: list[dict[str, object]] = []

    if docs and mutating and review and review_before_mutation and not code:
        review_domains = ("security",) if security else ("software-engineering",)
        units.append(
            _unit(
                "unit-source-review",
                outcome="Review the source material and establish evidence-backed findings",
                artifact="review-report",
                lifecycle="review",
                domains=review_domains,
                authority="review",
                mutation="read_only",
                context=context,
                tools=("repository", "filesystem"),
            )
        )
        units.append(
            _unit(
                "unit-documentation",
                outcome="Document the verified findings in accurate technical prose",
                artifact="documentation",
                lifecycle="documentation",
                domains=("software-engineering",),
                authority="modify",
                mutation="workspace_write",
                context=context,
                claims=("documentation-accurate",),
                depends_on=("unit-source-review",),
                tools=("repository", "filesystem"),
            )
        )
    elif docs and mutating and not code:
        units.append(
            _unit(
                "unit-documentation",
                outcome="Create accurate repository-grounded technical documentation",
                artifact="documentation",
                lifecycle="documentation",
                domains=("software-engineering",),
                authority="modify",
                mutation="workspace_write",
                context=context,
                claims=("documentation-accurate",),
                tools=("repository", "filesystem"),
            )
        )
        units.append(
            _unit(
                "unit-documentation-review",
                outcome="Independently review documentation accuracy and discoverability",
                artifact="review-report",
                lifecycle="review",
                domains=("software-engineering",),
                authority="review",
                mutation="read_only",
                context=context,
                depends_on=("unit-documentation",),
                tools=("repository", "filesystem"),
            )
        )
    elif mutating and code:
        units.append(
            _unit(
                "unit-implementation",
                outcome="Implement the requested production-quality application change",
                artifact="implementation-change",
                lifecycle="implementation",
                domains=("software-engineering",),
                authority="modify",
                mutation="workspace_write",
                context=context,
                languages=languages,
                frameworks=frameworks,
                claims=("implementation-complete",),
                tools=("repository", "filesystem", "shell", "package-manager"),
            )
        )
        units.append(
            _unit(
                "unit-tests",
                outcome="Implement unit, integration, and failure-path tests",
                artifact="test-code",
                lifecycle="testing",
                domains=("quality-assurance",),
                authority="modify",
                mutation="workspace_write",
                context=context,
                depends_on=("unit-implementation",),
                tools=("repository", "filesystem", "test-runner"),
            )
        )
        units.append(
            _unit(
                "unit-code-review",
                outcome="Independently review the implementation and test evidence",
                artifact="review-report",
                lifecycle="review",
                domains=("software-engineering",),
                authority="review",
                mutation="read_only",
                context=context,
                depends_on=("unit-tests",),
                tools=("repository", "filesystem"),
            )
        )
        evidence_outcome = "Independently analyze completed test and coverage evidence"
        if "integration" in tokens:
            evidence_outcome = (
                "Independently verify the complete running application integration and "
                "completed test evidence"
            )
        units.append(
            _unit(
                "unit-test-results",
                outcome=evidence_outcome,
                artifact="test-evidence",
                lifecycle="testing",
                domains=("quality-assurance",),
                authority="review",
                mutation="read_only",
                context=context,
                depends_on=("unit-tests",),
                tools=("test-runner",),
                parallelization="parallel",
            )
        )
        if security:
            units.append(
                _unit(
                    "unit-security-review",
                    outcome="Independently review application attack surfaces and controls",
                    artifact="review-report",
                    lifecycle="review",
                    domains=("security",),
                    # A review of a just-produced code change needs a different
                    # specialist than an architecture-only threat-model pass.
                    # The generated-code auditor is deliberately usable with
                    # repository evidence alone; scanners remain optional.
                    authority="review",
                    mutation="read_only",
                    context=context,
                    depends_on=("unit-tests",),
                    tools=("repository",),
                    parallelization="parallel",
                )
            )
        if release:
            dependencies = tuple(
                item
                for item in (
                    "unit-code-review",
                    "unit-test-results",
                    ("unit-security-review" if security else ""),
                )
                if item
            )
            units.append(
                _unit(
                    "unit-release-verification",
                    outcome="Verify the installed application and cross-platform release seams",
                    artifact="test-evidence",
                    lifecycle="release",
                    domains=("quality-assurance",),
                    authority="review",
                    mutation="read_only",
                    context=context,
                    depends_on=dependencies,
                    tools=("artifact-reader", "shell", "test-runner"),
                )
            )
    elif tests:
        evidence_outcome = (
            "Independently verify the complete running application integration and test evidence"
            if "integration" in tokens
            else "Analyze complete test and coverage evidence"
        )
        units.append(
            _unit(
                "unit-test-analysis" if review or analysis else "unit-tests",
                outcome=(
                    evidence_outcome
                    if review or analysis
                    else "Implement unit, integration, and failure-path tests"
                ),
                artifact="test-evidence" if review or analysis else "test-code",
                # Test-result interpretation remains part of the testing
                # lifecycle even when it is performed read-only and reviewed
                # independently. Labeling the evidence unit as review loses the
                # typed testing coverage that downstream staffing must prove.
                lifecycle="testing",
                domains=("quality-assurance",),
                authority="review" if review or analysis else "modify",
                mutation="read_only" if review or analysis else "workspace_write",
                context=context,
                tools=("test-runner", "filesystem"),
            )
        )
    elif (
        security
        and (review or analysis)
        and not mutating
        and not _has_reviewable_code_artifact(actionable_request, tokens)
    ):
        units.append(
            _unit(
                "unit-security-review",
                outcome="Review application attack surfaces and produce evidence-backed findings",
                artifact="review-report",
                lifecycle="review",
                domains=("security",),
                authority="review",
                mutation="read_only",
                context=context,
                tools=("repository",),
            )
        )
    elif review and code:
        review_dependencies: tuple[str, ...] = ()
        if security and not _has_inline_code_context(actionable_request, tokens):
            units.append(
                _unit(
                    "unit-codebase-discovery",
                    outcome="Map the relevant repository structure and trace the security-sensitive code path",
                    artifact="review-report",
                    lifecycle="discovery",
                    domains=("software-engineering",),
                    authority="review",
                    mutation="read_only",
                    context=context,
                    tools=("repository", "filesystem"),
                )
            )
            review_dependencies = ("unit-codebase-discovery",)
        units.append(
            _unit(
                "unit-code-review",
                outcome="Independently review code for defects and regressions",
                artifact="review-report",
                lifecycle="review",
                domains=("software-engineering",),
                authority="review",
                mutation="read_only",
                context=context,
                depends_on=review_dependencies,
                tools=("repository", "filesystem"),
            )
        )
        if security:
            units.append(
                _unit(
                    "unit-security-review",
                    outcome="Independently audit the proposed fix for exploitability and security regressions",
                    artifact="review-report",
                    lifecycle="review",
                    domains=("security",),
                    authority="review",
                    mutation="read_only",
                    context=context,
                    depends_on=review_dependencies,
                    tools=("repository", "filesystem"),
                    parallelization="parallel",
                )
            )
    elif docs:
        units.append(
            _unit(
                "unit-documentation-analysis",
                outcome="Review repository documentation for accuracy and discoverability",
                artifact="review-report",
                lifecycle="review",
                domains=("software-engineering",),
                authority="review",
                mutation="read_only",
                context=context,
                tools=("repository", "filesystem"),
            )
        )
    elif analysis and code:
        units.append(
            _unit(
                "unit-analysis",
                outcome="Produce evidence-backed technical analysis",
                artifact="analysis",
                lifecycle="discovery",
                domains=("software-engineering",),
                authority="advise",
                mutation="read_only",
                context=context,
                languages=languages,
                frameworks=frameworks,
                tools=("repository", "filesystem"),
            )
        )
    else:
        return None, ("deterministic_request_ambiguous",)

    return (
        parse_work_unit_plan(
            {
                "schema_version": 2,
                "request_summary": " ".join(request.split())[:2048],
                "units": units,
            }
        ),
        (),
    )


def _contract_tokens(contract: WorkforceContract) -> frozenset[str]:
    return _tokens(
        " ".join(
            (
                contract.agent_id,
                contract.display_name,
                contract.archetype,
                *contract.capability_ids,
                *contract.outcomes,
                *contract.artifact_kinds,
                *contract.lifecycle_phases,
                *contract.domains,
                *contract.stacks,
                *contract.scope_qualifiers,
            )
        )
    )


def _unit_tokens(unit: WorkUnit, request: str) -> frozenset[str]:
    return _tokens(
        " ".join(
            (
                request,
                unit.outcome,
                unit.artifact_kind,
                unit.lifecycle_phase,
                *unit.domains,
                *unit.languages,
                *unit.frameworks,
                *unit.required_capabilities,
            )
        )
    )


def _supports(contract: WorkforceContract, capability: str) -> bool:
    if capability in contract.capability_ids:
        return True
    required = _tokens(capability)
    return bool(required) and required <= _contract_tokens(contract)


def _semantic_score(unit: WorkUnit, contract: WorkforceContract, request: str) -> float:
    score = 0.0
    score += 0.18 if unit.artifact_kind in contract.artifact_kinds else 0.0
    score += 0.12 if unit.lifecycle_phase in contract.lifecycle_phases else 0.0
    score += 0.12 if unit.authority == contract.authority else 0.0
    score += 0.1 if set(unit.domains) <= set(contract.domains) else 0.0
    score += 0.15 if set(unit.languages + unit.frameworks) <= set(contract.stacks) else 0.0
    score += (
        0.2
        if unit.required_capabilities
        and all(_supports(contract, item) for item in unit.required_capabilities)
        else 0.0
    )
    query = _unit_tokens(unit, request)
    corpus = _contract_tokens(contract)
    overlap = len(query & corpus) / max(1, len(query))
    score += min(0.13, overlap * 0.5)
    if any(_tokens(item) <= query for item in contract.not_for if _tokens(item)):
        score -= 0.5
    return round(max(0.0, min(1.0, score)), 6)


def deterministic_rankings(
    plan: WorkUnitPlan,
    contracts: tuple[WorkforceContract, ...],
    *,
    request: str,
) -> dict[str, tuple[tuple[str, float], ...]]:
    """Build a bounded recall-first pool from every audited contract.

    Typed coverage and role ownership guarantee recall; semantic score orders
    the bounded pool but never gets sole authority to exclude a specialist.
    """

    from agency_runtime.core.workforce.lifecycle_roles import role_anchors

    result: dict[str, tuple[tuple[str, float], ...]] = {}
    for unit in plan.units:
        required = typed_staffing_requirements(unit)
        rows = sorted(
            (
                (
                    contract.agent_id,
                    _semantic_score(unit, contract, request),
                    typed_staffing_coverage(unit, contract),
                )
                for contract in contracts
            ),
            key=lambda item: (-item[1], item[0]),
        )
        by_id = {agent_id: row for row in rows for agent_id in (row[0],)}
        selected: set[str] = set()

        anchor_ids: set[str] = set()
        for agent_id in role_anchors(unit, request=request):
            row = by_id.get(agent_id)
            if row is not None and row[2]:
                selected.add(agent_id)
                anchor_ids.add(agent_id)

        # Preserve at least the strongest owner for every typed requirement.
        # This permits a complementary minimum team without sending the full
        # roster to inference or trusting one aggregate similarity threshold.
        for requirement in required:
            winner = next((row for row in rows if requirement in row[2]), None)
            if winner is not None:
                selected.add(winner[0])

        for agent_id, _score, coverage in rows:
            if coverage:
                selected.add(agent_id)
            if len(selected) >= 16:
                break

        bounded_ids = set(anchor_ids)
        for agent_id, _score, _coverage in rows:
            if agent_id in selected:
                bounded_ids.add(agent_id)
            if len(bounded_ids) >= 16:
                break
        bounded = sorted(
            (by_id[agent_id] for agent_id in bounded_ids),
            key=lambda item: (-item[1], item[0]),
        )[:16]
        result[unit.unit_id] = tuple((agent_id, score) for agent_id, score, _coverage in bounded)
    return result


def _budget(config: AgencyConfig) -> StaffingBudget:
    return StaffingBudget(
        max_work_units=config.workforce.max_work_units,
        max_selected_per_unit=config.workforce.max_selected_per_unit,
        max_selected_total=config.workforce.max_selected_total,
        max_loaded=1,
        max_delegated=config.workforce.max_selected_total,
        min_confidence=config.workforce.min_confidence,
        min_margin=config.workforce.min_margin,
    )


def deterministic_plan_and_staff(
    request: str,
    snapshot: WorkforceIndexSnapshot,
    *,
    config: AgencyConfig,
    context: StaffingContext,
) -> DeterministicWorkforceResult:
    plan, reasons = deterministic_work_plan(request, context=context)
    if plan is None:
        from agency_runtime.core.workforce.staffing_verifier import AbstentionReason

        staffing = StaffingDecision("abstained", (), (AbstentionReason(reasons[0]),))
        return DeterministicWorkforceResult(None, None, staffing, reasons)
    return deterministic_staff_plan(
        request,
        plan,
        snapshot,
        config=config,
        context=context,
    )


def deterministic_staff_plan(
    request: str,
    plan: WorkUnitPlan,
    snapshot: WorkforceIndexSnapshot,
    *,
    config: AgencyConfig,
    context: StaffingContext,
) -> DeterministicWorkforceResult:
    """Recruit the full audited workforce for an already-typed plan locally."""

    rankings = deterministic_rankings(plan, snapshot.contracts, request=request)
    if any(not rankings[unit.unit_id] for unit in plan.units):
        from agency_runtime.core.workforce.staffing_verifier import AbstentionReason

        code = "deterministic_staffing_gap"
        staffing = StaffingDecision("abstained", (), (AbstentionReason(code),))
        return DeterministicWorkforceResult(plan, None, staffing, (code,))
    contracts = {item.agent_id: item for item in snapshot.contracts}
    anchor_floor = 1.0
    for unit in plan.units:
        anchors = frozenset(role_anchors(unit, request=request))
        rankings[unit.unit_id] = tuple(
            sorted(
                (
                    (
                        agent_id,
                        max(score, anchor_floor) if agent_id in anchors else score,
                    )
                    for agent_id, score in rankings[unit.unit_id]
                ),
                key=lambda item: (-item[1], item[0] not in anchors, item[0]),
            )
        )
    required: dict[str, frozenset[str]] = {}
    acceptable: dict[str, frozenset[str]] = {}
    forbidden: dict[str, frozenset[str]] = {}
    for unit in plan.units:
        ranked_ids = frozenset(item for item, _score in rankings[unit.unit_id])
        required_ids = frozenset(
            agent_id
            for agent_id in role_anchors(unit, request=request)
            if agent_id in ranked_ids
            and not typed_staffing_ineligibility(unit, contracts[agent_id], context)
        )
        required[unit.unit_id] = required_ids
        acceptable[unit.unit_id] = ranked_ids.difference(required_ids)
        forbidden[unit.unit_id] = frozenset()
    proposal = build_deterministic_proposal(
        plan,
        snapshot.contracts,
        rankings,
        context=context,
        budget=_budget(config),
        semantic_required=required,
        semantic_acceptable=acceptable,
        semantic_forbidden=forbidden,
        invariant_required=required,
    )
    staffing = verify_staffing(
        plan,
        proposal,
        snapshot.contracts,
        context=context,
        budget=_budget(config),
    )
    codes = tuple(item.code for item in staffing.abstention_reasons)
    return DeterministicWorkforceResult(plan, proposal, staffing, codes)


__all__ = [
    "DeterministicWorkforceResult",
    "deterministic_plan_and_staff",
    "deterministic_rankings",
    "deterministic_staff_plan",
    "deterministic_work_plan",
]
