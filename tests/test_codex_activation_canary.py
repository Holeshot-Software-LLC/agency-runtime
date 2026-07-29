from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core import canary
from agency_runtime.core.activation_canary_contract import CODEX_ACTIVATION_CANARY_WORK_UNIT
from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.canary_backends import (
    codex_canary_record,
    codex_collaboration_evidence,
)
from agency_runtime.core.canary_proof import codex_activation_failures
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.header.contract import finalize_header
from agency_runtime.core.header.finalize import response_hash
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS
from agency_runtime.core.native_child_prompt_delivery import (
    parse_native_child_prompt_delivery,
    render_native_child_prompt_delivery,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import stub_inference_invoker, write_provider_config


def _valid_header() -> str:
    return (
        "Agency/Agencies loaded: code-reviewer\n"
        "Agency/Agencies delegated: code-reviewer via generic-worker/spawn_agent\n"
        "Skills loaded: none - no skill required\n"
        "Actual Model selected: canary-provider/model\n"
        "Recruited via: deterministic\n"
        "Why: exercise the installed runtime\n"
        "How it shaped outcome: identified the bounded regression risk\n\n"
        "Stripping may remove whitespace that callers intentionally preserve."
    )


def test_canary_module_import_does_not_depend_on_store_import_order() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from agency_runtime.core import canary; print(canary.CANARY_PROMPT)",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert canary.CANARY_PROMPT in completed.stdout


def _ready_host(_host: str) -> dict[str, object]:
    return {
        "host": "codex",
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "host_version": "codex 0.145.0",
        "install_id": "codex-install-1",
        "bundle_digest": "a" * 64,
    }


def _modified_hook_trust_report() -> dict[str, object]:
    events = tuple(event[0].lower() + event[1:] for event in CODEX_HOOK_EVENTS)
    return {
        "status": "modified",
        "expected_count": len(events),
        "observed_count": len(events),
        "trusted_count": 0,
        "managed_count": 0,
        "modified_count": len(events),
        "untrusted_count": 0,
        "disabled_count": 0,
        "missing_count": 0,
        "unexpected_count": 0,
        "duplicate_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "events": {
            event: {
                "enabled": True,
                "trustStatus": "modified",
                "currentHash": "sha256:" + "a" * 64,
            }
            for event in events
        },
    }


@pytest.fixture()
def configured_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield Store(tmp_path / "agency.db", config_path=config_path)
    finally:
        reset_config_cache()


