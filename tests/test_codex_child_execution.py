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
