"""Full-workforce regressions captured from live semantic-selection failures."""

from __future__ import annotations

import re
from dataclasses import replace
from functools import lru_cache

import pytest

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.workforce.contract import (
    project_workforce_contract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.fallback import (
    deterministic_plan_and_staff,
    deterministic_staff_plan,
)
from agency_runtime.core.workforce.inference import (
    _proposal_from_nominations,
    _semantic_staffing_classes,
    _typed_shortlists,
    staffing_budget_for_config,
)
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import known_contractor_agent
from agency_runtime.core.workforce.lifecycle_roles import role_anchors
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


@lru_cache(maxsize=1)
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
                ["implementation"],
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
                ["quality-assurance"],
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
                ["software-engineering"],
                ["review"],
                "review",
                "read_only",
                ["repository-read"],
                depends_on=["unit-implement", "unit-tests"],
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
    return parse_work_unit_plan(raw)


def test_active_incident_plan_has_a_safe_sufficient_audited_team() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Contain a credential-theft incident without offensive probing.",
            "units": [
                _unit(
                    "unit-incident-investigation",
                    "Preserve evidence and assess the active credential-theft incident",
                    "analysis",
                    "discovery",
                    ["security"],
                    ["analysis", "audit", "governance", "investigation", "risk-analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                ),
                _unit(
                    "unit-containment-plan",
                    "Prepare a reversible containment and recovery plan",
                    "plan",
                    "planning",
                    ["security"],
                    ["operations", "planning"],
                    "plan",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-incident-investigation"],
                ),
                _unit(
                    "unit-recovery-plan",
                    "Prepare a reversible recovery plan across security and service restoration",
                    "plan",
                    "planning",
                    ["security", "software-engineering"],
                    ["operations", "planning", "risk-analysis"],
                    "plan",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-containment-plan"],
                ),
            ],
        }
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "cloud-infrastructure",
                "communications-draft",
                "incident-timeline",
                "monitoring-observability",
                "native-delegation",
                "repository-read",
            }
        ),
        snapshot.generation,
    )

    result = deterministic_staff_plan(
        "Contain an active credential-theft incident, preserve forensic evidence, and "
        "prepare a reversible recovery plan. Do not probe the live target offensively.",
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.staffing.accepted
    assert {row.unit_id: row.selected for row in result.staffing.units} == {
        "unit-incident-investigation": ("incident-responder",),
        "unit-containment-plan": ("incident-responder",),
        "unit-recovery-plan": (
            "incident-responder",
            "incident-response-commander",
        ),
    }


def test_runtime_integration_shortlists_anchor_each_lifecycle_owner() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
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

    shortlists = {row["unit_id"]: row for row in _typed_shortlists(plan, snapshot.contracts)}

    assert shortlists["unit-routing-evidence"]["role_anchors"] == ["codebase-onboarding-engineer"]
    assert shortlists["unit-live-integration"]["role_anchors"] == [
        "application-integration-verifier",
        "test-results-analyzer",
    ]
    assert shortlists["unit-staffing-audit"]["role_anchors"] == ["selection-safety-critic"]


def test_runtime_request_recovers_codebase_anchor_from_generic_analysis() -> None:
    request = (
        "Diagnose why an installed runtime hook selected unrelated agents and failed to "
        "enforce its response header; inspect routing evidence and test the integration."
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-routing-diagnosis",
                    "Produce evidence-backed technical analysis",
                    "analysis",
                    "discovery",
                    ["software-engineering"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0], request=request) == ("codebase-onboarding-engineer",)


def test_documentation_unit_selects_existing_technical_writer_without_false_gap() -> None:
    snapshot = _snapshot()
    plan = parse_work_unit_plan(
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


def test_cross_platform_release_change_anchors_the_installer_owner() -> None:
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Correct the app and produce installable packages.",
            "units": [
                _unit(
                    "unit-release-change",
                    "A corrected app for Windows and Linux releases",
                    "implementation-change",
                    "implementation",
                    ["software-engineering"],
                    ["implementation"],
                    "modify",
                    "workspace_write",
                    ["repository-read", "repository-write", "code-execution"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0]) == ("cross-platform-installer-engineer",)


def test_untyped_implementation_anchors_the_governed_minimum_change_specialist() -> None:
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Implement the bounded application integration.",
            "units": [
                _unit(
                    "unit-application-integration",
                    "Complete the bounded application integration change",
                    "implementation-change",
                    "implementation",
                    ["software-engineering"],
                    ["implementation"],
                    "modify",
                    "workspace_write",
                    ["repository-read", "repository-write", "code-execution"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0]) == ("minimal-change-engineer",)


def test_local_page_workflow_anchors_the_ordinary_software_delivery_team() -> None:
    request = "Build a page that can be loaded locally without hosting it."
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-discovery",
                    "Analyze the local evidence page requirements",
                    "analysis",
                    "discovery",
                    ["software-engineering"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                ),
                _unit(
                    "unit-implementation",
                    "Implement the local evidence page",
                    "implementation-change",
                    "implementation",
                    ["software-engineering"],
                    ["implementation"],
                    "modify",
                    "workspace_write",
                    ["repository-read", "repository-write", "code-execution"],
                    depends_on=["unit-discovery"],
                ),
                _unit(
                    "unit-review",
                    "Review the local evidence page implementation",
                    "review-report",
                    "review",
                    ["quality-assurance"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-implementation"],
                ),
            ],
        }
    )

    assert [role_anchors(unit, request=request) for unit in plan.units] == [
        ("codebase-onboarding-engineer",),
        ("frontend-developer",),
        ("code-reviewer",),
    ]
    snapshot = _snapshot()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "code-execution",
                "native-delegation",
                "repository-read",
                "repository-write",
            }
        ),
        snapshot.generation,
    )

    result = deterministic_staff_plan(
        request,
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.staffing.accepted
    assert {row.unit_id: row.selected for row in result.staffing.units} == {
        "unit-discovery": ("codebase-onboarding-engineer",),
        "unit-implementation": ("frontend-developer",),
        "unit-review": ("code-reviewer",),
    }


def test_accessibility_review_anchors_the_audited_accessibility_specialist() -> None:
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Review the dashboard accessibility.",
            "units": [
                _unit(
                    "unit-accessibility-review",
                    "Accessibility assessment with actionable findings",
                    "review-report",
                    "review",
                    ["accessibility", "software-engineering"],
                    ["review", "audit", "accessibility"],
                    "review",
                    "read_only",
                    ["repository-read"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0]) == ("accessibility-auditor",)


def test_brand_whimsy_and_accessibility_owners_remain_in_isolated_units() -> None:
    request = (
        "Create brand-governance guidance and, in a separate isolated work unit, add "
        "bounded playful interface details with an independent accessibility audit."
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-brand",
                    "Brand-governance guidance and identity rules",
                    "plan",
                    "planning",
                    ["design"],
                    ["planning", "governance"],
                    "plan",
                    "read_only",
                    ["repository-read"],
                ),
                _unit(
                    "unit-whimsy",
                    "Implement bounded playful interface details",
                    "implementation-change",
                    "implementation",
                    ["design"],
                    ["implementation"],
                    "modify",
                    "workspace_write",
                    ["repository-read", "repository-write", "code-execution"],
                ),
                _unit(
                    "unit-accessibility",
                    "Independent accessibility audit of the interface details",
                    "review-report",
                    "review",
                    ["accessibility"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-whimsy"],
                ),
            ],
        }
    )
    assert [role_anchors(unit, request=request) for unit in plan.units] == [
        ("brand-guardian",),
        ("whimsy-injector",),
        ("accessibility-auditor",),
    ]
    snapshot = _snapshot()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "native-delegation",
                *(tool for contract in snapshot.contracts for tool in contract.tool_classes),
            }
        ),
        snapshot.generation,
    )

    result = deterministic_staff_plan(
        request,
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.staffing.accepted
    assert {row.unit_id: row.selected for row in result.staffing.units} == {
        "unit-brand": ("brand-guardian",),
        "unit-whimsy": ("whimsy-injector",),
        "unit-accessibility": ("accessibility-auditor",),
    }
    assert (
        len({context_id for row in result.staffing.units for _agent_id, context_id in row.contexts})
        == 3
    )


def test_accounts_payable_analysis_and_cfo_review_use_separate_finance_owners() -> None:
    request = (
        "Analyze supplied accounts-payable exceptions, then have the chief financial "
        "officer independently review cash-impact options in a separate context."
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-payables",
                    "Analyze supplied accounts-payable exceptions",
                    "analysis",
                    "discovery",
                    ["finance"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                ),
                _unit(
                    "unit-cfo-review",
                    "Independently review the cash-impact options",
                    "review-report",
                    "review",
                    ["finance"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-payables"],
                ),
            ],
        }
    )
    assert [role_anchors(unit, request=request) for unit in plan.units] == [
        ("accounts-payable-agent",),
        ("chief-financial-officer",),
    ]
    snapshot = _snapshot()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "native-delegation",
                *(tool for contract in snapshot.contracts for tool in contract.tool_classes),
            }
        ),
        snapshot.generation,
    )

    result = deterministic_staff_plan(
        request,
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.staffing.accepted
    assert {row.unit_id: row.selected for row in result.staffing.units} == {
        "unit-payables": ("accounts-payable-agent",),
        "unit-cfo-review": ("chief-financial-officer",),
    }


def test_postgres_query_diagnosis_anchors_the_database_optimizer() -> None:
    request = "Analyze measured PostgreSQL query-plan evidence for a slow write query."
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-query-analysis",
                    "Measured query-plan findings for the slow PostgreSQL write query",
                    "analysis",
                    "discovery",
                    ["software-engineering"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0], request=request) == ("database-optimizer",)