def _finish_v2_chain_through_hooks(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    slug: str,
    unit: str,
    task_name: str,
    plan: dict[str, object],
) -> dict[str, object]:
    tool_use_id = "spawn-tool-use"
    receiver_id = "019fa500-1111-7222-8333-444455556666"
    encrypted_message = "gAAAAA" + "opaque-codex-canary-message" * 2
    opaque_canary = str(plan["goal"]) == CODEX_ACTIVATION_CANARY_WORK_UNIT
    bridge = HookBridge("codex", store=store)
    pre_payload = {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "turn_id": trace_id,
        "cwd": "C:\\workspace",
        "transcript_path": "C:\\state\\rollout.jsonl",
        "permission_mode": "default",
        "tool_name": "collaborationspawn_agent",
        "tool_use_id": tool_use_id,
        "tool_input": {
            "fork_turns": "none",
            "task_name": task_name,
            "message": encrypted_message if opaque_canary else str(plan["goal"]),
        },
    }
    pre_tool = bridge.handle(pre_payload)
    pre_output = pre_tool["hookSpecificOutput"]
    if opaque_canary:
        assert pre_output == {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
        post_input = pre_payload["tool_input"]
    else:
        post_input = pre_output["updatedInput"]
    start = bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": session_id,
            "turn_id": "codex-child-turn",
            "agent_id": receiver_id,
            "agent_type": "worker",
        }
    )
    delivery = parse_native_child_prompt_delivery(
        start["hookSpecificOutput"]["additionalContext"] if opaque_canary else post_input["message"]
    )
    assert delivery is not None
    assert delivery.tool_use_id == tool_use_id
    assert delivery.work_unit_id == unit
    assert delivery.specialist_slug == slug
    assert delivery.original_task == str(plan["goal"])
    if opaque_canary:
        assert delivery.activation_token == "x" * 43
        after_start = store.get_completion_evidence_snapshot(session_id, trace_id)
        [started_activation] = after_start["specialist_activations"]
        assert started_activation["specialist_slug"] == slug
        assert started_activation["worker_id"] == receiver_id
        assert started_activation["native_run_id"] == f"codex-agent:{receiver_id}"
    assert (
        bridge.handle(
            {
                **pre_payload,
                "hook_event_name": "PostToolUse",
                "tool_input": post_input,
                "tool_response": json.dumps({"task_name": f"/root/{task_name}"}),
            }
        )
        == {}
    )
    assert (
        bridge.handle(
            {
                "hook_event_name": "SubagentStop",
                "session_id": session_id,
                "agent_id": receiver_id,
                "agent_type": "worker",
            }
        )
        == {}
    )
    store.record_model_receipt(
        trace_id=trace_id,
        session_id=session_id,
        host="codex",
        resolved_provider="canary-provider",
        resolved_model="model",
        status="success",
    )
    response = finalize_header(
        "Stripping may remove whitespace that callers intentionally preserve.",
        session_id,
        store,
        "",
        trace_id,
    )
    assert (
        bridge.handle(
            {
                "hook_event_name": "Stop",
                "session_id": session_id,
                "turn_id": trace_id,
                "stop_hook_active": True,
                "last_assistant_message": response,
            }
        )
        == {}
    )
    return {
        "backend": "codex",
        "profile_scope": "current-profile",
        "status": "completed",
        "exit_code": 0,
        "output": response,
        "collaboration": {
            "spawn_count": 1,
            "wait_count": 1,
            "unexpected_item_count": 0,
            "unexpected_item_types": [],
            "calls": [
                {
                    "id": "spawn-1",
                    "event_type": "item.completed",
                    "tool": "spawn_agent",
                    "sender_thread_id": "parent-thread",
                    "receiver_thread_ids": [receiver_id],
                    "agents_states": {receiver_id: "running"},
                    "status": "completed",
                    "prompt_delivery": {
                        "host": delivery.host,
                        "parent_session_id": delivery.parent_session_id,
                        "parent_trace_id": delivery.parent_trace_id,
                        "tool_use_id": delivery.tool_use_id,
                        "work_unit_id": delivery.work_unit_id,
                        "specialist_slug": delivery.specialist_slug,
                        "specialist_version": delivery.specialist_version,
                        "specialist_prompt_hash": delivery.specialist_prompt_hash,
                        "goal_hash": str(plan["goal_hash"]),
                    },
                },
                {
                    "id": "wait-1",
                    "event_type": "item.completed",
                    "tool": "wait",
                    "sender_thread_id": "parent-thread",
                    "receiver_thread_ids": [receiver_id],
                    "agents_states": {receiver_id: "completed"},
                    "status": "completed",
                    "prompt_delivery": None,
                },
            ],
        },
    }


def _record_complete_v2_chain(
    store: Store,
    monkeypatch: pytest.MonkeyPatch,
    *,
    task: str,
    hook_provenance: bool = True,
    persisted_tool_use_id: str | None = None,
) -> dict[str, object]:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "codex-canary-session"
    trace_id = "codex-canary-trace"
    preflight = run_preflight(
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
        ),
    )
    slug = next(
        value for value in preflight.selected_specialists if value not in PROTECTED_AGENT_SLUGS
    )
    assert slug == "code-reviewer"
    assert len(preflight.delegation_plan) == 1
    plan = preflight.delegation_plan[0]
    unit = str(plan["work_unit_id"])
    task_name = codex_task_name_for_work_unit(unit)
    if hook_provenance and persisted_tool_use_id is None:
        return _finish_v2_chain_through_hooks(
            store,
            session_id=session_id,
            trace_id=trace_id,
            slug=slug,
            unit=unit,
            task_name=task_name,
            plan=plan,
        )
    tool_use_id = "spawn-tool-use"
    activation = store.prepare_delegation_activation(
        session_id=session_id,
        trace_id=trace_id,
        specialist_slug=slug,
        work_unit_id=unit,
        **(
            {
                "grant_origin": "native_hook",
                "tool_use_id": persisted_tool_use_id or tool_use_id,
            }
            if hook_provenance
            else {}
        ),
    )
    receiver_id = "019fa500-1111-7222-8333-444455556666"
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id=session_id,
        trace_id=trace_id,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
    )
    consumed = store.consume_delegation_activation(
        activation_token=str(activation["activation_token"]),
        session_id=session_id,
        trace_id=trace_id,
        specialist_slug=slug,
        work_unit_id=unit,
        worker_id=f"task:{task_name}",
        native_run_id=f"codex-task:{task_name}",
    )
    assert (
        mark_delegation_executed(
            store,
            session_id=session_id,
            trace_id=trace_id,
            host="codex",
            backend="spawn_agent",
            agent=slug,
            work_unit_id=unit,
            executed_worker_kind="generic-worker",
            executed_worker_id=f"task:{task_name}",
            native_run_id=f"codex-task:{task_name}",
        )
        == 1
    )
    store.record_native_child_stopped(
        host="codex",
        backend="spawn_agent",
        session_id=session_id,
        trace_id=trace_id,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
    )
    completion = store.get_completion_evidence_snapshot(session_id, trace_id)
    accepted = store.commit_terminal_finalization(
        session_id=session_id,
        trace_id=trace_id,
        host="codex",
        action="accept",
        response_hash=response_hash(_valid_header()),
        status="completed",
        expected_evidence_revision=completion["evidence_revision"],
    )
    assert accepted["authoritative"] is True
    return {
        "backend": "codex",
        "profile_scope": "current-profile",
        "status": "completed",
        "exit_code": 0,
        "output": _valid_header(),
        "collaboration": {
            "spawn_count": 1,
            "wait_count": 1,
            "calls": [
                {
                    "id": "spawn-1",
                    "event_type": "item.completed",
                    "tool": "spawn_agent",
                    "sender_thread_id": "parent-thread",
                    "receiver_thread_ids": [receiver_id],
                    "agents_states": {receiver_id: "running"},
                    "status": "completed",
                    "prompt_delivery": {
                        "host": "codex",
                        "parent_session_id": session_id,
                        "parent_trace_id": trace_id,
                        "tool_use_id": tool_use_id,
                        "work_unit_id": unit,
                        "specialist_slug": slug,
                        "specialist_version": str(consumed["version"]),
                        "specialist_prompt_hash": str(consumed["prompt_hash"]),
                        "goal_hash": str(plan["goal_hash"]),
                    },
                },
                {
                    "id": "wait-1",
                    "event_type": "item.completed",
                    "tool": "wait",
                    "sender_thread_id": "parent-thread",
                    "receiver_thread_ids": [receiver_id],
                    "agents_states": {receiver_id: "completed"},
                    "status": "completed",
                    "prompt_delivery": None,
                },
            ],
        },
    }


