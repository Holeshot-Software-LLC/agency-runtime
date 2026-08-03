"""Link-resistant proof that one Codex child turn received its execution envelope."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.native_child_prompt_delivery import (
    CodexNativeChildExecutionDelivery,
    codex_opaque_child_message_ciphertext,
    is_codex_opaque_collaboration_message,
    parse_codex_native_child_execution_message,
)

_MAX_CODEX_CHILD_ROLLOUT_BYTES: Final[int] = 8 * 1024 * 1024
_MAX_CODEX_CHILD_ROLLOUT_LINE_BYTES: Final[int] = 512 * 1024
_MAX_CODEX_CHILD_ROLLOUT_LINES: Final[int] = 20_000


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def _execution_deliveries(value: Any) -> Iterator[CodexNativeChildExecutionDelivery]:
    for text in _strings(value):
        delivery = parse_codex_native_child_execution_message(text)
        if delivery is not None:
            yield delivery
            continue
        if not text.lstrip().startswith(("{", "[")):
            continue
        try:
            nested = safe_load_bounded_json(
                text,
                maximum_bytes=_MAX_CODEX_CHILD_ROLLOUT_LINE_BYTES,
                maximum_depth=16,
                maximum_nodes=2_000,
            )
        except (TypeError, ValueError):
            continue
        for nested_text in _strings(nested):
            nested_delivery = parse_codex_native_child_execution_message(nested_text)
            if nested_delivery is not None:
                yield nested_delivery


def _rollout_events(path: Path) -> list[dict[str, Any]] | None:
    try:
        payload = read_bounded_regular_file(
            path,
            limit=_MAX_CODEX_CHILD_ROLLOUT_BYTES,
            label="Codex child rollout",
        )
        text = payload.decode("utf-8", errors="strict")
    except (OSError, UnicodeError):
        return None
    lines = text.splitlines()
    if len(lines) > _MAX_CODEX_CHILD_ROLLOUT_LINES:
        return None
    events: list[dict[str, Any]] = []
    try:
        for line in lines:
            if not line.strip() or len(line.encode("utf-8")) > _MAX_CODEX_CHILD_ROLLOUT_LINE_BYTES:
                return None
            event = safe_load_bounded_json(
                line,
                maximum_bytes=_MAX_CODEX_CHILD_ROLLOUT_LINE_BYTES,
                maximum_depth=32,
                maximum_nodes=20_000,
            )
            if not isinstance(event, dict):
                return None
            events.append(event)
    except (TypeError, ValueError):
        return None
    return events


def _parent_rollout_directories(child_path: Path) -> tuple[Path, ...]:
    """Return the child day and its only possible prior-day rollover."""

    directories = [child_path.parent]
    try:
        child_date = date(
            int(child_path.parent.parent.parent.name),
            int(child_path.parent.parent.name),
            int(child_path.parent.name),
        )
        prior_date = child_date - timedelta(days=1)
        rollout_root = child_path.parent.parent.parent.parent
        prior_directory = (
            rollout_root
            / f"{prior_date.year:04d}"
            / f"{prior_date.month:02d}"
            / f"{prior_date.day:02d}"
        )
        if prior_directory != child_path.parent:
            directories.append(prior_directory)
    except (TypeError, ValueError):
        pass
    return tuple(directories)


def _child_rollout_directories(parent_path: Path) -> tuple[Path, ...]:
    """Return the parent day and its only possible next-day rollover."""

    directories = [parent_path.parent]
    try:
        parent_date = date(
            int(parent_path.parent.parent.parent.name),
            int(parent_path.parent.parent.name),
            int(parent_path.parent.name),
        )
        next_date = parent_date + timedelta(days=1)
        rollout_root = parent_path.parent.parent.parent.parent
        next_directory = (
            rollout_root
            / f"{next_date.year:04d}"
            / f"{next_date.month:02d}"
            / f"{next_date.day:02d}"
        )
        if next_directory != parent_path.parent:
            directories.append(next_directory)
    except (TypeError, ValueError):
        pass
    return tuple(directories)


def _parent_rollout_path(child_path: Path, parent_session_id: str) -> Path | None:
    """Resolve one exact same-run parent transcript across a date rollover."""

    candidates: list[Path] = []
    try:
        for directory in _parent_rollout_directories(child_path):
            if not directory.is_dir():
                continue
            for candidate in directory.iterdir():
                if candidate.name.startswith("rollout-") and candidate.name.endswith(
                    f"-{parent_session_id}.jsonl"
                ):
                    candidates.append(candidate)
                    if len(candidates) > 1:
                        return None
    except OSError:
        return None
    return candidates[0] if len(candidates) == 1 else None


def _child_rollout_path(parent_path: Path, worker_id: str) -> Path | None:
    """Resolve one exact child transcript across a date rollover."""

    candidates: list[Path] = []
    try:
        for directory in _child_rollout_directories(parent_path):
            if not directory.is_dir():
                continue
            for candidate in directory.iterdir():
                if candidate.name.startswith("rollout-") and candidate.name.endswith(
                    f"-{worker_id}.jsonl"
                ):
                    candidates.append(candidate)
                    if len(candidates) > 1:
                        return None
    except OSError:
        return None
    return candidates[0] if len(candidates) == 1 else None


def _parent_session_matches(
    events: list[dict[str, Any]],
    parent_session_id: str,
) -> bool:
    return (
        sum(
            1
            for event in events
            if event.get("type") == "session_meta"
            and isinstance(event.get("payload"), Mapping)
            and event["payload"].get("id") == parent_session_id
        )
        == 1
    )


def _parent_followup_ciphertext_from_events(
    events: list[dict[str, Any]],
    *,
    parent_session_id: str,
    execution_tool_use_id: str,
    expected: CodexNativeChildExecutionDelivery,
) -> str | None:
    """Recover one exact parent ciphertext from already bounded events."""

    if not _parent_session_matches(events, parent_session_id):
        return None
    messages: list[str] = []
    for event in events:
        payload = event.get("payload")
        if (
            event.get("type") != "response_item"
            or not isinstance(payload, Mapping)
            or payload.get("type") != "function_call"
            or payload.get("namespace") != "collaboration"
            or payload.get("name") != "followup_task"
            or payload.get("call_id") != execution_tool_use_id
        ):
            continue
        arguments = payload.get("arguments")
        if not isinstance(arguments, str):
            return None
        try:
            decoded = safe_load_bounded_json(
                arguments,
                maximum_bytes=_MAX_CODEX_CHILD_ROLLOUT_LINE_BYTES,
                maximum_depth=8,
                maximum_nodes=64,
            )
        except (TypeError, ValueError):
            return None
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != {"target", "message"}
            or decoded.get("target") != f"/root/{expected.native_task_name}"
            or not is_codex_opaque_collaboration_message(decoded.get("message"))
        ):
            return None
        messages.append(str(decoded["message"]))
    return messages[0] if len(messages) == 1 else None


def _parent_spawn_ciphertext_from_events(
    events: list[dict[str, Any]],
    *,
    parent_session_id: str,
    execution_tool_use_id: str,
    expected: CodexNativeChildExecutionDelivery,
) -> str | None:
    """Recover one exact first-turn spawn ciphertext from bounded parent events."""

    if not _parent_session_matches(events, parent_session_id):
        return None
    messages: list[str] = []
    for event in events:
        payload = event.get("payload")
        if (
            event.get("type") != "response_item"
            or not isinstance(payload, Mapping)
            or payload.get("type") != "function_call"
            or payload.get("namespace") != "collaboration"
            or payload.get("name") != "spawn_agent"
            or payload.get("call_id") != execution_tool_use_id
        ):
            continue
        arguments = payload.get("arguments")
        if not isinstance(arguments, str):
            return None
        try:
            decoded = safe_load_bounded_json(
                arguments,
                maximum_bytes=_MAX_CODEX_CHILD_ROLLOUT_LINE_BYTES,
                maximum_depth=8,
                maximum_nodes=64,
            )
        except (TypeError, ValueError):
            return None
        if (
            not isinstance(decoded, Mapping)
            or set(decoded) != {"fork_turns", "message", "task_name"}
            or decoded.get("fork_turns") != "none"
            or decoded.get("task_name") != expected.native_task_name
            or not is_codex_opaque_collaboration_message(decoded.get("message"))
        ):
            return None
        messages.append(str(decoded["message"]))
    return messages[0] if len(messages) == 1 else None


def _parent_followup_ciphertext(
    child_path: Path,
    *,
    parent_session_id: str,
    execution_tool_use_id: str,
    expected: CodexNativeChildExecutionDelivery,
) -> str | None:
    """Recover one exact parent ciphertext without retaining it as evidence."""

    parent_path = _parent_rollout_path(child_path, parent_session_id)
    if parent_path is None:
        return None
    events = _rollout_events(parent_path)
    if events is None:
        return None
    return _parent_followup_ciphertext_from_events(
        events,
        parent_session_id=parent_session_id,
        execution_tool_use_id=execution_tool_use_id,
        expected=expected,
    )


def _parent_spawn_ciphertext(
    child_path: Path,
    *,
    parent_session_id: str,
    execution_tool_use_id: str,
    expected: CodexNativeChildExecutionDelivery,
) -> str | None:
    """Recover one exact first-turn spawn ciphertext without retaining it."""

    parent_path = _parent_rollout_path(child_path, parent_session_id)
    if parent_path is None:
        return None
    events = _rollout_events(parent_path)
    if events is None:
        return None
    return _parent_spawn_ciphertext_from_events(
        events,
        parent_session_id=parent_session_id,
        execution_tool_use_id=execution_tool_use_id,
        expected=expected,
    )


def _child_lineage_matches(
    events: list[dict[str, Any]],
    *,
    parent_session_id: str,
    expected: CodexNativeChildExecutionDelivery,
) -> bool:
    """Require the opaque child transcript to retain its exact parent lineage."""

    matches = 0
    for event in events:
        payload = event.get("payload")
        if event.get("type") != "session_meta" or not isinstance(payload, Mapping):
            continue
        source = payload.get("source")
        subagent = source.get("subagent") if isinstance(source, Mapping) else None
        spawn = subagent.get("thread_spawn") if isinstance(subagent, Mapping) else None
        if (
            isinstance(spawn, Mapping)
            and spawn.get("parent_thread_id") == parent_session_id
            and spawn.get("agent_path") == f"/root/{expected.native_task_name}"
        ):
            matches += 1
    return matches == 1


def _opaque_current_turn_execution_observed(
    path: Path,
    events: list[dict[str, Any]],
    execution_events: list[dict[str, Any]],
    *,
    normalized_turn: str,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object,
    execution_tool_use_id: object,
    parent_events: list[dict[str, Any]] | None = None,
) -> bool:
    """Match the exact parent and child ciphertext without retaining either."""

    try:
        normalized_parent = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        normalized_tool_use = validate_correlation_id(
            execution_tool_use_id,
            field="execution_tool_use_id",
        )
    except ValueError:
        return False
    if not _child_lineage_matches(
        events,
        parent_session_id=normalized_parent,
        expected=expected,
    ):
        return False
    if parent_events is None:
        parent_ciphertext = _parent_followup_ciphertext(
            path,
            parent_session_id=normalized_parent,
            execution_tool_use_id=normalized_tool_use,
            expected=expected,
        )
    else:
        parent_ciphertext = _parent_followup_ciphertext_from_events(
            parent_events,
            parent_session_id=normalized_parent,
            execution_tool_use_id=normalized_tool_use,
            expected=expected,
        )
    if parent_ciphertext is None:
        return False
    child_ciphertexts = [
        ciphertext
        for event in execution_events
        if event.get("type") == "response_item"
        for ciphertext in (
            codex_opaque_child_message_ciphertext(
                event.get("payload"),
                native_task_name=expected.native_task_name,
                turn_id=normalized_turn,
            ),
        )
        if ciphertext is not None
    ]
    return child_ciphertexts == [parent_ciphertext]


def _two_turn_boundaries(
    events: list[dict[str, Any]],
    *,
    expected_execution_turn: str = "",
) -> tuple[int, int, int, int, str] | None:
    starts: list[tuple[int, str]] = []
    completions: list[tuple[int, str]] = []
    for index, event in enumerate(events):
        event_type = event.get("type")
        event_payload = event.get("payload")
        if (
            event_type == "event_msg"
            and isinstance(event_payload, dict)
            and event_payload.get("type") == "task_started"
        ):
            candidate_turn = str(event_payload.get("turn_id") or "").strip()
            if candidate_turn:
                starts.append((index, candidate_turn))
        if (
            event_type == "event_msg"
            and isinstance(event_payload, dict)
            and event_payload.get("type") == "task_complete"
        ):
            candidate_turn = str(event_payload.get("turn_id") or "").strip()
            if candidate_turn:
                completions.append((index, candidate_turn))
    if (
        len(starts) != 2
        or len(completions) != 2
        or starts[0][1] != completions[0][1]
        or starts[1][1] != completions[1][1]
        or (expected_execution_turn and starts[1][1] != expected_execution_turn)
        or not starts[0][0] < completions[0][0] < starts[1][0] < completions[1][0]
    ):
        return None
    return (
        starts[0][0],
        completions[0][0],
        starts[1][0],
        completions[1][0],
        starts[1][1],
    )


def _one_turn_boundaries(
    events: list[dict[str, Any]],
    *,
    expected_turn: str = "",
) -> tuple[int, int, str] | None:
    """Return one unambiguous started/completed child turn."""

    starts: list[tuple[int, str]] = []
    completions: list[tuple[int, str]] = []
    for index, event in enumerate(events):
        event_type = event.get("type")
        event_payload = event.get("payload")
        if (
            event_type == "event_msg"
            and isinstance(event_payload, Mapping)
            and event_payload.get("type") == "task_started"
        ):
            turn = str(event_payload.get("turn_id") or "").strip()
            if turn:
                starts.append((index, turn))
        if (
            event_type == "event_msg"
            and isinstance(event_payload, Mapping)
            and event_payload.get("type") == "task_complete"
        ):
            turn = str(event_payload.get("turn_id") or "").strip()
            if turn:
                completions.append((index, turn))
    if (
        len(starts) != 1
        or len(completions) != 1
        or starts[0][1] != completions[0][1]
        or (expected_turn and starts[0][1] != expected_turn)
        or starts[0][0] >= completions[0][0]
    ):
        return None
    return starts[0][0], completions[0][0], starts[0][1]


def _resolved_workspace_root(workspace_root: object) -> Path | None:
    raw_root = str(workspace_root or "").strip()
    if not raw_root:
        return None
    try:
        root = Path(raw_root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    return root if root.is_dir() else None


def _exact_turn_span(events: list[dict[str, Any]], turn_id: str) -> tuple[int, int] | None:
    """Return one exact started/completed span from a possibly multi-turn rollout."""

    starts: list[int] = []
    completions: list[int] = []
    for index, event in enumerate(events):
        payload = event.get("payload")
        if event.get("type") != "event_msg" or not isinstance(payload, Mapping):
            continue
        if payload.get("turn_id") != turn_id:
            continue
        if payload.get("type") == "task_started":
            starts.append(index)
        elif payload.get("type") == "task_complete":
            completions.append(index)
    if len(starts) != 1 or len(completions) != 1 or starts[0] >= completions[0]:
        return None
    return starts[0], completions[0]


def _patch_changes_are_workspace_local(changes: object, root: Path) -> bool:
    if not isinstance(changes, Mapping) or not changes:
        return False
    changed_paths: list[Path] = []
    try:
        for raw_path in changes:
            if not isinstance(raw_path, str) or not raw_path.strip():
                return False
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = root / candidate
            changed_paths.append(candidate.resolve(strict=False))
        return bool(
            changed_paths
            and all(path != root and path.is_relative_to(root) for path in changed_paths)
        )
    except (OSError, RuntimeError, ValueError):
        return False


def _workspace_write_observed_from_events(
    events: list[dict[str, Any]],
    *,
    turn_id: str,
    workspace_root: object,
) -> bool:
    """Require one successful Codex patch whose every changed path stays in the workspace."""

    root = _resolved_workspace_root(workspace_root)
    span = _exact_turn_span(events, turn_id)
    if root is None or span is None:
        return False

    for event in events[span[0] + 1 : span[1]]:
        payload = event.get("payload")
        if (
            event.get("type") != "event_msg"
            or not isinstance(payload, Mapping)
            or payload.get("type") != "patch_apply_end"
            or payload.get("turn_id") != turn_id
            or payload.get("success") is not True
            or payload.get("status") != "completed"
            or not isinstance(payload.get("call_id"), str)
            or not str(payload["call_id"]).strip()
        ):
            continue
        if _patch_changes_are_workspace_local(payload.get("changes"), root):
            return True
    return False


def codex_current_turn_workspace_write_observed(
    transcript_path: object,
    *,
    turn_id: object,
    worker_id: object,
    workspace_root: object,
) -> bool:
    """Prove a successful workspace-local patch in one exact Codex child turn."""

    try:
        normalized_turn = validate_correlation_id(turn_id, field="turn_id")
        normalized_worker = validate_correlation_id(worker_id, field="worker_id")
    except ValueError:
        return False
    raw_path = str(transcript_path or "").strip()
    if not raw_path:
        return False
    path = Path(raw_path)
    if (
        not path.is_absolute()
        or path.suffix.casefold() != ".jsonl"
        or not path.name.endswith(f"-{normalized_worker}.jsonl")
    ):
        return False
    events = _rollout_events(path)
    if events is None:
        return False
    session_matches = sum(
        1
        for event in events
        if event.get("type") == "session_meta"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("id") == normalized_worker
    )
    return bool(
        session_matches == 1
        and _workspace_write_observed_from_events(
            events,
            turn_id=normalized_turn,
            workspace_root=workspace_root,
        )
    )


def _initial_turn_execution_observed_from_events(
    path: Path,
    events: list[dict[str, Any]],
    boundaries: tuple[int, int, str],
    *,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object,
    execution_tool_use_id: object,
    parent_events: list[dict[str, Any]] | None = None,
    execution_event_limit: int | None = None,
) -> bool:
    """Match one exact parent spawn ciphertext to the child's first turn."""

    start, completion, turn = boundaries
    try:
        normalized_parent = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        normalized_tool_use = validate_correlation_id(
            execution_tool_use_id,
            field="execution_tool_use_id",
        )
    except ValueError:
        return False
    if not _child_lineage_matches(
        events,
        parent_session_id=normalized_parent,
        expected=expected,
    ):
        return False
    if parent_events is None:
        parent_ciphertext = _parent_spawn_ciphertext(
            path,
            parent_session_id=normalized_parent,
            execution_tool_use_id=normalized_tool_use,
            expected=expected,
        )
    else:
        parent_ciphertext = _parent_spawn_ciphertext_from_events(
            parent_events,
            parent_session_id=normalized_parent,
            execution_tool_use_id=normalized_tool_use,
            expected=expected,
        )
    if parent_ciphertext is None:
        return False
    event_end = completion + 1
    if execution_event_limit is not None:
        event_end = min(event_end, execution_event_limit)
    child_ciphertexts = [
        ciphertext
        for event in events[start + 1 : event_end]
        if event.get("type") == "response_item"
        for ciphertext in (
            codex_opaque_child_message_ciphertext(
                event.get("payload"),
                native_task_name=expected.native_task_name,
                turn_id=turn,
            ),
        )
        if ciphertext is not None
    ]
    return child_ciphertexts == [parent_ciphertext]


