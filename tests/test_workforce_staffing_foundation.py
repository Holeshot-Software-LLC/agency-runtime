"""Safety matrix for plan-first, inference-ranked workforce staffing."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agency_runtime.core.workforce import (
    StaffingBudget,
    StaffingContext,
    parse_recruiter_proposal,
    parse_work_unit_plan,
    verify_staffing,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
)
from agency_runtime.core.workforce.staffing_verifier import build_deterministic_proposal

_HASH = "sha256:" + "a" * 64
_GENERATION = 7


def _contract(
    agent_id: str,
    *,
    outcomes: tuple[str, ...],
    artifact: str = "analysis",
    lifecycle: str = "discovery",
    authority: str = "advise",
    domains: tuple[str, ...] = ("software-engineering",),
    stacks: tuple[str, ...] = (),
    enabled: bool = True,
    context_mode: str = "isolated_only",
    hosts: tuple[str, ...] = ("codex", "claude", "openclaw", "hermes"),
    platforms: tuple[str, ...] = ("windows", "linux"),
    tools: tuple[str, ...] = ("repository-read",),
    composition: CompositionContract | None = None,
) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="implementer" if authority == "modify" else "reviewer",
        outcomes=outcomes,
        capability_ids=(
            "implementation"
            if artifact == "implementation-change"
            else "testing"
            if artifact in {"test-code", "test-evidence"}
            else "review"
            if artifact == "review-report"
            else "analysis",
        ),
        artifact_kinds=(artifact,),
        lifecycle_phases=(lifecycle,),
        domains=domains,
        stacks=stacks,
        scope_qualifiers=(),
        not_for=(),
        authority=authority,
        context_mode=context_mode,
        tool_classes=tools,
        hosts=hosts,
        platforms=platforms,
        composition=composition or CompositionContract(independence_class=agent_id),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=enabled,
        employment="employee" if enabled else "disabled",
        origin="upstream",
    )


def _unit(
    unit_id: str,
    *,
    artifact: str = "analysis",
    lifecycle: str = "discovery",
    capabilities: tuple[str, ...] = ("technical-analysis",),
    authority: str = "advise",
    mutation: str = "read_only",
    languages: tuple[str, ...] = (),
    frameworks: tuple[str, ...] = (),
    claims: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "outcome": f"Complete {unit_id}",
        "artifact_kind": artifact,
        "lifecycle_phase": lifecycle,
        "domains": ["software-engineering"],
        "languages": list(languages),
        "frameworks": list(frameworks),
        "required_capabilities": list(capabilities),
        "authority": authority,
        "mutation_scope": mutation,
        "risks": ["regression"],
        "trust_boundaries": ["repository"],
        "claims": list(claims),
        "depends_on": list(depends_on),
        "resources": ["repository"],
        "required_tools": ["repository-read"],
        "platforms": ["windows", "linux"],
        "acceptance_evidence": [f"{unit_id} verified"],
        "parallelization": "unspecified",
    }


def _plan(*units: dict[str, object]):
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Complete the requested work with safe staffing.",
            "units": list(units),
        }
    )


def _ranks(ids: tuple[str, ...], semantic: tuple[str, ...]) -> list[dict[str, object]]:
    scores = {agent_id: round(1 - index * 0.05, 2) for index, agent_id in enumerate(semantic)}
    return [
        {"agent_id": agent_id, "rank": index, "score": scores[agent_id]}
        for index, agent_id in enumerate(ids, 1)
    ]


def _row(
    unit,
    roster: tuple[WorkforceContract, ...],
    *,
    semantic: tuple[str, ...],
    executable: tuple[str, ...],
    selected: tuple[str, ...],
    forbidden: tuple[str, ...] = (),
    runner_up: tuple[str, ...] = (),
    disabled_shadows: tuple[dict[str, object], ...] = (),
    unavailable_shadows: tuple[dict[str, object], ...] = (),
    delivery: str = "delegate",
    timing: str = "immediate",
    context_id: str | None = None,
    confidence: float = 0.95,
    margin: float = 0.4,
) -> dict[str, object]:
    contracts = {item.agent_id: item for item in roster}
    enabled = tuple(item for item in semantic if contracts[item].enabled)
    return {
        "unit_id": unit.unit_id,
        "required": list(selected),
        "acceptable": [],
        "forbidden": list(forbidden),
        "selected": list(selected),
        "runner_up": list(runner_up),
        "ranked_semantic": _ranks(semantic, semantic),
        "ranked_enabled": _ranks(enabled, semantic),
        "ranked_executable": _ranks(executable, semantic),
        "disabled_shadows": list(disabled_shadows),
        "unavailable_shadows": list(unavailable_shadows),
        "contexts": [
            {
                "agent_id": agent,
                "context_id": context_id or f"ctx-{unit.unit_id}-{agent}",
            }
            for agent in selected
        ],
        "confidence": confidence,
        "margin": margin,
        "delivery": delivery,
        "timing": timing,
        "abstention_reasons": [] if selected else ["no-safe-candidate"],
    }


def _proposal(plan, roster: tuple[WorkforceContract, ...], *rows: dict[str, object]):
    return parse_recruiter_proposal(
        {
            "schema_version": 2,
            "plan_hash": plan.plan_hash,
            "roster_fingerprint": workforce_index_fingerprint(roster),
            "roster_count": len(roster),
            "roster_generation": _GENERATION,
            "units": list(rows),
        },
        plan,
    )


def _context() -> StaffingContext:
    return StaffingContext(
        "codex",
        "windows",
        frozenset({"native-delegation", "repository-read"}),
        _GENERATION,
    )


def test_review_authority_can_satisfy_advisory_analysis_but_not_the_reverse() -> None:
    review_worker = _contract(
        "codebase-onboarding-engineer",
        outcomes=("Map repository code paths",),
        authority="review",
    )
    advisory_plan = _plan(_unit("unit-map", authority="advise", capabilities=("analysis",)))
    context = _context()
    advisory_proposal = build_deterministic_proposal(
        advisory_plan,
        (review_worker,),
        {"unit-map": (("codebase-onboarding-engineer", 0.99),)},
        context=context,
        budget=StaffingBudget(),
    )

    advisory = verify_staffing(
        advisory_plan,
        advisory_proposal,
        (review_worker,),
        context=context,
        budget=StaffingBudget(),
    )

    assert advisory.accepted
    assert advisory.units[0].selected == ("codebase-onboarding-engineer",)

    advisor = replace(review_worker, authority="advise")
    review_plan = _plan(_unit("unit-review", authority="review", capabilities=("analysis",)))
    review_proposal = build_deterministic_proposal(
        review_plan,
        (advisor,),
        {"unit-review": (("codebase-onboarding-engineer", 0.99),)},
        context=context,
        budget=StaffingBudget(),
    )
    review = verify_staffing(
        review_plan,
        review_proposal,
        (advisor,),
        context=context,
        budget=StaffingBudget(),
    )

    assert not review.accepted
    assert "agent_authority_mismatch" in {
        reason
        for item in review_proposal.units[0].unavailable_shadows
        for reason in item.reason_codes
    }


def _codes(decision) -> set[str]:
    return {item.code for item in decision.abstention_reasons}


def _implementation_roster() -> tuple[WorkforceContract, ...]:
    return (
        _contract(
            "python-engineer",
            outcomes=("Python packaging implementation",),
            artifact="implementation-change",
            lifecycle="implementation",
            authority="modify",
            stacks=("python",),
        ),
        _contract(
            "code-reviewer",
            outcomes=("Independent code review",),
            artifact="review-report",
            lifecycle="review",
            authority="review",
            composition=CompositionContract(
                must_review_independently=("python-engineer",),
                independence_class="review",
            ),
        ),
    )


def test_valid_implementation_requires_and_accepts_independent_assurance() -> None:
    roster = _implementation_roster()
    plan = _plan(
        _unit(
            "unit-implement",
            artifact="implementation-change",
            lifecycle="implementation",
            capabilities=("python-packaging",),
            authority="modify",
            mutation="workspace_write",
            languages=("python",),
        ),
        _unit(
            "unit-review",
            artifact="review-report",
            lifecycle="review",
            capabilities=("code-review",),
            authority="review",
            depends_on=("unit-implement",),
        ),
    )
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("python-engineer",),
            executable=("python-engineer",),
            selected=("python-engineer",),
        ),
        _row(
            plan.units[1],
            roster,
            semantic=("code-reviewer",),
            executable=("code-reviewer",),
            selected=("code-reviewer",),
            timing="after_artifact",
        ),
    )

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.accepted
    assert decision.units[0].contexts == (
        ("python-engineer", "ctx-unit-implement-python-engineer"),
    )


def test_plan_and_proposal_schemas_are_closed_bounded_and_snapshot_bound() -> None:
    raw = _unit("unit-one")
    raw["agent_id"] = "code-reviewer"
    with pytest.raises(ValueError, match="exactly"):
        _plan(raw)
    with pytest.raises(ValueError, match="earlier units"):
        _plan(_unit("unit-one", depends_on=("unit-two",)), _unit("unit-two"))
    with pytest.raises(ValueError, match="bounded list"):
        _plan(*(_unit(f"unit-{index}") for index in range(17)))


def test_plan_hash_roster_fingerprint_count_and_generation_are_authoritative() -> None:
    roster = (_contract("analyst", outcomes=("Technical analysis",)),)
    plan = _plan(_unit("unit-analysis"))
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("analyst",),
            executable=("analyst",),
            selected=("analyst",),
        ),
    )
    stale = replace(
        proposal,
        plan_hash="sha256:" + "b" * 64,
        roster_fingerprint="sha256:" + "c" * 64,
        roster_count=2,
        roster_generation=8,
    )

    decision = verify_staffing(plan, stale, roster, context=_context())

    assert {
        "plan_hash_mismatch",
        "roster_fingerprint_mismatch",
        "roster_count_mismatch",
        "roster_generation_mismatch",
    } <= _codes(decision)
    assert decision.units == ()


def test_wrong_but_host_and_tool_compatible_candidate_is_rejected() -> None:
    roster = (
        _contract("generic-coder", outcomes=("General coding",)),
        _contract("security-analyst", outcomes=("Supply chain security analysis",)),
    )
    plan = _plan(_unit("unit-security", capabilities=("supply-chain-security",)))
    row = _row(
        plan.units[0],
        roster,
        semantic=("generic-coder", "security-analyst"),
        executable=("security-analyst",),
        selected=("generic-coder",),
        forbidden=("generic-coder",),
    )
    proposal = _proposal(plan, roster, row)

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert {
        "forbidden_agent_selected",
        "selected_not_deterministic_minimum",
    } <= _codes(decision)


def test_semantically_forbidden_near_neighbor_cannot_enter_executable_team() -> None:
    roster = (
        _contract("wrong-neighbor", outcomes=("Technical analysis",)),
        _contract("right-specialist", outcomes=("Technical analysis",)),
    )
    plan = _plan(_unit("unit-analysis"))
    proposal = build_deterministic_proposal(
        plan,
        roster,
        {
            "unit-analysis": (
                ("wrong-neighbor", 1.0),
                ("right-specialist", 0.9),
            )
        },
        context=_context(),
        semantic_required={"unit-analysis": frozenset({"right-specialist"})},
        semantic_acceptable={"unit-analysis": frozenset()},
        semantic_forbidden={"unit-analysis": frozenset({"wrong-neighbor"})},
    )

    row = proposal.units[0]
    assert row.selected == ("right-specialist",)
    assert tuple(item.agent_id for item in row.ranked_semantic) == (
        "wrong-neighbor",
        "right-specialist",
    )
    assert tuple(item.agent_id for item in row.ranked_executable) == ("right-specialist",)
    assert row.forbidden == ("wrong-neighbor",)
    assert verify_staffing(plan, proposal, roster, context=_context()).accepted


def test_semantic_staffing_classes_must_partition_the_ranking() -> None:
    roster = (_contract("right-specialist", outcomes=("Technical analysis",)),)
    plan = _plan(_unit("unit-analysis"))

    with pytest.raises(ValueError, match="partition"):
        build_deterministic_proposal(
            plan,
            roster,
            {"unit-analysis": (("right-specialist", 1.0),)},
            context=_context(),
            semantic_required={"unit-analysis": frozenset()},
            semantic_acceptable={"unit-analysis": frozenset()},
            semantic_forbidden={"unit-analysis": frozenset()},
        )


def test_worker_declared_tools_are_descriptive_not_a_host_precondition() -> None:
    # ADR-0087 / pipeline intent: a specialist's declared tool_classes describe
    # what it CAN use, not tools the host must provide. The browser-reviewer
    # declares browser-interaction, but on a host that supplies the unit's
    # required tools it remains eligible -- its declared tool is descriptive
    # metadata, not a hard gate. Only the unit's required-tools check (host
    # capability) is a hard eligibility failure.
    roster = (
        _contract(
            "browser-reviewer",
            outcomes=("Technical analysis",),
            tools=("repository-read", "browser-interaction"),
        ),
    )
    plan = _plan(_unit("unit-analysis"))
    proposal = build_deterministic_proposal(
        plan,
        roster,
        {"unit-analysis": (("browser-reviewer", 1.0),)},
        context=_context(),
    )

    assert proposal.units[0].selected == ("browser-reviewer",)


def test_disabled_shadow_winner_is_reported_while_enabled_fallback_is_safe() -> None:
    roster = (
        _contract("ideal-analyst", outcomes=("Technical analysis",), enabled=False),
        _contract("fallback-analyst", outcomes=("Technical analysis",)),
    )
    plan = _plan(_unit("unit-analysis"))
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("ideal-analyst", "fallback-analyst"),
            executable=("fallback-analyst",),
            selected=("fallback-analyst",),
            forbidden=("ideal-analyst",),
            disabled_shadows=(
                {
                    "agent_id": "ideal-analyst",
                    "rank": 1,
                    "reason_codes": ["agent_disabled"],
                    "fallback_agent_id": "fallback-analyst",
                    "tradeoff": "The preferred specialist was disabled by the operator.",
                },
            ),
        ),
    )

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.accepted
    assert decision.units[0].disabled_shadows[0].agent_id == "ideal-analyst"


def test_unavailable_shadow_reason_must_match_deterministic_eligibility() -> None:
    roster = (
        _contract("linux-analyst", outcomes=("Technical analysis",), platforms=("linux",)),
        _contract("fallback-analyst", outcomes=("Technical analysis",)),
    )
    plan = _plan(_unit("unit-analysis"))
    row = _row(
        plan.units[0],
        roster,
        semantic=("linux-analyst", "fallback-analyst"),
        executable=("fallback-analyst",),
        selected=("fallback-analyst",),
        forbidden=("linux-analyst",),
        unavailable_shadows=(
            {
                "agent_id": "linux-analyst",
                "rank": 1,
                "reason_codes": ["agent-host-unsupported"],
                "fallback_agent_id": "fallback-analyst",
                "tradeoff": "The preferred specialist is unavailable on Windows.",
            },
        ),
    )
    proposal = _proposal(plan, roster, row)

    assert "unavailable_shadow_mismatch" in _codes(
        verify_staffing(plan, proposal, roster, context=_context())
    )


def test_complementary_specialists_use_distinct_contexts_and_cannot_conflict() -> None:
    roster = (
        _contract(
            "alpha-specialist",
            outcomes=("Alpha",),
            composition=CompositionContract(
                same_context_conflicts=("beta-specialist",),
                independence_class="alpha",
            ),
        ),
        _contract("beta-specialist", outcomes=("Beta",)),
    )
    plan = _plan(_unit("unit-combined", capabilities=("alpha", "beta")))
    row = _row(
        plan.units[0],
        roster,
        semantic=("alpha-specialist", "beta-specialist"),
        executable=("alpha-specialist", "beta-specialist"),
        selected=("alpha-specialist", "beta-specialist"),
        context_id="ctx-shared",
    )
    proposal = _proposal(plan, roster, row)

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert {"delegated_context_not_distinct", "same_context_conflict"} <= _codes(decision)


def test_complementary_specialists_can_jointly_cover_multiple_domains() -> None:
    roster = (
        _contract(
            "security-specialist",
            outcomes=("Security review",),
            domains=("security",),
        ),
        _contract(
            "quality-specialist",
            outcomes=("Quality verification",),
            domains=("quality-assurance",),
        ),
    )
    raw_unit = _unit(
        "unit-cross-domain",
        capabilities=("security-review", "quality-verification"),
    )
    raw_unit["domains"] = ["security", "quality-assurance"]
    plan = _plan(raw_unit)

    proposal = build_deterministic_proposal(
        plan,
        roster,
        {
            "unit-cross-domain": (
                ("security-specialist", 0.98),
                ("quality-specialist", 0.95),
            )
        },
        context=_context(),
    )
    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.accepted
    assert decision.units[0].selected == (
        "security-specialist",
        "quality-specialist",
    )


def test_broad_planning_capabilities_use_typed_authority_and_lifecycle() -> None:
    reviewer = _contract(
        "code-reviewer",
        outcomes=("Code quality findings",),
        artifact="review-report",
        lifecycle="review",
        authority="review",
    )
    raw_unit = _unit(
        "unit-review",
        artifact="review-report",
        lifecycle="review",
        capabilities=("audit", "investigation", "review", "verification"),
        authority="review",
    )
    plan = _plan(raw_unit)

    proposal = build_deterministic_proposal(
        plan,
        (reviewer,),
        {"unit-review": (("code-reviewer", 0.98),)},
        context=_context(),
    )

    assert verify_staffing(plan, proposal, (reviewer,), context=_context()).accepted


def test_subject_matter_reviewer_can_complement_test_evidence_owner() -> None:
    evidence_owner = _contract(
        "application-integration-verifier",
        outcomes=("Application test verification",),
        artifact="test-evidence",
        lifecycle="testing",
        authority="review",
        domains=("quality-assurance",),
    )
    security_reviewer = _contract(
        "code-reviewer",
        outcomes=("Security review",),
        artifact="review-report",
        lifecycle="review",
        authority="review",
        domains=("security", "software-engineering"),
    )
    raw_unit = _unit(
        "unit-security-tests",
        artifact="test-evidence",
        lifecycle="testing",
        capabilities=("testing", "verification", "review"),
        authority="review",
    )
    raw_unit["domains"] = ["security", "software-engineering", "quality-assurance"]
    plan = _plan(raw_unit)
    roster = (evidence_owner, security_reviewer)

    proposal = build_deterministic_proposal(
        plan,
        roster,
        {
            "unit-security-tests": (
                ("application-integration-verifier", 0.98),
                ("code-reviewer", 0.95),
            )
        },
        context=_context(),
    )
    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.accepted
    assert decision.units[0].selected == (
        "application-integration-verifier",
        "code-reviewer",
    )


def test_selection_exclusive_contract_is_enforced() -> None:
    roster = (
        _contract(
            "alpha",
            outcomes=("Alpha",),
            composition=CompositionContract(selection_exclusive=("beta",)),
        ),
        _contract("beta", outcomes=("Beta",)),
    )
    plan = _plan(_unit("unit-combined", capabilities=("alpha", "beta")))
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("alpha", "beta"),
            executable=("alpha", "beta"),
            selected=("alpha", "beta"),
        ),
    )

    assert "selection_exclusive_conflict" in _codes(
        verify_staffing(plan, proposal, roster, context=_context())
    )


def test_redundant_nonminimal_team_and_low_confidence_fail_atomically() -> None:
    roster = (
        _contract("first-analyst", outcomes=("Technical analysis",)),
        _contract("second-analyst", outcomes=("Technical analysis",)),
    )
    plan = _plan(_unit("unit-analysis"))
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("first-analyst", "second-analyst"),
            executable=("first-analyst", "second-analyst"),
            selected=("first-analyst", "second-analyst"),
            confidence=0.2,
            margin=0.01,
        ),
    )

    decision = verify_staffing(
        plan,
        proposal,
        roster,
        context=_context(),
        budget=StaffingBudget(max_selected_per_unit=1, max_selected_total=1),
    )

    assert {
        "selected_not_deterministic_minimum",
        "unit_agent_budget_exceeded",
        "selection_confidence_too_low",
        "selection_margin_too_low",
    } <= _codes(decision)
    assert decision.units == ()


def test_mutation_or_durable_claim_without_later_assurance_abstains() -> None:
    roster = (
        _contract(
            "python-engineer",
            outcomes=("Python packaging implementation",),
            artifact="implementation-change",
            lifecycle="implementation",
            authority="modify",
            stacks=("python",),
        ),
    )
    plan = _plan(
        _unit(
            "unit-implement",
            artifact="implementation-change",
            lifecycle="implementation",
            capabilities=("python-packaging",),
            authority="modify",
            mutation="workspace_write",
            languages=("python",),
            claims=("production-ready",),
        )
    )
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("python-engineer",),
            executable=("python-engineer",),
            selected=("python-engineer",),
        ),
    )

    assert "independent_assurance_missing" in _codes(
        verify_staffing(plan, proposal, roster, context=_context())
    )
    assert verify_staffing(
        plan,
        proposal,
        roster,
        context=_context(),
        explicit_indivisible_unit=True,
    ).accepted


def test_terminal_review_claim_is_itself_assurance_not_recursive_work() -> None:
    roster = (
        _contract(
            "reviewer",
            outcomes=("Evidence review",),
            artifact="review-report",
            lifecycle="review",
            authority="review",
        ),
    )
    plan = _plan(
        _unit(
            "unit-review",
            artifact="review-report",
            lifecycle="review",
            capabilities=("review",),
            authority="review",
            claims=("evidence-backed-findings",),
        )
    )
    proposal = _proposal(
        plan,
        roster,
        _row(
            plan.units[0],
            roster,
            semantic=("reviewer",),
            executable=("reviewer",),
            selected=("reviewer",),
        ),
    )

    assert "independent_assurance_missing" not in _codes(
        verify_staffing(plan, proposal, roster, context=_context())
    )


def test_explicit_recruiter_abstention_is_preserved() -> None:
    roster: tuple[WorkforceContract, ...] = ()
    plan = _plan(_unit("unit-analysis"))
    row = _row(plan.units[0], roster, semantic=(), executable=(), selected=())
    proposal = _proposal(plan, roster, row)

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.status == "abstained"
    assert {"no_safe_sufficient_team", "recruiter_abstained"} <= _codes(decision)


def test_named_regulated_assurance_requires_explicit_contract_coverage() -> None:
    generic = _contract(
        "code-reviewer",
        outcomes=("Independent source review",),
        artifact="review-report",
        lifecycle="review",
        authority="review",
    )
    plan = _plan(
        _unit(
            "unit-regulated-review",
            artifact="review-report",
            lifecycle="review",
            capabilities=("review", "regulated-assurance-do-178c"),
            authority="review",
        )
    )
    generic_proposal = build_deterministic_proposal(
        plan,
        (generic,),
        {"unit-regulated-review": (("code-reviewer", 0.99),)},
        context=_context(),
    )

    generic_decision = verify_staffing(
        plan,
        generic_proposal,
        (generic,),
        context=_context(),
    )

    assert generic_decision.status == "abstained"
    assert {"no_safe_sufficient_team", "recruiter_abstained"} <= _codes(generic_decision)

    qualified = replace(
        generic,
        worker_id="worker:do-178c-assurance-reviewer",
        agent_id="do-178c-assurance-reviewer",
        display_name="DO-178C Assurance Reviewer",
        capability_ids=("review", "regulated-assurance-do-178c"),
    )
    qualified_proposal = build_deterministic_proposal(
        plan,
        (qualified,),
        {"unit-regulated-review": (("do-178c-assurance-reviewer", 0.99),)},
        context=_context(),
    )

    qualified_decision = verify_staffing(
        plan,
        qualified_proposal,
        (qualified,),
        context=_context(),
    )

    assert qualified_decision.accepted
    assert qualified_decision.units[0].selected == ("do-178c-assurance-reviewer",)


def test_deterministic_proposal_builder_preserves_disabled_winner_visibility() -> None:
    roster = (
        _contract("disabled-analyst", outcomes=("Technical analysis",), enabled=False),
        _contract("enabled-analyst", outcomes=("Technical analysis",)),
    )
    plan = _plan(_unit("unit-analysis"))
    proposal = build_deterministic_proposal(
        plan,
        roster,
        {"unit-analysis": (("disabled-analyst", 0.99), ("enabled-analyst", 0.9))},
        context=_context(),
    )

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.accepted
    assert decision.units[0].selected == ("enabled-analyst",)
    assert decision.units[0].disabled_shadows[0].agent_id == "disabled-analyst"
    assert decision.units[0].disabled_shadows[0].fallback_agent_id == "enabled-analyst"


def test_deterministic_proposal_builder_cannot_bypass_confidence_or_margin_policy() -> None:
    roster = (
        _contract("first-analyst", outcomes=("Technical analysis",)),
        _contract("second-analyst", outcomes=("Technical analysis",)),
    )
    plan = _plan(_unit("unit-analysis"))
    proposal = build_deterministic_proposal(
        plan,
        roster,
        {"unit-analysis": (("first-analyst", 0.7), ("second-analyst", 0.69))},
        context=_context(),
    )

    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert not decision.accepted
    assert {"selection_confidence_too_low", "selection_margin_too_low"} <= _codes(decision)


def test_margin_compares_complete_alternative_teams_not_partial_near_neighbors() -> None:
    unit = _unit("unit-analysis")
    unit["domains"] = ["security", "software-engineering"]
    plan = _plan(unit)
    complete = _contract("complete-reviewer", outcomes=("Technical analysis",))
    partial = replace(
        _contract("partial-neighbor", outcomes=("Technical analysis",)),
        domains=("security",),
    )
    complete = replace(
        complete,
        domains=("security", "software-engineering"),
    )
    context = _context()

    proposal = build_deterministic_proposal(
        plan,
        (partial, complete),
        {plan.units[0].unit_id: (("partial-neighbor", 1.0), ("complete-reviewer", 0.9))},
        context=context,
    )
    decision = verify_staffing(plan, proposal, (partial, complete), context=context)

    assert proposal.units[0].selected == ("complete-reviewer",)
    assert proposal.units[0].margin == 0.9
    assert decision.accepted