def test_codex_canary_requires_and_attests_one_complete_v2_activation_chain(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = configured_store.db_path

    class Backend:
        def execute(self, **kwargs: object) -> dict[str, object]:
            return _record_complete_v2_chain(
                configured_store,
                monkeypatch,
                task=str(kwargs["task"]),
            )

    report = canary.run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CURRENT-PROFILE CANARY",
        db_path=path,
        profile_scope="current-profile",
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: Backend(),
    )

    assert report["canary_passed"] is True, report["unmet_prerequisites"]
    assert report["attestation_persisted"] is True
    assert report["evidence"]["proven"] is True
    assert report["evidence"]["cardinalities"] == {
        "routes": 1,
        "runs": 1,
        "traces": 1,
        "unit_agent_plan": 1,
        "delegations": 1,
        "activation_grants": 1,
        "activation_consumptions": 1,
        "worker_runs": 1,
        "specialist_loads": 1,
        "finalizations": 1,
    }
    attestation = configured_store.get_host_canary_attestation("codex")
    assert attestation is not None
    assert attestation["proof_contract"] == "agency.codex-activation-canary.v1"
    assert len(attestation["proof_digest"]) == 64


def test_codex_post_tool_reconciles_subagent_start_consumption_without_callback_id(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "codex-callback-rewrite-session"
    trace_id = "codex-callback-rewrite-trace"
    preflight = run_preflight(
        configured_store,
        session_id=session_id,
        trace_id=trace_id,
        user_message="Review the exact supplied change for correctness.",
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
        ),
    )
    [plan] = preflight.delegation_plan
    unit = str(plan["work_unit_id"])
    slug = str(plan["recommended_agent"])
    task_name = codex_task_name_for_work_unit(unit)
    pre_tool_use_id = "call_pre_tool_identity"
    configured_store.prepare_delegation_activation(
        session_id=session_id,
        trace_id=trace_id,
        specialist_slug=slug,
        work_unit_id=unit,
        grant_origin="native_hook",
        tool_use_id=pre_tool_use_id,
    )
    receiver_id = "019fa500-2222-7333-8444-555566667777"
    configured_store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
    )
    consumed = configured_store.consume_delegation_activation(
        activation_token="",
        native_hook_tool_use_id=pre_tool_use_id,
        session_id=session_id,
        trace_id=trace_id,
        specialist_slug=slug,
        work_unit_id=unit,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
        require_native_child_started=True,
        match_native_child_identity=True,
    )

    assert (
        HookBridge("codex", store=configured_store).handle(
            {
                "hook_event_name": "PostToolUse",
                "session_id": session_id,
                "turn_id": trace_id,
                "cwd": "C:\\workspace",
                "transcript_path": "C:\\state\\rollout.jsonl",
                "permission_mode": "default",
                "tool_name": "collaborationspawn_agent",
                "tool_input": {
                    "fork_turns": "none",
                    "task_name": f"/root/{task_name}",
                    "message": str(plan["goal"]),
                },
                "tool_response": json.dumps({"task_name": f"/root/{task_name}"}),
            }
        )
        == {}
    )
    [delegation] = configured_store.get_delegations(trace_id)
    assert delegation["status"] == "delegated"
    assert delegation["activation_receipt_id"] == consumed["id"]
    assert delegation["retrieved_specialist_slug"] == slug
    assert delegation["executed_worker_id"] == receiver_id
    assert delegation["native_run_id"] == f"codex-agent:{receiver_id}"