def test_postgres_request_recovers_database_anchor_from_generic_analysis() -> None:
    request = (
        "Analyze why this PostgreSQL write query is slow and return measured query-plan "
        "findings only."
    )
    generic_request = "Analyze why this repository query helper is slow."
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-query-analysis",
                    "Produce evidence-backed technical analysis",
                    "analysis",
                    "discovery",
                    ["software-engineering"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0], request=request) == ("database-optimizer",)
    assert role_anchors(plan.units[0], request=generic_request) == ("codebase-onboarding-engineer",)


def test_clinical_evidence_and_legal_review_anchor_bounded_specialists() -> None:
    request = (
        "Summarize supplied clinical-trial evidence and independently review its use in a "
        "legal document without diagnosis or compliance certification."
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-clinical-evidence",
                    "Evidence-grounded summary of supplied clinical-trial materials",
                    "analysis",
                    "discovery",
                    ["healthcare"],
                    ["analysis"],
                    "advise",
                    "read_only",
                    ["repository-read"],
                ),
                _unit(
                    "unit-legal-review",
                    "Independent review of evidence use in the legal document",
                    "review-report",
                    "review",
                    ["healthcare", "specialist-services"],
                    ["review"],
                    "review",
                    "read_only",
                    ["repository-read"],
                    depends_on=["unit-clinical-evidence"],
                ),
            ],
        }
    )

    assert [role_anchors(unit, request=request) for unit in plan.units] == [
        ("clinical-evidence-agent",),
        ("legal-document-review",),
    ]


