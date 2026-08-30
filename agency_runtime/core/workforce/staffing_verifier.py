"""Deterministically verify inference-ranked staffing against a roster snapshot."""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from agency_runtime.core.host_capabilities import expand_compatible_hosts
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.planning_contracts import (
    RECRUITMENT_SCHEMA_VERSION,
    RecruiterProposal,
    ShadowEvidence,
    UnitRecruitment,
    WorkUnit,
    WorkUnitPlan,
    parse_recruiter_proposal,
)

_TOKENS = re.compile(r"[a-z0-9]+")
_ASSURANCE_ARTIFACTS = frozenset({"review-report", "test-evidence"})
_ASSURANCE_PHASES = frozenset({"review", "testing", "release"})
_AUTHORITY_COMPATIBILITY = {
    "advise": frozenset({"advise", "plan", "review"}),
    "author": frozenset({"author", "modify"}),
    "modify": frozenset({"modify"}),
    "plan": frozenset({"plan"}),
    "review": frozenset({"review"}),
}


@lru_cache(maxsize=4)
def _workforce_fingerprint(contracts: tuple[WorkforceContract, ...]) -> str:
    """Reuse immutable snapshot validation across per-unit staffing operations."""

    return workforce_index_fingerprint(contracts)


@dataclass(frozen=True, slots=True)
class StaffingBudget:
    max_work_units: int = 16
    max_selected_per_unit: int = 4
    max_selected_total: int = 16
    # Loading and delegating are two deliveries of the same selection, not a
    # hierarchy. Their ceilings stay symmetric; prompt-size limits are enforced
    # separately against the host context budget.
    max_loaded: int = 16
    max_delegated: int = 16
    min_confidence: float = 0.8
    min_margin: float = 0.1

    def __post_init__(self) -> None:
        counts = (
            self.max_work_units,
            self.max_selected_per_unit,
            self.max_selected_total,
            self.max_loaded,
            self.max_delegated,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts
        ):
            raise ValueError("staffing budget counts must be nonnegative integers")
        if not 0 <= self.min_confidence <= 1 or not 0 <= self.min_margin <= 1:
            raise ValueError("staffing confidence and margin bounds must be between zero and one")


@dataclass(frozen=True, slots=True)
class StaffingContext:
    host: str
    platform: str
    available_tools: frozenset[str]
    roster_generation: int
    eligible_worker_ids: frozenset[str] | None = None
    # Deterministic marker-file evidence from the turn's working directory
    # (core/workspace_stacks.py). Surfaced to inference through the context
    # document; deterministic code never selects on it.
    detected_stacks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.host or not self.platform:
            raise ValueError("staffing host and platform are required")
        if isinstance(self.roster_generation, bool) or self.roster_generation < 0:
            raise ValueError("staffing roster generation must be nonnegative")


@dataclass(frozen=True, slots=True)
class AbstentionReason:
    code: str
    unit_id: str = ""
    agent_id: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class VerifiedUnitStaffing:
    unit_id: str
    selected: tuple[str, ...]
    delivery: str
    timing: str
    contexts: tuple[tuple[str, str], ...]
    disabled_shadows: tuple[ShadowEvidence, ...]
    unavailable_shadows: tuple[ShadowEvidence, ...]


# Verifier findings that annotate an accepted staffing decision instead of
# vetoing it (staff-first doctrine). Everything not listed here stays fatal.
ADVISORY_STAFFING_CODES: frozenset[str] = frozenset({"independent_assurance_missing"})


@dataclass(frozen=True, slots=True)
class StaffingDecision:
    status: str
    units: tuple[VerifiedUnitStaffing, ...]
    abstention_reasons: tuple[AbstentionReason, ...]

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _reason(
    reasons: list[AbstentionReason],
    code: str,
    *,
    unit_id: str = "",
    agent_id: str = "",
    detail: str = "",
) -> None:
    item = AbstentionReason(code, unit_id, agent_id, detail)
    if item not in reasons:
        reasons.append(item)


def _tokens(*values: str) -> frozenset[str]:
    return frozenset(token for value in values for token in _TOKENS.findall(value.casefold()))