def test_codex_subagent_start_promotes_earlier_synthetic_spawn_delegation(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mirror Codex's live PostToolUse-before-SubagentStart callback order."""

    from agency_runtime.core.policy.defaults import STARTER_ROSTER
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", "1")
    configured_store.reconcile_bundled_agents(STARTER_ROSTER)
    session_id = "codex-live-order-session"
    trace_id = "codex-live-order-trace"
    preflight = run_preflight(
        configured_store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=(canary.CANARY_PROMPT + "\n\nCanary nonce: 0123456789abcdef0123456789abcdef"),
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
        ),
    )
    [plan] = preflight.delegation_plan
    unit = str(plan["work_unit_id"])
    slug = str(plan["recommended_agent"])
    task_name = codex_task_name_for_work_unit(unit)
    tool_use_id = "call_live_callback_order"
    bridge = HookBridge("codex", store=configured_store)
    pre_payload = {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "turn_id": trace_id,
        "cwd": "C:\\workspace",
        "transcript_path": "C:\\state\\rollout.jsonl",
        "permission_mode": "default",
        "tool_name": "collaborationspawn_agent",
        "tool_use_id": tool_use_id,
        "tool_input": {
            "fork_turns": "none",
            "task_name": task_name,
            "message": "gAAAAA" + "opaque-codex-canary-message" * 2,
        },
    }
    pre_tool = bridge.handle(pre_payload)
    assert pre_tool["hookSpecificOutput"] == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }
    post_input = pre_payload["tool_input"]

    assert (
        bridge.handle(
            {
                **pre_payload,
                "hook_event_name": "PostToolUse",
                "tool_input": post_input,
                "tool_response": json.dumps({"task_name": f"/root/{task_name}"}),
            }
        )
        == {}
    )
    [synthetic] = configured_store.get_delegations(trace_id)
    assert synthetic["executed_worker_id"] == f"task:{task_name}"
    assert synthetic["native_run_id"] == f"codex-task:{task_name}"
    assert not synthetic["activation_receipt_id"]

    receiver_id = "019fa500-3333-7444-8555-666677778888"
    start = bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": session_id,
            "turn_id": "codex-child-turn",
            "agent_id": receiver_id,
            "agent_type": "worker",
        }
    )

    delivered = parse_native_child_prompt_delivery(start["hookSpecificOutput"]["additionalContext"])
    assert delivered is not None
    assert delivered.work_unit_id == unit
    [delegation] = configured_store.get_delegations(trace_id)
    assert delegation["activation_receipt_id"]
    assert delegation["retrieved_specialist_slug"] == slug
    assert delegation["executed_worker_kind"] == "generic-worker"
    assert delegation["executed_worker_id"] == receiver_id
    assert delegation["native_run_id"] == f"codex-agent:{receiver_id}"
    assert (
        bridge.handle(
            {
                "hook_event_name": "SubagentStop",
                "session_id": session_id,
                "agent_id": receiver_id,
                "agent_type": "worker",
            }
        )
        == {}
    )
    [outcome_free] = configured_store.get_delegations(trace_id)
    assert outcome_free["status"] == "delegated"
    assert (
        bridge.handle(
            {
                "hook_event_name": "SubagentStop",
                "session_id": session_id,
                "agent_id": receiver_id,
                "agent_type": "worker",
                "last_assistant_message": "The specialist completed the assigned review.",
            }
        )
        == {}
    )
    [completed] = configured_store.get_delegations(trace_id)
    assert completed["status"] == "completed"
    evidence = configured_store.get_canary_activation_snapshot(
        host="codex",
        query_hash=response_hash(
            canary.CANARY_PROMPT + "\n\nCanary nonce: 0123456789abcdef0123456789abcdef"
        ),
    )
    [worker_run] = evidence["worker_runs"]
    assert worker_run["delegation_event_id"] == delegation["id"]
    assert worker_run["work_unit_id"] == unit
    assert worker_run["exit_code"] == 0
    assert worker_run["ended_at"]