def _current_turn_execution_observed_from_events(
    path: Path,
    events: list[dict[str, Any]],
    boundaries: tuple[int, int, int, int, str],
    *,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object,
    execution_tool_use_id: object,
    parent_events: list[dict[str, Any]] | None = None,
    execution_event_start: int | None = None,
    execution_event_limit: int | None = None,
) -> bool:
    _first_start, first_completion, _execution_start, execution_completion, turn = boundaries
    execution_begin = first_completion + 1
    if execution_event_start is not None:
        execution_begin = max(execution_begin, execution_event_start)
    execution_end = execution_completion + 1
    if execution_event_limit is not None:
        execution_end = min(execution_end, execution_event_limit)
    execution_events = events[execution_begin:execution_end]
    observed = [
        delivery
        for event in execution_events
        for delivery in _execution_deliveries(event.get("payload"))
    ]
    if observed:
        return observed == [expected] and bool(observed[0].goal)
    return _opaque_current_turn_execution_observed(
        path,
        events,
        execution_events,
        normalized_turn=turn,
        expected=expected,
        parent_session_id=parent_session_id,
        execution_tool_use_id=execution_tool_use_id,
        parent_events=parent_events,
    )


def _completed_execution_response_index(
    events: list[dict[str, Any]],
    boundaries: tuple[int, int, int, int, str],
) -> int | None:
    """Require one nonempty, turn-bound final answer before task completion."""

    _first_start, _first_completion, execution_start, execution_completion, turn = boundaries
    final_payloads: list[tuple[int, Mapping[str, Any]]] = []
    for index in range(execution_start + 1, execution_completion):
        event = events[index]
        payload = event.get("payload")
        if (
            event.get("type") == "response_item"
            and isinstance(payload, Mapping)
            and payload.get("type") == "message"
            and payload.get("role") == "assistant"
            and payload.get("phase") == "final_answer"
        ):
            final_payloads.append((index, payload))
    if len(final_payloads) != 1:
        return None
    final_index, final_payload = final_payloads[0]
    passthrough = final_payload.get("internal_chat_message_metadata_passthrough")
    content = final_payload.get("content")
    if (
        not isinstance(final_payload.get("id"), str)
        or not str(final_payload["id"]).strip()
        or not isinstance(passthrough, Mapping)
        or passthrough.get("turn_id") != turn
        or not isinstance(content, list)
        or len(content) != 1
        or not isinstance(content[0], Mapping)
        or content[0].get("type") != "output_text"
        or not isinstance(content[0].get("text"), str)
        or not str(content[0]["text"]).strip()
    ):
        return None
    completion = events[execution_completion].get("payload")
    if not isinstance(completion, Mapping):
        return None
    completion_message = completion.get("last_agent_message")
    if not (
        completion.get("error") is None
        and isinstance(completion_message, str)
        and completion_message.strip() != ""
        and completion_message == content[0]["text"]
    ):
        return None
    return final_index


