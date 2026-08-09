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
from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.canary_backends import (
    _assert_codex_child_activation_is_tool_free,
    _codex_child_execution_projection,
    _codex_product_child_tool_evidence,
    _codex_product_rollout_collaboration_evidence,
    _codex_product_wait_counts,
    codex_canary_record,
    codex_collaboration_evidence,
)
from agency_runtime.core.codex_child_tool_evidence import (
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_FIELDS,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_SCHEMA,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V2_FIELDS,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V2_SCHEMA,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V3_FIELDS,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V3_SCHEMA,
    classify_codex_exec_wrapper_failure,
    decode_stored_codex_child_tool_evidence,
)
from agency_runtime.core.codex_native_plan_scope import deserialize_codex_native_plan_scope
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.header.contract import finalize_header
from agency_runtime.core.header.finalize import response_hash
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS
from agency_runtime.core.native_child_prompt_delivery import (
    parse_native_child_prompt_delivery,
    render_codex_direct_native_child_prompt_delivery,
    render_codex_native_child_execution_message,
    render_codex_opaque_native_child_prompt_delivery,
    render_native_child_prompt_delivery,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import work_unit_goal_hash
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


def _two_turn_child_events(execution_message: str) -> list[dict[str, object]]:
    return [
        {
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": "activation-turn"},
        },
        {
            "type": "response_item",
            "payload": {"type": "agent_message", "content": "ready"},
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": "activation-turn",
                "last_agent_message": "ready",
                "error": None,
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "message", "content": execution_message},
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": "execution-turn"},
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "task_complete",
                "turn_id": "execution-turn",
                "last_agent_message": "complete",
                "error": None,
            },
        },
    ]


def test_product_child_tool_evidence_is_fixed_and_content_free() -> None:
    events = [
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "status": "completed",
                "call_id": "exec-call",
                "input": (
                    'const one=await tools.shell_command({command:"private exec input"});'
                    'const two=await tools.apply_patch("private patch input");'
                    "await tools.private_tool();"
                ),
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "shell_command",
                "status": "failed",
                "arguments": "private shell arguments",
            },
        },
        {
            "type": "response_item",
            "payload": {"type": "function_call", "name": "apply_patch"},
        },
        {
            "type": "response_item",
            "payload": {"type": "function_call", "name": "private-tool", "status": "completed"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "exec-call",
                "output": [{"type": "input_text", "text": "Script failed\nprivate tool output"}],
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "patch_apply_end",
                "success": True,
                "status": "completed",
                "changes": {"private-path": {"type": "add", "content": "private bytes"}},
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "patch_apply_end",
                "success": False,
                "status": "failed",
                "stderr": "private failure",
            },
        },
        {"type": "event_msg", "payload": {"type": "patch_apply_end"}},
    ]

    evidence = _codex_product_child_tool_evidence(events)

    assert evidence == {
        "child_tool_call_count": 4,
        "child_function_tool_call_count": 3,
        "child_custom_tool_call_count": 1,
        "child_exec_tool_call_count": 1,
        "child_apply_patch_tool_call_count": 1,
        "child_shell_command_tool_call_count": 1,
        "child_other_tool_call_count": 1,
        "child_completed_tool_call_count": 2,
        "child_failed_tool_call_count": 1,
        "child_unknown_tool_call_count": 1,
        "child_tool_output_count": 1,
        "child_tool_output_missing_count": 3,
        "child_patch_apply_success_count": 1,
        "child_patch_apply_failure_count": 1,
        "child_patch_apply_unknown_count": 1,
        "child_exec_input_classified_count": 1,
        "child_exec_input_unclassified_count": 0,
        "child_exec_nested_tool_call_count": 3,
        "child_exec_nested_apply_patch_tool_call_count": 1,
        "child_exec_nested_shell_command_tool_call_count": 1,
        "child_exec_nested_other_tool_call_count": 1,
        "child_exec_wrapper_completed_count": 0,
        "child_exec_wrapper_failed_count": 1,
        "child_exec_wrapper_yielded_count": 0,
        "child_exec_wrapper_unknown_count": 0,
        "child_exec_wrapper_windows_split_writable_roots_count": 0,
        "child_exec_wrapper_windows_sandbox_setup_failed_count": 0,
        "child_exec_wrapper_approval_rejected_count": 0,
        "child_exec_wrapper_permission_denied_count": 0,
        "child_exec_wrapper_process_failed_other_count": 1,
        "child_exec_wrapper_failure_unknown_count": 0,
        "child_exec_wrapper_apply_patch_completed_count": 0,
        "child_exec_wrapper_apply_patch_failed_count": 0,
        "child_exec_wrapper_apply_patch_yielded_count": 0,
        "child_exec_wrapper_apply_patch_unknown_count": 0,
        "child_exec_wrapper_shell_command_completed_count": 0,
        "child_exec_wrapper_shell_command_failed_count": 0,
        "child_exec_wrapper_shell_command_yielded_count": 0,
        "child_exec_wrapper_shell_command_unknown_count": 0,
        "child_exec_wrapper_other_completed_count": 0,
        "child_exec_wrapper_other_failed_count": 0,
        "child_exec_wrapper_other_yielded_count": 0,
        "child_exec_wrapper_other_unknown_count": 0,
        "child_exec_wrapper_ambiguous_completed_count": 0,
        "child_exec_wrapper_ambiguous_failed_count": 1,
        "child_exec_wrapper_ambiguous_yielded_count": 0,
        "child_exec_wrapper_ambiguous_unknown_count": 0,
    }
    encoded = json.dumps(evidence)
    assert all(
        private not in encoded
        for private in (
            "private exec input",
            "private patch input",
            "private shell arguments",
            "private-tool",
            "private tool output",
            "private-path",
            "private bytes",
            "private failure",
        )
    )