def test_codex_activation_proof_rejects_parent_only_manual_grant(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = canary.CANARY_PROMPT + "\n\nCanary nonce: manual-origin-negative"
    result = _record_complete_v2_chain(
        configured_store,
        monkeypatch,
        task=task,
        hook_provenance=False,
    )
    evidence = configured_store.get_canary_activation_snapshot(
        host="codex",
        query_hash=response_hash(task),
    )

    failures = codex_activation_failures(
        result=result,
        evidence=evidence,
        response_hash=response_hash(_valid_header()),
    )

    assert failures == (
        "activation grant was not issued by the native hook for the exact Codex tool call",
    )


def test_codex_activation_proof_rejects_mismatched_hook_tool_call(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = canary.CANARY_PROMPT + "\n\nCanary nonce: tool-id-negative"
    result = _record_complete_v2_chain(
        configured_store,
        monkeypatch,
        task=task,
        persisted_tool_use_id="different-spawn-tool-use",
    )
    evidence = configured_store.get_canary_activation_snapshot(
        host="codex",
        query_hash=response_hash(task),
    )

    failures = codex_activation_failures(
        result=result,
        evidence=evidence,
        response_hash=response_hash(_valid_header()),
    )

    assert failures == (
        "activation grant was not issued by the native hook for the exact Codex tool call",
    )


@pytest.mark.parametrize(
    "failure_kind",
    ["tool_unavailable", "extra_child", "unexpected_tool", "wrong_output"],
)
def test_codex_activation_proof_rejects_incomplete_or_mismatched_topology(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
) -> None:
    task = canary.CANARY_PROMPT + "\n\nCanary nonce: deterministic-negative"
    result = _record_complete_v2_chain(configured_store, monkeypatch, task=task)
    evidence = configured_store.get_canary_activation_snapshot(
        host="codex",
        query_hash=response_hash(task),
    )
    candidate = deepcopy(result)
    expected_hash = response_hash(str(result["output"]))
    if failure_kind == "tool_unavailable":
        candidate["collaboration"] = {"calls": [], "spawn_count": 0, "wait_count": 0}
    elif failure_kind == "extra_child":
        extra = deepcopy(candidate["collaboration"]["calls"][0])
        extra["id"] = "spawn-extra"
        extra["receiver_thread_ids"] = ["019fa500-aaaa-7bbb-8ccc-ddddeeeeffff"]
        candidate["collaboration"]["calls"].append(extra)
    elif failure_kind == "unexpected_tool":
        candidate["collaboration"].update(
            unexpected_item_count=1,
            unexpected_item_types=["command_execution"],
        )
    else:
        expected_hash = response_hash(str(result["output"]) + " changed")

    failures = codex_activation_failures(
        result=candidate,
        evidence=evidence,
        response_hash=expected_hash,
    )

    assert failures
    if failure_kind == "wrong_output":
        assert any("exact authoritative accepted finalization" in item for item in failures)
    elif failure_kind == "unexpected_tool":
        assert any("non-allowlisted tool" in item for item in failures)
    else:
        assert any("exactly one completed spawn" in item for item in failures)


def _process_result(
    stdout: str,
    *,
    timed_out: bool = False,
    stderr: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=124 if timed_out else 0,
        timed_out=timed_out,
        stdout_truncated=False,
        stderr_truncated=False,
        stdout=stdout,
        stderr=stderr,
    )


def _write_codex_rollout(
    root: Path,
    thread_id: str,
    events: list[dict[str, object]],
    *,
    day: str = "27",
) -> Path:
    directory = root / "2026" / "07" / day
    directory.mkdir(parents=True, exist_ok=True)
    for candidate in (root, root / "2026", root / "2026" / "07", directory):
        candidate.chmod(0o700)
    path = directory / f"rollout-2026-07-{day}T12-00-00-{thread_id}.jsonl"
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def test_codex_v2_rollout_recovers_spawn_omitted_from_stdout(tmp_path: Path) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    receiver_id = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    tool_use_id = "call-native-spawn"
    task_name = "unit_code_review"
    original_task = "Review the implementation."
    encrypted_parent_message = "gAAAAABopaque-parent-tool-ciphertext"
    activation_token = "x" * 43
    prompt_body = "You are the exact reviewer."
    delivery = render_native_child_prompt_delivery(
        original_task,
        prompt_body,
        host="codex",
        parent_session_id=parent_id,
        parent_trace_id="trace",
        tool_use_id=tool_use_id,
        work_unit_id="unit-code",
        specialist_slug="code-reviewer",
        specialist_version="v1",
        specialist_prompt_hash=response_hash(prompt_body),
        activation_token=activation_token,
    )
    rollout_root = tmp_path / "sessions"
    _write_codex_rollout(
        rollout_root,
        parent_id,
        [
            {"type": "session_meta", "payload": {"id": parent_id, "source": "exec"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "id": "spawn-item",
                    "name": "spawn_agent",
                    "namespace": "collaboration",
                    "call_id": tool_use_id,
                    "arguments": json.dumps(
                        {
                            "fork_turns": "none",
                            "message": encrypted_parent_message,
                            "task_name": task_name,
                        }
                    ),
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "sub_agent_activity",
                    "event_id": tool_use_id,
                    "agent_thread_id": receiver_id,
                    "agent_path": f"/root/{task_name}",
                    "kind": "started",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": tool_use_id,
                    "output": json.dumps({"task_name": f"/root/{task_name}"}),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "id": "wait-item",
                    "name": "wait_agent",
                    "namespace": "collaboration",
                    "call_id": "call-native-wait",
                    "arguments": json.dumps({"timeout_ms": 60_000}),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call-native-wait",
                    "output": json.dumps({"message": "Wait completed.", "timed_out": False}),
                },
            },
        ],
    )
    child_path = _write_codex_rollout(
        rollout_root,
        receiver_id,
        [
            {
                "type": "session_meta",
                "payload": {
                    "id": receiver_id,
                    "source": {
                        "subagent": {
                            "thread_spawn": {
                                "parent_thread_id": parent_id,
                                "depth": 1,
                                "agent_path": f"/root/{task_name}",
                            }
                        }
                    },
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": delivery}],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "last_agent_message": "done",
                    "error": None,
                },
            },
        ],
    )
    stdout = "\n".join(
        json.dumps(event)
        for event in [
            {"type": "thread.started", "thread_id": parent_id},
            {
                "type": "item.completed",
                "item": {
                    "id": "stdout-wait",
                    "type": "collab_tool_call",
                    "tool": "wait",
                    "sender_thread_id": parent_id,
                    "receiver_thread_ids": [],
                    "prompt": None,
                    "agents_states": {},
                    "status": "completed",
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": _valid_header()},
            },
            {"type": "turn.completed"},
        ]
    )

    record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
    )

    assert record["status"] == "completed"
    collaboration = record["collaboration"]
    assert collaboration["evidence_source"] == "persisted_rollout"
    assert collaboration["spawn_count"] == 1
    assert collaboration["wait_count"] == 1
    assert collaboration["calls"][0]["native_task_name"] == task_name
    assert collaboration["calls"][0]["event_type"] == "rollout_call_completed"
    assert collaboration["calls"][0]["receiver_thread_ids"] == [receiver_id]
    encoded = json.dumps(record)
    assert activation_token not in encoded
    assert prompt_body not in encoded
    assert original_task not in encoded
    assert encrypted_parent_message not in encoded

    conflict = [json.loads(line) for line in stdout.splitlines()]
    conflict[1]["item"]["receiver_thread_ids"] = ["019fa6a6-bbbb-7ccc-8ddd-eeffeeffeeff"]
    conflict[1]["item"]["agents_states"] = {
        "019fa6a6-bbbb-7ccc-8ddd-eeffeeffeeff": {"status": "completed"}
    }
    conflicting_record = codex_canary_record(
        _process_result("\n".join(json.dumps(event) for event in conflict)),
        profile_scope="current-profile",
        rollout_root=rollout_root,
    )
    assert conflicting_record["status"] == "failed"
    assert conflicting_record["exit_code"] == 0
    assert conflicting_record["failure_reason"] == ("codex_collaboration_projection_unavailable")

    successful_child = child_path.read_text(encoding="utf-8")
    failed_child_events = [json.loads(line) for line in successful_child.splitlines()]
    failed_child_events[-1]["payload"].update(
        last_agent_message=None,
        error="encrypted child payload could not be decoded",
    )
    child_path.write_text(
        "\n".join(json.dumps(event) for event in failed_child_events) + "\n",
        encoding="utf-8",
    )
    child_path.chmod(0o600)
    failed_child_record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
    )
    assert failed_child_record["status"] == "failed"
    assert failed_child_record["failure_reason"] == ("codex_collaboration_projection_unavailable")
    child_path.write_text(successful_child, encoding="utf-8")
    child_path.chmod(0o600)

    child_path.write_text(
        child_path.read_text(encoding="utf-8")
        + json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "id": "nested-tool",
                    "name": "spawn_agent",
                    "namespace": "collaboration",
                    "call_id": "nested-call",
                    "arguments": "{}",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    child_path.chmod(0o600)
    nested_record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
    )
    assert nested_record["status"] == "failed"
    assert nested_record["exit_code"] == 0
    assert nested_record["failure_reason"] == "codex_collaboration_projection_unavailable"


def test_codex_v2_rollout_projection_fails_closed_on_ambiguous_parent(
    tmp_path: Path,
) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    rollout_root = tmp_path / "sessions"
    events = [{"type": "session_meta", "payload": {"id": parent_id, "source": "exec"}}]
    _write_codex_rollout(rollout_root, parent_id, events, day="27")
    _write_codex_rollout(rollout_root, parent_id, events, day="28")
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": parent_id}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": _valid_header()},
                }
            ),
            json.dumps({"type": "turn.completed"}),
        ]
    )

    record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
    )

    assert record["status"] == "failed"
    assert record["exit_code"] == 0
    assert record["failure_reason"] == "codex_collaboration_projection_unavailable"
    assert "collaboration" not in record


