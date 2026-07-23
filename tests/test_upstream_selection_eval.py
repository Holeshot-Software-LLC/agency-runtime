from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from functools import lru_cache

import pytest

from agency_runtime.cli.eval_commands import (
    _upstream_selection_context,
    cmd_eval_upstream_selection,
)
from agency_runtime.core.config import AgencyConfig, ProviderEntry
from agency_runtime.core.evals.upstream_selection import (
    CASES,
    MINIMUM_RELEASE_SCENARIOS,
    SCHEMA,
    UPSTREAM_LICENSE_BYTES,
    UPSTREAM_LICENSE_SHA256,
    UPSTREAM_PROMPT_BYTES,
    UPSTREAM_PROMPT_SHA256,
    SelectionAssignment,
    SelectionRun,
    pinned_upstream_license,
    pinned_upstream_prompt,
    run_matched_upstream_selection_benchmark,
    score_selection_run,
)
from agency_runtime.core.evals.workforce_selection import (
    WorkforceSelectionCase,
    run_workforce_inference_eval,
)
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot
from agency_runtime.core.structured_provider import StructuredProviderResult
from agency_runtime.core.workforce.contract import (
    project_workforce_contract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.inference import (
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
)
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import known_contractor_agent
from agency_runtime.core.workforce.planning_contracts import ShadowEvidence, parse_work_unit_plan
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import (
    AbstentionReason,
    StaffingContext,
    StaffingDecision,
    VerifiedUnitStaffing,
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


def _context(snapshot: WorkforceIndexSnapshot) -> StaffingContext:
    tools = {"native-delegation"}
    for contract in snapshot.contracts:
        tools.update(contract.tool_classes)
    return StaffingContext("codex", "windows", frozenset(tools), snapshot.generation)


def _provider() -> ProviderEntry:
    return ProviderEntry(
        name="matched-provider",
        type="cli",
        transport="codex",
        model="matched-model",
        timeout=5.0,
    )


def _case() -> WorkforceSelectionCase:
    return WorkforceSelectionCase(
        "matched-incident-selection",
        "Contain this active security incident and preserve supplied evidence.",
        ("incident-responder",),
        ("penetration-tester", "financial-analyst"),
        ("analysis",),
        ("discovery",),
        category="dangerous-incompatible-selection",
        helpful_workers=("incident-responder", "incident-response-commander"),
    )


def _attempt(provider: ProviderEntry) -> WorkforceInferenceAttempt:
    return WorkforceInferenceAttempt(
        "planner",
        provider.name,
        provider.type,
        provider.model,
        "",
        provider.model,
        "cli.explicit_model_argument",
        "applied",
        "structured_response_applied",
        3,
    )


def _accepted_outcome(provider: ProviderEntry) -> WorkforceRoutingOutcome:
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Contain the incident safely.",
            "units": [
                {
                    "unit_id": "unit-incident",
                    "outcome": "Produce an evidence-preserving containment analysis.",
                    "artifact_kind": "analysis",
                    "lifecycle_phase": "discovery",
                    "domains": ["security"],
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["analysis"],
                    "authority": "review",
                    "mutation_scope": "read_only",
                    "risks": ["active-incident"],
                    "trust_boundaries": ["supplied-evidence"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["incident-evidence"],
                    "required_tools": [],
                    "platforms": ["windows"],
                    "acceptance_evidence": ["Containment findings cite supplied evidence."],
                    "parallelization": "sequential",
                }
            ],
        }
    )
    staffing = StaffingDecision(
        "accepted",
        (
            VerifiedUnitStaffing(
                "unit-incident",
                ("incident-responder",),
                "delegate",
                "immediate",
                (("incident-responder", "context-incident"),),
                (),
                (),
            ),
        ),
        (),
    )
    return WorkforceRoutingOutcome(
        "accepted",
        "fast",
        "inferred",
        plan,
        None,
        staffing,
        (_attempt(provider),),
        (),
        1,
    )


def _abstained_disabled_outcome(provider: ProviderEntry) -> WorkforceRoutingOutcome:
    staffing = StaffingDecision(
        "abstained",
        (
            VerifiedUnitStaffing(
                "unit-disabled",
                (),
                "delegate",
                "immediate",
                (),
                (
                    ShadowEvidence(
                        "lsp-index-engineer",
                        1,
                        ("agent_disabled",),
                        "",
                        "The semantic winner is disabled; no weaker substitute was selected.",
                    ),
                ),
                (),
            ),
        ),
        (AbstentionReason("best_candidate_disabled", "unit-disabled"),),
    )
    return WorkforceRoutingOutcome(
        "abstained",
        "fast",
        "inferred",
        None,
        None,
        staffing,
        (_attempt(provider),),
        ("best_candidate_disabled",),
        1,
    )


def _upstream_result(provider: ProviderEntry, value: dict[str, object]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name=provider.name,
        provider_type=provider.type,
        transport=provider.transport,
        requested_model=provider.model,
        model_group="",
        actual_model=provider.model,
        model_receipt_source="cli.explicit_model_argument",
        latency_ms=4,
    )


def _selected_upstream_value() -> dict[str, object]:
    return {
        "status": "selected",
        "assignments": [
            {
                "agent_id": "incident-responder",
                "work_unit_id": "unit-incident",
                "artifact_kind": "analysis",
                "lifecycle_phase": "discovery",
                "context_id": "context-incident",
                "positive_evidence": ["incident-containment"],
            }
        ],
        "disabled_best_agents": [],
        "reason_codes": ["matched-selection"],
    }


def test_pinned_source_license_and_corpus_are_complete() -> None:
    source = pinned_upstream_prompt()
    license_text = pinned_upstream_license()
    snapshot = _snapshot()
    roster = {item.agent_id for item in snapshot.contracts}
    required_categories = {
        "dangerous-incompatible-selection",
        "disabled-best-candidate",
        "weak-incidental-lexical-match",
        "broad-multi-agent",
        "conflict-composition",
    }

    assert len(source.encode()) == UPSTREAM_PROMPT_BYTES
    assert hashlib.sha256(source.encode()).hexdigest() == UPSTREAM_PROMPT_SHA256
    assert source.startswith("---\nname: Agents Orchestrator")
    assert len(license_text.encode()) == UPSTREAM_LICENSE_BYTES
    assert hashlib.sha256(license_text.encode()).hexdigest() == UPSTREAM_LICENSE_SHA256
    assert license_text.startswith("MIT License\n")
    assert len(CASES) == 19
    assert len(CASES) < MINIMUM_RELEASE_SCENARIOS
    assert len({item.case_id for item in CASES}) == len(CASES)
    assert required_categories <= {item.category for item in CASES}
    for case in CASES:
        assert case.expected_helpful_workers
        assert case.forbidden_workers
        assert set(case.expected_helpful_workers).isdisjoint(case.forbidden_workers)
        assert set(case.required_workers) <= set(case.expected_helpful_workers)
        assert set(case.required_disabled_shadows) <= set(case.disabled_workers)
        assert case.latency_budget_ms > 0
        assert {
            *case.expected_helpful_workers,
            *case.forbidden_workers,
            *case.disabled_workers,
            *(agent for pair in case.forbidden_context_pairs for agent in pair),
        } <= roster


def test_shared_scorer_rejects_forbidden_conflicting_and_slow_selection() -> None:
    snapshot = _snapshot()
    case = _case()
    run = SelectionRun(
        "agency",
        "accepted",
        (
            SelectionAssignment(
                "incident-responder",
                "unit-incident",
                "analysis",
                "discovery",
                "context-shared",
            ),
            SelectionAssignment(
                "penetration-tester",
                "unit-incident",
                "analysis",
                "discovery",
                "context-shared",
            ),
        ),
        (),
        case.latency_budget_ms + 1,
        1,
        True,
        "matched-provider",
        "cli",
        "matched-model",
        "matched-model",
        "cli.explicit_model_argument",
    )

    score = score_selection_run(case, run, snapshot, _context(snapshot))

    assert score["passed"] is False
    assert score["forbidden_agents_selected"] == ["penetration-tester"]
    assert score["same_context_conflicts"] == [["incident-responder", "penetration-tester"]]
    assert score["latency_ms"] > score["latency_budget_ms"]


def test_matched_benchmark_uses_identical_bindings_and_never_claims_superiority() -> None:
    snapshot = _snapshot()
    context = _context(snapshot)
    provider = _provider()
    captured: dict[str, object] = {}

    def router(_request, routed_snapshot, **kwargs):
        assert routed_snapshot.contract_fingerprint == snapshot.contract_fingerprint
        assert kwargs["context"].eligible_worker_ids is not None
        return _accepted_outcome(provider)

    def invoker(selected_provider, prompt, schema, *, system_prompt, timeout):
        captured.update(
            provider=selected_provider,
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt,
            timeout=timeout,
        )
        return _upstream_result(provider, _selected_upstream_value())

    report = run_matched_upstream_selection_benchmark(
        snapshot,
        config=AgencyConfig(providers=(provider,)),
        context=context,
        cases=(_case(),),
        agency_router=router,
        invoker=invoker,
    )
    upstream_input = json.loads(str(captured["prompt"]))
    detail = report["details"][0]

    assert report["schema"] == SCHEMA
    assert report["passed"] is True
    assert report["benchmark_valid"] is True
    assert report["matched_controls"]["same_scoring_function"] is True
    assert report["claim"]["superiority_claimed"] is False
    assert report["claim"]["release_claim_eligible"] is False
    assert captured["provider"] == provider
    assert upstream_input["allowed_agent_ids"] == detail["allowed_agent_ids"]
    assert len(upstream_input["visible_roster"]) == snapshot.worker_count
    assert detail["agency"]["provider_name"] == detail["upstream"]["provider_name"]
    assert detail["agency"]["actual_model"] == detail["upstream"]["actual_model"]
    assert "expected_helpful_workers" not in str(captured["prompt"])
    assert "forbidden_workers" not in str(captured["prompt"])
    assert pinned_upstream_prompt() in str(captured["system_prompt"])


def test_disabled_semantic_winner_is_visible_but_not_allowed_and_must_be_disclosed() -> None:
    snapshot = _snapshot()
    context = _context(snapshot)
    provider = _provider()
    case = next(item for item in CASES if item.case_id == "disabled-lsp-winner")
    captured: dict[str, object] = {}

    def router(_request, routed_snapshot, **_kwargs):
        lsp = next(
            item for item in routed_snapshot.contracts if item.agent_id == "lsp-index-engineer"
        )
        assert lsp.enabled is False
        assert lsp.employment == "disabled"
        return _abstained_disabled_outcome(provider)

    def invoker(_provider, prompt, _schema, **_kwargs):
        captured["prompt"] = prompt
        return _upstream_result(
            provider,
            {
                "status": "abstained",
                "assignments": [],
                "disabled_best_agents": ["lsp-index-engineer"],
                "reason_codes": ["best-candidate-disabled"],
            },
        )

    report = run_matched_upstream_selection_benchmark(
        snapshot,
        config=AgencyConfig(providers=(provider,)),
        context=context,
        cases=(case,),
        agency_router=router,
        invoker=invoker,
    )
    upstream_input = json.loads(str(captured["prompt"]))
    lsp_card = next(
        item
        for item in upstream_input["visible_roster"]
        if item["agent_id"] == "lsp-index-engineer"
    )

    assert report["passed"] is True
    assert lsp_card["enabled"] is False
    assert "lsp-index-engineer" not in upstream_input["allowed_agent_ids"]
    assert report["details"][0]["agency"]["missing_disabled_disclosures"] == []
    assert report["details"][0]["upstream"]["missing_disabled_disclosures"] == []


def test_malformed_upstream_response_invalidates_benchmark_instead_of_creating_lift() -> None:
    snapshot = _snapshot()
    context = _context(snapshot)
    provider = _provider()

    def invoker(_provider, _prompt, _schema, **_kwargs):
        return _upstream_result(provider, {"unexpected": "response"})

    report = run_matched_upstream_selection_benchmark(
        snapshot,
        config=AgencyConfig(providers=(provider,)),
        context=context,
        cases=(_case(),),
        agency_router=lambda *_args, **_kwargs: _accepted_outcome(provider),
        invoker=invoker,
    )

    assert report["passed"] is False
    assert report["benchmark_valid"] is False
    assert "matched-incident-selection:arm_error" in report["fairness_violations"]
    assert report["details"][0]["upstream"]["status"] == "error"


def test_existing_workforce_eval_applies_disabled_case_overlay_and_allows_safe_abstention() -> None:
    snapshot = _snapshot()
    provider = _provider()
    case = next(item for item in CASES if item.case_id == "disabled-lsp-winner")

    def router(_request, routed_snapshot, **_kwargs):
        lsp = next(
            item for item in routed_snapshot.contracts if item.agent_id == "lsp-index-engineer"
        )
        assert lsp.enabled is False
        return _abstained_disabled_outcome(provider)

    report = run_workforce_inference_eval(
        snapshot,
        config=AgencyConfig(providers=(provider,)),
        context=_context(snapshot),
        cases=(case,),
        router=router,
    )

    assert report["passed"] is True
    assert report["details"][0]["missing_artifacts"] == []
    assert report["details"][0]["missing_lifecycles"] == []


def test_live_matched_eval_requires_exact_confirmation_and_defaults_to_full_tool_visibility() -> (
    None
):
    with pytest.raises(ValueError, match="RUN MATCHED UPSTREAM SELECTION EVAL"):
        cmd_eval_upstream_selection(
            Namespace(
                confirm_live_inference="",
                host="codex",
                platform="windows",
                available_tool=[],
                case=[],
                all=False,
                no_details=False,
                json=False,
            )
        )

    snapshot = _snapshot()
    context = _upstream_selection_context(
        Namespace(host="codex", platform="windows", available_tool=[]),
        snapshot,
    )
    assert "native-delegation" in context.available_tools
    assert all(
        set(contract.tool_classes) <= context.available_tools for contract in snapshot.contracts
    )
