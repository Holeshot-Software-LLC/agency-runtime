from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core import canary
from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.canary_backends import codex_canary_record
from agency_runtime.core.canary_proof import codex_activation_failures
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.header.contract import finalize_header
from agency_runtime.core.header.finalize import response_hash
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
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
    bridge = HookBridge("codex", store=store)
    pre_payload = {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "turn_id": trace_id,
        "tool_name": "spawn_agent",
        "tool_use_id": tool_use_id,
        "tool_input": {
            "task_name": task_name,
            "message": str(plan["goal"]),
            "agent_type": "worker",
        },
    }
    pre_tool = bridge.handle(pre_payload)
    updated_input = pre_tool["hookSpecificOutput"]["updatedInput"]
    delivery = parse_native_child_prompt_delivery(updated_input["message"])
    assert delivery is not None
    assert delivery.tool_use_id == tool_use_id
    assert delivery.work_unit_id == unit
    assert delivery.specialist_slug == slug
    bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": session_id,
            "agent_id": receiver_id,
            "agent_type": "worker",
        }
    )
    assert (
        bridge.handle(
            {
                **pre_payload,
                "hook_event_name": "PostToolUse",
                "tool_input": updated_input,
                "tool_response": {"task_name": task_name, "status": "accepted"},
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

    assert report["canary_passed"] is True
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


def _process_result(stdout: str, *, timed_out: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=124 if timed_out else 0,
        timed_out=timed_out,
        stdout_truncated=False,
        stderr_truncated=False,
        stdout=stdout,
        stderr="",
    )


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


def test_codex_process_timeout_remains_a_timeout() -> None:
    record = codex_canary_record(_process_result("", timed_out=True))
    assert record["status"] == "timed_out"
    assert record["exit_code"] == 124