def test_product_child_tool_evidence_ignores_quoted_names_and_fails_closed() -> None:
    events = [
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "status": "completed",
                "call_id": "classified",
                "input": (
                    "const quoted='tools.apply_patch('; // tools.private_tool()\n"
                    "await tools.shell_command({});"
                ),
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "status": "completed",
                "call_id": "unclassified",
                "input": "const dynamic=`${tools.apply_patch(value)}`;",
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "classified",
                "output": [{"type": "input_text", "text": "Script completed\nprivate"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": "unclassified",
                "output": [
                    {
                        "type": "input_text",
                        "text": "Script running with cell ID private\n",
                    }
                ],
            },
        },
    ]

    evidence = _codex_product_child_tool_evidence(events)

    assert evidence["child_exec_input_classified_count"] == 1
    assert evidence["child_exec_input_unclassified_count"] == 1
    assert evidence["child_exec_nested_tool_call_count"] == 1
    assert evidence["child_exec_nested_apply_patch_tool_call_count"] == 0
    assert evidence["child_exec_nested_shell_command_tool_call_count"] == 1
    assert evidence["child_exec_wrapper_completed_count"] == 1
    assert evidence["child_exec_wrapper_yielded_count"] == 1
    assert evidence["child_exec_wrapper_shell_command_completed_count"] == 1
    assert evidence["child_exec_wrapper_ambiguous_yielded_count"] == 1
    assert "private" not in json.dumps(evidence)


def test_product_child_tool_evidence_keeps_canonical_v1_store_rows_readable() -> None:
    legacy = dict.fromkeys(CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_FIELDS, 0)
    payload = json.dumps(legacy, sort_keys=True, separators=(",", ":"))

    assert (
        decode_stored_codex_child_tool_evidence(
            schema=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_SCHEMA,
            source=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE,
            recorded_at="2026-08-02T19:40:48Z",
            payload=payload,
        )
        == legacy
    )


def test_product_child_tool_evidence_keeps_canonical_v2_store_rows_readable() -> None:
    legacy = dict.fromkeys(CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V2_FIELDS, 0)
    payload = json.dumps(legacy, sort_keys=True, separators=(",", ":"))

    assert (
        decode_stored_codex_child_tool_evidence(
            schema=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V2_SCHEMA,
            source=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE,
            recorded_at="2026-08-02T19:40:48Z",
            payload=payload,
        )
        == legacy
    )


def test_product_child_tool_evidence_keeps_canonical_v3_store_rows_readable() -> None:
    legacy = dict.fromkeys(CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V3_FIELDS, 0)
    payload = json.dumps(legacy, sort_keys=True, separators=(",", ":"))

    assert (
        decode_stored_codex_child_tool_evidence(
            schema=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V3_SCHEMA,
            source=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE,
            recorded_at="2026-08-02T19:40:48Z",
            payload=payload,
        )
        == legacy
    )


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        (
            "Script failed\nfailed to prepare windows sandbox wrapper: windows "
            "sandbox cannot enforce split writable root sets directly",
            "windows_split_writable_roots",
        ),
        ("Script failed\nfailed to prepare fs sandbox", "windows_sandbox_setup_failed"),
        (
            "Script failed\nThis action was rejected due to unacceptable risk.",
            "approval_rejected",
        ),
        ("Script failed\nAccess is denied.", "permission_denied"),
        ("Script failed\nExit code: 7", "process_failed_other"),
        (
            [
                {"type": "input_text", "text": "Script failed"},
                {"type": "private_type", "text": "private"},
            ],
            "failure_unknown",
        ),
    ),
)
def test_wrapper_failure_classification_is_fixed_and_content_free(
    output: object,
    expected: str,
) -> None:
    assert classify_codex_exec_wrapper_failure(output) == expected


def test_product_child_tool_evidence_projects_fixed_wrapper_failure_category() -> None:
    evidence = _codex_product_child_tool_evidence(
        [
            {
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call",
                    "name": "exec",
                    "status": "completed",
                    "call_id": "exec-call",
                    "input": 'await tools.apply_patch("private");',
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call_output",
                    "call_id": "exec-call",
                    "output": "Script failed\nAccess is denied at private path",
                },
            },
        ]
    )

    assert evidence["child_exec_wrapper_failed_count"] == 1
    assert evidence["child_exec_wrapper_permission_denied_count"] == 1
    assert evidence["child_exec_wrapper_process_failed_other_count"] == 0
    assert evidence["child_exec_wrapper_apply_patch_failed_count"] == 1
    assert "private path" not in json.dumps(evidence)


def test_product_child_tool_evidence_correlates_nested_tool_and_wrapper_outcome() -> None:
    events = []
    wrappers = (
        ("patch", 'await tools.apply_patch("private patch");', "Script failed\nExit code: 1"),
        ("shell-ok", "await tools.shell_command({command: 'private'});", "Script completed"),
        (
            "shell-fail",
            "await tools.shell_command({command: 'secret'});",
            "Script failed\nExit code: 2",
        ),
    )
    for call_id, input_value, output in wrappers:
        events.extend(
            (
                {
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call",
                        "name": "exec",
                        "status": "completed",
                        "call_id": call_id,
                        "input": input_value,
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call_output",
                        "call_id": call_id,
                        "output": output,
                    },
                },
            )
        )

    evidence = _codex_product_child_tool_evidence(events)

    assert evidence["child_exec_wrapper_apply_patch_failed_count"] == 1
    assert evidence["child_exec_wrapper_shell_command_completed_count"] == 1
    assert evidence["child_exec_wrapper_shell_command_failed_count"] == 1
    assert evidence["child_exec_wrapper_process_failed_other_count"] == 2
    assert not any(
        evidence[f"child_exec_wrapper_{kind}_{outcome}_count"]
        for kind in ("other", "ambiguous")
        for outcome in ("completed", "failed", "yielded", "unknown")
    )
    assert "private" not in json.dumps(evidence)
    assert "secret" not in json.dumps(evidence)


