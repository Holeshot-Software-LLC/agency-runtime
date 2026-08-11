from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.evals.product_scenarios import product_scenario
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.selector.pipeline import _hireable_gap_units, route
from agency_runtime.core.selector.receipt_projection import project_durable_routing_receipt
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce import hiring as hiring_module
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
)
from agency_runtime.core.workforce.hiring import (
    apply_approved_hiring_case,
    commit_pending_contractor_hiring,
    hire_contractor_for_gap,
    restaff_after_hire,
)
from agency_runtime.core.workforce.inference import (
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit, parse_work_unit_plan
from agency_runtime.core.workforce.staffing_verifier import (
    AbstentionReason,
    StaffingBudget,
    StaffingContext,
    build_deterministic_proposal,
    verify_staffing,
)

_HASH = "sha256:" + "a" * 64


def _install_existing(store: Store) -> WorkforceContract:
    content = "Independently review software build changes and report evidence."
    digest = "sha256:" + hashlib.sha256(content.encode()).hexdigest()
    agent = {
        "slug": "general-build-reviewer",
        "name": "General Build Reviewer",
        "display_name": "General Build Reviewer",
        "division": "engineering",
        "description": "Independently reviews ordinary software build changes.",
        "categories": ["software-engineering", "review"],
        "capabilities": ["build-review", "review"],
        "task_types": ["review"],
        "artifact_kinds": ["review-report"],
        "lifecycle_phases": ["review"],
        "domains": ["software-engineering"],
        "authority": "review",
        "context_mode": "isolated_only",
        "required_tools": ["repository-read"],
        "tool_classes": ["repository-read"],
        "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
        "supported_platforms": ["windows", "linux"],
        "scope_qualifiers": ["general build review"],
        "not_for": ["quantum compiler implementation"],
        "composition": {"independence_class": "build-review"},
        "audit_status": "approved",
        "audit_revision": "fixture-v1",
        "routing_contract_valid": True,
        "version": "1.0.0",
        "hash": digest,
        "version_hash": digest,
        "prompt_body": content,
        "source": "fixture",
        "source_version": "fixture-v1",
        "origin": "upstream",
        "employment": "employee",
        "enabled": True,
    }
    store._activate_prevalidated_agent(agent)
    return workforce_index_snapshot(store, disabled_agents=()).contracts[0]


def _existing(*, enabled: bool = True) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id="worker:general-build-reviewer",
        agent_id="general-build-reviewer",
        display_name="General Build Reviewer",
        archetype="reviewer",
        outcomes=("build review",),
        capability_ids=("review",),
        artifact_kinds=("review-report",),
        lifecycle_phases=("review",),
        domains=("software-engineering",),
        stacks=(),
        scope_qualifiers=("general build review",),
        not_for=("quantum compiler implementation",),
        authority="review",
        context_mode="isolated_only",
        tool_classes=("repository-read",),
        hosts=("codex", "claude", "openclaw", "hermes"),
        platforms=("windows", "linux"),
        composition=CompositionContract(independence_class="build-review"),
        audit=AuditContract(status="approved", revision="1", contract_valid=True),
        version=_HASH,
        version_hash=_HASH,
        enabled=enabled,
        employment="employee" if enabled else "disabled",
        origin="upstream",
    )


def _unit() -> WorkUnit:
    return WorkUnit(
        unit_id="unit-quantum-build",
        outcome="Implement a portable quantum compiler build plugin",
        artifact_kind="implementation-change",
        lifecycle_phase="implementation",
        domains=("quantum-build-systems",),
        languages=("typescript",),
        frameworks=(),
        required_capabilities=("implementation",),
        authority="modify",
        mutation_scope="workspace_write",
        risks=("build-regression",),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(),
        resources=("repository",),
        required_tools=("repository-read",),
        platforms=("windows", "linux"),
        acceptance_evidence=("plugin builds on Windows and Linux",),
        parallelization="unspecified",
    )


def _contract(*, external_mutation: bool = False) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "slug": "quantum-build-engineer",
        "role": "Quantum Build Engineer",
        "narrow_scope": "Portable TypeScript build plugins for quantum compiler toolchains.",
        "outcomes_owned": ["quantum-build-implementation"],
        "artifacts_produced": ["implementation-change"],
        "capabilities": ["quantum-build-systems", "implementation"],
        "anti_capabilities": ["General product architecture is outside this role."],
        "preferred_scenarios": ["A quantum compiler needs portable TypeScript build integration."],
        "avoided_scenarios": ["Generic frontend feature implementation."],
        "forbidden_scenarios": ["Production deployment approval."],
        "lifecycle_phases": ["implementation"],
        "authority": "modify",
        "context_mode": "isolated_only",
        "external_mutation": external_mutation,
        "tools": ["repository-read"],
        "platforms": ["windows", "linux"],
        "hosts": ["codex", "claude", "openclaw", "hermes"],
        "requirements": ["Operate only on the assigned build plugin."],
        "relationships": [],
        "evidence_requirements": ["Windows and Linux build evidence."],
        "closest_workers": [
            {
                "worker": "general-build-reviewer",
                "insufficiency": "Reviews generic builds but cannot implement the quantum plugin.",
                "differentiation": "Owns narrow TypeScript quantum compiler build implementation.",
            }
        ],
        "positive_evaluations": [
            {
                "case_id": "positive-quantum-build",
                "scenario": "Implement the cross-platform quantum compiler build plugin.",
                "expectation": "select",
                "rationale": "The requested artifact is the contractor's narrow specialty.",
            }
        ],
        "hard_negative_evaluations": [
            {
                "case_id": "negative-generic-review",
                "scenario": "Review a standard web application build configuration.",
                "expectation": "select_other",
                "rationale": "A general build reviewer is the safer specialist.",
            }
        ],
    }


def _hiring_response(*, disabled: bool = False, external_mutation: bool = False) -> dict[str, Any]:
    return {
        "action": "hire",
        "decision_reason": "The complete workforce lacks the narrow implementation capability.",
        "gap_evidence": {
            "gap_proven": True,
            "uncovered_work_unit": "unit-quantum-build",
            "missing_capabilities": ["quantum-build-systems"],
            "nearest_workers": [
                {
                    "agent_id": "general-build-reviewer",
                    "insufficiency": "Review authority cannot implement this specialized plugin.",
                    "overlap_score": 0.31,
                }
            ],
            "disabled_covering_workers": ["general-build-reviewer"] if disabled else [],
            "required_scope": "Narrow portable quantum compiler build plugin implementation.",
            "expected_reuse": "Reusable for future quantum compiler packages.",
        },
        "duplicate_evidence": {
            "decision": "hire",
            "closest_workers": ["general-build-reviewer"],
            "maximum_overlap": 0.31,
            "coherent_amendment_target": "",
            "reason": "Authority and domain differ, so amendment would be incoherent.",
        },
        "contract": _contract(external_mutation=external_mutation),
    }


def _photonic_unit() -> WorkUnit:
    return replace(
        _unit(),
        unit_id="unit-photonic-build",
        outcome="Implement a portable photonic compiler build plugin",
        domains=("photonic-build-systems",),
        acceptance_evidence=("photonic plugin builds on Windows and Linux",),
    )


def _hiring_response_for(unit: WorkUnit) -> dict[str, Any]:
    if unit.unit_id == _unit().unit_id:
        return _hiring_response()
    response = deepcopy(_hiring_response())
    response["gap_evidence"].update(
        uncovered_work_unit=unit.unit_id,
        missing_capabilities=["photonic-build-systems"],
        required_scope="Narrow portable photonic compiler build plugin implementation.",
        expected_reuse="Reusable for future photonic compiler packages.",
    )
    contract = response["contract"]
    contract.update(
        slug="photonic-build-engineer",
        role="Photonic Build Engineer",
        narrow_scope="Portable TypeScript build plugins for photonic compiler toolchains.",
        outcomes_owned=["photonic-build-implementation"],
        capabilities=["photonic-build-systems", "implementation"],
        preferred_scenarios=["A photonic compiler needs portable TypeScript build integration."],
    )
    return response


def _amendment_unit() -> WorkUnit:
    return replace(
        _unit(),
        unit_id="unit-quantum-review",
        outcome="Review a portable quantum compiler build plugin",
        artifact_kind="review-report",
        lifecycle_phase="review",
        required_capabilities=("review",),
        authority="review",
        mutation_scope="read_only",
        acceptance_evidence=("quantum build review report",),
    )


