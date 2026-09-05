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


def test_actual_preflight_closes_with_deadline_receipt_and_scopes_vector_cache(
    tmp_path, monkeypatch
) -> None:
    from agency_runtime.core import installer_payloads
    from agency_runtime.core.preflight import run_preflight

    store = Store(tmp_path / "agency.db")
    clock = [1000.0]
    calls = []
    cache_paths = []
    monkeypatch.setattr(hiring.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(installer_payloads, "hook_timeout_seconds", lambda *_a, **_k: 75)
    real_plan = inference.plan_and_staff_workforce

    def plan(*args, **kwargs):
        cache_paths.append(kwargs.get("catalog_cache_directory"))
        return real_plan(*args, **kwargs)

    def invoke(provider, prompt, schema, *, timeout, **kwargs):
        calls.append(timeout)
        clock[0] += timeout
        return None

    monkeypatch.setattr(inference, "plan_and_staff_workforce", plan)
    monkeypatch.setattr(inference, "invoke_structured_provider_result", invoke)
    config = fixtures._config()
    config = replace(config, providers=(replace(config.providers[0], timeout=120),))
    result = run_preflight(
        store,
        session_id="deadline-session",
        trace_id="deadline-trace",
        host="claude",
        user_message="Review the Python backend source for correctness.",
        config=config,
    )
    assert calls == [65]
    assert cache_paths == [store.db_path.parent / "recall-vectors-v1"]
    assert not result.routing["selected_ids"]
    assert store.get_run("deadline-trace")["status"] == "preflight_failed"
    assert store.get_open_traces_for_session("deadline-session") == []
    receipt = store.get_preflight_failure_receipt("deadline-session", "deadline-trace")
    assert receipt is not None
    assert receipt["provider_attempts"][-1]["reason_code"] == "provider_deadline_exhausted"


@pytest.mark.parametrize("transport", ["structured", "embedding", "reranker"])
def test_real_http_transport_clamps_to_remaining_time_and_refuses_expired(monkeypatch, transport):
    from agency_runtime.core import structured_provider
    from agency_runtime.core.workforce import embedding_provider, reranker_provider
    from tests.test_workforce_embedding_provider import _provider as embedding_entry
    from tests.test_workforce_embedding_provider import _Response, _response_payload
    from tests.test_workforce_reranker_provider import _payload
    from tests.test_workforce_reranker_provider import _provider as reranker_entry

    clock = [1000.0]
    monkeypatch.setattr(hiring.time, "monotonic", lambda: clock[0])
    calls = []
    if transport == "embedding":
        module = embedding_provider
        provider = embedding_entry(provider_type="ollama", dimensions=2)
        payload = _response_payload("ollama", [[1, 0]])

        def invoke():
            return module.invoke_embedding_provider(provider, ("one query",))
    elif transport == "reranker":
        module = reranker_provider
        provider = reranker_entry()
        payload = _payload()

        def invoke():
            return module.invoke_reranker_provider(provider, "query", ("one", "two"))
    else:
        module = structured_provider
        provider = replace(embedding_entry(provider_type="ollama", dimensions=0), timeout=60)
        payload = {"model": provider.model, "message": {"content": '{"approved":true}'}}

        def invoke():
            return module.invoke_structured_provider_result(
                provider, "query", {"type": "object"}, system_prompt="Return JSON"
            )

    def respond(request, *, timeout):
        calls.append(timeout)
        return _Response(payload)

    monkeypatch.setattr(module, "open_no_redirect", respond)
    with inference_deadline(1002):
        assert invoke() is not None
        clock[0] = 1002
        if transport == "structured":
            assert invoke().failure_reason == "provider_deadline_exhausted"
        else:
            with pytest.raises(TimeoutError):
                invoke()
    assert calls == [2]


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
            assert remaining_provider_timeout(9999) == 1065 - clock[0]
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


@pytest.mark.parametrize("preparation_seconds,expected_calls", [(2, [3]), (6, [])])
def test_native_cli_rechecks_deadline_after_launch_preparation(
    monkeypatch, preparation_seconds, expected_calls
):
    from agency_runtime.core import cli_transport
    from agency_runtime.core.delegation.backends import BoundedProcessResult
    from tests.runtime_support import trusted_test_interpreter

    clock = [1000.0]
    monkeypatch.setattr(hiring.time, "monotonic", lambda: clock[0])
    calls = []

    def environment(*_args):
        clock[0] += preparation_seconds
        return {}

    def runner(_argv, *, timeout, **_kwargs):
        calls.append(timeout)
        return BoundedProcessResult(1, "", "")

    monkeypatch.setattr(cli_transport, "_isolated_invocation_environment", environment)
    with inference_deadline(1005):
        cli_transport.invoke_cli_structured(
            fixtures._config(provider_type="cli").providers[0],
            "Return one object",
            {"type": "object"},
            timeout=60,
            resolver=lambda *_a, **_k: str(trusted_test_interpreter()),
            runner=runner,
        )
    assert calls == expected_calls


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
