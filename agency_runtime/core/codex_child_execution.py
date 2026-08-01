"""Link-resistant proof that one Codex child turn received its execution envelope."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.native_child_prompt_delivery import (
    CodexNativeChildExecutionDelivery,
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


def codex_current_turn_execution_observed(
    transcript_path: object,
    *,
    turn_id: object,
    worker_id: object,
    expected: CodexNativeChildExecutionDelivery,
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
    observed = [
        delivery
        for event in events[completions[0][0] + 1 : completions[1][0] + 1]
        for delivery in _execution_deliveries(event.get("payload"))
    ]
    return observed == [expected]


__all__ = ["codex_current_turn_execution_observed"]