def _amendment_response(
    *,
    authority: str = "review",
    external_mutation: bool = False,
) -> dict[str, Any]:
    contract = _contract()
    contract.update(
        slug="general-build-reviewer",
        role="Quantum Build Reviewer Extension",
        outcomes_owned=["quantum-build-review"],
        artifacts_produced=["review-report"],
        capabilities=["quantum-build-systems", "review"],
        lifecycle_phases=["review"],
        authority=authority,
        external_mutation=external_mutation,
        closest_workers=[
            {
                "worker": "general-build-reviewer",
                "insufficiency": "The current scope lacks quantum compiler build review.",
                "differentiation": "Adds only the missing quantum build review specialization.",
            }
        ],
    )
    return {
        "action": "amend",
        "decision_reason": "The nearest worker can coherently absorb the narrow review gap.",
        "gap_evidence": {
            "gap_proven": True,
            "uncovered_work_unit": "unit-quantum-review",
            "missing_capabilities": ["quantum-build-systems"],
            "nearest_workers": [
                {
                    "agent_id": "general-build-reviewer",
                    "insufficiency": "Its current review scope excludes quantum compiler builds.",
                    "overlap_score": 0.78,
                }
            ],
            "disabled_covering_workers": [],
            "required_scope": "Narrow quantum compiler build review.",
            "expected_reuse": "Reusable for future quantum build reviews.",
        },
        "duplicate_evidence": {
            "decision": "amend",
            "closest_workers": ["general-build-reviewer"],
            "maximum_overlap": 0.78,
            "coherent_amendment_target": "general-build-reviewer",
            "reason": "The authority, artifact, lifecycle, and review identity remain unchanged.",
        },
        "contract": contract,
    }


def _config(*, provider_type: str = "litellm") -> AgencyConfig:
    provider = ProviderEntry(
        name="task-agency-router",
        type=provider_type,
        transport="codex" if provider_type == "cli" else "",
        model="hiring-model",
        base_url="https://router.example.test/v1" if provider_type != "cli" else "",
        api_key="secret" if provider_type != "cli" else "",
        timeout=5,
    )
    return AgencyConfig(
        providers=(provider,),
        workforce=replace(
            WorkforceConfig(),
            provider="task-agency-router",
            max_hires_per_day=3,
        ),
    )


def _result(value: dict[str, Any], provider: ProviderEntry) -> StructuredProviderResult:
    actual = "resolved-hiring-model" if provider.type != "cli" else ""
    return StructuredProviderResult(
        value=value,
        provider_name=provider.name,
        provider_type=provider.type,
        transport=provider.transport,
        requested_model=provider.model,
        model_group=provider.model if provider.type == "litellm" else "",
        actual_model=actual,
        model_receipt_source="response.body.model" if actual else "unavailable",
        latency_ms=11,
    )


_SAFE_SECURITY_REVIEW = {
    "verdict": "safe",
    "reasons": [],
    "required_changes": [],
    "same_provider_as_creator_warning": False,
}


def _invoker(
    hiring: dict[str, Any],
    critic: dict[str, Any],
    security: dict[str, Any] | None = None,
):
    responses = iter((hiring, critic, security or _SAFE_SECURITY_REVIEW))

    def invoke(provider, _prompt, _schema, **_kwargs):
        return _result(next(responses), provider)

    return invoke


def _recording_invoker(
    *responses: dict[str, Any],
    calls: list[dict[str, str]],
):
    pending = iter(responses)

    def invoke(provider, prompt, _schema, **kwargs):
        calls.append(
            {
                "prompt": prompt,
                "system_prompt": str(kwargs.get("system_prompt") or ""),
            }
        )
        try:
            value = next(pending)
        except StopIteration:
            value = _SAFE_SECURITY_REVIEW
        return _result(value, provider)

    return invoke


def test_inferred_gap_hires_registers_and_immediately_enables_contractor(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )

    assert outcome.hired is True
    assert outcome.worker["state"] == "contractor"
    assert outcome.worker["agent_slug"] == "quantum-build-engineer"
    assert outcome.hiring_case["status"] == "applied"
    assert store.get_roster_entry("quantum-build-engineer") is not None
    assert "Hired Contractor · Quantum Build Engineer" in outcome.notification
    assert [item.stage for item in outcome.attempts] == [
        "hiring",
        "hiring-critic",
        "security_review",
    ]


def test_hiring_prompts_preserve_instruction_and_mutation_boundaries(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    calls: list[dict[str, str]] = []

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_recording_invoker(
            _hiring_response(),
            {"approved": True, "reason_codes": []},
            calls=calls,
        ),
    )

    assert outcome.hired is True
    assert "Never write executable instructions" in calls[0]["system_prompt"]
    assert "external_mutation is true only for external_write" in calls[0]["system_prompt"]
    assert "explicit prohibitions are not granted authority" in calls[1]["system_prompt"]


def test_critic_can_independently_validate_runtime_gap_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    calls = 0

    def invoke(provider, prompt, _schema, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(_hiring_response(), provider)
        if "safety reviewer" in str(_kwargs.get("system_prompt") or ""):
            return _result(_SAFE_SECURITY_REVIEW, provider)
        document = json.loads(prompt)
        evidence = document.get("runtime_gap_evidence", {})
        workforce = evidence.get("complete_workforce", [])
        verified = evidence.get("verified_gap", {})
        approved = bool(
            verified.get("inference_declared") is True
            and verified.get("hiring_admitted") is True
            and verified.get("reason_codes")
            == [
                "inference_declared_gap",
                "no_safe_sufficient_team",
                "recruiter_abstained",
            ]
            and verified.get("typed_requirements")
            == [
                "artifact:implementation-change",
                "lifecycle:implementation",
                "domain:quantum-build-systems",
                "stack:typescript",
                "capability:implementation",
                "authority:modify",
            ]
            and verified.get("eligible_coverage") == []
            and set(verified.get("uncovered_requirements", ()))
            == set(verified.get("typed_requirements", ()))
            and verified.get("coverage_rows") == []
            and verified.get("coverage_row_count") == 0
            and verified.get("coverage_rows_complete") is True
            and evidence.get("workforce_count") == 1
            and len(workforce) == 1
            and workforce[0].get("agent_id") == "general-build-reviewer"
        )
        return _result(
            {
                "approved": approved,
                "reason_codes": [] if approved else ["gap_not_independently_verified"],
            },
            provider,
        )

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (replace(_existing(), stacks=("cobol",)),),
        store=store,
        config=_config(),
        gap_reason_codes=(
            "inference_declared_gap",
            "no_safe_sufficient_team",
            "recruiter_abstained",
        ),
        invoker=invoke,
    )

    assert outcome.hired is True
    assert calls == 3


def test_verified_gap_projection_excludes_ineligible_partial_coverage(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    partial = replace(_existing(), artifact_kinds=("implementation-change",), stacks=("cobol",))
    calls: list[dict[str, str]] = []

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (partial,),
        store=store,
        config=_config(),
        staffing_context=StaffingContext(
            "codex",
            "windows",
            frozenset({"repository-read"}),
            1,
        ),
        gap_reason_codes=(
            "inference_declared_gap",
            "no_safe_sufficient_team",
            "recruiter_abstained",
        ),
        invoker=_recording_invoker(
            _hiring_response(),
            {"approved": True, "reason_codes": []},
            calls=calls,
        ),
    )

    assert outcome.hired is True
    verified = json.loads(calls[1]["prompt"])["runtime_gap_evidence"]["verified_gap"]
    assert verified["eligibility_context_available"] is True
    assert verified["eligible_coverage"] == []
    assert set(verified["uncovered_requirements"]) == set(verified["typed_requirements"])
    assert verified["coverage_row_count"] == 1
    assert verified["coverage_rows_complete"] is True
    assert verified["coverage_rows"] == [
        {
            "agent_id": "general-build-reviewer",
            "covers": ["artifact:implementation-change"],
            "execution_eligible": False,
            "ineligibility_reasons": [
                "agent_authority_mismatch",
                "agent_domain_mismatch",
                "agent_stack_mismatch",
                "agent_capability_mismatch",
                "agent_explicitly_out_of_scope",
            ],
        }
    ]
    unobserved = hiring_module._verified_gap_projection(
        _unit(),
        (partial,),
        reason_codes=("inference_declared_gap",),
        staffing_context=None,
    )
    assert unobserved["eligibility_context_available"] is False
    assert unobserved["eligible_coverage"] == []
    assert unobserved["coverage_rows"][0]["execution_eligible"] is None