def test_codex_ephemeral_parent_failure_is_classified_without_raw_stderr() -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    result = _process_result("")
    result.returncode = 1
    result.stderr = f"collab spawn failed: no thread with id: {parent_id}"

    record = codex_canary_record(result, profile_scope="current-profile")

    assert record["failure_reason"] == "native_collaboration_full_history_parent_unavailable"
    assert parent_id not in json.dumps(record)


def test_codex_jsonl_parser_projects_one_spawn_wait_chain_without_prompt_content() -> None:
    receiver_id = "019fa500-1111-7222-8333-444455556666"
    prompt = render_native_child_prompt_delivery(
        "Review the implementation.",
        "You are the exact reviewer.",
        host="codex",
        parent_session_id="session",
        parent_trace_id="trace",
        tool_use_id="spawn-call",
        work_unit_id="unit-code",
        specialist_slug="code-reviewer",
        specialist_version="v1",
        specialist_prompt_hash=response_hash("You are the exact reviewer."),
        activation_token="x" * 43,
    )
    events = [
        {
            "type": "item.started",
            "item": {
                "id": "spawn-1",
                "type": "collab_tool_call",
                "tool": "spawn_agent",
                "sender_thread_id": "parent",
                "receiver_thread_ids": [],
                "prompt": prompt,
                "agents_states": {},
                "status": "in_progress",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "spawn-1",
                "type": "collab_tool_call",
                "tool": "spawn_agent",
                "sender_thread_id": "parent",
                "receiver_thread_ids": [receiver_id],
                "prompt": None,
                "agents_states": {receiver_id: {"status": "running", "message": None}},
                "status": "completed",
            },
        },
        {
            "type": "item.started",
            "item": {
                "id": "wait-1",
                "type": "collab_tool_call",
                "tool": "wait",
                "sender_thread_id": "parent",
                "receiver_thread_ids": [receiver_id],
                "prompt": None,
                "agents_states": {receiver_id: {"status": "running", "message": None}},
                "status": "in_progress",
            },
        },
        {
            "type": "item.completed",
            "item": {
                "id": "wait-1",
                "type": "collab_tool_call",
                "tool": "wait",
                "sender_thread_id": "parent",
                "receiver_thread_ids": [receiver_id],
                "prompt": None,
                "agents_states": {receiver_id: {"status": "completed", "message": "done"}},
                "status": "completed",
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": _valid_header()}},
        {"type": "turn.completed"},
    ]
    stdout = "\n".join(json.dumps(event) for event in events)

    record = codex_canary_record(_process_result(stdout), profile_scope="current-profile")

    assert record["status"] == "completed"
    assert record["collaboration"]["spawn_count"] == 1
    assert record["collaboration"]["wait_count"] == 1
    assert record["collaboration"]["unexpected_item_count"] == 0
    assert record["collaboration"]["calls"][0]["prompt_delivery"]["tool_use_id"] == "spawn-call"
    encoded = json.dumps(record)
    assert "x" * 43 not in encoded
    assert "You are the exact reviewer" not in encoded


def test_codex_jsonl_parser_ignores_only_exact_isolated_hook_trust_notice() -> None:
    notice = {
        "type": "item.completed",
        "item": {
            "id": "trust-notice",
            "type": "error",
            "message": "`--dangerously-bypass-hook-trust` is enabled. Enabled hooks may run "
            "without review for this invocation.",
        },
    }
    other = {
        "type": "item.completed",
        "item": {"id": "other-error", "type": "error", "message": "different"},
    }

    accepted = codex_collaboration_evidence(json.dumps(notice))
    rejected = codex_collaboration_evidence("\n".join(map(json.dumps, (notice, other))))

    assert accepted is not None
    assert accepted["unexpected_item_count"] == 0
    assert rejected is not None
    assert rejected["unexpected_item_count"] == 1
    assert rejected["unexpected_item_types"] == ["error"]


def test_codex_jsonl_parser_projects_non_allowlisted_tool_type_without_content() -> None:
    events = [
        {
            "type": "item.completed",
            "item": {
                "id": "command-1",
                "type": "command_execution",
                "command": "sensitive command body",
            },
        },
        {"type": "item.completed", "item": {"type": "agent_message", "text": _valid_header()}},
        {"type": "turn.completed"},
    ]
    stdout = "\n".join(json.dumps(event) for event in events)

    record = codex_canary_record(_process_result(stdout), profile_scope="current-profile")

    assert record["status"] == "completed"
    assert record["collaboration"]["unexpected_item_types"] == ["command_execution"]
    assert record["collaboration"]["unexpected_item_count"] == 1
    assert "sensitive command body" not in json.dumps(record)


def test_codex_canary_projects_only_one_fixed_hook_diagnostic() -> None:
    stdout = "\n".join(
        map(
            json.dumps,
            (
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": _valid_header()},
                },
                {"type": "turn.completed"},
            ),
        )
    )
    stderr = (
        "unrelated stderr\n"
        "agency_hook_diagnostic codex_post_tool_reconcile=response_shape_mismatch\n"
    )

    record = codex_canary_record(_process_result(stdout, stderr=stderr))
    ambiguous = codex_canary_record(
        _process_result(
            stdout,
            stderr=(stderr + "agency_hook_diagnostic codex_post_tool_reconcile=lineage_mismatch\n"),
        )
    )
    unsupported = codex_canary_record(
        _process_result(
            stdout,
            stderr="agency_hook_diagnostic codex_post_tool_reconcile=arbitrary_label\n",
        )
    )

    assert record["hook_diagnostic"] == "response_shape_mismatch"
    assert "unrelated stderr" not in json.dumps(record)
    assert "hook_diagnostic" not in ambiguous
    assert "hook_diagnostic" not in unsupported


def test_codex_canary_snapshot_projects_persisted_hook_diagnostic(
    configured_store: Store,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    monkeypatch.setattr(
        inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )
    session_id = "codex-diagnostic-session"
    trace_id = "codex-diagnostic-trace"
    preflight = run_preflight(
        configured_store,
        session_id=session_id,
        trace_id=trace_id,
        user_message="Review the exact supplied change for correctness.",
        host="codex",
        capability_receipt=native_adapter_capability_receipt(
            "codex",
            platform="windows" if os.name == "nt" else "linux",
            session_id=session_id,
            trace_id=trace_id,
        ),
    )

    configured_store.record_codex_canary_reconciliation_diagnostic(
        session_id=session_id,
        trace_id=trace_id,
        reason="response_shape_mismatch",
    )
    snapshot = configured_store.get_canary_activation_snapshot(
        host="codex",
        query_hash=str(preflight.routing["query_hash"]),
    )

    assert snapshot["hook_diagnostic"] == "response_shape_mismatch"


def test_failed_current_profile_reverification_invalidates_prior_attestation(
    configured_store: Store,
) -> None:
    configured_store.record_host_canary_attestation(
        host="codex",
        proof_contract="agency.codex-activation-canary.v1",
        proof_digest="a" * 64,
        profile_scope="current-profile",
        platform_system="test",
        platform_release="test",
        platform_machine="test",
        host_version="codex 0.145.0",
        plugin_version="0.1.0",
        install_id="codex-install-1",
        bundle_digest="a" * 64,
        trace_id="prior-trace",
    )

    class Backend:
        def execute(self, **_kwargs: object) -> dict[str, object]:
            return {
                "backend": "codex",
                "profile_scope": "current-profile",
                "status": "failed",
                "exit_code": 1,
            }

    report = canary.run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CURRENT-PROFILE CANARY",
        db_path=configured_store.db_path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: Backend(),
        profile_scope="current-profile",
    )

    assert report["canary_passed"] is False
    assert report["prior_attestation_invalidated"] is True
    assert configured_store.get_host_canary_attestation("codex") is None


def test_current_profile_hook_trust_failure_is_reported_precisely(
    configured_store: Store,
) -> None:
    class Backend:
        def execute(self, **_kwargs: object) -> dict[str, object]:
            return {
                "backend": "codex",
                "profile_scope": "current-profile",
                "status": "failed",
                "exit_code": 1,
                "stdout_truncated": False,
                "stderr_truncated": False,
                "failure_reason": "codex_hook_trust_not_ready",
                "hook_trust": _modified_hook_trust_report(),
                "model_invocation_attempted": False,
            }

    report = canary.run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CURRENT-PROFILE CANARY",
        db_path=configured_store.db_path,
        inspector=_ready_host,
        backend_factory=lambda *_args, **_kwargs: Backend(),
        profile_scope="current-profile",
    )

    assert report["canary_passed"] is False
    assert report["invocation"]["failure_reason"] == "codex_hook_trust_not_ready"
    assert report["invocation"]["hook_trust"]["status"] == "modified"
    assert report["invocation"]["model_invocation_attempted"] is False
    assert report["unmet_prerequisites"][0] == (
        "Codex does not report the settled Agency hook inventory as enabled and trusted"
    )


def test_codex_process_timeout_remains_a_timeout() -> None:
    record = codex_canary_record(_process_result("", timed_out=True))
    assert record["status"] == "timed_out"
    assert record["exit_code"] == 124
    assert record["failure_reason"] == "codex_exec_timed_out"