def _completed_initial_response_index(
    events: list[dict[str, Any]],
    boundaries: tuple[int, int, str],
) -> int | None:
    """Require one nonempty final answer before the initial turn completes."""

    start, completion, turn = boundaries
    final_payloads: list[tuple[int, Mapping[str, Any]]] = []
    for index in range(start + 1, completion):
        event = events[index]
        payload = event.get("payload")
        if (
            event.get("type") == "response_item"
            and isinstance(payload, Mapping)
            and payload.get("type") == "message"
            and payload.get("role") == "assistant"
            and payload.get("phase") == "final_answer"
        ):
            final_payloads.append((index, payload))
    if len(final_payloads) != 1:
        return None
    final_index, final_payload = final_payloads[0]
    passthrough = final_payload.get("internal_chat_message_metadata_passthrough")
    content = final_payload.get("content")
    if (
        not isinstance(final_payload.get("id"), str)
        or not str(final_payload["id"]).strip()
        or not isinstance(passthrough, Mapping)
        or passthrough.get("turn_id") != turn
        or not isinstance(content, list)
        or len(content) != 1
        or not isinstance(content[0], Mapping)
        or content[0].get("type") != "output_text"
        or not isinstance(content[0].get("text"), str)
        or not str(content[0]["text"]).strip()
    ):
        return None
    completion_payload = events[completion].get("payload")
    if not isinstance(completion_payload, Mapping):
        return None
    completion_message = completion_payload.get("last_agent_message")
    if not (
        completion_payload.get("error") is None
        and isinstance(completion_message, str)
        and completion_message.strip()
        and completion_message == content[0]["text"]
    ):
        return None
    return final_index


