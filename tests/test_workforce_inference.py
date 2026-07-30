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
    NOMINATION_RESPONSE_SCHEMA,
    PLAN_RESPONSE_SCHEMA,
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
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
        "workforce staff decision cannot form a safe team: unit-analyze"
    )
    assert outcome.staffing.units[0].selected == ("technical-analyst",)


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
    parsed = parse_work_unit_plan(plan)

    shortlist = _typed_shortlists(parsed, (generic, analyzer))

    assert shortlist[0]["candidates"][0]["agent_id"] == "test-results-analyzer"


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
    assert outcome.abstention_codes == ("staffing_critic_rejected", "wrong-neighbor-risk")


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


def test_no_provider_declines_without_selecting_or_calling_the_model() -> None:
    snapshot = _snapshot(_contract("technical-analyst"))
    outcome = plan_and_staff_workforce(
        "Analyze this repository code.",
        snapshot,
        config=AgencyConfig(),
        context=_context(),
        invoker=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("called")),
    )

    # ADR-0088: with no inference provider configured the runtime runs a
    # deterministic typed-recall floor instead of declining. A non-trivial,
    # non-ambiguous ask against a governable single specialist is accepted by
    # that floor, but the model is never called (it cannot be, offline).
    assert outcome.accepted
    assert outcome.status == "accepted"
    assert outcome.inference_mode == "deterministic"
    assert outcome.decision_source == "deterministic"
    assert outcome.calls_used == 0
    assert outcome.attempts == ()
    assert outcome.abstention_codes == ()
    assert outcome.plan is not None
    assert outcome.staffing.accepted
    assert len(outcome.staffing.units) == 1
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

    # ADR-0088: with no provider the runtime runs the deterministic typed-recall
    # floor. A complete governed team (implementer, tester, reviewer, results
    # analyzer) on the bench is now staffed by that floor rather than declined,
    # and the model is never called. The inference-path outcome that previously
    # lived here moves to the inference suite; this test now anchors the floor's
    # ability to assemble the governed team offline.
    assert outcome.accepted
    assert outcome.status == "accepted"
    assert outcome.inference_mode == "deterministic"
    assert outcome.decision_source == "deterministic"
    assert outcome.calls_used == 0
    assert outcome.attempts == ()
    assert outcome.abstention_codes == ()
    assert outcome.plan is not None
    assert outcome.staffing.accepted
    assert len(outcome.staffing.units) == 4
    staffed = {agent for unit in outcome.staffing.units for agent in unit.selected}
    assert staffed == {
        "python-application-engineer",
        "software-test-engineer",
        "code-reviewer",
        "test-results-analyzer",
    }


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

    # ADR-0088: offline the deterministic floor still abstains on trivial or
    # ambiguous intent rather than force a wrong typed pick. The decline is now
    # stamped "deterministic_abstained" (decision_source "none") instead of the
    # old "declined_no_provider" hard decline.
    for outcome in (trivial, ambiguous):
        assert outcome.status == "declined"
        assert outcome.inference_mode == "deterministic_abstained"
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
