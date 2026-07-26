from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.selector.pipeline import _hireable_gap_units, route
from agency_runtime.core.selector.receipt_projection import project_durable_routing_receipt
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
)
from agency_runtime.core.workforce.hiring import (
    apply_approved_hiring_case,
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
            hiring_model="hiring-model",
            critic_model="critic-model",
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


def _invoker(hiring: dict[str, Any], critic: dict[str, Any]):
    responses = iter((hiring, critic))

    def invoke(provider, _prompt, _schema, **_kwargs):
        return _result(next(responses), provider)

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
    assert [item.stage for item in outcome.attempts] == ["hiring", "hiring-critic"]


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


def test_coherent_gap_amends_existing_worker_without_roster_bloat(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    before = store.get_workforce_worker(existing.agent_id)
    parent = store.get_specialist_prompt(existing.agent_id)

    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        invoker=_invoker(
            _amendment_response(),
            {"approved": True, "reason_codes": []},
        ),
    )

    assert outcome.status == "amended"
    assert outcome.workforce_changed is True
    assert outcome.worker["worker_id"] == before["worker_id"]
    assert outcome.worker["revision"] == 1
    assert len(store.list_workforce_workers(limit=10)) == 1
    assert outcome.hiring_case["case_type"] == "amend"
    assert outcome.hiring_case["status"] == "applied"
    current = store.get_specialist_prompt(existing.agent_id)
    assert current["prompt_body"].startswith(parent["prompt_body"])
    assert "--- Agency capability amendment ---" in current["prompt_body"]
    assert "quantum-build-systems" in outcome.hiring_case["contract_evidence"]["domains"]


def test_amendment_rejects_authority_escalation_without_writing_case(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)

    outcome = hire_contractor_for_gap(
        "Review the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        invoker=lambda provider, *_args, **_kwargs: _result(
            _amendment_response(authority="modify"),
            provider,
        ),
    )

    assert outcome.status == "abstained"
    assert outcome.reason_codes == ("contract_invalid:ValueError",)
    assert store.list_hiring_cases(limit=10) == []
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 0


def test_high_risk_amendment_is_revision_bound_and_applies_only_after_approval(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    existing = _install_existing(store)
    outcome = hire_contractor_for_gap(
        "Review and publish the missing quantum compiler build integration.",
        _amendment_unit(),
        (existing,),
        store=store,
        config=_config(),
        invoker=_invoker(
            _amendment_response(external_mutation=True),
            {"approved": True, "reason_codes": []},
        ),
    )

    assert outcome.status == "approval_required"
    assert outcome.hiring_case["case_type"] == "amend"
    assert store.get_workforce_worker(existing.agent_id)["revision"] == 0
    approved = store.approve_hiring_case(
        outcome.hiring_case["id"],
        approved_by="release-security-reviewer",
    )
    worker = apply_approved_hiring_case(store, approved["id"])

    assert worker["worker_id"] == existing.worker_id
    assert worker["revision"] == 1
    assert store.get_hiring_case(approved["id"])["status"] == "applied"


def test_high_risk_hire_requires_approval_and_cli_receipt_remains_truthful(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    outcome = hire_contractor_for_gap(
        "Implement the externally mutating quantum compiler build integration.",
        _unit(),
        (_existing(),),
        store=store,
        config=_config(provider_type="cli"),
        invoker=_invoker(
            _hiring_response(external_mutation=True),
            {"approved": True, "reason_codes": []},
        ),
    )

    assert outcome.status == "approval_required"
    assert outcome.worker is None
    assert outcome.hiring_case["status"] == "proposed"
    receipts = outcome.hiring_case["model_evidence"]["receipts"]
    assert all(item["actual_model"] == "" for item in receipts)
    assert all(item["model_receipt_source"] == "cli.explicit_model_argument" for item in receipts)
    assert store.get_roster_entry("quantum-build-engineer") is None

    approved = store.approve_hiring_case(
        outcome.hiring_case["id"],
        approved_by="security-reviewer",
    )
    assert approved["status"] == "proposed"
    worker = apply_approved_hiring_case(store, approved["id"])

    assert worker["agent_slug"] == "quantum-build-engineer"
    assert worker["state"] == "contractor"
    assert store.get_hiring_case(approved["id"])["status"] == "applied"
    assert store.get_roster_entry("quantum-build-engineer") is not None
    assert apply_approved_hiring_case(store, approved["id"])["worker_id"] == worker["worker_id"]
    replay = store.approve_hiring_case(approved["id"], approved_by="security-reviewer")
    assert replay["status"] == "applied"


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
    hired = hire_contractor_for_gap(
        "Implement and independently review a quantum build plugin.",
        implementation,
        (existing,),
        store=store,
        config=_config(),
        invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
    )
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    result = restaff_after_hire(
        initial,
        (*snapshot.contracts, existing),
        hired_agent_id="quantum-build-engineer",
        causing_unit_id=implementation.unit_id,
        context=replace(initial_context, roster_generation=snapshot.generation),
        config=_config(),
    )

    assert hired.hired is True
    assert result.accepted is True
    assert result.calls_used == 1
    assert result.staffing.units[0].selected == ("quantum-build-engineer",)
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
            implementation.unit_id: [(existing.agent_id, 0.9)],
            review.unit_id: [(existing.agent_id, 0.9)],
        },
        context=context,
        budget=StaffingBudget(),
        semantic_required={implementation.unit_id: frozenset({existing.agent_id})},
        semantic_acceptable={review.unit_id: frozenset({existing.agent_id})},
    )
    staffing = verify_staffing(
        plan,
        proposal,
        snapshot.contracts,
        context=context,
        budget=StaffingBudget(),
    )
    assert {
        "required_agents_missing",
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
            invoker=_invoker(_hiring_response(), {"approved": True, "reason_codes": []}),
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
    ("max_hires", "max_daily", "expected_statuses", "expected_calls", "accepted"),
    [
        (0, 3, ("not_attempted", "not_attempted"), (), False),
        (1, 3, ("hired", "not_attempted"), ("unit-quantum-build",), False),
        (
            2,
            3,
            ("hired", "hired"),
            ("unit-quantum-build", "unit-photonic-build"),
            True,
        ),
        (2, 0, ("abstained", "not_attempted"), ("unit-quantum-build",), False),
    ],
)
def test_route_hiring_caps_and_daily_budget_are_cumulative_and_truthful(
    tmp_path: Path,
    monkeypatch,
    max_hires: int,
    max_daily: int,
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
        return real_hire(
            request,
            unit,
            contracts,
            **kwargs,
            invoker=_invoker(
                _hiring_response_for(unit),
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
            max_hires_per_task=max_hires,
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
    if max_hires == 1:
        assert result["hiring_events"][1]["reason_codes"] == ["task_hiring_limit_reached"]
    if max_daily == 0:
        assert result["hiring_events"][0]["reason_codes"] == ["daily_hiring_limit_reached"]
        assert result["hiring_events"][1]["reason_codes"] == ["daily_hiring_limit_reached"]
    receipt = project_durable_routing_receipt(result)
    assert [item["status"] for item in receipt["hiring"]["events"]] == list(expected_statuses)
