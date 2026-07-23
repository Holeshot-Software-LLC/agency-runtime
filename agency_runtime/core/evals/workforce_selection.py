"""Configured-inference workforce selection corpus and truthful grading."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.workforce.inference import (
    WorkforceRoutingOutcome,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.staffing_verifier import StaffingContext

SCHEMA: Final[str] = "agency-runtime.workforce-inference-eval"
VERSION: Final[str] = "1.2.0"


@dataclass(frozen=True, slots=True)
class WorkforceSelectionCase:
    case_id: str
    request: str
    required_workers: tuple[str, ...]
    forbidden_workers: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    required_lifecycles: tuple[str, ...]


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
    ),
    WorkforceSelectionCase(
        "installed-cross-platform-release",
        "Fix and package this app for Windows and Linux, test it, review it, and verify the installed release.",
        ("software-test-engineer", "code-reviewer", "cross-platform-release-verifier"),
        ("language-translator", "geographer"),
        ("implementation-change", "test-code", "review-report", "test-evidence"),
        ("implementation", "testing", "review", "release"),
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
    ),
    WorkforceSelectionCase(
        "application-observability",
        "Add production application observability, failure telemetry, tests, and independent review.",
        ("application-observability-engineer", "software-test-engineer", "code-reviewer"),
        ("social-media-strategist", "legal-document-review"),
        ("implementation-change", "test-code", "review-report"),
        ("implementation", "testing", "review"),
    ),
    WorkforceSelectionCase(
        "documentation-change",
        "Rewrite the repository README installation guide and independently review its technical accuracy.",
        ("technical-writer", "code-reviewer"),
        ("database-optimizer", "clinical-evidence-agent"),
        ("documentation", "review-report"),
        ("review",),
    ),
    WorkforceSelectionCase(
        "selection-safety-review",
        "Audit this workforce selection plan for wrong-neighbor choices and unsafe agent composition.",
        ("selection-safety-critic",),
        ("clinical-evidence-agent", "language-translator"),
        ("review-report",),
        ("review",),
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
    ),
)


WorkforceRouter = Callable[..., WorkforceRoutingOutcome]


def _case_result(
    case: WorkforceSelectionCase,
    outcome: WorkforceRoutingOutcome,
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
    forbidden_workers = sorted(set(case.forbidden_workers).intersection(selected))
    missing_artifacts = sorted(set(case.required_artifacts).difference(artifacts))
    missing_lifecycles = sorted(set(case.required_lifecycles).difference(lifecycles))
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
    passed = bool(
        outcome.accepted
        and inference_applied
        and not missing_workers
        and not forbidden_workers
        and not missing_artifacts
        and not missing_lifecycles
    )
    return {
        "case_id": case.case_id,
        "passed": passed,
        "status": outcome.status,
        "inference_mode": outcome.inference_mode,
        "inference_applied": inference_applied,
        "selected_workers": list(selected),
        "required_workers": list(case.required_workers),
        "missing_workers": missing_workers,
        "forbidden_workers_selected": forbidden_workers,
        "artifacts": list(artifacts),
        "missing_artifacts": missing_artifacts,
        "lifecycles": list(lifecycles),
        "missing_lifecycles": missing_lifecycles,
        "plan_units": plan_units,
        "abstention_codes": list(outcome.abstention_codes),
        "calls_used": outcome.calls_used,
        "model_attempts": attempts,
    }


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
    details = [
        _case_result(
            case,
            router(case.request, snapshot, config=config, context=context),
        )
        for case in cases
    ]
    passed_count = sum(bool(item["passed"]) for item in details)
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
        "passed": passed_count == len(details),
        "details": details,
    }


__all__ = [
    "CASES",
    "SCHEMA",
    "VERSION",
    "WorkforceSelectionCase",
    "run_workforce_inference_eval",
]
