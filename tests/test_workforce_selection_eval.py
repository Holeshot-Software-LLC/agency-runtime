from __future__ import annotations

from argparse import Namespace
from dataclasses import replace

import pytest

from agency_runtime.cli.eval_commands import _eval_staffing_context, cmd_eval_workforce
from agency_runtime.core.config import AgencyConfig, WorkforceConfig
from agency_runtime.core.evals.workforce_selection import (
    CASES,
    SCHEMA,
    VERSION,
    run_workforce_inference_eval,
)
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.workforce.inference import (
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingContext,
    StaffingDecision,
    VerifiedUnitStaffing,
)


def _accepted_outcome() -> WorkforceRoutingOutcome:
    case = CASES[0]
    artifacts = zip(case.required_artifacts, case.required_lifecycles, strict=True)
    units = []
    verified = []
    for index, (artifact, lifecycle) in enumerate(artifacts, start=1):
        unit_id = f"unit-eval-{index}"
        units.append(
            {
                "unit_id": unit_id,
                "outcome": f"Produce the required {artifact}",
                "artifact_kind": artifact,
                "lifecycle_phase": lifecycle,
                "domains": ["software-engineering"],
                "languages": [],
                "frameworks": [],
                "required_capabilities": ["implementation" if index == 1 else "review"],
                "authority": "modify" if index < 3 else "review",
                "mutation_scope": "workspace_write" if index < 3 else "read_only",
                "risks": [],
                "trust_boundaries": ["repository"],
                "claims": [],
                "depends_on": [],
                "resources": ["repository"],
                "required_tools": [],
                "platforms": ["windows"],
                "acceptance_evidence": ["evaluation evidence"],
                "parallelization": "unspecified",
            }
        )
        selected = (case.required_workers[index - 1],)
        verified.append(
            VerifiedUnitStaffing(
                unit_id,
                selected,
                "delegate",
                "immediate" if index == 1 else "after_artifact",
                ((selected[0], f"context-{index}"),),
                (),
                (),
            )
        )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": case.request,
            "units": units,
        }
    )
    return WorkforceRoutingOutcome(
        "accepted",
        "balanced",
        "inferred",
        plan,
        None,
        StaffingDecision("accepted", tuple(verified), ()),
        (
            WorkforceInferenceAttempt(
                "planner",
                "task-agency-router",
                "litellm",
                "workforce-model",
                "task-agency-router",
                "resolved-model",
                "response.body.model",
                "applied",
                "structured_response_applied",
                12,
            ),
        ),
        (),
        1,
    )


def test_configured_inference_eval_grades_required_team_and_bounds_calls() -> None:
    snapshot = WorkforceIndexSnapshot(
        7,
        272,
        (),
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
        "{}",
    )
    calls: list[str] = []

    def router(request, _snapshot, **_kwargs):
        calls.append(request)
        return _accepted_outcome()

    config = AgencyConfig(workforce=WorkforceConfig(mode="balanced", balanced_call_budget=4))
    report = run_workforce_inference_eval(
        snapshot,
        config=config,
        context=StaffingContext("codex", "windows", frozenset(), 7),
        cases=(CASES[0],),
        router=router,
    )

    assert report["schema"] == SCHEMA
    assert report["version"] == VERSION
    assert report["passed"] is True
    assert report["passed_count"] == 1
    assert report["maximum_provider_calls"] == 4
    assert report["details"][0]["selected_workers"] == list(CASES[0].required_workers)
    assert len(report["details"][0]["plan_units"]) == len(CASES[0].required_artifacts)
    assert calls == [CASES[0].request]


def test_runtime_routing_failure_case_rejects_business_wrong_neighbors() -> None:
    case = next(item for item in CASES if item.case_id == "runtime-routing-integration-failure")

    assert "application-integration-verifier" in case.required_workers
    assert "selection-safety-critic" in case.required_workers
    assert "test-results-analyzer" in case.required_workers
    assert {"business-strategist", "financial-analyst"} <= set(case.forbidden_workers)
    assert {"review-report", "test-evidence"} <= set(case.required_artifacts)


def test_security_patch_case_requires_discovery_code_and_security_review() -> None:
    case = next(item for item in CASES if item.case_id == "repository-security-patch-review")

    assert case.required_workers == (
        "codebase-onboarding-engineer",
        "code-reviewer",
        "ai-generated-code-security-auditor",
    )
    assert {"business-strategist", "technical-writer"} <= set(case.forbidden_workers)
    assert case.required_artifacts == ("review-report",)
    assert case.required_lifecycles == ("discovery", "review")


def test_configured_inference_eval_rejects_deterministic_fallback_success() -> None:
    snapshot = WorkforceIndexSnapshot(
        7,
        272,
        (),
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
        "{}",
    )

    def router(_request, _snapshot, **_kwargs):
        return replace(_accepted_outcome(), inference_mode="deterministic")

    report = run_workforce_inference_eval(
        snapshot,
        config=AgencyConfig(),
        context=StaffingContext("codex", "windows", frozenset(), 7),
        cases=(CASES[0],),
        router=router,
    )

    detail = report["details"][0]
    assert report["passed"] is False
    assert detail["inference_applied"] is False
    assert detail["missing_workers"] == []
    assert detail["model_attempts"][0]["validation_detail"] == ""


def test_live_workforce_eval_requires_explicit_cost_confirmation() -> None:
    with pytest.raises(ValueError, match="RUN LIVE WORKFORCE EVAL"):
        cmd_eval_workforce(
            Namespace(
                confirm_live_inference="",
                host="codex",
                platform="windows",
                available_tool=[],
                all=False,
                no_details=False,
                json=False,
            )
        )


def test_live_workforce_eval_canonicalizes_tool_aliases() -> None:
    context = _eval_staffing_context(
        Namespace(
            host="codex",
            platform="windows",
            available_tool=["repository", "shell", "test-runner", "package-manager"],
        ),
        19,
    )

    assert context.available_tools == frozenset(
        {"repository-read", "shell-execution", "test-execution", "package-management"}
    )
    assert context.roster_generation == 19


def test_live_workforce_eval_rejects_unknown_tool_aliases() -> None:
    with pytest.raises(ValueError, match="unknown --available-tool capability: filesystem"):
        _eval_staffing_context(
            Namespace(
                host="codex",
                platform="windows",
                available_tool=["filesystem"],
            ),
            19,
        )


def test_live_workforce_eval_rejects_empty_roster_before_provider_calls(
    monkeypatch,
) -> None:
    import agency_runtime.cli.eval_commands as subject

    empty = WorkforceIndexSnapshot(
        0,
        0,
        (),
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
        "{}",
    )
    monkeypatch.setattr(subject, "Store", lambda: object())
    monkeypatch.setattr(subject, "load_config", AgencyConfig)
    monkeypatch.setattr(subject, "configured_workforce_providers", lambda *_a, **_k: (object(),))
    monkeypatch.setattr(subject, "workforce_index_snapshot", lambda _store: empty)
    with pytest.raises(ValueError, match="populated audited workforce"):
        cmd_eval_workforce(
            Namespace(
                confirm_live_inference="RUN LIVE WORKFORCE EVAL",
                host="codex",
                platform="windows",
                available_tool=[],
                all=False,
                no_details=False,
                json=False,
            )
        )
