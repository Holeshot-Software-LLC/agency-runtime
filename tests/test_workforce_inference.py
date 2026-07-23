"""Inference-first workforce planning, recruitment, and receipt tests."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from agency_runtime.core.config import AgencyConfig, ProviderEntry, WorkforceConfig
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.selector.pipeline import _record_workforce_model_receipts
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.fallback import (
    deterministic_plan_and_staff,
    deterministic_work_plan,
)
from agency_runtime.core.workforce.inference import (
    PLAN_RESPONSE_SCHEMA,
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
    _detail_cards,
    _inference_index,
    _normalized_plan_response,
    _recruiter_directory,
    _typed_shortlists,
    configured_workforce_providers,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.plan_policy import plan_policy_violations
from agency_runtime.core.workforce.planning_contracts import (
    MAX_LABEL_CHARS,
    MAX_TEXT_CHARS,
    parse_work_unit_plan,
)
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.routing_projection import project_workforce_routing
from agency_runtime.core.workforce.staffing_verifier import StaffingContext, StaffingDecision

_GENERATION = 7
_HASH = "sha256:" + "a" * 64


def test_planner_schema_matches_strict_identifier_and_required_array_contract() -> None:
    unit = PLAN_RESPONSE_SCHEMA["properties"]["units"]["items"]["properties"]

    assert "review" in unit["required_capabilities"]["items"]["enum"]
    assert unit["outcome"]["maxLength"] == MAX_TEXT_CHARS
    assert PLAN_RESPONSE_SCHEMA["properties"]["request_summary"]["maxLength"] == MAX_TEXT_CHARS
    required = (
        "domains",
        "required_capabilities",
        "resources",
        "platforms",
        "acceptance_evidence",
    )
    for field in required:
        assert unit[field]["minItems"] == 1
    for field in ("resources", "acceptance_evidence"):
        assert unit[field]["items"]["maxLength"] == MAX_LABEL_CHARS


def test_inference_index_keeps_complete_worker_and_disabled_control_facts() -> None:
    enabled = _contract("enabled-worker")
    disabled = _contract("disabled-worker", enabled=False)

    view = _inference_index((enabled, disabled))
    fields = view["fields"]
    rows = view["workers"]
    slug_index = fields.index("agent_id")

    assert [row[slug_index] for row in rows] == ["enabled-worker", "disabled-worker"]
    assert view["defaults"]["enabled"] is True
    override_fields = view["override_fields"]
    disabled_override = dict(zip(override_fields, view["worker_overrides"][0], strict=True))
    assert disabled_override["agent_id"] == "disabled-worker"
    assert disabled_override["employment"] == "disabled"
    assert disabled_override["enabled"] is False
    assert {
        "worker_id",
        "display_name",
        "scope_qualifiers",
        "context_mode",
        "tool_classes",
        "version",
    } <= set(fields)
    assert "same_context_conflicts" in view["relationship_fields"]


def test_recruiter_directory_keeps_every_worker_and_full_typed_candidate_details() -> None:
    contracts = tuple(_contract(f"worker-{index}") for index in range(14))
    snapshot = _snapshot(*contracts)
    directory = _recruiter_directory(contracts)

    assert len(directory["workers"]) == 14
    assert directory["fields"] == [
        "agent_id",
        "primary_outcome",
        "capability_ids",
        "domains",
        "stacks",
        "enabled",
        "employment",
    ]
    detail = _detail_cards(
        snapshot,
        request="Analyze the repository.",
        plan=parse_work_unit_plan(_plan_document()),
        required_ids=("worker-13",),
    )
    assert any(item["agent_id"] == "worker-13" for item in detail)
    assert next(item for item in detail if item["agent_id"] == "worker-13")["version"] == _HASH


def _contract(agent_id: str, *, enabled: bool = True) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="analyst",
        outcomes=("Technical analysis",),
        capability_ids=("analysis",),
        artifact_kinds=("analysis",),
        lifecycle_phases=("discovery",),
        domains=("software-engineering",),
        stacks=(),
        scope_qualifiers=(),
        not_for=(),
        authority="advise",
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


def _plan_document() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "request_summary": "Analyze the repository implementation.",
        "units": [
            {
                "unit_id": "unit-analyze",
                "outcome": "Complete technical analysis",
                "artifact_kind": "analysis",
                "lifecycle_phase": "discovery",
                "domains": ["software-engineering"],
                "languages": [],
                "frameworks": [],
                "required_capabilities": ["technical-analysis"],
                "authority": "advise",
                "mutation_scope": "read_only",
                "risks": ["regression"],
                "trust_boundaries": ["repository"],
                "claims": [],
                "depends_on": [],
                "resources": ["repository"],
                "required_tools": ["repository-read"],
                "platforms": ["windows", "linux"],
                "acceptance_evidence": ["analysis findings are evidence-backed"],
                "parallelization": "unspecified",
            }
        ],
    }


def _compact_plan_document() -> dict[str, Any]:
    return {
        "request_summary": "Analyze the repository implementation.",
        "units": [
            {
                "unit_id": "unit-analyze",
                "outcome": "Complete technical analysis",
                "artifact_kind": "analysis",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["analysis"],
                "novel_capability": "",
                "depends_on": [],
            }
        ],
    }


def _nominee(
    agent_id: str,
    score: float,
    classification: str = "required",
) -> dict[str, Any]:
    forbidden = classification == "forbidden"
    return {
        "agent_id": agent_id,
        "score": score,
        "classification": classification,
        "positive_evidence": [] if forbidden else ["scope-match"],
        "negative_evidence": ["wrong-neighbor"] if forbidden else [],
    }


def _nomination_document(selected: str = "technical-analyst") -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": "unit-analyze",
                "ranked_semantic": [
                    _nominee(selected, 0.98),
                ],
            }
        ]
    }


def _provider(name: str = "task-agency-router", *, model: str = "router-alias") -> ProviderEntry:
    return ProviderEntry(
        name=name,
        type="litellm",
        model=model,
        base_url="https://router.example.test/v1",
        api_key="secret",
        timeout=5,
    )


def _config(mode: str = "balanced", **workforce: object) -> AgencyConfig:
    policy = replace(WorkforceConfig(mode=mode), **workforce)
    return AgencyConfig(providers=(_provider(),), workforce=policy)


def _context() -> StaffingContext:
    return StaffingContext(
        "codex",
        "windows",
        frozenset(
            {
                "code-execution",
                "native-delegation",
                "package-management",
                "repository-read",
                "repository-write",
                "shell-execution",
                "test-execution",
            }
        ),
        _GENERATION,
    )


def _result(value: dict[str, Any], *, actual: str = "gpt-5.6-mini") -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model=actual,
        model_receipt_source="response.body.model" if actual else "unavailable",
        latency_ms=17,
    )


def test_balanced_mode_accepts_clear_local_route_after_compact_plan_with_receipt() -> None:
    snapshot = _snapshot(
        _contract("technical-analyst"), _contract("disabled-specialist", enabled=False)
    )
    calls: list[tuple[str, str, str]] = []

    def invoke(provider, prompt, _schema, **_kwargs):
        payload = json.loads(prompt)
        calls.append((provider.name, provider.model, prompt))
        assert "roster" not in payload
        assert "detail_cards" not in payload
        assert "analysis" in payload["planning_taxonomy"]["known_capability_ids"]
        return _result(_compact_plan_document())

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 1
    assert [item.stage for item in outcome.attempts] == ["planner"]
    assert all(item.model_group == "router-alias" for item in outcome.attempts)
    assert all(item.actual_model == "gpt-5.6-mini" for item in outcome.attempts)
    assert outcome.staffing.units[0].selected == ("technical-analyst",)


def test_warm_route_reuses_version_bound_plan_and_candidate_without_inference() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    calls = 0

    def invoke(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return _result(_compact_plan_document())

    first = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=invoke,
        routing_context_fingerprint="policy-v1",
    )
    second = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=invoke,
        routing_context_fingerprint="policy-v1",
    )

    assert first.accepted and second.accepted
    assert calls == 1
    assert first.cache_hits == ()
    assert second.cache_hits == ("plan", "candidate")
    assert second.calls_used == 0
    assert second.attempts == ()


def test_plan_cache_invalidates_on_every_external_routing_identity() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    config = _config(mode="fast")
    context = _context()
    calls = 0

    def invoke(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return _result(_compact_plan_document())

    def run(
        request: str = "Analyze this implementation safely.",
        *,
        current_snapshot: WorkforceIndexSnapshot = snapshot,
        current_config: AgencyConfig = config,
        current_context: StaffingContext = context,
        policy: str = "policy-v1",
    ) -> None:
        assert plan_and_staff_workforce(
            request,
            current_snapshot,
            config=current_config,
            context=current_context,
            invoker=invoke,
            routing_context_fingerprint=policy,
        ).accepted

    run()
    run(request="Analyze the second implementation safely.")
    run(current_context=replace(context, host="claude"))
    run(
        current_context=replace(
            context,
            available_tools=context.available_tools | {"browser-control"},
        )
    )
    run(policy="policy-v2")
    run(current_snapshot=replace(snapshot, generation=snapshot.generation + 1))
    run(current_config=replace(config, providers=(replace(config.providers[0], model="other"),)))
    run(current_config=replace(config, providers=(replace(config.providers[0], api_key="other"),)))

    assert calls == 8


def test_warm_ambiguous_route_reuses_bounded_recruiter_result() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    nominations = _nomination_document()
    nominations["units"][0]["ranked_semantic"].append(
        _nominee("analysis-alternative", 0.9, "acceptable")
    )
    calls = 0

    def invoke(_provider, prompt, _schema, **_kwargs):
        nonlocal calls
        calls += 1
        payload = json.loads(prompt)
        return _result(_compact_plan_document() if "planning_taxonomy" in payload else nominations)

    first = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
        routing_context_fingerprint="policy-v1",
    )
    second = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
        routing_context_fingerprint="policy-v1",
    )

    assert first.accepted and second.accepted
    assert calls == 2
    assert second.cache_hits == ("plan", "candidate", "recruiter")
    assert second.calls_used == 0


def test_balanced_recruiter_repairs_only_missing_work_unit_rows() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    plan = _compact_plan_document()
    second = json.loads(json.dumps(plan["units"][0]))
    second["unit_id"] = "unit-analyze-second"
    second["outcome"] = "Complete a second independent technical analysis"
    plan["units"].append(second)
    first_row = _nomination_document()["units"][0]
    first_row["ranked_semantic"].append(_nominee("analysis-alternative", 0.90, "acceptable"))
    second_row = {
        "unit_id": "unit-analyze-second",
        "ranked_semantic": [
            _nominee("technical-analyst", 0.98),
            _nominee("analysis-alternative", 0.90, "acceptable"),
        ],
    }
    responses = iter(
        (
            _result(plan),
            _result({"units": [first_row]}),
            _result({"units": [second_row]}),
        )
    )

    outcome = plan_and_staff_workforce(
        "Analyze two independent repository concerns.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [(item.stage, item.status) for item in outcome.attempts] == [
        ("planner", "applied"),
        ("recruiter", "rejected"),
        ("recruiter", "applied"),
    ]
    assert "missing work units: unit-analyze-second" in outcome.attempts[1].validation_detail
    assert [item.unit_id for item in outcome.staffing.units] == [
        "unit-analyze",
        "unit-analyze-second",
    ]


def test_inference_normalizes_duplicate_candidate_rows() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    plan = _compact_plan_document()
    nominations = _nomination_document()
    nominations["units"][0]["ranked_semantic"] = [
        _nominee("technical-analyst", 0.90),
        _nominee("technical-analyst", 0.98),
        _nominee("analysis-alternative", 0.80, "acceptable"),
    ]
    responses = iter((_result(plan), _result(nominations)))

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert outcome.plan is not None
    assert outcome.plan.units[0].required_capabilities == ("analysis",)
    assert outcome.proposal is not None
    assert outcome.proposal.units[0].ranked_semantic[0].score == 1.0


def test_inference_uses_semantic_order_without_trusting_uncalibrated_score_gaps() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    nominations = _nomination_document()
    nominations["units"][0]["ranked_semantic"] = [
        _nominee("technical-analyst", 0.99, "required"),
        _nominee("analysis-alternative", 0.98, "acceptable"),
    ]
    prompts: list[dict[str, Any]] = []
    responses = iter((_result(_compact_plan_document()), _result(nominations)))

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(json.loads(prompt))
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert [item.stage for item in outcome.attempts] == ["planner", "recruiter"]
    assert "roster" not in prompts[1]
    assert {item["agent_id"] for item in prompts[1]["detail_cards"]} == {
        "analysis-alternative",
        "technical-analyst",
    }
    assert prompts[1]["response_contract"]["candidate_ids_must_come_from_detail_cards"]
    assert outcome.proposal is not None
    row = outcome.proposal.units[0]
    assert [(item.agent_id, item.score) for item in row.ranked_semantic] == [
        ("technical-analyst", 1.0),
        ("analysis-alternative", 0.9),
    ]
    assert row.margin == 0.1


def test_downstream_assurance_does_not_repeat_dependency_carried_domains() -> None:
    plan = _plan_document()
    plan["units"][0]["domains"] = ["security", "software-engineering"]
    plan["units"][0]["languages"] = ["python"]
    plan["units"][0]["frameworks"] = ["pytest"]
    assurance = {
        **dict(plan["units"][0]),
        "unit_id": "unit-tests",
        "outcome": "Focused test evidence",
        "artifact_kind": "test-evidence",
        "lifecycle_phase": "testing",
        "domains": ["security", "software-engineering", "quality-assurance"],
        "languages": ["python"],
        "frameworks": ["pytest"],
        "required_capabilities": ["testing", "verification"],
        "authority": "advise",
        "depends_on": ["unit-analyze"],
    }
    plan["units"].append(assurance)

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][1]["domains"] == ["quality-assurance"]
    assert normalized["units"][1]["languages"] == []
    assert normalized["units"][1]["frameworks"] == []
    assert normalized["units"][1]["authority"] == "review"
    assert normalized["units"][0]["required_capabilities"] == ["analysis"]
    assert normalized["units"][1]["required_capabilities"] == ["verification"]


def test_model_cannot_make_implementation_unstaffable_with_generic_capabilities() -> None:
    plan = _plan_document()
    plan["units"][0].update(
        {
            "artifact_kind": "implementation-change",
            "lifecycle_phase": "implementation",
            "authority": "modify",
            "mutation_scope": "workspace_write",
            "required_capabilities": ["analysis", "design"],
        }
    )

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][0]["required_capabilities"] == ["implementation"]


def test_repository_discovery_does_not_require_every_observed_language() -> None:
    plan = _plan_document()
    plan["units"][0].update(
        {
            "outcome": "Map repository code paths and trust boundaries",
            "artifact_kind": "analysis",
            "lifecycle_phase": "discovery",
            "domains": ["software-engineering"],
            "languages": ["javascript", "python", "typescript"],
            "frameworks": ["fastapi", "react"],
            "authority": "review",
            "mutation_scope": "read_only",
        }
    )

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][0]["languages"] == []
    assert normalized["units"][0]["frameworks"] == []


def test_specialized_discovery_preserves_required_language_expertise() -> None:
    plan = _plan_document()
    plan["units"][0].update(
        {
            "outcome": "Analyze repository authentication paths for Python vulnerabilities",
            "artifact_kind": "analysis",
            "lifecycle_phase": "discovery",
            "domains": ["security", "software-engineering"],
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "authority": "review",
            "mutation_scope": "read_only",
        }
    )

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][0]["languages"] == ["python"]
    assert normalized["units"][0]["frameworks"] == ["fastapi"]


def test_selection_audit_does_not_inherit_the_application_domain() -> None:
    plan = _plan_document()
    discovery = plan["units"][0]
    discovery.update(
        {
            "outcome": "Map the repository routing path",
            "artifact_kind": "analysis",
            "lifecycle_phase": "discovery",
            "domains": ["software-engineering"],
            "authority": "review",
            "mutation_scope": "read_only",
        }
    )
    plan["units"].append(
        {
            **dict(discovery),
            "unit_id": "unit-selection-audit",
            "outcome": "Audit the staffing decision for unsafe near-neighbor choices",
            "artifact_kind": "review-report",
            "lifecycle_phase": "review",
            "domains": ["workforce-governance", "software-engineering"],
            "required_capabilities": ["review"],
            "depends_on": ["unit-analyze"],
        }
    )

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][1]["domains"] == ["workforce-governance"]


def test_repository_security_review_requires_distinct_code_and_security_reviews() -> None:
    request = (
        "Review this repository security patch. First map the affected code path, then "
        "independently review correctness and audit exploitability without changing files."
    )
    plan = _plan_document()
    discovery = plan["units"][0]
    discovery.update(
        {
            "outcome": "Map repository code paths",
            "authority": "review",
            "required_capabilities": ["analysis"],
        }
    )
    combined_review = {
        **dict(discovery),
        "unit_id": "unit-security-review",
        "outcome": "Review correctness and exploitability",
        "artifact_kind": "review-report",
        "lifecycle_phase": "review",
        "domains": ["security", "software-engineering"],
        "required_capabilities": ["review"],
        "depends_on": ["unit-analyze"],
    }
    plan["units"].append(combined_review)
    collapsed = parse_work_unit_plan(_normalized_plan_response(plan))

    assert plan_policy_violations(request, collapsed) == ("plan_missing_code_correctness_review",)

    correctness_review = {
        **combined_review,
        "unit_id": "unit-correctness-review",
        "outcome": "Review code correctness",
        "domains": ["software-engineering"],
    }
    exploitability_review = {
        **combined_review,
        "unit_id": "unit-exploitability-review",
        "outcome": "Audit security exploitability",
        "depends_on": ["unit-analyze"],
    }
    plan["units"] = [discovery, correctness_review, exploitability_review]
    complete = parse_work_unit_plan(_normalized_plan_response(plan))

    assert plan_policy_violations(request, complete) == ()


def test_code_review_inherits_subject_domain_without_requiring_its_stack() -> None:
    plan = _plan_document()
    plan["units"][0].update(
        {
            "artifact_kind": "implementation-change",
            "lifecycle_phase": "implementation",
            "domains": ["software-engineering"],
            "languages": ["typescript"],
            "authority": "modify",
            "mutation_scope": "workspace_write",
        }
    )
    review = {
        **dict(plan["units"][0]),
        "unit_id": "unit-review",
        "outcome": "Independent code review",
        "artifact_kind": "review-report",
        "lifecycle_phase": "review",
        "domains": ["quality-assurance"],
        "required_capabilities": ["audit", "review"],
        "authority": "review",
        "mutation_scope": "read_only",
        "depends_on": ["unit-analyze"],
    }
    plan["units"].append(review)

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][1]["domains"] == ["software-engineering"]
    assert normalized["units"][1]["languages"] == []
    assert normalized["units"][1]["required_capabilities"] == ["review"]


def test_code_review_does_not_inherit_qa_domain_from_test_dependency() -> None:
    plan = _plan_document()
    plan["units"][0]["domains"] = ["software-engineering"]
    tests = {
        **dict(plan["units"][0]),
        "unit_id": "unit-tests",
        "outcome": "Implement tests",
        "artifact_kind": "test-code",
        "lifecycle_phase": "testing",
        "domains": ["quality-assurance"],
        "authority": "modify",
        "mutation_scope": "workspace_write",
        "depends_on": ["unit-analyze"],
    }
    review = {
        **dict(plan["units"][0]),
        "unit_id": "unit-review",
        "outcome": "Review implementation and tests",
        "artifact_kind": "review-report",
        "lifecycle_phase": "review",
        "domains": ["quality-assurance"],
        "authority": "review",
        "mutation_scope": "read_only",
        "depends_on": ["unit-analyze", "unit-tests"],
    }
    plan["units"].extend((tests, review))

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][2]["domains"] == ["software-engineering"]


def test_test_implementation_uses_quality_assurance_not_subject_domain() -> None:
    plan = _plan_document()
    plan["units"][0]["domains"] = ["software-engineering"]
    test_unit = {
        **dict(plan["units"][0]),
        "unit_id": "unit-tests",
        "outcome": "Implement failure-path tests",
        "artifact_kind": "test-code",
        "lifecycle_phase": "testing",
        "domains": ["software-engineering"],
        "required_capabilities": ["implementation", "testing"],
        "authority": "modify",
        "mutation_scope": "workspace_write",
        "depends_on": ["unit-analyze"],
    }
    plan["units"].append(test_unit)

    normalized = _normalized_plan_response(plan)

    assert normalized["units"][1]["domains"] == ["quality-assurance"]
    assert normalized["units"][1]["required_capabilities"] == ["testing"]


def test_semantically_invalid_provider_output_gets_one_bounded_repair_attempt() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    invalid = _compact_plan_document()
    invalid["units"].append(dict(invalid["units"][0]))
    responses = iter(
        (
            _result(invalid),
            _result(_compact_plan_document()),
        )
    )
    prompts: list[str] = []

    def invoke(*args, **kwargs):
        prompts.append(args[1])
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(balanced_call_budget=3),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert [attempt.status for attempt in outcome.attempts] == [
        "rejected",
        "applied",
    ]
    assert outcome.attempts[0].validation_detail == "work-unit plan contains duplicate unit ids"
    assert "work-unit plan contains duplicate unit ids" in prompts[1]


def test_configured_inference_failure_abstains_without_keyword_selection() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: None,
    )

    assert not outcome.accepted
    assert outcome.plan is None
    assert outcome.abstention_codes == ("workforce_inference_failed",)
    assert outcome.calls_used == 1
    assert outcome.attempts[0].status == "failed"


def test_wrong_but_structurally_valid_selection_is_rejected_by_deterministic_staffing() -> None:
    wrong = replace(
        _contract("wrong-neighbor"),
        outcomes=("Marketing prose",),
        domains=("marketing",),
    )
    snapshot = _snapshot(
        _contract("technical-analyst"),
        _contract("analysis-alternative"),
        wrong,
    )
    unsafe = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "ranked_semantic": [
                    _nominee("wrong-neighbor", 0.99, "required"),
                    _nominee("technical-analyst", 0.90, "forbidden"),
                    _nominee("analysis-alternative", 0.89, "forbidden"),
                ],
            }
        ]
    }
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(unsafe),
            _result(unsafe),
        )
    )

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert not outcome.accepted
    assert outcome.abstention_codes == ("workforce_inference_failed",)
    assert [attempt.status for attempt in outcome.attempts] == [
        "applied",
        "rejected",
        "rejected",
    ]
    assert outcome.staffing.units == ()


def test_inference_forbidden_near_neighbor_is_not_selected_despite_higher_score() -> None:
    snapshot = _snapshot(
        _contract("right-specialist"),
        _contract("plausible-wrong-neighbor"),
    )
    nominations = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "ranked_semantic": [
                    _nominee("plausible-wrong-neighbor", 0.99, "forbidden"),
                    _nominee("right-specialist", 0.90, "required"),
                ],
            }
        ]
    }
    responses = iter((_result(_compact_plan_document()), _result(nominations)))

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert outcome.staffing.units[0].selected == ("right-specialist",)
    assert outcome.proposal is not None
    assert outcome.proposal.units[0].forbidden == ("plausible-wrong-neighbor",)


def test_typed_shortlist_breaks_coverage_ties_with_unit_semantics() -> None:
    generic = replace(
        _contract("generic-evidence-reviewer"),
        outcomes=("Review accessibility compliance evidence",),
        artifact_kinds=("test-evidence",),
        lifecycle_phases=("testing",),
        domains=("quality-assurance",),
        authority="review",
    )
    analyzer = replace(
        _contract("test-results-analyzer"),
        outcomes=("Interpret completed automated test results and failure evidence",),
        artifact_kinds=("test-evidence",),
        lifecycle_phases=("testing",),
        domains=("quality-assurance",),
        authority="review",
    )
    plan = _plan_document()
    plan["units"][0].update(
        {
            "outcome": "Interpret completed automated test results",
            "artifact_kind": "test-evidence",
            "lifecycle_phase": "testing",
            "domains": ["quality-assurance"],
            "required_capabilities": ["verification"],
            "authority": "review",
        }
    )
    parsed = parse_work_unit_plan(_normalized_plan_response(plan))

    shortlist = _typed_shortlists(parsed, (generic, analyzer))

    assert shortlist[0]["candidates"][0]["agent_id"] == "test-results-analyzer"


def test_strict_mode_critic_can_only_veto_an_already_verified_team() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result({"approved": False, "reason_codes": ["wrong-neighbor-risk"]}),
        )
    )
    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config("strict"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert not outcome.accepted
    assert outcome.calls_used == 2
    assert [item.stage for item in outcome.attempts] == ["planner", "critic"]
    assert outcome.abstention_codes == ("staffing_critic_rejected", "wrong-neighbor-risk")


def test_fast_mode_uses_one_call_and_runtime_binds_plan_and_roster_hashes() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config("fast"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: _result(_compact_plan_document()),
    )

    assert outcome.accepted
    assert outcome.calls_used == 1
    assert [item.stage for item in outcome.attempts] == ["planner"]
    assert outcome.proposal is not None and outcome.plan is not None
    assert outcome.proposal.plan_hash == outcome.plan.plan_hash
    assert outcome.proposal.roster_fingerprint == snapshot.contract_fingerprint


def test_provider_and_stage_model_selection_are_explicit_and_case_insensitive() -> None:
    config = AgencyConfig(
        providers=(_provider("Primary"), _provider("Backup", model="backup-model")),
        workforce=WorkforceConfig(
            provider="backup",
            planner_model="cheap-planner",
            recruiter_model="task-agency-router",
        ),
    )

    planner = configured_workforce_providers(config, stage="planner")
    recruiter = configured_workforce_providers(config, stage="recruiter")

    assert [(item.name, item.model) for item in planner] == [("Backup", "cheap-planner")]
    assert [(item.name, item.model) for item in recruiter] == [("Backup", "task-agency-router")]


def test_no_provider_uses_conservative_typed_fallback_without_model_calls() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    outcome = plan_and_staff_workforce(
        "Analyze this repository code.",
        snapshot,
        config=AgencyConfig(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("called")),
    )

    assert outcome.accepted
    assert outcome.inference_mode == "deterministic"
    assert outcome.calls_used == 0
    assert outcome.attempts == ()
    assert outcome.staffing.units[0].selected == ("technical-analyst",)


def test_deterministic_plan_prioritizes_explicit_security_review_over_generic_code_terms() -> None:
    plan, reasons = deterministic_work_plan(
        "Review application security design and audit threat boundaries.",
        context=_context(),
    )

    assert reasons == ()
    assert plan is not None
    assert len(plan.units) == 1
    assert plan.units[0].unit_id == "unit-security-review"
    assert plan.units[0].domains == ("security",)
    assert plan.units[0].required_capabilities == ("application-attack-surfaces",)


def test_security_implementation_schedules_review_without_optional_scanner() -> None:
    context = _context()
    assert "security-analysis" not in context.available_tools

    plan, reasons = deterministic_work_plan(
        "Implement an authentication security fix in this codebase.",
        context=context,
    )

    assert reasons == ()
    assert plan is not None
    by_id = {unit.unit_id: unit for unit in plan.units}
    assert "unit-security-review" in by_id
    assert by_id["unit-security-review"].depends_on == ("unit-tests",)
    assert by_id["unit-security-review"].required_capabilities == (
        "exploitability-regression-analysis",
    )
    assert "security-analysis" not in by_id["unit-security-review"].required_tools


def test_deterministic_plan_preserves_review_then_document_dependencies() -> None:
    plan, reasons = deterministic_work_plan(
        "Review the authentication design, then document the deployment workflow.",
        context=_context(),
    )

    assert reasons == ()
    assert plan is not None
    assert [item.unit_id for item in plan.units] == [
        "unit-source-review",
        "unit-documentation",
    ]
    assert plan.units[1].depends_on == ("unit-source-review",)


def test_no_provider_code_change_entails_coding_testing_and_independent_review() -> None:
    base = _contract("technical-analyst")
    implementation = replace(
        base,
        worker_id="worker:python-application-engineer",
        agent_id="python-application-engineer",
        display_name="Python Application Engineer",
        archetype="implementer",
        outcomes=("Python application delivery",),
        artifact_kinds=("implementation-change",),
        lifecycle_phases=("implementation",),
        stacks=("python",),
        authority="modify",
        composition=CompositionContract(independence_class="implementation"),
    )
    testing = replace(
        base,
        worker_id="worker:software-test-engineer",
        agent_id="software-test-engineer",
        display_name="Software Test Engineer",
        archetype="tester",
        outcomes=("Integration tests and failure path tests",),
        artifact_kinds=("test-code",),
        lifecycle_phases=("testing",),
        domains=("quality-assurance",),
        authority="modify",
        composition=CompositionContract(independence_class="testing"),
    )
    reviewer = replace(
        base,
        worker_id="worker:code-reviewer",
        agent_id="code-reviewer",
        display_name="Code Reviewer",
        archetype="reviewer",
        outcomes=("Independent review of diffs",),
        artifact_kinds=("review-report",),
        lifecycle_phases=("review",),
        authority="review",
        composition=CompositionContract(independence_class="review"),
    )
    results = replace(
        base,
        worker_id="worker:test-results-analyzer",
        agent_id="test-results-analyzer",
        display_name="Test Results Analyzer",
        archetype="tester",
        outcomes=("Analyze supplied test results and coverage evidence",),
        artifact_kinds=("test-evidence",),
        lifecycle_phases=("testing",),
        domains=("quality-assurance",),
        authority="review",
        tool_classes=("test-execution",),
        composition=CompositionContract(independence_class="testing-quality-analysis"),
    )

    outcome = plan_and_staff_workforce(
        "Fix this Python application bug.",
        _snapshot(implementation, testing, reviewer, results),
        config=AgencyConfig(),
        context=_context(),
    )

    assert outcome.accepted, [
        (
            unit.unit_id,
            unit.ranked_executable,
            unit.negative_evidence,
            unit.abstention_reasons,
        )
        for unit in outcome.proposal.units
    ]
    assert [item.unit_id for item in outcome.staffing.units] == [
        "unit-implementation",
        "unit-tests",
        "unit-code-review",
        "unit-test-results",
    ]
    assert [item.selected for item in outcome.staffing.units] == [
        ("python-application-engineer",),
        ("software-test-engineer",),
        ("code-reviewer",),
        ("test-results-analyzer",),
    ]
    assert outcome.staffing.units[-1].timing == "after_artifact"


def test_no_provider_ambiguous_or_trivial_request_stays_with_resident_managers() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))

    trivial = plan_and_staff_workforce(
        "hello",
        snapshot,
        config=AgencyConfig(),
        context=_context(),
    )
    ambiguous = plan_and_staff_workforce(
        "What do you think?",
        snapshot,
        config=AgencyConfig(),
        context=_context(),
    )

    assert trivial.abstention_codes == ("deterministic_request_trivial",)
    assert ambiguous.abstention_codes == ("deterministic_request_ambiguous",)
    assert trivial.plan is None and ambiguous.plan is None


def test_workforce_attempts_persist_router_alias_and_reconciled_actual_model() -> None:
    class ReceiptStore:
        def __init__(self) -> None:
            self.receipts: list[dict[str, object]] = []

        def record_model_receipt(self, **values: object) -> None:
            self.receipts.append(values)

    store = ReceiptStore()
    outcome = WorkforceRoutingOutcome(
        status="accepted",
        mode="fast",
        inference_mode="inferred",
        plan=None,
        proposal=None,
        staffing=StaffingDecision("accepted", (), ()),
        attempts=(
            WorkforceInferenceAttempt(
                stage="combined",
                provider_name="agency-router",
                provider_type="litellm",
                requested_model="task-agency-router",
                model_group="task-agency-router",
                actual_model="openai/gpt-5.6-mini",
                model_receipt_source="response.body.model",
                status="applied",
                reason_code="structured_response_applied",
                latency_ms=12,
            ),
        ),
        abstention_codes=(),
        calls_used=1,
    )

    _record_workforce_model_receipts(
        store,  # type: ignore[arg-type]
        outcome,
        session_id="session",
        trace_id="trace",
        host="codex",
    )

    assert store.receipts == [
        {
            "trace_id": "trace",
            "session_id": "session",
            "host": "codex",
            "requested_model": "task-agency-router",
            "model_group": "task-agency-router",
            "resolved_provider": "agency-router",
            "resolved_model": "openai/gpt-5.6-mini",
            "attempted_fallbacks": 0,
            "source": "wrapper",
            "status": "success",
        }
    ]


def test_workforce_routing_reports_only_rejected_or_failed_attempts_as_failures() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    deterministic = deterministic_plan_and_staff(
        "Analyze the repository implementation.",
        snapshot,
        config=AgencyConfig(),
        context=StaffingContext(
            "codex",
            "windows",
            frozenset({"native-delegation", "repository-read"}),
            snapshot.generation,
        ),
    )
    outcome = WorkforceRoutingOutcome(
        status="accepted",
        mode="balanced",
        inference_mode="inferred",
        plan=deterministic.plan,
        proposal=deterministic.proposal,
        staffing=deterministic.staffing,
        attempts=(
            WorkforceInferenceAttempt(
                stage="planner",
                provider_name="codex-subscription",
                provider_type="cli",
                requested_model="gpt-5.6-luna",
                model_group="",
                actual_model="gpt-5.6-luna",
                model_receipt_source="cli.explicit_model_argument",
                status="applied",
                reason_code="structured_response_applied",
                latency_ms=12,
            ),
            WorkforceInferenceAttempt(
                stage="recruiter",
                provider_name="codex-subscription",
                provider_type="cli",
                requested_model="gpt-5.6-luna",
                model_group="",
                actual_model="gpt-5.6-luna",
                model_receipt_source="cli.explicit_model_argument",
                status="rejected",
                reason_code="provider_response_contract_invalid",
                latency_ms=8,
            ),
        ),
        abstention_codes=(),
        calls_used=2,
    )

    routing = project_workforce_routing(
        outcome,
        (
            {
                "slug": "technical-analyst",
                "name": "Technical Analyst",
                "description": "Produces evidence-backed technical analysis.",
                "capabilities": ["technical-analysis"],
                "tags": ["software-engineering"],
                "required_tools": ["repository-read"],
                "evidence_requirements": ["Evidence-backed analysis"],
            },
        ),
        request="Analyze the repository implementation.",
        roster_count=1,
        contract_fingerprint=snapshot.contract_fingerprint,
    )

    assert routing["inference_failures"] == ["provider_response_contract_invalid"]
