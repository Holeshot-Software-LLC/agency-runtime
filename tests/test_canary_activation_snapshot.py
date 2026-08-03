from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import stub_inference_invoker, write_provider_config

_REQUEST = "Review this Python code for correctness"


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield Store(tmp_path / "agency.db", config_path=config_path)
    finally:
        reset_config_cache()


def _ready_turn(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
    *,
    session_id: str = "session",
    trace_id: str = "trace",
) -> tuple[str, str]:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    result = run_preflight(
        store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=_REQUEST,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
        ),
    )
    slug = next(
        candidate
        for candidate in result.selected_specialists
        if candidate not in PROTECTED_AGENT_SLUGS
    )
    completion = store.get_completion_evidence_snapshot(session_id, trace_id)
    unit = next(
        item["work_unit_id"]
        for item in completion["unit_agent_plan"]
        if item["recommended_agent"] == slug
    )
    return slug, str(unit)


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value} | {
            nested for item in value.values() for nested in _keys(item)
        }
    if isinstance(value, list):
        return {nested for item in value for nested in _keys(item)}
    return set()


def test_canary_activation_snapshot_resolves_one_redacted_evidence_graph(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slug, unit = _ready_turn(store, monkeypatch)
    prepared = store.prepare_delegation_activation(
        session_id="session",
        trace_id="trace",
        specialist_slug=slug,
        work_unit_id=unit,
    )
    assert (
        mark_delegation_executed(
            store,
            session_id="session",
            trace_id="trace",
            host="codex",
            backend="spawn_agent",
            agent=slug,
            work_unit_id=unit,
            executed_worker_kind="generic-worker",
            executed_worker_id="worker-1",
            native_run_id="child-1",
        )
        == 1
    )
    consumed = store.consume_delegation_activation(
        activation_token=str(prepared["activation_token"]),
        session_id="session",
        trace_id="trace",
        specialist_slug=slug,
        work_unit_id=unit,
        worker_id="worker-1",
        native_run_id="child-1",
    )
    store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        work_unit_id=unit,
        worker_id="worker-1",
        native_run_id="child-1",
        outcome="ok",
    )
    store.record_finalization(
        trace_id="trace",
        host="codex",
        action="continue",
        missing=["specialist-activation"],
        response_hash=sha256(b"canary response").hexdigest(),
    )

    query_hash = sha256(_REQUEST.encode("utf-8")).hexdigest()
    snapshot = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)

    assert snapshot["proven"] is True
    assert snapshot["status"] == "resolved"
    assert snapshot["reason"] == "exact_route_resolved"
    assert snapshot["session_id"] == "session"
    assert snapshot["trace_id"] == "trace"
    assert snapshot["route"]["query_hash"] == query_hash
    assert snapshot["run"]["request_fingerprint"] == query_hash
    assert any(item["work_unit_id"] == unit for item in snapshot["unit_agent_plan"])
    assert snapshot["activation_grants"][0]["id"] == prepared["receipt_id"]
    assert snapshot["activation_consumptions"][0]["grant_id"] == prepared["grant_id"]
    assert snapshot["worker_runs"][0]["exit_code"] == 0
    assert snapshot["specialist_loads"][0]["activation_receipt_id"] == prepared["receipt_id"]
    delegation = next(item for item in snapshot["delegations"] if item["work_unit_id"] == unit)
    assert delegation["status"] == "completed"
    assert delegation["activation_receipt_id"] == prepared["receipt_id"]
    assert snapshot["finalizations"][0]["missing"] == ["specialist-activation"]
    for name in (
        "unit_agent_plan",
        "delegations",
        "activation_grants",
        "activation_consumptions",
        "worker_runs",
        "specialist_loads",
        "finalizations",
    ):
        assert snapshot["cardinalities"][name] == len(snapshot[name])

    forbidden = {
        "activation_token",
        "token_hash",
        "grant_payload",
        "receipt_payload",
        "preflight_result",
        "prompt_body",
        "user_message",
        "stdout",
        "stderr",
        "workdir",
        "goal",
    }
    assert forbidden.isdisjoint(_keys(snapshot))
    encoded = json.dumps(snapshot, sort_keys=True)
    assert str(prepared["activation_token"]) not in encoded
    assert str(consumed["prompt_body"]) not in encoded
    assert _REQUEST not in encoded


