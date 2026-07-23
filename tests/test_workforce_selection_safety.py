"""Full-workforce regressions captured from live semantic-selection failures."""

from __future__ import annotations

import re
from dataclasses import replace

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.workforce.contract import (
    project_workforce_contract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.fallback import deterministic_plan_and_staff
from agency_runtime.core.workforce.inference import (
    _normalized_plan_response,
    _proposal_from_nominations,
    _typed_shortlists,
    staffing_budget_for_config,
)
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import known_contractor_agent
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingContext,
    build_deterministic_proposal,
    verify_staffing,
)


def _snapshot() -> WorkforceIndexSnapshot:
    contracts = tuple(project_workforce_contract(agent) for agent in BundledRoster()) + tuple(
        project_workforce_contract(
            known_contractor_agent(contract),
            origin="agency",
        )
        for contract in KNOWN_CONTRACTORS_BY_SLUG.values()
    )
    records = tuple(project_recruiter_index_record(contract) for contract in contracts)
    return WorkforceIndexSnapshot(
        generation=7,
        worker_count=len(contracts),
        contracts=contracts,
        contract_fingerprint=workforce_index_fingerprint(contracts),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )


def _unit(
    unit_id: str,
    outcome: str,
    artifact_kind: str,
    lifecycle_phase: str,
    domains: list[str],
    required_capabilities: list[str],
    authority: str,
    mutation_scope: str,
    required_tools: list[str],
    *,
    depends_on: list[str] | None = None,
    languages: list[str] | None = None,
    platform: str = "windows",
) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "outcome": outcome,
        "artifact_kind": artifact_kind,
        "lifecycle_phase": lifecycle_phase,
        "domains": domains,
        "languages": languages or [],
        "frameworks": [],
        "required_capabilities": required_capabilities,
        "authority": authority,
        "mutation_scope": mutation_scope,
        "risks": [],
        "trust_boundaries": ["repository"],
        "claims": [],
        "depends_on": depends_on or [],
        "resources": ["repository"],
        "required_tools": required_tools,
        "platforms": [platform],
        "acceptance_evidence": ["The unit artifact is independently verified."],
        "parallelization": "sequential",
    }


def _captured_typescript_plan():
    raw = {
        "schema_version": 2,
        "request_summary": "Implement a TypeScript feature with tests and review.",
        "units": [
            _unit(
                "unit-implement",
                "Implement the TypeScript application feature",
                "implementation-change",
                "implementation",
                ["software-engineering"],
                ["analysis", "design"],
                "modify",
                "workspace_write",
                ["repository-read", "repository-write", "code-execution"],
                languages=["typescript"],
            ),
            _unit(
                "unit-tests",
                "Add automated feature tests and failure-path tests",
                "test-code",
                "testing",
                ["software-engineering"],
                ["testing"],
                "modify",
                "workspace_write",
                ["repository-read", "repository-write", "test-execution"],
                depends_on=["unit-implement"],
            ),
            _unit(
                "unit-review",
                "Independently review implementation and tests",
                "review-report",
                "review",
                ["quality-assurance"],
                ["review"],
                "review",
                "read_only",
                ["repository-read"],
                depends_on=["unit-implement", "unit-tests"],
                languages=["typescript"],
            ),
            _unit(
                "unit-results",
                "Execute tests and interpret completed test results",
                "test-evidence",
                "testing",
                ["quality-assurance"],
                ["verification"],
                "review",
                "read_only",
                ["test-execution"],
                depends_on=["unit-review"],
            ),
        ],
    }
    return parse_work_unit_plan(_normalized_plan_response(raw))


def test_runtime_integration_shortlists_anchor_each_lifecycle_owner() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        _normalized_plan_response(
            {
                "schema_version": 2,
                "request_summary": "Diagnose a runtime routing failure and verify the fix.",
                "units": [
                    _unit(
                        "unit-routing-evidence",
                        "Inspect Agency runtime routing evidence",
                        "analysis",
                        "discovery",
                        ["software-engineering"],
                        ["analysis"],
                        "review",
                        "read_only",
                        ["repository-read", "runtime-evidence"],
                    ),
                    _unit(
                        "unit-live-integration",
                        "Run live integration tests and interpret the completed evidence",
                        "test-evidence",
                        "testing",
                        ["quality-assurance"],
                        ["verification"],
                        "review",
                        "read_only",
                        ["runtime-evidence", "test-execution"],
                        depends_on=["unit-routing-evidence"],
                    ),
                    _unit(
                        "unit-staffing-audit",
                        "Audit the workforce staffing decision",
                        "review-report",
                        "review",
                        ["workforce-governance"],
                        ["review"],
                        "review",
                        "read_only",
                        ["runtime-evidence"],
                        depends_on=["unit-routing-evidence"],
                    ),
                ],
            }
        )
    )

    shortlists = {row["unit_id"]: row for row in _typed_shortlists(plan, snapshot.contracts)}

    assert shortlists["unit-routing-evidence"]["role_anchors"] == ["codebase-onboarding-engineer"]
    assert shortlists["unit-live-integration"]["role_anchors"] == [
        "application-integration-verifier",
        "test-results-analyzer",
    ]
    assert shortlists["unit-staffing-audit"]["role_anchors"] == ["selection-safety-critic"]


