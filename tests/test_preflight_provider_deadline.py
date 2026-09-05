"""AR-401: exercise the calls inside hiring, not a fake whole hiring round."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core.provider_deadline import (
    inference_deadline,
    remaining_provider_timeout,
)
from agency_runtime.core.selector import pipeline
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce import hiring, inference
from tests import test_workforce_dynamic_hiring as fixtures
from tests.test_staffing_contract_boundaries import _empty_gaps


def test_hiring_clamps_each_call_and_records_exhaustion(tmp_path: Path, monkeypatch) -> None:
    store = Store(tmp_path / "agency.db")
    snapshot, initial = _empty_gaps(store, count=1)
    config = fixtures._config()
    config = replace(config, providers=(replace(config.providers[0], timeout=60),))
    clock = [1000.0]
    monkeypatch.setattr(hiring.time, "monotonic", lambda: clock[0])
    request = SimpleNamespace(
        user_message=initial.plan.request_summary,
        host="codex",
        platform="windows",
        available_tools=("repository-read", "native-delegation"),
        session_id="deadline-boundary",
        trace_id="deadline-boundary",
        hiring_deadline_monotonic=1075.0,
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

        def invoke(provider, prompt, schema, *, timeout, **_kwargs):
            calls.append((clock[0], timeout))
            clock[0] += min(50.0, timeout)
            return fixtures._result(next(answers), provider) if timeout >= 50.0 else None

        return real_hire(message, unit, contracts, **kwargs, invoker=invoke)

    monkeypatch.setattr(hiring, "hire_contractor_for_gap", scripted_hire)
    final, _, _, events = pipeline._run_gap_hiring(
        initial,
        request,
        config,
        store,
        snapshot,
        store.get_active_roster_as_catalog(disabled_agents=()),
        defer_commits=True,
    )
    assert calls == [(1000.0, 60.0), (1050.0, 15.0)]
    assert clock[0] == 1065.0  # Ten seconds remain to close the attempt.
    assert not final.accepted
    assert "hiring_lease_budget_exhausted" in events[0]["reason_codes"]
    assert fixtures.workforce_index_snapshot(store, disabled_agents=()).worker_count == 1
    assert not events[0].get("_pending_commit")


@pytest.mark.parametrize("stage", ["planner", "recruiter", "critic", "recall_reranker"])
def test_semantic_repair_uses_the_same_deadline(monkeypatch, stage) -> None:
    clock = [1000.0]
    monkeypatch.setattr(hiring.time, "monotonic", lambda: clock[0])
    provider = replace(fixtures._config().providers[0], timeout=60)
    calls = []

    def invoke(provider, prompt, schema, *, timeout, **_kwargs):
        calls.append(timeout)
        clock[0] += min(50, timeout)
        return fixtures._result({}, provider)

    def invalid(_value):
        raise ValueError("invalid semantic reply")

    with inference_deadline(1070):
        parsed, attempts, reason = inference._invoke_stage(
            stage=stage,
            providers=(provider,),
            prompt="test",
            schema={},
            system_prompt="test",
            budget=inference._CallBudget(5),
            invoker=invoke,
            parser=invalid,
        )
    assert parsed is None
    assert calls == [60, 20]
    assert reason == "workforce_inference_deadline_exhausted"
    assert attempts[-1].reason_code == "provider_deadline_exhausted"
    assert attempts[-1].timeout_ms == 20000


def test_provider_fallback_stops_at_the_shared_hiring_deadline(monkeypatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr(hiring.time, "monotonic", lambda: clock[0])
    provider = replace(fixtures._config().providers[0], timeout=60)
    calls = []

    def invoke(provider, prompt, schema, *, timeout, **_kwargs):
        calls.append(timeout)
        clock[0] += min(50, timeout)
        return None

    result, winner, failures = hiring._invoke(
        (provider, provider, provider),
        prompt="test",
        schema={},
        system="test",
        stage="hiring",
        invoker=invoke,
        budget=hiring._CallBudget(5, deadline_monotonic=1070),
    )
    assert result is winner is None
    assert calls == [60, 20]
    assert failures[-1].reason_code == "hiring_lease_budget_exhausted"
    assert failures[-1].timeout_ms == 20000


def test_expired_budget_never_invokes_provider_or_spends_a_call(monkeypatch) -> None:
    monkeypatch.setattr(hiring.time, "monotonic", lambda: 1000.0)
    provider = fixtures._config().providers[0]
    budget = hiring._CallBudget(5, deadline_monotonic=999)

    def forbidden(*_args, **_kwargs):
        pytest.fail("expired budget reached the provider")

    _, _, failures = hiring._invoke(
        (provider,),
        prompt="test",
        schema={},
        system="test",
        stage="hiring",
        invoker=forbidden,
        budget=budget,
    )
    assert budget.used == 0
    assert failures[0].status == "skipped"
    assert failures[0].reason_code == "hiring_lease_budget_exhausted"


def test_deadline_context_cannot_extend_or_leak_after_an_exception(monkeypatch) -> None:
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr(hiring.time, "monotonic", lambda: 1000.0)
    with pytest.raises(RuntimeError), inference_deadline(1030):
        assert remaining_provider_timeout(60) == 30
        with inference_deadline(1100):
            assert remaining_provider_timeout(60) == 30
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(remaining_provider_timeout, 60).result() == 60
        raise RuntimeError("route failed")
    assert remaining_provider_timeout(60) == 60