def test_stackless_observability_owner_complements_python_implementation() -> None:
    request = (
        "Implement a production Python API with application observability, then separately "
        "verify installed Windows and Linux release evidence."
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-python-observability",
                    "Production Python API with application observability",
                    "implementation-change",
                    "implementation",
                    ["software-engineering"],
                    ["implementation"],
                    "modify",
                    "workspace_write",
                    ["repository-read", "repository-write", "code-execution"],
                    languages=["python"],
                )
            ],
        }
    )
    assert role_anchors(plan.units[0], request=request) == (
        "python-application-engineer",
        "application-observability-engineer",
    )
    snapshot = _snapshot()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "native-delegation",
                *(tool for contract in snapshot.contracts for tool in contract.tool_classes),
            }
        ),
        snapshot.generation,
    )

    result = deterministic_staff_plan(
        request,
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.proposal is not None
    assert result.proposal.units[0].selected == (
        "application-observability-engineer",
        "python-application-engineer",
    )


def test_incremental_language_server_change_anchors_the_lsp_specialist() -> None:
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Implement cancellation-safe incremental indexing.",
            "units": [
                _unit(
                    "unit-lsp-index",
                    "Language server supports cancellation-safe incremental indexing",
                    "implementation-change",
                    "implementation",
                    ["software-engineering"],
                    ["implementation"],
                    "modify",
                    "workspace_write",
                    ["repository-read", "repository-write", "code-execution"],
                )
            ],
        }
    )

    assert role_anchors(plan.units[0]) == ("lsp-index-engineer",)
    assert role_anchors(
        parse_work_unit_plan(
            {
                "schema_version": 2,
                "request_summary": "Implement cancellation handling.",
                "units": [
                    _unit(
                        "unit-generic-index-change",
                        "Implement cancellation handling",
                        "implementation-change",
                        "implementation",
                        ["software-engineering"],
                        ["implementation"],
                        "modify",
                        "workspace_write",
                        ["repository-read", "repository-write", "code-execution"],
                    )
                ],
            }
        ).units[0],
        request="Implement cancellation-safe indexing in the language server.",
    ) == ("lsp-index-engineer",)

    snapshot = _snapshot()
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "native-delegation",
                "repository-read",
                "repository-write",
                "code-execution",
                *(tool for contract in snapshot.contracts for tool in contract.tool_classes),
            }
        ),
        snapshot.generation,
    )
    result = deterministic_staff_plan(
        "Implement cancellation-safe incremental indexing in the language server.",
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.proposal is not None
    assert result.proposal.units[0].required == ("lsp-index-engineer",)
    assert result.proposal.units[0].selected == ("lsp-index-engineer",)
    assert result.proposal.units[0].margin >= AgencyConfig().workforce.min_margin


def test_disabled_lsp_discovery_anchor_is_disclosed_before_safe_fallback() -> None:
    request = (
        "Diagnose cancellation and stale-symbol defects in a language-server index. "
        "Explain the safest next step if the best specialist is disabled."
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": request,
            "units": [
                _unit(
                    "unit-lsp-diagnosis",
                    "Diagnose cancellation and stale-symbol defects",
                    "analysis",
                    "discovery",
                    ["software-engineering"],
                    ["analysis", "investigation"],
                    "review",
                    "read_only",
                    ["repository-read"],
                )
            ],
        }
    )
    assert role_anchors(plan.units[0], request=request) == ("lsp-index-engineer",)

    snapshot = _snapshot()
    contracts = tuple(
        replace(contract, enabled=False, employment="disabled")
        if contract.agent_id == "lsp-index-engineer"
        else contract
        for contract in snapshot.contracts
    )
    records = tuple(project_recruiter_index_record(contract) for contract in contracts)
    disabled_snapshot = replace(
        snapshot,
        contracts=contracts,
        contract_fingerprint=workforce_index_fingerprint(contracts),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "native-delegation",
                *(tool for contract in contracts for tool in contract.tool_classes),
            }
        ),
        disabled_snapshot.generation,
        frozenset(contract.agent_id for contract in contracts if contract.enabled),
    )

    result = deterministic_staff_plan(
        request,
        plan,
        disabled_snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.proposal is not None
    row = result.proposal.units[0]
    assert "lsp-index-engineer" not in row.selected
    assert row.disabled_shadows[0].agent_id == "lsp-index-engineer"
    assert row.disabled_shadows[0].fallback_agent_id in row.selected


def test_deterministic_staffing_requires_each_safe_lifecycle_owner() -> None:
    snapshot = _snapshot()
    plan = _captured_typescript_plan()
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

    result = deterministic_staff_plan(
        "Implement and independently verify the TypeScript application change.",
        plan,
        snapshot,
        config=AgencyConfig(),
        context=context,
    )

    assert result.staffing.accepted
    assert {row.unit_id: row.selected for row in result.staffing.units} == {
        "unit-implement": ("typescript-application-engineer",),
        "unit-tests": ("software-test-engineer",),
        "unit-review": ("code-reviewer",),
        "unit-results": ("test-results-analyzer",),
    }


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


@pytest.mark.skip(
    reason=(
        "ADR-0087: optimal specialist selection per ask is an inference-path "
        "property. The deterministic decider no longer claims it; this assertion "
        "moves to the inference suite once the recruiter is the primary decider."
    )
)
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


def test_model_required_specialist_is_trusted_under_adr_0087() -> None:
    # ADR-0087: inference is the sole decider. When the model nominates an
    # ELIGIBLE specialist as required, the runtime trusts that pick. Determinism
    # must not override an explicit model choice with a role anchor. Here both
    # the broad code-reviewer and the security auditor are eligible and cover
    # the unit; the model nominates the security auditor as required, so it is
    # selected even though a generic code-reviewer is also a valid anchor-free
    # candidate.
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
    role_owner = "ai-generated-code-security-auditor"
    shortlist = _typed_shortlists(plan, snapshot.contracts)[0]
    candidates = [item["agent_id"] for item in shortlist["candidates"]]
    assert {role_owner, "code-reviewer"} <= set(candidates)
    ordered = [
        role_owner,
        "code-reviewer",
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
                            if agent_id == role_owner
                            else "acceptable"
                            if agent_id == "code-reviewer"
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

    # The model's eligible required pick is the selection authority.
    assert proposal.units[0].required == (role_owner,)
    assert proposal.units[0].selected == (role_owner,)
    # No agent lands in both required and forbidden (clean partition).
    assert not set(proposal.units[0].required) & set(proposal.units[0].forbidden)


def test_role_anchor_fallback_only_when_model_nominates_no_eligible_required() -> None:
    # ADR-0087: role anchors are a recall/fallback safety net, not a gate that
    # overrides the model. The fallback seeds required from eligible audited
    # lifecycle owners ONLY when the model nominates no eligible required
    # specialist, and it respects the model's explicit forbidden set. Exercise
    # _semantic_staffing_classes directly with controlled inputs so the behavior
    # is pinned independent of which roster candidates happen to be recalled.
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
    unit = plan.units[0]
    contracts_by_id = {contract.agent_id: contract for contract in snapshot.contracts}
    role_owner = "ai-generated-code-security-auditor"
    assert role_anchors(unit) == (role_owner,)
    # software-test-engineer is a real specialist that is ineligible for this
    # security review unit (authority + domain + capability mismatch), so it
    # stands in for a model that nominates the wrong specialist as required.
    ineligible = "software-test-engineer"

    # Case 1: the model nominates an ineligible specialist as required. No
    # eligible model-required pick exists, so the fallback seeds required from
    # the eligible audited lifecycle owner.
    required, acceptable, forbidden = _semantic_staffing_classes(
        unit,
        {ineligible: "required"},
        {ineligible: 0.99, role_owner: 0.0},
        contracts_by_id,
        context,
    )
    assert required == {role_owner}
    assert ineligible not in acceptable  # ineligible -> forbidden
    assert ineligible in forbidden
    assert role_owner not in forbidden

    # Case 2: the model explicitly forbids the only eligible anchor. The
    # fallback respects that forbidden set, so required stays empty and no agent
    # is silently promoted over the model's choice (a declared gap, not an
    # override).
    required, acceptable, forbidden = _semantic_staffing_classes(
        unit,
        {ineligible: "required", role_owner: "forbidden"},
        {ineligible: 0.99, role_owner: 0.90},
        contracts_by_id,
        context,
    )
    assert required == set()
    assert role_owner in forbidden
    # Clean partition invariant: no agent in both required and forbidden.
    assert not (required & forbidden)


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