def test_canary_activation_snapshot_fails_closed_for_missing_or_ambiguous_route(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_hash = sha256(b"not recorded").hexdigest()
    missing = store.get_canary_activation_snapshot(host="codex", query_hash=missing_hash)
    assert missing["proven"] is False
    assert missing["status"] == "not_proven"
    assert missing["reason"] == "route_not_found"
    assert missing["cardinalities"]["routes"] == 0
    assert missing["route"] is None

    _ready_turn(store, monkeypatch)
    query_hash = sha256(_REQUEST.encode("utf-8")).hexdigest()
    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO routing_decisions "
            "(id, trace_id, session_id, query_hash, context_fingerprint, status, "
            "source, selected_ids, semantic_ids, companion_ids, confidence, "
            "latency_ms, provider, work_units, decision, created_at) "
            "SELECT 'duplicate-route', trace_id, session_id, query_hash, "
            "context_fingerprint, status, source, selected_ids, semantic_ids, "
            "companion_ids, confidence, latency_ms, provider, work_units, decision, "
            "created_at FROM routing_decisions WHERE query_hash = ? LIMIT 1",
            (query_hash,),
        )
        connection.commit()
    finally:
        connection.close()

    ambiguous = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)
    assert ambiguous["proven"] is False
    assert ambiguous["status"] == "not_proven"
    assert ambiguous["reason"] == "route_ambiguous"
    assert ambiguous["cardinalities"]["routes"] == 2
    assert ambiguous["run"] is None
    assert ambiguous["route"] is None

    with pytest.raises(ValueError, match="lowercase SHA-256"):
        store.get_canary_activation_snapshot(host="codex", query_hash=query_hash.upper())
    with pytest.raises(ValueError, match="supported execution host"):
        store.get_canary_activation_snapshot(host="unknown", query_hash=query_hash)


def test_canary_activation_snapshot_binds_repeated_prompt_to_exact_session(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ready_turn(
        store,
        monkeypatch,
        session_id="historical-session",
        trace_id="historical-trace",
    )
    _ready_turn(
        store,
        monkeypatch,
        session_id="current-session",
        trace_id="current-trace",
    )
    query_hash = sha256(_REQUEST.encode("utf-8")).hexdigest()

    historical_lookup = store.get_canary_activation_snapshot(
        host="codex",
        query_hash=query_hash,
    )
    exact_lookup = store.get_canary_activation_snapshot(
        host="codex",
        query_hash=query_hash,
        session_id="current-session",
    )

    assert historical_lookup["proven"] is False
    assert historical_lookup["reason"] == "route_ambiguous"
    assert historical_lookup["cardinalities"]["routes"] == 2
    assert exact_lookup["proven"] is True
    assert exact_lookup["reason"] == "exact_route_resolved"
    assert exact_lookup["session_id"] == "current-session"
    assert exact_lookup["trace_id"] == "current-trace"


def test_canary_activation_snapshot_projects_exact_preflight_failure(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import pipeline

    request = "Diagnose the exact preflight failure without retaining this request."
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            TimeoutError("private provider timeout detail")
        ),
    )
    with pytest.raises(TimeoutError, match="private provider timeout detail"):
        run_preflight(
            store,
            session_id="failed-session",
            trace_id="failed-trace",
            user_message=request,
            host="codex",
            capability_receipt=native_adapter_capability_receipt(
                "codex",
                platform="windows" if os.name == "nt" else "linux",
                session_id="failed-session",
                trace_id="failed-trace",
            ),
        )

    query_hash = sha256(request.encode("utf-8")).hexdigest()
    snapshot = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)

    assert snapshot["proven"] is False
    assert snapshot["reason"] == "preflight_failed"
    assert snapshot["session_id"] == "failed-session"
    assert snapshot["trace_id"] == "failed-trace"
    assert snapshot["cardinalities"]["routes"] == 0
    assert snapshot["cardinalities"]["runs"] == 1
    assert snapshot["cardinalities"]["preflight_failures"] == 1
    assert snapshot["run"]["status"] == "preflight_failed"
    assert snapshot["preflight_failure"]["stage"] == "routing"
    assert snapshot["preflight_failure"]["reason_code"] == "routing_failed"
    assert snapshot["preflight_failure"]["exception_category"] == "timeout"
    encoded = json.dumps(snapshot, sort_keys=True)
    assert request not in encoded
    assert "private provider timeout detail" not in encoded