def test_documentation_unit_selects_existing_technical_writer_without_false_gap() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        _normalized_plan_response(
            {
                "schema_version": 2,
                "request_summary": "Write accurate repository documentation.",
                "units": [
                    _unit(
                        "unit-documentation",
                        "Write an accurate README for the implemented Python CLI",
                        "documentation",
                        "documentation",
                        ["software-engineering"],
                        ["documentation"],
                        "modify",
                        "workspace_write",
                        ["repository-read", "repository-write"],
                    )
                ],
            }
        )
    )
    shortlist = _typed_shortlists(plan, snapshot.contracts)[0]

    assert shortlist["role_anchors"] == ["technical-writer"]
    assert any(candidate["agent_id"] == "technical-writer" for candidate in shortlist["candidates"])
    candidate_ids = [candidate["agent_id"] for candidate in shortlist["candidates"]]

    context = StaffingContext(
        "codex",
        "windows",
        frozenset({"native-delegation", "repository-read", "repository-write", "test-execution"}),
        snapshot.generation,
    )
    proposal = _proposal_from_nominations(
        {
            "units": [
                {
                    "unit_id": "unit-documentation",
                    "ranked_semantic": [
                        {
                            "agent_id": agent_id,
                            "score": 0.99 if agent_id == "technical-writer" else 0.5,
                            "classification": (
                                "required" if agent_id == "technical-writer" else "acceptable"
                            ),
                            "positive_evidence": [
                                (
                                    "owns-repository-documentation"
                                    if agent_id == "technical-writer"
                                    else "typed-shortlist-candidate"
                                )
                            ],
                            "negative_evidence": [],
                        }
                        for agent_id in candidate_ids
                    ],
                }
            ]
        },
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert proposal.units[0].selected == ("technical-writer",)
    assert proposal.units[0].abstention_reasons == ()


def test_code_review_anchor_cannot_be_demoted_by_a_plausible_wrong_neighbor() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Diagnose why repository routing failed.",
            "units": [
                _unit(
                    "unit-diagnosis",
                    "Diagnose why the hook selected unrelated specialists and report the defect",
                    "review-report",
                    "review",
                    ["software-engineering"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read", "runtime-evidence"],
                )
            ],
        }
    )
    shortlist = _typed_shortlists(plan, snapshot.contracts)[0]
    candidate_ids = [item["agent_id"] for item in shortlist["candidates"]]
    assert shortlist["role_anchors"] == ["code-reviewer"]
    ordered = [
        "ai-generated-code-security-auditor",
        *(item for item in candidate_ids if item != "ai-generated-code-security-auditor"),
    ]
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "code-execution",
                "native-delegation",
                "repository-read",
                "runtime-evidence",
                "test-execution",
            }
        ),
        snapshot.generation,
    )
    proposal = _proposal_from_nominations(
        {
            "units": [
                {
                    "unit_id": "unit-diagnosis",
                    "ranked_semantic": [
                        {
                            "agent_id": agent_id,
                            "score": round(1.0 - (index * 0.03), 2),
                            "classification": "acceptable",
                            "positive_evidence": ["plausible-review-candidate"],
                            "negative_evidence": [],
                        }
                        for index, agent_id in enumerate(ordered)
                    ],
                }
            ]
        },
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert proposal.units[0].selected == ("code-reviewer",)
    assert proposal.units[0].margin >= AgencyConfig().workforce.min_margin
    assert verify_staffing(plan, proposal, snapshot.contracts, context=context).accepted


def test_nonsoftware_review_does_not_force_a_code_reviewer() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Review a product positioning decision.",
            "units": [
                _unit(
                    "unit-product-review",
                    "Review the product positioning decision",
                    "review-report",
                    "review",
                    ["product-strategy"],
                    ["review"],
                    "review",
                    "read_only",
                    [],
                )
            ],
        }
    )

    assert _typed_shortlists(plan, snapshot.contracts)[0]["role_anchors"] == []