def test_codex_child_projection_rejects_duplicate_execution_delivery() -> None:
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Perform the exact task."),
        goal="Perform the exact task.",
    )
    events = _two_turn_child_events(message)
    events.insert(4, deepcopy(events[3]))

    with pytest.raises(ValueError, match="conflicting execution envelope"):
        _codex_child_execution_projection(
            events,
            expected={
                "work_unit_id": "unit-1234567890",
                "native_task_name": "unit_1234567890",
                "goal_hash": work_unit_goal_hash("Perform the exact task."),
            },
            opaque_message=None,
        )


def test_codex_product_child_activation_turn_must_be_tool_free() -> None:
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Perform the exact task."),
        goal="Perform the exact task.",
    )
    events = _two_turn_child_events(message)
    events.insert(
        2,
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "shell_command",
                "call_id": "activation-tool",
            },
        },
    )

    with pytest.raises(ValueError, match="activation turn"):
        _assert_codex_child_activation_is_tool_free(events)


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


def _prepare_exact_opaque_activation(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    plan: dict[str, object],
    tool_use_id: str,
) -> dict[str, object]:
    """Use the preflight-staged private scope for one synthetic hook grant."""

    work_unit_id = str(plan["work_unit_id"])
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT scope_payload FROM codex_native_plan_scopes "
            "WHERE session_id = ? AND trace_id = ? AND work_unit_id = ?",
            (session_id, trace_id, work_unit_id),
        ).fetchone()
    finally:
        connection.close()
    scope = deserialize_codex_native_plan_scope(row["scope_payload"])
    return store.prepare_codex_opaque_native_child_activation(
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=work_unit_id,
        specialist_slug=scope.specialist.slug,
        specialist_version=scope.specialist.version,
        specialist_prompt_hash=scope.specialist.content_hash,
        goal_hash=str(plan["goal_hash"]),
        resource_hashes=list(plan["resource_hashes"]),
        required_evidence=list(plan["required_evidence"]),
        tool_use_id=tool_use_id,
    )


