"""Native Codex and Claude Code hook protocol bridge.

Both hosts send one JSON object on stdin.  This module translates their
documented event fields into the shared adapter operations without depending on
a shell, transcript parsing, or host-private Python APIs.
"""

from __future__ import annotations

import json
import re
import sys
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, BinaryIO, TextIO
from uuid import UUID, uuid4

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation.native_labels import (
    codex_task_name_for_work_unit,
    internal_work_unit_from_codex_task_name,
)
from agency_runtime.core.header.finalize import (
    TERMINAL_ACTION_STATUS,
    TERMINAL_OUTCOME_MESSAGES,
)
from agency_runtime.core.native_child_activation import (
    NativeChildRunIdentity,
    build_native_child_run_identity,
)
from agency_runtime.core.retry_receipts import (
    attach_retry_receipt as _attach_retry_receipt,
)
from agency_runtime.core.retry_receipts import (
    normalize_receipt_id as _normalize_receipt_id,
)
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
_VERIFICATION_UNAVAILABLE = (
    "Agency Runtime could not verify or persist the turn-scoped evidence contract. "
    "Do not publish this response; restore the evidence store and start a new turn."
)
_STOP_EVENT_DISCRIMINATOR = re.compile(
    rb'"hook_event_name"\s*:\s*"Stop"',
)
_EVENT_DISCRIMINATOR = re.compile(
    rb'"hook_event_name"\s*:\s*"([A-Za-z][A-Za-z0-9]{0,63})"',
)

_SKILL_TOOL_NAMES = frozenset(
    {
        "Skill",
        "skill",
        "skill_view",
        "record_skill_loaded",
        "agency_record_skill_loaded",
        "agency.record_skill_loaded",
        "mcp__agency__agency.record_skill_loaded",
        "mcp__agency__agency_record_skill_loaded",
    }
)
_SPECIALIST_TOOL_NAMES = {
    "agency_agents_load": "agency_agents_load",
    "agency_agents_inspect": "agency_agents_inspect",
    "agency.load_specialist": "agency_agents_load",
    "mcp__agency__agency.load_specialist": "agency_agents_load",
    "mcp__agency__agency_agents_load": "agency_agents_load",
    "mcp__agency__agency_agents_inspect": "agency_agents_inspect",
}
_DELEGATION_TOOL_NAMES = {
    "agency.delegate": "agency.delegate",
    "mcp__agency__agency.delegate": "agency.delegate",
    "agency_agents_delegate": "agency_agents_delegate",
    "mcp__agency__agency_agents_delegate": "agency_agents_delegate",
    "delegate_task": "delegate_task",
    "delegate_async": "delegate_async",
    "spawn_agent": "spawn_agent",
    "functions.collaboration.spawn_agent": "spawn_agent",
    "followup_task": "followup_task",
    "functions.collaboration.followup_task": "followup_task",
    "sessions_spawn": "sessions_spawn",
}
_CODEX_SPAWN_TOOL_NAMES = frozenset(
    {
        "Agent",
        "spawn_agent",
        "functions.collaboration.spawn_agent",
    }
)
_CLAUDE_AGENT_TOOL_NAME = "Agent"
_CLAUDE_CHILD_PREFLIGHT_MARKER = "[AGENCY CHILD PREFLIGHT v1]"
_CLAUDE_CHILD_IDENTITY_MARKER = "[AGENCY NATIVE CHILD IDENTITY v1]"
_MAX_CLAUDE_CHILD_RECIPE_CHARS = 8_192


def _bounded_completion_reason(reason: object) -> str:
    """Keep one rejection within the native hook's byte-level JSON budget."""

    value = str(reason or _VERIFICATION_UNAVAILABLE)
    encoded = json.dumps(value, ensure_ascii=True).encode("ascii")
    if len(encoded) > MAX_CONTEXT_CHARS:
        return _VERIFICATION_UNAVAILABLE
    return value


def _completion_rejection(reason: str, *, retry: bool) -> dict[str, Any]:
    """Return the native fail-closed shape shared by Codex and Claude."""
    bounded = _bounded_completion_reason(reason)
    if retry:
        return {"continue": False, "stopReason": bounded}
    return {"decision": "block", "reason": bounded}


def _boundary_failure_result(
    payload: Any,
    *,
    raw_bytes: bytes = b"",
    oversized: bool = False,
    expected_event: str = "",
) -> dict[str, Any]:
    """Block any oversized envelope and every recognizable malformed Stop."""

    parsed_stop = isinstance(payload, dict) and payload.get("hook_event_name") == "Stop"
    raw_stop = bool(_STOP_EVENT_DISCRIMINATOR.search(raw_bytes))
    expected_stop = expected_event == "Stop"
    event_matches = _EVENT_DISCRIMINATOR.findall(raw_bytes)
    known_non_stop = len(event_matches) == 1 and event_matches[0].decode("ascii") in (
        _CODEX_EVENTS | _CLAUDE_EVENTS
    ) - {"Stop"}
    if oversized and expected_event in (_CODEX_EVENTS | _CLAUDE_EVENTS) - {"Stop"}:
        return {}
    if oversized and not expected_event and known_non_stop:
        return {}
    if not (oversized or expected_stop or parsed_stop or raw_stop):
        return {}
    return _completion_rejection(
        _VERIFICATION_UNAVAILABLE,
        retry=True,
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


@dataclass(frozen=True, slots=True)
class ClaudeChildAssignment:
    """One content-free, store-verified Claude child work-unit binding."""

    session_id: str
    trace_id: str
    tool_use_id: str
    work_unit_id: str
    specialist_slug: str


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
    )


def _claude_native_child_identity(agent_id: object) -> NativeChildRunIdentity:
    """Derive the one lineage representation shared by child and post-tool hooks."""

    validated_agent_id = validate_correlation_id(agent_id, field="agent_id")
    return build_native_child_run_identity(
        worker_kind="generic-worker",
        worker_id=validated_agent_id,
        native_run_id=f"claude-agent:{validated_agent_id}",
    )


def _codex_native_child_identity(agent_id: object) -> NativeChildRunIdentity:
    """Derive the documented Codex child lineage without inventing a specialist."""

    validated_agent_id = validate_correlation_id(agent_id, field="agent_id")
    return build_native_child_run_identity(
        worker_kind="generic-worker",
        worker_id=validated_agent_id,
        native_run_id=f"codex-agent:{validated_agent_id}",
    )


