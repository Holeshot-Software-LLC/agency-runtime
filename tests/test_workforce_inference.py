"""Inference-first workforce planning, recruitment, and receipt tests."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    InferenceConfig,
    InferenceProfile,
    ProviderEntry,
    WorkforceConfig,
)
from agency_runtime.core.preflight_failure import preflight_staffing_reason_codes
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
    _RECRUITER_REPAIR_SYSTEM,
    _RECRUITER_SYSTEM,
    NOMINATION_RESPONSE_SCHEMA,
    PLAN_RESPONSE_SCHEMA,
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
    _CallBudget,
    _explicit_indivisible_unit_request,
    _invoke_stage,
    _NominationAccumulator,
    _NominationValidationError,
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


def test_recruiter_schema_requires_explicit_staff_or_gap_decision() -> None:
    row = NOMINATION_RESPONSE_SCHEMA["properties"]["units"]["items"]

    assert "decision" in row["required"]
    assert row["properties"]["decision"]["enum"] == ["staff", "gap"]
    assert "minItems" not in row["properties"]["ranked_semantic"]


def test_writer_sentinel_declares_one_indivisible_inference_unit() -> None:
    request = (
        "Create one workspace-local file named writer-result.txt. This request is one "
        "indivisible implementation work unit for one filesystem implementation specialist. "
        "Do not split it into analysis, testing, review, or documentation units."
    )

    assert _explicit_indivisible_unit_request(request) is True
    assert (
        _explicit_indivisible_unit_request("Create and independently review the product.") is False
    )


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
                "decision": "staff",
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


def test_balanced_mode_always_uses_inference_for_planning_and_selection() -> None:
    snapshot = _snapshot(
        _contract("technical-analyst"), _contract("disabled-specialist", enabled=False)
    )
    calls: list[tuple[str, str, str]] = []

    def invoke(provider, prompt, _schema, **_kwargs):
        payload = json.loads(prompt)
        calls.append((provider.name, provider.model, prompt))
        if "planning_taxonomy" in payload:
            assert "roster" not in payload
            assert "detail_cards" not in payload
            assert "analysis" in payload["planning_taxonomy"]["known_capability_ids"]
            return _result(_compact_plan_document())
        assert payload["detail_cards"]
        return _result(_nomination_document())

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
    assert all(item.model_group == "router-alias" for item in outcome.attempts)
    assert all(item.actual_model == "gpt-5.6-mini" for item in outcome.attempts)
    assert outcome.staffing.units[0].selected == ("technical-analyst",)


def test_explicit_indivisible_request_bounds_planner_prompt_schema_and_parser() -> None:
    reviewer = replace(
        _contract("code-reviewer"),
        outcomes=("Code review",),
        capability_ids=("review",),
        artifact_kinds=("review-report",),
        lifecycle_phases=("review",),
        authority="review",
    )
    snapshot = _snapshot(reviewer)
    planner_calls = 0

    def invoke(provider, prompt, schema, **_kwargs):
        nonlocal planner_calls
        payload = json.loads(prompt.split("\n\n[RUNTIME VALIDATION FEEDBACK]", 1)[0])
        if "planning_taxonomy" not in payload:
            return _result(_nomination_document("code-reviewer"))
        planner_calls += 1
        assert payload["constraints"]["max_primary_units"] == 1
        assert payload["constraints"]["explicit_indivisible_unit"] is True
        assert payload["constraints"]["required_artifact_kind"] == "review-report"
        assert schema["properties"]["units"]["maxItems"] == 1
        assert schema["properties"]["units"]["items"]["properties"]["artifact_kind"] == {
            "enum": ["review-report"],
            "type": "string",
        }
        document = _compact_plan_document()
        if planner_calls == 1:
            document["units"].append(
                {
                    **document["units"][0],
                    "unit_id": "unit-extra",
                    "depends_on": ["unit-analyze"],
                }
            )
        else:
            document["units"][0].update(
                {
                    "outcome": "Review the requested behavioral regression risk",
                    "artifact_kind": "review-report",
                    "capability_ids": ["review"],
                }
            )
        return _result(document)

    outcome = plan_and_staff_workforce(
        "Treat this runtime repair as exactly one indivisible review work unit. Do not split it.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
        required_planned_artifact_kind="review-report",
    )

    assert outcome.accepted
    assert planner_calls == 2
    assert len(outcome.plan.units) == 1
    assert [item.status for item in outcome.attempts] == [
        "rejected",
        "applied",
        "applied",
    ]


def test_explicit_indivisible_implementation_unit_embeds_assurance() -> None:
    writer = replace(
        _contract("filesystem-implementation-specialist"),
        outcomes=("Workspace file implementation",),
        artifact_kinds=("implementation-change",),
        lifecycle_phases=("implementation",),
        authority="modify",
        tool_classes=("repository-write",),
    )
    snapshot = _snapshot(writer)
    calls: list[str] = []

    def invoke(_provider, prompt, _schema, **_kwargs):
        payload = json.loads(prompt)
        calls.append("planner" if "planning_taxonomy" in payload else "recruiter")
        if "planning_taxonomy" in payload:
            document = _compact_plan_document()
            document["units"][0].update(
                {
                    "outcome": "Create and verify the exact workspace file",
                    "artifact_kind": "implementation-change",
                }
            )
            return _result(document)
        assert payload["response_contract"]["separate_independent_assurance_required"] is False
        return _result(_nomination_document("filesystem-implementation-specialist"))

    outcome = plan_and_staff_workforce(
        "Create one workspace-local file as one indivisible implementation work unit for one "
        "filesystem implementation specialist. Do not split this into testing or review units.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert calls == ["planner", "recruiter"]
    assert outcome.staffing.units[0].selected == ("filesystem-implementation-specialist",)


def test_disabled_only_candidate_cannot_be_appointed_by_online_fallback() -> None:
    snapshot = _snapshot(_contract("technical-analyst", enabled=False))

    # ADR-0087: with a provider configured the recruiter is primary. The planner
    # and recruiter run, but the only nomination is outside the enabled
    # candidate cards. The runtime must abstain rather than deterministically
    # appointing that worker.
    responses = iter(
        [
            _result(_compact_plan_document()),
            _result(_nomination_document("technical-analyst")),
            _result(_nomination_document("technical-analyst")),
        ]
    )

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert not outcome.accepted
    assert outcome.calls_used == 3
    assert [item.stage for item in outcome.attempts] == [
        "planner",
        "recruiter",
        "recruiter",
    ]
    assert [item.status for item in outcome.attempts] == ["applied", "rejected", "rejected"]
    assert outcome.proposal is None
    assert outcome.decision_source == "none"


def test_warm_route_reuses_version_bound_plan_and_inference_selection() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    calls = 0

    def invoke(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        payload = json.loads(_args[1])
        return _result(
            _compact_plan_document() if "planning_taxonomy" in payload else _nomination_document()
        )

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
    assert calls == 2
    assert first.cache_hits == ()
    assert second.cache_hits == ("plan", "recruiter")
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
        payload = json.loads(_args[1])
        return _result(
            _compact_plan_document() if "planning_taxonomy" in payload else _nomination_document()
        )

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

    assert calls == 16


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
    assert second.cache_hits == ("plan", "recruiter")
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
        "decision": "staff",
        "ranked_semantic": [
            _nominee("technical-analyst", 0.98),
            _nominee("analysis-alternative", 0.90, "acceptable"),
        ],
    }
    system_prompts: list[str] = []

    def invoke(_provider, _prompt, _schema, **kwargs):
        system_prompts.append(kwargs["system_prompt"])
        if len(system_prompts) == 1:
            return _result(plan)
        if len(system_prompts) == 2:
            return _result({"units": [first_row]})
        repair_system = system_prompts[-1]
        if (
            "Return exactly one corrected unit row for every listed failed unit"
            not in repair_system
            or "Omit every unlisted planned unit" not in repair_system
            or "Never omit a unit" in repair_system
        ):
            return None
        return _result({"units": [second_row]})

    outcome = plan_and_staff_workforce(
        "Analyze two independent repository concerns.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [(item.stage, item.status) for item in outcome.attempts] == [
        ("planner", "applied"),
        ("recruiter", "rejected"),
        ("recruiter", "applied"),
    ]
    assert outcome.attempts[1].validation_detail == (
        "workforce nomination failures: unit-analyze-second=missing_work_unit"
    )
    assert "Return exactly one unit row for every planned unit" in system_prompts[1]
    assert [item.unit_id for item in outcome.staffing.units] == [
        "unit-analyze",
        "unit-analyze-second",
    ]


def test_recruiter_repair_rejects_rows_outside_recorded_failure_set() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    plan_document = _plan_document()
    plan_document["units"][0]["required_capabilities"] = ["analysis"]
    second = json.loads(json.dumps(plan_document["units"][0]))
    second["unit_id"] = "unit-analyze-second"
    second["outcome"] = "Complete a second independent technical analysis"
    plan_document["units"].append(second)
    plan = parse_work_unit_plan(plan_document)
    parser = _NominationAccumulator(
        plan,
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        allowed_candidate_ids=frozenset({"technical-analyst", "analysis-alternative"}),
    )
    first_row = _nomination_document()["units"][0]
    first_row["ranked_semantic"].append(_nominee("analysis-alternative", 0.90, "acceptable"))
    second_row = {
        "unit_id": "unit-analyze-second",
        "decision": "staff",
        "ranked_semantic": [
            _nominee("technical-analyst", 0.98),
            _nominee("analysis-alternative", 0.90, "acceptable"),
        ],
    }
    replacement_first = json.loads(json.dumps(first_row))
    replacement_first["ranked_semantic"] = [
        _nominee("analysis-alternative", 0.99),
        _nominee("technical-analyst", 0.98, "acceptable"),
    ]

    with pytest.raises(_NominationValidationError) as initial:
        parser.parse({"units": [first_row]})
    assert [failure.unit_id for failure in initial.value.failures] == ["unit-analyze-second"]

    with pytest.raises(ValueError, match="repair rows do not match failed units"):
        parser.parse({"units": [replacement_first, second_row]})

    proposal = parser.parse({"units": [second_row]})
    assert proposal.units[0].selected == ("technical-analyst",)
    assert proposal.units[1].selected == ("technical-analyst",)


def test_recruiter_repair_receives_every_invalid_unit_and_preserves_valid_rows() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    plan_document = _plan_document()
    plan_document["request_summary"] = "Analyze nine independent repository concerns."
    plan_document["units"] = []
    nominations: list[dict[str, Any]] = []
    valid_by_id: dict[str, dict[str, Any]] = {}
    invalid_unit_ids = ("unit-analysis-03", "unit-analysis-07")
    for index in range(1, 10):
        unit_id = f"unit-analysis-{index:02d}"
        unit = json.loads(json.dumps(_plan_document()["units"][0]))
        unit["unit_id"] = unit_id
        unit["outcome"] = f"Complete independent technical analysis {index}"
        unit["required_capabilities"] = ["analysis"]
        plan_document["units"].append(unit)
        valid_row = {
            "unit_id": unit_id,
            "decision": "staff",
            "ranked_semantic": [
                _nominee("technical-analyst", 0.98),
                _nominee("analysis-alternative", 0.90, "acceptable"),
            ],
        }
        valid_by_id[unit_id] = valid_row
        if unit_id in invalid_unit_ids:
            invalid_row = json.loads(json.dumps(valid_row))
            invalid_row["ranked_semantic"] = [
                _nominee("technical-analyst", 0.98, "forbidden"),
                _nominee("analysis-alternative", 0.90, "forbidden"),
            ]
            nominations.append(invalid_row)
        else:
            nominations.append(valid_row)

    plan = parse_work_unit_plan(plan_document)
    parser = _NominationAccumulator(
        plan,
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        allowed_candidate_ids=frozenset({"technical-analyst", "analysis-alternative"}),
    )
    prompts: list[str] = []
    system_prompts: list[str] = []
    repair_unit_ids: list[str] = []

    def invoke(_provider, prompt, _schema, **kwargs):
        prompts.append(prompt)
        system_prompts.append(kwargs["system_prompt"])
        if len(prompts) == 1:
            return _result({"units": nominations})
        if (
            "Return exactly one corrected unit row for every listed failed unit"
            not in system_prompts[-1]
            or "Omit every unlisted planned unit" not in system_prompts[-1]
            or "Never omit a unit" in system_prompts[-1]
        ):
            return None
        feedback = prompt.partition("[RUNTIME VALIDATION FEEDBACK]")[2]
        repair_unit_ids.extend(unit_id for unit_id in invalid_unit_ids if unit_id in feedback)
        return _result({"units": [valid_by_id[unit_id] for unit_id in repair_unit_ids]})

    proposal, attempts, failure = _invoke_stage(
        stage="recruiter",
        providers=(_provider(),),
        prompt="production-shaped nine-unit recruiter request",
        schema=NOMINATION_RESPONSE_SCHEMA,
        system_prompt=_RECRUITER_SYSTEM,
        budget=_CallBudget(2),
        invoker=invoke,
        parser=parser.parse,
        before_provider=parser.reset,
        repair_system_prompt=_RECRUITER_REPAIR_SYSTEM,
    )

    assert failure == ""
    assert proposal is not None
    assert [attempt.status for attempt in attempts] == [
        "rejected",
        "applied",
    ]
    detail = attempts[0].validation_detail
    assert "unit-analysis-03=staff_without_safe_team" in detail
    assert "unit-analysis-07=staff_without_safe_team" in detail
    assert prompts[1].count("staff_without_safe_team") == 2
    assert "Return exactly one unit row for every planned unit" in system_prompts[0]
    assert repair_unit_ids == list(invalid_unit_ids)
    assert [item.unit_id for item in proposal.units] == [
        f"unit-analysis-{index:02d}" for index in range(1, 10)
    ]
    assert all(item.selected == ("technical-analyst",) for item in proposal.units)


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
    assert prompts[1]["response_contract"]["maximum_selected_per_unit"] == 4
    assert prompts[1]["response_contract"]["staff_decision_requires_safe_typed_coverage"]
    assert prompts[1]["response_contract"]["gap_decision_requires_no_safe_team"]
    assert outcome.proposal is not None
    row = outcome.proposal.units[0]
    assert [(item.agent_id, item.score) for item in row.ranked_semantic] == [
        ("technical-analyst", 1.0),
        ("analysis-alternative", 0.9),
    ]
    assert row.margin == 0.1


def test_recruiter_receives_complete_positive_and_negative_activation_contract() -> None:
    qualifiers = tuple(f"preferred activation {index}" for index in range(1, 5))
    exclusions = tuple(f"avoid activation {index}" for index in range(1, 5))
    snapshot = _snapshot(
        replace(
            _contract("code-intelligence-evaluator"),
            scope_qualifiers=qualifiers,
            not_for=exclusions,
        )
    )
    nominations = _nomination_document()
    nominations["units"][0]["ranked_semantic"][0]["agent_id"] = "code-intelligence-evaluator"
    prompts: list[dict[str, Any]] = []
    systems: list[str] = []
    responses = iter((_result(_compact_plan_document()), _result(nominations)))

    def invoke(_provider, prompt, _schema, **kwargs):
        prompts.append(json.loads(prompt))
        systems.append(str(kwargs["system_prompt"]))
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Evaluate two code-intelligence tools for this repository.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert prompts[1]["detail_cards"] == [
        {
            "agent_id": "code-intelligence-evaluator",
            "display_name": "Code Intelligence Evaluator",
            "outcomes": ["Technical analysis"],
            "scope_qualifiers": list(qualifiers),
            "not_for": list(exclusions),
        }
    ]
    assert "open-ended pool" in systems[1]
    assert "who would I want handling this exact work" in systems[1]
    assert "parent model or a generalist" in systems[1]
    assert "declare a gap" in systems[1]


def test_open_ended_pool_can_declare_gap_without_inventing_a_roster_candidate() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    novel_plan = _compact_plan_document()
    novel_plan["request_summary"] = "Evaluate a quantum compiler build system."
    novel_plan["units"][0].update(
        outcome="Evaluate the quantum compiler build system",
        domains=["quantum-build-systems"],
        novel_capability="quantum-build-evaluation",
    )
    gap = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "gap",
                "ranked_semantic": [],
            }
        ]
    }
    recruiter_prompt: dict[str, Any] = {}
    responses = iter((_result(novel_plan), _result(gap)))

    def invoke(_provider, prompt, _schema, **_kwargs):
        payload = json.loads(prompt)
        if "detail_cards" in payload:
            recruiter_prompt.update(payload)
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Evaluate an unfamiliar quantum compiler build system.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    # ADR-0118: the recruiter sees every enabled specialist's card (no
    # deterministic domain filter hides candidates) and still declares a gap
    # because none faithfully matches the quantum-build-system ideal.
    assert len(recruiter_prompt["detail_cards"]) == 1
    assert recruiter_prompt["detail_cards"][0]["agent_id"] == "technical-analyst"
    assert not outcome.accepted
    assert outcome.inference_mode == "inferred"
    assert outcome.decision_source == "inferred"
    assert outcome.proposal is not None
    assert outcome.proposal.units[0].ranked_semantic == ()
    assert outcome.proposal.units[0].selected == ()
    assert outcome.proposal.units[0].abstention_reasons == ("inference-declared-gap",)


def test_semantically_invalid_provider_output_gets_one_bounded_repair_attempt() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    invalid = _compact_plan_document()
    invalid["units"].append(dict(invalid["units"][0]))
    responses = iter(
        (
            _result(invalid),
            _result(_compact_plan_document()),
            _result(_nomination_document()),
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
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "rejected",
        "applied",
        "applied",
    ]
    assert outcome.attempts[0].validation_detail == "work-unit plan contains duplicate unit ids"
    assert "work-unit plan contains duplicate unit ids" in prompts[1]


def test_planner_repair_enforces_configured_work_unit_limit_before_recruitment() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    oversized = _compact_plan_document()
    template = oversized["units"][0]
    oversized["units"] = [
        {
            **template,
            "unit_id": f"unit-analyze-{index}",
            "outcome": f"Complete technical analysis {index}",
        }
        for index in range(9)
    ]
    repaired = _compact_plan_document()
    responses = iter(
        (
            _result(oversized),
            _result(repaired),
            _result(_nomination_document()),
        )
    )
    prompts: list[str] = []

    def invoke(*args, **kwargs):
        prompts.append(args[1])
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(max_work_units=8),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "rejected",
        "applied",
        "applied",
    ]
    assert outcome.attempts[0].validation_detail == (
        "compact intent units must contain at most 8 items"
    )
    assert "compact intent units must contain at most 8 items" in prompts[1]


def test_planner_clamps_large_configured_limit_to_compact_schema_ceiling() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(_nomination_document()),
        )
    )
    planner_limits: list[int] = []

    def invoke(_provider, prompt, _schema, **_kwargs):
        payload = json.loads(prompt)
        if "constraints" in payload:
            planner_limits.append(payload["constraints"]["max_primary_units"])
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(max_work_units=64),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert planner_limits == [16]


def test_planner_repair_receives_exact_assurance_graph_and_remains_inference_owned() -> None:
    request = (
        "Build a Python API and TypeScript dashboard, validate state-changing operations for "
        "security, and add tests."
    )

    def unit(
        unit_id: str,
        artifact_kind: str,
        domain: str,
        capability: str,
        depends_on: list[str],
    ) -> dict[str, Any]:
        return {
            "unit_id": unit_id,
            "outcome": unit_id.replace("unit-", "").replace("-", " "),
            "artifact_kind": artifact_kind,
            "domains": [domain],
            "stacks": [],
            "capability_ids": [capability],
            "novel_capability": "",
            "depends_on": depends_on,
        }

    implementation = unit(
        "unit-implementation",
        "implementation-change",
        "software-engineering",
        "implementation",
        [],
    )
    tests = unit(
        "unit-tests",
        "test-code",
        "quality-assurance",
        "testing",
        [],
    )
    code_review = unit(
        "unit-code-review",
        "review-report",
        "software-engineering",
        "review",
        ["unit-implementation"],
    )
    incomplete = {
        "request_summary": request,
        "units": [implementation, tests, code_review],
    }
    repaired = {
        "request_summary": request,
        "units": [
            implementation,
            {**tests, "depends_on": ["unit-implementation"]},
            {**code_review, "depends_on": ["unit-tests"]},
            unit(
                "unit-test-evidence",
                "test-evidence",
                "quality-assurance",
                "testing",
                ["unit-tests"],
            ),
            unit(
                "unit-security-review",
                "review-report",
                "security",
                "review",
                ["unit-tests"],
            ),
        ],
    }

    def specialist(
        agent_id: str,
        *,
        artifact: str,
        lifecycle: str,
        domain: str,
        capability: str,
        authority: str,
        tools: tuple[str, ...],
    ) -> WorkforceContract:
        return replace(
            _contract(agent_id),
            outcomes=(f"Own {artifact} work",),
            capability_ids=(capability,),
            artifact_kinds=(artifact,),
            lifecycle_phases=(lifecycle,),
            domains=(domain,),
            authority=authority,
            tool_classes=tools,
        )

    selected = {
        "unit-implementation": "api-implementer",
        "unit-tests": "test-author",
        "unit-code-review": "code-reviewer",
        "unit-test-evidence": "test-results-analyzer",
        "unit-security-review": "application-security-reviewer",
    }
    snapshot = _snapshot(
        specialist(
            "api-implementer",
            artifact="implementation-change",
            lifecycle="implementation",
            domain="software-engineering",
            capability="implementation",
            authority="modify",
            tools=("repository-read", "repository-write", "code-execution"),
        ),
        specialist(
            "test-author",
            artifact="test-code",
            lifecycle="testing",
            domain="quality-assurance",
            capability="testing",
            authority="modify",
            tools=(
                "repository-read",
                "repository-write",
                "code-execution",
                "test-execution",
            ),
        ),
        specialist(
            "code-reviewer",
            artifact="review-report",
            lifecycle="review",
            domain="software-engineering",
            capability="review",
            authority="review",
            tools=("repository-read",),
        ),
        specialist(
            "test-results-analyzer",
            artifact="test-evidence",
            lifecycle="testing",
            domain="quality-assurance",
            capability="testing",
            authority="review",
            tools=("repository-read", "test-execution"),
        ),
        specialist(
            "application-security-reviewer",
            artifact="review-report",
            lifecycle="review",
            domain="security",
            capability="review",
            authority="review",
            tools=("repository-read",),
        ),
    )
    prompts: list[str] = []

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            initial = json.loads(prompt)
            contract = initial["constraints"]["plan_acceptance_contract"]
            assert contract["code_mutation"]["required_artifact_kinds"] == [
                "implementation-change",
                "test-code",
                "review-report",
                "test-evidence",
            ]
            return _result(incomplete)
        if len(prompts) == 2:
            feedback = json.loads(prompt.partition("[RUNTIME VALIDATION FEEDBACK]\n")[2])
            codes = [item["code"] for item in feedback["violations"]]
            assert codes == [
                "plan_missing_test_evidence_review",
                "plan_tests_not_ordered_after_implementation",
                "plan_missing_security_review",
            ]
            assert all(item["required_correction"] for item in feedback["violations"])
            return _result(repaired)
        nominations = {
            "units": [
                {
                    "unit_id": item["unit_id"],
                    "decision": "staff",
                    "ranked_semantic": [_nominee(selected[item["unit_id"]], 0.98)],
                }
                for item in repaired["units"]
            ]
        }
        return _result(nominations)

    outcome = plan_and_staff_workforce(
        request,
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "rejected",
        "applied",
        "applied",
    ]
    assert outcome.plan is not None
    assert [item.unit_id for item in outcome.plan.units] == [
        item["unit_id"] for item in repaired["units"]
    ]
    assert {item for row in outcome.staffing.units for item in row.selected} == set(
        selected.values()
    )


def test_default_fast_mode_funds_recruiter_contract_repair_after_planning() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    invalid = _nomination_document()
    del invalid["units"][0]["decision"]
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(invalid),
            _result(_nomination_document()),
        )
    )

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "applied",
        "rejected",
        "applied",
    ]
    assert outcome.attempts[1].reason_code == "provider_response_contract_invalid"


def test_default_fast_mode_funds_one_repair_for_each_inference_stage() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    invalid_plan = _compact_plan_document()
    invalid_plan["units"].append(dict(invalid_plan["units"][0]))
    invalid_nomination = _nomination_document()
    del invalid_nomination["units"][0]["decision"]
    responses = iter(
        (
            _result(invalid_plan),
            _result(_compact_plan_document()),
            _result(invalid_nomination),
            _result(_nomination_document()),
        )
    )

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert outcome.calls_used == 4
    assert [(attempt.stage, attempt.status) for attempt in outcome.attempts] == [
        ("planner", "rejected"),
        ("planner", "applied"),
        ("recruiter", "rejected"),
        ("recruiter", "applied"),
    ]
    assert outcome.attempts[0].reason_code == "provider_response_contract_invalid"
    assert outcome.attempts[2].reason_code == "provider_response_contract_invalid"


def test_configured_inference_failure_is_loud_without_keyword_selection() -> None:
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
    assert outcome.status == "inference_unavailable"
    assert outcome.abstention_codes == (
        "inference_unavailable",
        "workforce_inference_failed",
    )
    assert outcome.calls_used == 1
    assert outcome.attempts[0].status == "failed"


def test_staff_decision_without_safe_team_gets_one_bounded_inference_repair() -> None:
    wrong = replace(
        _contract("wrong-neighbor"),
        outcomes=("Planning guidance",),
        artifact_kinds=("plan",),
        lifecycle_phases=("planning",),
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
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("wrong-neighbor", 0.99, "required"),
                    _nominee("technical-analyst", 0.90, "forbidden"),
                    _nominee("analysis-alternative", 0.89, "forbidden"),
                ],
            }
        ]
    }
    repaired = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("technical-analyst", 0.99, "required"),
                    _nominee("analysis-alternative", 0.90, "acceptable"),
                    _nominee("wrong-neighbor", 0.89, "forbidden"),
                ],
            }
        ]
    }
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(unsafe),
            _result(repaired),
        )
    )

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(balanced_call_budget=3),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "applied",
        "rejected",
        "applied",
    ]
    assert outcome.attempts[1].validation_detail == (
        "workforce nomination failures: unit-analyze=staff_without_safe_team"
    )
    assert outcome.staffing.units[0].selected == ("technical-analyst",)


def test_whole_team_verifier_rejection_gets_one_bounded_recruiter_repair() -> None:
    snapshot = _snapshot(
        _contract("technical-analyst"),
        _contract("analysis-alternative"),
    )
    over_budget = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("technical-analyst", 0.99, "required"),
                    _nominee("analysis-alternative", 0.98, "required"),
                ],
            }
        ]
    }
    repaired = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("technical-analyst", 0.99, "required"),
                    _nominee("analysis-alternative", 0.98, "acceptable"),
                ],
            }
        ]
    }
    prompts: list[str] = []
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(over_budget),
            _result(repaired),
        )
    )

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(prompt)
        return next(responses)

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(mode="fast", max_selected_total=1),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "applied",
        "rejected",
        "applied",
    ]
    assert outcome.attempts[1].validation_detail == (
        "workforce staffing verification failures: "
        "global=selected_agent_budget_exceeded,"
        "global=delegated_agent_budget_exceeded"
    )
    feedback = json.loads(prompts[2].partition("[RUNTIME VALIDATION FEEDBACK]\n")[2])
    assert feedback["staffing_violations"] == [
        {"unit_id": "", "code": "selected_agent_budget_exceeded"},
        {"unit_id": "", "code": "delegated_agent_budget_exceeded"},
    ]
    assert outcome.staffing.units[0].selected == ("technical-analyst",)


def test_verifier_repair_exhaustion_is_terminal_and_not_cached() -> None:
    snapshot = _snapshot(
        _contract("technical-analyst"),
        _contract("analysis-alternative"),
    )
    over_budget = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("technical-analyst", 0.99, "required"),
                    _nominee("analysis-alternative", 0.98, "required"),
                ],
            }
        ]
    }
    repaired = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "staff",
                "ranked_semantic": [
                    _nominee("technical-analyst", 0.99, "required"),
                    _nominee("analysis-alternative", 0.98, "acceptable"),
                ],
            }
        ]
    }
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(over_budget),
            _result(over_budget),
        )
    )
    config = _config(mode="fast", max_selected_total=1)
    repair_phase = False
    second_calls = 0

    def invoke(*_args, **_kwargs):
        nonlocal second_calls
        if repair_phase:
            second_calls += 1
            return _result(repaired)
        return next(responses)

    first = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=config,
        context=_context(),
        invoker=invoke,
    )

    assert not first.accepted
    assert first.status == "inference_invalid"
    assert first.proposal is None
    assert first.calls_used == 3
    assert [attempt.status for attempt in first.attempts] == [
        "applied",
        "rejected",
        "rejected",
    ]
    assert tuple(reason.code for reason in first.staffing.abstention_reasons) == (
        "selected_agent_budget_exceeded",
        "delegated_agent_budget_exceeded",
    )
    failed_routing = project_workforce_routing(
        first,
        (),
        request="Analyze this implementation safely.",
        roster_count=snapshot.worker_count,
        contract_fingerprint=snapshot.contract_fingerprint,
    )
    assert preflight_staffing_reason_codes(failed_routing) == [
        "selected_agent_budget_exceeded",
        "delegated_agent_budget_exceeded",
    ]

    repair_phase = True

    second = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=config,
        context=_context(),
        invoker=invoke,
    )

    assert second.accepted
    assert second_calls == 1
    assert second.cache_hits == ("plan",)
    assert [attempt.status for attempt in second.attempts] == ["applied"]


def test_recruiter_repair_declares_gap_when_typed_recall_proves_uncovered_requirements() -> None:
    architect = replace(
        _contract("software-architect"),
        outcomes=("Design software architecture",),
        capability_ids=("architecture", "design"),
        artifact_kinds=("architecture-record",),
        lifecycle_phases=("design",),
        stacks=(),
        authority="plan",
    )
    snapshot = _snapshot(architect)
    # The uncovered proof lives on the capability axis: stacks are per-axis
    # wildcarded (undeclared stacks defer to inference), so a mandatory gap
    # needs a requirement no enabled worker's declared typed data covers.
    plan = {
        "request_summary": "Design an automated application architecture pipeline.",
        "units": [
            {
                "unit_id": "unit-architecture",
                "outcome": "Design the automated application architecture pipeline",
                "artifact_kind": "architecture-record",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["architecture", "design", "automation"],
                "novel_capability": "",
                "depends_on": [],
            }
        ],
    }
    unsafe = {
        "units": [
            {
                "unit_id": "unit-architecture",
                "decision": "staff",
                "ranked_semantic": [_nominee("software-architect", 0.98)],
            }
        ]
    }
    gap = {
        "units": [
            {
                "unit_id": "unit-architecture",
                "decision": "gap",
                "ranked_semantic": [],
            }
        ]
    }
    prompts: list[str] = []
    systems: list[str] = []

    def invoke(_provider, prompt, _schema, **kwargs):
        prompts.append(prompt)
        systems.append(kwargs["system_prompt"])
        if len(prompts) == 1:
            return _result(plan)
        if len(prompts) == 2:
            recruiter = json.loads(prompt)
            recall = recruiter["typed_recall"][0]
            assert recall["uncovered_requirements"] == [
                "capability:automation",
            ]
            assert recall["candidates"] == [
                {
                    "agent_id": "software-architect",
                    "covers": [
                        "artifact:architecture-record",
                        "authority:plan",
                        "capability:architecture",
                        "capability:design",
                        "domain:software-engineering",
                        "lifecycle:design",
                    ],
                    "execution_eligible": True,
                    "ineligibility_reasons": [],
                    "untyped_candidate": False,
                }
            ]
            return _result(unsafe)
        feedback = json.loads(prompt.partition("[RUNTIME VALIDATION FEEDBACK]\n")[2])
        assert feedback["failed_units"] == [
            {
                "unit_id": "unit-architecture",
                "code": "staff_without_safe_team",
                "required_correction": (
                    "Rank at least one semantically faithful candidate for this unit so the "
                    "staff decision can select a team, adding the coverage complements a "
                    "complete team needs within maximum_selected_per_unit. Declare gap only "
                    "when no supplied candidate is faithful."
                ),
            }
        ]
        return _result(gap)

    outcome = plan_and_staff_workforce(
        "Design an automated application architecture pipeline.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=invoke,
    )

    assert not outcome.accepted
    assert outcome.status == "abstained"
    assert outcome.inference_mode == "inferred"
    assert outcome.decision_source == "inferred"
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == [
        "applied",
        "rejected",
        "applied",
    ]
    assert systems[-1] == _RECRUITER_REPAIR_SYSTEM
    assert outcome.proposal is not None
    assert outcome.proposal.units[0].selected == ()
    assert outcome.proposal.units[0].abstention_reasons == ("inference-declared-gap",)


def test_recruiter_failure_detail_never_persists_unknown_candidate_content() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    unknown_candidate = "provider-secret-candidate-name"
    invalid = _nomination_document(unknown_candidate)
    invalid["units"][0]["ranked_semantic"][0]["positive_evidence"] = [
        "provider-authored-private-rationale"
    ]
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(invalid),
            _result(_nomination_document()),
        )
    )

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely without retaining provider content.",
        snapshot,
        config=_config(mode="fast"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert outcome.accepted
    detail = outcome.attempts[1].validation_detail
    assert detail == "workforce nomination failures: unit-analyze=invalid_candidate"
    assert unknown_candidate not in detail
    assert "provider-authored-private-rationale" not in detail


def test_explicit_gap_decision_survives_as_hiring_signal() -> None:
    snapshot = _snapshot(_contract("technical-analyst"), _contract("analysis-alternative"))
    gap = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "gap",
                "ranked_semantic": [
                    _nominee("technical-analyst", 0.99, "forbidden"),
                    _nominee("analysis-alternative", 0.90, "forbidden"),
                ],
            }
        ]
    }
    responses = iter((_result(_compact_plan_document()), _result(gap)))

    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: next(responses),
    )

    assert not outcome.accepted
    assert outcome.inference_mode == "inferred"
    assert outcome.calls_used == 2
    assert outcome.proposal is not None
    assert outcome.proposal.units[0].selected == ()
    assert outcome.proposal.units[0].abstention_reasons == ("inference-declared-gap",)


def test_inference_forbidden_near_neighbor_is_not_selected_despite_higher_score() -> None:
    snapshot = _snapshot(
        _contract("right-specialist"),
        _contract("plausible-wrong-neighbor"),
    )
    nominations = {
        "units": [
            {
                "unit_id": "unit-analyze",
                "decision": "staff",
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


def test_typed_shortlist_is_canonical_recall_without_local_ranking() -> None:
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
    parsed = parse_work_unit_plan(plan)

    shortlist = _typed_shortlists(parsed, (generic, analyzer))

    candidate_ids = [item["agent_id"] for item in shortlist[0]["candidates"]]
    assert candidate_ids == sorted(candidate_ids)
    assert candidate_ids == ["generic-evidence-reviewer", "test-results-analyzer"]
    assert shortlist[0]["role_anchors"] == []


def test_typed_recall_matrix_is_bounded_independently_of_roster_size() -> None:
    unit_template = _plan_document()["units"][0]
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Analyze sixteen repository concerns.",
            "units": [
                {
                    **unit_template,
                    "unit_id": f"unit-analyze-{index}",
                    "outcome": f"Complete technical analysis {index}",
                }
                for index in range(16)
            ],
        }
    )
    base = _contract("technical-analyst")
    contracts = tuple(
        replace(
            base,
            worker_id=f"worker:technical-analyst-{index:04d}",
            agent_id=f"technical-analyst-{index:04d}",
            display_name=f"Technical Analyst {index:04d}",
        )
        for index in range(500)
    )

    recall = _typed_shortlists(plan, contracts, context=_context())

    assert all(row["candidate_count"] == 500 for row in recall)
    assert all(row["candidate_rows_complete"] is False for row in recall)
    assert all(len(row["candidates"]) <= 24 for row in recall)
    assert len(json.dumps(recall, separators=(",", ":")).encode("utf-8")) <= 320 * 1024


def test_strict_mode_critic_can_only_veto_an_already_verified_team() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    responses = iter(
        (
            _result(_compact_plan_document()),
            _result(_nomination_document()),
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
    assert outcome.calls_used == 3
    assert [item.stage for item in outcome.attempts] == ["planner", "recruiter", "critic"]
    assert outcome.status == "inference_invalid"
    assert outcome.abstention_codes == (
        "inference_invalid",
        "staffing_critic_rejected",
        "wrong-neighbor-risk",
    )


def test_fast_mode_uses_planner_and_recruiter_and_binds_runtime_hashes() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    outcome = plan_and_staff_workforce(
        "Analyze this implementation safely.",
        snapshot,
        config=_config("fast"),
        context=_context(),
        invoker=lambda *_args, **_kwargs: _result(
            _compact_plan_document()
            if "planning_taxonomy" in json.loads(_args[1])
            else _nomination_document()
        ),
    )

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert [item.stage for item in outcome.attempts] == ["planner", "recruiter"]
    assert outcome.proposal is not None and outcome.plan is not None
    assert outcome.proposal.plan_hash == outcome.plan.plan_hash
    assert outcome.proposal.roster_fingerprint == snapshot.contract_fingerprint


def test_provider_and_stage_model_selection_are_explicit_and_case_insensitive() -> None:
    # ADR-0153: stage-specific model selection now lives on the inference
    # profile, not on the legacy workforce.*_model knobs. Two routes resolve
    # to two different profiles backed by the same providers chain.
    planner_profile = InferenceProfile(
        name="agency-planner",
        adapter="litellm",
        model="cheap-planner",
        base_url="https://router.example.test/v1",
        api_key_env="LITELLM_API_KEY",
    )
    recruiter_profile = InferenceProfile(
        name="agency-recruiter",
        adapter="litellm",
        model="task-agency-router",
        base_url="https://router.example.test/v1",
        api_key_env="LITELLM_API_KEY",
    )
    config = AgencyConfig(
        providers=(_provider("Primary"), _provider("Backup", model="backup-model")),
        workforce=WorkforceConfig(provider="backup"),
        inference=InferenceConfig(
            default_profile="agency-planner",
            routes={
                "workforce.planner": "agency-planner",
                "workforce.recruiter": "agency-recruiter",
            },
            profiles={
                "agency-planner": planner_profile,
                "agency-recruiter": recruiter_profile,
            },
        ),
    )

    planner = configured_workforce_providers(config, stage="planner", route_key="workforce.planner")
    recruiter = configured_workforce_providers(
        config, stage="recruiter", route_key="workforce.recruiter"
    )

    assert [(item.name, item.model) for item in planner] == [("agency-planner", "cheap-planner")]
    assert [(item.name, item.model) for item in recruiter] == [
        ("agency-recruiter", "task-agency-router")
    ]


def test_no_provider_declines_without_selecting_or_calling_the_model() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    outcome = plan_and_staff_workforce(
        "Analyze this repository code.",
        snapshot,
        config=AgencyConfig(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("called")),
    )

    assert not outcome.accepted
    assert outcome.status == "inference_unavailable"
    assert outcome.inference_mode == "unavailable"
    assert outcome.decision_source == "none"
    assert outcome.calls_used == 0
    assert outcome.attempts == ()
    assert outcome.abstention_codes == (
        "inference_unavailable",
        "workforce_provider_unavailable",
    )
    assert outcome.plan is None
    assert outcome.proposal is None
    assert outcome.staffing.units == ()


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
    assert plan.units[0].required_capabilities == ("review",)


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
    assert by_id["unit-security-review"].required_capabilities == ("review",)
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


def test_repository_readme_rewrite_is_documentation_not_code_implementation() -> None:
    request = "Rewrite the repository README installation guide and independently review it."
    plan, reasons = deterministic_work_plan(request, context=_context())

    assert reasons == ()
    assert plan is not None
    assert [item.unit_id for item in plan.units] == [
        "unit-documentation",
        "unit-documentation-review",
    ]
    assert plan.units[1].depends_on == ("unit-documentation",)
    assert plan_policy_violations(request, plan) == ()


def test_production_observability_does_not_imply_release_verification() -> None:
    request = "Add production application observability, failure telemetry, tests, and review."
    plan, reasons = deterministic_work_plan(request, context=_context())

    assert reasons == ()
    assert plan is not None
    assert all(item.lifecycle_phase != "release" for item in plan.units)
    assert plan_policy_violations(request, plan) == ()


def test_read_only_live_test_evidence_remains_in_the_testing_lifecycle() -> None:
    request = (
        "Diagnose why an installed runtime hook selected unrelated agents; inspect routing "
        "evidence, test the live integration locally, and independently audit the result."
    )

    plan, reasons = deterministic_work_plan(request, context=_context())

    assert reasons == ()
    assert plan is not None
    evidence = next(item for item in plan.units if item.artifact_kind == "test-evidence")
    assert evidence.lifecycle_phase == "testing"
    assert evidence.authority == "review"
    assert evidence.mutation_scope == "read_only"


def test_prohibited_mutation_words_do_not_create_fallback_code_or_docs_work() -> None:
    postgres, postgres_reasons = deterministic_work_plan(
        "Analyze why this PostgreSQL write query is slow. Do not write documentation or "
        "change application code; return measured query-plan findings only.",
        context=_context(),
    )
    clinical, clinical_reasons = deterministic_work_plan(
        "Summarize the supplied clinical-trial evidence and independently review its use "
        "in a legal document. Do not diagnose, code medical billing, or certify compliance.",
        context=_context(),
    )

    assert postgres is None
    assert postgres_reasons == ("deterministic_request_ambiguous",)
    assert clinical is None
    assert clinical_reasons == ("deterministic_request_ambiguous",)


def test_prohibited_mutation_words_do_not_trigger_implementation_policy() -> None:
    request = (
        "Analyze why this PostgreSQL write query is slow. Do not write documentation or "
        "change application code; return measured query-plan findings only."
    )
    plan = parse_work_unit_plan(_plan_document())

    assert plan_policy_violations(request, plan) == ()


def test_no_provider_code_change_declines_without_a_governed_team() -> None:
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

    assert not outcome.accepted
    assert outcome.status == "inference_unavailable"
    assert outcome.inference_mode == "unavailable"
    assert outcome.decision_source == "none"
    assert outcome.calls_used == 0
    assert outcome.attempts == ()
    assert outcome.abstention_codes[0] == "inference_unavailable"
    assert outcome.plan is None
    assert outcome.proposal is None
    assert outcome.staffing.units == ()


def test_no_provider_ambiguous_or_trivial_request_declines() -> None:
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

    for outcome in (trivial, ambiguous):
        assert outcome.status == "inference_unavailable"
        assert outcome.inference_mode == "unavailable"
        assert outcome.decision_source == "none"
        assert outcome.calls_used == 0
        assert outcome.plan is None
        assert outcome.staffing.units == ()


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


def test_reconcile_unit_id_handles_exact_match() -> None:
    """Exact plan unit_ids pass through unchanged (the common path)."""

    from agency_runtime.core.workforce.inference import _reconcile_unit_id

    plan_ids = frozenset({"unit-discovery", "unit-implementation", "unit-review"})
    assert _reconcile_unit_id("unit-discovery", plan_ids) == "unit-discovery"
    assert _reconcile_unit_id("UNIT-DISCOVERY", plan_ids) == "unit-discovery"


def test_reconcile_unit_id_maps_normalized_compound_word() -> None:
    """GLM-5.2 sometimes splits compound words (codepath→code-paths).

    The helper must reconcile the normalized form to the canonical plan id
    when exactly one plan unit is a high-prefix-similarity match.
    """

    from agency_runtime.core.workforce.inference import _reconcile_unit_id

    plan_ids = frozenset(
        {
            "unit-discovery-codepath-mapping",
            "unit-implementation-bugfix",
            "unit-review-correctness",
        }
    )
    # GLM-5.2 returned this instead of unit-discovery-codepath-mapping
    assert (
        _reconcile_unit_id("unit-discovery-code-paths", plan_ids)
        == "unit-discovery-codepath-mapping"
    )


def test_reconcile_unit_id_rejects_unknown_id() -> None:
    """Genuinely unknown unit_ids return None (no false reconciliation)."""

    from agency_runtime.core.workforce.inference import _reconcile_unit_id

    plan_ids = frozenset({"unit-discovery", "unit-implementation"})
    assert _reconcile_unit_id("unit-totally-different-thing", plan_ids) is None
    assert _reconcile_unit_id("", plan_ids) is None


def test_reconcile_unit_id_rejects_ambiguous_match() -> None:
    """When two plan ids match equally well, reconciliation is rejected."""

    from agency_runtime.core.workforce.inference import _reconcile_unit_id

    plan_ids = frozenset(
        {"unit-discovery-codepath-mapping", "unit-discovery-codepath-analysis"}
    )
    # Both share the same long prefix, so this is ambiguous
    assert _reconcile_unit_id("unit-discovery-code-paths", plan_ids) is None