def _direct_collaboration(
    *,
    receiver_id: str,
    prompt_delivery: dict[str, object],
    work_unit_id: str,
    task_name: str,
    goal_hash: str,
) -> dict[str, object]:
    execution_delivery = {
        "work_unit_id": work_unit_id,
        "native_task_name": task_name,
        "goal_hash": goal_hash,
    }
    common = {
        "event_type": "item.completed",
        "sender_thread_id": "parent-thread",
        "receiver_thread_ids": [receiver_id],
        "status": "completed",
    }
    return {
        "spawn_count": 1,
        "followup_count": 0,
        "wait_count": 1,
        "unexpected_item_count": 0,
        "unexpected_item_types": [],
        "calls": [
            {
                **common,
                "id": "spawn-1",
                "tool": "spawn_agent",
                "agents_states": {receiver_id: "running"},
                "prompt_delivery": prompt_delivery,
                "execution_delivery": execution_delivery,
                "followup_tool_use_id": "spawn-tool-use",
            },
            {
                **common,
                "id": "wait-execution",
                "tool": "wait",
                "agents_states": {receiver_id: "completed"},
                "prompt_delivery": None,
            },
        ],
    }


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
            "message": encrypted_message,
        },
    }
    pre_tool = bridge.handle(pre_payload)
    pre_output = pre_tool["hookSpecificOutput"]
    assert pre_output == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }
    post_input = pre_payload["tool_input"]
    start = bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": session_id,
            "turn_id": "codex-child-turn",
            "agent_id": receiver_id,
            "agent_type": "worker",
        }
    )
    delivery = parse_native_child_prompt_delivery(start["hookSpecificOutput"]["additionalContext"])
    assert delivery is not None
    assert delivery.tool_use_id == tool_use_id
    assert delivery.work_unit_id == unit
    assert delivery.specialist_slug == slug
    assert delivery.original_task == ""
    assert delivery.goal_hash == str(plan["goal_hash"])
    assert delivery.activation_token == ""
    after_start = store.get_completion_evidence_snapshot(session_id, trace_id)
    [started_activation] = after_start["specialist_activations"]
    assert started_activation["specialist_slug"] == slug
    assert started_activation["worker_id"] == receiver_id
    assert started_activation["native_run_id"] == f"codex-agent:{receiver_id}"
    observed = bridge.handle(
        {
            **pre_payload,
            "hook_event_name": "PostToolUse",
            "tool_input": post_input,
            "tool_response": json.dumps({"task_name": f"/root/{task_name}"}),
        }
    )
    observed_context = observed["hookSpecificOutput"]["additionalContext"]
    assert observed_context.startswith("[AGENCY UPDATED HEADER SNAPSHOT v1]\n")
    assert observed_context.count("Agency/Agencies loaded:") == 1
    execution_turn = "019fa500-2222-7333-8444-555566667777"
    transcript = store.db_path.parent / f"rollout-test-{receiver_id}.jsonl"
    parent_transcript = store.db_path.parent / f"rollout-test-{session_id}.jsonl"
    parent_transcript.write_text(
        "\n".join(
            json.dumps(event)
            for event in (
                {"type": "session_meta", "payload": {"id": session_id}},
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "spawn_agent",
                        "namespace": "collaboration",
                        "call_id": tool_use_id,
                        "arguments": json.dumps(post_input),
                    },
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    execution_input = {
        "type": "agent_message",
        "id": "amsg-execution",
        "author": "/root",
        "recipient": f"/root/{task_name}",
        "internal_chat_message_metadata_passthrough": {"turn_id": execution_turn},
        "content": [
            {
                "type": "input_text",
                "text": "Message Type: NEW_TASK\n"
                f"Task name: /root/{task_name}\n"
                "Sender: /root\n"
                "Payload:\n",
            },
            {
                "type": "encrypted_content",
                "encrypted_content": encrypted_message,
            },
        ],
    }
    transcript.write_text(
        "\n".join(
            json.dumps(event)
            for event in (
                {
                    "type": "session_meta",
                    "payload": {
                        "id": receiver_id,
                        "source": {
                            "subagent": {
                                "thread_spawn": {
                                    "parent_thread_id": session_id,
                                    "agent_path": f"/root/{task_name}",
                                }
                            }
                        },
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "task_started", "turn_id": execution_turn},
                },
                {
                    "type": "response_item",
                    "payload": execution_input,
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "id": "assistant-final",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "reviewed"}],
                        "phase": "final_answer",
                        "internal_chat_message_metadata_passthrough": {"turn_id": execution_turn},
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": execution_turn,
                        "last_agent_message": "reviewed",
                        "error": None,
                    },
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    [(expected_execution, _specialist, execution_identity, _mutation_scope)] = (
        bridge._codex_execution_candidates(session_id=session_id, trace_id=trace_id)
    )
    assert (
        bridge._codex_execution_claim_observed(
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=unit,
            identity=execution_identity,
        )
        == tool_use_id
    )
    from agency_runtime.core.codex_child_execution import (
        codex_initial_turn_execution_observed,
    )

    assert codex_initial_turn_execution_observed(
        transcript,
        turn_id=execution_turn,
        worker_id=receiver_id,
        expected=expected_execution,
        parent_session_id=session_id,
        execution_tool_use_id=tool_use_id,
    )
    assert (
        bridge.handle(
            {
                "hook_event_name": "SubagentStop",
                "session_id": session_id,
                "turn_id": execution_turn,
                "agent_id": receiver_id,
                "agent_type": "worker",
                "agent_transcript_path": str(transcript),
                "last_assistant_message": "reviewed",
            }
        )
        == {}
    )
    completed_worker = store.get_native_child_run(
        host="codex",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
    )
    assert completed_worker is not None
    assert completed_worker["ended_at"]
    assert completed_worker["exit_code"] == 0
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
                "transcript_path": str(parent_transcript),
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
        "collaboration": _direct_collaboration(
            receiver_id=receiver_id,
            work_unit_id=unit,
            task_name=task_name,
            goal_hash=str(plan["goal_hash"]),
            prompt_delivery={
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
        ),
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
    activation = (
        _prepare_exact_opaque_activation(
            store,
            session_id=session_id,
            trace_id=trace_id,
            plan=plan,
            tool_use_id=persisted_tool_use_id or tool_use_id,
        )
        if hook_provenance
        else store.prepare_delegation_activation(
            session_id=session_id,
            trace_id=trace_id,
            specialist_slug=slug,
            work_unit_id=unit,
        )
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
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
    )
    assert store.claim_codex_native_child_execution(
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=unit,
        worker_id=receiver_id,
        native_run_id=f"codex-agent:{receiver_id}",
        tool_use_id=tool_use_id,
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
        "collaboration": _direct_collaboration(
            receiver_id=receiver_id,
            work_unit_id=unit,
            task_name=task_name,
            goal_hash=str(plan["goal_hash"]),
            prompt_delivery={
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
        ),
    }












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


def test_codex_direct_rollout_projects_one_spawn_and_terminal_wait(tmp_path: Path) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    receiver_id = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    tool_use_id = "call-native-spawn"
    work_unit_id = "unit-code"
    task_name = codex_task_name_for_work_unit(work_unit_id)
    goal = "Review the implementation."
    ciphertext = "gAAAAA" + "opaque-direct-spawn-message" * 2
    prompt_body = "You are the exact reviewer."
    delivery = render_codex_direct_native_child_prompt_delivery(
        prompt_body,
        parent_session_id=parent_id,
        parent_trace_id="trace",
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug="code-reviewer",
        specialist_version="v1",
        specialist_prompt_hash=response_hash(prompt_body),
        goal_hash=work_unit_goal_hash(goal),
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
                            "message": ciphertext,
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
    _write_codex_rollout(
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
            {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "run"}},
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": delivery}],
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "id": "amsg-execution",
                    "author": "/root",
                    "recipient": f"/root/{task_name}",
                    "internal_chat_message_metadata_passthrough": {"turn_id": "run"},
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Message Type: NEW_TASK\n"
                            f"Task name: /root/{task_name}\n"
                            "Sender: /root\n"
                            "Payload:\n",
                        },
                        {"type": "encrypted_content", "encrypted_content": ciphertext},
                    ],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "turn_id": "run",
                    "last_agent_message": "reviewed",
                    "error": None,
                },
            },
        ],
    )
    stdout = json.dumps({"type": "thread.started", "thread_id": parent_id})

    collaboration = codex_collaboration_evidence(stdout, rollout_root=rollout_root)

    assert collaboration is not None
    assert [row["tool"] for row in collaboration["calls"]] == ["spawn_agent", "wait"]
    assert collaboration["followup_count"] == 0
    assert collaboration["wait_count"] == 1
    spawn = collaboration["calls"][0]
    assert spawn["execution_delivery"] == {
        "work_unit_id": work_unit_id,
        "native_task_name": task_name,
        "goal_hash": work_unit_goal_hash(goal),
    }
    assert spawn["followup_tool_use_id"] == tool_use_id

    product = _codex_product_rollout_collaboration_evidence(
        stdout,
        rollout_root,
        not_before=None,
        not_after=None,
    )
    assert product["spawn_count"] == 1
    assert product["followup_count"] == 0
    assert product["wait_count"] == 1
    assert product["calls"][0]["activation_completion_count"] == 0
    assert product["calls"][0]["execution_completion_count"] == 1