def codex_initial_turn_execution_observed(
    transcript_path: object,
    *,
    turn_id: object,
    worker_id: object,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object,
    execution_tool_use_id: object,
) -> bool:
    """Prove that one Codex child's exact spawn message ran in its first turn."""

    if not isinstance(expected, CodexNativeChildExecutionDelivery):
        raise TypeError("expected must be a CodexNativeChildExecutionDelivery")
    try:
        normalized_turn = validate_correlation_id(turn_id, field="turn_id")
        normalized_worker = validate_correlation_id(worker_id, field="worker_id")
    except ValueError:
        return False
    raw_path = str(transcript_path or "").strip()
    if not raw_path:
        return False
    path = Path(raw_path)
    if (
        not path.is_absolute()
        or path.suffix.casefold() != ".jsonl"
        or not path.name.endswith(f"-{normalized_worker}.jsonl")
    ):
        return False
    events = _rollout_events(path)
    if events is None:
        return False
    session_matches = sum(
        1
        for event in events
        if event.get("type") == "session_meta"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("id") == normalized_worker
    )
    boundaries = _one_turn_boundaries(events, expected_turn=normalized_turn)
    return bool(
        session_matches == 1
        and boundaries is not None
        and _initial_turn_execution_observed_from_events(
            path,
            events,
            boundaries,
            expected=expected,
            parent_session_id=parent_session_id,
            execution_tool_use_id=execution_tool_use_id,
        )
    )


