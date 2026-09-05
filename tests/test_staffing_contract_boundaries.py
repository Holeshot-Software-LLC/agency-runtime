"""AR-400/401/402: compose real staffing and hiring with valid offline replies."""

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core.selector import pipeline
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce import hiring
from agency_runtime.core.workforce.inference import (
    WorkforceInferenceAttempt,
    WorkforceRoutingOutcome,
    _valid_inferred_gap_proposal,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit, parse_work_unit_plan
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingBudget,
    StaffingContext,
    build_deterministic_proposal,
    verify_staffing,
)
from tests import test_workforce_dynamic_hiring as fixtures


def _empty_gaps(store: Store, *, count: int = 2):
    reviewer = fixtures._install_existing(store)
    snapshot = fixtures.workforce_index_snapshot(store, disabled_agents=())
    gaps = (fixtures._unit(), fixtures._photonic_unit())[:count]
    review = WorkUnit(
        unit_id="unit-independent-review",
        outcome="Independently review the compiler build plugins",
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
        depends_on=tuple(unit.unit_id for unit in gaps),
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
            "units": [asdict(unit) for unit in (*gaps, review)],
        }
    )
    context = StaffingContext(
        "codex", "windows", frozenset({"repository-read", "native-delegation"}), snapshot.generation
    )
    proposal = build_deterministic_proposal(
        plan,
        snapshot.contracts,
        {**{unit.unit_id: [] for unit in gaps}, review.unit_id: [(reviewer.agent_id, 0.9)]},
        context=context,
        budget=StaffingBudget(),
        semantic_required={},
        semantic_acceptable={review.unit_id: frozenset({reviewer.agent_id})},
        semantic_gap_units=frozenset(unit.unit_id for unit in gaps),
    )
    staffing = verify_staffing(
        plan, proposal, snapshot.contracts, context=context, budget=StaffingBudget()
    )
    assert _valid_inferred_gap_proposal(proposal, staffing)
    attempt = WorkforceInferenceAttempt(
        stage="recruiter",
        provider_name="offline",
        provider_type="litellm",
        requested_model="offline",
        model_group="offline",
        actual_model="offline",
        model_receipt_source="response.body.model",
        status="applied",
        reason_code="structured_response_applied",
        latency_ms=0,
    )
    return snapshot, WorkforceRoutingOutcome(
        status="abstained",
        mode="balanced",
        inference_mode="inferred",
        plan=plan,
        proposal=proposal,
        staffing=staffing,
        attempts=(attempt,),
        abstention_codes=tuple(reason.code for reason in staffing.abstention_reasons),
        calls_used=1,
    )


@pytest.mark.parametrize("defer_commits", [False, True])
@pytest.mark.parametrize("count,max_hires", [(1, 1), (2, 1), (2, 2)])
def test_empty_gap_hires_accumulate_without_premature_commits(
    tmp_path: Path, monkeypatch, count: int, max_hires: int, defer_commits: bool
) -> None:
    store = Store(tmp_path / "agency.db")
    snapshot, initial = _empty_gaps(store, count=count)
    config = fixtures._config()
    config = replace(config, workforce=replace(config.workforce, max_hires_per_turn=max_hires))
    request = SimpleNamespace(
        user_message=initial.plan.request_summary,
        host="codex",
        platform="windows",
        available_tools=("repository-read", "native-delegation"),
        session_id="offline-boundary",
        trace_id="offline-boundary",
        hiring_deadline_monotonic=None,
    )
    real_hire = hiring.hire_contractor_for_gap
    calls = []

    def scripted_hire(message, unit, contracts, **kwargs):
        answers = iter(
            (
                fixtures._hiring_response_for(unit),
                {"approved": True, "reason_codes": []},
                fixtures._SAFE_SECURITY_REVIEW,
            )
        )

        def invoke(provider, prompt, schema, **_kwargs):
            calls.append(unit.unit_id)
            return fixtures._result(next(answers), provider)

        return real_hire(message, unit, contracts, **kwargs, invoker=invoke)

    monkeypatch.setattr(hiring, "hire_contractor_for_gap", scripted_hire)
    final, projected, _, events = pipeline._run_gap_hiring(
        initial,
        request,
        config,
        store,
        snapshot,
        store.get_active_roster_as_catalog(disabled_agents=()),
        defer_commits=defer_commits,
    )
    assert len(calls) == 3 * max_hires
    assert final.accepted is (max_hires == count)
    assert final.proposal.units[0].selected == ("quantum-build-engineer",)
    if count == 2:
        assert final.proposal.units[1].selected == (
            ("photonic-build-engineer",) if max_hires == 2 else ()
        )
        if max_hires == 1:
            assert "inference-declared-gap" in final.proposal.units[1].abstention_reasons
            assert events[1]["reason_codes"] == ["task_hiring_limit_reached"]
    assert projected.worker_count == snapshot.worker_count + max_hires
    committed = fixtures.workforce_index_snapshot(store, disabled_agents=())
    assert committed.worker_count == snapshot.worker_count + (0 if defer_commits else max_hires)
    assert sum(event.get("_pending_commit") is not None for event in events) == (
        max_hires if defer_commits else 0
    )


def test_restaffing_an_amended_worker_preserves_its_other_assignment(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    worker = fixtures._install_existing(store)
    snapshot = fixtures.workforce_index_snapshot(store, disabled_agents=())
    first = replace(
        fixtures._unit(),
        artifact_kind="review-report",
        lifecycle_phase="review",
        authority="review",
        mutation_scope="read_only",
        required_capabilities=("review",),
        domains=("software-engineering",),
        languages=(),
    )
    second = replace(first, unit_id="unit-other-review", depends_on=(first.unit_id,))
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Review two related components",
            "units": [asdict(first), asdict(second)],
        }
    )
    context = StaffingContext(
        "codex", "windows", frozenset({"repository-read"}), snapshot.generation
    )
    proposal = build_deterministic_proposal(
        plan,
        snapshot.contracts,
        {first.unit_id: [], second.unit_id: [(worker.agent_id, 1.0)]},
        context=context,
        budget=StaffingBudget(),
        semantic_required={second.unit_id: frozenset({worker.agent_id})},
        semantic_gap_units=frozenset({first.unit_id}),
    )
    initial = WorkforceRoutingOutcome(
        status="abstained",
        mode="balanced",
        inference_mode="inferred",
        plan=plan,
        proposal=proposal,
        staffing=verify_staffing(
            plan, proposal, snapshot.contracts, context=context, budget=StaffingBudget()
        ),
        attempts=(),
        abstention_codes=("no_safe_sufficient_team",),
        calls_used=1,
    )
    final = hiring.restaff_after_hire(
        initial,
        snapshot.contracts,
        hired_agent_id=worker.agent_id,
        causing_unit_id=first.unit_id,
        context=context,
        config=fixtures._config(),
    )
    assert final.accepted
    assert [row.selected for row in final.proposal.units] == [
        (worker.agent_id,),
        (worker.agent_id,),
    ]
