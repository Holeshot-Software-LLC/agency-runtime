"""Native Codex and Claude Code hook protocol bridge.

Both hosts send one JSON object on stdin.  This module translates their
documented event fields into the shared adapter operations without depending on
a shell, transcript parsing, or host-private Python APIs.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, BinaryIO, TextIO

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.store.sqlite import Store

MAX_HOOK_INPUT_BYTES = 1_048_576
MAX_HOOK_OUTPUT_BYTES = 65_536
MAX_CONTEXT_CHARS = 48_000

_CODEX_EVENTS = {
    "SessionStart",
    "SubagentStart",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStop",
    "Stop",
}
_CLAUDE_EVENTS = {
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PostToolUseFailure",
    "SubagentStart",
    "SubagentStop",
    "Stop",
    "PreCompact",
    "PostCompact",
    "SessionEnd",
}
_INTERNAL_CONTINUATION_MARKERS = (
    "agency header invalid:",
    "your response is missing or has malformed agency header fields:",
    "delegation opportunity was detected",
    "agency header does not match recorded evidence",
)


class HookInputError(ValueError):
    """Raised when a host hook envelope violates the documented shape."""


@dataclass(frozen=True)
class HookCorrelation:
    """Stable correlation passed through every shared adapter operation."""

    session_id: str
    turn_id: str
    work_unit_id: str
    model: str
    tool_use_id: str

    @property
    def trace_id(self) -> str:
        # A session is not a turn. Falling back to it would falsely correlate
        # unrelated turns; callers without a turn/tool id remain uncorrelated.
        return self.turn_id or self.tool_use_id


def _optional_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise HookInputError(f"{key} must be a string or null")
    return value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = _optional_string(payload, key)
    if not value:
        raise HookInputError(f"{key} is required")
    return value


def _optional_bool(payload: dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise HookInputError(f"{key} must be a boolean")
    return value


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _first_string(mapping: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _response_work_unit(response: Any) -> str:
    if not isinstance(response, dict):
        return ""
    return _first_string(
        response,
        "work_unit_id",
        "workUnitId",
        "task_id",
        "taskId",
        "agentId",
        "agent_id",
    )


def _is_internal_continuation(prompt: str) -> bool:
    normalized = prompt.strip().casefold()
    return any(marker in normalized for marker in _INTERNAL_CONTINUATION_MARKERS)


def _canonical_tool_call(
    host: str,
    tool_name: str,
    tool_input: Any,
    tool_response: Any,
) -> tuple[str, dict[str, Any]]:
    """Map documented native tool names to BaseAdapter evidence names."""
    args = _dict_or_empty(tool_input)
    lowered = tool_name.casefold().replace("-", "_")
    suffix = lowered.rsplit("__", 1)[-1].rsplit(".", 1)[-1]

    if suffix in {"skill", "skill_view"}:
        return "skill_view", {
            **args,
            "name": _first_string(args, "name", "skill", "command"),
        }
    if suffix in {"agency_agents_load", "agency_agents_inspect"}:
        return suffix, args
    if suffix in {
        "agency_agents_delegate",
        "delegate_task",
        "delegate_async",
        "spawn_agent",
        "followup_task",
    } or (host == "claude" and tool_name == "Agent"):
        work_unit_id = _first_string(args, "work_unit_id", "workUnitId", "task_id", "taskId")
        work_unit_id = work_unit_id or _response_work_unit(tool_response)
        normalized = {
            **args,
            "agent": _first_string(
                args,
                "agent",
                "slug",
                "recommended_agent",
                "subagent_type",
                "task_name",
                "target",
            ),
            "goal": _first_string(args, "goal", "task", "prompt", "description", "message"),
            "work_unit_id": work_unit_id,
        }
        return (
            "agency_agents_delegate" if suffix == "agency_agents_delegate" else "delegate_task",
            normalized,
        )
    return tool_name, args


class HookBridge:
    """Translate one native hook event to a host adapter operation."""

    def __init__(
        self, host: str, *, store: Store | None = None, adapter: Any | None = None
    ) -> None:
        normalized_host = host.strip().casefold()
        if normalized_host not in {"codex", "claude"}:
            raise ValueError(f"unsupported hook host: {host}")
        self.host = normalized_host
        self.store = store if store is not None else Store()
        self.adapter = adapter or self._new_adapter()

    def _new_adapter(self) -> Any:
        if self.host == "codex":
            from agency_runtime.adapters.codex.wrapper import CodexAdapter

            return CodexAdapter(store=self.store)
        from agency_runtime.adapters.claude.wrapper import ClaudeAdapter

        return ClaudeAdapter(store=self.store)

    def _event_name(self, payload: dict[str, Any]) -> str:
        event = _required_string(payload, "hook_event_name")
        supported = _CODEX_EVENTS if self.host == "codex" else _CLAUDE_EVENTS
        if event not in supported:
            raise HookInputError(f"unsupported {self.host} hook event: {event}")
        return event

    def _correlation(
        self, payload: dict[str, Any], tool_input: Any = None, tool_response: Any = None
    ) -> HookCorrelation:
        args = _dict_or_empty(tool_input)
        session_id = _required_string(payload, "session_id")
        turn_id = _optional_string(payload, "turn_id")
        tool_use_id = _optional_string(payload, "tool_use_id")
        model = _optional_string(payload, "model")
        work_unit_id = _first_string(
            args,
            "work_unit_id",
            "workUnitId",
            "task_id",
            "taskId",
        )
        work_unit_id = work_unit_id or _optional_string(payload, "agent_id")
        work_unit_id = work_unit_id or _response_work_unit(tool_response) or tool_use_id
        return HookCorrelation(session_id, turn_id, work_unit_id, model, tool_use_id)

    def _unambiguous_open_trace(self, session_id: str) -> str:
        """Recover one open routed turn when a host omits native turn IDs.

        Claude's documented hook envelope does not guarantee a ``turn_id``.
        Falling back to the session ID would merge unrelated turns, while
        dropping correlation makes response finalization and live-canary
        evidence impossible.  A recent routing trace is therefore reused only
        when exactly one trace for this session has not been finalized yet.
        Ambiguous or unavailable history remains deliberately uncorrelated.
        """

        recent_activity = getattr(self.store, "recent_runtime_activity", None)
        if not callable(recent_activity) or not session_id:
            return ""
        try:
            activity = recent_activity(limit=200)
        except Exception:
            return ""
        if not isinstance(activity, dict):
            return ""
        finalized = {
            str(row.get("trace_id"))
            for row in activity.get("finalizations", [])
            if isinstance(row, dict) and row.get("trace_id")
        }
        open_traces = {
            str(row.get("trace_id"))
            for row in activity.get("routing", [])
            if isinstance(row, dict)
            and row.get("session_id") == session_id
            and row.get("trace_id")
            and str(row.get("trace_id")) not in finalized
        }
        return next(iter(open_traces)) if len(open_traces) == 1 else ""

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise HookInputError("hook input must be a JSON object")
        event = self._event_name(payload)

        if event == "UserPromptSubmit":
            prompt = _required_string(payload, "prompt")
            if _is_internal_continuation(prompt):
                return {}
            correlation = self._correlation(payload)
            result = self.adapter.pre_llm_call_handler(
                session_id=correlation.session_id,
                user_message=prompt,
                model=correlation.model,
                trace_id=correlation.trace_id,
            )
            context = result.get("context") if isinstance(result, dict) else None
            if not isinstance(context, str) or not context:
                return {}
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context[:MAX_CONTEXT_CHARS],
                }
            }

        if event in {"PostToolUse", "PostToolUseFailure"}:
            tool_name = _required_string(payload, "tool_name")
            tool_input = payload.get("tool_input")
            tool_response = payload.get("tool_response")
            if event == "PostToolUseFailure":
                tool_response = {
                    "status": "failed",
                    "error": _required_string(payload, "error"),
                    "is_interrupt": _optional_bool(payload, "is_interrupt"),
                }
            correlation = self._correlation(payload, tool_input, tool_response)
            canonical_name, canonical_args = _canonical_tool_call(
                self.host,
                tool_name,
                tool_input,
                tool_response,
            )
            if correlation.work_unit_id and not _first_string(
                canonical_args, "work_unit_id", "workUnitId"
            ):
                canonical_args["work_unit_id"] = correlation.work_unit_id
            self.adapter.post_tool_call_handler(
                tool_name=canonical_name,
                args=canonical_args,
                result=tool_response,
                session_id=correlation.session_id,
                trace_id=correlation.trace_id,
                turn_id=correlation.turn_id,
                work_unit_id=correlation.work_unit_id,
                model=correlation.model,
                tool_use_id=correlation.tool_use_id,
            )
            return {}

        if event == "Stop":
            correlation = self._correlation(payload)
            if _optional_bool(payload, "stop_hook_active"):
                return {}
            final_response = _optional_string(payload, "last_assistant_message")
            if not final_response:
                return {}
            verification = self.adapter.pre_verify_handler(
                final_response,
                session_id=correlation.session_id,
                model=correlation.model,
                attempt=0,
            )
            trace_id = correlation.trace_id or self._unambiguous_open_trace(correlation.session_id)
            if isinstance(verification, dict) and verification.get("action") == "continue":
                reason = str(
                    verification.get("message")
                    or "Agency Runtime evidence verification requires another pass."
                )
                self._record_finalization(trace_id, "continue")
                return {"decision": "block", "reason": reason[:MAX_CONTEXT_CHARS]}
            self._record_finalization(trace_id, "accept")
            return {}

        # Session, pre-tool, compaction, permission, and subagent lifecycle
        # events intentionally have no side effect in the shared boundary yet.
        return {}

    def _record_finalization(self, trace_id: str, action: str) -> None:
        if not trace_id:
            return
        try:
            self.store.record_finalization(
                trace_id=trace_id,
                host=self.host,
                action=action,
                missing=[],
            )
        except Exception:
            # Evidence persistence must not break the host's response path.
            return


def _write_output(stream: BinaryIO | TextIO, payload: dict[str, Any]) -> None:
    try:
        encoded = (
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError):
        encoded = b"{}\n"
    if len(encoded) > MAX_HOOK_OUTPUT_BYTES:
        encoded = b"{}\n"
    try:
        stream.write(encoded)  # type: ignore[arg-type]
    except TypeError:
        stream.write(encoded.decode("utf-8"))  # type: ignore[arg-type]
    stream.flush()


def run_hook_stdio(
    host: str,
    *,
    store: Store | None = None,
    input_stream: BinaryIO | TextIO | None = None,
    output_stream: BinaryIO | TextIO | None = None,
    error_stream: TextIO | None = None,
) -> int:
    """Read one bounded event, emit one JSON object, and always fail open."""
    source = input_stream or sys.stdin.buffer
    sink = output_stream or sys.stdout.buffer
    errors = error_stream or sys.stderr

    try:
        raw = source.read(MAX_HOOK_INPUT_BYTES + 1)
        raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
        if len(raw_bytes) > MAX_HOOK_INPUT_BYTES:
            raise HookInputError("hook input exceeds the size limit")
        payload = safe_load_bounded_json(raw_bytes)
        if not isinstance(payload, dict):
            raise HookInputError("hook input must be one JSON object")
        result = HookBridge(host, store=store).handle(payload)
        if not isinstance(result, dict):
            raise RuntimeError("hook bridge returned a non-object result")
    except (
        HookInputError,
        BoundedJSONError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"agency hook {host}: {exc}; host operation continues", file=errors)
        result = {}
    except Exception as exc:  # Defensive boundary around adapters and storage.
        print(
            f"agency hook {host}: {type(exc).__name__}; host operation continues",
            file=errors,
        )
        result = {}

    _write_output(sink, result)
    return 0


__all__ = [
    "MAX_HOOK_INPUT_BYTES",
    "MAX_HOOK_OUTPUT_BYTES",
    "HookBridge",
    "HookCorrelation",
    "HookInputError",
    "run_hook_stdio",
]