def codex_initial_turn_execution_completion_observed(
    parent_transcript_path: object,
    *,
    worker_id: object,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object,
    execution_tool_use_id: object,
    require_workspace_write: bool = False,
    workspace_root: object = "",
) -> bool:
    """Prove one completed Codex initial execution turn from its parent transcript."""

    if not isinstance(expected, CodexNativeChildExecutionDelivery):
        raise TypeError("expected must be a CodexNativeChildExecutionDelivery")
    try:
        normalized_parent = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        normalized_worker = validate_correlation_id(worker_id, field="worker_id")
        normalized_tool_use = validate_correlation_id(
            execution_tool_use_id,
            field="execution_tool_use_id",
        )
    except ValueError:
        return False
    raw_path = str(parent_transcript_path or "").strip()
    if not raw_path:
        return False
    parent_path = Path(raw_path)
    if (
        not parent_path.is_absolute()
        or parent_path.suffix.casefold() != ".jsonl"
        or not parent_path.name.endswith(f"-{normalized_parent}.jsonl")
    ):
        return False
    parent_events = _rollout_events(parent_path)
    if parent_events is None or not _parent_session_matches(parent_events, normalized_parent):
        return False
    child_path = _child_rollout_path(parent_path, normalized_worker)
    if child_path is None or _parent_rollout_path(child_path, normalized_parent) != parent_path:
        return False
    child_events = _rollout_events(child_path)
    if child_events is None:
        return False
    session_matches = sum(
        1
        for event in child_events
        if event.get("type") == "session_meta"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("id") == normalized_worker
    )
    boundaries = _one_turn_boundaries(child_events)
    if session_matches != 1 or boundaries is None:
        return False
    try:
        validate_correlation_id(boundaries[2], field="execution_turn_id")
    except ValueError:
        return False
    response_index = _completed_initial_response_index(child_events, boundaries)
    return bool(
        response_index is not None
        and _initial_turn_execution_observed_from_events(
            child_path,
            child_events,
            boundaries,
            expected=expected,
            parent_session_id=normalized_parent,
            execution_tool_use_id=normalized_tool_use,
            parent_events=parent_events,
            execution_event_limit=response_index,
        )
        and (
            not require_workspace_write
            or _workspace_write_observed_from_events(
                child_events,
                turn_id=boundaries[2],
                workspace_root=workspace_root,
            )
        )
    )


