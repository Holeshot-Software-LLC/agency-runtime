"""AR-387 / ADR-0203: the recruiter sees the complete eligible card set per unit.

The detail cards are the union of every unit's bounded recall rows, so a card
can be present for one unit and ineligible for another without any row saying
so. Live on 2026-09-03 the recruiter ranked three modify-authority implementers
as required on a plan-authority install unit for exactly that reason (they
carried cards through the implementation unit's rows and no eligibility flag
for the plan unit), left the eligible planners in the rows unranked, and the
turn died twice on ``staff_without_safe_team``. These tests pin the
replacement contract: every recall row carries ``eligible_candidate_ids``, the
verifier's own eligibility over the cards, complete and identity-sorted, with
``eligible_candidates_without_card`` for the eligible workers the bounded
recall did not card; the safe-team repair contract names the eligible cards
covering each requirement the ranked team left uncovered; and both prompts say
that a card outside the list can be forbidden or omitted but never staffed.
"""

from __future__ import annotations

import json
from typing import Any

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import (
    _NOMINATION_REPAIR_REQUIREMENTS,
    _RECRUITER_REPAIR_SYSTEM,
    _RECRUITER_SYSTEM,
    MAX_ELIGIBLE_COVERERS_PER_REQUIREMENT,
    _annotate_eligible_candidates,
    _eligible_coverers_by_requirement,
    _typed_shortlists,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import StaffingContext

_HASH = "sha256:" + "a" * 64
_GENERATION = 7
_PLAN_UNIT = "unit-install-plan"
_IMPL_UNIT = "unit-install-execution"
_TOOLS = frozenset(
    {"code-execution", "repository-read", "repository-write", "shell-execution", "test-execution"}
)


def _contract(
    agent_id: str,
    *,
    artifacts: tuple[str, ...] = ("plan", "analysis", "review-report"),
    lifecycles: tuple[str, ...] = ("discovery", "planning", "review"),
    authority: str = "plan",
    domains: tuple[str, ...] = ("specialist-services", "operations"),
    capabilities: tuple[str, ...] = ("analysis", "planning", "review"),
    platforms: tuple[str, ...] = ("windows", "linux"),
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
        artifact_kinds=artifacts,
        lifecycle_phases=lifecycles,
        domains=domains,
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority=authority,
        context_mode="isolated_only",
        tool_classes=("repository-read",),
        hosts=("codex", "claude", "openclaw", "hermes"),
        platforms=platforms,
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


def _sre() -> WorkforceContract:
    # Plan authority, declaring both domains the captured install plan named.
    return _contract(
        "sre-site-reliability-engineer", domains=("software-engineering", "operations")
    )


def _desktop_engineer() -> WorkforceContract:
    return _contract(
        "desktop-app-engineer",
        artifacts=("implementation-change", "analysis"),
        lifecycles=("discovery", "implementation", "testing"),
        authority="modify",
        domains=("software-engineering", "desktop"),
        capabilities=("analysis", "implementation", "testing"),
    )


def _windows_planner() -> WorkforceContract:
    return _contract(
        "windows-only-planner", domains=("software-engineering",), platforms=("windows",)
    )


def _roster() -> tuple[WorkforceContract, ...]:
    return (_operations_manager(), _sre(), _desktop_engineer(), _windows_planner())


def _context() -> StaffingContext:
    return StaffingContext("codex", "linux", _TOOLS, _GENERATION)


def _typed_plan(domains: tuple[str, ...] = ("operations", "software-engineering")):
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Install the editor on the machine.",
            "units": [
                {
                    "unit_id": _PLAN_UNIT,
                    "outcome": "Plan the editor installation using the supported method.",
                    "artifact_kind": "plan",
                    "lifecycle_phase": "planning",
                    "domains": list(domains),
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["planning"],
                    "authority": "plan",
                    "mutation_scope": "read_only",
                    "risks": [],
                    "trust_boundaries": ["repository"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["repository"],
                    "required_tools": ["repository-read"],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["The install plan names the supported method."],
                    "parallelization": "sequential",
                },
                {
                    "unit_id": _IMPL_UNIT,
                    "outcome": "Install the editor as planned.",
                    "artifact_kind": "implementation-change",
                    "lifecycle_phase": "implementation",
                    "domains": ["software-engineering", "desktop"],
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["implementation"],
                    "authority": "modify",
                    "mutation_scope": "workspace_write",
                    "risks": ["regression"],
                    "trust_boundaries": ["repository"],
                    "claims": ["implementation-complete"],
                    "depends_on": [_PLAN_UNIT],
                    "resources": ["repository"],
                    "required_tools": ["repository-read", "repository-write", "code-execution"],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["The editor starts."],
                    "parallelization": "sequential",
                },
            ],
        }
    )


def test_every_recall_row_carries_the_complete_eligible_card_set() -> None:
    plan = _typed_plan()
    roster = _roster()
    recall = _typed_shortlists(plan, roster, context=_context())
    # The desktop card exists only because the implementation unit recalled it;
    # the windows-only planner is a card nobody can staff on linux.
    cards = frozenset(c.agent_id for c in roster)

    _annotate_eligible_candidates(plan, recall, roster, _context(), cards)

    by_unit = {row["unit_id"]: row for row in recall}
    assert by_unit[_PLAN_UNIT]["eligible_candidate_ids"] == [
        "operations-manager",
        "sre-site-reliability-engineer",
    ]
    assert by_unit[_PLAN_UNIT]["eligible_candidates_without_card"] == 0
    assert by_unit[_IMPL_UNIT]["eligible_candidate_ids"] == ["desktop-app-engineer"]
    # An eligible worker with no card is counted, not listed.
    _annotate_eligible_candidates(
        plan, recall, roster, _context(), frozenset({"operations-manager"})
    )
    assert by_unit[_PLAN_UNIT]["eligible_candidate_ids"] == ["operations-manager"]
    assert by_unit[_PLAN_UNIT]["eligible_candidates_without_card"] == 1


def test_eligible_coverers_are_facts_not_a_ranking() -> None:
    unit = _typed_plan().units[0]
    roster = _roster()

    coverers = _eligible_coverers_by_requirement(
        unit, ("domain:software-engineering", "domain:operations"), roster, _context(), None
    )

    # Identity-sorted, eligible only: the modify implementer and the windows
    # planner both declare software-engineering and neither is listed.
    assert coverers == (
        ("domain:software-engineering", ("sre-site-reliability-engineer",)),
        ("domain:operations", ("operations-manager", "sre-site-reliability-engineer")),
    )
    # Restricted to the cards the recruiter may rank.
    assert _eligible_coverers_by_requirement(
        unit, ("domain:operations",), roster, _context(), frozenset({"operations-manager"})
    ) == (("domain:operations", ("operations-manager",)),)
    # Nothing is named without a context or without requirements.
    assert _eligible_coverers_by_requirement(unit, ("domain:operations",), roster, None, None) == ()
    assert _eligible_coverers_by_requirement(unit, (), roster, _context(), None) == ()
    # Bounded.
    many = tuple(_contract(f"planner-{index:02d}") for index in range(12))
    (row,) = _eligible_coverers_by_requirement(unit, ("domain:operations",), many, _context(), None)
    assert len(row[1]) == MAX_ELIGIBLE_COVERERS_PER_REQUIREMENT
    assert row[1] == tuple(sorted(row[1]))


def test_both_prompts_state_the_eligibility_boundary() -> None:
    assert "eligible_candidate_ids" in _RECRUITER_SYSTEM
    assert "can only be forbidden or omitted" in _RECRUITER_SYSTEM
    assert "eligible_candidate_ids" in _RECRUITER_REPAIR_SYSTEM
    assert "eligible_coverers_by_requirement" in _RECRUITER_REPAIR_SYSTEM
    assert "can only be forbidden or omitted" in _RECRUITER_REPAIR_SYSTEM
    assert "never staffed" in _RECRUITER_REPAIR_SYSTEM
    assert (
        "eligible_coverers_by_requirement"
        in _NOMINATION_REPAIR_REQUIREMENTS["staff_without_safe_team"]
    )
    assert (
        "neither required nor acceptable"
        in _NOMINATION_REPAIR_REQUIREMENTS["staff_without_safe_team"]
    )


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
        actual_model="minimax-m3",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def _row(agent_id: str, classification: str, score: float) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "score": score,
        "classification": classification,
        "positive_evidence": ["install-scope-fit"] if classification != "forbidden" else [],
        "negative_evidence": [] if classification != "forbidden" else ["wrong-authority"],
    }