def _claude_child_preflight_recipe(assignment: ClaudeChildAssignment) -> str:
    """Render a bounded child-owned activation recipe with no prompt or bearer."""

    fields = {
        "parent_session_id": assignment.session_id,
        "parent_trace_id": assignment.trace_id,
        "parent_tool_use_id": assignment.tool_use_id,
        "work_unit_id": assignment.work_unit_id,
        "specialist_slug": assignment.specialist_slug,
    }
    lines = [
        _CLAUDE_CHILD_PREFLIGHT_MARKER,
        "This content-free recipe belongs only to this native child. It does not "
        "inherit or contain a specialist prompt or activation token.",
        *(f"{name}={json.dumps(value, ensure_ascii=True)}" for name, value in fields.items()),
        "Use the exact worker_id and native_run_id injected by the "
        "[AGENCY NATIVE CHILD IDENTITY v1] SubagentStart context. If that identity "
        "is absent, do not claim an Agency specialist was loaded.",
        "Inside this child, call agency.prepare_delegation exactly once with the "
        "specialist_slug, parent_session_id as session_id, parent_trace_id as "
        "trace_id, work_unit_id, worker_kind=generic-worker, and worker_id.",
        "Immediately call agency.load_specialist with the returned activation_token, "
        "the same slug/session/trace/work-unit values, worker_id, and native_run_id. "
        "Apply the returned exact prompt only inside this child.",
        "Never copy the activation token or specialist prompt into status text, the "
        "child result, or another worker. If preparation or loading fails, continue "
        "only as an ordinary native worker and report that Agency activation was not "
        "established.",
    ]
    recipe = "\n".join(lines)
    if len(recipe) > _MAX_CLAUDE_CHILD_RECIPE_CHARS:
        raise RuntimeError("Claude child preflight recipe exceeds its context budget")
    return recipe


def _native_work_unit_label(host: str, tool_name: str, args: dict[str, Any]) -> str:
    """Return only an explicit Agency recipe label from official native args."""

    candidate = ""
    if host == "codex" and tool_name in _CODEX_SPAWN_TOOL_NAMES:
        # Resolution is store-bound in HookBridge so an arbitrary legal-looking
        # native label cannot invent a persisted Agency work unit.
        return ""
    elif host == "claude" and tool_name == "Agent":
        candidate = _first_string(args, "description")
    return candidate if candidate.startswith(("specialist:", "unit-")) else ""


def _canonical_tool_call(
    host: str,
    tool_name: str,
    tool_input: Any,
    tool_response: Any,
) -> tuple[str, dict[str, Any]]:
    """Map only explicit Agency and host-native identifiers to evidence names.

    Tool names are an authority boundary. Namespace suffix matching would let
    an unrelated server impersonate an Agency evidence tool, so every accepted
    spelling is enumerated here.
    """
    args = _dict_or_empty(tool_input)

    if tool_name in _SKILL_TOOL_NAMES:
        return "skill_view", {
            **args,
            "name": _first_string(args, "name", "skill", "skill_name", "command"),
        }
    if canonical_specialist := _SPECIALIST_TOOL_NAMES.get(tool_name):
        return canonical_specialist, args

    canonical_delegate = _DELEGATION_TOOL_NAMES.get(tool_name)
    if host == "claude" and tool_name == "Agent":
        canonical_delegate = "delegate_task"
    elif host == "codex" and tool_name == "Agent":
        canonical_delegate = "spawn_agent"
    if canonical_delegate:
        work_unit_id = _first_string(args, "work_unit_id", "workUnitId", "task_id", "taskId")
        work_unit_id = work_unit_id or _native_work_unit_label(host, tool_name, args)
        work_unit_id = work_unit_id or _response_work_unit(tool_response)
        normalized = {
            **args,
            "agent": _first_string(
                args,
                "agent",
                "agentId",
                "agent_id",
                "slug",
                "recommended_agent",
                "subagent_type",
                "target",
            ),
            "goal": _first_string(args, "goal", "task", "prompt", "description", "message"),
            "work_unit_id": work_unit_id,
        }
        return canonical_delegate, normalized
    return tool_name, args