def test_critic_rejection_gets_one_inferred_replacement_and_fresh_approval(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    rejected = _hiring_response()
    rejected["contract"]["narrow_scope"] = "Rejected candidate private marker."
    replacement = deepcopy(_hiring_response())
    replacement["contract"].update(
        slug="quantum-build-integration-specialist",
        role="Quantum Build Integration Specialist",
        narrow_scope="Portable quantum compiler build integration for the assigned plugin.",
    )
    calls: list[dict[str, str]] = []

    request = "Implement the missing quantum compiler build integration. RAW-REQUEST-MARKER"
    outcome = hire_contractor_for_gap(
        request,
        _unit(),
        (replace(_existing(), stacks=("cobol",)),),
        store=store,
        config=_config(),
        gap_reason_codes=(
            "inference_declared_gap",
            "no_safe_sufficient_team",
            "recruiter_abstained",
        ),
        invoker=_recording_invoker(
            rejected,
            {
                "approved": False,
                "reason_codes": [
                    "authority_scope_is_incoherent_or_overbroad",
                    "relationship_dependencies_are_underspecified",
                ],
            },
            replacement,
            {"approved": True, "reason_codes": []},
            calls=calls,
        ),
    )

    assert outcome.hired is True
    assert outcome.worker["agent_slug"] == "quantum-build-integration-specialist"
    assert [item.stage for item in outcome.attempts] == [
        "hiring",
        "hiring-critic",
        "hiring-repair",
        "hiring-repair-critic",
        "security_review",
    ]
    repair_prompt = json.loads(calls[2]["prompt"])
    assert repair_prompt["critic_feedback"]["reason_codes"] == [
        "authority_scope_is_incoherent_or_overbroad",
        "relationship_dependencies_are_underspecified",
    ]
    assert repair_prompt["replacement_required"] is True
    assert "Rejected candidate private marker" not in calls[2]["prompt"]
    assert "only replacement attempt" in calls[2]["system_prompt"]
    for critic_call in (calls[1], calls[3]):
        critic_prompt = json.loads(critic_call["prompt"])
        verified_gap = critic_prompt["runtime_gap_evidence"]["verified_gap"]
        assert verified_gap["inference_declared"] is True
        assert verified_gap["hiring_admitted"] is True
        assert verified_gap["reason_codes"] == [
            "inference_declared_gap",
            "no_safe_sufficient_team",
            "recruiter_abstained",
        ]
        assert set(verified_gap["uncovered_requirements"]) == set(
            verified_gap["typed_requirements"]
        )
        assert verified_gap["coverage_rows"] == []
        assert verified_gap["coverage_row_count"] == 0
        assert verified_gap["coverage_rows_complete"] is True
        assert critic_prompt["runtime_gap_evidence"]["workforce_count"] == 1
        assert [
            item["agent_id"] for item in critic_prompt["runtime_gap_evidence"]["complete_workforce"]
        ] == ["general-build-reviewer"]
        assert "RAW-REQUEST-MARKER" not in critic_call["prompt"]
        assert "runtime_gap_evidence" in critic_call["system_prompt"]
    assert [item["stage"] for item in outcome.hiring_case["model_evidence"]["receipts"]] == [
        "hiring",
        "hiring-critic",
        "hiring-repair",
        "hiring-repair-critic",
        "security_review",
    ]


def test_product_request_gap_repair_receives_live_reason_family_and_typed_proof(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    request = product_scenario("python-cli-service").prompt(trial_id="ar219-5c45f15-readme-01")
    rejected = _hiring_response()
    replacement = deepcopy(_hiring_response())
    replacement["contract"]["relationships"] = []
    replacement["contract"]["evidence_requirements"] = [
        "Windows and Linux build evidence.",
        "The assigned acceptance check passes in the isolated workspace.",
    ]
    calls: list[dict[str, str]] = []
    live_reasons = [
        "relationships_not_coherent",
        "acceptance_evidence_insufficient",
        "gap_not_independently_proven",
    ]

    outcome = hire_contractor_for_gap(
        request,
        _unit(),
        (replace(_existing(), stacks=("cobol",)),),
        store=store,
        config=_config(),
        gap_reason_codes=(
            "inference_declared_gap",
            "no_safe_sufficient_team",
            "recruiter_abstained",
        ),
        invoker=_recording_invoker(
            rejected,
            {"approved": False, "reason_codes": live_reasons},
            replacement,
            {"approved": True, "reason_codes": []},
            calls=calls,
        ),
    )

    assert outcome.hired is True
    repair_prompt = json.loads(calls[2]["prompt"])
    assert repair_prompt["critic_feedback"]["reason_codes"] == live_reasons
    original_input = repair_prompt["original_hiring_input"]
    assert original_input["request"] == request
    verified = original_input["verified_gap"]
    assert verified["hiring_admitted"] is True
    assert set(verified["uncovered_requirements"]) == set(verified["typed_requirements"])
    assert verified["coverage_row_count"] == 0
    assert verified["coverage_rows_complete"] is True
    assert "relationships must be empty unless" in calls[2]["system_prompt"]
    assert "every work-unit acceptance check" in calls[2]["system_prompt"]
    assert "For relationship-coherence codes, remove speculative" in calls[2]["system_prompt"]
    assert "For acceptance-evidence codes, bind evidence requirements" in calls[2]["system_prompt"]
    assert (
        "For independent-gap codes, use original_hiring_input.verified_gap"
        in calls[2]["system_prompt"]
    )
    assert "original_hiring_input.verified_gap" in calls[2]["system_prompt"]
    assert "raw recruiter content is neither available nor required" in calls[3]["system_prompt"]


def test_two_call_budget_never_starts_an_uncriticizable_replacement(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    config = _config()
    config = replace(
        config,
        workforce=replace(config.workforce, hiring_call_budget=2),
    )
    calls: list[dict[str, str]] = []

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=config,
        invoker=_recording_invoker(
            _hiring_response(),
            {"approved": False, "reason_codes": ["authority_scope_is_overbroad"]},
            _hiring_response(),
            {"approved": True, "reason_codes": []},
            calls=calls,
        ),
    )

    assert outcome.status == "rejected"
    assert outcome.reason_codes == ("authority_scope_is_overbroad",)
    assert [item.stage for item in outcome.attempts] == ["hiring", "hiring-critic"]
    assert len(calls) == 2
    assert store.list_hiring_cases(limit=10) == []
    assert store.list_workforce_workers(limit=10) == []


def test_second_critic_rejection_is_terminal_content_free_and_mutation_free(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    replacement = deepcopy(_hiring_response())
    replacement["contract"].update(
        slug="quantum-build-integration-specialist",
        role="Quantum Build Integration Specialist",
    )
    calls: list[dict[str, str]] = []

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_recording_invoker(
            _hiring_response(),
            {"approved": False, "reason_codes": ["authority_scope_is_overbroad"]},
            replacement,
            {
                "approved": False,
                "reason_codes": ["REMAINING_SCOPE_GAP", "private critic prose"],
            },
            calls=calls,
        ),
    )

    assert outcome.status == "rejected"
    assert outcome.reason_codes == ("remaining_scope_gap",)
    assert [item.stage for item in outcome.attempts] == [
        "hiring",
        "hiring-critic",
        "hiring-repair",
        "hiring-repair-critic",
    ]
    assert len(calls) == 4
    assert store.list_hiring_cases(limit=10) == []
    assert store.list_workforce_workers(limit=10) == []


def test_hire_binds_natural_language_contract_to_exact_causing_unit(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    response["contract"].update(
        artifacts_produced=["USB diagnostic report"],
        lifecycle_phases=["review"],
        capabilities=["windows-usb-diagnostics"],
        tools=["system-event-log"],
        platforms=["linux"],
        hosts=["openclaw"],
        anti_capabilities=["Do not change drivers without human approval."],
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset({"repository-read"}),
        1,
    )

    outcome = hire_contractor_for_gap(
        "Investigate recurring USB connect and disconnect sounds on this Windows computer.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        staffing_context=context,
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.hired is True
    contract = outcome.hiring_case["contract_evidence"]
    assert contract["artifact_kinds"][0] == "implementation-change"
    assert contract["lifecycle_phases"][0] == "implementation"
    assert contract["capability_ids"] == ["implementation"]
    assert contract["tool_classes"][0] == "repository-read"
    assert contract["platforms"][0] == "windows"
    assert contract["hosts"][0] == "codex"
    assert outcome.contract.anti_capabilities == ("do not change drivers without human approval.",)


def test_hire_compiles_schema_maximum_lists_into_bounded_workforce_contract(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    contract = response["contract"]
    contract.update(
        outcomes_owned=[f"owned-outcome-{index}" for index in range(12)],
        artifacts_produced=[f"artifact-{index}" for index in range(12)],
        capabilities=[f"capability-{index}" for index in range(12)],
        preferred_scenarios=[f"Preferred scenario {index}." for index in range(12)],
        avoided_scenarios=[f"Avoided scenario {index}." for index in range(12)],
        forbidden_scenarios=[f"Forbidden scenario {index}." for index in range(12)],
        tools=[f"tool-{index}" for index in range(12)],
    )

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.hired is True
    compiled = outcome.hiring_case["contract_evidence"]
    assert len(compiled["outcomes"]) == 8
    assert len(compiled["artifact_kinds"]) == 8
    assert len(compiled["tool_classes"]) == 8
    assert len(compiled["scope_qualifiers"]) == 4
    assert len(compiled["not_for"]) == 4
    assert compiled["artifact_kinds"][0] == "implementation-change"
    assert compiled["capability_ids"] == ["implementation"]
    assert compiled["tool_classes"][0] == "repository-read"


def test_hire_bounds_unicode_routing_projection_but_preserves_employment_contract(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    contract = response["contract"]
    full_prose = "é" * 160
    full_role = "É" * 100
    contract.update(
        role=full_role,
        outcomes_owned=[full_prose],
        preferred_scenarios=[full_prose],
        avoided_scenarios=[full_prose],
        forbidden_scenarios=[full_prose],
    )

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.hired is True
    evidence = outcome.hiring_case
    assert evidence is not None
    employment = evidence["critic_evidence"]["employment_contract"]
    workforce = evidence["contract_evidence"]
    assert employment["outcomes_owned"] == [full_prose]
    assert employment["role"] == full_role
    assert len(workforce["outcomes"][0].encode("utf-8")) <= 192
    assert len(workforce["scope_qualifiers"][0].encode("utf-8")) <= 192
    assert len(workforce["not_for"][0].encode("utf-8")) <= 192
    assert len(workforce["display_name"].encode("utf-8")) <= 128


@pytest.mark.parametrize(
    ("validation_error", "expected"),
    [
        (
            "workforce outcomes exceeds 8 items provider-secret",
            "contract_invalid:workforce_projection:outcomes",
        ),
        (
            "unexpected projection failure provider-secret",
            "contract_invalid:workforce_projection",
        ),
    ],
)
def test_hire_reports_content_free_workforce_projection_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    validation_error: str,
    expected: str,
) -> None:
    store = Store(tmp_path / "agency.db")

    def reject_projection(*_args, **_kwargs):
        raise ValueError(validation_error)

    monkeypatch.setattr(hiring_module, "project_workforce_contract", reject_projection)
    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == (expected,)
    assert "provider-secret" not in " ".join(outcome.reason_codes)
    assert store.list_hiring_cases(limit=10) == []


def test_hire_rejects_relationship_targets_unknown_to_the_roster(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    response["contract"]["relationships"] = [
        {"kind": "must_follow", "target": "nonexistent-review-gate"}
    ]

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == ("contract_invalid:relationship_target_unknown",)
    assert store.list_hiring_cases(limit=10) == []


def test_hire_accepts_relationship_targets_present_in_the_roster(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    response["contract"]["relationships"] = [
        {"kind": "must_follow", "target": "general-build-reviewer"}
    ]

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.hired is True


def test_hire_reports_content_free_employment_revalidation_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    def reject_revalidation(*_args, **_kwargs):
        raise ValueError("provider-secret")

    monkeypatch.setattr(hiring_module, "compile_contractor", reject_revalidation)
    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == ("contract_invalid:employment_revalidation",)
    assert "provider-secret" not in " ".join(outcome.reason_codes)


def test_atomic_preflight_route_does_not_publish_an_in_memory_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline

    monkeypatch.setattr(
        pipeline,
        "_remember_routing",
        lambda *_args, **_kwargs: pytest.fail("atomic preflight published a route cache entry"),
    )

    result = route(
        "atomic-preflight-session",
        "Review this implementation for correctness.",
        [],
        config=AgencyConfig(),
        trace_id="atomic-preflight-trace",
        host="codex",
        platform="windows",
        preflight_atomic=True,
    )

    assert result["trace_id"] == "atomic-preflight-trace"


def test_deferred_hire_commits_only_with_the_preflight_ready_cas(tmp_path: Path) -> None:
    from agency_runtime.core.preflight_recipe import _content_free_routing_recipe
    from agency_runtime.core.store import preflight as store_preflight

    store = Store(tmp_path / "agency.db")
    pending = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        defer_commit=True,
        session_id="session",
        trace_id="deferred-hire",
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )
    assert pending.pending_commit is not None
    assert store.list_hiring_cases(limit=10) == []
    assert store.get_roster_entry("quantum-build-engineer") is None

    started = store.begin_preflight_attempt(
        session_id="session",
        trace_id="deferred-hire",
        host="codex",
        request_fingerprint="a" * 64,
        request_kind="nontrivial",
    )
    routing = {
        "trace_id": "deferred-hire",
        "query_hash": "a" * 64,
        "context_fingerprint": "b" * 64,
        "status": "accepted",
        "source": "workforce_inference",
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 1.0,
        "latency_ms": 0,
        "work_units": {
            "delegate": False,
            "count": 1,
            "confidence": "high",
            "source": "verified-workforce-plan",
        },
        "workforce_unit_descriptors": [],
        "workforce_unit_bindings": [],
        "_pending_hiring_commits": [pending.pending_commit],
    }
    routing_recipe = _content_free_routing_recipe(routing, trace_id="deferred-hire")
    projected = store_preflight._project_routing_evidence(
        routing_recipe,
        trace_id="deferred-hire",
    )
    assert projected is not None
    recipe = {
        "recipe_version": 5,
        "policy_fingerprint": "c" * 64,
        "session_id": "session",
        "trace_id": "deferred-hire",
        "host": "codex",
        # `isolated` was deleted with its enforcement in d9f6e6be; `direct` is
        # the only mode `_project_preflight_recipe` accepts, and anything else
        # projects to None and reports as a mismatched replay recipe.
        "delivery_mode": "direct",
        "context_limit": 4_096,
        "routing": projected["decision"],
        "specialist_refs": [],
        "unit_assignment_agents": [],
        "unit_agent_plan": [],
        "trivial": False,
        "roster_size": 1,
    }
    ready_arguments = {
        "session_id": "session",
        "trace_id": "deferred-hire",
        "recipe": recipe,
        "host": "codex",
        "routing_evidence": routing_recipe,
        "specialist_refs": [],
    }
    assert store.mark_preflight_ready(
        **ready_arguments,
        attempt_token="stale-attempt",
    ) == {"outcome": "cas_lost"}
    assert store.list_hiring_cases(limit=10) == []
    assert store.get_roster_entry("quantum-build-engineer") is None

    committed = store.mark_preflight_ready(
        **ready_arguments,
        attempt_token=started["attempt_token"],
    )

    assert committed == {"outcome": "committed"}
    assert store.get_workforce_worker("quantum-build-engineer")["state"] == "contractor"
    assert store.list_hiring_cases(limit=10)[0]["status"] == "applied"
    connection = store._connect()
    try:
        receipt_count = connection.execute(
            "SELECT COUNT(*) FROM model_receipts WHERE trace_id = ?",
            ("deferred-hire",),
        ).fetchone()[0]
    finally:
        connection.close()
    assert receipt_count == 3


def test_deferred_hire_commits_even_when_daily_count_exceeds_old_limit(
    tmp_path: Path,
) -> None:
    """AR-241: the daily hire cap no longer rejects at commit time. A deferred
    hire commits successfully even when a competing hire already pushed the
    daily count past the old max_hires_per_day."""

    store = Store(tmp_path / "agency.db")
    config = replace(
        _config(),
        workforce=replace(_config().workforce, max_hires_per_day=1),
    )
    pending = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=config,
        defer_commit=True,
        session_id="deferred-session",
        trace_id="deferred-trace",
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )
    assert pending.pending_commit is not None

    competing = hire_contractor_for_gap(
        "Implement the missing photonic compiler build integration.",
        _photonic_unit(),
        (_existing(),),
        store=store,
        config=config,
        invoker=_invoker(
            _hiring_response_for(_photonic_unit()),
            {"approved": True, "reason_codes": []},
        ),
    )
    assert competing.hired is True

    # AR-241: no RuntimeError — the daily cap no longer rejects at commit.
    _case, worker = commit_pending_contractor_hiring(pending.pending_commit, store=store)
    assert worker is not None
    assert worker["agent_slug"] == "quantum-build-engineer"
    assert store.get_roster_entry("quantum-build-engineer") is not None


def test_disabled_covering_worker_prevents_duplicate_before_critic_or_write(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    calls = 0

    def invoke(provider, _prompt, _schema, **_kwargs):
        nonlocal calls
        calls += 1
        return _result(_hiring_response(disabled=True), provider)

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(enabled=False),),
        store=store,
        config=_config(),
        invoker=invoke,
    )

    assert outcome.reason_codes == ("disabled_worker_covers_gap",)
    assert calls == 1
    assert store.list_hiring_cases(limit=10) == []


@pytest.mark.parametrize(
    ("action", "gap_proven", "expected"),
    [
        ("abstain", True, "hiring_inference_abstained"),
        ("hire", False, "hiring_gap_disputed"),
    ],
)
def test_hiring_decline_preserves_its_decision_stage(
    tmp_path: Path,
    action: str,
    gap_proven: bool,
    expected: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    response["action"] = action
    response["gap_evidence"]["gap_proven"] = gap_proven
    if action == "abstain":
        response["contract"] = None

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        gap_reason_codes=("inference_declared_gap", "no_safe_sufficient_team"),
        invoker=lambda provider, *_args, **_kwargs: _result(response, provider),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == (expected,)
    assert len(outcome.attempts) == 1
    assert store.list_hiring_cases(limit=10) == []


def test_amend_first_default_amends_near_match_above_threshold(tmp_path: Path) -> None:
    """AR-240: the amend-first default amends a near-match whose overlap is
    above the threshold, rather than rejecting it. The existing worker's
    revision is bumped and no duplicate is created."""

    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)

    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        invoker=_invoker(
            _amendment_response(),
            {"approved": True, "reason_codes": []},
            _SAFE_SECURITY_REVIEW,
        ),
    )

    assert outcome.status == "amended"
    assert outcome.reason_codes == ()
    assert len(store.list_workforce_workers(limit=10)) == 1
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 1


def test_amend_first_below_threshold_falls_through_to_hire(tmp_path: Path) -> None:
    """AR-240: when the overlap is below the threshold, the amendment falls
    through to the standard hire path. The recruiter's duplicate_evidence
    decision stays amend but the low overlap makes the amendment incoherent,
    so the candidate is treated as a distinct hire."""

    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    # A distinct hire contract with a low-overlap amend proposal: the model
    # proposed amend but the overlap is below threshold, so we fall through.
    response = _hiring_response()
    response["action"] = "amend"
    response["duplicate_evidence"] = {
        "decision": "amend",
        "closest_workers": ["general-build-reviewer"],
        "maximum_overlap": 0.4,
        "coherent_amendment_target": "general-build-reviewer",
        "reason": "Low overlap; amendment is incoherent.",
    }

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (existing,),
        store=store,
        config=_config(),
        invoker=_invoker(
            response,
            {"approved": True, "reason_codes": []},
            _SAFE_SECURITY_REVIEW,
        ),
    )

    assert outcome.status == "hired"
    assert outcome.worker["agent_slug"] == "quantum-build-engineer"


def test_amendment_binds_model_extension_slug_to_inferred_target(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    response = _amendment_response()
    response["contract"]["slug"] = "quantum-build-review-extension"

    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        allow_existing_worker_amendment=True,
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "amended"
    assert outcome.contract is not None
    assert outcome.contract.slug == existing.agent_id
    assert outcome.hiring_case["proposed_slug"] == existing.agent_id
    assert outcome.worker["agent_slug"] == existing.agent_id
    assert len(store.list_workforce_workers(limit=10)) == 1


def test_amendment_preserves_existing_values_inside_smaller_workforce_bounds(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    response = _amendment_response()
    response["contract"].update(
        outcomes_owned=[f"owned-outcome-{index}" for index in range(12)],
        artifacts_produced=["review-report", *(f"artifact-{index}" for index in range(11))],
        capabilities=["review", *(f"capability-{index}" for index in range(11))],
        preferred_scenarios=[f"Preferred scenario {index}." for index in range(12)],
        avoided_scenarios=[f"Avoided scenario {index}." for index in range(12)],
        forbidden_scenarios=[f"Forbidden scenario {index}." for index in range(12)],
        tools=["repository-read", *(f"tool-{index}" for index in range(11))],
    )

    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        allow_existing_worker_amendment=True,
        invoker=_invoker(response, {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "amended"
    amended = outcome.hiring_case["contract_evidence"]
    employment = outcome.hiring_case["critic_evidence"]["employment_contract"]
    assert len(employment["outcomes_owned"]) == 12
    assert len(employment["preferred_scenarios"]) == 12
    assert len(employment["avoided_scenarios"]) == 12
    assert len(employment["forbidden_scenarios"]) == 12
    assert len(amended["outcomes"]) == 8
    assert len(amended["artifact_kinds"]) == 8
    assert len(amended["tool_classes"]) == 8
    assert len(amended["scope_qualifiers"]) == 4
    assert len(amended["not_for"]) == 4
    for field in (
        "outcomes",
        "capability_ids",
        "artifact_kinds",
        "lifecycle_phases",
        "domains",
        "stacks",
        "tool_classes",
        "hosts",
        "platforms",
        "scope_qualifiers",
        "not_for",
    ):
        assert set(getattr(existing, field)) <= set(amended[field])


def test_amendment_rejects_authority_escalation_without_writing_case(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)

    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        allow_existing_worker_amendment=True,
        invoker=lambda provider, *_args, **_kwargs: _result(
            _amendment_response(authority="modify"),
            provider,
        ),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == ("contract_invalid:amendment_authority_context",)
    assert store.list_hiring_cases(limit=10) == []
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 0


def test_amendment_reports_content_free_projection_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)

    def reject_projection(*_args, **_kwargs):
        raise ValueError("workforce outcomes exceeds 8 items provider-secret")

    monkeypatch.setattr(hiring_module, "project_workforce_contract", reject_projection)
    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        allow_existing_worker_amendment=True,
        invoker=lambda provider, *_args, **_kwargs: _result(
            _amendment_response(),
            provider,
        ),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == ("contract_invalid:amendment_projection:outcomes",)
    assert "provider-secret" not in " ".join(outcome.reason_codes)
    assert store.list_hiring_cases(limit=10) == []
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 0


def test_high_risk_amendment_waits_for_owner_approval_then_applies(
    tmp_path: Path,
) -> None:
    """An amendment asserting an owner-gated risk class (approval authority) is
    recorded as a high-tier proposed case and applies only after explicit
    owner approval; the reviewer verdict alone no longer instantiates it."""

    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    response = _amendment_response()
    response["contract"]["requirements"] = ["Approval authority for release publication."]
    outcome = hire_contractor_for_gap(
        "Review and publish the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        allow_existing_worker_amendment=True,
        invoker=_invoker(
            response,
            {"approved": True, "reason_codes": []},
            _SAFE_SECURITY_REVIEW,
        ),
    )

    assert outcome.status == "pending_approval"
    assert outcome.worker is None
    assert outcome.workforce_changed is False
    case = outcome.hiring_case
    assert case["case_type"] == "amend"
    assert case["status"] == "proposed"
    assert case["risk_tier"] == "high"
    assert case["human_approval_required"] is True
    assert "approval" in case["critic_evidence"]["security_review"]["risk_classes"]
    assert "hiring approve" in outcome.notification
    # The existing worker is untouched while the case waits.
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 0

    # Owner approval materializes the amendment through the audited path.
    store.approve_hiring_case(case["id"], approved_by="operator")
    worker = apply_approved_hiring_case(store, case["id"])
    assert worker["revision"] == 1
    assert store.get_hiring_case(case["id"])["status"] == "applied"


def test_security_review_approved_external_hire_is_hired_without_human_gate(
    tmp_path: Path,
) -> None:
    """AR-238: the isolated security reviewer is the gate, not human approval.

    An external-mutation contract that the reviewer approves (verdict safe) is
    hired directly. The reviewer runs in the same CLI provider chain and its
    receipt is recorded truthfully alongside the hiring and critic receipts.
    """

    store = Store(tmp_path / "agency.db")
    external_unit = replace(_unit(), mutation_scope="external_write")
    outcome = hire_contractor_for_gap(
        "Implement the externally mutating quantum compiler build integration.",
        external_unit,
        (_existing(),),
        store=store,
        config=_config(provider_type="cli"),
        invoker=_invoker(
            _hiring_response(external_mutation=False),
            {"approved": True, "reason_codes": []},
            _SAFE_SECURITY_REVIEW,
        ),
    )

    assert outcome.hired is True
    assert outcome.worker["agent_slug"] == "quantum-build-engineer"
    assert outcome.hiring_case["status"] == "applied"
    assert outcome.hiring_case["risk_tier"] == "standard"
    assert outcome.hiring_case["human_approval_required"] is False
    review = outcome.hiring_case["critic_evidence"]["security_review"]
    assert review["verdict"] == "safe"
    receipts = outcome.hiring_case["model_evidence"]["receipts"]
    assert all(item["actual_model"] == "" for item in receipts)
    assert all(item["model_receipt_source"] == "cli.explicit_model_argument" for item in receipts)
    assert store.get_roster_entry("quantum-build-engineer") is not None


def test_owner_gated_hire_waits_for_approval_then_materializes(
    tmp_path: Path,
) -> None:
    """A hire asserting an owner-gated risk class stops before registration:
    the case persists as proposed/high/approval-required, no worker or roster
    entry exists, and `apply_approved_hiring_case` materializes it only after
    an operator records approval."""

    store = Store(tmp_path / "agency.db")
    response = _hiring_response()
    response["contract"]["capabilities"] = [
        "Quantum compiler build plugins",
        "Credential access for the build signing service",
    ]
    outcome = hire_contractor_for_gap(
        "Implement the quantum compiler build integration with signing.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(provider_type="cli"),
        invoker=_invoker(
            response,
            {"approved": True, "reason_codes": []},
            _SAFE_SECURITY_REVIEW,
        ),
    )

    assert outcome.status == "pending_approval"
    assert outcome.hired is False
    assert outcome.worker is None
    case = outcome.hiring_case
    assert case["status"] == "proposed"
    assert case["risk_tier"] == "high"
    assert case["human_approval_required"] is True
    assert "credential" in case["critic_evidence"]["security_review"]["risk_classes"]
    assert store.get_roster_entry("quantum-build-engineer") is None
    with pytest.raises(ValueError, match="requires explicit human approval"):
        apply_approved_hiring_case(store, case["id"])

    store.approve_hiring_case(case["id"], approved_by="operator")
    worker = apply_approved_hiring_case(store, case["id"])
    assert worker["agent_slug"] == "quantum-build-engineer"
    assert store.get_hiring_case(case["id"])["status"] == "applied"
    assert store.get_roster_entry("quantum-build-engineer") is not None


def test_security_review_unsafe_verdict_rejects_without_instantiating_worker(
    tmp_path: Path,
) -> None:
    """AR-238: an unsafe verdict rejects the case; the worker is never created.

    The reviewer returns unsafe on every attempt; after the bounded repair
    budget is exhausted the case is rejected and the worker is never
    instantiated.
    """

    store = Store(tmp_path / "agency.db")
    unsafe = {
        "verdict": "unsafe",
        "reasons": ["credential_access_marker"],
        "required_changes": ["Remove credential access from capabilities."],
        "same_provider_as_creator_warning": False,
    }
    config = replace(_config(), workforce=replace(_config().workforce, hiring_call_budget=8))
    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=config,
        invoker=_recording_invoker(
            _hiring_response(),
            {"approved": True, "reason_codes": []},
            unsafe,
            _hiring_response(),
            unsafe,
            _hiring_response(),
            unsafe,
            _hiring_response(),
            unsafe,
            _hiring_response(),
            unsafe,
            _hiring_response(),
            unsafe,
            calls=[],
        ),
    )

    assert outcome.status == "rejected"
    assert "safety_repair_budget_exhausted" in outcome.reason_codes
    assert outcome.worker is None
    assert outcome.hiring_case is None
    assert store.get_roster_entry("quantum-build-engineer") is None


def test_deferred_external_hire_reports_class_without_committing(tmp_path: Path) -> None:
    """AR-238: a deferred external hire is held until the preflight ready CAS,
    gated by the security reviewer (safe) rather than human approval."""

    store = Store(tmp_path / "agency.db")

    outcome = hire_contractor_for_gap(
        "Implement the externally mutating quantum compiler build integration.",
        replace(_unit(), mutation_scope="external_write"),
        (_existing(),),
        store=store,
        config=_config(),
        defer_commit=True,
        invoker=_invoker(
            _hiring_response(external_mutation=False),
            {"approved": True, "reason_codes": []},
            _SAFE_SECURITY_REVIEW,
        ),
    )

    assert outcome.status == "hired"
    assert outcome.reason_codes == ()
    assert outcome.pending_commit is not None
    assert outcome.worker is not None
    assert store.list_hiring_cases(limit=10) == []


def test_workspace_unit_overrides_model_external_mutation_claim(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    response = _hiring_response(external_mutation=True)
    response["contract"]["requirements"] = [
        "No network or credential access, external services, or global installs."
    ]

    outcome = hire_contractor_for_gap(
        "Implement the isolated quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(),
        invoker=_invoker(
            response,
            {"approved": True, "reason_codes": []},
        ),
    )

    assert outcome.status == "hired"
    assert outcome.reason_codes == ()
    assert outcome.contract is not None
    assert outcome.contract.external_mutation is False
    assert outcome.hiring_case["human_approval_required"] is False


def test_hired_contractor_is_restaffed_without_repeating_inference(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    implementation = _unit()
    review = WorkUnit(
        unit_id="unit-independent-review",
        outcome="Independently review the quantum build plugin",
        artifact_kind="review-report",
        lifecycle_phase="review",
        domains=("software-engineering",),
        languages=(),
        frameworks=(),
        required_capabilities=("review",),
        authority="review",
        mutation_scope="read_only",
        risks=("build-regression",),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(implementation.unit_id,),
        resources=("implementation artifact",),
        required_tools=("repository-read",),
        platforms=("windows", "linux"),
        acceptance_evidence=("independent review report",),
        parallelization="sequential",
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Implement and independently review a quantum build plugin.",
            "units": [asdict(implementation), asdict(review)],
        }
    )
    existing = _existing()
    initial_context = StaffingContext(
        "codex",
        "windows",
        frozenset({"native-delegation", "repository-read"}),
        1,
    )
    initial_proposal = build_deterministic_proposal(
        plan,
        (existing,),
        {
            implementation.unit_id: [(existing.agent_id, 0.9)],
            review.unit_id: [(existing.agent_id, 0.9)],
        },
        context=initial_context,
        budget=StaffingBudget(),
    )
    initial_staffing = verify_staffing(
        plan,
        initial_proposal,
        (existing,),
        context=initial_context,
        budget=StaffingBudget(),
    )
    initial = WorkforceRoutingOutcome(
        status="abstained",
        mode="balanced",
        inference_mode="inferred",
        plan=plan,
        proposal=initial_proposal,
        staffing=initial_staffing,
        attempts=(
            WorkforceInferenceAttempt(
                stage="recruiter",
                provider_name="task-agency-router",
                provider_type="litellm",
                requested_model="recruiter-model",
                model_group="task-agency-router",
                actual_model="resolved-recruiter",
                model_receipt_source="response.body.model",
                status="applied",
                reason_code="structured_response_applied",
                latency_ms=10,
            ),
        ),
        abstention_codes=tuple(item.code for item in initial_staffing.abstention_reasons),
        calls_used=1,
    )
    replacement = deepcopy(_hiring_response())
    replacement["contract"].update(
        slug="quantum-build-integration-specialist",
        role="Quantum Build Integration Specialist",
    )
    hired = hire_contractor_for_gap(
        "Implement and independently review a quantum build plugin.",
        implementation,
        (existing,),
        store=store,
        config=_config(),
        invoker=_recording_invoker(
            _hiring_response(),
            {"approved": False, "reason_codes": ["authority_scope_is_overbroad"]},
            replacement,
            {"approved": True, "reason_codes": []},
            calls=[],
        ),
    )
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    result = restaff_after_hire(
        initial,
        (*snapshot.contracts, existing),
        hired_agent_id="quantum-build-integration-specialist",
        causing_unit_id=implementation.unit_id,
        context=replace(initial_context, roster_generation=snapshot.generation),
        config=_config(),
    )

    assert hired.hired is True
    assert [item.stage for item in hired.attempts] == [
        "hiring",
        "hiring-critic",
        "hiring-repair",
        "hiring-repair-critic",
        "security_review",
    ]
    assert result.accepted is True
    assert result.calls_used == 1
    assert result.staffing.units[0].selected == ("quantum-build-integration-specialist",)
    assert result.staffing.units[1].selected == ("general-build-reviewer",)


def test_route_hires_and_assigns_real_gap_in_same_preflight(tmp_path: Path, monkeypatch) -> None:
    from agency_runtime.core.workforce import hiring as hiring_module
    from agency_runtime.core.workforce import inference as inference_module

    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    implementation = _unit()
    review = WorkUnit(
        unit_id="unit-independent-review",
        outcome="Independently review the quantum build plugin",
        artifact_kind="review-report",
        lifecycle_phase="review",
        domains=("software-engineering",),
        languages=(),
        frameworks=(),
        required_capabilities=("review",),
        authority="review",
        mutation_scope="read_only",
        risks=("build-regression",),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(implementation.unit_id,),
        resources=("implementation artifact",),
        required_tools=("repository-read",),
        platforms=("windows", "linux"),
        acceptance_evidence=("independent review report",),
        parallelization="sequential",
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Implement and independently review a quantum build plugin.",
            "units": [asdict(implementation), asdict(review)],
        }
    )
    session_id = "dynamic-hiring-session"
    trace_id = "dynamic-hiring-trace"
    capability = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id=session_id,
        trace_id=trace_id,
        available_tools=("repository-read", "native-delegation"),
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(capability.capabilities),
        snapshot.generation,
    )
    proposal = build_deterministic_proposal(
        plan,
        snapshot.contracts,
        {
            implementation.unit_id: [],
            review.unit_id: [(existing.agent_id, 0.9)],
        },
        context=context,
        budget=StaffingBudget(),
        semantic_required={},
        semantic_acceptable={review.unit_id: frozenset({existing.agent_id})},
        semantic_gap_units=frozenset({implementation.unit_id}),
    )
    staffing = verify_staffing(
        plan,
        proposal,
        snapshot.contracts,
        context=context,
        budget=StaffingBudget(),
    )
    assert {
        "no_safe_sufficient_team",
        "recruiter_abstained",
    } <= {item.code for item in staffing.abstention_reasons}
    inferred = WorkforceRoutingOutcome(
        status="abstained",
        mode="balanced",
        inference_mode="inferred",
        plan=plan,
        proposal=proposal,
        staffing=staffing,
        attempts=(
            WorkforceInferenceAttempt(
                stage="recruiter",
                provider_name="task-agency-router",
                provider_type="litellm",
                requested_model="recruiter-model",
                model_group="task-agency-router",
                actual_model="resolved-recruiter",
                model_receipt_source="response.body.model",
                status="applied",
                reason_code="structured_response_applied",
                latency_ms=10,
            ),
        ),
        abstention_codes=tuple(item.code for item in staffing.abstention_reasons),
        calls_used=1,
    )
    implicit_proposal = build_deterministic_proposal(
        plan,
        snapshot.contracts,
        {
            implementation.unit_id: [(existing.agent_id, 0.9)],
            review.unit_id: [(existing.agent_id, 0.9)],
        },
        context=context,
        budget=StaffingBudget(),
        semantic_required={implementation.unit_id: frozenset({existing.agent_id})},
        semantic_acceptable={review.unit_id: frozenset({existing.agent_id})},
    )
    implicit_staffing = verify_staffing(
        plan,
        implicit_proposal,
        snapshot.contracts,
        context=context,
        budget=StaffingBudget(),
    )
    assert (
        _hireable_gap_units(
            replace(inferred, proposal=implicit_proposal, staffing=implicit_staffing)
        )
        == ()
    )
    assert _hireable_gap_units(inferred) == (implementation.unit_id,)
    unsafe = replace(
        inferred,
        staffing=replace(
            staffing,
            abstention_reasons=(
                *staffing.abstention_reasons,
                AbstentionReason("forbidden_agent_selected", implementation.unit_id),
            ),
        ),
    )
    assert _hireable_gap_units(unsafe) == ()
    real_hire = hiring_module.hire_contractor_for_gap

    def fake_hire(*args, **kwargs):
        return real_hire(
            *args,
            **kwargs,
            invoker=_invoker(
                _hiring_response(external_mutation=True),
                {"approved": True, "reason_codes": []},
            ),
        )

    monkeypatch.setattr(inference_module, "plan_and_staff_workforce", lambda *_a, **_k: inferred)
    monkeypatch.setattr(hiring_module, "hire_contractor_for_gap", fake_hire)
    config = _config()
    result = route(
        session_id,
        "Implement and independently review a quantum build plugin.",
        store.get_active_roster_as_catalog(disabled_agents=()),
        config=config,
        store=store,
        trace_id=trace_id,
        host="codex",
        platform="windows",
        capability_receipt=capability,
        workforce_snapshot=snapshot,
    )

    assert result["status"] == "accepted"
    assert result["hiring_event"]["status"] == "hired"
    assert result["hiring_event"]["unit_id"] == implementation.unit_id
    assert result["hiring_events"] == [result["hiring_event"]]
    assert result["hiring_event"]["worker"] == "quantum-build-engineer"
    assert "quantum-build-engineer" in result["selected_ids"]
    assert store.get_workforce_worker("quantum-build-engineer")["state"] == "contractor"
    receipt = project_durable_routing_receipt(result)
    assert receipt["hiring"]["attempted_count"] == 1
    assert receipt["hiring"]["workforce_changes"] == 1
    assert receipt["hiring"]["events"][0]["status"] == "hired"


@pytest.mark.parametrize(
    (
        "max_hires",
        "max_daily",
        "decline_first",
        "expected_statuses",
        "expected_calls",
        "accepted",
    ),
    [
        (0, 3, False, ("not_attempted", "not_attempted"), (), False),
        (1, 3, False, ("hired", "not_attempted"), ("unit-quantum-build",), False),
        (
            1,
            3,
            True,
            ("abstained", "hired"),
            ("unit-quantum-build", "unit-photonic-build"),
            False,
        ),
        (
            2,
            3,
            False,
            ("hired", "hired"),
            ("unit-quantum-build", "unit-photonic-build"),
            True,
        ),
        # AR-241: daily hire cap removal — max_daily=0 no longer rejects.
        (
            2,
            0,
            False,
            ("hired", "hired"),
            ("unit-quantum-build", "unit-photonic-build"),
            True,
        ),
    ],
)
def test_route_hiring_caps_and_daily_budget_are_cumulative_and_truthful(
    tmp_path: Path,
    monkeypatch,
    max_hires: int,
    max_daily: int,
    decline_first: bool,
    expected_statuses: tuple[str, ...],
    expected_calls: tuple[str, ...],
    accepted: bool,
) -> None:
    from agency_runtime.core.workforce import hiring as hiring_module
    from agency_runtime.core.workforce import inference as inference_module

    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    quantum = _unit()
    photonic = _photonic_unit()
    review = WorkUnit(
        unit_id="unit-independent-review",
        outcome="Independently review both compiler build plugins",
        artifact_kind="review-report",
        lifecycle_phase="review",
        domains=("software-engineering",),
        languages=(),
        frameworks=(),
        required_capabilities=("review",),
        authority="review",
        mutation_scope="read_only",
        risks=("build-regression",),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(quantum.unit_id, photonic.unit_id),
        resources=("implementation artifacts",),
        required_tools=("repository-read",),
        platforms=("windows", "linux"),
        acceptance_evidence=("independent review report",),
        parallelization="sequential",
    )
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Implement and review quantum and photonic build plugins.",
            "units": [asdict(quantum), asdict(photonic), asdict(review)],
        }
    )
    session_id = f"multi-gap-{max_hires}-{max_daily}"
    trace_id = f"multi-gap-trace-{max_hires}-{max_daily}"
    capability = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id=session_id,
        trace_id=trace_id,
        available_tools=("repository-read", "native-delegation"),
    )
    context = StaffingContext(
        "codex",
        "windows",
        frozenset(capability.capabilities),
        snapshot.generation,
    )
    rankings = {
        quantum.unit_id: [(existing.agent_id, 0.9)],
        photonic.unit_id: [(existing.agent_id, 0.9)],
        review.unit_id: [(existing.agent_id, 0.9)],
    }
    proposal = build_deterministic_proposal(
        plan,
        snapshot.contracts,
        rankings,
        context=context,
        budget=StaffingBudget(),
        semantic_required={
            quantum.unit_id: frozenset({existing.agent_id}),
            photonic.unit_id: frozenset({existing.agent_id}),
        },
        semantic_acceptable={review.unit_id: frozenset({existing.agent_id})},
        semantic_gap_units=frozenset({quantum.unit_id, photonic.unit_id}),
    )
    staffing = verify_staffing(
        plan,
        proposal,
        snapshot.contracts,
        context=context,
        budget=StaffingBudget(),
    )
    for unit_id in (quantum.unit_id, photonic.unit_id):
        codes = {item.code for item in staffing.abstention_reasons if item.unit_id == unit_id}
        assert {"required_agents_missing", "no_safe_sufficient_team"} <= codes
    inferred = WorkforceRoutingOutcome(
        status="abstained",
        mode="balanced",
        inference_mode="inferred",
        plan=plan,
        proposal=proposal,
        staffing=staffing,
        attempts=(
            WorkforceInferenceAttempt(
                stage="recruiter",
                provider_name="task-agency-router",
                provider_type="litellm",
                requested_model="recruiter-model",
                model_group="task-agency-router",
                actual_model="resolved-recruiter",
                model_receipt_source="response.body.model",
                status="applied",
                reason_code="structured_response_applied",
                latency_ms=10,
            ),
        ),
        abstention_codes=tuple(item.code for item in staffing.abstention_reasons),
        calls_used=1,
    )
    real_hire = hiring_module.hire_contractor_for_gap
    calls: list[str] = []

    def fake_hire(request, unit, contracts, **kwargs):
        calls.append(unit.unit_id)
        response = _hiring_response_for(unit)
        if decline_first and unit.unit_id == quantum.unit_id:
            response["action"] = "abstain"
            response["contract"] = None
        return real_hire(
            request,
            unit,
            contracts,
            **kwargs,
            invoker=_invoker(
                response,
                {"approved": True, "reason_codes": []},
            ),
        )

    monkeypatch.setattr(inference_module, "plan_and_staff_workforce", lambda *_a, **_k: inferred)
    monkeypatch.setattr(hiring_module, "hire_contractor_for_gap", fake_hire)
    config = _config()
    config = replace(
        config,
        workforce=replace(
            config.workforce,
            max_hires_per_turn=max_hires,
            max_hires_per_day=max_daily,
        ),
    )
    result = route(
        session_id,
        "Implement and review quantum and photonic build plugins.",
        store.get_active_roster_as_catalog(disabled_agents=()),
        config=config,
        store=store,
        trace_id=trace_id,
        host="codex",
        platform="windows",
        capability_receipt=capability,
        workforce_snapshot=snapshot,
    )

    assert tuple(item["unit_id"] for item in result["hiring_events"]) == (
        quantum.unit_id,
        photonic.unit_id,
    )
    assert tuple(item["status"] for item in result["hiring_events"]) == expected_statuses
    assert tuple(calls) == expected_calls
    assert (result["status"] == "accepted") is accepted
    if max_hires == 0:
        assert {tuple(item["reason_codes"]) for item in result["hiring_events"]} == {
            ("task_hiring_limit_reached",)
        }
    if max_hires == 1 and not decline_first:
        assert result["hiring_events"][1]["reason_codes"] == ["task_hiring_limit_reached"]
    if decline_first:
        assert result["hiring_events"][0]["reason_codes"] == ["hiring_inference_abstained"]
    # AR-241: max_daily == 0 no longer rejects (daily cap removed).
    receipt = project_durable_routing_receipt(result)
    assert [item["status"] for item in receipt["hiring"]["events"]] == list(expected_statuses)


