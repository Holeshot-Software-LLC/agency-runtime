"""Configured-inference workforce selection corpus and truthful grading."""

from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Final

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.workforce.contract import workforce_index_fingerprint
from agency_runtime.core.workforce.inference import (
    WorkforceRoutingOutcome,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import StaffingContext

SCHEMA: Final[str] = "agency-runtime.workforce-inference-eval"
VERSION: Final[str] = "1.3.0"
DEFAULT_COLD_SELECTION_BUDGET_MS: Final[int] = 15_000


@dataclass(frozen=True, slots=True)
class WorkforceSelectionCase:
    case_id: str
    request: str
    required_workers: tuple[str, ...]
    forbidden_workers: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    required_lifecycles: tuple[str, ...]
    category: str = ""
    helpful_workers: tuple[str, ...] = ()
    disabled_workers: tuple[str, ...] = ()
    required_disabled_shadows: tuple[str, ...] = ()
    forbidden_context_pairs: tuple[tuple[str, str], ...] = ()
    outcome_policy: str = "accepted"
    latency_budget_ms: int = DEFAULT_COLD_SELECTION_BUDGET_MS

    def __post_init__(self) -> None:
        helpful = self.expected_helpful_workers
        identifier_groups = (
            self.required_workers,
            self.forbidden_workers,
            helpful,
            self.disabled_workers,
            self.required_disabled_shadows,
        )
        if not self.case_id or not self.request or not self.category:
            raise ValueError("selection cases require an id, request, and category")
        if not helpful or not self.forbidden_workers:
            raise ValueError("selection cases require helpful and forbidden workers")
        if any(len(items) != len(set(items)) for items in identifier_groups):
            raise ValueError("selection case worker identifiers must be unique")
        if not set(self.required_workers) <= set(helpful):
            raise ValueError("required workers must be expected helpful workers")
        if set(helpful) & set(self.forbidden_workers):
            raise ValueError("helpful and forbidden workers must be disjoint")
        if not set(self.required_disabled_shadows) <= set(self.disabled_workers):
            raise ValueError("required disabled shadows must be disabled by the case")
        if self.outcome_policy not in {"accepted", "accepted_or_abstained"}:
            raise ValueError("selection case outcome policy is invalid")
        if isinstance(self.latency_budget_ms, bool) or self.latency_budget_ms <= 0:
            raise ValueError("selection case latency budget must be positive")
        for pair in self.forbidden_context_pairs:
            if len(pair) != 2 or pair[0] == pair[1]:
                raise ValueError("selection case context conflicts require distinct pairs")

    @property
    def expected_helpful_workers(self) -> tuple[str, ...]:
        return self.helpful_workers or self.required_workers


CASES: Final[tuple[WorkforceSelectionCase, ...]] = (
    WorkforceSelectionCase(
        "python-production-change",
        "Fix this Python application bug, add failure-path tests, and independently review it.",
        (
            "python-application-engineer",
            "software-test-engineer",
            "code-reviewer",
            "test-results-analyzer",
        ),
        ("technical-writer", "typescript-application-engineer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review", "testing"),
        category="compound-coding",
    ),
    WorkforceSelectionCase(
        "typescript-production-change",
        "Implement this TypeScript application feature with tests and independent code review.",
        (
            "typescript-application-engineer",
            "software-test-engineer",
            "code-reviewer",
            "test-results-analyzer",
        ),
        ("python-application-engineer", "technical-writer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review", "testing"),
        category="compound-coding",
    ),
    WorkforceSelectionCase(
        "backend-service-change",
        "Build a production backend service endpoint with integration tests and code review.",
        (
            "backend-service-engineer",
            "software-test-engineer",
            "code-reviewer",
            "test-results-analyzer",
        ),
        ("ui-designer", "technical-writer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review", "testing"),
        category="compound-coding",
    ),
    WorkforceSelectionCase(
        "installed-cross-platform-release",
        "Fix and package this app for Windows and Linux, test it, review it, and verify the installed release.",
        ("software-test-engineer", "code-reviewer", "cross-platform-release-verifier"),
        ("language-translator", "geographer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review", "release"),
        category="cross-platform-release",
    ),
    WorkforceSelectionCase(
        "application-integration",
        "Implement the app integration, add tests, then independently verify the complete running application.",
        (
            "software-test-engineer",
            "code-reviewer",
            "application-integration-verifier",
        ),
        ("technical-writer", "financial-analyst"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review"),
        category="integration-assurance",
    ),
    WorkforceSelectionCase(
        "application-observability",
        "Add production application observability, failure telemetry, tests, and independent review.",
        ("application-observability-engineer", "software-test-engineer", "code-reviewer"),
        ("social-media-strategist", "legal-document-review"),
        ("implementation-change", "test-code", "review-report"),
        ("implementation", "testing", "review"),
        category="observability-assurance",
    ),
    WorkforceSelectionCase(
        "documentation-change",
        "Rewrite the repository README installation guide and independently review its technical accuracy.",
        ("technical-writer", "code-reviewer"),
        ("database-optimizer", "clinical-evidence-agent"),
        ("documentation", "review-report"),
        ("review",),
        category="documentation",
    ),
    WorkforceSelectionCase(
        "selection-safety-review",
        "Audit this workforce selection plan for wrong-neighbor choices and unsafe agent composition.",
        ("selection-safety-critic",),
        ("clinical-evidence-agent", "language-translator"),
        ("review-report",),
        ("review",),
        category="selection-safety",
    ),
    WorkforceSelectionCase(
        "repository-security-patch-review",
        (
            "Review this repository security patch. First map the affected code path, then "
            "independently review correctness and audit exploitability without changing files."
        ),
        (
            "codebase-onboarding-engineer",
            "code-reviewer",
            "ai-generated-code-security-auditor",
        ),
        ("business-strategist", "financial-analyst", "technical-writer"),
        ("review-report",),
        ("discovery", "review"),
        category="security-review",
    ),
    WorkforceSelectionCase(
        "runtime-routing-integration-failure",
        (
            "Diagnose why an installed Agency Runtime hook selected unrelated agents and did "
            "not enforce its response header; inspect routing evidence, test the live "
            "integration locally, and independently audit the staffing decision."
        ),
        (
            "application-integration-verifier",
            "selection-safety-critic",
            "test-results-analyzer",
        ),
        ("business-strategist", "financial-analyst", "technical-writer"),
        ("review-report", "test-evidence"),
        ("review", "testing"),
        category="weak-lexical-neighbor",
    ),
    WorkforceSelectionCase(
        "active-incident-containment",
        (
            "Contain an active credential-theft incident, preserve forensic evidence, and "
            "prepare a reversible recovery plan. Do not probe the live target offensively."
        ),
        ("incident-responder",),
        ("penetration-tester", "application-security-engineer"),
        ("analysis", "plan"),
        ("discovery", "planning"),
        category="dangerous-incompatible-selection",
        helpful_workers=("incident-responder", "incident-response-commander"),
    ),
    WorkforceSelectionCase(
        "lsp-incremental-index",
        (
            "Implement cancellation-safe incremental indexing in this language server, add "
            "failure-path tests, and independently review the change."
        ),
        (
            "lsp-index-engineer",
            "software-test-engineer",
            "code-reviewer",
            "test-results-analyzer",
        ),
        ("seo-specialist", "database-optimizer", "technical-writer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review"),
        category="rare-specialty",
    ),
    WorkforceSelectionCase(
        "disabled-lsp-winner",
        (
            "Diagnose cancellation and stale-symbol defects in a language-server index. "
            "Explain the safest next step if the best specialist is disabled."
        ),
        (),
        ("seo-specialist", "database-optimizer", "technical-writer"),
        ("analysis",),
        ("discovery",),
        category="disabled-best-candidate",
        helpful_workers=("lsp-index-engineer",),
        disabled_workers=("lsp-index-engineer",),
        required_disabled_shadows=("lsp-index-engineer",),
        outcome_policy="accepted_or_abstained",
    ),
    WorkforceSelectionCase(
        "incidental-finance-language",
        (
            "Fix the Python parser field named annual_revenue, add failure-path tests, and "
            "independently review the code. Do not perform financial analysis."
        ),
        (
            "python-application-engineer",
            "software-test-engineer",
            "code-reviewer",
            "test-results-analyzer",
        ),
        (
            "financial-analyst",
            "finance-tracker",
            "chief-financial-officer",
            "business-strategist",
        ),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review"),
        category="weak-incidental-lexical-match",
    ),
    WorkforceSelectionCase(
        "broad-python-typescript-application",
        (
            "Build a production Python API plus TypeScript dashboard with failure-path tests, "
            "accessibility review, observability, independent integration verification, and "
            "installed Windows and Linux release evidence."
        ),
        (
            "python-application-engineer",
            "typescript-application-engineer",
            "software-test-engineer",
            "code-reviewer",
            "test-results-analyzer",
            "accessibility-auditor",
            "application-observability-engineer",
            "application-integration-verifier",
            "cross-platform-release-verifier",
        ),
        ("rapid-prototyper", "senior-developer", "technical-writer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review", "release"),
        category="broad-multi-agent",
    ),
    WorkforceSelectionCase(
        "brand-and-whimsy-separated",
        (
            "Create brand-governance guidance and, in a separate isolated work unit, add "
            "bounded playful interface details with an independent accessibility audit."
        ),
        ("brand-guardian", "whimsy-injector", "accessibility-auditor"),
        ("seo-specialist", "financial-analyst"),
        ("plan", "implementation-change", "review-report"),
        ("planning", "implementation", "review"),
        category="conflict-composition",
        forbidden_context_pairs=(("brand-guardian", "whimsy-injector"),),
    ),
    WorkforceSelectionCase(
        "accounts-payable-cfo-separated",
        (
            "Analyze supplied accounts-payable exceptions, then have the chief financial "
            "officer independently review cash-impact options in a separate context."
        ),
        ("accounts-payable-agent", "chief-financial-officer"),
        ("growth-hacker", "personal-growth-mentor"),
        ("analysis", "review-report"),
        ("discovery", "review"),
        category="conflict-composition",
        forbidden_context_pairs=(("accounts-payable-agent", "chief-financial-officer"),),
    ),
    WorkforceSelectionCase(
        "postgres-write-query-analysis",
        (
            "Analyze why this PostgreSQL write query is slow. Do not write documentation or "
            "change application code; return measured query-plan findings only."
        ),
        ("database-optimizer",),
        ("technical-writer", "financial-analyst", "backend-service-engineer"),
        ("analysis",),
        ("discovery",),
        category="weak-incidental-lexical-match",
    ),
    WorkforceSelectionCase(
        "clinical-legal-boundary-review",
        (
            "Summarize the supplied clinical-trial evidence and independently review its use "
            "in a legal document. Do not diagnose, code medical billing, or certify compliance."
        ),
        ("clinical-evidence-agent", "legal-document-review"),
        ("medical-billing-coding-specialist", "legal-compliance-checker"),
        ("analysis", "review-report"),
        ("discovery", "review"),
        category="high-risk-boundary",
    ),
)


WorkforceRouter = Callable[..., WorkforceRoutingOutcome]


def _snapshot_for_case(
    snapshot: WorkforceIndexSnapshot,
    case: WorkforceSelectionCase,
) -> WorkforceIndexSnapshot:
    if not case.disabled_workers:
        return snapshot
    disabled = set(case.disabled_workers)
    contracts = tuple(
        replace(contract, enabled=False, employment="disabled")
        if contract.agent_id in disabled
        else contract
        for contract in snapshot.contracts
    )
    records = tuple(project_recruiter_index_record(contract) for contract in contracts)
    return WorkforceIndexSnapshot(
        generation=snapshot.generation,
        worker_count=len(contracts),
        contracts=contracts,
        contract_fingerprint=workforce_index_fingerprint(contracts),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )


def _case_result(
    case: WorkforceSelectionCase,
    outcome: WorkforceRoutingOutcome,
    *,
    latency_ms: float,
) -> dict[str, Any]:
    selected = tuple(
        dict.fromkeys(agent_id for unit in outcome.staffing.units for agent_id in unit.selected)
    )
    artifacts = tuple(
        dict.fromkeys(unit.artifact_kind for unit in (outcome.plan.units if outcome.plan else ()))
    )
    lifecycles = tuple(
        dict.fromkeys(unit.lifecycle_phase for unit in (outcome.plan.units if outcome.plan else ()))
    )
    disabled_disclosures = tuple(
        dict.fromkeys(
            [shadow.agent_id for unit in outcome.staffing.units for shadow in unit.disabled_shadows]
            + (
                []
                if outcome.proposal is None
                else [
                    shadow.agent_id
                    for unit in outcome.proposal.units
                    for shadow in unit.disabled_shadows
                ]
            )
        )
    )
    contexts: dict[str, set[str]] = {}
    for unit in outcome.staffing.units:
        for agent_id, context_id in unit.contexts:
            contexts.setdefault(context_id, set()).add(agent_id)
    plan_units = [
        {
            "unit_id": unit.unit_id,
            "artifact_kind": unit.artifact_kind,
            "lifecycle_phase": unit.lifecycle_phase,
            "domains": list(unit.domains),
            "languages": list(unit.languages),
            "frameworks": list(unit.frameworks),
            "required_capabilities": list(unit.required_capabilities),
            "required_tools": list(unit.required_tools),
            "depends_on": list(unit.depends_on),
        }
        for unit in (outcome.plan.units if outcome.plan else ())
    ]
    missing_workers = sorted(set(case.required_workers).difference(selected))
    helpful_workers = case.expected_helpful_workers
    helpful_selected = sorted(set(helpful_workers).intersection(selected))
    forbidden_workers = sorted(set(case.forbidden_workers).intersection(selected))
    selected_disabled = sorted(set(case.disabled_workers).intersection(selected))
    missing_disabled_shadows = sorted(
        set(case.required_disabled_shadows).difference(disabled_disclosures)
    )
    forbidden_context_pairs = sorted(
        [left, right]
        for left, right in case.forbidden_context_pairs
        if any({left, right} <= agent_ids for agent_ids in contexts.values())
    )
    allowed_abstention = (
        case.outcome_policy == "accepted_or_abstained" and outcome.status == "abstained"
    )
    missing_artifacts = (
        [] if allowed_abstention else sorted(set(case.required_artifacts).difference(artifacts))
    )
    missing_lifecycles = (
        [] if allowed_abstention else sorted(set(case.required_lifecycles).difference(lifecycles))
    )
    attempts = [
        {
            "stage": item.stage,
            "provider": item.provider_name,
            "requested_model": item.requested_model,
            "router_alias": item.model_group,
            "actual_model": item.actual_model,
            "model_receipt_source": item.model_receipt_source,
            "status": item.status,
            "reason_code": item.reason_code,
            "validation_detail": item.validation_detail,
        }
        for item in outcome.attempts
    ]
    applied_stages = {item.stage for item in outcome.attempts if item.status == "applied"}
    inference_applied = bool(
        outcome.inference_mode == "inferred"
        and ("combined" in applied_stages or "planner" in applied_stages)
    )
    outcome_ok = outcome.accepted or allowed_abstention
    precision = len(helpful_selected) / len(selected) if selected else 0.0
    recall = len(helpful_selected) / len(helpful_workers)
    passed = bool(
        outcome_ok
        and inference_applied
        and not missing_workers
        and not forbidden_workers
        and not selected_disabled
        and not missing_disabled_shadows
        and not forbidden_context_pairs
        and not missing_artifacts
        and not missing_lifecycles
        and latency_ms <= case.latency_budget_ms
    )
    return {
        "case_id": case.case_id,
        "category": case.category,
        "request": case.request,
        "passed": passed,
        "status": outcome.status,
        "outcome_policy": case.outcome_policy,
        "inference_mode": outcome.inference_mode,
        "inference_applied": inference_applied,
        "selected_workers": list(selected),
        "helpful_workers": list(helpful_workers),
        "helpful_selected": helpful_selected,
        "helpful_precision": round(precision, 6),
        "helpful_recall": round(recall, 6),
        "required_workers": list(case.required_workers),
        "missing_workers": missing_workers,
        "forbidden_workers": list(case.forbidden_workers),
        "forbidden_workers_selected": forbidden_workers,
        "disabled_workers": list(case.disabled_workers),
        "disabled_workers_selected": selected_disabled,
        "disabled_workers_disclosed": list(disabled_disclosures),
        "missing_disabled_shadows": missing_disabled_shadows,
        "forbidden_context_pairs": [list(pair) for pair in case.forbidden_context_pairs],
        "forbidden_context_pairs_selected": forbidden_context_pairs,
        "artifacts": list(artifacts),
        "missing_artifacts": missing_artifacts,
        "lifecycles": list(lifecycles),
        "missing_lifecycles": missing_lifecycles,
        "plan_units": plan_units,
        "abstention_codes": list(outcome.abstention_codes),
        "calls_used": outcome.calls_used,
        "latency_ms": round(latency_ms, 3),
        "latency_budget_ms": case.latency_budget_ms,
        "model_attempts": attempts,
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def run_workforce_inference_eval(
    snapshot: WorkforceIndexSnapshot,
    *,
    config: AgencyConfig,
    context: StaffingContext,
    cases: tuple[WorkforceSelectionCase, ...] = CASES,
    router: WorkforceRouter = plan_and_staff_workforce,
) -> dict[str, Any]:
    """Run explicit configured inference and grade semantic team outcomes."""

    if not cases:
        raise ValueError("workforce inference evaluation requires at least one case")
    details: list[dict[str, Any]] = []
    for case in cases:
        case_snapshot = _snapshot_for_case(snapshot, case)
        started = time.perf_counter()
        outcome = router(case.request, case_snapshot, config=config, context=context)
        details.append(
            _case_result(
                case,
                outcome,
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        )
    passed_count = sum(bool(item["passed"]) for item in details)
    latencies = [float(item["latency_ms"]) for item in details]
    call_budget = {
        "fast": config.workforce.fast_call_budget,
        "balanced": config.workforce.balanced_call_budget,
        "strict": config.workforce.strict_call_budget,
    }[config.workforce.mode]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "evidence": {
            "kind": "configured_inference",
            "network_may_be_used": True,
            "live_host_used": False,
            "task_outcomes_measured": False,
            "superiority_claimed": False,
            "limitation": (
                "This grades configured planner/recruiter team selection. It does not execute "
                "the assigned work or prove application quality."
            ),
        },
        "workforce": {
            "count": snapshot.worker_count,
            "generation": snapshot.generation,
            "contract_fingerprint": snapshot.contract_fingerprint,
            "recruiter_fingerprint": snapshot.recruiter_fingerprint,
        },
        "host": context.host,
        "platform": context.platform,
        "case_count": len(details),
        "passed_count": passed_count,
        "failed_count": len(details) - passed_count,
        "maximum_provider_calls": len(details) * call_budget,
        "latency": {
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(_percentile(latencies, 0.95), 3),
            "maximum_ms": round(max(latencies), 3),
        },
        "passed": passed_count == len(details),
        "details": details,
    }


__all__ = [
    "CASES",
    "DEFAULT_COLD_SELECTION_BUDGET_MS",
    "SCHEMA",
    "VERSION",
    "WorkforceSelectionCase",
    "run_workforce_inference_eval",
]