def codex_current_turn_execution_observed(
    transcript_path: object,
    *,
    turn_id: object,
    worker_id: object,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object = "",
    execution_tool_use_id: object = "",
) -> bool:
    """Return whether the exact current child turn contains its one execution message."""

    if not isinstance(expected, CodexNativeChildExecutionDelivery):
        raise TypeError("expected must be a CodexNativeChildExecutionDelivery")
    try:
        normalized_turn = validate_correlation_id(turn_id, field="turn_id")
        normalized_worker = validate_correlation_id(worker_id, field="worker_id")
    except ValueError:
        return False
    raw_path = str(transcript_path or "").strip()
    if not raw_path:
        return False
    path = Path(raw_path)
    if (
        not path.is_absolute()
        or path.suffix.casefold() != ".jsonl"
        or not path.name.endswith(f"-{normalized_worker}.jsonl")
    ):
        return False
    events = _rollout_events(path)
    if events is None:
        return False
    session_matches = sum(
        1
        for event in events
        if event.get("type") == "session_meta"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("id") == normalized_worker
    )
    boundaries = _two_turn_boundaries(
        events,
        expected_execution_turn=normalized_turn,
    )
    if session_matches != 1 or boundaries is None:
        return False
    return _current_turn_execution_observed_from_events(
        path,
        events,
        boundaries,
        expected=expected,
        parent_session_id=parent_session_id,
        execution_tool_use_id=execution_tool_use_id,
    )


