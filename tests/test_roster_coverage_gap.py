"""ADR-0198 / AR-384: the roster's unserved typed requirements are waived, not fatal.

The planner draws its tokens from the roster vocabulary, not from what the
roster can cover for one unit's authority and host. On the 2026-09-03 install
smoke the only contract declaring ``domain:desktop`` carried modify authority,
so every plan unit naming that domain was provably unstaffable before the
recruiter spoke, and the conjunctive sufficiency rule rejected each honest
``staff`` answer. These tests pin the replacement contract: a token some
enabled contract declares but none covers eligibly is waived from team
sufficiency and recorded as ``roster_coverage_gap``; a token no contract
declares stays mandatory, because that is a real gap for hiring; a token some
eligible contract covers stays mandatory, because omitting an available
complement is the ranking's fault.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.selector.pipeline import _hireable_gap_units
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import (
    _NominationValidationError,
    _typed_shortlists,
    _valid_inferred_gap_proposal,
    _validate_nomination_decisions,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import (
    ADVISORY_STAFFING_CODES,
    ROSTER_COVERAGE_GAP,
    AbstentionReason,
    RosterCoverageGaps,
    StaffingContext,
    build_deterministic_proposal,
    typed_staffing_coverage,
    typed_staffing_coverage_gaps,
    verify_staffing,
)

_HASH = "sha256:" + "a" * 64
_GENERATION = 7
_UNIT = "unit-install-operation"


def _contract(
    agent_id: str,
    *,
    artifact: str = "plan",
    lifecycle: str = "planning",
    authority: str = "plan",
    domains: tuple[str, ...] = ("operations",),
    capabilities: tuple[str, ...] = ("analysis", "planning", "review"),
    enabled: bool = True,
) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="planner" if authority == "plan" else "implementer",
        outcomes=(f"{agent_id} outcome",),
        capability_ids=capabilities,
        artifact_kinds=(artifact,),
        lifecycle_phases=(lifecycle,),
        domains=domains,
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority=authority,
        context_mode="isolated_only",
        tool_classes=("repository-read",),
        hosts=("codex", "claude", "openclaw", "hermes"),
        platforms=("windows", "linux"),
        composition=CompositionContract(independence_class=agent_id),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=enabled,
        employment="employee" if enabled else "disabled",
        origin="upstream",
    )


def _operations_manager() -> WorkforceContract:
    return _contract("operations-manager")


def _desktop_engineer(*, enabled: bool = True) -> WorkforceContract:
    # The captured shape: the only desktop contract is a modify-authority
    # implementer, ineligible for a plan unit on authority and capability.
    return _contract(
        "desktop-app-engineer",
        artifact="implementation-change",
        lifecycle="implementation",
        authority="modify",
        domains=("software-engineering", "desktop"),
        capabilities=("analysis", "implementation", "testing"),
        enabled=enabled,
    )


def _qa_planner() -> WorkforceContract:
    return _contract("qa-planner", domains=("quality-assurance", "operations"))


def _plan(
    *,
    domains: tuple[str, ...] = ("desktop", "operations"),
    capabilities: tuple[str, ...] = ("planning", "operations"),
):
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Install the editor on the machine.",
            "units": [
                {
                    "unit_id": _UNIT,
                    "outcome": "Install the editor using the selected supported method.",
                    "artifact_kind": "plan",
                    "lifecycle_phase": "planning",
                    "domains": list(domains),
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": list(capabilities),
                    "authority": "plan",
                    "mutation_scope": "read_only",
                    "risks": [],
                    "trust_boundaries": ["repository"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["repository"],
                    "required_tools": ["repository-read"],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["The command path and version are recorded."],
                    "parallelization": "sequential",
                }
            ],
        }
    )


def _context() -> StaffingContext:
    return StaffingContext(
        "codex",
        "linux",
        frozenset({"native-delegation", "repository-read", "shell-execution"}),
        _GENERATION,
    )


def _codes(decision) -> set[str]:
    return {item.code for item in decision.abstention_reasons}


def test_unserved_domain_is_waived_and_recorded_on_the_accepted_decision() -> None:
    plan = _plan()
    roster = (_operations_manager(), _desktop_engineer())

    gaps = typed_staffing_coverage_gaps(plan.units[0], roster, _context())

    assert gaps == RosterCoverageGaps(uncovered=("domain:desktop",), waived=("domain:desktop",))
    assert gaps.unknown == ()

    proposal = build_deterministic_proposal(
        plan,
        roster,
        {_UNIT: (("operations-manager", 0.84), ("desktop-app-engineer", 0.55))},
        context=_context(),
        semantic_required={_UNIT: frozenset({"operations-manager"})},
        semantic_acceptable={_UNIT: frozenset({"desktop-app-engineer"})},
        semantic_forbidden={_UNIT: frozenset()},
    )
    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert proposal.units[0].selected == ("operations-manager",)
    assert decision.accepted
    assert decision.units[0].selected == ("operations-manager",)
    # The gap rides on the accepted decision with the exact token, so the
    # receipt says which requirement the roster could not serve.
    assert decision.abstention_reasons == (
        AbstentionReason(ROSTER_COVERAGE_GAP, _UNIT, "", "domain:desktop"),
    )
    assert ROSTER_COVERAGE_GAP in ADVISORY_STAFFING_CODES


def test_a_token_no_contract_declares_stays_mandatory() -> None:
    # `simulation` is a core planner capability no fixture contract supports,
    # so the unit names a specialty the roster does not have at all. That is a
    # hiring gap, not a coverage gap to wave through.
    plan = _plan(capabilities=("planning", "simulation"))
    roster = (_operations_manager(), _desktop_engineer())

    gaps = typed_staffing_coverage_gaps(plan.units[0], roster, _context())

    assert gaps.uncovered == ("domain:desktop", "capability:simulation")
    assert gaps.waived == ("domain:desktop",)
    assert gaps.unknown == ("capability:simulation",)

    proposal = build_deterministic_proposal(
        plan,
        roster,
        {_UNIT: (("operations-manager", 0.84),)},
        context=_context(),
        semantic_required={_UNIT: frozenset({"operations-manager"})},
        semantic_acceptable={_UNIT: frozenset()},
        semantic_forbidden={_UNIT: frozenset()},
    )
    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert proposal.units[0].selected == ()
    assert proposal.units[0].abstention_reasons == ("no-safe-deterministic-team",)
    assert decision.status == "abstained"
    assert {"no_safe_sufficient_team", ROSTER_COVERAGE_GAP} <= _codes(decision)


def test_a_coverable_token_still_needs_its_complement() -> None:
    # quality-assurance is served eligibly by qa-planner, so it stays in the
    # sufficiency proof: the minimum team pulls the complement in, and a
    # ranking that forbids it has no safe team even though desktop is waived.
    plan = _plan(domains=("desktop", "operations", "quality-assurance"))
    roster = (_operations_manager(), _qa_planner(), _desktop_engineer())
    ranking = {
        _UNIT: (
            ("operations-manager", 0.9),
            ("qa-planner", 0.85),
            ("desktop-app-engineer", 0.55),
        )
    }

    assert typed_staffing_coverage_gaps(plan.units[0], roster, _context()).waived == (
        "domain:desktop",
    )

    complemented = build_deterministic_proposal(
        plan,
        roster,
        ranking,
        context=_context(),
        semantic_required={_UNIT: frozenset({"operations-manager"})},
        semantic_acceptable={_UNIT: frozenset({"qa-planner", "desktop-app-engineer"})},
        semantic_forbidden={_UNIT: frozenset()},
    )
    assert complemented.units[0].selected == ("operations-manager", "qa-planner")
    assert verify_staffing(plan, complemented, roster, context=_context()).accepted

    forbidding = build_deterministic_proposal(
        plan,
        roster,
        ranking,
        context=_context(),
        semantic_required={_UNIT: frozenset({"operations-manager"})},
        semantic_acceptable={_UNIT: frozenset({"desktop-app-engineer"})},
        semantic_forbidden={_UNIT: frozenset({"qa-planner"})},
    )
    decision = verify_staffing(plan, forbidding, roster, context=_context())

    assert forbidding.units[0].selected == ()
    assert decision.status == "abstained"
    assert {"no_safe_sufficient_team", ROSTER_COVERAGE_GAP} <= _codes(decision)


def test_coverage_gaps_count_only_enabled_typed_contracts_under_eligibility() -> None:
    plan = _plan()
    unit = plan.units[0]
    manager = _operations_manager()
    wildcard = replace(
        _contract("untyped-generalist", domains=()),
        artifact_kinds=(),
        lifecycle_phases=(),
        stacks=(),
    )

    # A disabled declarer does not make the token served-but-unserved: the
    # recall block never shows disabled workers, so the verifier agrees.
    disabled = typed_staffing_coverage_gaps(
        unit, (manager, _desktop_engineer(enabled=False)), _context()
    )
    assert disabled.uncovered == ("domain:desktop",)
    assert disabled.waived == ()

    # Wildcard coverage is not positive evidence, so it neither covers nor
    # declares anything here.
    assert typed_staffing_coverage_gaps(unit, (manager, wildcard), _context()).unknown == (
        "domain:desktop",
    )

    # Without a context nothing is judged ineligible, so nothing is waived and
    # the uncovered set is exactly what no enabled typed contract declares.
    no_context = typed_staffing_coverage_gaps(unit, (manager, _desktop_engineer()), None)
    assert no_context == RosterCoverageGaps(uncovered=(), waived=())


def test_typed_recall_shows_the_same_waived_tokens_the_verifier_waives() -> None:
    plan = _plan()
    roster = (_operations_manager(), _desktop_engineer())

    recall = _typed_shortlists(plan, roster, context=_context())

    assert recall[0]["uncovered_requirements"] == ["domain:desktop"]
    assert recall[0]["waived_requirements"] == ["domain:desktop"]
    assert recall[0]["waived_requirements"] == sorted(
        typed_staffing_coverage_gaps(plan.units[0], roster, _context()).waived
    )


def test_operations_capability_reads_the_operations_domain() -> None:
    unit = _plan().units[0]
    manager = _operations_manager()
    elsewhere = _contract("product-planner", domains=("software-engineering",))

    assert "capability:operations" in typed_staffing_coverage(unit, manager)
    assert "capability:operations" not in typed_staffing_coverage(unit, elsewhere)


def test_repair_contract_names_only_the_coverable_axis() -> None:
    plan = _plan(domains=("desktop", "operations", "quality-assurance"))
    roster = (_operations_manager(), _qa_planner(), _desktop_engineer())
    ranking = {
        _UNIT: (
            ("operations-manager", 0.9),
            ("qa-planner", 0.85),
            ("desktop-app-engineer", 0.55),
        )
    }
    proposal = build_deterministic_proposal(
        plan,
        roster,
        ranking,
        context=_context(),
        semantic_required={_UNIT: frozenset({"operations-manager"})},
        semantic_acceptable={_UNIT: frozenset({"desktop-app-engineer"})},
        semantic_forbidden={_UNIT: frozenset({"qa-planner"})},
    )

    with pytest.raises(_NominationValidationError) as raised:
        _validate_nomination_decisions(
            plan,
            proposal,
            {_UNIT: "staff"},
            roster,
            ranking,
            _context(),
            semantic_forbidden={_UNIT: ("qa-planner",)},
        )

    failure = raised.value.failures[0]
    assert (failure.code, failure.axis) == ("staff_without_safe_team", "domain")
    repair = failure.repair_contract.as_prompt_dict()
    # The waived token is named separately and never listed as something the
    # repair must cover; the coverable domain is the only ask.
    assert repair["roster_uncovered_requirement_ids"] == ["domain:desktop"]
    assert repair["uncovered_requirement_ids"] == ["domain:quality-assurance"]
    assert repair["uncovered_after_required_ids"] == ["domain:quality-assurance"]


def test_declared_gap_on_an_unserved_unit_stays_hireable() -> None:
    plan = _plan()
    roster = (_operations_manager(), _desktop_engineer())
    proposal = build_deterministic_proposal(
        plan,
        roster,
        {_UNIT: ()},
        context=_context(),
        semantic_gap_units=frozenset({_UNIT}),
    )
    decision = verify_staffing(plan, proposal, roster, context=_context())

    assert decision.status == "abstained"
    assert _codes(decision) == {
        "no_safe_sufficient_team",
        "recruiter_abstained",
        ROSTER_COVERAGE_GAP,
    }
    # The advisory gap is the honest reason the gap is real; it must not read
    # as verifier dirt that keeps the unit away from hiring.
    assert _valid_inferred_gap_proposal(proposal, decision)
    outcome = SimpleNamespace(plan=plan, proposal=proposal, staffing=decision)
    assert _hireable_gap_units(outcome) == (_UNIT,)


def _snapshot(*contracts: WorkforceContract) -> WorkforceIndexSnapshot:
    records = tuple(project_recruiter_index_record(item) for item in contracts)
    return WorkforceIndexSnapshot(
        generation=_GENERATION,
        worker_count=len(contracts),
        contracts=contracts,
        contract_fingerprint=workforce_index_fingerprint(contracts),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )


def _result(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="gpt-5.6-mini",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def _nominee(agent_id: str, score: float, classification: str) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "score": score,
        "classification": classification,
        "positive_evidence": ["operations-planning-coverage"],
        "negative_evidence": [],
    }


def test_staff_decision_survives_an_unserved_requirement_end_to_end() -> None:
    # The captured 2026-09-03 helix turn: the recruiter staffs the operations
    # manager with the desktop implementer as an acceptable cousin. Before
    # ADR-0198 the runtime rejected it as staff_without_safe_team on the
    # domain axis and the turn died at the repair; now it is accepted first
    # time and the receipt names the unserved domain.
    snapshot = _snapshot(_operations_manager(), _desktop_engineer())
    plan = {
        "request_summary": "Install the editor on the machine.",
        "units": [
            {
                "unit_id": _UNIT,
                "outcome": "Install the editor using the selected supported method.",
                "artifact_kind": "plan",
                "domains": ["desktop", "operations"],
                "stacks": [],
                "capability_ids": ["planning", "operations"],
                "novel_capability": "",
                "depends_on": [],
            }
        ],
    }
    nomination = {
        "units": [
            {
                "unit_id": _UNIT,
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("operations-manager", 0.84, "required"),
                    _nominee("desktop-app-engineer", 0.55, "acceptable"),
                ],
            }
        ]
    }
    responses = iter((_result(plan), _result(nomination)))
    prompts: list[str] = []

    def invoke(*args, **_kwargs):
        prompts.append(args[1])
        return next(responses)

    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="task-agency-router",
                type="litellm",
                model="router-alias",
                base_url="https://router.example.test/v1",
                api_key="secret",
                timeout=5,
            ),
        ),
        workforce=WorkforceConfig(mode="balanced", balanced_call_budget=3),
    )
    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        snapshot,
        config=config,
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert [attempt.status for attempt in outcome.attempts] == ["applied", "applied"]
    assert outcome.staffing.units[0].selected == ("operations-manager",)
    assert outcome.staffing.abstention_reasons == (
        AbstentionReason(ROSTER_COVERAGE_GAP, _UNIT, "", "domain:desktop"),
    )
    recall = json.loads(prompts[1])["typed_recall"][0]
    assert recall["uncovered_requirements"] == ["domain:desktop"]
    assert recall["waived_requirements"] == ["domain:desktop"]


def test_routing_receipt_names_the_waived_token_and_drops_prose() -> None:
    from agency_runtime.core.selector.receipt_projection import (
        normalize_durable_routing_receipt,
        project_durable_routing_receipt,
    )

    secret = "the operator's password is hunter2"
    routing = {
        "trace_id": "trace-coverage-gap",
        "query_hash": "a" * 64,
        "context_fingerprint": "c" * 64,
        "selected_ids": ["operations-manager"],
        "semantic_ids": ["operations-manager"],
        "confidence": 0.84,
        "top_score": 0.84,
        "latency_ms": 17,
        "candidate_count": 2,
        "status": "accepted",
        "source": "inference",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": "inferred",
        "provider_attempts": [],
        "workforce_proposal": {
            "units": [
                {
                    "unit_id": _UNIT,
                    "required": ["operations-manager"],
                    "acceptable": ["desktop-app-engineer"],
                    "selected": ["operations-manager"],
                    "abstention_reasons": [],
                }
            ]
        },
        "workforce_staffing": {
            "status": "accepted",
            "units": [],
            "abstention_reasons": [
                {"code": ROSTER_COVERAGE_GAP, "unit_id": _UNIT, "detail": "domain:desktop"},
                {"code": ROSTER_COVERAGE_GAP, "unit_id": _UNIT, "detail": secret},
                {"code": ROSTER_COVERAGE_GAP, "unit_id": _UNIT, "detail": "vibes:desktop"},
                {"code": "independent_assurance_missing", "unit_id": _UNIT, "detail": secret},
            ],
        },
    }

    receipt = project_durable_routing_receipt(routing)

    unit = receipt["staffing"]["units"][0]
    assert unit["reason_codes"] == [ROSTER_COVERAGE_GAP, "independent_assurance_missing"]
    # Only the axis-prefixed roster token survives; prose and an unknown axis
    # fail closed to omission rather than to an opaque value.
    assert unit["coverage_gaps"] == ["domain:desktop"]
    assert secret not in json.dumps(receipt)
    assert normalize_durable_routing_receipt(receipt) == receipt
