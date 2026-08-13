"""Adversarial tests for Codex plaintext spawn transcript provenance."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import codex_spawn_provenance as subject

_SESSION = "019ff8ee-eb1c-7de3-815d-3deea9eca028"
_CHILD_THREAD = "019ff956-4849-7453-9174-8c5143ff5d29"
_DEPTH_TWO_PARENT = "019ff927-9be7-7073-88bc-e5857ce841f4"
_GRANDCHILD_THREAD = "019ff928-4178-7421-86f6-d391c6316d98"
_EXEC_SESSION = "019ff1e8-e0fe-7fe0-b8ba-57de219228c6"
_EXEC_CHILD = "019ff1e9-defe-77c2-8bd1-9d503f1670b6"
_TURN = "019ff8ef-c6e1-7961-a682-d8aa9f11f464"
_V4_TURN = "550e8400-e29b-41d4-a716-446655440000"
_CALL = "call_4fLyxjPXggCL0L9VWsSXDWr3"
_FUNCTION_ITEM = "fc_" + "a" * 50
_ARGS = {
    "task_name": "security_review",
    "message": "Review the exact transaction boundary.",
    "fork_turns": "all",
}
_MISSING = object()

_DESKTOP_ROOT = "019ff5e8-e866-7f60-9720-c10a0753ca6f"
_DESKTOP_PARENT = "019ff5e9-e999-7293-87c0-80a1784f816a"
_DESKTOP_CHILD = "019ff653-7840-76b1-91a0-3fce88331fe4"
_DESKTOP_TURN = "019ff632-eb5c-75d0-9830-bec5247e0a5a"
_DESKTOP_CALL = "call_DesktopMarkedSpawn000001"
_DESKTOP_FUNCTION_ITEM = "fc_" + "9" * 50
_DESKTOP_CONTEXT_WINDOWS = {
    _DESKTOP_ROOT: "019ff5e8-e866-7f60-9720-c11d05b613e5",
    _DESKTOP_PARENT: "019ff5e9-e999-7293-87c0-80b192433582",
    _DESKTOP_CHILD: "019ff653-7840-76b1-91a0-3fd88aa72cdd",
}
_DESKTOP_ARGS = {
    "task_name": "desktop_review",
    "message": "Review the sanitized Desktop boundary.",
    "fork_turns": "all",
}
_DESKTOP_DYNAMIC_TOOLS = [
    {
        "type": "namespace",
        "name": "codex_app",
        "description": "Sanitized Desktop tools.",
        "tools": [
            {
                "type": "function",
                "name": "sanitized_tool",
                "description": "Synthetic observed-shape tool.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "deferLoading": True,
            }
        ],
    },
    {
        "type": "namespace",
        "name": "plugin_management",
        "description": "Sanitized plugin tools.",
        "tools": [],
    },
]
_DESKTOP_DYNAMIC_TOOLS_SHA256 = "d1060035f3e4bf53e8af0940ad8723e794921afa3b2f026eb02c0135f6115f90"


def _real_record(
    kind: str,
    payload: dict[str, Any],
    *,
    ordinal: int,
    timestamp: str,
) -> dict[str, Any]:
    return {"timestamp": timestamp, "type": kind, "payload": payload, "ordinal": ordinal}


def _real_metadata_common(
    *,
    thread_id: str,
    timestamp: str,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "cwd": "C:\\sanitized\\agency-runtime",
        "originator": "codex-tui",
        "cli_version": "0.147.0",
        "thread_source": "subagent",
        "model_provider": "openai",
        "base_instructions": {"text": "sanitized Codex 0.147 instructions"},
        "history_mode": "paginated",
        "context_window": {"window_id": thread_id},
        "git": {
            "branch": "codex/sanitized",
            "commit_hash": "a" * 40,
            "repository_url": "https://example.invalid/agency-runtime",
        },
    }


def _real_root_metadata(
    *,
    session_id: str = _SESSION,
    ordinal: int = 0,
    outer_timestamp: str | None = None,
) -> dict[str, Any]:
    timestamp = "2026-08-13T02:23:55.164Z"
    return _real_record(
        "session_meta",
        {
            "session_id": session_id,
            "id": session_id,
            **_real_metadata_common(thread_id=session_id, timestamp=timestamp),
            "source": "cli",
            "thread_source": "user",
        },
        ordinal=ordinal,
        timestamp=outer_timestamp or timestamp,
    )


def _real_subagent_metadata(
    *,
    thread_id: str,
    parent_thread_id: str,
    root_session_id: str,
    depth: int,
    agent_path: str,
    inherited: bool,
) -> dict[str, Any]:
    timestamp = {
        _CHILD_THREAD: "2026-08-13T04:16:49.225Z",
        _DEPTH_TWO_PARENT: "2026-08-13T03:25:50.439Z",
        _GRANDCHILD_THREAD: "2026-08-13T03:26:32.824Z",
    }[thread_id]
    payload = {
        "session_id": root_session_id,
        "id": thread_id,
        **_real_metadata_common(thread_id=thread_id, timestamp=timestamp),
        "parent_thread_id": parent_thread_id,
        "source": {
            "subagent": {
                "thread_spawn": {
                    "parent_thread_id": parent_thread_id,
                    "depth": depth,
                    "agent_path": agent_path,
                    "agent_nickname": "Goodall",
                    "agent_role": None,
                }
            }
        },
        "agent_nickname": "Goodall",
        "agent_path": agent_path,
        "multi_agent_version": "v2",
    }
    if inherited:
        payload["forked_from_id"] = parent_thread_id
        payload["subagent_history_start_ordinal"] = 27
    return _real_record("session_meta", payload, ordinal=0, timestamp=timestamp)


def _causal_edge(
    *,
    parent_thread_id: str,
    child_thread_id: str,
    task_name: str,
    child_agent_path: str,
    fork_turns: str,
    ordinal: int,
    call_id: str,
    function_item_character: str,
    call_timestamp: str,
    start_timestamp: str,
) -> list[dict[str, Any]]:
    turn_id = _TURN if parent_thread_id == _SESSION else _V4_TURN
    started_at_ms = int(
        datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        .replace(tzinfo=timezone.utc)
        .timestamp()
        * 1000
    )
    return [
        _real_record(
            "response_item",
            {
                "type": "function_call",
                "namespace": "collaboration",
                "name": "spawn_agent",
                "arguments": json.dumps(
                    {
                        "task_name": task_name,
                        "message": "Sanitized bounded child task.",
                        "fork_turns": fork_turns,
                    },
                    separators=(",", ":"),
                ),
                "call_id": call_id,
                "id": "fc_" + function_item_character * 50,
                "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
            },
            ordinal=ordinal,
            timestamp=call_timestamp,
        ),
        _real_record(
            "event_msg",
            {
                "type": "item_completed",
                "thread_id": parent_thread_id,
                "turn_id": turn_id,
                "item": {
                    "type": "SubAgentActivity",
                    "id": call_id,
                    "kind": "started",
                    "agent_thread_id": child_thread_id,
                    "agent_path": child_agent_path,
                },
                "started_at_ms": started_at_ms,
                "completed_at_ms": started_at_ms,
            },
            ordinal=ordinal + 1,
            timestamp=start_timestamp,
        ),
    ]


def _cross_file_paths(
    home: Path,
    *,
    depth: int,
) -> tuple[Path, Path, Path | None]:
    sessions = home / "sessions"
    root = sessions / "2026" / "08" / "12" / f"rollout-2026-08-12T22-23-55-{_SESSION}.jsonl"
    if depth == 1:
        current = (
            sessions / "2026" / "08" / "13" / f"rollout-2026-08-13T00-16-49-{_CHILD_THREAD}.jsonl"
        )
        return current, root, None
    current = (
        sessions / "2026" / "08" / "12" / f"rollout-2026-08-12T23-26-32-{_GRANDCHILD_THREAD}.jsonl"
    )
    parent = (
        sessions / "2026" / "08" / "12" / f"rollout-2026-08-12T23-25-50-{_DEPTH_TWO_PARENT}.jsonl"
    )
    return current, root, parent


def _write_cross_file_chain(
    home: Path,
    *,
    depth: int,
    inherited: bool,
) -> tuple[Path, Path, Path | None]:
    current, root, parent = _cross_file_paths(home, depth=depth)
    current_thread = _CHILD_THREAD if depth == 1 else _GRANDCHILD_THREAD
    current_parent = _SESSION if depth == 1 else _DEPTH_TWO_PARENT
    current_task = "depth_one_child" if depth == 1 else "depth_two_child"
    parent_task = "depth_one_parent"
    current.parent.mkdir(parents=True, exist_ok=True)
    root.parent.mkdir(parents=True, exist_ok=True)
    current_agent_path = (
        f"/root/{current_task}" if depth == 1 else f"/root/{parent_task}/{current_task}"
    )
    current_records = [
        _real_subagent_metadata(
            thread_id=current_thread,
            parent_thread_id=current_parent,
            root_session_id=_SESSION,
            depth=depth,
            agent_path=current_agent_path,
            inherited=inherited,
        ),
        *_records(marker=[])[1:],
    ]
    root_records = [_real_root_metadata()]
    if depth == 1:
        root_records.extend(
            _causal_edge(
                parent_thread_id=_SESSION,
                child_thread_id=current_thread,
                task_name=current_task,
                child_agent_path=current_agent_path,
                fork_turns="2" if inherited else "none",
                ordinal=10,
                call_id="call_DepthOneChild12345678901",
                function_item_character="b",
                call_timestamp="2026-08-13T04:16:49.100Z",
                start_timestamp="2026-08-13T04:16:49.225Z",
            )
        )
    else:
        root_records.extend(
            _causal_edge(
                parent_thread_id=_SESSION,
                child_thread_id=_DEPTH_TWO_PARENT,
                task_name=parent_task,
                child_agent_path=f"/root/{parent_task}",
                fork_turns="all",
                ordinal=10,
                call_id="call_DepthOneParent1234567890",
                function_item_character="c",
                call_timestamp="2026-08-13T03:25:50.100Z",
                start_timestamp="2026-08-13T03:25:50.439Z",
            )
        )
        assert parent is not None
        copied_root = _real_root_metadata(
            ordinal=1,
            outer_timestamp="2026-08-13T03:25:50.439Z",
        )
        parent_records = [
            _real_subagent_metadata(
                thread_id=_DEPTH_TWO_PARENT,
                parent_thread_id=_SESSION,
                root_session_id=_SESSION,
                depth=1,
                agent_path=f"/root/{parent_task}",
                inherited=True,
            ),
            copied_root,
            *_causal_edge(
                parent_thread_id=_DEPTH_TWO_PARENT,
                child_thread_id=current_thread,
                task_name=current_task,
                child_agent_path=current_agent_path,
                fork_turns="3" if inherited else "none",
                ordinal=10,
                call_id="call_DepthTwoChild12345678901",
                function_item_character="d",
                call_timestamp="2026-08-13T03:26:32.700Z",
                start_timestamp="2026-08-13T03:26:32.824Z",
            ),
        ]
        _write(parent, parent_records)
    _write(root, root_records)
    _write(current, current_records)
    return current, root, parent


def _desktop_record(
    kind: str,
    payload: dict[str, Any],
    *,
    timestamp: str,
) -> dict[str, Any]:
    return {"timestamp": timestamp, "type": kind, "payload": payload}


def _desktop_git(variant: str) -> dict[str, Any]:
    git: dict[str, Any] = {
        "commit_hash": "b" * 40,
        "repository_url": "https://example.invalid/sanitized.git",
    }
    if variant == "branch":
        git["branch"] = "codex/sanitized"
    return git


def _desktop_metadata_common(
    *,
    thread_id: str,
    timestamp: str,
    git_variant: str,
    dynamic_tools: object = _MISSING,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "timestamp": timestamp,
        "cwd": "C:\\sanitized\\agency-runtime",
        "originator": "Codex Desktop",
        "cli_version": "0.147.0-alpha.6.6",
        "model_provider": "openai",
        "base_instructions": {"text": "sanitized Desktop instructions"},
        "history_mode": "legacy",
        "context_window": {"window_id": _DESKTOP_CONTEXT_WINDOWS[thread_id]},
        "git": _desktop_git(git_variant),
    }
    if dynamic_tools is not _MISSING:
        payload["dynamic_tools"] = deepcopy(dynamic_tools)
    return payload


def _desktop_root_metadata(
    *,
    git_variant: str = "branch",
    outer_timestamp: str = "2026-08-12T12:18:37.445Z",
) -> dict[str, Any]:
    payload = {
        "session_id": _DESKTOP_ROOT,
        "id": _DESKTOP_ROOT,
        **_desktop_metadata_common(
            thread_id=_DESKTOP_ROOT,
            timestamp="2026-08-12T12:18:29.766Z",
            git_variant=git_variant,
            dynamic_tools=_DESKTOP_DYNAMIC_TOOLS,
        ),
        "source": "vscode",
        "thread_source": "user",
    }
    return _desktop_record("session_meta", payload, timestamp=outer_timestamp)


def _desktop_subagent_metadata(
    *,
    thread_id: str,
    parent_thread_id: str,
    depth: int,
    agent_path: str,
    inherited: bool,
    dynamic_tools: bool,
    git_variant: str = "branch",
    outer_timestamp: str | None = None,
) -> dict[str, Any]:
    timestamp = {
        _DESKTOP_PARENT: "2026-08-12T12:19:35.653Z",
        _DESKTOP_CHILD: "2026-08-12T14:14:53.361Z",
    }[thread_id]
    payload = {
        "session_id": _DESKTOP_ROOT,
        "id": thread_id,
        **_desktop_metadata_common(
            thread_id=thread_id,
            timestamp=timestamp,
            git_variant=git_variant,
            dynamic_tools=_DESKTOP_DYNAMIC_TOOLS if dynamic_tools else _MISSING,
        ),
        "parent_thread_id": parent_thread_id,
        "source": {
            "subagent": {
                "thread_spawn": {
                    "parent_thread_id": parent_thread_id,
                    "depth": depth,
                    "agent_path": agent_path,
                    "agent_nickname": "Curie",
                    "agent_role": None,
                }
            }
        },
        "thread_source": "subagent",
        "agent_nickname": "Curie",
        "agent_path": agent_path,
        "multi_agent_version": "v2",
    }
    if inherited:
        payload["forked_from_id"] = parent_thread_id
    return _desktop_record(
        "session_meta",
        payload,
        timestamp=outer_timestamp
        or (
            "2026-08-12T12:19:40.733Z"
            if thread_id == _DESKTOP_PARENT
            else "2026-08-12T14:14:58.070Z"
        ),
    )


def _desktop_causal_pair(
    *,
    child_thread_id: str,
    child_agent_path: str,
    fork_turns: str,
    call_id: str,
    function_item_character: str,
    call_timestamp: str,
    event_timestamp: str,
    event_outer_residual_ms: int = 0,
    marker: object = _MISSING,
) -> list[dict[str, Any]]:
    call: dict[str, Any] = {
        "type": "function_call",
        "id": "fc_" + function_item_character * 50,
        "name": "spawn_agent",
        "namespace": "collaboration",
        "arguments": json.dumps(
            {
                "task_name": child_agent_path.rsplit("/", 1)[-1],
                "fork_turns": fork_turns,
                "message": "Sanitized bounded Desktop child task.",
            },
            separators=(",", ":"),
        ),
        "call_id": call_id,
        "internal_chat_message_metadata_passthrough": {"turn_id": _DESKTOP_TURN},
    }
    if marker is not _MISSING:
        call["encrypted_function_args"] = marker
    event_datetime = datetime.strptime(event_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=timezone.utc
    )
    occurred_at_ms = int(event_datetime.timestamp() * 1000)
    event_outer_timestamp = (
        event_datetime + timedelta(milliseconds=event_outer_residual_ms)
    ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if function_item_character == "7":
        output_id = "fco_019ff5e9-fe74-7c61-b81a-3413fa2cb44b"
        output_timestamp = "2026-08-12T12:19:40.789Z"
    else:
        output_id = "fco_019ff653-8b5a-78f1-ba7f-7660fcc370ad"
        output_timestamp = "2026-08-12T14:14:58.138Z"
    return [
        _desktop_record("response_item", call, timestamp=call_timestamp),
        _desktop_record(
            "event_msg",
            {
                "type": "sub_agent_activity",
                "event_id": call_id,
                "occurred_at_ms": occurred_at_ms,
                "agent_thread_id": child_thread_id,
                "agent_path": child_agent_path,
                "kind": "started",
            },
            timestamp=event_outer_timestamp,
        ),
        _desktop_record(
            "response_item",
            {
                "type": "function_call_output",
                "id": output_id,
                "call_id": call_id,
                "output": json.dumps(
                    {"task_name": child_agent_path},
                    separators=(",", ":"),
                ),
                "internal_chat_message_metadata_passthrough": {"turn_id": _DESKTOP_TURN},
            },
            timestamp=output_timestamp,
        ),
    ]


def _desktop_current_records(
    *,
    marker: object = [],
    args: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    call: dict[str, Any] = {
        "type": "function_call",
        "id": _DESKTOP_FUNCTION_ITEM,
        "name": "spawn_agent",
        "namespace": "collaboration",
        "arguments": json.dumps(args or _DESKTOP_ARGS, separators=(",", ":")),
        "call_id": _DESKTOP_CALL,
        "internal_chat_message_metadata_passthrough": {"turn_id": _DESKTOP_TURN},
    }
    if marker is not _MISSING:
        call["encrypted_function_args"] = marker
    return [
        _desktop_record(
            "event_msg",
            {
                "type": "task_started",
                "turn_id": _DESKTOP_TURN,
                "started_at": 1786544098,
                "model_context_window": 258400,
                "collaboration_mode_kind": "default",
            },
            timestamp="2026-08-12T14:14:58.070Z",
        ),
        _desktop_record(
            "response_item",
            call,
            timestamp="2026-08-12T14:15:00.000Z",
        ),
    ]


def _desktop_rollout_path(
    home: Path,
    *,
    thread_id: str,
    residual_seconds: int = 0,
) -> Path:
    local_timestamp = {
        _DESKTOP_ROOT: datetime(2026, 8, 12, 8, 18, 29),
        _DESKTOP_PARENT: datetime(2026, 8, 12, 8, 19, 35),
        _DESKTOP_CHILD: datetime(2026, 8, 12, 10, 14, 53),
    }[thread_id] + timedelta(seconds=residual_seconds)
    return (
        home
        / "sessions"
        / local_timestamp.strftime("%Y")
        / local_timestamp.strftime("%m")
        / local_timestamp.strftime("%d")
        / f"rollout-{local_timestamp.strftime('%Y-%m-%dT%H-%M-%S')}-{thread_id}.jsonl"
    )


def _desktop_copied_metadata(record: dict[str, Any], *, timestamp: str) -> dict[str, Any]:
    copied = deepcopy(record)
    copied["timestamp"] = timestamp
    return copied


def _write_desktop_chain(
    home: Path,
    *,
    depth: int,
    inherited: bool,
    prefix_variant: str,
    dynamic_tools: bool | None = None,
    git_variant: str = "branch",
    fork_turns: str | None = None,
    current_marker: object = [],
    root_marker: object = _MISSING,
    parent_marker: object = _MISSING,
    current_residual_seconds: int = 0,
    root_event_outer_residual_ms: int = 0,
    parent_event_outer_residual_ms: int = 0,
    parent_inherited: bool = True,
) -> tuple[Path, Path, Path | None]:
    current_dynamic_tools = (
        dynamic_tools
        if dynamic_tools is not None
        else not (depth == 2 and prefix_variant == "child-only")
    )
    current_fork_turns = fork_turns
    if current_fork_turns is None:
        if not inherited:
            current_fork_turns = "none"
        elif depth == 1:
            current_fork_turns = "all" if prefix_variant == "full" else "2"
        else:
            current_fork_turns = "2" if prefix_variant == "child-only" else "all"
    root_path = _desktop_rollout_path(home, thread_id=_DESKTOP_ROOT)
    parent_path = _desktop_rollout_path(home, thread_id=_DESKTOP_PARENT)
    current_thread = _DESKTOP_PARENT if depth == 1 else _DESKTOP_CHILD
    current_path = _desktop_rollout_path(
        home,
        thread_id=current_thread,
        residual_seconds=current_residual_seconds,
    )
    current_agent_path = (
        "/root/desktop_parent" if depth == 1 else "/root/desktop_parent/desktop_child"
    )
    current_metadata = _desktop_subagent_metadata(
        thread_id=current_thread,
        parent_thread_id=_DESKTOP_ROOT if depth == 1 else _DESKTOP_PARENT,
        depth=depth,
        agent_path=current_agent_path,
        inherited=inherited,
        dynamic_tools=current_dynamic_tools,
        git_variant=git_variant,
    )
    root_metadata = _desktop_root_metadata(git_variant=git_variant)
    root_records = [
        root_metadata,
        *_desktop_causal_pair(
            child_thread_id=_DESKTOP_PARENT,
            child_agent_path="/root/desktop_parent",
            fork_turns=(
                current_fork_turns if depth == 1 else ("all" if parent_inherited else "none")
            ),
            call_id="call_DesktopRootEdge000000001",
            function_item_character="7",
            call_timestamp="2026-08-12T12:19:35.403Z",
            event_timestamp="2026-08-12T12:19:40.765Z",
            event_outer_residual_ms=root_event_outer_residual_ms,
            marker=root_marker,
        ),
    ]
    current_prefix = [current_metadata]
    parent_metadata: dict[str, Any] | None = None
    if depth == 1:
        if prefix_variant == "full":
            current_prefix.append(
                _desktop_copied_metadata(
                    root_metadata,
                    timestamp="2026-08-12T12:19:40.734Z",
                )
            )
    else:
        parent_metadata = _desktop_subagent_metadata(
            thread_id=_DESKTOP_PARENT,
            parent_thread_id=_DESKTOP_ROOT,
            depth=1,
            agent_path="/root/desktop_parent",
            inherited=parent_inherited,
            dynamic_tools=True,
            git_variant=git_variant,
        )
        parent_records = [
            parent_metadata,
            _desktop_copied_metadata(
                root_metadata,
                timestamp="2026-08-12T12:19:40.734Z",
            ),
            *_desktop_causal_pair(
                child_thread_id=_DESKTOP_CHILD,
                child_agent_path=current_agent_path,
                fork_turns=current_fork_turns,
                call_id="call_DesktopParentEdge0000001",
                function_item_character="8",
                call_timestamp="2026-08-12T14:14:50.186Z",
                event_timestamp="2026-08-12T14:14:58.119Z",
                event_outer_residual_ms=parent_event_outer_residual_ms,
                marker=parent_marker,
            ),
        ]
        parent_path.parent.mkdir(parents=True, exist_ok=True)
        _write(parent_path, parent_records)
        if prefix_variant in {"full", "child-parent"}:
            current_prefix.append(
                _desktop_copied_metadata(
                    parent_metadata,
                    timestamp="2026-08-12T14:14:58.071Z",
                )
            )
        if prefix_variant == "full":
            current_prefix.append(
                _desktop_copied_metadata(
                    root_metadata,
                    timestamp="2026-08-12T14:14:58.071Z",
                )
            )
    root_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.parent.mkdir(parents=True, exist_ok=True)
    _write(root_path, root_records)
    _write(current_path, [*current_prefix, *_desktop_current_records(marker=current_marker)])
    return current_path, root_path, parent_path if depth == 2 else None


def _write_desktop_root_rollout(
    home: Path,
    *,
    marker: object = [],
    git_variant: str = "branch",
) -> Path:
    path = _desktop_rollout_path(home, thread_id=_DESKTOP_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(
        path,
        [
            _desktop_root_metadata(git_variant=git_variant),
            *_desktop_current_records(marker=marker),
        ],
    )
    return path


def _prepare_desktop_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    assert subject._DESKTOP_DYNAMIC_TOOLS_SHA256 == _DESKTOP_DYNAMIC_TOOLS_SHA256
    fixture_digest = hashlib.sha256(
        json.dumps(
            _DESKTOP_DYNAMIC_TOOLS,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    monkeypatch.setattr(subject, "_DESKTOP_DYNAMIC_TOOLS_SHA256", fixture_digest)


def _attest_desktop(path: Path, home: Path) -> subject.CodexPlaintextSpawnAttestation | None:
    return subject.attest_codex_plaintext_spawn(
        path,
        session_id=_DESKTOP_ROOT,
        turn_id=_DESKTOP_TURN,
        tool_use_id=_DESKTOP_CALL,
        tool_input=_DESKTOP_ARGS,
        environ={"CODEX_HOME": str(home)},
    )


def test_exact_desktop_alpha_marked_root_attests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    path = _write_desktop_root_rollout(home)

    attestation = _attest_desktop(path, home)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.profile_id == "desktop-0.147.0-alpha.6.6"
    assert attestation.cli_version == "0.147.0-alpha.6.6"
    assert attestation.ancestry_thread_ids == (_DESKTOP_ROOT,)
    assert subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_DESKTOP_ARGS,
    )


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "full",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "all",
                "root_marker": [],
                "residual": 1,
                "root_event_outer_residual_ms": 1,
            },
            id="d1-inherited-full-all-dynamic-branch-residual1-marked-root-edge",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "2",
                "residual": 0,
            },
            id="d1-inherited-external-two-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "3",
                "residual": 0,
            },
            id="d1-inherited-external-three-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "3",
                "residual": 1,
            },
            id="d1-inherited-external-three-dynamic-branch-residual1",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "4",
                "residual": 0,
            },
            id="d1-inherited-external-four-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "5",
                "residual": 0,
            },
            id="d1-inherited-external-five-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "full",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "all",
                "residual": 0,
            },
            id="d1-inherited-full-all-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "full",
                "dynamic_tools": True,
                "git_variant": "no-branch",
                "fork_turns": "all",
                "residual": 0,
            },
            id="d1-inherited-full-all-dynamic-no-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": False,
                "prefix_variant": "child-only",
                "dynamic_tools": False,
                "git_variant": "branch",
                "fork_turns": "none",
                "residual": 0,
            },
            id="d1-sparse-external-none-no-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "full",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "all",
                "parent_marker": [],
                "residual": 0,
            },
            id="d2-full-all-dynamic-branch-residual0-marked-parent-edge",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "child-parent",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "all",
                "residual": 0,
            },
            id="d2-child-parent-all-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": False,
                "git_variant": "branch",
                "fork_turns": "2",
                "residual": 0,
            },
            id="d2-inherited-child-inherited-parent-two-no-dynamic-branch-residual0",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "child-parent",
                "dynamic_tools": False,
                "git_variant": "branch",
                "fork_turns": "all",
                "residual": 0,
                "parent_inherited": False,
            },
            id="d2-child-parent-sparse-parent-all-no-dynamic-branch-residual0",
        ),
    ],
)
def test_desktop_alpha_observed_ancestry_variants_attest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, Any],
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=case["depth"],
        inherited=case["inherited"],
        prefix_variant=case["prefix_variant"],
        dynamic_tools=case["dynamic_tools"],
        git_variant=case["git_variant"],
        fork_turns=case["fork_turns"],
        root_marker=case.get("root_marker", _MISSING),
        parent_marker=case.get("parent_marker", _MISSING),
        current_residual_seconds=case["residual"],
        root_event_outer_residual_ms=case.get("root_event_outer_residual_ms", 0),
        parent_event_outer_residual_ms=case.get("parent_event_outer_residual_ms", 0),
        parent_inherited=case.get("parent_inherited", True),
    )

    attestation = _attest_desktop(current, home)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.profile_id == "desktop-0.147.0-alpha.6.6"
    expected_threads = (
        (_DESKTOP_PARENT, _DESKTOP_ROOT)
        if case["depth"] == 1
        else (_DESKTOP_CHILD, _DESKTOP_PARENT, _DESKTOP_ROOT)
    )
    assert attestation.ancestry_thread_ids == expected_threads
    assert len(attestation.external_file_paths) == case["depth"]
    if case["depth"] == 1:
        assert attestation.external_file_paths == (str(_root.resolve()),)
        assert attestation.ancestry_file_indexes == (0, 1)
        copied_count = 1 if case["prefix_variant"] == "full" else 0
        assert attestation.external_record_file_indexes == (0,) * copied_count + (1, 1, 1)
    else:
        assert _parent is not None
        assert attestation.external_file_paths == (
            str(_parent.resolve()),
            str(_root.resolve()),
        )
        assert attestation.ancestry_file_indexes == (0, 1, 2)
        copied_count = {"child-only": 0, "child-parent": 1, "full": 2}[case["prefix_variant"]]
        assert attestation.external_record_file_indexes == (
            (0,) * copied_count + (1, 1, 1, 1, 2, 2, 2)
        )
    assert subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_DESKTOP_ARGS,
    )


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "1",
                "residual": 0,
            },
            id="d1-inherited-child-only-dynamic-branch-fork1-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "6",
                "residual": 0,
            },
            id="d1-inherited-child-only-dynamic-branch-fork6-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": False,
                "git_variant": "branch",
                "fork_turns": "2",
                "residual": 0,
            },
            id="d1-inherited-child-only-no-dynamic-branch-fork2-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": False,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "none",
                "residual": 0,
            },
            id="d1-sparse-child-only-dynamic-branch-none-residual0",
        ),
        pytest.param(
            {
                "depth": 1,
                "inherited": True,
                "prefix_variant": "child-only",
                "dynamic_tools": True,
                "git_variant": "no-branch",
                "fork_turns": "2",
                "residual": 0,
            },
            id="d1-inherited-child-only-dynamic-no-branch-fork2-residual0",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "child-parent",
                "dynamic_tools": True,
                "git_variant": "no-branch",
                "fork_turns": "all",
                "residual": 0,
            },
            id="d2-inherited-child-parent-dynamic-no-branch-all-residual0-parent-inherited",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "child-parent",
                "dynamic_tools": False,
                "git_variant": "branch",
                "fork_turns": "3",
                "residual": 0,
                "parent_inherited": False,
            },
            id="d2-inherited-child-parent-no-dynamic-branch-fork3-residual0-parent-sparse",
        ),
        pytest.param(
            {
                "depth": 2,
                "inherited": True,
                "prefix_variant": "full",
                "dynamic_tools": True,
                "git_variant": "branch",
                "fork_turns": "all",
                "residual": 1,
            },
            id="d2-inherited-full-dynamic-branch-all-residual1-parent-inherited",
        ),
    ],
)
def test_desktop_alpha_rejects_unobserved_shape_cross_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: dict[str, Any],
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=case["depth"],
        inherited=case["inherited"],
        prefix_variant=case["prefix_variant"],
        dynamic_tools=case["dynamic_tools"],
        git_variant=case["git_variant"],
        fork_turns=case["fork_turns"],
        current_residual_seconds=case["residual"],
        parent_inherited=case.get("parent_inherited", True),
    )

    assert _attest_desktop(current, home) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "cli-version-with-desktop-lineage",
        "cli-source-with-desktop-version",
        "paginated-history-with-desktop-version",
        "cli-origin-with-desktop-version",
        "desktop-thread-source-user",
        "desktop-envelope-ordinal",
        "desktop-extra-metadata-key",
        "desktop-context-key-drift",
        "desktop-multi-agent-disabled",
        "desktop-subagent-other",
        "desktop-fork-parent-drift",
        "desktop-history-start-injected",
        "desktop-dynamic-tools-drift",
        "desktop-git-key-drift",
        "desktop-git-hash-drift",
        "desktop-depth-three",
        "desktop-agent-role-nonnull",
        "desktop-agent-path-drift",
    ],
)
def test_desktop_alpha_profile_and_metadata_drift_fail_open(  # noqa: C901
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=1,
        inherited=True,
        prefix_variant="child-only",
    )
    records = [json.loads(line) for line in current.read_text(encoding="utf-8").splitlines()]
    metadata = records[0]
    payload = metadata["payload"]
    spawn = payload["source"]["subagent"]["thread_spawn"]
    if mutation == "cli-version-with-desktop-lineage":
        payload["cli_version"] = "0.147.0"
    elif mutation == "cli-source-with-desktop-version":
        payload["source"] = "cli"
    elif mutation == "paginated-history-with-desktop-version":
        payload["history_mode"] = "paginated"
    elif mutation == "cli-origin-with-desktop-version":
        payload["originator"] = "codex-tui"
    elif mutation == "desktop-thread-source-user":
        payload["thread_source"] = "user"
    elif mutation == "desktop-envelope-ordinal":
        metadata["ordinal"] = 0
    elif mutation == "desktop-extra-metadata-key":
        payload["future_key"] = True
    elif mutation == "desktop-context-key-drift":
        payload["context_window"]["future_key"] = True
    elif mutation == "desktop-multi-agent-disabled":
        payload["multi_agent_version"] = "disabled"
    elif mutation == "desktop-subagent-other":
        payload["source"] = {"subagent": {"other": "guardian"}}
    elif mutation == "desktop-fork-parent-drift":
        payload["forked_from_id"] = _DESKTOP_CHILD
    elif mutation == "desktop-history-start-injected":
        payload["subagent_history_start_ordinal"] = 27
    elif mutation == "desktop-dynamic-tools-drift":
        payload["dynamic_tools"][0]["name"] = "future_app"
    elif mutation == "desktop-git-key-drift":
        payload["git"]["future_key"] = "future"
    elif mutation == "desktop-git-hash-drift":
        payload["git"]["commit_hash"] = "B" * 40
    elif mutation == "desktop-depth-three":
        spawn["depth"] = 3
    elif mutation == "desktop-agent-role-nonnull":
        spawn["agent_role"] = "reviewer"
    elif mutation == "desktop-agent-path-drift":
        payload["agent_path"] = "/root/different"
    _write(current, records)

    assert _attest_desktop(current, home) is None


def test_desktop_alpha_and_cli_profiles_cannot_cross_mix(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[], cli_version="0.147.0-alpha.6.6"))

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "parent_thread_id",
    [_DESKTOP_ROOT, _DESKTOP_PARENT],
    ids=["parent-is-session", "parent-differs-from-session"],
)
def test_desktop_alpha_no_depth_guardian_shape_fails_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    parent_thread_id: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    path = _desktop_rollout_path(home, thread_id=_DESKTOP_CHILD)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "session_id": _DESKTOP_ROOT,
        "id": _DESKTOP_CHILD,
        **_desktop_metadata_common(
            thread_id=_DESKTOP_CHILD,
            timestamp="2026-08-12T14:14:53.361Z",
            git_variant="branch",
        ),
        "parent_thread_id": parent_thread_id,
        "source": {"subagent": {"other": "guardian"}},
        "thread_source": "subagent",
        "multi_agent_version": "disabled",
    }
    _write(
        path,
        [
            _desktop_record(
                "session_meta",
                metadata,
                timestamp="2026-08-12T14:14:58.070Z",
            ),
            *_desktop_current_records(),
        ],
    )

    assert _attest_desktop(path, home) is None


@pytest.mark.parametrize("mutation", ["metadata-binding", "causal-binding"])
def test_desktop_alpha_depth_two_requires_inherited_parent_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, parent = _write_desktop_chain(
        home,
        depth=2,
        inherited=True,
        prefix_variant="child-only",
    )
    assert parent is not None
    if mutation == "metadata-binding":
        current_records = [
            json.loads(line) for line in current.read_text(encoding="utf-8").splitlines()
        ]
        current_records[0]["payload"].pop("forked_from_id")
        _write(current, current_records)
        parent_records = [
            json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()
        ]
        arguments = json.loads(parent_records[-3]["payload"]["arguments"])
        arguments["fork_turns"] = "none"
        parent_records[-3]["payload"]["arguments"] = json.dumps(
            arguments,
            separators=(",", ":"),
        )
        _write(parent, parent_records)
    else:
        parent_records = [
            json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()
        ]
        arguments = json.loads(parent_records[-3]["payload"]["arguments"])
        arguments["fork_turns"] = "none"
        parent_records[-3]["payload"]["arguments"] = json.dumps(
            arguments,
            separators=(",", ":"),
        )
        _write(parent, parent_records)

    assert _attest_desktop(current, home) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-root-owner",
        "ambiguous-root-owner",
        "replaced-root-owner",
        "missing-parent-owner",
        "ambiguous-parent-owner",
        "replaced-parent-owner",
        "copied-parent-drift",
        "copied-root-drift",
    ],
)
def test_desktop_alpha_requires_unique_canonical_owners_and_exact_copies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, root, parent = _write_desktop_chain(
        home,
        depth=2,
        inherited=True,
        prefix_variant="full",
    )
    assert parent is not None
    attestation: subject.CodexPlaintextSpawnAttestation | None = None
    if mutation in {"replaced-root-owner", "replaced-parent-owner"}:
        attestation = _attest_desktop(current, home)
        assert attestation is not None
    if mutation == "missing-root-owner":
        root.unlink()
    elif mutation == "ambiguous-root-owner":
        root.with_name(root.name.replace("T08-18-29", "T07-18-29")).write_bytes(root.read_bytes())
    elif mutation == "replaced-root-owner":
        raw = root.read_bytes()
        root.unlink()
        root.write_bytes(raw)
    elif mutation == "missing-parent-owner":
        parent.unlink()
    elif mutation == "ambiguous-parent-owner":
        parent.with_name(parent.name.replace("T08-19-35", "T07-19-35")).write_bytes(
            parent.read_bytes()
        )
    elif mutation == "replaced-parent-owner":
        raw = parent.read_bytes()
        parent.unlink()
        parent.write_bytes(raw)
    else:
        records = [json.loads(line) for line in current.read_text(encoding="utf-8").splitlines()]
        copied = records[1] if mutation == "copied-parent-drift" else records[2]
        if mutation == "copied-parent-drift":
            copied["payload"]["git"]["branch"] = "codex/different"
        else:
            copied["payload"]["model_provider"] = "future-provider"
        _write(current, records)

    if attestation is None:
        assert _attest_desktop(current, home) is None
    else:
        assert not subject.codex_plaintext_spawn_attestation_is_current(
            attestation,
            tool_input=_DESKTOP_ARGS,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "not-adjacent-call-start",
        "event-id-drift",
        "child-id-drift",
        "path-drift",
        "event-schema-drift",
        "event-time-minus-one",
        "event-time-plus-two",
        "duplicate-start",
        "missing-start",
        "missing-output",
        "output-before-start",
        "output-call-id-drift",
        "output-id-drift",
        "output-turn-drift",
        "output-path-drift",
        "output-schema-drift",
        "output-uuid-before-event",
        "output-outer-plus-three",
    ],
)
def test_desktop_alpha_direct_causal_transaction_is_exact(  # noqa: C901
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, root, _parent = _write_desktop_chain(
        home,
        depth=1,
        inherited=True,
        prefix_variant="child-only",
    )
    records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    _call, start, output = records[-3:]
    if mutation == "not-adjacent-call-start":
        records.insert(
            -2, _desktop_record("event_msg", {"type": "token_count"}, timestamp=start["timestamp"])
        )
    elif mutation == "event-id-drift":
        start["payload"]["event_id"] = "call_AAAAAAAAAAAAAAAAAAAAAAAA"
    elif mutation == "child-id-drift":
        start["payload"]["agent_thread_id"] = _DESKTOP_CHILD
    elif mutation == "path-drift":
        start["payload"]["agent_path"] = "/root/different"
    elif mutation == "event-schema-drift":
        start["payload"]["future_key"] = True
    elif mutation == "event-time-minus-one":
        start["payload"]["occurred_at_ms"] += 1
    elif mutation == "event-time-plus-two":
        start["timestamp"] = "2026-08-12T12:19:40.767Z"
    elif mutation == "duplicate-start":
        records.append(deepcopy(start))
    elif mutation == "missing-start":
        records.pop(-2)
    elif mutation == "missing-output":
        records.pop()
    elif mutation == "output-before-start":
        records[-2:] = [output, start]
    elif mutation == "output-call-id-drift":
        output["payload"]["call_id"] = "call_AAAAAAAAAAAAAAAAAAAAAAAA"
    elif mutation == "output-id-drift":
        output["payload"]["id"] = "fco_not-a-uuid"
    elif mutation == "output-turn-drift":
        output["payload"]["internal_chat_message_metadata_passthrough"]["turn_id"] = _TURN
    elif mutation == "output-path-drift":
        output["payload"]["output"] = '{"task_name":"/root/different"}'
    elif mutation == "output-schema-drift":
        output["payload"]["future_key"] = True
    elif mutation == "output-uuid-before-event":
        output["payload"]["id"] = f"fco_{_DESKTOP_PARENT}"
    elif mutation == "output-outer-plus-three":
        output["timestamp"] = "2026-08-12T12:19:40.791Z"
    _write(root, records)

    assert _attest_desktop(current, home) is None


@pytest.mark.parametrize(
    ("edge", "mutation"),
    [
        pytest.param("parent", "event-id", id="parent-event-id"),
        pytest.param("root", "event-id", id="root-event-id"),
        pytest.param("root", "reused-output-id", id="cross-edge-output-id-reuse"),
    ],
)
def test_desktop_alpha_depth_two_binds_both_causal_transactions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    edge: str,
    mutation: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, root, parent = _write_desktop_chain(
        home,
        depth=2,
        inherited=True,
        prefix_variant="child-only",
    )
    assert parent is not None
    path = parent if edge == "parent" else root
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if mutation == "event-id":
        records[-2]["payload"]["event_id"] = "call_AAAAAAAAAAAAAAAAAAAAAAAA"
    else:
        parent_records = [
            json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()
        ]
        records[-1]["payload"]["id"] = parent_records[-1]["payload"]["id"]
    _write(path, records)

    assert _attest_desktop(current, home) is None


@pytest.mark.parametrize("edge", ["parent", "root"])
def test_desktop_alpha_depth_two_currentness_revalidates_each_external_edge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    edge: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, root, parent = _write_desktop_chain(
        home,
        depth=2,
        inherited=True,
        prefix_variant="child-only",
    )
    assert parent is not None
    attestation = _attest_desktop(current, home)
    assert attestation is not None
    path = parent if edge == "parent" else root
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records[-2]["payload"]["event_id"] = "call_AAAAAAAAAAAAAAAAAAAAAAAA"
    _write(path, records)

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_DESKTOP_ARGS,
    )


@pytest.mark.parametrize(
    ("target", "marker"),
    [
        pytest.param("current", _MISSING, id="current-missing"),
        pytest.param("current", None, id="current-null"),
        pytest.param("current", ["ciphertext"], id="current-nonempty"),
        pytest.param("ancestor", None, id="ancestor-null"),
        pytest.param("ancestor", ["ciphertext"], id="ancestor-nonempty"),
        pytest.param("ancestor", {}, id="ancestor-wrong-type"),
    ],
)
def test_desktop_alpha_current_and_ancestor_marker_domains_are_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    marker: object,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=1,
        inherited=True,
        prefix_variant="child-only",
        current_marker=marker if target == "current" else [],
        root_marker=marker if target == "ancestor" else _MISSING,
    )

    assert _attest_desktop(current, home) is None


@pytest.mark.parametrize(
    "residual_seconds",
    [pytest.param(-1, id="minus-one"), pytest.param(2, id="plus-two")],
)
def test_desktop_alpha_filename_residual_rejects_unobserved_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    residual_seconds: int,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=1,
        inherited=True,
        prefix_variant="child-only",
        current_residual_seconds=residual_seconds,
    )

    assert _attest_desktop(current, home) is None


def test_cli_profile_accepts_observed_plus_one_filename_residual(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = rollout
    shifted = original.with_name(original.name.replace("T22-23-55", "T22-23-56"))
    _write(shifted, _records(marker=[]))

    assert _attest(shifted, environ) is not None


def test_cross_file_cli_external_rollout_rejects_plus_one_residual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    root.rename(root.with_name(root.name.replace("T22-23-55", "T22-23-56")))

    assert _attest(current, {"CODEX_HOME": str(home)}) is None


def test_desktop_alpha_requires_task_start_before_current_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    path = _write_desktop_root_rollout(home)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    records.pop(1)
    _write(path, records)

    assert _attest_desktop(path, home) is None


@pytest.mark.parametrize(
    "field",
    [
        pytest.param("arguments", id="arguments"),
        pytest.param("turn", id="turn"),
        pytest.param("call", id="call"),
        pytest.param("task-schema", id="task-schema"),
    ],
)
def test_desktop_alpha_current_call_binds_shared_authorization_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    path = _write_desktop_root_rollout(home)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    task = records[1]["payload"]
    call = records[2]["payload"]
    if field == "arguments":
        drifted = {**_DESKTOP_ARGS, "message": "Different transcript message."}
        call["arguments"] = json.dumps(drifted, separators=(",", ":"))
    elif field == "turn":
        call["internal_chat_message_metadata_passthrough"]["turn_id"] = _TURN
    elif field == "call":
        call["call_id"] = "call_AAAAAAAAAAAAAAAAAAAAAAAA"
    elif field == "task-schema":
        task["future_key"] = True
    _write(path, records)

    assert _attest_desktop(path, home) is None


def test_desktop_alpha_current_or_external_direct_replay_invalidates_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_desktop_fixture(monkeypatch)

    current_home = tmp_path / "current-home"
    current_path = _write_desktop_root_rollout(current_home)
    current_attestation = _attest_desktop(current_path, current_home)
    assert current_attestation is not None
    current_replay = _desktop_record(
        "event_msg",
        {
            "type": "sub_agent_activity",
            "event_id": _DESKTOP_CALL,
            "occurred_at_ms": 1786544100000,
            "agent_thread_id": _DESKTOP_CHILD,
            "agent_path": "/root/desktop_review",
            "kind": "started",
        },
        timestamp="2026-08-12T14:15:00.000Z",
    )
    with current_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(current_replay, separators=(",", ":")) + "\n")
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        current_attestation,
        tool_input=_DESKTOP_ARGS,
    )

    external_home = tmp_path / "external-home"
    external_path, root, _parent = _write_desktop_chain(
        external_home,
        depth=1,
        inherited=True,
        prefix_variant="child-only",
    )
    external_attestation = _attest_desktop(external_path, external_home)
    assert external_attestation is not None
    root_records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    with root.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(root_records[-2], separators=(",", ":")) + "\n")
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        external_attestation,
        tool_input=_DESKTOP_ARGS,
    )


def test_desktop_alpha_sealed_profile_and_external_arrays_are_authoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=1,
        inherited=True,
        prefix_variant="child-only",
    )
    attestation = _attest_desktop(current, home)
    assert attestation is not None

    unsealed_atomic_drift = replace(
        attestation,
        profile_id="cli-tui-0.147.0",
        cli_version="0.147.0",
    )
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        unsealed_atomic_drift,
        tool_input=_DESKTOP_ARGS,
    )

    profile_drift = replace(attestation, profile_id="cli-tui-0.147.0", seal="")
    profile_drift = replace(profile_drift, seal=subject._sealed(profile_drift))
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        profile_drift,
        tool_input=_DESKTOP_ARGS,
    )

    array_drift = replace(
        attestation,
        external_edge_child_thread_ids=(),
        seal="",
    )
    array_drift = replace(array_drift, seal=subject._sealed(array_drift))
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        array_drift,
        tool_input=_DESKTOP_ARGS,
    )


@pytest.mark.parametrize("mutation", ["ancestry-index", "record-index", "file-order"])
def test_desktop_alpha_depth_two_rejects_resealed_index_or_file_order_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, _root, _parent = _write_desktop_chain(
        home,
        depth=2,
        inherited=True,
        prefix_variant="child-only",
    )
    attestation = _attest_desktop(current, home)
    assert attestation is not None
    if mutation == "ancestry-index":
        drifted = replace(attestation, ancestry_file_indexes=(0, 2, 1), seal="")
    elif mutation == "record-index":
        swapped = tuple(
            2 if value == 1 else 1 for value in attestation.external_record_file_indexes
        )
        drifted = replace(attestation, external_record_file_indexes=swapped, seal="")
    else:
        drifted = replace(
            attestation,
            external_file_paths=tuple(reversed(attestation.external_file_paths)),
            seal="",
        )
    drifted = replace(drifted, seal=subject._sealed(drifted))

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        drifted,
        tool_input=_DESKTOP_ARGS,
    )


@pytest.mark.parametrize(
    ("depth", "location", "memory_mode"),
    [
        pytest.param(1, "root", _MISSING, id="external-root-missing"),
        pytest.param(1, "root", "enabled", id="external-root-enabled"),
        pytest.param(1, "current", "enabled", id="current-depth-one-enabled"),
        pytest.param(2, "current", "enabled", id="current-depth-two-enabled"),
        pytest.param(2, "parent", "enabled", id="external-parent-enabled"),
    ],
)
def test_desktop_alpha_late_metadata_cannot_poison_initial_or_current_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    depth: int,
    location: str,
    memory_mode: object,
) -> None:
    _prepare_desktop_fixture(monkeypatch)
    home = tmp_path / "codex-home"
    current, root, parent = _write_desktop_chain(
        home,
        depth=depth,
        inherited=True,
        prefix_variant="child-only",
    )
    historical = _desktop_root_metadata(
        outer_timestamp=(
            "2026-08-12T12:20:00.000Z" if location == "root" else "2026-08-12T14:14:59.000Z"
        )
    )
    if memory_mode is not _MISSING:
        historical["payload"]["memory_mode"] = memory_mode
    target = {"root": root, "current": current, "parent": parent}[location]
    assert target is not None
    target_records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    if location in {"root", "parent"}:
        historical_index = len(target_records)
    else:
        historical_index = 2
    target_records.insert(historical_index, historical)
    _write(target, target_records)
    attestation = _attest_desktop(current, home)
    assert attestation is not None

    target_records[historical_index]["payload"]["model_provider"] = "future-provider"
    _write(target, target_records)

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_DESKTOP_ARGS,
    )
    assert _attest_desktop(current, home) is None


def _record(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"timestamp": "2026-08-13T00:00:00.000Z", "type": kind, "payload": payload}


def _root_metadata(
    *,
    session_id: str = _SESSION,
    cli_version: str = "0.147.0",
    source: str = "cli",
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> dict[str, Any]:
    return _record(
        "session_meta",
        {
            "id": session_id,
            "session_id": session_id,
            "cli_version": cli_version,
            "history_mode": history_mode,
            "source": source,
            "thread_source": "user",
            "originator": originator,
        },
    )


def _subagent_metadata(
    *,
    thread_id: str,
    parent_thread_id: str,
    depth: int,
    cli_version: str = "0.147.0",
    root_session_id: str = _SESSION,
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> dict[str, Any]:
    return _record(
        "session_meta",
        {
            "id": thread_id,
            "session_id": root_session_id,
            "forked_from_id": parent_thread_id,
            "parent_thread_id": parent_thread_id,
            "cli_version": cli_version,
            "history_mode": history_mode,
            "originator": originator,
            "subagent_history_start_ordinal": None if history_mode == "legacy" else 27,
            "multi_agent_version": "v2",
            "agent_path": "/root/security_review",
            "agent_nickname": "Goodall",
            "source": {
                "subagent": {
                    "thread_spawn": {
                        "parent_thread_id": parent_thread_id,
                        "depth": depth,
                        "agent_path": "/root/security_review",
                        "agent_nickname": "Goodall",
                        "agent_role": None,
                    }
                }
            },
            "thread_source": "subagent",
        },
    )


def _records(
    *,
    args: dict[str, Any] | None = None,
    marker: object = _MISSING,
    cli_version: str = "0.147.0",
    call_id: str = _CALL,
    turn_id: str = _TURN,
    session_id: str = _SESSION,
    source: str = "cli",
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> list[dict[str, Any]]:
    call = {
        "type": "function_call",
        "namespace": "collaboration",
        "name": "spawn_agent",
        "arguments": json.dumps(args or _ARGS, separators=(",", ":")),
        "call_id": call_id,
        "id": _FUNCTION_ITEM,
        "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
    }
    if marker is not _MISSING:
        call["encrypted_function_args"] = marker
    return [
        _root_metadata(
            session_id=session_id,
            cli_version=cli_version,
            source=source,
            history_mode=history_mode,
            originator=originator,
        ),
        _record("event_msg", {"type": "task_started", "turn_id": turn_id}),
        _record("response_item", call),
    ]


def _forked_records(
    *,
    thread_id: str = _CHILD_THREAD,
    parent_thread_id: str = _SESSION,
    depth: int = 1,
    parent_metadata: dict[str, Any] | None = None,
    marker: object = _MISSING,
    root_session_id: str = _SESSION,
    root_source: str = "cli",
    history_mode: str = "paginated",
    originator: str = "codex-tui",
) -> list[dict[str, Any]]:
    records = _records(
        marker=marker,
        session_id=root_session_id,
        source=root_source,
        history_mode=history_mode,
        originator=originator,
    )
    return [
        _subagent_metadata(
            thread_id=thread_id,
            parent_thread_id=parent_thread_id,
            depth=depth,
            root_session_id=root_session_id,
            history_mode=history_mode,
            originator=originator,
        ),
        parent_metadata
        or _root_metadata(
            session_id=root_session_id,
            source=root_source,
            history_mode=history_mode,
            originator=originator,
        ),
        *records[1:],
    ]


@pytest.fixture
def rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "codex-home"
    path = (
        home / "sessions" / "2026" / "08" / "12" / f"rollout-2026-08-12T22-23-55-{_SESSION}.jsonl"
    )
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    return path, {"CODEX_HOME": str(home)}


@pytest.fixture
def forked_rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "codex-home"
    path = (
        home
        / "sessions"
        / "2026"
        / "08"
        / "13"
        / f"rollout-2026-08-13T00-16-49-{_CHILD_THREAD}.jsonl"
    )
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    return path, {"CODEX_HOME": str(home)}


@pytest.fixture
def exec_rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str]]:
    home = tmp_path / "codex-home"
    path = (
        home
        / "sessions"
        / "2026"
        / "08"
        / "11"
        / f"rollout-2026-08-11T13-41-04-{_EXEC_CHILD}.jsonl"
    )
    path.parent.mkdir(parents=True)
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    return path, {"CODEX_HOME": str(home)}


def _write(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, separators=(",", ":")) + "\n" for record in records),
        encoding="utf-8",
    )


def _attest(
    path: Path,
    environ: dict[str, str],
    *,
    tool_input: object = _ARGS,
    session_id: str = _SESSION,
) -> subject.CodexPlaintextSpawnAttestation | None:
    return subject.attest_codex_plaintext_spawn(
        path,
        session_id=session_id,
        turn_id=_TURN,
        tool_use_id=_CALL,
        tool_input=tool_input,
        environ=environ,
    )


def test_exact_marked_spawn_attests_and_tolerates_unrelated_append(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))

    attestation = _attest(path, environ)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.cli_version == "0.147.0"
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(_record("event_msg", {"type": "token_count"})) + "\n")
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_outer_record_ordinal_remains_optional(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    for ordinal, record in enumerate(records):
        record["ordinal"] = ordinal
    _write(path, records)

    assert _attest(path, environ) is not None


def test_target_response_item_rejects_an_extra_outer_key(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    records[-1]["future_envelope_field"] = True
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize("ordinal", [True, -1, "0", 1.0, None])
def test_target_response_item_requires_a_nonnegative_integer_ordinal(
    rollout: tuple[Path, dict[str, str]],
    ordinal: object,
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    records[-1]["ordinal"] = ordinal
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "timestamp",
    [
        _MISSING,
        None,
        1723507200,
        "2026-08-13T00:00:00Z",
        "2026-08-13T00:00:00.000000Z",
        "2026-13-13T00:00:00.000Z",
        "2026-08-13T24:00:00.000Z",
        "2026-08-13T00:00:00.000+00:00",
    ],
)
def test_target_response_item_requires_exact_observed_timestamp(
    rollout: tuple[Path, dict[str, str]],
    timestamp: object,
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    if timestamp is _MISSING:
        records[-1].pop("timestamp")
    else:
        records[-1]["timestamp"] = timestamp
    _write(path, records)

    assert _attest(path, environ) is None


def test_exact_forked_child_shape_attests_and_binds_thread_and_root(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = forked_rollout
    _write(path, _forked_records(marker=[]))

    attestation = _attest(path, environ)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _CHILD_THREAD
    assert attestation.root_session_id == _SESSION
    assert attestation.ancestry_thread_ids == (_CHILD_THREAD, _SESSION)
    assert len(attestation.ancestry_lengths) == 2
    assert all(length > 0 for length in attestation.ancestry_lengths)
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


@pytest.mark.parametrize(("depth", "inherited"), [(1, True), (1, False), (2, True), (2, False)])
def test_exact_one_metadata_tui_chain_attests_across_canonical_rollouts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    depth: int,
    inherited: bool,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, _root, _parent = _write_cross_file_chain(
        home,
        depth=depth,
        inherited=inherited,
    )

    attestation = _attest(current, {"CODEX_HOME": str(home)})

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    expected_threads = (
        (_CHILD_THREAD, _SESSION)
        if depth == 1
        else (_GRANDCHILD_THREAD, _DEPTH_TWO_PARENT, _SESSION)
    )
    assert attestation.ancestry_thread_ids == expected_threads
    assert len(attestation.external_file_paths) == depth
    assert attestation.external_file_utc_offset_minutes == (-240,) * depth
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_one_metadata_tui_chain_accepts_independent_cross_offset_rollouts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    shifted_root = root.with_name(root.name.replace("T22-23-55", "T21-23-55"))
    shifted_parent = parent.with_name(parent.name.replace("T23-25-50", "T21-25-50"))
    root.rename(shifted_root)
    parent.rename(shifted_parent)

    attestation = _attest(current, {"CODEX_HOME": str(home)})

    assert attestation is not None
    assert tuple(map(Path, attestation.external_file_paths)) == (
        shifted_parent,
        shifted_root,
    )
    assert attestation.external_file_utc_offset_minutes == (-360, -300)
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_cross_file_ancestry_allows_only_unrelated_external_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    attestation = _attest(current, {"CODEX_HOME": str(home)})
    assert attestation is not None

    with root.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(_record("event_msg", {"type": "token_count"})) + "\n")

    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_external_rollouts_use_one_initial_streaming_pass_each(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    external_inodes = {root.stat().st_ino, parent.stat().st_ino}
    initial_passes: dict[int, int] = dict.fromkeys(external_inodes, 0)
    original_snapshot_lines = subject._snapshot_lines

    def observed_snapshot_lines(
        descriptor: int,
        size: int,
        *,
        start: int = 0,
    ):
        inode = os.fstat(descriptor).st_ino
        if inode in initial_passes and start == 0:
            initial_passes[inode] += 1
        return original_snapshot_lines(descriptor, size, start=start)

    monkeypatch.setattr(subject, "_snapshot_lines", observed_snapshot_lines)

    assert _attest(current, {"CODEX_HOME": str(home)}) is not None
    assert initial_passes == dict.fromkeys(external_inodes, 1)


@pytest.mark.parametrize("edge_owner", ["root", "parent"])
def test_cross_file_causal_edges_accept_exact_empty_delivery_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    edge_owner: str,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    target = root if edge_owner == "root" else parent
    records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    records[-2]["payload"]["encrypted_function_args"] = []
    _write(target, records)

    attestation = _attest(current, {"CODEX_HOME": str(home)})

    assert attestation is not None
    target.write_bytes(
        target.read_bytes().replace(b'"encrypted_function_args":[]', b'"future_marker_property":{}')
    )
    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_one_metadata_depth_one_accepts_observed_three_turn_inheritance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    arguments = json.loads(records[-2]["payload"]["arguments"])
    arguments["fork_turns"] = "3"
    records[-2]["payload"]["arguments"] = json.dumps(arguments, separators=(",", ":"))
    _write(root, records)

    assert _attest(current, {"CODEX_HOME": str(home)}) is not None


def test_one_metadata_depth_one_accepts_observed_four_turn_inheritance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    arguments = json.loads(records[-2]["payload"]["arguments"])
    arguments["fork_turns"] = "4"
    records[-2]["payload"]["arguments"] = json.dumps(arguments, separators=(",", ":"))
    _write(root, records)

    assert _attest(current, {"CODEX_HOME": str(home)}) is not None


def test_depth_two_accepts_numeric_inherited_root_edge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=2, inherited=True)
    records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    arguments = json.loads(records[-2]["payload"]["arguments"])
    arguments["fork_turns"] = "4"
    records[-2]["payload"]["arguments"] = json.dumps(arguments, separators=(",", ":"))
    _write(root, records)

    assert _attest(current, {"CODEX_HOME": str(home)}) is not None


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_root",
        "missing_parent",
        "ambiguous_root_path",
        "malformed_root_filename",
        "bounded_root_directory",
        "current_depth_three",
        "cycle",
        "root_extra_key",
        "root_missing_git",
        "wrong_version",
        "wrong_lineage",
        "copied_root_drift",
        "parent_not_inherited",
        "sparse_wrong_fork_turns",
        "inherited_wrong_fork_turns",
        "inherited_noncanonical_decimal",
        "root_inherited_none",
        "non_null_agent_role",
        "causal_marker_null",
        "causal_marker_nonempty",
        "causal_marker_wrong",
        "causal_marker_extra",
        "causal_not_adjacent",
        "causal_event_parent",
        "causal_turn",
        "causal_agent_path",
        "causal_time",
        "causal_completed_bool",
        "metadata_ordinal",
        "metadata_timestamp",
        "noncanonical_agent_path",
        "duplicate_started",
    ],
)
def test_cross_file_ancestry_rejects_missing_ambiguous_or_unbound_lineage(  # noqa: C901
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    depth = (
        1
        if mutation
        in {
            "missing_root",
            "ambiguous_root_path",
            "malformed_root_filename",
            "bounded_root_directory",
            "current_depth_three",
            "cycle",
            "root_extra_key",
            "root_missing_git",
            "wrong_version",
            "wrong_lineage",
            "sparse_wrong_fork_turns",
            "inherited_wrong_fork_turns",
            "inherited_noncanonical_decimal",
            "causal_marker_null",
            "causal_marker_nonempty",
            "causal_marker_wrong",
            "causal_marker_extra",
            "causal_not_adjacent",
            "causal_event_parent",
            "causal_turn",
            "causal_agent_path",
            "causal_time",
            "causal_completed_bool",
            "metadata_ordinal",
            "metadata_timestamp",
            "noncanonical_agent_path",
            "duplicate_started",
        }
        else 2
    )
    inherited = mutation != "sparse_wrong_fork_turns"
    current, root, parent = _write_cross_file_chain(
        home,
        depth=depth,
        inherited=inherited,
    )
    current_records = [
        json.loads(line) for line in current.read_text(encoding="utf-8").splitlines()
    ]
    root_records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    parent_records = (
        [json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()]
        if parent is not None
        else []
    )
    if mutation == "missing_root":
        root.unlink()
    elif mutation == "missing_parent":
        assert parent is not None
        parent.unlink()
    elif mutation == "ambiguous_root_path":
        duplicate = root.with_name(root.name.replace("T22-23-55", "T21-23-55"))
        duplicate.write_bytes(root.read_bytes())
    elif mutation == "malformed_root_filename":
        malformed = root.with_name(root.name.replace("T22-23-55", "T99-23-55"))
        root.rename(malformed)
    elif mutation == "bounded_root_directory":
        (root.parent / "unrelated.jsonl").write_text("{}\n", encoding="utf-8")
        monkeypatch.setattr(subject, "_MAX_ROLLOUT_DIRECTORY_ENTRIES", 1)
    elif mutation == "current_depth_three":
        current_records[0]["payload"]["source"]["subagent"]["thread_spawn"]["depth"] = 3
    elif mutation == "cycle":
        current_records[0]["payload"]["parent_thread_id"] = _CHILD_THREAD
        current_records[0]["payload"]["forked_from_id"] = _CHILD_THREAD
        current_records[0]["payload"]["source"]["subagent"]["thread_spawn"]["parent_thread_id"] = (
            _CHILD_THREAD
        )
    elif mutation == "root_extra_key":
        root_records[0]["payload"]["future"] = True
    elif mutation == "root_missing_git":
        root_records[0]["payload"].pop("git")
    elif mutation == "wrong_version":
        current_records[0]["payload"]["cli_version"] = "0.148.0"
    elif mutation == "wrong_lineage":
        current_records[0]["payload"]["originator"] = "codex_exec"
    elif mutation == "copied_root_drift":
        parent_records[1]["payload"]["model_provider"] = "different"
    elif mutation == "parent_not_inherited":
        parent_records[0]["payload"].pop("forked_from_id")
        parent_records[0]["payload"].pop("subagent_history_start_ordinal")
    elif mutation in {
        "sparse_wrong_fork_turns",
        "inherited_wrong_fork_turns",
        "inherited_noncanonical_decimal",
    }:
        records = root_records if depth == 1 else parent_records
        records[-2]["payload"]["arguments"] = json.dumps(
            {
                "task_name": "depth_one_child" if depth == 1 else "depth_two_child",
                "message": "Sanitized bounded child task.",
                "fork_turns": (
                    "2"
                    if mutation == "sparse_wrong_fork_turns"
                    else "04"
                    if mutation == "inherited_noncanonical_decimal"
                    else "none"
                ),
            },
            separators=(",", ":"),
        )
    elif mutation == "root_inherited_none":
        root_records[-2]["payload"]["arguments"] = json.dumps(
            {
                "task_name": "depth_one_parent",
                "message": "Sanitized bounded child task.",
                "fork_turns": "none",
            },
            separators=(",", ":"),
        )
    elif mutation == "non_null_agent_role":
        current_records[0]["payload"]["source"]["subagent"]["thread_spawn"]["agent_role"] = (
            "reviewer"
        )
    elif mutation in {
        "causal_marker_null",
        "causal_marker_nonempty",
        "causal_marker_wrong",
        "causal_marker_extra",
    }:
        root_records[-2]["payload"]["encrypted_function_args"] = {
            "causal_marker_null": None,
            "causal_marker_nonempty": ["sealed"],
            "causal_marker_wrong": {},
            "causal_marker_extra": [],
        }[mutation]
        if mutation == "causal_marker_extra":
            root_records[-2]["payload"]["future"] = True
    elif mutation == "causal_not_adjacent":
        root_records.insert(-1, _record("event_msg", {"type": "token_count"}))
    elif mutation == "causal_event_parent":
        root_records[-1]["payload"]["thread_id"] = _CHILD_THREAD
    elif mutation == "causal_turn":
        root_records[-1]["payload"]["turn_id"] = _V4_TURN
    elif mutation == "causal_agent_path":
        root_records[-1]["payload"]["item"]["agent_path"] = "/root/other"
    elif mutation == "causal_time":
        root_records[-1]["payload"]["started_at_ms"] += 1
        root_records[-1]["payload"]["completed_at_ms"] += 1
    elif mutation == "causal_completed_bool":
        root_records[-1]["payload"]["completed_at_ms"] = float(
            root_records[-1]["payload"]["started_at_ms"]
        )
    elif mutation == "metadata_ordinal":
        current_records[0]["ordinal"] = 1
    elif mutation == "metadata_timestamp":
        current_records[0]["payload"]["timestamp"] = "2026-02-30T04:16:49.226Z"
    elif mutation == "noncanonical_agent_path":
        current_records[0]["payload"]["agent_path"] = "/root//depth_one_child"
        current_records[0]["payload"]["source"]["subagent"]["thread_spawn"]["agent_path"] = (
            "/root//depth_one_child"
        )
    elif mutation == "duplicate_started":
        root_records.append(root_records[-1])
    if current.exists():
        _write(current, current_records)
    if root.exists():
        _write(root, root_records)
    if parent is not None and parent.exists():
        _write(parent, parent_records)

    assert _attest(current, {"CODEX_HOME": str(home)}) is None


def test_one_metadata_exec_fork_remains_unsupported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, _root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    records = [json.loads(line) for line in current.read_text(encoding="utf-8").splitlines()]
    records[0]["payload"]["history_mode"] = "legacy"
    records[0]["payload"]["originator"] = "codex_exec"
    records[0]["payload"]["subagent_history_start_ordinal"] = None
    _write(current, records)

    assert _attest(current, {"CODEX_HOME": str(home)}) is None


def test_external_rollout_hardlink_and_oversize_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    hardlink = tmp_path / "root-hardlink.jsonl"
    try:
        os.link(root, hardlink)
    except OSError:
        pytest.skip("hardlinks are unavailable on this filesystem")
    assert _attest(current, {"CODEX_HOME": str(home)}) is None
    hardlink.unlink()

    with root.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                _record("event_msg", {"type": "token_count", "padding": "x" * 4096}),
                separators=(",", ":"),
            )
            + "\n"
        )
    original_limit = subject._MAX_TRANSCRIPT_BYTES
    monkeypatch.setattr(subject, "_MAX_TRANSCRIPT_BYTES", root.stat().st_size - 1)
    assert current.stat().st_size < subject._MAX_TRANSCRIPT_BYTES
    assert original_limit > root.stat().st_size
    assert _attest(current, {"CODEX_HOME": str(home)}) is None


def test_external_ancestry_aggregate_byte_bound_is_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    exact_size = root.stat().st_size + parent.stat().st_size
    monkeypatch.setattr(subject, "_MAX_EXTERNAL_ANCESTRY_BYTES", exact_size)

    assert _attest(current, {"CODEX_HOME": str(home)}) is not None

    monkeypatch.setattr(subject, "_MAX_EXTERNAL_ANCESTRY_BYTES", exact_size - 1)
    assert _attest(current, {"CODEX_HOME": str(home)}) is None


def test_final_currentness_recomputes_unique_external_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    attestation = _attest(current, {"CODEX_HOME": str(home)})
    assert attestation is not None
    duplicate = root.with_name(root.name.replace("T22-23-55", "T21-23-55"))
    original_open_rollout = subject._open_rollout
    opens = 0

    def racing_open_rollout(path: Path, sessions_root: Path):
        nonlocal opens
        descriptor, metadata = original_open_rollout(path, sessions_root)
        opens += 1
        if opens == 2:
            duplicate.write_bytes(root.read_bytes())
        return descriptor, metadata

    monkeypatch.setattr(subject, "_open_rollout", racing_open_rollout)

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )
    assert duplicate.exists()


def test_current_external_ancestry_aggregate_byte_bound_is_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    attestation = _attest(current, {"CODEX_HOME": str(home)})
    assert attestation is not None
    with root.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(_record("event_msg", {"type": "token_count"})) + "\n")
    current_total = root.stat().st_size + parent.stat().st_size
    monkeypatch.setattr(subject, "_MAX_EXTERNAL_ANCESTRY_BYTES", current_total)

    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)

    monkeypatch.setattr(subject, "_MAX_EXTERNAL_ANCESTRY_BYTES", current_total - 1)
    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


@pytest.mark.parametrize(
    "mutation",
    [
        "current_metadata",
        "parent_metadata",
        "root_metadata",
        "copied_root",
        "parent_launch",
        "root_launch",
        "parent_replacement",
        "root_replacement",
        "root_unbound_mutation",
        "parent_duplicate_suffix",
        "root_session_meta_suffix",
        "root_ambiguous_path_suffix",
    ],
)
def test_cross_file_bound_mutation_replacement_or_replay_invalidates_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    if mutation == "root_unbound_mutation":
        with root.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    _record("event_msg", {"type": "token_count", "padding": "aaaa"}),
                    separators=(",", ":"),
                )
                + "\n"
            )
    attestation = _attest(current, {"CODEX_HOME": str(home)})
    assert attestation is not None
    target = {
        "current_metadata": current,
        "parent_metadata": parent,
        "root_metadata": root,
        "copied_root": parent,
        "parent_launch": parent,
        "root_launch": root,
    }.get(mutation)
    if target is not None:
        raw = target.read_bytes()
        needle = {
            "current_metadata": b'"agent_nickname":"Goodall"',
            "parent_metadata": b'"agent_nickname":"Goodall"',
            "root_metadata": b'"model_provider":"openai"',
            "copied_root": b'"model_provider":"openai"',
            "parent_launch": b'\\"task_name\\":\\"depth_two_child\\"',
            "root_launch": b'\\"task_name\\":\\"depth_one_parent\\"',
        }[mutation]
        replacement = (
            needle.replace(b"Goodall", b"Badall!")
            .replace(b"openai", b"closed")
            .replace(b"depth", b"wrong")
        )
        target.write_bytes(raw.replace(needle, replacement, 1))
    elif mutation in {"parent_replacement", "root_replacement"}:
        replaced = parent if mutation == "parent_replacement" else root
        raw = replaced.read_bytes()
        replaced.unlink()
        replaced.write_bytes(raw)
    elif mutation == "root_unbound_mutation":
        raw = root.read_bytes()
        assert b'"padding":"aaaa"' in raw
        root.write_bytes(raw.replace(b'"padding":"aaaa"', b'"padding":"bbbb"'))
    elif mutation == "parent_duplicate_suffix":
        with parent.open("a", encoding="utf-8") as stream:
            duplicate = _causal_edge(
                parent_thread_id=_DEPTH_TWO_PARENT,
                child_thread_id=_GRANDCHILD_THREAD,
                task_name="depth_two_child",
                child_agent_path="/root/depth_one_parent/depth_two_child",
                fork_turns="3",
                ordinal=100,
                call_id=attestation.external_edge_call_ids[0],
                function_item_character="e",
                call_timestamp="2026-08-13T03:26:32.700Z",
                start_timestamp="2026-08-13T03:26:32.824Z",
            )
            stream.write(
                "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in duplicate)
            )
    elif mutation == "root_session_meta_suffix":
        with root.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(_real_root_metadata(), separators=(",", ":")) + "\n")
    elif mutation == "root_ambiguous_path_suffix":
        duplicate = root.with_name(root.name.replace("T22-23-55", "T21-23-55"))
        duplicate.write_bytes(root.read_bytes())

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )


def test_cross_file_external_identity_and_scanned_prefix_are_sealed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)

    replacement_home = tmp_path / "replacement-home"
    current, root, _parent = _write_cross_file_chain(
        replacement_home,
        depth=1,
        inherited=True,
    )
    attestation = _attest(current, {"CODEX_HOME": str(replacement_home)})
    assert attestation is not None
    original = root.read_bytes()
    root.unlink()
    root.write_bytes(original)
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )

    prefix_home = tmp_path / "prefix-home"
    current, root, _parent = _write_cross_file_chain(
        prefix_home,
        depth=1,
        inherited=True,
    )
    records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    records.insert(
        1,
        _real_record(
            "event_msg",
            {"type": "token_count", "opaque_bucket": "alpha"},
            ordinal=5,
            timestamp="2026-08-13T04:00:00.000Z",
        ),
    )
    _write(root, records)
    attestation = _attest(current, {"CODEX_HOME": str(prefix_home)})
    assert attestation is not None
    raw = root.read_bytes()
    assert raw.count(b'"opaque_bucket":"alpha"') == 1
    root.write_bytes(raw.replace(b'"opaque_bucket":"alpha"', b'"opaque_bucket":"omega"'))
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )


def test_cross_file_external_records_and_parallel_arrays_are_structurally_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, _root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    attestation = _attest(current, {"CODEX_HOME": str(home)})
    assert attestation is not None

    forged_record = replace(
        attestation,
        external_record_sha256=("0" * 64, *attestation.external_record_sha256[1:]),
        seal="",
    )
    forged_record = replace(forged_record, seal=subject._sealed(forged_record))
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        forged_record,
        tool_input=_ARGS,
    )

    forged_shape = replace(
        attestation,
        external_file_snapshot_sha256=(
            *attestation.external_file_snapshot_sha256,
            "0" * 64,
        ),
        seal="",
    )
    forged_shape = replace(forged_shape, seal=subject._sealed(forged_shape))
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        forged_shape,
        tool_input=_ARGS,
    )


def test_cross_file_both_causal_edges_and_history_variant_are_authoritative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)

    parent_join_home = tmp_path / "parent-join-home"
    current, _root, parent = _write_cross_file_chain(
        parent_join_home,
        depth=2,
        inherited=True,
    )
    assert parent is not None
    parent_records = [json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()]
    parent_records[-1]["payload"]["thread_id"] = _SESSION
    _write(parent, parent_records)
    assert _attest(current, {"CODEX_HOME": str(parent_join_home)}) is None

    root_join_home = tmp_path / "root-join-home"
    current, root, _parent = _write_cross_file_chain(
        root_join_home,
        depth=2,
        inherited=True,
    )
    root_records = [json.loads(line) for line in root.read_text(encoding="utf-8").splitlines()]
    root_arguments = json.loads(root_records[-2]["payload"]["arguments"])
    root_arguments["fork_turns"] = "none"
    root_records[-2]["payload"]["arguments"] = json.dumps(
        root_arguments,
        separators=(",", ":"),
    )
    _write(root, root_records)
    assert _attest(current, {"CODEX_HOME": str(root_join_home)}) is None

    variant_home = tmp_path / "variant-home"
    current, _root, parent = _write_cross_file_chain(
        variant_home,
        depth=2,
        inherited=True,
    )
    assert parent is not None
    parent_records = [json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()]
    current_arguments = json.loads(parent_records[-2]["payload"]["arguments"])
    current_arguments["fork_turns"] = "none"
    parent_records[-2]["payload"]["arguments"] = json.dumps(
        current_arguments,
        separators=(",", ":"),
    )
    _write(parent, parent_records)
    assert _attest(current, {"CODEX_HOME": str(variant_home)}) is None


def test_cross_file_copied_root_matches_canonical_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, _root, parent = _write_cross_file_chain(home, depth=2, inherited=True)
    assert parent is not None
    parent_records = [json.loads(line) for line in parent.read_text(encoding="utf-8").splitlines()]
    parent_records[1]["payload"]["model_provider"] = "different"
    _write(parent, parent_records)

    assert _attest(current, {"CODEX_HOME": str(home)}) is None


def test_cross_file_nonzero_offset_is_required_for_canonical_lookup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, _root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)

    assert _attest(current, {"CODEX_HOME": str(home)}) is not None


def test_cross_file_appended_causal_replay_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "codex-home"
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(subject, "storage_file_is_trusted", lambda *_a, **_k: True)
    current, root, _parent = _write_cross_file_chain(home, depth=1, inherited=True)
    attestation = _attest(current, {"CODEX_HOME": str(home)})
    assert attestation is not None
    replay = _causal_edge(
        parent_thread_id=_SESSION,
        child_thread_id=_CHILD_THREAD,
        task_name="depth_one_child",
        child_agent_path="/root/depth_one_child",
        fork_turns="2",
        ordinal=100,
        call_id=attestation.external_edge_call_ids[0],
        function_item_character="e",
        call_timestamp="2026-08-13T04:16:49.100Z",
        start_timestamp="2026-08-13T04:16:49.225Z",
    )
    with root.open("a", encoding="utf-8") as stream:
        stream.write("".join(json.dumps(item, separators=(",", ":")) + "\n" for item in replay))

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )


def test_exact_exec_root_shape_attests(
    exec_rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = exec_rollout
    path = original.with_name(f"rollout-2026-08-11T13-39-59-{_EXEC_SESSION}.jsonl")
    _write(
        path,
        _records(
            marker=[],
            session_id=_EXEC_SESSION,
            source="exec",
            history_mode="legacy",
            originator="codex_exec",
        ),
    )

    attestation = _attest(path, environ, session_id=_EXEC_SESSION)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _EXEC_SESSION
    assert attestation.root_session_id == _EXEC_SESSION
    assert attestation.ancestry_thread_ids == (_EXEC_SESSION,)


def test_exact_exec_depth_one_child_shape_attests(
    exec_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = exec_rollout
    _write(
        path,
        _forked_records(
            thread_id=_EXEC_CHILD,
            parent_thread_id=_EXEC_SESSION,
            root_session_id=_EXEC_SESSION,
            root_source="exec",
            history_mode="legacy",
            originator="codex_exec",
            marker=[],
        ),
    )

    attestation = _attest(path, environ, session_id=_EXEC_SESSION)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _EXEC_CHILD
    assert attestation.root_session_id == _EXEC_SESSION
    assert attestation.ancestry_thread_ids == (_EXEC_CHILD, _EXEC_SESSION)


@pytest.mark.parametrize(
    ("source", "history_mode", "originator"),
    [
        ("cli", "legacy", "codex-tui"),
        ("exec", "paginated", "codex_exec"),
        ("unknown", "legacy", "codex_exec"),
        ("exec", "unknown", "codex_exec"),
        ("exec", "legacy", "codex-tui"),
        ("cli", "paginated", "codex_exec"),
    ],
)
def test_root_rollout_rejects_cross_mixed_or_unknown_lineage(
    rollout: tuple[Path, dict[str, str]],
    source: str,
    history_mode: str,
    originator: str,
) -> None:
    path, environ = rollout
    _write(
        path,
        _records(
            marker=[],
            source=source,
            history_mode=history_mode,
            originator=originator,
        ),
    )

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "child_history",
        "child_originator",
        "root_source",
        "root_history",
        "missing_child_history",
        "missing_root_source",
        "exec_history_start",
    ],
)
def test_exec_child_and_root_must_share_one_exact_lineage(
    exec_rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    path, environ = exec_rollout
    records = _forked_records(
        thread_id=_EXEC_CHILD,
        parent_thread_id=_EXEC_SESSION,
        root_session_id=_EXEC_SESSION,
        root_source="exec",
        history_mode="legacy",
        originator="codex_exec",
        marker=[],
    )
    child = records[0]["payload"]
    root = records[1]["payload"]
    if mutation == "child_history":
        child["history_mode"] = "paginated"
    elif mutation == "child_originator":
        child["originator"] = "codex-tui"
    elif mutation == "root_source":
        root["source"] = "cli"
    elif mutation == "root_history":
        root["history_mode"] = "paginated"
    elif mutation == "missing_child_history":
        child.pop("history_mode")
    elif mutation == "missing_root_source":
        root.pop("source")
    elif mutation == "exec_history_start":
        child["subagent_history_start_ordinal"] = 27
    _write(path, records)

    assert _attest(path, environ, session_id=_EXEC_SESSION) is None


def test_unobserved_exec_depth_two_shape_fails_closed(
    exec_rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = exec_rollout
    current = "019ff1ea-0000-7000-8000-000000000001"
    path = original.with_name(f"rollout-2026-08-11T13-42-00-{current}.jsonl")
    parent = _subagent_metadata(
        thread_id=_EXEC_CHILD,
        parent_thread_id=_EXEC_SESSION,
        depth=1,
        root_session_id=_EXEC_SESSION,
        history_mode="legacy",
        originator="codex_exec",
    )
    _write(
        path,
        _forked_records(
            thread_id=current,
            parent_thread_id=_EXEC_CHILD,
            depth=2,
            parent_metadata=parent,
            root_session_id=_EXEC_SESSION,
            root_source="exec",
            history_mode="legacy",
            originator="codex_exec",
            marker=[],
        ),
    )

    assert _attest(path, environ, session_id=_EXEC_SESSION) is None


def test_exact_depth_two_forked_child_shape_attests(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    original, environ = forked_rollout
    path = original.parents[1] / "12" / f"rollout-2026-08-12T23-26-32-{_GRANDCHILD_THREAD}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = _subagent_metadata(
        thread_id=_DEPTH_TWO_PARENT,
        parent_thread_id=_SESSION,
        depth=1,
    )
    _write(
        path,
        _forked_records(
            thread_id=_GRANDCHILD_THREAD,
            parent_thread_id=_DEPTH_TWO_PARENT,
            depth=2,
            parent_metadata=parent,
            marker=[],
        ),
    )

    attestation = _attest(path, environ)

    assert isinstance(attestation, subject.CodexPlaintextSpawnAttestation)
    assert attestation.thread_id == _GRANDCHILD_THREAD
    assert attestation.ancestry_thread_ids == (
        _GRANDCHILD_THREAD,
        _DEPTH_TWO_PARENT,
    )
    assert attestation.root_session_id == _SESSION


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_parent",
        "reordered",
        "duplicate_thread",
        "current_depth_three",
        "parent_depth_two",
        "parent_root_link",
        "explicit_root_third_meta",
    ],
)
def test_depth_two_fork_requires_exact_observed_two_record_chain(
    forked_rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    original, environ = forked_rollout
    path = original.parents[1] / "12" / f"rollout-2026-08-12T23-26-32-{_GRANDCHILD_THREAD}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = _subagent_metadata(
        thread_id=_DEPTH_TWO_PARENT,
        parent_thread_id=_SESSION,
        depth=1,
    )
    records = _forked_records(
        thread_id=_GRANDCHILD_THREAD,
        parent_thread_id=_DEPTH_TWO_PARENT,
        depth=2,
        parent_metadata=parent,
        marker=[],
    )
    if mutation == "missing_parent":
        records.pop(1)
    elif mutation == "reordered":
        records[:2] = reversed(records[:2])
    elif mutation == "duplicate_thread":
        records[1]["payload"]["id"] = _GRANDCHILD_THREAD
    elif mutation == "current_depth_three":
        records[0]["payload"]["source"]["subagent"]["thread_spawn"]["depth"] = 3
    elif mutation == "parent_depth_two":
        records[1]["payload"]["source"]["subagent"]["thread_spawn"]["depth"] = 2
    elif mutation == "parent_root_link":
        records[1]["payload"]["forked_from_id"] = _CHILD_THREAD
    elif mutation == "explicit_root_third_meta":
        records.insert(2, _root_metadata())
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "thread_id",
        "root_session_id",
        "parent_thread_id",
        "forked_from_id",
        "source_parent_thread_id",
        "depth",
        "parent_id",
        "extra_source_key",
        "history_start_type",
        "history_start_null",
        "multi_agent_version",
        "top_level_agent_path",
        "third_session_meta",
        "nonleading_parent_meta",
    ],
)
def test_forked_rollout_requires_exact_thread_root_and_parent_ancestry(
    forked_rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    path, environ = forked_rollout
    records = _forked_records(marker=[])
    child = records[0]["payload"]
    parent = records[1]["payload"]
    unrelated = "019ff999-9999-7999-8999-999999999999"
    if mutation == "thread_id":
        child["id"] = unrelated
    elif mutation == "root_session_id":
        child["session_id"] = _CHILD_THREAD
    elif mutation == "parent_thread_id":
        child["parent_thread_id"] = unrelated
    elif mutation == "forked_from_id":
        child["forked_from_id"] = unrelated
    elif mutation == "source_parent_thread_id":
        child["source"]["subagent"]["thread_spawn"]["parent_thread_id"] = unrelated
    elif mutation == "depth":
        child["source"]["subagent"]["thread_spawn"]["depth"] = 2
    elif mutation == "parent_id":
        parent["id"] = unrelated
    elif mutation == "extra_source_key":
        child["source"]["forged"] = {}
    elif mutation == "history_start_type":
        child["subagent_history_start_ordinal"] = True
    elif mutation == "history_start_null":
        child["subagent_history_start_ordinal"] = None
    elif mutation == "multi_agent_version":
        child["multi_agent_version"] = "v1"
    elif mutation == "top_level_agent_path":
        child["agent_path"] = "/root/different"
    elif mutation == "third_session_meta":
        records.insert(2, _root_metadata())
    elif mutation == "nonleading_parent_meta":
        records[1:3] = [records[2], records[1]]
    _write(path, records)

    assert _attest(path, environ) is None


def test_forked_rollout_rejects_thread_identity_as_root_session_identity(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = forked_rollout
    _write(path, _forked_records(marker=[]))

    assert (
        subject.attest_codex_plaintext_spawn(
            path,
            session_id=_CHILD_THREAD,
            turn_id=_TURN,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "tui"),
        ("thread_source", "subagent"),
        ("forked_from_id", _CHILD_THREAD),
        ("parent_thread_id", _CHILD_THREAD),
    ],
)
def test_root_rollout_requires_exact_nonforked_metadata(
    rollout: tuple[Path, dict[str, str]], field: str, value: object
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    records[0]["payload"][field] = value
    _write(path, records)

    assert _attest(path, environ) is None


def test_forked_parent_record_mutation_invalidates_attestation(
    forked_rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = forked_rollout
    _write(path, _forked_records(marker=[]))
    attestation = _attest(path, environ)
    assert attestation is not None
    raw = path.read_bytes()
    assert raw.count(b'"source":"cli"') == 1
    path.write_bytes(raw.replace(b'"source":"cli"', b'"source":"tui"'))

    assert not subject.codex_plaintext_spawn_attestation_is_current(
        attestation,
        tool_input=_ARGS,
    )


@pytest.mark.parametrize("marker", [_MISSING, None, ["ciphertext"], {}, "[]"])
def test_missing_null_or_nonempty_marker_never_attests(
    rollout: tuple[Path, dict[str, str]], marker: object
) -> None:
    path, environ = rollout
    _write(path, _records(marker=marker))

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_id",
        "malformed_id",
        "extra_payload_key",
        "extra_metadata_key",
    ],
)
def test_function_call_requires_exact_observed_response_item_schema(
    rollout: tuple[Path, dict[str, str]],
    mutation: str,
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    call = records[-1]["payload"]
    if mutation == "missing_id":
        call.pop("id")
    elif mutation == "malformed_id":
        call["id"] = "fc_" + "g" * 50
    elif mutation == "extra_payload_key":
        call["delivery_mode"] = "plaintext"
    elif mutation == "extra_metadata_key":
        call["internal_chat_message_metadata_passthrough"]["future_key"] = True
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize("position", ["before", "after"])
def test_function_item_identity_must_be_unique_across_initial_snapshot(
    rollout: tuple[Path, dict[str, str]],
    position: str,
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    reused = _record(
        "response_item",
        {
            "type": "future_response_type",
            "call_id": "call_AAAAAAAAAAAAAAAAAAAAAAAA",
            "id": _FUNCTION_ITEM,
        },
    )
    if position == "before":
        records.insert(-1, reused)
    else:
        records.append(reused)
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    ("turn_id", "call_id"),
    [
        ("parent-turn", _CALL),
        (_TURN, "spawn-call-one"),
        ("019FF8EF-C6E1-7961-A682-D8AA9F11F464", _CALL),
        (_TURN, "call_" + "a" * 25),
    ],
)
def test_attestation_requires_exact_codex_turn_and_call_identity_formats(
    rollout: tuple[Path, dict[str, str]],
    turn_id: str,
    call_id: str,
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[], turn_id=turn_id, call_id=call_id))

    assert (
        subject.attest_codex_plaintext_spawn(
            path,
            session_id=_SESSION,
            turn_id=turn_id,
            tool_use_id=call_id,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )


@pytest.mark.parametrize(
    "mutation",
    [
        {"cli_version": "0.147.0-alpha.6.6"},
        {"call_id": "call_AAAAAAAAAAAAAAAAAAAAAAAA"},
        {"turn_id": "019ff8ef-c6e1-7961-a682-d8aa9f11f465"},
    ],
)
def test_version_or_correlation_drift_never_attests(
    rollout: tuple[Path, dict[str, str]], mutation: dict[str, str]
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[], **mutation))

    assert _attest(path, environ) is None


def test_observed_v4_turn_identity_remains_supported(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[], turn_id=_V4_TURN))

    assert (
        subject.attest_codex_plaintext_spawn(
            path,
            session_id=_SESSION,
            turn_id=_V4_TURN,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is not None
    )


@pytest.mark.parametrize(
    "identity",
    [
        "00000000-0000-0000-0000-000000000000",
        "123e4567-e89b-12d3-a456-426614174000",
        "019ff8ee-eb1c-7de3-015d-3deea9eca028",
    ],
)
def test_session_identity_requires_non_nil_rfc_uuid7(
    rollout: tuple[Path, dict[str, str]],
    identity: str,
) -> None:
    original, environ = rollout
    path = original.with_name(original.name.replace(_SESSION, identity))
    _write(path, _records(marker=[], session_id=identity))

    assert (
        subject.attest_codex_plaintext_spawn(
            path,
            session_id=identity,
            turn_id=_TURN,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )


@pytest.mark.parametrize(
    "turn_id",
    [
        "00000000-0000-0000-0000-000000000000",
        "123e4567-e89b-12d3-a456-426614174000",
        "550e8400-e29b-41d4-0716-446655440000",
    ],
)
def test_turn_identity_requires_non_nil_observed_rfc_uuid_version(
    rollout: tuple[Path, dict[str, str]],
    turn_id: str,
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[], turn_id=turn_id))

    assert (
        subject.attest_codex_plaintext_spawn(
            path,
            session_id=_SESSION,
            turn_id=turn_id,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )


@pytest.mark.parametrize("clock", ["T24-00-00", "T23-60-00", "T23-59-60", "T99-99-99"])
def test_rollout_filename_requires_a_valid_clock_time(
    rollout: tuple[Path, dict[str, str]],
    clock: str,
) -> None:
    original, environ = rollout
    path = original.with_name(original.name.replace("T22-23-55", clock))
    _write(path, _records(marker=[]))

    assert _attest(path, environ) is None


@pytest.mark.parametrize(
    ("month", "day_value"),
    [("8", "12"), ("08", "3"), ("8", "3")],
)
def test_rollout_path_requires_canonical_padded_date_components(
    rollout: tuple[Path, dict[str, str]],
    month: str,
    day_value: str,
) -> None:
    original, environ = rollout
    sessions = Path(environ["CODEX_HOME"]) / "sessions"
    path = (
        sessions
        / "2026"
        / month
        / day_value
        / f"rollout-2026-{month}-{day_value}T22-23-55-{_SESSION}.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, _records(marker=[]))

    assert _attest(path, environ) is None
    assert original.parent != path.parent


def test_full_arguments_and_pinned_schema_must_match(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    transcript_args = {**_ARGS, "message": "different"}
    _write(path, _records(args=transcript_args, marker=[]))
    assert _attest(path, environ) is None

    unknown = {**_ARGS, "future_field": True}
    _write(path, _records(args=unknown, marker=[]))
    assert _attest(path, environ, tool_input=unknown) is None


def test_duplicate_json_keys_and_ambiguous_calls_fail(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    _write(path, records)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            '"encrypted_function_args":[]',
            '"encrypted_function_args":[],"encrypted_function_args":[]',
        ),
        encoding="utf-8",
    )
    assert _attest(path, environ) is None

    _write(path, [*records, records[-1]])
    assert _attest(path, environ) is None


@pytest.mark.parametrize("terminal", ["function_call_output", "task_complete"])
def test_completed_or_output_call_is_stale_before_attestation(
    rollout: tuple[Path, dict[str, str]], terminal: str
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    if terminal == "function_call_output":
        records.append(_record("response_item", {"type": terminal, "call_id": _CALL}))
    else:
        records.append(_record("event_msg", {"type": terminal, "turn_id": _TURN}))
    _write(path, records)

    assert _attest(path, environ) is None


def test_unknown_same_call_response_item_fails_initial_attestation(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    records.append(_record("response_item", {"type": "future_state", "call_id": _CALL}))
    _write(path, records)

    assert _attest(path, environ) is None


@pytest.mark.parametrize("terminal", ["function_call", "function_call_output", "task_complete"])
def test_append_replay_output_or_completion_invalidates_attestation(
    rollout: tuple[Path, dict[str, str]], terminal: str
) -> None:
    path, environ = rollout
    records = _records(marker=[])
    _write(path, records)
    attestation = _attest(path, environ)
    assert attestation is not None
    appended = (
        records[-1]
        if terminal == "function_call"
        else _record(
            "response_item" if terminal == "function_call_output" else "event_msg",
            (
                {"type": terminal, "call_id": _CALL}
                if terminal == "function_call_output"
                else {"type": terminal, "turn_id": _TURN}
            ),
        )
    )
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(appended, separators=(",", ":")) + "\n")

    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_appended_unknown_same_call_response_item_invalidates_attestation(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))
    attestation = _attest(path, environ)
    assert attestation is not None
    appended = _record("response_item", {"type": "future_state", "call_id": _CALL})
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(appended, separators=(",", ":")) + "\n")

    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_appended_different_call_cannot_reuse_attested_function_item_identity(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))
    attestation = _attest(path, environ)
    assert attestation is not None
    appended = _record(
        "response_item",
        {
            "type": "future_response_type",
            "call_id": "call_AAAAAAAAAAAAAAAAAAAAAAAA",
            "id": _FUNCTION_ITEM,
        },
    )
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(appended, separators=(",", ":")) + "\n")

    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)


def test_record_mutation_and_forged_seal_are_rejected(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))
    attestation = _attest(path, environ)
    assert attestation is not None
    raw = path.read_bytes()
    original = b"Review the exact transaction boundary."
    replacement = b"Review the exact transaction boundary!"
    assert len(original) == len(replacement)
    path.write_bytes(raw.replace(original, replacement))
    assert not subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=_ARGS)
    assert not subject.codex_plaintext_spawn_attestation_is_current(
        replace(attestation, call_sha256="0" * 64), tool_input=_ARGS
    )


def test_path_escape_relative_path_hardlink_and_incomplete_record_fail(
    rollout: tuple[Path, dict[str, str]], tmp_path: Path
) -> None:
    path, environ = rollout
    _write(path, _records(marker=[]))
    assert (
        subject.attest_codex_plaintext_spawn(
            Path(path.name),
            session_id=_SESSION,
            turn_id=_TURN,
            tool_use_id=_CALL,
            tool_input=_ARGS,
            environ=environ,
        )
        is None
    )
    escaped = tmp_path / path.name
    escaped.write_bytes(path.read_bytes())
    assert _attest(escaped, environ) is None

    link = path.with_name("linked.jsonl")
    try:
        os.link(path, link)
    except OSError:
        pytest.skip("hard links are unavailable")
    try:
        assert _attest(path, environ) is None
    finally:
        link.unlink()
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    assert _attest(path, environ) is None


def test_observed_large_rollout_line_is_supported_but_argument_budget_is_bounded(
    rollout: tuple[Path, dict[str, str]],
) -> None:
    path, environ = rollout
    large = {**_ARGS, "message": "x" * (600 * 1024)}
    _write(path, _records(args=large, marker=[]))
    attestation = _attest(path, environ, tool_input=large)
    assert attestation is not None
    assert subject.codex_plaintext_spawn_attestation_is_current(attestation, tool_input=large)

    oversized = {**_ARGS, "message": "x" * (1024 * 1024)}
    _write(path, _records(args=oversized, marker=[]))
    assert _attest(path, environ, tool_input=oversized) is None