def test_captured_typescript_plan_forms_exact_safe_lifecycle_team_from_full_workforce() -> None:
    snapshot = _snapshot()
    plan = _captured_typescript_plan()
    config = AgencyConfig()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "code-execution",
                "native-delegation",
                "package-management",
                "repository-read",
                "repository-write",
                "test-execution",
            }
        ),
        snapshot.generation,
    )
    expected = {
        "unit-implement": "typescript-application-engineer",
        "unit-tests": "software-test-engineer",
        "unit-review": "code-reviewer",
        "unit-results": "test-results-analyzer",
    }
    rows = []
    for shortlist in _typed_shortlists(plan, snapshot.contracts):
        unit_id = shortlist["unit_id"]
        expected_agent = expected[unit_id]
        candidates = [item["agent_id"] for item in shortlist["candidates"]]
        assert candidates[0] == expected_agent
        rows.append(
            {
                "unit_id": unit_id,
                "ranked_semantic": [
                    {
                        "agent_id": agent_id,
                        "score": round(1.0 - (index * 0.03), 2),
                        "classification": (
                            "required" if agent_id == expected_agent else "forbidden"
                        ),
                        "positive_evidence": (
                            ["decisive-scope-match"] if agent_id == expected_agent else []
                        ),
                        "negative_evidence": (
                            [] if agent_id == expected_agent else ["wrong-neighbor"]
                        ),
                    }
                    for index, agent_id in enumerate(candidates)
                ],
            }
        )

    proposal = _proposal_from_nominations(
        {"units": rows},
        plan,
        snapshot,
        config=config,
        context=context,
    )
    decision = verify_staffing(
        plan,
        proposal,
        snapshot.contracts,
        context=context,
        budget=staffing_budget_for_config(config),
    )

    assert snapshot.worker_count == 272
    assert decision.accepted
    assert {unit.unit_id: unit.selected for unit in decision.units} == {
        unit_id: (agent_id,) for unit_id, agent_id in expected.items()
    }


def test_security_patch_review_uses_discovery_code_and_security_specialists() -> None:
    snapshot = _snapshot()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "native-delegation",
                "repository-read",
                "repository-write",
                "source-control",
                "test-execution",
            }
        ),
        snapshot.generation,
    )

    result = deterministic_plan_and_staff(
        "Review this security patch.",
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.accepted
    assert {unit.unit_id: unit.selected for unit in result.staffing.units} == {
        "unit-codebase-discovery": ("codebase-onboarding-engineer",),
        "unit-code-review": ("code-reviewer",),
        "unit-security-review": ("ai-generated-code-security-auditor",),
    }


def test_live_shaped_multidomain_security_plan_recruits_the_exact_safe_team() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Review a repository security patch",
            "units": [
                _unit(
                    "unit-code-path-analysis",
                    "Map the affected code path and trust boundaries",
                    "analysis",
                    "discovery",
                    ["software-engineering"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                ),
                _unit(
                    "unit-correctness-review",
                    "Independently review correctness and regression risk",
                    "review-report",
                    "review",
                    ["software-engineering"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-code-path-analysis"],
                ),
                _unit(
                    "unit-exploitability-audit",
                    "Audit exploitability and security regressions",
                    "review-report",
                    "review",
                    ["security", "software-engineering"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-code-path-analysis"],
                ),
            ],
        }
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset({"native-delegation", "repository-read", "source-control"}),
        snapshot.generation,
    )
    expected = {
        "unit-code-path-analysis": "codebase-onboarding-engineer",
        "unit-correctness-review": "code-reviewer",
        "unit-exploitability-audit": "ai-generated-code-security-auditor",
    }
    rows = []
    for shortlist in _typed_shortlists(plan, snapshot.contracts):
        unit_id = shortlist["unit_id"]
        candidates = [item["agent_id"] for item in shortlist["candidates"]]
        assert candidates[0] == expected[unit_id]
        rows.append(
            {
                "unit_id": unit_id,
                "ranked_semantic": [
                    {
                        "agent_id": agent_id,
                        "score": round(1.0 - (index * 0.03), 2),
                        "classification": "required" if index == 0 else "forbidden",
                        "positive_evidence": ["decisive-scope-match"] if index == 0 else [],
                        "negative_evidence": [] if index == 0 else ["wrong-neighbor"],
                    }
                    for index, agent_id in enumerate(candidates)
                ],
            }
        )

    config = AgencyConfig()
    proposal = _proposal_from_nominations(
        {"units": rows},
        plan,
        snapshot,
        config=config,
        context=context,
    )
    decision = verify_staffing(
        plan,
        proposal,
        snapshot.contracts,
        context=context,
        budget=staffing_budget_for_config(config),
    )

    assert decision.accepted
    assert {unit.unit_id: unit.selected for unit in decision.units} == {
        unit_id: (agent_id,) for unit_id, agent_id in expected.items()
    }


def test_runtime_promotes_security_role_owner_over_broad_code_reviewer() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Audit a security patch for exploitability",
            "units": [
                _unit(
                    "unit-exploitability-audit",
                    "Audit exploitability and security regressions",
                    "review-report",
                    "review",
                    ["security", "software-engineering"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                )
            ],
        }
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset({"native-delegation", "repository-read", "source-control"}),
        snapshot.generation,
    )
    shortlist = _typed_shortlists(plan, snapshot.contracts)[0]
    candidates = [item["agent_id"] for item in shortlist["candidates"]]
    role_owner = "ai-generated-code-security-auditor"
    assert {role_owner, "code-reviewer"} <= set(candidates)
    ordered = [
        "code-reviewer",
        role_owner,
        *(item for item in candidates if item not in {"code-reviewer", role_owner}),
    ]
    nominations = {
        "units": [
            {
                "unit_id": "unit-exploitability-audit",
                "ranked_semantic": [
                    {
                        "agent_id": agent_id,
                        "score": round(1.0 - (index * 0.03), 2),
                        "classification": (
                            "required"
                            if agent_id == "code-reviewer"
                            else "acceptable"
                            if agent_id == role_owner
                            else "forbidden"
                        ),
                        "positive_evidence": (
                            ["review-scope-match"]
                            if agent_id in {"code-reviewer", role_owner}
                            else []
                        ),
                        "negative_evidence": (
                            [] if agent_id in {"code-reviewer", role_owner} else ["wrong-neighbor"]
                        ),
                    }
                    for index, agent_id in enumerate(ordered)
                ],
            }
        ]
    }

    proposal = _proposal_from_nominations(
        nominations,
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert proposal.units[0].selected == (role_owner,)


def _contract_plan(contract, *, outcome: str | None = None):
    capability = "-".join(re.findall(r"[a-z0-9]+", contract.outcomes[0].casefold()))
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": outcome or contract.outcomes[0],
            "units": [
                _unit(
                    "unit-contract",
                    outcome
                    or (
                        contract.scope_qualifiers[0]
                        if contract.scope_qualifiers
                        else contract.outcomes[0]
                    ),
                    contract.artifact_kinds[0],
                    contract.lifecycle_phases[0],
                    [contract.domains[0]],
                    [capability],
                    contract.authority,
                    "workspace_write" if contract.authority == "modify" else "read_only",
                    list(contract.tool_classes),
                    platform=contract.platforms[0],
                )
            ],
        }
    )