class HookBridge:
    """Translate one native hook event to a host adapter operation."""

    def __init__(
        self,
        host: str,
        *,
        store: Store | None = None,
        adapter: Any | None = None,
        _master: dict[str, Any] | None = None,
    ) -> None:
        normalized_host = host.strip().casefold()
        if normalized_host not in {"codex", "claude"}:
            raise ValueError(f"unsupported hook host: {host}")
        self.host = normalized_host
        self._store = store
        self._adapter = adapter
        self._master = _master

    @property
    def store(self) -> Store:
        if self._store is None:
            self._store = Store()
        return self._store

    @store.setter
    def store(self, value: Store) -> None:
        self._store = value

    @property
    def adapter(self) -> Any:
        if self._adapter is None:
            self._adapter = self._new_adapter()
        return self._adapter

    @adapter.setter
    def adapter(self, value: Any) -> None:
        self._adapter = value

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
        try:
            session_id = validate_correlation_id(
                _required_string(payload, "session_id"),
                field="session_id",
            )
            turn_id = validate_correlation_id(
                _optional_string(payload, "turn_id"),
                field="turn_id",
                required=False,
            )
            tool_use_id = validate_correlation_id(
                _optional_string(payload, "tool_use_id"),
                field="tool_use_id",
                required=False,
            )
        except ValueError as exc:
            raise HookInputError(str(exc)) from exc
        model = _optional_string(payload, "model")
        work_unit_id = _first_string(
            args,
            "work_unit_id",
            "workUnitId",
            "task_id",
            "taskId",
        )
        work_unit_id = work_unit_id or _response_work_unit(tool_response)
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

        open_trace_getter = getattr(self.store, "get_open_traces_for_session", None)
        if callable(open_trace_getter) and session_id:
            try:
                open_traces = list(open_trace_getter(session_id))
            except Exception:
                open_traces = []
            if open_traces:
                return str(open_traces[0]) if len(open_traces) == 1 else ""

        recent_activity = getattr(self.store, "recent_runtime_activity", None)
        if not callable(recent_activity) or not session_id:
            return ""
        try:
            activity = recent_activity(limit=200)
        except Exception:
            return ""
        if not isinstance(activity, dict):
            return ""
        session_runs = [
            row
            for row in activity.get("runs", [])
            if isinstance(row, dict) and row.get("session_id") == session_id and row.get("trace_id")
        ]
        if session_runs:
            open_traces = {
                str(row.get("trace_id"))
                for row in session_runs
                if row.get("status") in {"active", "evidence_only"}
            }
            return next(iter(open_traces)) if len(open_traces) == 1 else ""

        terminal = {
            str(row.get("trace_id"))
            for row in activity.get("finalizations", [])
            if isinstance(row, dict)
            and row.get("trace_id")
            and row.get("action") in {"accept", "retry_exhausted"}
        }
        open_traces = {
            str(row.get("trace_id"))
            for row in activity.get("routing", [])
            if isinstance(row, dict)
            and row.get("session_id") == session_id
            and row.get("trace_id")
            and str(row.get("trace_id")) not in terminal
        }
        return next(iter(open_traces)) if len(open_traces) == 1 else ""

    def _native_child_parent_scope(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, str, str]:
        correlation = self._correlation(payload)
        trace_id = correlation.trace_id or self._unambiguous_open_trace(correlation.session_id)
        return correlation.session_id, trace_id, correlation.work_unit_id

    def _resolve_codex_task_name(
        self,
        *,
        tool_name: str,
        tool_input: Any,
        session_id: str,
        trace_id: str,
    ) -> str:
        """Resolve only allowlisted native spawn labels to one internal unit."""

        if self.host != "codex" or tool_name not in _CODEX_SPAWN_TOOL_NAMES:
            return ""
        task_name = _first_string(_dict_or_empty(tool_input), "task_name")
        if not task_name or not session_id or not trace_id:
            return ""
        candidates: set[str] = set()
        try:
            candidates.update(
                str(row.get("work_unit_id") or "").strip()
                for row in self.store.get_delegations(trace_id)
                if isinstance(row, dict) and str(row.get("session_id") or "").strip() == session_id
            )
        except Exception:
            return ""
        direct = internal_work_unit_from_codex_task_name(task_name)
        if direct and direct in candidates:
            return direct
        try:
            snapshot = self.store.get_completion_evidence_snapshot(
                session_id,
                trace_id,
            )
        except Exception:
            return ""
        candidates.update(
            str(row.get("work_unit_id") or "").strip()
            for row in snapshot.get("specialist_activations", [])
            if isinstance(row, dict)
        )
        matches = [
            work_unit_id
            for work_unit_id in candidates
            if work_unit_id and codex_task_name_for_work_unit(work_unit_id) == task_name
        ]
        return matches[0] if len(matches) == 1 else ""

    def _resolve_claude_child_assignment(
        self,
        *,
        payload: dict[str, Any],
        tool_input: Any,
        trace_id: str = "",
    ) -> ClaudeChildAssignment | None:
        """Resolve one exact persisted plan row without correlating by callback order."""

        if (
            self.host != "claude"
            or _optional_string(payload, "tool_name") != _CLAUDE_AGENT_TOOL_NAME
        ):
            return None
        args = _dict_or_empty(tool_input)
        description = args.get("description")
        if (
            not isinstance(description, str)
            or not description
            or description != description.strip()
        ):
            return None
        correlation = self._correlation(payload, tool_input)
        if not correlation.tool_use_id:
            return None
        resolved_trace = trace_id or correlation.turn_id
        if not resolved_trace:
            resolved_trace = self._unambiguous_open_trace(correlation.session_id)
        if not resolved_trace:
            return None
        try:
            snapshot = self.store.get_completion_evidence_snapshot(
                correlation.session_id,
                resolved_trace,
            )
        except Exception:
            return None
        if (
            not isinstance(snapshot, dict)
            or snapshot.get("session_id") != correlation.session_id
            or snapshot.get("trace_id") != resolved_trace
            or snapshot.get("status") not in {"active", "evidence_only"}
            or snapshot.get("delivery_mode") != "isolated"
        ):
            return None

        references = snapshot.get("selected_specialists")
        if not isinstance(references, list):
            return None
        reference_slugs = [
            str(reference.get("slug") or "")
            for reference in references
            if isinstance(reference, dict)
        ]
        plan = snapshot.get("unit_agent_plan")
        if not isinstance(plan, list):
            return None
        if plan:
            matches = [
                row
                for row in plan
                if isinstance(row, dict) and row.get("work_unit_id") == description
            ]
            if len(matches) != 1:
                return None
            specialist_slug = str(matches[0].get("recommended_agent") or "")
        elif description.startswith("specialist:"):
            specialist_slug = description.removeprefix("specialist:")
        else:
            return None
        if not specialist_slug or reference_slugs.count(specialist_slug) != 1:
            return None
        # ``removeprefix`` plus the fixed prefix makes reconstruction identical;
        # no second string-equality branch can add validation here.
        return ClaudeChildAssignment(
            session_id=correlation.session_id,
            trace_id=resolved_trace,
            tool_use_id=correlation.tool_use_id,
            work_unit_id=description,
            specialist_slug=specialist_slug,
        )

    @staticmethod
    def _claude_post_tool_response(
        payload: dict[str, Any],
        tool_response: Any,
    ) -> tuple[Any, NativeChildRunIdentity | None]:
        """Project only host-returned child identity into canonical evidence."""

        if not isinstance(tool_response, dict):
            return tool_response, None
        agent_id = _first_string(tool_response, "agent_id", "agentId")
        agent_id = agent_id or _optional_string(payload, "agent_id")
        if not agent_id:
            return tool_response, None
        try:
            identity = _claude_native_child_identity(agent_id)
        except ValueError:
            return tool_response, None
        return (
            {
                **tool_response,
                "agent_id": identity.worker_id,
                "native_run_id": identity.native_run_id,
            },
            identity,
        )

    def _handle_claude_pre_tool_use(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Attach a child-owned recipe while leaving Claude's Agent scheduler intact."""

        if _required_string(payload, "tool_name") != _CLAUDE_AGENT_TOOL_NAME:
            return {}
        tool_input = payload.get("tool_input")
        args = _dict_or_empty(tool_input)
        prompt = args.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise HookInputError("Claude Agent tool_input.prompt is required")
        if _CLAUDE_CHILD_PREFLIGHT_MARKER in prompt:
            return {}
        assignment = self._resolve_claude_child_assignment(
            payload=payload,
            tool_input=tool_input,
        )
        if assignment is None:
            return {}
        recipe = _claude_child_preflight_recipe(assignment)
        updated_input = {
            **args,
            "prompt": f"{prompt}\n\n{recipe}",
        }
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": updated_input,
            }
        }
        encoded = json.dumps(
            result,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return result if len(encoded) < MAX_HOOK_OUTPUT_BYTES else {}

    def _handle_claude_subagent_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Give this child its own identity without assigning any specialist."""

        session_id, trace_id, work_unit_id = self._native_child_parent_scope(payload)
        _required_string(payload, "agent_type")
        try:
            identity = _claude_native_child_identity(_required_string(payload, "agent_id"))
        except ValueError:
            return {}
        recorder = getattr(self.store, "record_native_child_started", None)
        if callable(recorder) and trace_id:
            recorder(
                host="claude",
                backend="delegate_task",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
        context = "\n".join(
            [
                _CLAUDE_CHILD_IDENTITY_MARKER,
                "This identity belongs only to the current native child. It does not "
                "load, select, or inherit an Agency specialist.",
                f"worker_kind={json.dumps(identity.worker_kind)}",
                f"worker_id={json.dumps(identity.worker_id, ensure_ascii=True)}",
                f"native_run_id={json.dumps(identity.native_run_id, ensure_ascii=True)}",
                "Use these exact values only when this child's prompt contains an "
                "[AGENCY CHILD PREFLIGHT v1] recipe. Otherwise make no Agency "
                "specialist claim.",
            ]
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        }

    def _handle_claude_subagent_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate lifecycle identity without inventing an undocumented parent join."""

        session_id, trace_id, work_unit_id = self._native_child_parent_scope(payload)
        _required_string(payload, "agent_type")
        try:
            identity = _claude_native_child_identity(_required_string(payload, "agent_id"))
        except ValueError:
            return {}
        recorder = getattr(self.store, "record_native_child_stopped", None)
        if callable(recorder) and trace_id:
            recorder(
                host="claude",
                backend="delegate_task",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
        return {}

    def _handle_codex_subagent_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Inject only exact native identity plus child-owned fallback routing."""

        session_id, trace_id, work_unit_id = self._native_child_parent_scope(payload)
        _required_string(payload, "agent_type")
        try:
            identity = _codex_native_child_identity(_required_string(payload, "agent_id"))
        except ValueError:
            return {}
        recorder = getattr(self.store, "record_native_child_started", None)
        if callable(recorder) and trace_id:
            recorder(
                host="codex",
                backend="spawn_agent",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
        child_session_id = f"codex-child:{identity.worker_id}"
        context = "\n".join(
            [
                _CLAUDE_CHILD_IDENTITY_MARKER,
                "This identity belongs only to the current native Codex child. It "
                "does not load, select, or inherit an Agency specialist.",
                f"worker_kind={json.dumps(identity.worker_kind)}",
                f"worker_id={json.dumps(identity.worker_id, ensure_ascii=True)}",
                f"native_run_id={json.dumps(identity.native_run_id, ensure_ascii=True)}",
                "If this child's task contains an [AGENCY CHILD PREFLIGHT v1] recipe, "
                "follow only that exact current recipe and consume its one-use activation "
                "inside this child.",
                "If no current recipe is present, independently call agency.preflight "
                "before substantive work using the complete delegated assignment as "
                "user_message and "
                f"session_id={json.dumps(child_session_id, ensure_ascii=True)}. Apply only "
                "the returned child-turn context. Do not claim parent Agency delegation "
                "without an authoritative activation receipt.",
            ]
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        }

    def _handle_codex_subagent_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Record an exact Codex lifecycle stop without guessing task correlation."""

        session_id, trace_id, work_unit_id = self._native_child_parent_scope(payload)
        _required_string(payload, "agent_type")
        try:
            identity = _codex_native_child_identity(_required_string(payload, "agent_id"))
        except ValueError:
            return {}
        recorder = getattr(self.store, "record_native_child_stopped", None)
        if callable(recorder) and trace_id:
            recorder(
                host="codex",
                backend="spawn_agent",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
        return {}

    def _handle_post_tool_use(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Record one canonical tool observation outside the main event dispatcher."""

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
        turn_trace_id = correlation.turn_id or self._unambiguous_open_trace(correlation.session_id)
        if self.host == "claude" and tool_name == _CLAUDE_AGENT_TOOL_NAME and not turn_trace_id:
            return {}
        trace_id = turn_trace_id or correlation.tool_use_id
        canonical_name, canonical_args = _canonical_tool_call(
            self.host,
            tool_name,
            tool_input,
            tool_response,
        )
        if self.host == "claude" and tool_name == _CLAUDE_AGENT_TOOL_NAME:
            assignment = self._resolve_claude_child_assignment(
                payload=payload,
                tool_input=tool_input,
                trace_id=trace_id,
            )
            canonical_args["work_unit_id"] = (
                assignment.work_unit_id if assignment is not None else ""
            )
            if assignment is not None:
                canonical_args["agent"] = assignment.specialist_slug
            else:
                # ``subagent_type`` is a native Claude worker profile, not an
                # Agency specialist identity. Only an exact persisted plan row
                # can authorize the specialist projection.
                canonical_args["agent"] = ""
            requested_model = _first_string(_dict_or_empty(tool_input), "model")
            resolved_model = _first_string(
                _dict_or_empty(tool_response),
                "resolved_model",
                "resolvedModel",
                "model",
            )
            canonical_args["requested_model"] = requested_model
            canonical_args["resolved_model"] = resolved_model or "unavailable"
            tool_response, _identity = self._claude_post_tool_response(
                payload,
                tool_response,
            )
        elif self.host == "codex" and tool_name in _CODEX_SPAWN_TOOL_NAMES:
            if isinstance(tool_response, dict):
                agent_id = _first_string(tool_response, "agent_id", "agentId")
                if agent_id:
                    try:
                        identity = _codex_native_child_identity(agent_id)
                    except ValueError:
                        pass
                    else:
                        tool_response = {
                            **tool_response,
                            "agent_id": identity.worker_id,
                            "native_run_id": identity.native_run_id,
                        }
        resolved_codex_unit = self._resolve_codex_task_name(
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=correlation.session_id,
            trace_id=trace_id,
        )
        if resolved_codex_unit:
            canonical_args["work_unit_id"] = resolved_codex_unit
        if correlation.work_unit_id and not _first_string(
            canonical_args, "work_unit_id", "workUnitId"
        ):
            canonical_args["work_unit_id"] = correlation.work_unit_id
        self.adapter.post_tool_call_handler(
            tool_name=canonical_name,
            args=canonical_args,
            result=tool_response,
            session_id=correlation.session_id,
            trace_id=trace_id,
            turn_id=correlation.turn_id,
            work_unit_id=correlation.work_unit_id,
            model=correlation.model,
            tool_use_id=correlation.tool_use_id,
            agent_id=_optional_string(payload, "agent_id"),
        )
        return {}

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise HookInputError("hook input must be a JSON object")
        from agency_runtime.core.runtime_control import read_enforcement_runtime_control

        master = self._master
        self._master = None
        if master is None:
            master, _master_transport = read_enforcement_runtime_control()
        if not master["enabled"]:
            return {}
        event = self._event_name(payload)

        if event == "UserPromptSubmit":
            prompt = _required_string(payload, "prompt")
            correlation = self._correlation(payload)
            trace_id = correlation.trace_id or str(uuid4())
            origin_receipt = self._user_prompt_origin(correlation, trace_id=trace_id)
            if origin_receipt.origin == "internal_retry":
                return {}
            reservation = self._reserve_user_turn(correlation.session_id, trace_id)
            try:
                result = self.adapter.pre_llm_call_handler(
                    session_id=correlation.session_id,
                    user_message=prompt,
                    model=correlation.model,
                    trace_id=trace_id,
                    reservation_token=str(reservation.get("reservation_token") or ""),
                    origin_receipt=origin_receipt,
                )
            except Exception as error:
                try:
                    self._close_unused_reservation(
                        correlation.session_id,
                        trace_id,
                        reservation,
                    )
                except Exception as cleanup_error:
                    raise error from cleanup_error
                raise
            context = result.get("context") if isinstance(result, dict) else None
            if not isinstance(context, str) or not context:
                self._close_unused_reservation(
                    correlation.session_id,
                    trace_id,
                    reservation,
                )
                return {}
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context[:MAX_CONTEXT_CHARS],
                }
            }

        if event == "PreToolUse" and self.host == "claude":
            return self._handle_claude_pre_tool_use(payload)

        if event == "SubagentStart":
            return (
                self._handle_claude_subagent_start(payload)
                if self.host == "claude"
                else self._handle_codex_subagent_start(payload)
            )

        if event == "SubagentStop":
            return (
                self._handle_claude_subagent_stop(payload)
                if self.host == "claude"
                else self._handle_codex_subagent_stop(payload)
            )

        if event in {"PostToolUse", "PostToolUseFailure"}:
            return self._handle_post_tool_use(event, payload)

        if event == "Stop":
            return self._handle_stop(payload)

        if event in {"SessionStart", "PostCompact", "SessionEnd"}:
            return self._handle_resident_lifecycle(event, payload)

        # Pre-tool, permission, and subagent lifecycle events intentionally have
        # no side effect in the shared boundary yet.
        return {}

    def _handle_resident_lifecycle(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply bounded manager-binding lifecycle effects for native host hooks."""

        correlation = self._correlation(payload)
        if event == "SessionEnd":
            self._close_session_turns(correlation.session_id, "session_ended")
            operation = getattr(self.store, "retire_resident_manager_binding", None)
            failure = "evidence store cannot retire resident managers"
        elif event == "PostCompact" or (
            event == "SessionStart"
            and _optional_string(payload, "source").strip().casefold() == "compact"
        ):
            operation = getattr(self.store, "mark_resident_manager_restore_required", None)
            failure = "evidence store cannot restore resident managers"
        else:
            return {}
        if not callable(operation):
            raise RuntimeError(failure)
        operation(session_id=correlation.session_id, host=self.host)
        return {}

    def _acknowledge_resident_manager_delivery(
        self,
        *,
        session_id: str,
        trace_id: str,
    ) -> None:
        """Prove the host consumed this turn's manager delivery before finalization."""

        from agency_runtime.core.resident_manager_binding import (
            canonical_resident_manager_host,
            resident_manager_host_mode,
            validate_resident_manager_binding,
        )

        raw_binding: object = None
        snapshot_reader = getattr(self.store, "get_completion_evidence_snapshot", None)
        if callable(snapshot_reader):
            snapshot = snapshot_reader(session_id, trace_id)
            if not isinstance(snapshot, dict):
                raise RuntimeError("resident-manager delivery evidence is unavailable")
            raw_binding = snapshot.get("resident_manager_binding")
            if raw_binding is None:
                return
            try:
                binding = validate_resident_manager_binding(
                    raw_binding,
                    session_id=session_id,
                )
            except ValueError as exc:
                raise RuntimeError("resident-manager delivery evidence is invalid") from exc
            if binding.host != canonical_resident_manager_host(self.host):
                if binding.host_mode == "request_scoped":
                    return
                raise RuntimeError("resident-manager delivery host does not match")

        acknowledge = getattr(self.store, "acknowledge_resident_manager_binding", None)
        if not callable(acknowledge):
            raise RuntimeError("evidence store cannot acknowledge resident managers")
        acknowledged = acknowledge(
            session_id=session_id,
            host=self.host,
            trace_id=trace_id,
            binding=raw_binding,
        )
        if resident_manager_host_mode(self.host) == "persistent" and acknowledged is not True:
            raise RuntimeError("resident-manager delivery acknowledgement failed")

    def _is_authenticated_retry(
        self,
        prompt: str,
        correlation: HookCorrelation,
    ) -> bool:
        """Compatibility projection; prompt content never grants retry authority."""

        del prompt
        return self._user_prompt_origin(correlation).origin == "internal_retry"

    def _user_prompt_origin(
        self,
        correlation: HookCorrelation,
        *,
        trace_id: str = "",
    ) -> Any:
        """Seal external-user or retry origin from durable host lifecycle state."""

        from agency_runtime.core.turn_origin import native_adapter_turn_origin

        resolver = getattr(self.store, "resolve_pending_internal_retry", None)
        internal = False
        if callable(resolver) and correlation.session_id and correlation.trace_id:
            try:
                resolved = resolver(correlation.session_id, correlation.trace_id)
            except Exception:
                resolved = None
            internal = resolved == correlation.trace_id
        origin = "internal_retry" if internal else "external_user"
        event = "user_prompt_submit_retry" if internal else "user_prompt_submit"
        return native_adapter_turn_origin(
            origin,
            host=self.host,
            event=event,
            session_id=correlation.session_id,
            trace_id=trace_id or correlation.trace_id or str(uuid4()),
        )

    def _reserve_user_turn(self, session_id: str, trace_id: str) -> dict[str, Any]:
        """Durably rotate a session to exactly one external user turn."""
        reserver = getattr(self.store, "reserve_session_turn", None)
        if not callable(reserver):
            raise RuntimeError("evidence store cannot reserve a session turn")
        result = reserver(
            session_id=session_id,
            trace_id=trace_id,
            host=self.host,
        )
        if not isinstance(result, dict) or str(result.get("trace_id") or "") != trace_id:
            raise RuntimeError("session turn reservation could not be verified")
        reservation_token = str(result.get("reservation_token") or "").strip()
        if reservation_token:
            try:
                UUID(reservation_token)
            except (TypeError, ValueError, AttributeError) as exc:
                raise RuntimeError("session turn reservation identity is invalid") from exc
        elif result.get("created") is True:
            raise RuntimeError("session turn reservation identity was not persisted")
        return result

    def _close_unused_reservation(
        self,
        session_id: str,
        trace_id: str,
        reservation: dict[str, Any],
    ) -> None:
        """Abandon only the exact, still-unpromoted reservation for this prompt."""
        reservation_token = str(reservation.get("reservation_token") or "")
        if not reservation_token:
            return
        abandon = getattr(self.store, "abandon_preflight_reservation", None)
        if not callable(abandon):
            raise RuntimeError("evidence store cannot abandon a preflight reservation")
        abandon(
            session_id=session_id,
            trace_id=trace_id,
            reservation_token=reservation_token,
            status="preflight_skipped",
        )

    def _current_open_trace(self, session_id: str) -> tuple[str, bool]:
        """Return the unique open trace and whether any open trace exists."""
        getter = getattr(self.store, "get_open_traces_for_session", None)
        if not callable(getter):
            raise RuntimeError("evidence store cannot verify current turn correlation")
        candidates = [str(value) for value in getter(session_id) if str(value)]
        if not candidates:
            return "", False
        if len(candidates) != 1:
            return "", True
        return candidates[0], True

    def _handle_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Revalidate one final response and translate the outcome per host."""
        correlation = self._correlation(payload)
        host_retry = _optional_bool(payload, "stop_hook_active")
        final_response = _optional_string(payload, "last_assistant_message")
        trace_id = correlation.trace_id
        try:
            if not trace_id:
                trace_id, has_open_trace = self._current_open_trace(correlation.session_id)
                if has_open_trace and not trace_id:
                    raise RuntimeError("current turn correlation is ambiguous")
                if not has_open_trace:
                    # Public/MCP finalization closes before native Stop. Only
                    # when no current turn exists may an exact terminal digest
                    # recover a host envelope that omitted its turn ID.
                    trace_id = self._authoritative_trace_for_response(
                        correlation.session_id,
                        final_response,
                    )
            self._acknowledge_resident_manager_delivery(
                session_id=correlation.session_id,
                trace_id=trace_id,
            )
            terminal = self._exact_terminal_finalization(
                correlation.session_id,
                trace_id,
                final_response,
            )
            if terminal is not None:
                return self._terminal_completion_result(str(terminal["action"]))
            if self._is_terminal_turn(correlation.session_id, trace_id):
                return self._reject_completion(
                    (
                        "AGENCY TURN TERMINAL: The submitted response does not match the "
                        "exact response accepted for this trace. It cannot be published or "
                        "retried; begin a new user turn."
                    ),
                    retry=True,
                )
            retry = host_retry
        except Exception:
            self._close_turn(correlation.session_id, trace_id, "verification_failed")
            return self._reject_completion(_VERIFICATION_UNAVAILABLE, retry=True)

        verification = self._verify_final_response(
            final_response,
            correlation=correlation,
            trace_id=trace_id,
            retry=retry,
        )
        if verification.get("verification_unavailable") is True:
            self._close_turn(correlation.session_id, trace_id, "verification_failed")
            return self._reject_completion(_VERIFICATION_UNAVAILABLE, retry=True)
        if verification.get("action") == "continue":
            return self._handle_continuation_decision(
                correlation=correlation,
                trace_id=trace_id,
                final_response=final_response,
                host_retry=host_retry,
                verification=verification,
            )

        if verification.get("runtime_disabled") is True:
            return {}

        accepted = self._commit_terminal_finalization(
            session_id=correlation.session_id,
            trace_id=trace_id,
            action="accept",
            status="completed",
            response_text=final_response,
            expected_evidence_revision=verification.get("evidence_revision"),
        )
        if not accepted:
            return self._reject_completion(_VERIFICATION_UNAVAILABLE, retry=True)
        return {}

    def _handle_continuation_decision(
        self,
        *,
        correlation: HookCorrelation,
        trace_id: str,
        final_response: str,
        host_retry: bool,
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        """Claim one retry or terminalize the already revalidated response."""

        reason = str(
            verification.get("message")
            or "Agency Runtime evidence verification requires another pass."
        )
        claim = self._claim_continuation(
            session_id=correlation.session_id,
            trace_id=trace_id,
            response_text=final_response,
            retry_active=host_retry,
        )
        if claim is None:
            return self._verification_failed(correlation.session_id, trace_id)
        if claim["outcome"] == "claimed":
            return self._reject_completion(
                _attach_retry_receipt(reason, claim["receipt_id"]),
                retry=False,
            )

        # ``_handle_stop`` verified this exact response immediately before the
        # atomic continuation claim.  Re-running the provider here caused the
        # second Stop callback to be evaluated twice and made exact terminal
        # replay observably non-idempotent.  The terminal commit below binds
        # the verified evidence revision with a CAS, so a concurrent evidence
        # change fails closed without another provider call.
        if verification.get("runtime_disabled") is True:
            return {}
        if verification.get("action") == "accept":
            action = "accept"
            status = "completed"
        elif verification.get("delegation_strength") == "strongly_preferred":
            action = "delegation_declined"
            status = "delegation_declined"
        else:
            action = "retry_exhausted"
            status = "retry_exhausted"
        committed = self._commit_terminal_finalization(
            session_id=correlation.session_id,
            trace_id=trace_id,
            action=action,
            status=status,
            response_text=final_response,
            expected_evidence_revision=verification.get("evidence_revision"),
        )
        if not committed:
            return self._verification_failed(correlation.session_id, trace_id)
        if action == "accept":
            return {}
        return self._terminal_completion_result(action)

    def _verification_failed(self, session_id: str, trace_id: str) -> dict[str, Any]:
        self._close_turn(session_id, trace_id, "verification_failed")
        return self._reject_completion(_VERIFICATION_UNAVAILABLE, retry=True)

    def _claim_continuation(
        self,
        *,
        session_id: str,
        trace_id: str,
        response_text: str,
        retry_active: bool,
    ) -> dict[str, str] | None:
        """Atomically claim, replay, or exhaust one revision opportunity."""

        from agency_runtime.core.header.finalize import response_hash

        claimer = getattr(self.store, "claim_continuation", None)
        if not callable(claimer):
            return None
        digest = response_hash(response_text)
        try:
            result = claimer(
                session_id=session_id,
                trace_id=trace_id,
                host=self.host,
                response_hash=digest,
                retry_active=retry_active,
            )
        except Exception:
            return None
        if not isinstance(result, dict) or result.get("outcome") not in {
            "claimed",
            "replay",
            "exhausted",
        }:
            return None
        if result.get("response_hash") != digest:
            return None
        receipt_id = _normalize_receipt_id(result.get("receipt_id"))
        if result["outcome"] in {"claimed", "replay"} and not receipt_id:
            return None
        return {
            "outcome": str(result["outcome"]),
            "receipt_id": receipt_id,
            "response_hash": digest,
        }

    def _commit_terminal_finalization(
        self,
        *,
        session_id: str,
        trace_id: str,
        action: str,
        status: str,
        response_text: str,
        expected_evidence_revision: Any,
    ) -> bool:
        """Atomically bind one terminal response outcome to its exact turn."""
        from agency_runtime.core.header.finalize import response_hash

        committer = getattr(self.store, "commit_terminal_finalization", None)
        if not callable(committer):
            return False
        digest = response_hash(response_text)
        if (
            isinstance(expected_evidence_revision, bool)
            or not isinstance(expected_evidence_revision, int)
            or expected_evidence_revision <= 0
        ):
            return False
        arguments: dict[str, Any] = {
            "session_id": session_id,
            "trace_id": trace_id,
            "host": self.host,
            "action": action,
            "response_hash": digest,
            "status": status,
            "expected_evidence_revision": expected_evidence_revision,
        }
        if action == "accept" and status == "completed":
            from agency_runtime.core.turn_intent import classify_pending_interaction

            pending = classify_pending_interaction(response_text)
            arguments.update(
                pending_interaction_kind=pending.kind,
                pending_interaction_fingerprint=pending.response_fingerprint,
            )
        try:
            result = committer(**arguments)
        except Exception:
            return False
        return bool(
            isinstance(result, dict)
            and result.get("authoritative") is True
            and result.get("outcome") in {"committed", "replay"}
            and result.get("action") == action
            and result.get("response_hash") == digest
            and result.get("status") == status
        )

    def _authoritative_trace_for_response(
        self,
        session_id: str,
        final_response: str,
    ) -> str:
        """Recover one exact terminal trace when a host omits its turn ID."""
        from agency_runtime.core.header.finalize import response_hash

        finder = getattr(self.store, "find_authoritative_trace", None)
        if not callable(finder):
            raise RuntimeError("evidence store cannot recover terminal correlation")
        digest = response_hash(final_response)
        resolved: set[str] = set()
        for action in TERMINAL_ACTION_STATUS:
            candidate = finder(
                session_id,
                action=action,
                response_hash=digest,
            )
            if candidate is None:
                continue
            if not isinstance(candidate, str) or not candidate.strip():
                raise RuntimeError("terminal response correlation could not be verified")
            resolved.add(candidate.strip())
        if not resolved:
            return ""
        if len(resolved) != 1:
            raise RuntimeError("terminal response correlation could not be verified")
        return resolved.pop()

    def _exact_terminal_finalization(
        self,
        session_id: str,
        trace_id: str,
        final_response: str,
    ) -> dict[str, Any] | None:
        """Return one exact terminal event after validating its action/status pair."""

        from agency_runtime.core.header.finalize import terminal_response_run

        run = terminal_response_run(
            self.store,
            session_id,
            trace_id,
            final_response,
        )
        if run is None:
            return None
        action = str(run.get("action") or "")
        expected_status = TERMINAL_ACTION_STATUS.get(action)
        if (
            run.get("authoritative") is not True
            or expected_status is None
            or str(run.get("terminal_status") or "") != expected_status
            or str(run.get("status") or "") != expected_status
        ):
            raise RuntimeError("terminal response belongs to an inconsistent Agency turn")
        return run

    def _terminal_completion_result(self, action: str) -> dict[str, Any]:
        """Return an idempotent non-corrective envelope for one terminal action."""

        if action == "accept":
            return {}
        message = TERMINAL_OUTCOME_MESSAGES.get(action)
        if message is None:
            raise RuntimeError("terminal response action is invalid")
        return self._reject_completion(message, retry=True)

    def _accept_exact_finalized_response(
        self,
        session_id: str,
        trace_id: str,
        final_response: str,
    ) -> bool:
        """Idempotently accept only an exact response finalized earlier."""
        run = self._exact_terminal_finalization(
            session_id,
            trace_id,
            final_response,
        )
        if run is None:
            return False
        return str(run.get("action") or "") == "accept"

    def _is_terminal_turn(self, session_id: str, trace_id: str) -> bool:
        """Return exact terminal state, failing closed on unreadable correlation."""
        getter = getattr(self.store, "get_run", None)
        if not callable(getter):
            raise RuntimeError("turn lifecycle could not be verified")
        run = getter(trace_id)
        if run is None:
            return False
        if not isinstance(run, dict) or str(run.get("session_id") or "") != session_id:
            raise RuntimeError("turn lifecycle correlation could not be verified")
        return str(run.get("status") or "") not in {"active", "evidence_only"}

    def _verify_final_response(
        self,
        final_response: str,
        *,
        correlation: HookCorrelation,
        trace_id: str,
        retry: bool,
    ) -> dict[str, Any]:
        """Contain verifier failures and normalize its accept/revise contract."""
        evaluator = getattr(self.adapter, "evaluate_completion_policy", None)
        try:
            if callable(evaluator):
                verification = evaluator(
                    final_response,
                    session_id=correlation.session_id,
                    model=correlation.model,
                    trace_id=trace_id,
                )
            else:
                legacy = self.adapter.pre_verify_handler(
                    final_response,
                    session_id=correlation.session_id,
                    model=correlation.model,
                    attempt=1 if retry else 0,
                    trace_id=trace_id,
                )
                verification = {"action": "accept"} if legacy is None else legacy
        except Exception:
            return {"action": "continue", "message": _VERIFICATION_UNAVAILABLE}
        if not isinstance(verification, dict) or verification.get("action") not in {
            "accept",
            "continue",
        }:
            return {"action": "continue", "message": _VERIFICATION_UNAVAILABLE}
        revision = verification.get("evidence_revision")
        valid_revision = (
            isinstance(revision, int) and not isinstance(revision, bool) and revision > 0
        )
        if verification.get("runtime_disabled") is not True and not valid_revision:
            return {
                "action": "continue",
                "message": _VERIFICATION_UNAVAILABLE,
                "verification_unavailable": True,
            }
        return verification

    def _reject_completion(self, reason: str, *, retry: bool) -> dict[str, Any]:
        """Return a host-native fail-closed completion result."""
        return _completion_rejection(reason, retry=retry)

    def _record_finalization(
        self,
        trace_id: str,
        action: str,
        *,
        response_text: str = "",
    ) -> str:
        if not trace_id:
            return ""
        try:
            from agency_runtime.core.header.finalize import response_hash

            receipt = self.store.record_finalization(
                trace_id=trace_id,
                host=self.host,
                action=action,
                missing=[],
                response_hash=response_hash(response_text) if response_text else "",
            )
        except Exception:
            return ""
        return _normalize_receipt_id(receipt)

    def _close_turn(self, session_id: str, trace_id: str, status: str) -> bool:
        if not session_id or not trace_id:
            return False
        closer = getattr(self.store, "close_turn_evidence", None)
        getter = getattr(self.store, "get_run", None)
        if not callable(closer) or not callable(getter):
            return False
        try:
            closer(session_id, trace_id, status=status)
            run = getter(trace_id)
        except Exception:
            return False
        return bool(
            isinstance(run, dict)
            and str(run.get("session_id") or "") == session_id
            and str(run.get("status") or "") == status
        )

    def _close_session_turns(self, session_id: str, status: str) -> None:
        getter = getattr(self.store, "get_open_traces_for_session", None)
        if not callable(getter) or not session_id:
            return
        try:
            trace_ids = list(getter(session_id))
        except Exception:
            return
        for trace_id in trace_ids:
            self._close_turn(session_id, str(trace_id), status)


def _write_output(stream: BinaryIO | TextIO, payload: dict[str, Any]) -> None:
    def fallback() -> bytes:
        if payload.get("continue") is False:
            safe = _completion_rejection(_VERIFICATION_UNAVAILABLE, retry=True)
        elif payload.get("decision") == "block":
            safe = _completion_rejection(_VERIFICATION_UNAVAILABLE, retry=False)
        else:
            safe = {}
        return json.dumps(safe, ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n"

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
        encoded = fallback()
    if len(encoded) > MAX_HOOK_OUTPUT_BYTES:
        encoded = fallback()
    try:
        stream.write(encoded)  # type: ignore[arg-type]
    except TypeError:
        stream.write(encoded.decode("utf-8"))  # type: ignore[arg-type]
    stream.flush()


def run_hook_stdio(
    host: str,
    *,
    store: Store | None = None,
    db_path: str | None = None,
    config_path: str | None = None,
    expected_event: str = "",
    input_stream: BinaryIO | TextIO | None = None,
    output_stream: BinaryIO | TextIO | None = None,
    error_stream: TextIO | None = None,
) -> int:
    """Read one bounded event using its installer-bound expected event."""
    source = input_stream or sys.stdin.buffer
    sink = output_stream or sys.stdout.buffer
    errors = error_stream or sys.stderr

    from agency_runtime.core.runtime_control import read_enforcement_runtime_control

    master, _master_transport = read_enforcement_runtime_control()
    if not master["enabled"]:
        # Keep the native hook a true pass-through while Agency is off. In
        # particular, malformed or oversized Stop envelopes must not reach the
        # fail-closed completion policy and block an otherwise publishable host
        # response. Drain only the already bounded hook input for pipe hygiene;
        # its contents are deliberately neither parsed nor validated.
        with suppress(Exception):
            source.read(MAX_HOOK_INPUT_BYTES + 1)
        _write_output(sink, {})
        return 0

    payload: Any = None
    raw_bytes = b""
    oversized = False
    try:
        raw = source.read(MAX_HOOK_INPUT_BYTES + 1)
        raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
        if len(raw_bytes) > MAX_HOOK_INPUT_BYTES:
            oversized = True
            raise HookInputError("hook input exceeds the size limit")
        payload = safe_load_bounded_json(raw_bytes)
        if not isinstance(payload, dict):
            raise HookInputError("hook input must be one JSON object")
        if expected_event and payload.get("hook_event_name") != expected_event:
            raise HookInputError("hook event does not match the registered command")
        active_store = store
        if active_store is None and (db_path or config_path):
            active_store = (
                Store(db_path, config_path=config_path) if config_path else Store(db_path)
            )
        result = HookBridge(host, store=active_store, _master=master).handle(payload)
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
        result = _boundary_failure_result(
            payload,
            raw_bytes=raw_bytes,
            oversized=oversized,
            expected_event=expected_event,
        )
        outcome = "response publication blocked" if result else "host operation continues"
        print(f"agency hook {host}: {exc}; {outcome}", file=errors)
    except Exception as exc:  # Defensive boundary around adapters and storage.
        result = _boundary_failure_result(
            payload,
            raw_bytes=raw_bytes,
            oversized=oversized,
            expected_event=expected_event,
        )
        outcome = "response publication blocked" if result else "host operation continues"
        print(
            f"agency hook {host}: {type(exc).__name__}; {outcome}",
            file=errors,
        )

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