def _nomination(plan_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "units": [
            {"unit_id": _PLAN_UNIT, "decision": "staff", "ranked_semantic": plan_rows},
            {
                "unit_id": _IMPL_UNIT,
                "decision": "staff",
                "ranked_semantic": [_row("desktop-app-engineer", "required", 0.9)],
            },
        ]
    }


def test_the_captured_blindness_is_repaired_with_the_eligible_coverer_named() -> None:
    # Turn 201 on the ADR-0201 run: the recruiter required a modify-authority
    # implementer on the plan unit and ranked operations-manager as an
    # acceptable, which covers operations but not software-engineering; the
    # eligible planner declaring both domains sat unranked.
    plan_document = {
        "request_summary": "Install the editor on the machine.",
        "units": [
            {
                "unit_id": _PLAN_UNIT,
                "outcome": "Plan the editor installation using the supported method.",
                "artifact_kind": "plan",
                "domains": ["operations", "software-engineering"],
                "stacks": [],
                "capability_ids": ["planning"],
                "novel_capability": "",
                "depends_on": [],
            },
            {
                "unit_id": _IMPL_UNIT,
                "outcome": "Install the editor as planned.",
                "artifact_kind": "implementation-change",
                "domains": ["software-engineering", "desktop"],
                "stacks": [],
                "capability_ids": ["implementation"],
                "novel_capability": "",
                "depends_on": [_PLAN_UNIT],
            },
        ],
    }
    blind = _nomination(
        [
            _row("desktop-app-engineer", "required", 0.88),
            _row("operations-manager", "acceptable", 0.6),
        ]
    )
    # A repair answers only for the failed unit; the implementation row is kept.
    repaired = {
        "units": [
            {
                "unit_id": _PLAN_UNIT,
                "decision": "staff",
                "ranked_semantic": [
                    _row("sre-site-reliability-engineer", "required", 0.86),
                    _row("operations-manager", "acceptable", 0.7),
                ],
            }
        ]
    }
    responses = iter((_result(plan_document), _result(blind), _result(repaired)))
    prompts: list[str] = []

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(prompt)
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
        "Install the editor on this machine and then run it.",
        _snapshot(*_roster()),
        config=config,
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert [attempt.status for attempt in outcome.attempts] == ["applied", "rejected", "applied"]
    # The first recruiter prompt told the recruiter exactly which cards it could staff.
    recall = {row["unit_id"]: row for row in json.loads(prompts[1])["typed_recall"]}
    assert recall[_PLAN_UNIT]["eligible_candidate_ids"] == [
        "operations-manager",
        "sre-site-reliability-engineer",
    ]
    assert "desktop-app-engineer" not in recall[_PLAN_UNIT]["eligible_candidate_ids"]
    # The repair named the eligible coverer of the token the ranked team missed.
    feedback = json.loads(prompts[2].split("[RUNTIME VALIDATION FEEDBACK]\n", 1)[1])
    (failed,) = [row for row in feedback["failed_units"] if row["unit_id"] == _PLAN_UNIT]
    assert failed["code"] == "staff_without_safe_team"
    contract = failed["safe_team_contract"]
    assert contract["eligible_coverers_by_requirement"] == {
        "domain:software-engineering": ["sre-site-reliability-engineer"]
    }
    assert "eligible_coverers_by_requirement" in failed["required_correction"]
    assert outcome.staffing.units[0].selected == ("sre-site-reliability-engineer",)