def _single_worker_proposal(contract, plan, context, contracts):
    return build_deterministic_proposal(
        plan,
        contracts,
        {"unit-contract": ((contract.agent_id, 1.0),)},
        context=context,
    )


def test_every_worker_contract_has_positive_negative_shadow_and_eligibility_evidence() -> None:
    snapshot = _snapshot()
    all_tools = frozenset(tool for contract in snapshot.contracts for tool in contract.tool_classes)
    failures: list[tuple[str, str, object]] = []

    for contract in snapshot.contracts:
        context = StaffingContext(
            contract.hosts[0],
            contract.platforms[0],
            all_tools,
            snapshot.generation,
        )
        plan = _contract_plan(contract)
        positive = _single_worker_proposal(contract, plan, context, snapshot.contracts).units[0]
        if positive.selected != (contract.agent_id,):
            failures.append((contract.agent_id, "positive", positive))

        if not contract.not_for:
            failures.append((contract.agent_id, "missing-hard-negative", contract.not_for))
        else:
            negative_plan = _contract_plan(contract, outcome=contract.not_for[0])
            negative = _single_worker_proposal(
                contract, negative_plan, context, snapshot.contracts
            ).units[0]
            reasons = {
                code for evidence in negative.negative_evidence for code in evidence.reason_codes
            }
            if negative.selected or "agent_explicitly_out_of_scope" not in reasons:
                failures.append((contract.agent_id, "hard-negative", negative))

        disabled = replace(contract, enabled=False, employment="disabled")
        disabled_contracts = tuple(
            disabled if item.agent_id == contract.agent_id else item for item in snapshot.contracts
        )
        disabled_row = _single_worker_proposal(disabled, plan, context, disabled_contracts).units[0]
        if (
            disabled_row.selected
            or not disabled_row.disabled_shadows
            or disabled_row.disabled_shadows[0].agent_id != contract.agent_id
        ):
            failures.append((contract.agent_id, "disabled-shadow", disabled_row))

        excluded_context = replace(context, eligible_worker_ids=frozenset())
        unavailable = _single_worker_proposal(
            contract, plan, excluded_context, snapshot.contracts
        ).units[0]
        unavailable_reasons = {
            code for shadow in unavailable.unavailable_shadows for code in shadow.reason_codes
        }
        if unavailable.selected or "agent_not_live_eligible" not in unavailable_reasons:
            failures.append((contract.agent_id, "live-eligibility", unavailable))

    assert snapshot.worker_count == 272
    assert failures == []