def codex_child_execution_completion_observed(
    parent_transcript_path: object,
    *,
    worker_id: object,
    expected: CodexNativeChildExecutionDelivery,
    parent_session_id: object,
    execution_tool_use_id: object,
    require_workspace_write: bool = False,
    workspace_root: object = "",
) -> bool:
    """Prove one completed Codex follow-up turn from the exact parent transcript."""

    if not isinstance(expected, CodexNativeChildExecutionDelivery):
        raise TypeError("expected must be a CodexNativeChildExecutionDelivery")
    try:
        normalized_parent = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        normalized_worker = validate_correlation_id(worker_id, field="worker_id")
        normalized_tool_use = validate_correlation_id(
            execution_tool_use_id,
            field="execution_tool_use_id",
        )
    except ValueError:
        return False
    raw_path = str(parent_transcript_path or "").strip()
    if not raw_path:
        return False
    parent_path = Path(raw_path)
    if (
        not parent_path.is_absolute()
        or parent_path.suffix.casefold() != ".jsonl"
        or not parent_path.name.endswith(f"-{normalized_parent}.jsonl")
    ):
        return False
    parent_events = _rollout_events(parent_path)
    if parent_events is None or not _parent_session_matches(
        parent_events,
        normalized_parent,
    ):
        return False
    child_path = _child_rollout_path(parent_path, normalized_worker)
    if child_path is None or _parent_rollout_path(child_path, normalized_parent) != parent_path:
        return False
    child_events = _rollout_events(child_path)
    if child_events is None:
        return False
    session_matches = sum(
        1
        for event in child_events
        if event.get("type") == "session_meta"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("id") == normalized_worker
    )
    boundaries = _two_turn_boundaries(child_events)
    if (
        session_matches != 1
        or boundaries is None
        or not _child_lineage_matches(
            child_events,
            parent_session_id=normalized_parent,
            expected=expected,
        )
    ):
        return False
    try:
        validate_correlation_id(boundaries[4], field="execution_turn_id")
    except ValueError:
        return False
    response_index = _completed_execution_response_index(child_events, boundaries)
    if response_index is None:
        return False
    return _current_turn_execution_observed_from_events(
        child_path,
        child_events,
        boundaries,
        expected=expected,
        parent_session_id=normalized_parent,
        execution_tool_use_id=normalized_tool_use,
        parent_events=parent_events,
        execution_event_start=boundaries[2] + 1,
        execution_event_limit=response_index,
    ) and (
        not require_workspace_write
        or _workspace_write_observed_from_events(
            child_events,
            turn_id=boundaries[4],
            workspace_root=workspace_root,
        )
    )


__all__ = [
    "codex_child_execution_completion_observed",
    "codex_current_turn_execution_observed",
    "codex_current_turn_workspace_write_observed",
    "codex_initial_turn_execution_completion_observed",
    "codex_initial_turn_execution_observed",
]