def test_codex_v2_rollout_recovers_spawn_omitted_from_stdout(tmp_path: Path) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    receiver_id = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    tool_use_id = "call-native-spawn"
    task_name = codex_task_name_for_work_unit("unit-code")
    original_task = "Review the implementation."
    encrypted_parent_message = "gAAAAABopaque-parent-tool-ciphertext"
    encrypted_followup_message = "gAAAAABopaque-followup-tool-ciphertext"
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
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "id": "followup-item",
                    "name": "followup_task",
                    "namespace": "collaboration",
                    "call_id": "call-native-followup",
                    "arguments": json.dumps(
                        {
                            "target": f"/root/{task_name}",
                            "message": encrypted_followup_message,
                        }
                    ),
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "sub_agent_activity",
                    "event_id": "call-native-followup",
                    "agent_thread_id": receiver_id,
                    "agent_path": f"/root/{task_name}",
                    "kind": "interacted",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call-native-followup",
                    "output": "",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "id": "wait-execution-item",
                    "name": "wait_agent",
                    "namespace": "collaboration",
                    "call_id": "call-native-execution-wait",
                    "arguments": json.dumps({"timeout_ms": 60_000}),
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call-native-execution-wait",
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
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "activation-turn"},
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
                    "turn_id": "activation-turn",
                    "last_agent_message": "ready",
                    "error": None,
                },
            },
            {
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "execution-turn"},
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "agent_message",
                    "id": "amsg-execution",
                    "author": "/root",
                    "recipient": f"/root/{task_name}",
                    "internal_chat_message_metadata_passthrough": {"turn_id": "execution-turn"},
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Message Type: NEW_TASK\n"
                            f"Task name: /root/{task_name}\n"
                            "Sender: /root\n"
                            "Payload:\n",
                        },
                        {
                            "type": "encrypted_content",
                            "encrypted_content": encrypted_followup_message,
                        },
                    ],
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "turn_id": "execution-turn",
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
                "item": {
                    "id": "skills-notice",
                    "type": "error",
                    "message": "Skill descriptions were shortened to fit the 2% skills context "
                    "budget. Codex can still see every skill, but some descriptions are shorter. "
                    "Disable unused skills or plugins to leave more room for the rest.",
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
    assert record["session_id"] == parent_id
    collaboration = record["collaboration"]
    assert collaboration["evidence_source"] == "persisted_rollout"
    assert collaboration["spawn_count"] == 1
    assert collaboration["followup_count"] == 1
    assert collaboration["wait_count"] == 2
    assert collaboration["calls"][0]["native_task_name"] == task_name
    assert collaboration["calls"][0]["event_type"] == "rollout_call_completed"
    assert collaboration["calls"][0]["receiver_thread_ids"] == [receiver_id]
    assert collaboration["host_notice_count"] == 1
    assert collaboration["host_notice_types"] == ["skill_catalog_descriptions_shortened"]
    encoded = json.dumps(record)
    assert activation_token not in encoded
    assert prompt_body not in encoded
    assert original_task not in encoded
    assert encrypted_parent_message not in encoded
    assert encrypted_followup_message not in encoded

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


def test_codex_v2_rollout_reports_content_free_parent_spawn_failure(
    tmp_path: Path,
) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    rollout_root = tmp_path / "sessions"
    secret = "private parent reasoning that must never reach evidence"
    _write_codex_rollout(
        rollout_root,
        parent_id,
        [
            {"type": "session_meta", "payload": {"id": parent_id, "source": "exec"}},
            {
                "type": "response_item",
                "payload": {"type": "reasoning", "summary": secret},
            },
        ],
    )
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
    assert record["failure_reason"] == "codex_parent_spawn_missing"
    assert record["collaboration_diagnostic"] == {
        "schema": "agency.codex-collaboration-diagnostic.v1",
        "proven": False,
        "reason": "parent_spawn_missing",
        "parent_rollout_observed": True,
        "spawn_count": 0,
        "followup_count": 0,
        "wait_count": 0,
        "tool_output_count": 0,
        "child_start_count": 0,
        "child_interaction_count": 0,
        "agent_message_count": 0,
        "unexpected_item_count": 0,
    }
    assert secret not in json.dumps(record)


def test_codex_product_rollout_projects_exact_eight_unit_reuse_topology(
    tmp_path: Path,
) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    receiver_ids = tuple(
        f"019fa6a6-a{index:03x}-7a83-b3fb-d2c20411f6{index:02x}" for index in range(1, 9)
    )
    units = tuple(f"unit-product-{index}" for index in range(1, 9))
    specialists = (
        "codebase-onboarding-engineer",
        "python-application-engineer",
        "software-test-engineer",
        "technical-writer",
        "code-reviewer",
        "code-reviewer",
        "test-results-analyzer",
        "application-integration-verifier",
    )
    task_names = tuple(codex_task_name_for_work_unit(unit) for unit in units)
    rollout_root = tmp_path / "sessions"
    parent_events: list[dict[str, object]] = [
        {"type": "session_meta", "payload": {"id": parent_id, "source": "exec"}}
    ]
    stdout_events: list[dict[str, object]] = [{"type": "thread.started", "thread_id": parent_id}]
    secrets: list[str] = []
    for index, (receiver_id, unit, task_name, specialist) in enumerate(
        zip(receiver_ids, units, task_names, specialists, strict=True),
        start=1,
    ):
        tool_use_id = f"call-product-spawn-{index}"
        original_task = f"private product unit task {index}"
        specialist_prompt = f"private specialist prompt {index}"
        secrets.extend((original_task, specialist_prompt))
        delivery = render_codex_opaque_native_child_prompt_delivery(
            specialist_prompt,
            parent_session_id=parent_id,
            parent_trace_id="product-trace",
            tool_use_id=tool_use_id,
            work_unit_id=unit,
            specialist_slug=specialist,
            specialist_version="v1",
            specialist_prompt_hash=response_hash(specialist_prompt),
            goal_hash=work_unit_goal_hash(original_task),
        )
        encrypted_followup_message = "gAAAAA" + f"opaque-product-followup-{index}-ciphertext" * 2
        parent_events.extend(
            (
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "id": f"spawn-item-{index}",
                        "name": "spawn_agent",
                        "namespace": "collaboration",
                        "call_id": tool_use_id,
                        "arguments": json.dumps(
                            {
                                "fork_turns": "none",
                                "message": f"encrypted-parent-message-{index}",
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
                        "id": f"wait-item-{index}",
                        "name": "wait_agent",
                        "namespace": "collaboration",
                        "call_id": f"call-product-wait-{index}",
                        "arguments": json.dumps(
                            {}
                            if index == 8
                            else {"timeout_ms": 3_600_000 if index == 1 else 60_000}
                        ),
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": f"call-product-wait-{index}",
                        "output": json.dumps({"message": "Wait completed.", "timed_out": False}),
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "id": f"followup-item-{index}",
                        "name": "followup_task",
                        "namespace": "collaboration",
                        "call_id": f"call-product-followup-{index}",
                        "arguments": json.dumps(
                            {
                                "target": f"/root/{task_name}",
                                "message": encrypted_followup_message,
                            }
                        ),
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "sub_agent_activity",
                        "event_id": f"call-product-followup-{index}",
                        "agent_thread_id": receiver_id,
                        "agent_path": f"/root/{task_name}",
                        "kind": "interacted",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": f"call-product-followup-{index}",
                        "output": "",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "id": f"execution-wait-item-{index}",
                        "name": "wait_agent",
                        "namespace": "collaboration",
                        "call_id": f"call-product-execution-wait-{index}",
                        "arguments": json.dumps({"timeout_ms": 60_000}),
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": f"call-product-execution-wait-{index}",
                        "output": json.dumps({"message": "Wait completed.", "timed_out": False}),
                    },
                },
            )
        )
        if index == 1:
            parent_events.extend(
                (
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "id": f"execution-commentary-wait-item-{index}",
                            "name": "wait_agent",
                            "namespace": "collaboration",
                            "call_id": f"call-product-execution-commentary-wait-{index}",
                            "arguments": json.dumps({"timeout_ms": 120_000}),
                        },
                    },
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": f"call-product-execution-commentary-wait-{index}",
                            "output": json.dumps(
                                {"message": "Wait completed.", "timed_out": False}
                            ),
                        },
                    },
                )
            )
        stdout_events.extend(
            (
                {
                    "type": "item.started",
                    "item": {
                        "id": f"stdout-spawn-{index}",
                        "type": "collab_tool_call",
                        "tool": "spawn_agent",
                        "sender_thread_id": parent_id,
                        "receiver_thread_ids": [],
                        "prompt": f"encrypted-parent-message-{index}",
                        "agents_states": {},
                        "status": "in_progress",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "id": f"stdout-spawn-{index}",
                        "type": "collab_tool_call",
                        "tool": "spawn_agent",
                        "sender_thread_id": parent_id,
                        "receiver_thread_ids": [receiver_id],
                        "prompt": None,
                        "agents_states": {receiver_id: {"status": "running", "message": None}},
                        "status": "completed",
                    },
                },
                {
                    "type": "item.started",
                    "item": {
                        "id": f"stdout-wait-{index}",
                        "type": "collab_tool_call",
                        "tool": "wait",
                        "sender_thread_id": parent_id,
                        "receiver_thread_ids": [],
                        "prompt": None,
                        "agents_states": {},
                        "status": "in_progress",
                    },
                },
                {
                    "type": "item.completed",
                    "item": {
                        "id": f"stdout-wait-{index}",
                        "type": "collab_tool_call",
                        "tool": "wait",
                        "sender_thread_id": parent_id,
                        "receiver_thread_ids": [],
                        "prompt": None,
                        "agents_states": {},
                        "status": "completed",
                    },
                },
            )
        )
        _write_codex_rollout(
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
                    "type": "event_msg",
                    "payload": {
                        "type": "task_started",
                        "turn_id": f"activation-turn-{index}",
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
                        "turn_id": f"activation-turn-{index}",
                        "last_agent_message": "ready",
                        "error": None,
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_started",
                        "turn_id": f"execution-turn-{index}",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "agent_message",
                        "id": f"amsg-execution-{index}",
                        "author": "/root",
                        "recipient": f"/root/{task_name}",
                        "internal_chat_message_metadata_passthrough": {
                            "turn_id": f"execution-turn-{index}"
                        },
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Message Type: NEW_TASK\n"
                                f"Task name: /root/{task_name}\n"
                                "Sender: /root\n"
                                "Payload:\n",
                            },
                            {
                                "type": "encrypted_content",
                                "encrypted_content": encrypted_followup_message,
                            },
                        ],
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "id": f"child-tool-{index}",
                        "name": "shell_command",
                        "namespace": "functions",
                        "call_id": f"child-call-{index}",
                        "arguments": json.dumps({"command": f"private command {index}"}),
                        "status": "completed",
                    },
                },
                {
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": f"child-call-{index}",
                        "output": json.dumps({"output": f"private output {index}"}),
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": f"execution-turn-{index}",
                        "last_agent_message": f"private completed result {index}",
                        "error": None,
                    },
                },
            ],
        )
        secrets.extend(
            (
                f"encrypted-parent-message-{index}",
                encrypted_followup_message,
                f"private command {index}",
                f"private output {index}",
                f"private completed result {index}",
            )
        )
    _write_codex_rollout(rollout_root, parent_id, parent_events)
    stdout_events.extend(
        (
            {
                "type": "item.completed",
                "item": {
                    "id": "skills-notice",
                    "type": "error",
                    "message": "Skill descriptions were shortened to fit the 2% skills context "
                    "budget. Codex can still see every skill, but some descriptions are shorter. "
                    "Disable unused skills or plugins to leave more room for the rest.",
                },
            },
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": _valid_header()},
            },
            {"type": "turn.completed"},
        )
    )
    stdout = "\n".join(json.dumps(event) for event in stdout_events)

    record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
        rollout_contract="product",
    )

    assert record["status"] == "completed"
    collaboration = record["collaboration"]
    assert collaboration["schema"] == "agency.codex-product-collaboration.v2"
    assert collaboration["spawn_count"] == 8
    assert collaboration["followup_count"] == 8
    assert collaboration["wait_count"] == 17
    assert collaboration["completed_wait_count"] == 17
    assert collaboration["completed_child_count"] == 8
    assert collaboration["child_tool_call_count"] == 8
    assert collaboration["child_function_tool_call_count"] == 8
    assert collaboration["child_custom_tool_call_count"] == 0
    assert collaboration["child_exec_tool_call_count"] == 0
    assert collaboration["child_apply_patch_tool_call_count"] == 0
    assert collaboration["child_shell_command_tool_call_count"] == 8
    assert collaboration["child_other_tool_call_count"] == 0
    assert collaboration["child_completed_tool_call_count"] == 8
    assert collaboration["child_failed_tool_call_count"] == 0
    assert collaboration["child_unknown_tool_call_count"] == 0
    assert collaboration["child_tool_output_count"] == 8
    assert collaboration["child_tool_output_missing_count"] == 0
    assert collaboration["child_patch_apply_success_count"] == 0
    assert collaboration["child_patch_apply_failure_count"] == 0
    assert collaboration["child_patch_apply_unknown_count"] == 0
    assert all(row["tool_evidence"]["child_tool_call_count"] == 1 for row in collaboration["calls"])
    assert collaboration["host_notice_count"] == 1
    assert collaboration["host_notice_types"] == ["skill_catalog_descriptions_shortened"]
    assert [row["prompt_delivery"]["work_unit_id"] for row in collaboration["calls"]] == [*units]
    assert {row["prompt_delivery"]["specialist_slug"] for row in collaboration["calls"]} == set(
        specialists
    )
    encoded = json.dumps(record)
    assert all(secret not in encoded for secret in secrets)


