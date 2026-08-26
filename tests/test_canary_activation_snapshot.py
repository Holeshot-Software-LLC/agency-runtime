from __future__ import annotations

import json
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME,
    CODEX_ACTIVATION_CANARY_PROMPT,
    CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
    CODEX_ACTIVATION_CANARY_WORK_UNIT,
)
from agency_runtime.core.canary_proof import codex_activation_failures
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import stub_inference_invoker, write_provider_config

_REQUEST = "Review this Python code for correctness"
_CHILD_TASK = "Review the exact child change."
_CHILD = "019fb000-1111-7222-8333-444455556666"
_LAUNCH = "launch-canary-child"
_NONCE = "nonce-canary-child"
_PROMPT = "You are the exact code-review specialist."


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _native_child_decision() -> dict[str, object]:
    attempts = [
        {
            "provider_name": "selector",
            "provider_type": "openai",
            "requested_model": "gpt-test",
            "model_group": "",
            "actual_model": "",
            "model_receipt_source": "unavailable",
            "status": "applied",
            "reason_code": "",
        }
    ]
    cards = [
        {
            "specialist_slug": "code-reviewer",
            "specialist_version": "v1",
            "specialist_prompt_hash": _digest(_PROMPT),
            "body_character_length": len(_PROMPT),
        }
    ]
    team_digest = _digest(
        json.dumps(
            cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "codex",
        "parent_session_id": "snapshot-parent",
        "parent_trace_id": "snapshot-trace",
        "launch_id": _LAUNCH,
        "binding_kind": "child_id",
        "binding_id": _CHILD,
        "provider_attempts": attempts,
        "provider_receipt_digest": canonical_native_child_provider_receipt_digest(attempts),
        "task_sha256": _digest(_CHILD_TASK),
        "team_digest": team_digest,
        "candidate_digest": _digest("runtime"),
        "runtime_digest": _digest("runtime"),
        "install_id": "codex-install-1",
        "bundle_digest": _digest("bundle"),
        "issued_at": "2026-08-12T12:00:00Z",
        "expires_at": "2026-08-12T12:05:00Z",
        "nonce": _NONCE,
        "cards": cards,
    }


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


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key) for key in value} | {
            nested for item in value.values() for nested in _keys(item)
        }
    if isinstance(value, list):
        return {nested for item in value for nested in _keys(item)}
    return set()


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