def _contract_tokens(contract: WorkforceContract) -> frozenset[str]:
    # Identity is audited contract evidence too. The recall scorer has always
    # considered it, so the verifier must use the same evidence vocabulary or
    # exact specialists such as ``python-application-engineer`` can rank first
    # and then be rejected for not spelling their own role again in an outcome.
    return _tokens(
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


def _supports_planning_capability(contract: WorkforceContract, capability: str) -> bool | None:
    """Interpret the planner's controlled broad vocabulary from typed fields."""

    if capability in contract.capability_ids:
        return True
    lifecycle = set(contract.lifecycle_phases)
    artifacts = set(contract.artifact_kinds)
    rule = _CAPABILITY_RULES.get(capability)
    if rule is not None:
        return rule(contract, lifecycle, artifacts)
    if capability == "risk-analysis":
        tokens = _contract_tokens(contract)
        return contract.authority in {"plan", "review"} and bool(
            tokens & {"risk", "risks", "safety", "unsafe"}
        )
    if capability == "architecture":
        # An architecture-record unit needs someone who owns the design. A
        # planner, a designer, or an architect-by-lifecycle fits; a read-only
        # reviewer or implementer does not own the system design.
        return (
            contract.authority == "plan"
            or bool(lifecycle & {"architecture", "design", "planning"})
            or bool(artifacts & {"architecture-record", "plan"})
        )
    return None


def _analysis_rule(contract: WorkforceContract, _lifecycle, _artifacts) -> bool:
    return contract.authority in {"advise", "plan", "review"}


def _audit_rule(contract: WorkforceContract, _lifecycle, _artifacts) -> bool:
    return contract.authority == "review"


def _coordination_rule(_contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return "coordination" in lifecycle


def _design_rule(contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return contract.authority == "plan" or "design" in lifecycle


def _documentation_rule(_contract: WorkforceContract, lifecycle, artifacts) -> bool:
    return "documentation" in artifacts or "documentation" in lifecycle


def _implementation_rule(contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return contract.authority == "modify" or "implementation" in lifecycle


def _investigation_rule(_contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return bool(lifecycle & {"discovery", "review", "testing"})


def _operations_rule(_contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return bool(lifecycle & {"coordination", "release"})


def _planning_rule(contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return contract.authority == "plan" or "planning" in lifecycle


def _review_rule(contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return contract.authority == "review" or "review" in lifecycle


def _testing_rule(_contract: WorkforceContract, lifecycle, artifacts) -> bool:
    return "testing" in lifecycle or bool(artifacts & {"test-code", "test-evidence"})


def _verification_rule(contract: WorkforceContract, lifecycle, _artifacts) -> bool:
    return contract.authority == "review" or "testing" in lifecycle


_CAPABILITY_RULES: dict[str, Callable[[WorkforceContract, set[str], set[str]], bool]] = {
    "analysis": _analysis_rule,
    "audit": _audit_rule,
    "coordination": _coordination_rule,
    "design": _design_rule,
    "documentation": _documentation_rule,
    "implementation": _implementation_rule,
    "investigation": _investigation_rule,
    "operations": _operations_rule,
    "planning": _planning_rule,
    "review": _review_rule,
    "testing": _testing_rule,
    "verification": _verification_rule,
}


def _supports(contract: WorkforceContract, capability: str) -> bool:
    broad = _supports_planning_capability(contract, capability)
    if broad is not None:
        return broad
    required = _tokens(capability)
    return bool(required) and required <= _contract_tokens(contract)


def _authority_satisfies(unit: WorkUnit, contract: WorkforceContract) -> bool:
    """Allow bounded read-only expertise without weakening review or mutation authority."""

    contract_authority = contract.authority
    if (
        unit.authority in {"advise", "review"}
        and unit.artifact_kind == "analysis"
        and unit.lifecycle_phase == "discovery"
        and contract_authority == "modify"
    ):
        # A governed implementer may inspect and diagnose its own specialty in
        # read-only discovery. It still cannot satisfy an independent
        # review-report or any mutation without modify authority on that unit.
        return True
    if (
        unit.authority == "plan"
        and unit.artifact_kind == "plan"
        and unit.lifecycle_phase == "planning"
        and contract_authority == "review"
        and "plan" in contract.artifact_kinds
        and "planning" in contract.lifecycle_phases
    ):
        # An audited reviewer with explicit planning artifacts may author
        # read-only guidance. It still cannot satisfy an independent review
        # or any mutation authority.
        return True
    return contract_authority in _AUTHORITY_COMPATIBILITY.get(unit.authority, frozenset())


def _out_of_scope(contract: WorkforceContract, unit: WorkUnit) -> bool:
    unit_tokens = _tokens(
        unit.outcome,
        unit.artifact_kind,
        unit.lifecycle_phase,
        *unit.domains,
        *unit.languages,
        *unit.frameworks,
        *unit.required_capabilities,
        *unit.risks,
        *unit.trust_boundaries,
    )
    return any(_tokens(value) and _tokens(value) <= unit_tokens for value in contract.not_for)


def _is_live_eligible(contract: WorkforceContract, context: StaffingContext) -> bool:
    eligible = context.eligible_worker_ids
    return eligible is None or contract.agent_id in eligible


def _supports_platform(
    unit: WorkUnit,
    contract: WorkforceContract,
    context: StaffingContext,
) -> bool:
    return context.platform in contract.platforms and context.platform in unit.platforms


def _covers_required_capability(unit: WorkUnit, contract: WorkforceContract) -> bool:
    return not unit.required_capabilities or any(
        _supports(contract, item) for item in unit.required_capabilities
    )


def _contract_binding_reasons(contract: WorkforceContract) -> tuple[str, ...]:
    reasons: list[str] = []
    if contract.schema_version != WORKFORCE_CONTRACT_SCHEMA_VERSION:
        reasons.append("agent_schema_unsupported")
    if contract.audit.status != "approved" or not contract.audit.contract_valid:
        reasons.append("agent_not_approved")
    if not contract.audit.revision or not contract.version or not contract.version_hash:
        reasons.append("agent_version_unbound")
    return tuple(reasons)


def _unit_compatibility_reasons(
    unit: WorkUnit,
    contract: WorkforceContract,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not _authority_satisfies(unit, contract):
        reasons.append("agent_authority_mismatch")
    if unit.domains and not set(unit.domains) & set(contract.domains):
        reasons.append("agent_domain_mismatch")
    if (
        unit.languages + unit.frameworks
        and contract.stacks
        and not set(unit.languages + unit.frameworks) & set(contract.stacks)
    ):
        reasons.append("agent_stack_mismatch")
    if not _covers_required_capability(unit, contract):
        reasons.append("agent_capability_mismatch")
    return tuple(reasons)


def _eligibility(
    unit: WorkUnit,
    contract: WorkforceContract,
    context: StaffingContext,
    *,
    ignore_enabled: bool = False,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not _is_live_eligible(contract, context) and not (ignore_enabled and not contract.enabled):
        reasons.append("agent_not_live_eligible")
    if not contract.enabled and not ignore_enabled:
        reasons.append("agent_disabled")
    reasons.extend(_contract_binding_reasons(contract))
    # ADR-0087: zcode uses the same hook model as codex/claude. Specialists that
    # declare codex or claude are eligible on zcode even though they do not list
    # it (zcode is new; existing contracts predate it), and vice versa. The same
    # equivalence applies to every host pair in expand_compatible_hosts.
    effective_hosts = expand_compatible_hosts(contract.hosts)
    if context.host not in effective_hosts:
        reasons.append("agent_host_unsupported")
    if not _supports_platform(unit, contract, context):
        reasons.append("agent_platform_unsupported")
    required_tools = set(unit.required_tools)
    if not required_tools <= context.available_tools:
        reasons.append("agent_tools_missing")
    # A specialist's declared tool_classes describe what it CAN use, not a
    # precondition the host must satisfy. Re-gating contracts on their full
    # declared tool set (the legacy broad-required-tool trap) rejects the
    # model's best-coverage specialist when it owns an optional surface the
    # host doesn't advertise -- e.g. a security auditor that declares
    # security-analysis on a host that supplies only repository-read. The unit's
    # required-tools check above is the real host-capability gate; the worker's
    # own tools are descriptive metadata, not a hard eligibility failure.
    reasons.extend(_unit_compatibility_reasons(unit, contract))
    if _out_of_scope(contract, unit):
        reasons.append("agent_explicitly_out_of_scope")
    return tuple(reasons)


REQUIREMENT_AXES: frozenset[str] = frozenset(
    {
        "artifact",
        "lifecycle",
        "domain",
        "stack",
        "capability",
        "authority",
    }
)
"""Every axis `_requirements` can name. Team sufficiency is conjunctive across
all of them, so one uncovered axis defeats every possible team."""


def _requirements(unit: WorkUnit) -> tuple[str, ...]:
    values = [
        f"artifact:{unit.artifact_kind}",
        f"lifecycle:{unit.lifecycle_phase}",
        *(f"domain:{item}" for item in unit.domains),
        *(f"stack:{item}" for item in unit.languages + unit.frameworks),
        *(f"capability:{item}" for item in unit.required_capabilities),
        f"authority:{unit.authority}",
    ]
    return tuple(dict.fromkeys(values))


def _coverage(unit: WorkUnit, contract: WorkforceContract) -> frozenset[str]:
    requirements = _requirements(unit)
    covered: set[str] = set()
    if unit.artifact_kind in contract.artifact_kinds:
        covered.add(f"artifact:{unit.artifact_kind}")
    if unit.lifecycle_phase in contract.lifecycle_phases:
        covered.add(f"lifecycle:{unit.lifecycle_phase}")
    covered.update(f"domain:{item}" for item in unit.domains if item in contract.domains)
    if contract.stacks:
        covered.update(
            f"stack:{item}" for item in unit.languages + unit.frameworks if item in contract.stacks
        )
    else:
        # Per-axis wildcard: a contract that declares no stacks neither proves
        # nor disproves stack coverage. Nearly the whole roster predates stack
        # enrichment (4/280 contracts declare stacks), so treating absence as
        # non-coverage made every stack-bearing unit provably unstaffable and
        # forced the recruiter into mandatory gaps. Declared stacks keep exact
        # matching; empty stacks defer the stack judgment to inference.
        covered.update(f"stack:{item}" for item in unit.languages + unit.frameworks)
    covered.update(
        f"capability:{item}" for item in unit.required_capabilities if _supports(contract, item)
    )
    if _authority_satisfies(unit, contract):
        covered.add(f"authority:{unit.authority}")
    # ADR-0118 / settled inference-only contract: deterministic coverage
    # verification is sound only when contracts carry typed coverage fields.
    # When a contract declares none of artifact_kinds, lifecycle_phases, domains,
    # or stacks (the common state for roster specialists before enrichment
    # runs), it can neither prove nor disprove coverage. Treat it as a wildcard
    # that covers every requirement so the recruiter's faithful-match decision
    # is not hard-rejected by a typed-data gate that has no data to evaluate.
    # Objective invariants (eligibility, host/platform/tools, forbidden
    # conflicts) still apply downstream.
    if not covered and not (
        contract.artifact_kinds or contract.lifecycle_phases or contract.domains or contract.stacks
    ):
        return frozenset(requirements)
    return frozenset(covered)


def is_wildcard_coverage(unit: WorkUnit, contract: WorkforceContract) -> bool:
    """Return whether this contract's coverage is a wildcard (no typed fields).

    A wildcard contract covers every requirement by default so the verifier
    does not hard-reject teams that include un-enriched roster specialists.
    But wildcard coverage is NOT positive evidence of fit — callers should
    present it as ``untyped_candidate`` to the recruiter rather than as
    typed coverage.
    """

    return not (
        contract.artifact_kinds or contract.lifecycle_phases or contract.domains or contract.stacks
    )


def typed_staffing_requirements(unit: WorkUnit) -> tuple[str, ...]:
    """Expose the deterministic requirements used to prove team sufficiency."""

    return _requirements(unit)


def typed_staffing_coverage(
    unit: WorkUnit,
    contract: WorkforceContract,
) -> frozenset[str]:
    """Expose one worker's typed contribution without making it eligible."""

    return _coverage(unit, contract)


def typed_staffing_ineligibility(
    unit: WorkUnit,
    contract: WorkforceContract,
    context: StaffingContext,
) -> tuple[str, ...]:
    """Expose deterministic execution exclusions for audited recruitment policy."""

    return _eligibility(unit, contract, context)


def _minimum_team(
    unit: WorkUnit,
    ranked_ids: tuple[str, ...],
    contracts: dict[str, WorkforceContract],
    maximum: int,
) -> tuple[str, ...]:
    required = set(_requirements(unit))
    for size in range(1, min(maximum, len(ranked_ids)) + 1):
        for combination in itertools.combinations(ranked_ids, size):
            combined: set[str] = set()
            for agent_id in combination:
                combined.update(_coverage(unit, contracts[agent_id]))
            if required <= combined:
                return combination
    return ()


def _minimum_team_with_required(
    unit: WorkUnit,
    ranked_ids: tuple[str, ...],
    contracts: dict[str, WorkforceContract],
    required_ids: frozenset[str],
    maximum: int,
) -> tuple[str, ...]:
    if not required_ids:
        return _minimum_team(unit, ranked_ids, contracts, maximum)
    if not required_ids <= set(ranked_ids) or len(required_ids) > maximum:
        return ()
    ordered_required = tuple(item for item in ranked_ids if item in required_ids)
    covered = set().union(*(_coverage(unit, contracts[item]) for item in ordered_required))
    missing = set(_requirements(unit)).difference(covered)
    if not missing:
        return ordered_required
    remaining = tuple(item for item in ranked_ids if item not in required_ids)
    for size in range(1, min(maximum - len(ordered_required), len(remaining)) + 1):
        for additions in itertools.combinations(remaining, size):
            combined = set(covered)
            for agent_id in additions:
                combined.update(_coverage(unit, contracts[agent_id]))
            if set(_requirements(unit)) <= combined:
                chosen = {*ordered_required, *additions}
                return tuple(item for item in ranked_ids if item in chosen)
    return ()


def _semantic_forbidden(row: UnitRecruitment) -> frozenset[str]:
    """Return the set of agents the recruiter classified as forbidden.

    Previously derived from ``row.negative_evidence`` reason codes, but that
    was a round-trip: the deterministic builder wrote ``forbidden`` IDs into
    ``negative_evidence`` with a ``semantic-forbidden`` tag, then this function
    read it back. Derive directly from ``row.forbidden`` instead.
    """

    return frozenset(row.forbidden)


def _rank_signature(items: Sequence[Any]) -> tuple[tuple[str, int, float], ...]:
    return tuple((item.agent_id, item.rank, item.score) for item in items)


def _filtered_ranks(row: UnitRecruitment, predicate: Any) -> tuple[tuple[str, int, float], ...]:
    result: list[tuple[str, int, float]] = []
    for item in row.ranked_semantic:
        if predicate(item.agent_id):
            result.append((item.agent_id, len(result) + 1, item.score))
    return tuple(result)


def _snapshot(
    proposal: RecruiterProposal,
    contracts: Sequence[WorkforceContract],
    context: StaffingContext,
    reasons: list[AbstentionReason],
) -> dict[str, WorkforceContract]:
    roster: dict[str, WorkforceContract] = {}
    for contract in contracts:
        if contract.agent_id in roster:
            _reason(reasons, "duplicate_roster_agent", agent_id=contract.agent_id)
        roster[contract.agent_id] = contract
    try:
        fingerprint = _workforce_fingerprint(tuple(contracts))
    except ValueError as exc:
        _reason(reasons, "invalid_roster_snapshot", detail=str(exc))
        return roster
    if proposal.roster_fingerprint != fingerprint:
        _reason(reasons, "roster_fingerprint_mismatch")
    if proposal.roster_count != len(contracts):
        _reason(reasons, "roster_count_mismatch")
    if proposal.roster_generation != context.roster_generation:
        _reason(reasons, "roster_generation_mismatch")
    return roster


def _ranking(
    unit: WorkUnit,
    row: UnitRecruitment,
    roster: dict[str, WorkforceContract],
    context: StaffingContext,
    reasons: list[AbstentionReason],
) -> tuple[str, ...]:
    for agent_id in sorted({item.agent_id for item in row.ranked_semantic} - set(roster)):
        _reason(reasons, "unknown_ranked_agent", unit_id=unit.unit_id, agent_id=agent_id)
    enabled = _filtered_ranks(row, lambda item: item in roster and roster[item].enabled)
    if _rank_signature(row.ranked_enabled) != enabled:
        _reason(reasons, "ranked_enabled_mismatch", unit_id=unit.unit_id)
    semantic_forbidden = _semantic_forbidden(row)
    executable = _filtered_ranks(
        row,
        lambda item: (
            item in roster
            and item not in semantic_forbidden
            and not _eligibility(unit, roster[item], context)
        ),
    )
    if _rank_signature(row.ranked_executable) != executable:
        _reason(reasons, "ranked_executable_mismatch", unit_id=unit.unit_id)
    return tuple(item[0] for item in executable)


def _selection(
    unit: WorkUnit,
    row: UnitRecruitment,
    roster: dict[str, WorkforceContract],
    executable: tuple[str, ...],
    context: StaffingContext,
    budget: StaffingBudget,
    reasons: list[AbstentionReason],
) -> tuple[str, ...]:
    claimed = set(row.required + row.acceptable + row.forbidden + row.selected + row.runner_up)
    for agent_id in sorted(claimed - set(roster)):
        _reason(reasons, "unknown_claimed_agent", unit_id=unit.unit_id, agent_id=agent_id)
    if not set(row.required) <= set(row.selected):
        _reason(reasons, "required_agents_missing", unit_id=unit.unit_id)
    if not set(row.selected) <= set(row.required + row.acceptable):
        _reason(reasons, "selected_agents_outside_allowed_set", unit_id=unit.unit_id)
    semantic_forbidden = _semantic_forbidden(row)
    expected_forbidden = tuple(
        item.agent_id
        for item in row.ranked_semantic
        if item.agent_id in roster
        and (
            item.agent_id in semantic_forbidden
            or _eligibility(unit, roster[item.agent_id], context)
        )
    )
    if row.forbidden != expected_forbidden:
        _reason(reasons, "forbidden_set_mismatch", unit_id=unit.unit_id)
    if set(row.forbidden) & set(row.selected):
        _reason(reasons, "forbidden_agent_selected", unit_id=unit.unit_id)
    if set(row.runner_up) & (set(row.selected) | set(row.forbidden)):
        _reason(reasons, "runner_up_set_invalid", unit_id=unit.unit_id)
    # ADR-0087: the model's eligible required nomination is the selection
    # authority. Role anchors can order recall and drive the offline-only floor,
    # but determinism must NOT re-derive required from role_anchors in an online
    # proposal. The guarantees below validate eligibility, composition,
    # coverage, and budget around the trusted required set.
    expected = _minimum_team_with_required(
        unit,
        executable,
        roster,
        frozenset(row.required),
        budget.max_selected_per_unit,
    )
    if row.selected != expected:
        _reason(reasons, "selected_not_deterministic_minimum", unit_id=unit.unit_id)
    if not expected:
        _reason(reasons, "no_safe_sufficient_team", unit_id=unit.unit_id)
    expected_runner = tuple(item for item in executable if item not in expected)[
        : len(row.runner_up)
    ]
    if row.runner_up != expected_runner:
        _reason(reasons, "runner_up_order_mismatch", unit_id=unit.unit_id)
    return expected


def _shadow_signature(
    items: Sequence[ShadowEvidence],
) -> tuple[tuple[str, int, tuple[str, ...], str], ...]:
    return tuple(
        (item.agent_id, item.rank, item.reason_codes, item.fallback_agent_id) for item in items
    )


def _shadows(
    unit: WorkUnit,
    row: UnitRecruitment,
    roster: dict[str, WorkforceContract],
    context: StaffingContext,
    selected: tuple[str, ...],
    reasons: list[AbstentionReason],
) -> None:
    fallback = selected[0] if selected else ""
    fallback_rank = next(
        (item.rank for item in row.ranked_semantic if item.agent_id == fallback),
        len(row.ranked_semantic) + 1,
    )
    disabled: list[tuple[str, int, tuple[str, ...], str]] = []
    unavailable: list[tuple[str, int, tuple[str, ...], str]] = []
    for item in row.ranked_semantic:
        if item.rank >= fallback_rank or item.agent_id not in roster:
            continue
        contract = roster[item.agent_id]
        failed = _eligibility(unit, contract, context)
        if not failed:
            continue
        target = (
            disabled
            if not contract.enabled
            and not _eligibility(unit, contract, context, ignore_enabled=True)
            else unavailable
        )
        target.append((item.agent_id, item.rank, failed, fallback))
    if _shadow_signature(row.disabled_shadows) != tuple(disabled):
        _reason(reasons, "disabled_shadow_mismatch", unit_id=unit.unit_id)
    if _shadow_signature(row.unavailable_shadows) != tuple(unavailable):
        _reason(reasons, "unavailable_shadow_mismatch", unit_id=unit.unit_id)


def _ancestors(plan: WorkUnitPlan, unit_id: str) -> frozenset[str]:
    units = {unit.unit_id: unit for unit in plan.units}
    found: set[str] = set()
    pending = list(units[unit_id].depends_on)
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(units[current].depends_on)
    return frozenset(found)


def _agent_composition(
    row: UnitRecruitment,
    agent_id: str,
    binding: dict[str, str],
    ancestor_units: frozenset[str],
    ancestor_agents: set[str],
    required_agents: set[str],
    selected: dict[str, tuple[str, ...]],
    contexts: dict[str, dict[str, str]],
    roster: dict[str, WorkforceContract],
    context: StaffingContext,
    reasons: list[AbstentionReason],
) -> None:
    if agent_id not in roster:
        return
    contract = roster[agent_id]
    relation = contract.composition
    if row.delivery == "delegate" and "native-delegation" not in context.available_tools:
        _reason(
            reasons,
            "native_delegation_unavailable",
            unit_id=row.unit_id,
            agent_id=agent_id,
        )
    checks = (
        (relation.selection_exclusive, "selection_exclusive_conflict", set(row.selected)),
        (
            relation.requires,
            "required_composition_agent_missing",
            required_agents,
        ),
        (relation.must_follow, "composition_order_invalid", ancestor_agents),
    )
    for targets, code, present in checks:
        for target in targets:
            if (code == "selection_exclusive_conflict" and target in present) or (
                code != "selection_exclusive_conflict" and target not in present
            ):
                _reason(
                    reasons,
                    code,
                    unit_id=row.unit_id,
                    agent_id=agent_id,
                    detail=target,
                )
    for target in relation.same_context_conflicts:
        if target in binding and binding[target] == binding[agent_id]:
            _reason(
                reasons,
                "same_context_conflict",
                unit_id=row.unit_id,
                agent_id=agent_id,
                detail=target,
            )
    for target in relation.must_review_independently:
        if target not in ancestor_agents:
            _reason(
                reasons,
                "independent_review_target_missing",
                unit_id=row.unit_id,
                agent_id=agent_id,
                detail=target,
            )
            continue
        target_units = [name for name in ancestor_units if target in selected[name]]
        if binding[agent_id] in {contexts[name].get(target, "") for name in target_units}:
            _reason(
                reasons,
                "review_context_reused",
                unit_id=row.unit_id,
                agent_id=agent_id,
                detail=target,
            )
        own_class = relation.independence_class
        if own_class and own_class == roster[target].composition.independence_class:
            _reason(
                reasons,
                "review_independence_class_reused",
                unit_id=row.unit_id,
                agent_id=agent_id,
                detail=target,
            )


def _substitution_groups(
    row: UnitRecruitment,
    roster: dict[str, WorkforceContract],
    reasons: list[AbstentionReason],
) -> None:
    groups: dict[str, list[str]] = {}
    for agent_id in row.selected:
        if agent_id in roster and roster[agent_id].composition.substitution_group:
            groups.setdefault(roster[agent_id].composition.substitution_group, []).append(agent_id)
    for group, members in groups.items():
        if len(members) > 1 and not all(
            other in roster[member].composition.complements
            for member in members
            for other in members
            if member != other
        ):
            _reason(reasons, "redundant_substitution_group", unit_id=row.unit_id, detail=group)


def _composition(
    plan: WorkUnitPlan,
    proposal: RecruiterProposal,
    roster: dict[str, WorkforceContract],
    context: StaffingContext,
    reasons: list[AbstentionReason],
) -> None:
    units = {unit.unit_id: unit for unit in plan.units}
    selected = {row.unit_id: row.selected for row in proposal.units}
    contexts = {
        row.unit_id: {item.agent_id: item.context_id for item in row.contexts}
        for row in proposal.units
    }
    for row in proposal.units:
        binding = contexts[row.unit_id]
        if tuple(binding) != row.selected or len(binding) != len(row.contexts):
            _reason(reasons, "context_binding_mismatch", unit_id=row.unit_id)
            continue
        if row.delivery == "delegate" and len(set(binding.values())) != len(binding):
            _reason(reasons, "delegated_context_not_distinct", unit_id=row.unit_id)
        ancestor_units = _ancestors(plan, row.unit_id)
        ancestor_agents = {agent for name in ancestor_units for agent in selected[name]}
        downstream_assurance_agents = {
            agent_id
            for candidate in proposal.units
            for agent_id in candidate.selected
            if row.unit_id in _ancestors(plan, candidate.unit_id)
            and units[candidate.unit_id].authority == "review"
            and units[candidate.unit_id].artifact_kind in _ASSURANCE_ARTIFACTS
            and units[candidate.unit_id].lifecycle_phase in _ASSURANCE_PHASES
            and candidate.timing == "after_artifact"
        }
        required_agents = set(row.selected) | ancestor_agents | downstream_assurance_agents
        for agent_id in row.selected:
            _agent_composition(
                row,
                agent_id,
                binding,
                ancestor_units,
                ancestor_agents,
                required_agents,
                selected,
                contexts,
                roster,
                context,
                reasons,
            )
        _substitution_groups(row, roster, reasons)


def _has_assurance(
    source_id: str,
    plan: WorkUnitPlan,
    proposal: RecruiterProposal,
    roster: dict[str, WorkforceContract],
) -> bool:
    source = next(row for row in proposal.units if row.unit_id == source_id)
    source_contexts = {item.context_id for item in source.contexts}
    source_classes = {
        roster[item].composition.independence_class
        for item in source.selected
        if item in roster and roster[item].composition.independence_class
    }
    units = {unit.unit_id: unit for unit in plan.units}
    for row in proposal.units:
        unit = units[row.unit_id]
        if source_id not in _ancestors(plan, unit.unit_id):
            continue
        if (
            unit.authority != "review"
            or unit.artifact_kind not in _ASSURANCE_ARTIFACTS
            or unit.lifecycle_phase not in _ASSURANCE_PHASES
            or row.timing != "after_artifact"
        ):
            continue
        row_contexts = {item.context_id for item in row.contexts}
        row_classes = {
            roster[item].composition.independence_class
            for item in row.selected
            if item in roster and roster[item].composition.independence_class
        }
        if (
            not set(row.selected) & set(source.selected)
            and not row_contexts & source_contexts
            and not row_classes & source_classes
        ):
            return True
    return False


def _assurance(
    plan: WorkUnitPlan,
    proposal: RecruiterProposal,
    roster: dict[str, WorkforceContract],
    reasons: list[AbstentionReason],
) -> None:
    for unit in plan.units:
        required = unit.authority == "modify" and (
            unit.mutation_scope != "read_only"
            or (bool(unit.claims) and unit.artifact_kind in {"implementation-change", "test-code"})
        )
        if required and not _has_assurance(unit.unit_id, plan, proposal, roster):
            _reason(reasons, "independent_assurance_missing", unit_id=unit.unit_id)


def _budgets(
    plan: WorkUnitPlan,
    proposal: RecruiterProposal,
    budget: StaffingBudget,
    reasons: list[AbstentionReason],
) -> None:
    if len(plan.units) > budget.max_work_units:
        _reason(reasons, "work_unit_budget_exceeded")
    total = sum(len(row.selected) for row in proposal.units)
    loaded = sum(len(row.selected) for row in proposal.units if row.delivery == "load")
    delegated = sum(len(row.selected) for row in proposal.units if row.delivery == "delegate")
    if total > budget.max_selected_total:
        _reason(reasons, "selected_agent_budget_exceeded")
    if loaded > budget.max_loaded:
        _reason(reasons, "loaded_agent_budget_exceeded")
    if delegated > budget.max_delegated:
        _reason(reasons, "delegated_agent_budget_exceeded")
    for row in proposal.units:
        if len(row.selected) > budget.max_selected_per_unit:
            _reason(reasons, "unit_agent_budget_exceeded", unit_id=row.unit_id)
        if row.selected and row.confidence < budget.min_confidence:
            _reason(reasons, "selection_confidence_too_low", unit_id=row.unit_id)
        if row.selected and row.margin < budget.min_margin:
            _reason(reasons, "selection_margin_too_low", unit_id=row.unit_id)


def verify_staffing(
    plan: WorkUnitPlan,
    proposal: RecruiterProposal,
    contracts: Sequence[WorkforceContract],
    *,
    context: StaffingContext,
    budget: StaffingBudget | None = None,
    explicit_indivisible_unit: bool = False,
) -> StaffingDecision:
    """Recompute a proposal and accept it only when the complete recipe is safe."""

    active_budget = budget or StaffingBudget()
    reasons: list[AbstentionReason] = []
    if proposal.plan_hash != plan.plan_hash:
        _reason(reasons, "plan_hash_mismatch")
    roster = _snapshot(proposal, contracts, context, reasons)
    for unit, row in zip(plan.units, proposal.units, strict=True):
        executable = _ranking(unit, row, roster, context, reasons)
        selected = _selection(unit, row, roster, executable, context, active_budget, reasons)
        _shadows(unit, row, roster, context, selected, reasons)
        if not row.selected:
            for detail in row.abstention_reasons or ("no_safe_candidate",):
                _reason(reasons, "recruiter_abstained", unit_id=row.unit_id, detail=detail)
    _composition(plan, proposal, roster, context, reasons)
    if not (explicit_indivisible_unit and len(plan.units) == 1):
        _assurance(plan, proposal, roster, reasons)
    _budgets(plan, proposal, active_budget, reasons)
    # Staff-first doctrine: advisory findings annotate an accepted decision
    # instead of vetoing it. Missing independent assurance is a composition
    # preference the receipt records honestly; it is not a reason to leave a
    # fully staffed team unstaffed. Every other code stays fatal, and any
    # unstaffed unit keeps the whole decision abstained regardless.
    fatal = [item for item in reasons if item.code not in ADVISORY_STAFFING_CODES]
    fully_staffed = all(row.selected for row in proposal.units)
    if fatal or not fully_staffed:
        return StaffingDecision("abstained", (), tuple(reasons))
    return StaffingDecision(
        "accepted",
        tuple(
            VerifiedUnitStaffing(
                row.unit_id,
                row.selected,
                row.delivery,
                row.timing,
                tuple((item.agent_id, item.context_id) for item in row.contexts),
                row.disabled_shadows,
                row.unavailable_shadows,
            )
            for row in proposal.units
        ),
        # Advisory findings ride along on the accepted decision so receipts
        # stay honest about composition preferences the team does not meet.
        tuple(reasons),
    )


def _validated_semantic_gap_units(
    plan: WorkUnitPlan,
    semantic_gap_units: frozenset[str] | None,
) -> frozenset[str]:
    declared_gaps = semantic_gap_units or frozenset()
    if declared_gaps - frozenset(unit.unit_id for unit in plan.units):
        raise ValueError("semantic gap units must belong to the plan")
    return declared_gaps


def build_deterministic_proposal(
    plan: WorkUnitPlan,
    contracts: Sequence[WorkforceContract],
    rankings: Mapping[str, Sequence[tuple[str, float]]],
    *,
    context: StaffingContext,
    budget: StaffingBudget | None = None,
    semantic_required: Mapping[str, frozenset[str]] | None = None,
    semantic_acceptable: Mapping[str, frozenset[str]] | None = None,
    semantic_forbidden: Mapping[str, frozenset[str]] | None = None,
    invariant_required: Mapping[str, frozenset[str]] | None = None,
    semantic_gap_units: frozenset[str] | None = None,
) -> RecruiterProposal:
    """Build a verifier-compatible proposal from deterministic semantic ranks."""

    active_budget = budget or StaffingBudget()
    declared_gaps = _validated_semantic_gap_units(plan, semantic_gap_units)
    roster = {item.agent_id: item for item in contracts}
    if len(roster) != len(contracts):
        raise ValueError("deterministic proposal roster contains duplicate agents")
    rows: list[dict[str, Any]] = []
    for unit in plan.units:
        raw_ranks = rankings.get(unit.unit_id, ())
        if len(raw_ranks) > 16 or (not raw_ranks and unit.unit_id not in declared_gaps):
            raise ValueError("verified proposal requires one bounded ranking per staffed unit")
        seen: set[str] = set()
        semantic: list[tuple[str, float]] = []
        for agent_id, score in raw_ranks:
            if agent_id not in roster or agent_id in seen:
                raise ValueError("deterministic ranking contains an unknown or duplicate agent")
            if isinstance(score, bool) or not 0.0 <= float(score) <= 1.0:
                raise ValueError("deterministic ranking score must be between zero and one")
            seen.add(agent_id)
            semantic.append((agent_id, round(float(score), 6)))
        if any(left[1] < right[1] for left, right in itertools.pairwise(semantic)):
            raise ValueError("deterministic ranking scores must be descending")
        explicit_semantics = any(
            mapping is not None
            for mapping in (semantic_required, semantic_acceptable, semantic_forbidden)
        )
        required_ids = (
            frozenset()
            if semantic_required is None
            else semantic_required.get(unit.unit_id, frozenset())
        )
        acceptable_ids = (
            frozenset()
            if semantic_acceptable is None
            else semantic_acceptable.get(unit.unit_id, frozenset())
        )
        forbidden_ids = (
            frozenset()
            if semantic_forbidden is None
            else semantic_forbidden.get(unit.unit_id, frozenset())
        )
        invariant_ids = (
            frozenset()
            if invariant_required is None
            else invariant_required.get(unit.unit_id, frozenset())
        )
        if invariant_ids - required_ids:
            raise ValueError("invariant staffing owners must also be semantically required")
        ranked_ids = {agent_id for agent_id, _score in semantic}
        if (
            (required_ids | acceptable_ids | forbidden_ids) != ranked_ids
            or required_ids & acceptable_ids
            or required_ids & forbidden_ids
            or acceptable_ids & forbidden_ids
        ) and explicit_semantics:
            raise ValueError("semantic staffing classes must partition the complete ranking")
        enabled = [(agent_id, score) for agent_id, score in semantic if roster[agent_id].enabled]
        executable = [
            (agent_id, score)
            for agent_id, score in semantic
            if agent_id not in forbidden_ids and not _eligibility(unit, roster[agent_id], context)
        ]
        selected = _minimum_team_with_required(
            unit,
            tuple(agent_id for agent_id, _score in executable),
            roster,
            required_ids,
            active_budget.max_selected_per_unit,
        )
        runner_up = tuple(agent_id for agent_id, _score in executable if agent_id not in selected)[
            :2
        ]
        forbidden = tuple(
            agent_id
            for agent_id, _score in semantic
            if agent_id in forbidden_ids or _eligibility(unit, roster[agent_id], context)
        )
        fallback = selected[0] if selected else ""
        fallback_rank = next(
            (index for index, (agent_id, _score) in enumerate(semantic, 1) if agent_id == fallback),
            len(semantic) + 1,
        )
        disabled_shadows: list[dict[str, Any]] = []
        unavailable_shadows: list[dict[str, Any]] = []
        for rank, (agent_id, _score) in enumerate(semantic, 1):
            if rank >= fallback_rank:
                continue
            contract = roster[agent_id]
            failed = _eligibility(unit, contract, context)
            if not failed:
                continue
            target = (
                disabled_shadows
                if not contract.enabled
                and not _eligibility(unit, contract, context, ignore_enabled=True)
                else unavailable_shadows
            )
            target.append(
                {
                    "agent_id": agent_id,
                    "rank": rank,
                    "reason_codes": list(failed),
                    "fallback_agent_id": fallback,
                    "tradeoff": "The higher deterministic match is unavailable under current policy.",
                }
            )
        score_by_id = dict(semantic)
        confidence = min((score_by_id[item] for item in selected), default=0.0)
        # Margin compares complete executable teams, not an individually
        # higher-ranked worker that cannot satisfy the unit. Treating a partial
        # near neighbor as the runner made a safely sufficient lower-ranked
        # specialist look ambiguous and forced false abstentions.
        if invariant_ids:
            # A lifecycle owner is a semantic invariant, not an interchangeable
            # runner-up. Keep required owners in the comparison pool and vary
            # only complementary workers. If the required minimum is already
            # the selected team, there is no valid alternative team.
            selected_complements = set(selected).difference(invariant_ids)
            alternative = _minimum_team_with_required(
                unit,
                tuple(
                    agent_id
                    for agent_id, _score in executable
                    if agent_id not in selected_complements
                ),
                roster,
                invariant_ids,
                active_budget.max_selected_per_unit,
            )
            if alternative == selected:
                alternative = ()
        else:
            alternative = _minimum_team(
                unit,
                tuple(agent_id for agent_id, _score in executable if agent_id not in selected),
                roster,
                active_budget.max_selected_per_unit,
            )
        alternative_score = min(
            (score_by_id[item] for item in alternative),
            default=0.0,
        )
        margin = round(max(0.0, confidence - alternative_score), 6) if selected else 0.0
        projected_required = required_ids if explicit_semantics else frozenset(selected)
        projected_acceptable = acceptable_ids if explicit_semantics else frozenset()
        rows.append(
            {
                "unit_id": unit.unit_id,
                "required": [item for item, _score in semantic if item in projected_required],
                "acceptable": [item for item, _score in semantic if item in projected_acceptable],
                "forbidden": list(forbidden),
                "selected": list(selected),
                "runner_up": list(runner_up),
                "ranked_semantic": [
                    {"agent_id": item, "rank": rank, "score": score}
                    for rank, (item, score) in enumerate(semantic, 1)
                ],
                "ranked_enabled": [
                    {"agent_id": item, "rank": rank, "score": score}
                    for rank, (item, score) in enumerate(enabled, 1)
                ],
                "ranked_executable": [
                    {"agent_id": item, "rank": rank, "score": score}
                    for rank, (item, score) in enumerate(executable, 1)
                ],
                "disabled_shadows": disabled_shadows,
                "unavailable_shadows": unavailable_shadows,
                "contexts": [
                    {"agent_id": item, "context_id": f"ctx-{unit.unit_id}-{item}"}
                    for item in selected
                ],
                "confidence": confidence,
                "margin": margin,
                "delivery": "load",
                "timing": "after_artifact"
                if unit.authority == "review" and unit.depends_on
                else "immediate",
                "abstention_reasons": (
                    []
                    if selected
                    else [
                        "inference-declared-gap"
                        if unit.unit_id in declared_gaps
                        else "no-safe-deterministic-team"
                    ]
                ),
            }
        )
    return parse_recruiter_proposal(
        {
            "schema_version": RECRUITMENT_SCHEMA_VERSION,
            "plan_hash": plan.plan_hash,
            "roster_fingerprint": _workforce_fingerprint(tuple(contracts)),
            "roster_count": len(contracts),
            "roster_generation": context.roster_generation,
            "units": rows,
        },
        plan,
    )


# The same closed verifier composes an inference-authored ranking in production
# and deterministic evaluation inputs in offline tests. Give the production
# path an evidence-faithful name while retaining the historical helper as an
# explicit compatibility surface for deterministic test fixtures.
build_verified_proposal = build_deterministic_proposal


__all__ = [
    "AbstentionReason",
    "StaffingBudget",
    "StaffingContext",
    "StaffingDecision",
    "VerifiedUnitStaffing",
    "build_deterministic_proposal",
    "build_verified_proposal",
    "typed_staffing_coverage",
    "typed_staffing_ineligibility",
    "typed_staffing_requirements",
    "verify_staffing",
]