@pytest.mark.parametrize("timeout_ms", [0, True, 3_600_001])
def test_codex_product_wait_timeout_stays_bounded(timeout_ms: object) -> None:
    with pytest.raises(ValueError, match="wait arguments exceeded the bounded contract"):
        _codex_product_wait_counts(
            [
                {
                    "arguments": {"timeout_ms": timeout_ms},
                    "call_id": "product-wait",
                    "index": 2,
                }
            ],
            outputs={
                "product-wait": {
                    "message": "Wait completed.",
                    "timed_out": False,
                }
            },
            last_spawn_index=1,
        )


def test_codex_product_wait_rejects_unknown_arguments() -> None:
    with pytest.raises(ValueError, match="wait arguments exceeded the bounded contract"):
        _codex_product_wait_counts(
            [
                {
                    "arguments": {"timeout_ms": 60_000, "targets": []},
                    "call_id": "product-wait",
                    "index": 2,
                }
            ],
            outputs={
                "product-wait": {
                    "message": "Wait completed.",
                    "timed_out": False,
                }
            },
            last_spawn_index=1,
        )


def test_codex_product_rollout_preserves_first_content_free_topology_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
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
                    "call_id": "spawn-call",
                    "arguments": "{}",
                },
            },
            {
                "type": "event_msg",
                "payload": {
                    "type": "sub_agent_activity",
                    "event_id": "spawn-call",
                    "agent_thread_id": "019fa6a6-a001-7a83-b3fb-d2c20411f601",
                    "agent_path": "/root/unit_product_1",
                    "kind": "started",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "spawn-call",
                    "output": "{}",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "id": "wait-item",
                    "name": "wait_agent",
                    "namespace": "collaboration",
                    "call_id": "wait-call",
                    "arguments": "{}",
                },
            },
            {
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "wait-call",
                    "output": "{}",
                },
            },
        ],
    )
    monkeypatch.setattr(
        "agency_runtime.core.canary_backends._codex_product_rollout_collaboration_evidence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("Codex product spawn output did not match its native task")
        ),
    )
    stdout = "\n".join(
        (
            json.dumps({"type": "thread.started", "thread_id": parent_id}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": _valid_header()},
                }
            ),
            json.dumps({"type": "turn.completed"}),
        )
    )

    record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
        rollout_contract="product",
    )

    assert record["status"] == "failed"
    assert record["collaboration_diagnostic"]["reason"] == "product_spawn_output_invalid"
    assert record["collaboration_diagnostic"]["spawn_count"] == 1
    assert record["collaboration_diagnostic"]["wait_count"] == 1
    assert "Codex product spawn output" not in json.dumps(record)