def test_task_gap_amendment_is_rejected_when_amendment_is_disallowed(
    tmp_path: Path,
) -> None:
    """An ordinary task gap creates a distinct exact specialist: when the
    caller forbids existing-worker amendment (the pipeline's task-staffing
    default), an inference-proposed amend abstains with the exact reason
    instead of broadening a near-match."""

    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        allow_existing_worker_amendment=False,
        invoker=_invoker(_amendment_response(), {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "abstained"
    assert "task_gap_requires_distinct_specialist" in outcome.reason_codes
    assert outcome.worker is None
    assert outcome.hiring_case is None
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 0


def _renamed_repeat_of_the_candidate() -> WorkforceContract:
    """An incumbent already answering to the candidate's role, under another slug.

    Deliberately not a subset of the candidate on outcomes or domains, so
    `_obvious_duplicate` cannot see it. That is the live failure shape, not a
    contrived one.
    """

    return replace(
        _existing(),
        worker_id="worker:quantum-build-engineer-legacy",
        agent_id="quantum-build-engineer-legacy",
        # Spacing and case differ; the role claim does not.
        display_name="quantum  build   ENGINEER",
        authority="modify",
        outcomes=("legacy quantum toolchain ownership",),
        domains=("legacy-build-systems",),
    )


def test_structural_duplicate_check_alone_cannot_see_a_renamed_repeat() -> None:
    """Pins why the role-identity check has to exist at all.

    If `_obvious_duplicate` ever starts catching this on its own, the extra
    check is redundant and this test says so by failing.
    """

    incumbent = _renamed_repeat_of_the_candidate()
    candidate = replace(
        _existing(),
        worker_id="worker:quantum-build-engineer",
        agent_id="quantum-build-engineer",
        display_name="Quantum Build Engineer",
        authority="modify",
        outcomes=("quantum build implementation",),
        domains=("quantum-build-systems",),
    )

    assert hiring_module._obvious_duplicate(candidate, incumbent) is False
    assert hiring_module._duplicate_role_identity(candidate, (incumbent,)) == incumbent.agent_id


def test_a_role_identity_match_needs_the_same_authority() -> None:
    """Same name at a different authority is a different job, not a duplicate."""

    incumbent = replace(_renamed_repeat_of_the_candidate(), authority="review")
    candidate = replace(
        _existing(),
        worker_id="worker:quantum-build-engineer",
        agent_id="quantum-build-engineer",
        display_name="Quantum Build Engineer",
        authority="modify",
    )

    assert hiring_module._duplicate_role_identity(candidate, (incumbent,)) == ""


def test_second_contractor_for_an_existing_role_is_refused_and_names_the_incumbent(
    tmp_path: Path,
) -> None:
    """Rule 6's dedupe requirement, at the seam where a card is actually minted.

    The roster grew two "Request Clarification Specialist" contractors this way:
    identical name, authority and task types, different slug, prose different
    enough that the structural check passed. Abstaining is the whole point --
    the incumbent is still selectable, so nothing is lost by not minting.
    """

    store = Store(tmp_path / "agency.db")
    incumbent = _renamed_repeat_of_the_candidate()

    outcome = hire_contractor_for_gap(
        "Implement the missing quantum compiler build integration.",
        _unit(),
        (_existing(), incumbent),
        store=store,
        config=_config(),
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )

    assert outcome.status == "abstained"
    assert "deterministic_duplicate_detected" in outcome.reason_codes
    # Forensics: a bare "duplicate detected" cannot be reconstructed later.
    assert f"duplicate_role_identity:{incumbent.agent_id}" in outcome.reason_codes
    assert outcome.worker is None
    assert store.list_hiring_cases(limit=10) == []
