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
    parent_sessions = [
        event
        for event in events
        if event.get("type") == "session_meta"
        and isinstance(event.get("payload"), Mapping)
        and event["payload"].get("id") == parent_session_id
    ]
    if len(parent_sessions) != 1:
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
    parent_ciphertext = _parent_followup_ciphertext(
        path,
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
    session_matches = 0
    starts: list[tuple[int, str]] = []
    completions: list[tuple[int, str]] = []
    for index, event in enumerate(events):
        event_type = event.get("type")
        event_payload = event.get("payload")
        if event_type == "session_meta" and isinstance(event_payload, dict):
            if event_payload.get("id") == normalized_worker:
                session_matches += 1
            continue
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
        session_matches != 1
        or len(starts) != 2
        or len(completions) != 2
        or starts[0][1] != completions[0][1]
        or starts[1][1] != completions[1][1]
        or starts[1][1] != normalized_turn
        or not starts[0][0] < completions[0][0] < starts[1][0] < completions[1][0]
    ):
        return False
    execution_events = events[completions[0][0] + 1 : completions[1][0] + 1]
    observed = [
        delivery
        for event in execution_events
        for delivery in _execution_deliveries(event.get("payload"))
    ]
    if observed:
        return observed == [expected]
    return _opaque_current_turn_execution_observed(
        path,
        events,
        execution_events,
        normalized_turn=normalized_turn,
        expected=expected,
        parent_session_id=parent_session_id,
        execution_tool_use_id=execution_tool_use_id,
    )


__all__ = ["codex_current_turn_execution_observed"]