def test_codex_product_rollout_does_not_mask_a_baseline_topology_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    rollout_root = tmp_path / "sessions"
    _write_codex_rollout(
        rollout_root,
        parent_id,
        [{"type": "session_meta", "payload": {"id": parent_id, "source": "exec"}}],
    )
    monkeypatch.setattr(
        "agency_runtime.core.canary_backends._codex_product_rollout_collaboration_evidence",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("Codex product spawn output did not match its native task")
        ),
    )
    stdout = "\n".join(
        (
            json.dumps({"type": "thread.started", "thread_id": parent_id}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": _valid_header()},
                }
            ),
            json.dumps({"type": "turn.completed"}),
        )
    )

    record = codex_canary_record(
        _process_result(stdout),
        profile_scope="current-profile",
        rollout_root=rollout_root,
        rollout_contract="product",
    )

    assert record["status"] == "failed"
    assert record["collaboration_diagnostic"]["reason"] == "parent_spawn_missing"


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


def test_codex_jsonl_parser_classifies_only_exact_allowlisted_host_notices() -> None:
    trust_notice = {
        "type": "item.completed",
        "item": {
            "id": "trust-notice",
            "type": "error",
            "message": "`--dangerously-bypass-hook-trust` is enabled. Enabled hooks may run "
            "without review for this invocation.",
        },
    }
    skill_catalog_notice = {
        "type": "item.completed",
        "item": {
            "id": "skills-notice",
            "type": "error",
            "message": "Skill descriptions were shortened to fit the skills context budget. "
            "Codex can still see every skill, but some descriptions are shorter. Disable unused "
            "skills or plugins to leave more room for the rest.",
        },
    }
    skill_catalog_percent_notice = {
        "type": "item.completed",
        "item": {
            "id": "skills-percent-notice",
            "type": "error",
            "message": "Skill descriptions were shortened to fit the 2% skills context budget. "
            "Codex can still see every skill, but some descriptions are shorter. Disable unused "
            "skills or plugins to leave more room for the rest.",
        },
    }
    near_miss = {
        "type": "item.completed",
        "item": {
            "id": "other-error",
            "type": "error",
            "message": skill_catalog_notice["item"]["message"] + " ",
        },
    }

    accepted = codex_collaboration_evidence(
        "\n".join(
            map(json.dumps, (trust_notice, skill_catalog_notice, skill_catalog_percent_notice))
        )
    )
    rejected = codex_collaboration_evidence(
        "\n".join(
            map(
                json.dumps,
                (trust_notice, skill_catalog_notice, skill_catalog_percent_notice, near_miss),
            )
        )
    )

    assert accepted is not None
    assert accepted["unexpected_item_count"] == 0
    assert accepted["host_notice_count"] == 3
    assert accepted["host_notice_types"] == [
        "hook_trust_bypass",
        "skill_catalog_descriptions_shortened",
    ]
    assert rejected is not None
    assert rejected["unexpected_item_count"] == 1
    assert rejected["unexpected_item_types"] == ["error"]
    assert rejected["host_notice_count"] == 3
    assert rejected["host_notice_types"] == accepted["host_notice_types"]
    assert skill_catalog_notice["item"]["message"] not in json.dumps(accepted)
    assert skill_catalog_percent_notice["item"]["message"] not in json.dumps(accepted)
    assert near_miss["item"]["message"] not in json.dumps(rejected)


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


def test_codex_canary_projects_only_allowlisted_hook_event_diagnostics() -> None:
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
        "\r\n".join(
            (
                "unrelated stderr",
                "agency_hook_diagnostic codex_hook_event=UserPromptSubmit stage=accepted",
                "agency_hook_diagnostic codex_hook_event=UserPromptSubmit stage=completed",
                "agency_hook_diagnostic codex_hook_event=PreToolUse stage=accepted",
                "agency_hook_diagnostic codex_hook_event=PreToolUse stage=failed",
                "agency_hook_diagnostic codex_hook_event=UnknownEvent stage=accepted",
                "agency_hook_diagnostic codex_hook_event=Stop stage=arbitrary",
            )
        )
        + "\r\n"
    )

    record = codex_canary_record(_process_result(stdout, stderr=stderr))

    assert record["hook_events"] == {
        "UserPromptSubmit": {"accepted": 1, "completed": 1, "failed": 0},
        "PreToolUse": {"accepted": 1, "completed": 0, "failed": 1},
    }
    assert "unrelated stderr" not in json.dumps(record)
    assert "UnknownEvent" not in json.dumps(record)


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
        proof_contract="agency.codex-activation-canary.v2",
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