def test_restricted_codex_parent_snapshot_resolves_only_the_exact_live_route(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-parent"
    trace_id = "restricted-trace"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'a' * 32}"
    result = run_preflight(
        store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=task,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
            available_tools=("repository-read", "native-delegation"),
        ),
    )

    snapshot = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
    )

    assert result.routing["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert snapshot is not None
    assert snapshot["proven"] is True
    assert snapshot["session_id"] == session_id
    assert snapshot["trace_id"] == trace_id
    assert snapshot["route"]["selected_ids"] == ["code-reviewer"]
    assert (
        store.get_codex_activation_canary_parent_snapshot(
            session_id=session_id,
            trace_id="other-trace",
        )
        is None
    )


def test_restricted_codex_user_prompt_injects_the_exact_native_plan(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.installer import seed_starter_roster
    from agency_runtime.core.workforce import inference

    seed_starter_roster(store)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "restricted-plan-parent"
    trace_id = "restricted-plan-trace"
    task = f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {'b' * 32}"

    output = HookBridge(
        "codex",
        store=store,
        _master={"enabled": True},
    ).handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": trace_id,
            "model": "gpt-5.6-codex",
            "prompt": task,
        }
    )

    context = output["hookSpecificOutput"]["additionalContext"]
    assert context.count("[AGENCY DELEGATION PLAN]") == 1
    plan = context.split("[AGENCY DELEGATION PLAN]", 1)[1]
    assert '"specialist":"code-reviewer"' in plan
    assert f'"native_task_name":"{CODEX_ACTIVATION_CANARY_NATIVE_TASK_NAME}"' in plan
    assert json.dumps(CODEX_ACTIVATION_CANARY_WORK_UNIT) in plan
    assert '"work_unit_id":"unit-05d45f7553"' in plan
    snapshot = store.get_codex_activation_canary_parent_snapshot(
        session_id=session_id,
        trace_id=trace_id,
    )
    assert snapshot is not None
    assert snapshot["route"]["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE


def test_store_receipt_remains_diagnostic_without_host_artifact_proof(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    preflight = run_preflight(
        store,
        session_id="snapshot-parent",
        trace_id="snapshot-trace",
        user_message=_REQUEST,
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id="snapshot-parent",
            trace_id="snapshot-trace",
        ),
    )
    decision = _native_child_decision()
    decision_id = store.record_routing_decision(
        trace_id="snapshot-trace",
        session_id="snapshot-parent",
        query_hash=str(decision["task_sha256"]),
        context_fingerprint=_digest("context"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": ["code-reviewer"],
            "semantic_ids": ["code-reviewer"],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "candidate_count": 1,
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": decision["task_sha256"],
            "query_hash": decision["task_sha256"],
            "context_fingerprint": _digest("context"),
            "native_child_delivery": decision,
        },
    )
    query_hash = str(preflight.routing["query_hash"])

    missing = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)
    assert missing["route"]["id"] != decision_id
    assert missing["cardinalities"]["native_child_routes"] == 1
    assert missing["cardinalities"]["native_child_deliveries"] == 0
    assert missing["native_child_route"] is None
    assert missing["native_child_delivery"] is None
    assert missing["host_child_delivery"] is None

    # Codex 0.147 cannot mint this receipt through the live artifact verifier;
    # seed the private Store boundary and prove that it remains diagnostic.
    receipt = store._record_native_child_delivery_verification(
        decision_id=decision_id,
        nonce=_NONCE,
        artifact_digest=_digest("host-artifact"),
        host="codex",
        parent_session_id="snapshot-parent",
        parent_trace_id="snapshot-trace",
        launch_id=_LAUNCH,
        binding_kind="child_id",
        binding_id=_CHILD,
        child_id=_CHILD,
        cards=decision["cards"],
    )
    snapshot = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)

    assert snapshot["route"]["id"] != snapshot["native_child_route"]["decision_id"]
    assert snapshot["native_child_route"]["decision_id"] == decision_id
    assert snapshot["native_child_delivery"] == receipt
    assert snapshot["host_child_delivery"] is None
    assert snapshot["cardinalities"]["native_child_routes"] == 1
    assert snapshot["cardinalities"]["native_child_deliveries"] == 1

    response = "Agency/Agencies loaded: code-reviewer"
    response_hash = _digest(response)
    canary_snapshot = deepcopy(snapshot)
    canary_snapshot["run"].update(
        status="completed",
        ended_at="2026-08-12T12:00:02Z",
        terminal_finalization_id="final-1",
    )
    canary_snapshot["worker_runs"] = [
        {
            "worker_id": _CHILD,
            "native_run_id": f"codex-agent:{_CHILD}",
            "backend": "spawn_agent",
            "host": "codex",
            "started_at": "2026-08-12T12:00:00Z",
            "ended_at": "2026-08-12T12:00:02Z",
        }
    ]
    canary_snapshot["finalizations"] = [
        {
            "id": "final-1",
            "action": "accept",
            "terminal_status": "completed",
            "response_hash": response_hash,
        }
    ]
    canary_snapshot["cardinalities"].update(worker_runs=1, finalizations=1)
    result = {
        "collaboration": {
            "unexpected_item_count": 0,
            "unexpected_item_types": [],
            "calls": [
                {
                    "tool": "spawn_agent",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": "snapshot-parent",
                    "receiver_thread_ids": [_CHILD],
                    "execution_delivery": {"native_task_name": "agency_task"},
                },
                {
                    "tool": "wait",
                    "status": "completed",
                    "event_type": "item.completed",
                    "sender_thread_id": "snapshot-parent",
                    "receiver_thread_ids": [_CHILD],
                    "agents_states": {_CHILD: "completed"},
                },
            ],
        }
    }

    assert codex_activation_failures(
        result=result,
        evidence=canary_snapshot,
        response_hash=response_hash,
    ) == ("verified host-authored Codex child card delivery was not proven",)

    second = deepcopy(decision)
    second["launch_id"] = "launch-second-child"
    second["nonce"] = "nonce-second-child"
    second["binding_id"] = "second-child"
    store.record_routing_decision(
        trace_id="snapshot-trace",
        session_id="snapshot-parent",
        query_hash=str(second["task_sha256"]),
        context_fingerprint=_digest("second-context"),
        decision={
            "status": "applied",
            "semantic_status": "applied",
            "source": "native_child_inference",
            "selected_ids": ["code-reviewer"],
            "semantic_ids": ["code-reviewer"],
            "companion_ids": [],
            "available_companion_ids": [],
            "unavailable_companion_ids": [],
            "confidence": 0.9,
            "latency_ms": 12,
            "provider": "selector",
            "candidate_count": 1,
            "top_score": 0.0,
            "native_child_reason": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "source_message_hash": second["task_sha256"],
            "query_hash": second["task_sha256"],
            "context_fingerprint": _digest("second-context"),
            "native_child_delivery": second,
        },
    )
    ambiguous = store.get_canary_activation_snapshot(host="codex", query_hash=query_hash)
    assert ambiguous["cardinalities"]["native_child_routes"] == 2
    assert ambiguous["cardinalities"]["native_child_deliveries"] == 1
    assert ambiguous["native_child_route"] is None
    assert ambiguous["native_child_delivery"] is None
    assert ambiguous["host_child_delivery"] is None
