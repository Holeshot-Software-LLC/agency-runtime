"""Causal Codex child execution-envelope projection tests."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core.codex_child_execution import (
    codex_current_turn_execution_observed,
)
from agency_runtime.core.native_child_prompt_delivery import (
    parse_codex_native_child_execution_message,
    render_codex_native_child_execution_message,
)
from agency_runtime.core.unit_assignment import work_unit_goal_hash


def _rollout(path: Path, *, worker: str, turn: str, message: str) -> None:
    events = [
        {
            "type": "session_meta",
            "payload": {
                "id": worker,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": "parent",
                            "agent_path": "/root/unit_1234567890",
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
            "payload": {"type": "message", "content": "activation only"},
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "activation-turn"},
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "developer",
                "content": [{"type": "input_text", "text": json.dumps({"content": message})}],
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": turn},
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": turn},
        },
    ]
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def _opaque_rollouts(
    child_path: Path,
    parent_path: Path,
    *,
    worker: str,
    parent: str,
    turn: str,
    tool_use_id: str,
    ciphertext: str,
) -> None:
    task_name = "unit_1234567890"
    parent_events = [
        {"type": "session_meta", "payload": {"id": parent}},
        {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "followup_task",
                "namespace": "collaboration",
                "call_id": tool_use_id,
                "arguments": json.dumps({"target": f"/root/{task_name}", "message": ciphertext}),
            },
        },
    ]
    child_events = [
        {
            "type": "session_meta",
            "payload": {
                "id": worker,
                "source": {
                    "subagent": {
                        "thread_spawn": {
                            "parent_thread_id": parent,
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
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "activation-turn"},
        },
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn}},
        {
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "id": "amsg-execution",
                "author": "/root",
                "recipient": f"/root/{task_name}",
                "internal_chat_message_metadata_passthrough": {"turn_id": turn},
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
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn}},
    ]
    parent_path.write_text(
        "\n".join(json.dumps(event) for event in parent_events) + "\n",
        encoding="utf-8",
    )
    child_path.write_text(
        "\n".join(json.dumps(event) for event in child_events) + "\n",
        encoding="utf-8",
    )


def test_current_turn_requires_exact_execution_envelope(tmp_path: Path) -> None:
    worker = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    turn = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Implement the unit."),
    )
    expected = parse_codex_native_child_execution_message(message)
    assert expected is not None
    path = tmp_path / f"rollout-test-{worker}.jsonl"
    _rollout(path, worker=worker, turn=turn, message=message)

    assert codex_current_turn_execution_observed(
        path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
    )
    assert not codex_current_turn_execution_observed(
        path,
        turn_id="activation-turn",
        worker_id=worker,
        expected=expected,
    )


def test_execution_projection_rejects_wrong_identity_or_tampering(tmp_path: Path) -> None:
    worker = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    turn = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Implement the unit."),
    )
    expected = parse_codex_native_child_execution_message(message)
    assert expected is not None
    path = tmp_path / f"rollout-test-{worker}.jsonl"
    _rollout(path, worker=worker, turn=turn, message=message.replace("evidence-backed", "wrong"))

    assert not codex_current_turn_execution_observed(
        path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
    )

    assert not codex_current_turn_execution_observed(
        path,
        turn_id=turn,
        worker_id="different-worker",
        expected=expected,
    )


def test_execution_projection_rejects_duplicate_or_single_turn_evidence(
    tmp_path: Path,
) -> None:
    worker = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    turn = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Implement the unit."),
    )
    expected = parse_codex_native_child_execution_message(message)
    assert expected is not None
    path = tmp_path / f"rollout-test-{worker}.jsonl"
    _rollout(path, worker=worker, turn=turn, message=message)
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    events.insert(5, events[4])
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )

    assert not codex_current_turn_execution_observed(
        path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
    )

    single_turn = [
        {"type": "session_meta", "payload": {"id": worker}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": turn}},
        {"type": "response_item", "payload": {"content": message}},
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": turn}},
    ]
    path.write_text(
        "\n".join(json.dumps(event) for event in single_turn) + "\n",
        encoding="utf-8",
    )
    assert not codex_current_turn_execution_observed(
        path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
    )


def test_current_turn_matches_exact_parent_and_child_ciphertext(tmp_path: Path) -> None:
    worker = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    parent = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    turn = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    tool_use_id = "call-native-followup"
    ciphertext = "gAAAAA" + "opaque-followup-ciphertext" * 2
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Implement the unit."),
    )
    expected = parse_codex_native_child_execution_message(message)
    assert expected is not None
    child_path = tmp_path / f"rollout-test-{worker}.jsonl"
    parent_path = tmp_path / f"rollout-test-{parent}.jsonl"
    _opaque_rollouts(
        child_path,
        parent_path,
        worker=worker,
        parent=parent,
        turn=turn,
        tool_use_id=tool_use_id,
        ciphertext=ciphertext,
    )

    assert codex_current_turn_execution_observed(
        child_path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
        parent_session_id=parent,
        execution_tool_use_id=tool_use_id,
    )
    assert not codex_current_turn_execution_observed(
        child_path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
        parent_session_id=parent,
        execution_tool_use_id="different-followup",
    )

    parent_text = parent_path.read_text(encoding="utf-8")
    parent_events = [json.loads(line) for line in parent_text.splitlines()]
    parent_events[0]["payload"]["id"] = "different-parent"
    parent_path.write_text(
        "\n".join(json.dumps(event) for event in parent_events) + "\n",
        encoding="utf-8",
    )
    assert not codex_current_turn_execution_observed(
        child_path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
        parent_session_id=parent,
        execution_tool_use_id=tool_use_id,
    )
    parent_path.write_text(parent_text, encoding="utf-8")

    child_text = child_path.read_text(encoding="utf-8")
    child_path.write_text(
        child_text.replace(ciphertext, "gAAAAA" + "different-ciphertext" * 2),
        encoding="utf-8",
    )
    assert not codex_current_turn_execution_observed(
        child_path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
        parent_session_id=parent,
        execution_tool_use_id=tool_use_id,
    )
    child_path.write_text(child_text, encoding="utf-8")
    child_events = [
        json.loads(line) for line in child_path.read_text(encoding="utf-8").splitlines()
    ]
    child_events[0]["payload"]["source"]["subagent"]["thread_spawn"]["parent_thread_id"] = (
        "different-parent"
    )
    child_path.write_text(
        "\n".join(json.dumps(event) for event in child_events) + "\n",
        encoding="utf-8",
    )
    assert not codex_current_turn_execution_observed(
        child_path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
        parent_session_id=parent,
        execution_tool_use_id=tool_use_id,
    )


def test_parent_ciphertext_resolves_across_midnight_rollover(tmp_path: Path) -> None:
    worker = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    parent = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    turn = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    tool_use_id = "call-native-followup"
    ciphertext = "gAAAAA" + "opaque-followup-ciphertext" * 2
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-1234567890",
        goal_hash=work_unit_goal_hash("Implement the unit."),
    )
    expected = parse_codex_native_child_execution_message(message)
    assert expected is not None
    child_directory = tmp_path / "sessions" / "2026" / "08" / "02"
    parent_directory = tmp_path / "sessions" / "2026" / "08" / "01"
    child_directory.mkdir(parents=True)
    parent_directory.mkdir(parents=True)
    child_path = child_directory / f"rollout-test-{worker}.jsonl"
    parent_path = parent_directory / f"rollout-test-{parent}.jsonl"
    _opaque_rollouts(
        child_path,
        parent_path,
        worker=worker,
        parent=parent,
        turn=turn,
        tool_use_id=tool_use_id,
        ciphertext=ciphertext,
    )

    assert codex_current_turn_execution_observed(
        child_path,
        turn_id=turn,
        worker_id=worker,
        expected=expected,
        parent_session_id=parent,
        execution_tool_use_id=tool_use_id,
    )
