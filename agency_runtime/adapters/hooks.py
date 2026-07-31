"""Native Codex and Claude Code hook protocol bridge.

Both hosts send one JSON object on stdin.  This module translates their
documented event fields into the shared adapter operations without depending on
a shell, transcript parsing, or host-private Python APIs.
"""

from __future__ import annotations

import json
import os
import re
import sys
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, BinaryIO, TextIO
from uuid import UUID, uuid4

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation.native_labels import (
    CODEX_TASK_NAME_PATTERN,
    codex_task_name_for_work_unit,
    internal_work_unit_from_codex_task_name,
)
from agency_runtime.core.header.finalize import (
    TERMINAL_ACTION_STATUS,
    TERMINAL_OUTCOME_MESSAGES,
)
from agency_runtime.core.installer_contracts import (
    CODEX_HOOK_EVENTS,
    CODEX_NATIVE_SPAWN_HOOK_TOOL_NAMES,
    CODEX_NATIVE_WAIT_HOOK_TOOL_NAMES,
)
from agency_runtime.core.native_child_activation import (
    NATIVE_CHILD_ACTIVATION_TOKEN_CHARS,
    NativeChildRunIdentity,
    build_native_child_run_identity,
)
from agency_runtime.core.native_child_prompt_delivery import (
    NativeChildPromptDelivery,
    parse_native_child_prompt_delivery,
    render_native_child_prompt_delivery,
)
from agency_runtime.core.observability import (
    RuntimeBoundary,
    correlate_current_observation,
    mark_current_observation,
)
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import (
    native_child_activation_contract,
    work_unit_goal_hash,
)

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


def _codex_hook_event_diagnostic_enabled(host: str, event: object) -> bool:
    if host != "codex" or event not in CODEX_HOOK_EVENTS:
        return False
    from agency_runtime.core.codex_activation_verification import (
        is_codex_hook_event_diagnostics_environment,
    )

    return is_codex_hook_event_diagnostics_environment(os.environ)


def _emit_codex_hook_event_diagnostic(
    errors: TextIO,
    event: str,
    stage: str,
) -> None:
    """Emit one fixed canary marker without affecting the hook boundary."""

    if not event:
        return
    with suppress(Exception):
        print(
            f"agency_hook_diagnostic codex_hook_event={event} stage={stage}",
            file=errors,
        )


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
        "functions.collaboration.spawn_agent",
        *CODEX_NATIVE_SPAWN_HOOK_TOOL_NAMES,
    }
)
_CLAUDE_AGENT_TOOL_NAME = "Agent"
_CLAUDE_CHILD_IDENTITY_MARKER = "[AGENCY NATIVE CHILD IDENTITY v1]"
_NATIVE_CHILD_DELIVERY_PLACEHOLDER_TOKEN = "x" * NATIVE_CHILD_ACTIVATION_TOKEN_CHARS
_PLANNED_NATIVE_WORK_UNIT_PATTERN = re.compile(r"^unit-[0-9a-f]{10}$")


def _emit_codex_reconciliation_diagnostic(
    reason: str,
    *,
    resolved_work_unit: str,
    delivery_activated: bool,
    store: Any,
    session_id: str,
    trace_id: str,
) -> None:
    """Emit one content-free rejection code only inside the activation canary."""

    if not reason or not resolved_work_unit or delivery_activated:
        return
    from agency_runtime.core.codex_activation_verification import (
        CODEX_RECONCILIATION_DIAGNOSTIC_REASONS,
        is_restricted_codex_activation_canary_environment,
    )

    if reason not in CODEX_RECONCILIATION_DIAGNOSTIC_REASONS:
        raise ValueError("Codex reconciliation diagnostic reason is invalid")
    if is_restricted_codex_activation_canary_environment(os.environ):
        recorder = getattr(store, "record_codex_canary_reconciliation_diagnostic", None)
        if not callable(recorder):
            raise RuntimeError("Codex canary diagnostic store is unavailable")
        recorder(
            session_id=session_id,
            trace_id=trace_id,
            reason=reason,
        )
        print(
            f"agency_hook_diagnostic codex_post_tool_reconcile={reason}",
            file=sys.stderr,
        )


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
    host: str = "",
) -> dict[str, Any]:
    """Block Agency-owned child launches and recognizable malformed Stop events."""

    if isinstance(payload, dict) and _agency_owned_native_child_pre_tool_use(payload, host):
        return _pre_tool_use_denial(_VERIFICATION_UNAVAILABLE, host=host)
    # Installed PreToolUse handlers are matcher-bound to the native child tool.
    # If the envelope is too large to parse, continuing would bypass the exact
    # specialist and one-use grant checks for an Agency-planned launch.
    if oversized and expected_event == "PreToolUse":
        return _pre_tool_use_denial(_VERIFICATION_UNAVAILABLE, host=host)

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
    # ZCode only recognizes {"decision": "block", ...}; the lifecycle shape is
    # silently ignored and would collapse this malformed-Stop block into a
    # pass-through accept. See AR-127.
    retry = host != "zcode"
    return _completion_rejection(
        _VERIFICATION_UNAVAILABLE,
        retry=retry,
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
class NativeChildAssignment:
    """One exact store-verified native child work-unit binding."""

    session_id: str
    trace_id: str
    tool_use_id: str
    work_unit_id: str
    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str
    goal_hash: str
    mutation_scope: str
    resource_hashes: tuple[str, ...]
    required_evidence: tuple[str, ...]


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


def _planned_native_work_unit_id(host: str, payload: dict[str, Any]) -> str:
    """Return only a canonical Agency-planned native-child label."""

    if payload.get("hook_event_name") != "PreToolUse":
        return ""
    tool_name = _optional_string(payload, "tool_name")
    args = _dict_or_empty(payload.get("tool_input"))
    if host == "codex":
        if tool_name not in _CODEX_SPAWN_TOOL_NAMES:
            return ""
        return internal_work_unit_from_codex_task_name(args.get("task_name"))
    if host not in {"claude", "zcode"} or tool_name != _CLAUDE_AGENT_TOOL_NAME:
        return ""
    native_label = _first_string(args, "description")
    return native_label if _PLANNED_NATIVE_WORK_UNIT_PATTERN.fullmatch(native_label) else ""


def _agency_owned_native_child_pre_tool_use(payload: dict[str, Any], host: str) -> bool:
    """Recognize a planned label or an already injected exact-delivery envelope."""

    if _planned_native_work_unit_id(host, payload):
        return True
    args = _dict_or_empty(payload.get("tool_input"))
    task_field = "message" if host == "codex" else "prompt"
    return parse_native_child_prompt_delivery(args.get(task_field)) is not None


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


def _zcode_native_child_identity(agent_id: object) -> NativeChildRunIdentity:
    """Derive the ZCode child lineage (same Agent-tool model as Claude)."""

    validated_agent_id = validate_correlation_id(agent_id, field="agent_id")
    return build_native_child_run_identity(
        worker_kind="generic-worker",
        worker_id=validated_agent_id,
        native_run_id=f"zcode-agent:{validated_agent_id}",
    )


def _native_child_identity(host: str, agent_id: object) -> NativeChildRunIdentity:
    """Own the host-to-lineage mapping used by every native-child boundary."""

    if host == "claude":
        return _claude_native_child_identity(agent_id)
    if host == "zcode":
        return _zcode_native_child_identity(agent_id)
    if host == "codex":
        return _codex_native_child_identity(agent_id)
    raise ValueError("unsupported native-child host")


def _native_child_backend(host: str) -> str:
    """Return the canonical native delegation backend for one hook host."""

    return "spawn_agent" if host == "codex" else "delegate_task"


def _pre_tool_use_denial(reason: object, *, host: str = "") -> dict[str, Any]:
    """Block a planned child that cannot receive its exact specialist."""

    bounded = _bounded_completion_reason(reason)
    if host == "zcode":
        return {"decision": "block", "reason": bounded}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": bounded,
        }
    }


def _native_child_response_mapping(host: str, tool_response: Any) -> dict[str, Any] | None:
    """Return one bounded host response mapping without inventing provenance."""

    projected_response = tool_response
    if host == "codex" and isinstance(tool_response, str):
        try:
            decoded = safe_load_bounded_json(
                tool_response,
                maximum_bytes=MAX_CONTEXT_CHARS,
                maximum_depth=8,
                maximum_nodes=64,
            )
        except (BoundedJSONError, TypeError, ValueError):
            return None
        if not isinstance(decoded, dict):
            return None
        projected_response = decoded
    if not isinstance(projected_response, dict):
        return None
    return projected_response


def _native_child_tool_identity(
    host: str,
    tool_response: Any,
    *,
    fallback_agent_id: object = "",
) -> tuple[Any, NativeChildRunIdentity | None]:
    """Project only host-returned child identity into activation evidence."""

    projected_response = _native_child_response_mapping(host, tool_response)
    if projected_response is None:
        return tool_response, None
    agent_id = (
        _first_string(projected_response, "agent_id", "agentId")
        or str(fallback_agent_id or "").strip()
    )
    if agent_id:
        try:
            identity = _native_child_identity(host, agent_id)
        except ValueError:
            return tool_response, None
        return (
            {
                **projected_response,
                "agent_id": identity.worker_id,
                "native_run_id": identity.native_run_id,
            },
            identity,
        )
    if host != "codex":
        return tool_response, None
    task_name = _first_string(projected_response, "task_name", "taskName")
    if not task_name:
        return tool_response, None
    if task_name.startswith("/root/"):
        path_parts = task_name.split("/")
        if (
            len(path_parts) < 3
            or path_parts[:2] != ["", "root"]
            or any(CODEX_TASK_NAME_PATTERN.fullmatch(part) is None for part in path_parts[2:])
        ):
            return tool_response, None
        task_name = path_parts[-1]
    if CODEX_TASK_NAME_PATTERN.fullmatch(task_name) is None:
        return tool_response, None
    try:
        identity = build_native_child_run_identity(
            worker_kind="generic-worker",
            worker_id=f"task:{task_name}",
            native_run_id=f"codex-task:{task_name}",
        )
    except ValueError:
        return tool_response, None
    return (
        {
            "task_name": task_name,
            "agent_id": identity.worker_id,
            "native_run_id": identity.native_run_id,
        },
        identity,
    )


def _native_child_pre_tool_output(
    *,
    args: dict[str, Any],
    task_field: str,
    task: str,
    prompt_body: str,
    host: str,
    assignment: NativeChildAssignment,
    activation_token: str,
) -> dict[str, Any]:
    """Render and size-check one pure hook response before Store mutation."""

    delivered_task = render_native_child_prompt_delivery(
        task,
        prompt_body,
        host=host,
        parent_session_id=assignment.session_id,
        parent_trace_id=assignment.trace_id,
        tool_use_id=assignment.tool_use_id,
        work_unit_id=assignment.work_unit_id,
        specialist_slug=assignment.specialist_slug,
        specialist_version=assignment.specialist_version,
        specialist_prompt_hash=assignment.specialist_prompt_hash,
        activation_token=activation_token,
    )
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**args, task_field: delivered_task},
        }
    }
    encoded = json.dumps(
        result,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) >= MAX_HOOK_OUTPUT_BYTES:
        raise ValueError("native-child delivery exceeds the host hook limit")
    return result


def _recover_codex_opaque_canary_task(
    host: str,
    task: str,
    *,
    expected_goal_hash: str,
) -> str:
    """Recover only the package-owned canary hidden by Codex encryption."""

    if host != "codex" or re.fullmatch(r"gAAAAA[A-Za-z0-9_-]{24,}={0,2}", task) is None:
        return ""
    from agency_runtime.core.activation_canary_contract import (
        CODEX_ACTIVATION_CANARY_WORK_UNIT,
    )

    return (
        CODEX_ACTIVATION_CANARY_WORK_UNIT
        if work_unit_goal_hash(CODEX_ACTIVATION_CANARY_WORK_UNIT) == expected_goal_hash
        else ""
    )


def _native_child_pre_tool_result(
    result: dict[str, Any],
    *,
    preserve_codex_input: bool,
) -> dict[str, Any]:
    """Keep opaque Codex tool input native while allowing the verified call."""

    if not preserve_codex_input:
        return result
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }


def _native_work_unit_label(host: str, tool_name: str, args: dict[str, Any]) -> str:
    """Return only an explicit Agency recipe label from official native args."""

    candidate = ""
    if host == "codex" and tool_name in _CODEX_SPAWN_TOOL_NAMES:
        # Resolution is store-bound in HookBridge so an arbitrary legal-looking
        # native label cannot invent a persisted Agency work unit.
        return ""
    elif host in {"claude", "zcode"} and tool_name == "Agent":
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
    if host in {"claude", "zcode"} and tool_name == "Agent":
        canonical_delegate = "delegate_task"
    elif host == "codex" and tool_name in _CODEX_SPAWN_TOOL_NAMES:
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
        if normalized_host not in {"codex", "claude", "zcode"}:
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

        # ADR-0087: zcode reuses the Claude hook model and Agent-tool delegation
        # primitive, so it shares the ClaudeAdapter behavior. But it must keep
        # its own host identity so runtime-control reads the zcode row (not
        # claude's) and all evidence receipts are attributed to zcode rather
        # than masqueraded as claude.
        adapter = ClaudeAdapter(store=self.store)
        if self.host == "zcode":
            adapter.host_name = "zcode"
        return adapter

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
            and row.get("action") in TERMINAL_ACTION_STATUS
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
        trace_id = correlation.trace_id
        run_reader = getattr(self.store, "get_run", None)
        if trace_id and callable(run_reader):
            try:
                candidate = run_reader(trace_id)
            except Exception:
                candidate = None
            if not (
                isinstance(candidate, dict)
                and candidate.get("session_id") == correlation.session_id
                and candidate.get("status") in {"active", "evidence_only"}
            ):
                trace_id = ""
        trace_id = trace_id or self._unambiguous_open_trace(correlation.session_id)
        return correlation.session_id, trace_id, correlation.work_unit_id

    def _issue_native_child_parent_scope(
        self,
        *,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        identity: NativeChildRunIdentity,
    ) -> dict[str, Any] | None:
        """Persist one explicit cross-process join receipt when parent evidence is exact."""

        if self.host not in {"codex", "claude"} or not session_id or not trace_id:
            return None
        issuer = getattr(self.store, "create_native_child_parent_scope", None)
        if not callable(issuer):
            return None
        child_session_id = f"{self.host}-child:{identity.worker_id}"
        try:
            receipt = issuer(
                host=self.host,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_kind=identity.worker_kind,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
                child_session_id=child_session_id,
            )
        except Exception:
            return None
        return receipt if isinstance(receipt, dict) else None

    def _record_native_child_lifecycle(
        self,
        payload: dict[str, Any],
        *,
        event: str,
    ) -> tuple[str, str, str, NativeChildRunIdentity] | None:
        """Validate and record one host-owned native-child lifecycle edge."""

        if event not in {"started", "stopped"}:
            raise ValueError("native-child lifecycle event is invalid")
        session_id, trace_id, work_unit_id = self._native_child_parent_scope(payload)
        _required_string(payload, "agent_type")
        try:
            identity = _native_child_identity(
                self.host,
                _required_string(payload, "agent_id"),
            )
        except ValueError:
            return None
        recorder = getattr(self.store, f"record_native_child_{event}", None)
        if callable(recorder) and trace_id:
            recorder(
                host=self.host,
                backend=_native_child_backend(self.host),
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
        return session_id, trace_id, work_unit_id, identity

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
        candidates.update(
            str(row.get("work_unit_id") or "").strip()
            for row in snapshot.get("unit_agent_plan", [])
            if isinstance(row, dict)
        )
        if not snapshot.get("unit_agent_plan"):
            candidates.update(
                f"specialist:{str(row.get('slug') or '').strip()}"
                for row in snapshot.get("selected_specialists", [])
                if isinstance(row, dict) and str(row.get("slug") or "").strip()
            )
        matches = [
            work_unit_id
            for work_unit_id in candidates
            if work_unit_id and codex_task_name_for_work_unit(work_unit_id) == task_name
        ]
        return matches[0] if len(matches) == 1 else ""

    @staticmethod
    def _assignment_from_snapshot(
        snapshot: Any,
        *,
        session_id: str,
        trace_id: str,
        tool_use_id: str,
        native_label: str,
        host: str,
        native_goal_hash: str = "",
    ) -> NativeChildAssignment | None:
        """Resolve one exact selected reference from one persisted plan snapshot."""

        if (
            not isinstance(snapshot, dict)
            or snapshot.get("session_id") != session_id
            or snapshot.get("trace_id") != trace_id
            or snapshot.get("status") not in {"active", "evidence_only"}
            or snapshot.get("delivery_mode") != "isolated"
        ):
            return None
        raw_references = snapshot.get("selected_specialists")
        raw_plan = snapshot.get("unit_agent_plan")
        if not isinstance(raw_references, list) or not isinstance(raw_plan, list):
            return None
        references: dict[str, dict[str, Any]] = {}
        for value in raw_references:
            if not isinstance(value, dict):
                return None
            slug = str(value.get("slug") or "").strip()
            version = str(value.get("version") or "").strip()
            content_hash = str(value.get("hash") or "").strip()
            if not slug or not version or not content_hash or slug in references:
                return None
            references[slug] = value

        candidates: list[tuple[str, str, str, str, tuple[str, ...], tuple[str, ...]]] = []
        if raw_plan:
            for row in raw_plan:
                if not isinstance(row, dict):
                    return None
                work_unit_id = str(row.get("work_unit_id") or "").strip()
                specialist_slug = str(row.get("recommended_agent") or "").strip()
                goal_hash = str(row.get("goal_hash") or "").strip().casefold()
                mutation_scope = str(row.get("mutation_scope") or "").strip().casefold()
                raw_resource_hashes = row.get("resource_hashes")
                raw_required_evidence = row.get("required_evidence")
                if (
                    not work_unit_id
                    or not specialist_slug
                    or re.fullmatch(r"[0-9a-f]{64}", goal_hash) is None
                    or not isinstance(raw_resource_hashes, list)
                    or not isinstance(raw_required_evidence, list)
                ):
                    return None
                expected_label = (
                    codex_task_name_for_work_unit(work_unit_id) if host == "codex" else work_unit_id
                )
                label_matches = bool(native_label) and expected_label == native_label
                goal_matches = (
                    host == "codex"
                    and not native_label
                    and bool(native_goal_hash)
                    and goal_hash == native_goal_hash
                )
                if label_matches or goal_matches:
                    candidates.append(
                        (
                            work_unit_id,
                            specialist_slug,
                            goal_hash,
                            mutation_scope,
                            tuple(str(item) for item in raw_resource_hashes),
                            tuple(str(item) for item in raw_required_evidence),
                        )
                    )
        else:
            # Legacy reference-only recipes have no authenticated goal binding.
            # Keep them replayable through explicit MCP activation, but never
            # inject their prompt into an arbitrary native-child task.
            return None
        if len(candidates) != 1:
            return None
        (
            work_unit_id,
            specialist_slug,
            goal_hash,
            mutation_scope,
            resource_hashes,
            required_evidence,
        ) = candidates[0]
        reference = references.get(specialist_slug)
        if reference is None:
            return None
        return NativeChildAssignment(
            session_id=session_id,
            trace_id=trace_id,
            tool_use_id=tool_use_id,
            work_unit_id=work_unit_id,
            specialist_slug=specialist_slug,
            specialist_version=str(reference["version"]),
            specialist_prompt_hash=str(reference["hash"]),
            goal_hash=goal_hash,
            mutation_scope=mutation_scope,
            resource_hashes=resource_hashes,
            required_evidence=required_evidence,
        )

    def _resolve_native_child_assignment(
        self,
        *,
        payload: dict[str, Any],
        tool_input: Any,
        trace_id: str = "",
    ) -> NativeChildAssignment | None:
        """Resolve one exact persisted row without callback-order correlation."""

        tool_name = _optional_string(payload, "tool_name")
        native_goal_hash = ""
        if self.host in {"claude", "zcode"}:
            if tool_name != _CLAUDE_AGENT_TOOL_NAME:
                return None
            native_label = _first_string(_dict_or_empty(tool_input), "description")
        else:
            if tool_name not in _CODEX_SPAWN_TOOL_NAMES:
                return None
            args = _dict_or_empty(tool_input)
            native_label = _first_string(args, "task_name")
            message = _first_string(args, "message")
            delivery = parse_native_child_prompt_delivery(message)
            original_message = delivery.original_task if delivery is not None else message
            native_goal_hash = (
                work_unit_goal_hash(original_message)
                if not native_label and original_message
                else ""
            )
        if not native_label and not (self.host == "codex" and native_goal_hash):
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
        return self._assignment_from_snapshot(
            snapshot,
            session_id=correlation.session_id,
            trace_id=resolved_trace,
            tool_use_id=correlation.tool_use_id,
            native_label=native_label,
            native_goal_hash=native_goal_hash if self.host == "codex" else "",
            host=self.host,
        )

    def _resolve_claude_child_assignment(
        self,
        *,
        payload: dict[str, Any],
        tool_input: Any,
        trace_id: str = "",
    ) -> NativeChildAssignment | None:
        """Compatibility wrapper for the shared exact native-child resolver."""

        if self.host != "claude":
            return None
        return self._resolve_native_child_assignment(
            payload=payload,
            tool_input=tool_input,
            trace_id=trace_id,
        )

    @staticmethod
    def _claude_post_tool_response(
        payload: dict[str, Any],
        tool_response: Any,
    ) -> tuple[Any, NativeChildRunIdentity | None]:
        """Compatibility wrapper around the canonical child identity projector."""

        return _native_child_tool_identity(
            "claude",
            tool_response,
            fallback_agent_id=_optional_string(payload, "agent_id"),
        )

    def _verify_existing_native_child_delivery(
        self,
        delivery: NativeChildPromptDelivery,
        assignment: NativeChildAssignment | None,
    ) -> dict[str, Any]:
        """Authenticate an idempotent hook replay against its pending Store grant."""

        verifier = getattr(self.store, "verify_pending_delegation_activation", None)
        identity_matches = assignment is not None and (
            delivery.host == self.host
            and delivery.parent_session_id == assignment.session_id
            and delivery.parent_trace_id == assignment.trace_id
            and delivery.tool_use_id == assignment.tool_use_id
            and delivery.work_unit_id == assignment.work_unit_id
            and delivery.specialist_slug == assignment.specialist_slug
            and delivery.specialist_version == assignment.specialist_version
            and delivery.specialist_prompt_hash == assignment.specialist_prompt_hash
            and work_unit_goal_hash(delivery.original_task) == assignment.goal_hash
        )
        if not identity_matches or not callable(verifier):
            return _pre_tool_use_denial(
                "Agency refused an unverified native-child prompt delivery; start a "
                "fresh Agency preflight.",
                host=self.host,
            )
        try:
            verified = verifier(
                activation_token=delivery.activation_token,
                host=delivery.host,
                session_id=delivery.parent_session_id,
                trace_id=delivery.parent_trace_id,
                work_unit_id=delivery.work_unit_id,
                specialist_slug=delivery.specialist_slug,
                specialist_version=delivery.specialist_version,
                specialist_prompt_hash=delivery.specialist_prompt_hash,
                grant_origin="native_hook",
                tool_use_id=delivery.tool_use_id,
            )
        except Exception:
            verified = False
        if verified is not True:
            return _pre_tool_use_denial(
                "Agency refused an invalid, expired, consumed, or unavailable "
                "native-child activation grant; start a fresh Agency preflight.",
                host=self.host,
            )
        return {}

    def _handle_native_child_pre_tool_use(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Inject one exact prompt while leaving the native scheduler in control."""

        tool_name = _required_string(payload, "tool_name")
        if self.host in {"claude", "zcode"} and tool_name != _CLAUDE_AGENT_TOOL_NAME:
            return {}
        if self.host == "codex" and tool_name not in _CODEX_SPAWN_TOOL_NAMES:
            return {}
        tool_input = payload.get("tool_input")
        args = _dict_or_empty(tool_input)
        task_field = "prompt" if self.host in {"claude", "zcode"} else "message"
        task = args.get(task_field)
        if not isinstance(task, str) or not task:
            raise HookInputError(f"{tool_name} tool_input.{task_field} is required")
        delivery = parse_native_child_prompt_delivery(task)
        assignment = self._resolve_native_child_assignment(
            payload=payload,
            tool_input=tool_input,
        )
        if delivery is not None:
            return self._verify_existing_native_child_delivery(delivery, assignment)
        if assignment is None:
            if _planned_native_work_unit_id(self.host, payload):
                return _pre_tool_use_denial(
                    "Agency could not verify this planned native child in the evidence "
                    "Store; it was not launched as an untyped substitute.",
                    host=self.host,
                )
            return {}
        opaque_codex_task = False
        if work_unit_goal_hash(task) != assignment.goal_hash:
            recovered = _recover_codex_opaque_canary_task(
                self.host,
                task,
                expected_goal_hash=assignment.goal_hash,
            )
            if recovered:
                # Codex persists an opaque spawn message in current-profile
                # rollouts. The closed-world canary goal is package-owned, and
                # the unencrypted native task label already resolved exactly
                # one persisted assignment, so recover that constant without
                # weakening ordinary goal equality.
                task = recovered
                opaque_codex_task = True
            else:
                return _pre_tool_use_denial(
                    "Agency refused this native child because its task does not exactly match "
                    "the persisted work-unit goal. Use the exact goal from the delegation plan.",
                    host=self.host,
                )
        try:
            activation_contract = native_child_activation_contract(
                task,
                mutation_scope=assignment.mutation_scope,
                resource_hashes=assignment.resource_hashes,
                required_evidence=assignment.required_evidence,
            )
        except ValueError:
            return _pre_tool_use_denial(
                "Agency could not verify this native child's planned mutation and evidence "
                "boundary. Use the exact current delegation plan.",
                host=self.host,
            )
        prompt_reader = getattr(self.store, "get_versioned_specialist_prompt", None)
        preparer = getattr(self.store, "prepare_delegation_activation", None)
        if not callable(prompt_reader) or not callable(preparer):
            return _pre_tool_use_denial(
                "Agency could not access the exact planned specialist; the native child "
                "was not launched as an untyped substitute.",
                host=self.host,
            )
        prompt = prompt_reader(
            assignment.specialist_slug,
            assignment.specialist_version,
            assignment.specialist_prompt_hash,
            max_chars=MAX_SPECIALIST_PROMPT_CHARS,
        )
        if (
            not isinstance(prompt, dict)
            or prompt.get("prompt_truncated") is not False
            or prompt.get("version") != assignment.specialist_version
            or prompt.get("hash") != assignment.specialist_prompt_hash
            or not isinstance(prompt.get("prompt_body"), str)
            or not prompt["prompt_body"]
        ):
            return _pre_tool_use_denial(
                f"Agency could not verify {assignment.specialist_slug}'s exact selected "
                "prompt version; the planned native child was not launched.",
                host=self.host,
            )
        try:
            _native_child_pre_tool_output(
                args=args,
                task_field=task_field,
                task=task,
                prompt_body=prompt["prompt_body"],
                host=self.host,
                assignment=assignment,
                activation_token=_NATIVE_CHILD_DELIVERY_PLACEHOLDER_TOKEN,
            )
        except ValueError:
            return _pre_tool_use_denial(
                "Agency's exact child context exceeds the host hook limit; split the "
                "work unit or use a smaller audited specialist prompt.",
                host=self.host,
            )
        try:
            activation = preparer(
                session_id=assignment.session_id,
                trace_id=assignment.trace_id,
                specialist_slug=assignment.specialist_slug,
                work_unit_id=assignment.work_unit_id,
                worker_kind="generic-worker",
                grant_origin="native_hook",
                tool_use_id=assignment.tool_use_id,
                **activation_contract,
            )
            if (
                activation.get("version") != assignment.specialist_version
                or activation.get("prompt_hash") != assignment.specialist_prompt_hash
            ):
                raise ValueError("prepared activation identity does not match the plan")
            activation_token = str(activation.get("activation_token") or "")
            result = _native_child_pre_tool_output(
                args=args,
                task_field=task_field,
                task=task,
                prompt_body=prompt["prompt_body"],
                host=self.host,
                assignment=assignment,
                activation_token=activation_token,
            )
        except (RuntimeError, ValueError):
            return _pre_tool_use_denial(
                f"Agency could not issue {assignment.specialist_slug}'s one-use activation; "
                "the planned native child was not launched.",
                host=self.host,
            )
        # Codex owns decryption and dispatch of collaboration messages. An
        # updatedInput replacement leaves both the injected plaintext and the
        # original encrypted block in the child envelope, which current Codex
        # rejects during decryption. Preserve opaque native input exactly;
        # SubagentStart retrieves the persisted grant and injects the context.
        return _native_child_pre_tool_result(
            result,
            preserve_codex_input=opaque_codex_task,
        )

    def _handle_claude_subagent_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Give this child its own identity without assigning any specialist."""

        lifecycle = self._record_native_child_lifecycle(payload, event="started")
        if lifecycle is None:
            return {}
        session_id, trace_id, work_unit_id, identity = lifecycle
        parent_scope = self._issue_native_child_parent_scope(
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=work_unit_id,
            identity=identity,
        )
        context_lines = [
            _CLAUDE_CHILD_IDENTITY_MARKER,
            "This identity belongs only to the current native child. It does not "
            "load, select, or inherit an Agency specialist.",
            f"worker_kind={json.dumps(identity.worker_kind)}",
            f"worker_id={json.dumps(identity.worker_id, ensure_ascii=True)}",
            f"native_run_id={json.dumps(identity.native_run_id, ensure_ascii=True)}",
            "A planned child receives [AGENCY EXACT SPECIALIST ACTIVATION v1] "
            "instructions directly in its native task through the installed PreToolUse "
            "hook. Follow that exact prompt when present; no prepare/load tool calls are "
            "required. Otherwise make no Agency specialist claim until independently "
            "calling agency.preflight with the complete delegated assignment.",
        ]
        if parent_scope is not None:
            context_lines.append(
                "To join the parent budget, cache, and singleflight controls exactly once, "
                "call agency.preflight before substantive unplanned work with "
                f"session_id={json.dumps(parent_scope['child_session_id'], ensure_ascii=True)}, "
                f"host={json.dumps(self.host)}, the complete delegated assignment as "
                "user_message, and "
                f"parent_scope_token={json.dumps(parent_scope['parent_scope_token'], ensure_ascii=True)}. "
                "Do not send parent_session_id or parent_trace_id; the Store receipt owns "
                "that authority."
            )
        else:
            context_lines.append(
                "An exact parent-scope receipt is unavailable. Route independently and do "
                "not claim or reuse parent budget, cache, lineage, or specialist evidence."
            )
        context = "\n".join(context_lines)
        return {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        }

    def _handle_claude_subagent_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate lifecycle identity without inventing an undocumented parent join."""

        self._record_native_child_lifecycle(payload, event="stopped")
        return {}

    def _handle_codex_subagent_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Inject exact identity and any unambiguous staged Codex delivery."""

        lifecycle = self._record_native_child_lifecycle(payload, event="started")
        if lifecycle is None:
            return {}
        session_id, trace_id, work_unit_id, identity = lifecycle
        parent_scope = self._issue_native_child_parent_scope(
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=work_unit_id,
            identity=identity,
        )
        child_session_id = f"codex-child:{identity.worker_id}"
        exact_delivery = ""
        pending_reader = getattr(self.store, "get_pending_native_hook_delivery", None)
        if callable(pending_reader) and trace_id:
            try:
                pending = pending_reader(
                    host="codex",
                    session_id=session_id,
                    trace_id=trace_id,
                    worker_id=identity.worker_id,
                    native_run_id=identity.native_run_id,
                )
            except (RuntimeError, ValueError):
                pending = None
            if isinstance(pending, dict):
                from agency_runtime.core.activation_canary_contract import (
                    CODEX_ACTIVATION_CANARY_WORK_UNIT,
                )

                try:
                    snapshot = self.store.get_completion_evidence_snapshot(
                        session_id,
                        trace_id,
                    )
                    assignment = self._assignment_from_snapshot(
                        snapshot,
                        session_id=session_id,
                        trace_id=trace_id,
                        tool_use_id=str(pending.get("tool_use_id") or ""),
                        native_label=codex_task_name_for_work_unit(
                            str(pending.get("work_unit_id") or "")
                        ),
                        host="codex",
                    )
                    pending_identity = (
                        str(pending.get("work_unit_id") or ""),
                        str(pending.get("slug") or ""),
                        str(pending.get("version") or ""),
                        str(pending.get("prompt_hash") or ""),
                    )
                    assignment_identity = (
                        assignment.work_unit_id if assignment is not None else "",
                        assignment.specialist_slug if assignment is not None else "",
                        assignment.specialist_version if assignment is not None else "",
                        assignment.specialist_prompt_hash if assignment is not None else "",
                    )
                    if (
                        assignment is None
                        or pending_identity != assignment_identity
                        or assignment.goal_hash
                        != work_unit_goal_hash(CODEX_ACTIVATION_CANARY_WORK_UNIT)
                    ):
                        raise ValueError("pending Codex delivery does not match the canary plan")
                    exact_delivery = render_native_child_prompt_delivery(
                        CODEX_ACTIVATION_CANARY_WORK_UNIT,
                        str(pending.get("prompt_body") or ""),
                        host="codex",
                        parent_session_id=session_id,
                        parent_trace_id=trace_id,
                        tool_use_id=assignment.tool_use_id,
                        work_unit_id=assignment.work_unit_id,
                        specialist_slug=assignment.specialist_slug,
                        specialist_version=assignment.specialist_version,
                        specialist_prompt_hash=assignment.specialist_prompt_hash,
                        activation_token=_NATIVE_CHILD_DELIVERY_PLACEHOLDER_TOKEN,
                    )
                    activation = self.store.consume_delegation_activation(
                        activation_token="",
                        native_hook_tool_use_id=assignment.tool_use_id,
                        session_id=session_id,
                        trace_id=trace_id,
                        specialist_slug=assignment.specialist_slug,
                        work_unit_id=assignment.work_unit_id,
                        worker_id=identity.worker_id,
                        native_run_id=identity.native_run_id,
                        require_native_child_started=True,
                        match_native_child_identity=True,
                    )
                    if (
                        activation.get("slug") != assignment.specialist_slug
                        or activation.get("version") != assignment.specialist_version
                        or activation.get("prompt_hash") != assignment.specialist_prompt_hash
                        or activation.get("prompt_body") != pending.get("prompt_body")
                        or activation.get("worker_kind") != identity.worker_kind
                        or activation.get("worker_id") != identity.worker_id
                        or activation.get("native_run_id") != identity.native_run_id
                    ):
                        raise ValueError("Codex child activation receipt did not match delivery")
                except (KeyError, RuntimeError, ValueError):
                    exact_delivery = ""
        if exact_delivery:
            if len(exact_delivery) > MAX_CONTEXT_CHARS:
                exact_delivery = (
                    _CLAUDE_CHILD_IDENTITY_MARKER
                    + "\nAgency could not deliver the exact specialist context within the "
                    "host limit. Stop this child without substantive work."
                )
            return {
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": exact_delivery,
                }
            }
        context_lines = [
            _CLAUDE_CHILD_IDENTITY_MARKER,
            "This identity belongs only to the current native Codex child. It does not "
            "load, select, or inherit an Agency specialist.",
            f"worker_kind={json.dumps(identity.worker_kind)}",
            f"worker_id={json.dumps(identity.worker_id, ensure_ascii=True)}",
            f"native_run_id={json.dumps(identity.native_run_id, ensure_ascii=True)}",
            "If no current recipe is present, independently call agency.preflight "
            "before substantive work using the complete delegated assignment as "
            "user_message and "
            f"session_id={json.dumps(child_session_id, ensure_ascii=True)}.",
        ]
        if parent_scope is not None:
            context_lines.append(
                "To join the parent controls exactly once, include "
                f"parent_scope_token={json.dumps(parent_scope['parent_scope_token'], ensure_ascii=True)} "
                "in that same agency.preflight call. Do not send parent_session_id or "
                "parent_trace_id; the Store receipt owns that authority."
            )
        else:
            context_lines.append(
                "An exact parent-scope receipt is unavailable. Route independently and do "
                "not claim or reuse parent budget, cache, lineage, or specialist evidence."
            )
        context_lines.append(
            "Apply only the returned child-turn context. Do not claim parent Agency "
            "delegation without an authoritative activation receipt."
        )
        context = "\n".join(context_lines)
        if len(context) > MAX_CONTEXT_CHARS:
            context = (
                _CLAUDE_CHILD_IDENTITY_MARKER
                + "\nAgency could not deliver the exact specialist context within the "
                "host limit. Stop this child without substantive work."
            )
        return {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        }

    def _handle_codex_subagent_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Close an exact Codex child only when the host supplies its final message."""

        lifecycle = self._record_native_child_lifecycle(payload, event="stopped")
        final_message = _optional_string(payload, "last_assistant_message")
        if lifecycle is None or not final_message.strip():
            return {}
        session_id, trace_id, work_unit_id, identity = lifecycle
        recorder = getattr(self.store, "record_native_child_ended", None)
        if callable(recorder) and trace_id:
            recorder(
                host=self.host,
                backend=_native_child_backend(self.host),
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
                outcome="ok",
            )
        return {}

    def _reconcile_consumed_codex_child(
        self,
        *,
        payload: dict[str, Any],
        tool_input: Any,
        tool_response: Any,
        trace_id: str,
        work_unit_id: str,
    ) -> tuple[tuple[str, Any, NativeChildRunIdentity] | None, str]:
        """Recover only an exact SubagentStart-consumed Codex child projection."""

        tool_name = _optional_string(payload, "tool_name")
        if (
            self.host != "codex"
            or tool_name not in CODEX_NATIVE_SPAWN_HOOK_TOOL_NAMES
            or not trace_id
            or not work_unit_id
        ):
            return None, "boundary_mismatch"
        correlation = self._correlation(payload, tool_input, tool_response)
        if not correlation.session_id:
            return None, "session_unavailable"
        task_name = _first_string(_dict_or_empty(tool_input), "task_name", "taskName")
        expected_task_name = codex_task_name_for_work_unit(work_unit_id)
        if task_name and task_name not in {
            expected_task_name,
            f"/root/{expected_task_name}",
        }:
            return None, "task_label_mismatch"
        raw_response = _native_child_response_mapping("codex", tool_response)
        projected_response, synthetic_identity = _native_child_tool_identity(
            "codex",
            tool_response,
        )
        if raw_response is None or synthetic_identity is None:
            return None, "response_identity_unavailable"
        raw_task_name = _first_string(raw_response, "task_name", "taskName")
        if (
            set(raw_response) not in ({"task_name"}, {"task_name", "nickname"})
            or not raw_task_name.startswith("/root/")
            or _first_string(projected_response, "task_name", "taskName") != expected_task_name
        ):
            return None, "response_shape_mismatch"
        try:
            snapshot = self.store.get_completion_evidence_snapshot(
                correlation.session_id,
                trace_id,
            )
        except (RuntimeError, ValueError):
            return None, "snapshot_unavailable"
        plans = [
            row
            for row in snapshot.get("unit_agent_plan", [])
            if isinstance(row, dict) and row.get("work_unit_id") == work_unit_id
        ]
        if len(plans) != 1:
            return None, "plan_cardinality_mismatch"
        specialist_slug = str(plans[0].get("recommended_agent") or "")
        references = [
            row
            for row in snapshot.get("selected_specialists", [])
            if isinstance(row, dict) and row.get("slug") == specialist_slug
        ]
        activations = [
            row
            for row in snapshot.get("specialist_activations", [])
            if isinstance(row, dict)
            and row.get("work_unit_id") == work_unit_id
            and row.get("specialist_slug") == specialist_slug
            and row.get("consumed_at")
        ]
        if len(references) != 1 or len(activations) != 1:
            # Parent PostToolUse currently precedes child SubagentStart, so one
            # reference with no activation is pending rather than rejected.
            reason = {
                (1, 0): "",
            }.get(
                (len(references), len(activations)),
                "reference_activation_cardinality_mismatch",
            )
            return None, reason
        reference = references[0]
        activation = activations[0]
        if activation.get("specialist_version") != reference.get("version") or activation.get(
            "specialist_prompt_hash"
        ) != reference.get("hash"):
            return None, "reference_activation_mismatch"
        lineage_reader = getattr(self.store, "get_consumed_delegation_lineage", None)
        if not callable(lineage_reader):
            return None, "lineage_reader_unavailable"
        try:
            lineage = lineage_reader(
                session_id=correlation.session_id,
                trace_id=trace_id,
                specialist_slug=specialist_slug,
                work_unit_id=work_unit_id,
            )
        except (RuntimeError, ValueError):
            return None, "lineage_unavailable"
        expected_lineage = {
            "worker_kind": str(activation.get("worker_kind") or ""),
            "worker_id": str(activation.get("worker_id") or ""),
            "native_run_id": str(activation.get("native_run_id") or ""),
        }
        if lineage != expected_lineage:
            return None, "lineage_mismatch"
        try:
            identity = build_native_child_run_identity(**expected_lineage)
        except (TypeError, ValueError):
            return None, "identity_invalid"
        if (
            identity.worker_id.startswith("task:")
            or identity.native_run_id != f"codex-agent:{identity.worker_id}"
        ):
            return None, "identity_synthetic"
        return (
            (
                specialist_slug,
                {
                    **projected_response,
                    "agent_id": identity.worker_id,
                    "native_run_id": identity.native_run_id,
                },
                identity,
            ),
            "",
        )

    @staticmethod
    def _reconciled_codex_projection(
        reconciled: tuple[str, Any, NativeChildRunIdentity] | None,
        tool_response: Any,
        identity: NativeChildRunIdentity | None,
    ) -> tuple[str, Any, NativeChildRunIdentity | None]:
        """Use an exact replay projection or preserve the ordinary hook result."""

        if reconciled is None:
            return "", tool_response, identity
        return reconciled

    def _resolve_codex_post_tool_unit(
        self,
        *,
        tool_name: str,
        tool_input: Any,
        tool_response: Any,
        session_id: str,
        trace_id: str,
    ) -> str:
        """Resolve a planned unit from exact input or bounded native output."""

        resolved = self._resolve_codex_task_name(
            tool_name=tool_name,
            tool_input=tool_input,
            session_id=session_id,
            trace_id=trace_id,
        )
        if resolved:
            return resolved
        response_projection, _response_identity = _native_child_tool_identity(
            "codex",
            tool_response,
        )
        response_task_name = _first_string(
            _dict_or_empty(response_projection),
            "task_name",
            "taskName",
        )
        return self._resolve_codex_task_name(
            tool_name=tool_name,
            tool_input={"task_name": response_task_name},
            session_id=session_id,
            trace_id=trace_id,
        )

    def _consume_native_child_prompt_delivery(
        self,
        *,
        event: str,
        payload: dict[str, Any],
        tool_input: Any,
        tool_response: Any,
        trace_id: str,
    ) -> tuple[NativeChildPromptDelivery | None, Any, NativeChildRunIdentity | None, bool]:
        """Consume a hook-issued grant only after authoritative native execution."""

        args = _dict_or_empty(tool_input)
        raw_task = args.get("prompt" if self.host in {"claude", "zcode"} else "message")
        task = raw_task if isinstance(raw_task, str) else ""
        delivery, native_hook_without_token = self._native_child_delivery(
            payload=payload,
            tool_input=tool_input,
            task=task,
            trace_id=trace_id,
        )
        if delivery is None:
            return None, tool_response, None, False
        correlation = self._correlation(payload, tool_input, tool_response)
        assignment = self._resolve_native_child_assignment(
            payload=payload,
            tool_input=tool_input,
            trace_id=trace_id,
        )
        expected = (
            self.host,
            correlation.session_id,
            trace_id,
            correlation.tool_use_id,
            assignment.work_unit_id if assignment is not None else "",
            assignment.specialist_slug if assignment is not None else "",
            assignment.specialist_version if assignment is not None else "",
            assignment.specialist_prompt_hash if assignment is not None else "",
        )
        observed = (
            delivery.host,
            delivery.parent_session_id,
            delivery.parent_trace_id,
            delivery.tool_use_id,
            delivery.work_unit_id,
            delivery.specialist_slug,
            delivery.specialist_version,
            delivery.specialist_prompt_hash,
        )
        if (
            event != "PostToolUse"
            or assignment is None
            or observed != expected
            or work_unit_goal_hash(delivery.original_task) != assignment.goal_hash
        ):
            return delivery, tool_response, None, False
        raw_response = _native_child_response_mapping(self.host, tool_response)
        projected_response, identity = _native_child_tool_identity(self.host, tool_response)
        if identity is None:
            return delivery, projected_response, None, False
        if self.host == "codex":
            response_task_name = _first_string(projected_response, "task_name", "taskName")
            expected_task_name = _first_string(args, "task_name", "taskName")
            tool_name = _optional_string(payload, "tool_name")
            raw_task_name = _first_string(raw_response or {}, "task_name", "taskName")
            if tool_name == "collaborationspawn_agent" and (
                raw_response is None
                or set(raw_response) not in ({"task_name"}, {"task_name", "nickname"})
                or not raw_task_name.startswith("/root/")
                or response_task_name != expected_task_name
                or set(projected_response) != {"task_name", "agent_id", "native_run_id"}
            ):
                return delivery, projected_response, identity, False
            if response_task_name and response_task_name != expected_task_name:
                return delivery, projected_response, identity, False
        require_native_child_started = (
            self.host == "codex"
            and _optional_string(payload, "tool_name") in CODEX_NATIVE_SPAWN_HOOK_TOOL_NAMES
        )
        response_supplied_agent_id = bool(_first_string(raw_response or {}, "agent_id", "agentId"))
        lineage = {
            "worker_kind": identity.worker_kind,
            "worker_id": identity.worker_id,
            "native_run_id": identity.native_run_id,
        }
        consumer = getattr(self.store, "consume_delegation_activation", None)
        if not callable(consumer):
            return delivery, projected_response, identity, False
        try:
            activation = consumer(
                activation_token=("" if native_hook_without_token else delivery.activation_token),
                native_hook_tool_use_id=(delivery.tool_use_id if native_hook_without_token else ""),
                session_id=delivery.parent_session_id,
                trace_id=delivery.parent_trace_id,
                specialist_slug=delivery.specialist_slug,
                work_unit_id=delivery.work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
                require_native_child_started=require_native_child_started,
                match_native_child_identity=response_supplied_agent_id,
            )
        except ValueError:
            lineage_reader = getattr(self.store, "get_consumed_delegation_lineage", None)
            if not callable(lineage_reader):
                return delivery, projected_response, identity, False
            existing = lineage_reader(
                session_id=delivery.parent_session_id,
                trace_id=delivery.parent_trace_id,
                specialist_slug=delivery.specialist_slug,
                work_unit_id=delivery.work_unit_id,
                activation_token=("" if native_hook_without_token else delivery.activation_token),
                tool_use_id=delivery.tool_use_id,
            )
            if require_native_child_started and isinstance(existing, dict):
                if response_supplied_agent_id and existing != lineage:
                    return delivery, projected_response, identity, False
                try:
                    identity = build_native_child_run_identity(
                        worker_kind=existing["worker_kind"],
                        worker_id=existing["worker_id"],
                        native_run_id=existing["native_run_id"],
                    )
                except (KeyError, TypeError, ValueError):
                    return delivery, projected_response, None, False
                projected_response = {
                    **projected_response,
                    "agent_id": identity.worker_id,
                    "native_run_id": identity.native_run_id,
                }
                return delivery, projected_response, identity, True
            return delivery, projected_response, identity, existing == lineage
        if require_native_child_started:
            try:
                identity = build_native_child_run_identity(
                    worker_kind=activation["worker_kind"],
                    worker_id=activation["worker_id"],
                    native_run_id=activation["native_run_id"],
                )
            except (KeyError, TypeError, ValueError):
                return delivery, projected_response, None, False
            projected_response = {
                **projected_response,
                "agent_id": identity.worker_id,
                "native_run_id": identity.native_run_id,
            }
        verified = (
            isinstance(activation, dict)
            and activation.get("slug") == delivery.specialist_slug
            and activation.get("version") == delivery.specialist_version
            and activation.get("prompt_hash") == delivery.specialist_prompt_hash
            and activation.get("prompt_body") == delivery.prompt_body
            and activation.get("worker_kind") == identity.worker_kind
            and activation.get("worker_id") == identity.worker_id
            and activation.get("native_run_id") == identity.native_run_id
        )
        return delivery, projected_response, identity, verified

    def _native_child_delivery(
        self,
        *,
        payload: dict[str, Any],
        tool_input: Any,
        task: str,
        trace_id: str,
    ) -> tuple[NativeChildPromptDelivery | None, bool]:
        """Parse plaintext delivery or recover one opaque Codex canary delivery."""

        delivery = parse_native_child_prompt_delivery(task)
        if delivery is not None:
            return delivery, False
        delivery = self._codex_opaque_native_child_delivery(
            payload=payload,
            tool_input=tool_input,
            task=task,
            trace_id=trace_id,
        )
        return delivery, delivery is not None

    def _codex_opaque_native_child_delivery(
        self,
        *,
        payload: dict[str, Any],
        tool_input: Any,
        task: str,
        trace_id: str,
    ) -> NativeChildPromptDelivery | None:
        """Rebuild non-secret delivery evidence for one opaque Codex canary call."""

        if self.host != "codex":
            return None
        assignment = self._resolve_native_child_assignment(
            payload=payload,
            tool_input=tool_input,
            trace_id=trace_id,
        )
        recovered = (
            _recover_codex_opaque_canary_task(
                self.host,
                task,
                expected_goal_hash=assignment.goal_hash,
            )
            if assignment is not None
            else ""
        )
        prompt_reader = getattr(self.store, "get_versioned_specialist_prompt", None)
        if assignment is None or not recovered or not callable(prompt_reader):
            return None
        prompt = prompt_reader(
            assignment.specialist_slug,
            assignment.specialist_version,
            assignment.specialist_prompt_hash,
            max_chars=MAX_SPECIALIST_PROMPT_CHARS,
        )
        if (
            not isinstance(prompt, dict)
            or prompt.get("prompt_truncated") is not False
            or prompt.get("version") != assignment.specialist_version
            or prompt.get("hash") != assignment.specialist_prompt_hash
            or not isinstance(prompt.get("prompt_body"), str)
            or not prompt["prompt_body"]
        ):
            return None
        rendered = render_native_child_prompt_delivery(
            recovered,
            prompt["prompt_body"],
            host="codex",
            parent_session_id=assignment.session_id,
            parent_trace_id=assignment.trace_id,
            tool_use_id=assignment.tool_use_id,
            work_unit_id=assignment.work_unit_id,
            specialist_slug=assignment.specialist_slug,
            specialist_version=assignment.specialist_version,
            specialist_prompt_hash=assignment.specialist_prompt_hash,
            activation_token=_NATIVE_CHILD_DELIVERY_PLACEHOLDER_TOKEN,
        )
        return parse_native_child_prompt_delivery(rendered)

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
        if (
            self.host in {"claude", "zcode"}
            and tool_name == _CLAUDE_AGENT_TOOL_NAME
            and not turn_trace_id
        ):
            return {}
        trace_id = turn_trace_id or correlation.tool_use_id
        canonical_name, canonical_args = _canonical_tool_call(
            self.host,
            tool_name,
            tool_input,
            tool_response,
        )
        observed_tool_response = tool_response
        delivery: NativeChildPromptDelivery | None = None
        _delivery_identity: NativeChildRunIdentity | None = None
        delivery_activated = False
        if (self.host in {"claude", "zcode"} and tool_name == _CLAUDE_AGENT_TOOL_NAME) or (
            self.host == "codex" and tool_name in _CODEX_SPAWN_TOOL_NAMES
        ):
            delivery, tool_response, _delivery_identity, delivery_activated = (
                self._consume_native_child_prompt_delivery(
                    event=event,
                    payload=payload,
                    tool_input=tool_input,
                    tool_response=tool_response,
                    trace_id=trace_id,
                )
            )
        resolved_codex_unit = self._resolve_codex_post_tool_unit(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_response=observed_tool_response,
            session_id=correlation.session_id,
            trace_id=trace_id,
        )
        reconciled_codex_specialist = ""
        reconciled, reconciliation_rejection = self._reconcile_consumed_codex_child(
            payload=payload,
            tool_input=tool_input,
            tool_response=observed_tool_response,
            trace_id=trace_id,
            work_unit_id=resolved_codex_unit if not delivery_activated else "",
        )
        _emit_codex_reconciliation_diagnostic(
            reconciliation_rejection,
            resolved_work_unit=resolved_codex_unit,
            delivery_activated=delivery_activated,
            store=self.store,
            session_id=correlation.session_id,
            trace_id=trace_id,
        )
        reconciled_codex_specialist, tool_response, _delivery_identity = (
            self._reconciled_codex_projection(
                reconciled,
                tool_response,
                _delivery_identity,
            )
        )
        if self.host in {"claude", "zcode"} and tool_name == _CLAUDE_AGENT_TOOL_NAME:
            assignment = self._resolve_native_child_assignment(
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
            if delivery is not None and delivery_activated:
                canonical_args["goal"] = delivery.original_task
            elif not isinstance(tool_response, dict) or not _first_string(
                tool_response, "native_run_id"
            ):
                if self.host == "claude":
                    tool_response, _identity = self._claude_post_tool_response(
                        payload,
                        tool_response,
                    )
                else:
                    tool_response, _identity = _native_child_tool_identity(
                        "zcode",
                        tool_response,
                    )
        elif self.host == "codex" and tool_name in _CODEX_SPAWN_TOOL_NAMES:
            if delivery is not None and delivery_activated:
                canonical_args["agent"] = delivery.specialist_slug
                canonical_args["work_unit_id"] = delivery.work_unit_id
                canonical_args["goal"] = delivery.original_task
            elif reconciled_codex_specialist:
                canonical_args["agent"] = reconciled_codex_specialist
                canonical_args["work_unit_id"] = resolved_codex_unit
            elif not isinstance(tool_response, dict) or not _first_string(
                tool_response, "native_run_id"
            ):
                tool_response, _identity = _native_child_tool_identity(
                    "codex",
                    tool_response,
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
        return self._codex_post_tool_header_output(
            event=event,
            tool_name=tool_name,
            tool_response=observed_tool_response,
            session_id=correlation.session_id,
            trace_id=trace_id,
            model=correlation.model,
        )

    def _codex_post_tool_header_output(
        self,
        *,
        event: str,
        tool_name: str,
        tool_response: Any,
        session_id: str,
        trace_id: str,
        model: str,
    ) -> dict[str, Any]:
        """Return the latest bounded Codex header after recorded tool evidence."""

        context = self._codex_post_wait_header_context(
            event=event,
            tool_name=tool_name,
            tool_response=tool_response,
            session_id=session_id,
            trace_id=trace_id,
            model=model,
        )
        if not context:
            context = self._codex_header_snapshot_context(
                session_id=session_id,
                trace_id=trace_id,
                model=model,
                marker="UPDATED",
                instruction=(
                    "Agency recorded the preceding tool observation. Start the next "
                    "substantive or final parent response with these exact seven lines, "
                    "unchanged, then add the response body. A later Agency header snapshot "
                    "for this turn supersedes this one."
                ),
            )
        if not context:
            return {}
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context[:MAX_CONTEXT_CHARS],
            }
        }

    def _codex_post_wait_header_context(
        self,
        *,
        event: str,
        tool_name: str,
        tool_response: Any,
        session_id: str,
        trace_id: str,
        model: str,
    ) -> str:
        """Render the authoritative header immediately after a successful Codex wait."""

        if (
            self.host != "codex"
            or event != "PostToolUse"
            or tool_name not in CODEX_NATIVE_WAIT_HOOK_TOOL_NAMES
            or not session_id
            or not trace_id
        ):
            return ""
        response = _native_child_response_mapping("codex", tool_response)
        if (
            response is None
            or response.get("timed_out") is not False
            or _first_string(response, "message") != "Wait completed."
        ):
            return ""
        return self._codex_header_snapshot_context(
            session_id=session_id,
            trace_id=trace_id,
            model=model,
            marker="FINAL",
            instruction=(
                "The native wait completed. Start the next substantive or final parent "
                "response with these exact seven lines, unchanged, then add the response "
                "body. This is current-turn Store evidence, not a suggested draft."
            ),
        )

    def _codex_header_snapshot_context(
        self,
        *,
        session_id: str,
        trace_id: str,
        model: str,
        marker: str,
        instruction: str,
    ) -> str:
        """Render one exact current-turn header without manufacturing evidence."""

        if self.host != "codex" or not session_id or not trace_id:
            return ""
        from agency_runtime.core.header.contract import (
            EvidenceCorrelationError,
            fill_header_fields,
            format_header,
        )

        try:
            header = format_header(
                fill_header_fields(
                    {},
                    session_id,
                    self.store,
                    model,
                    trace_id,
                )
            )
        except (EvidenceCorrelationError, KeyError, RuntimeError, ValueError):
            return ""
        return f"[AGENCY {marker} HEADER SNAPSHOT v1]\n{instruction}\n{header}"

    def _handle_user_prompt_submit(self, payload: dict[str, Any]) -> dict[str, Any]:
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
        header_context = self._codex_header_snapshot_context(
            session_id=correlation.session_id,
            trace_id=trace_id,
            model=correlation.model,
            marker="INITIAL",
            instruction=(
                "Start each substantive progress update and the final parent response "
                "with these exact seven lines, unchanged, then add the response body. "
                "A later Agency header snapshot for this turn supersedes this one."
            ),
        )
        combined_context = f"{context.rstrip()}\n\n{header_context}" if header_context else context
        if len(combined_context) > MAX_CONTEXT_CHARS:
            combined_context = context
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": combined_context[:MAX_CONTEXT_CHARS],
            }
        }

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
            return self._handle_user_prompt_submit(payload)

        if event == "PreToolUse":
            return self._handle_native_child_pre_tool_use(payload)

        if event == "SubagentStart":
            if self.host == "zcode":
                # ZCode exposes planned Agent-tool boundaries but no documented
                # child lifecycle identifier that can authorize a parent join.
                return {}
            return (
                self._handle_claude_subagent_start(payload)
                if self.host == "claude"
                else self._handle_codex_subagent_start(payload)
            )

        if event == "SubagentStop":
            if self.host == "zcode":
                return {}
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
            return self._handle_terminal_rejection(
                correlation=correlation,
                trace_id=trace_id,
                final_response=final_response,
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

    def _handle_terminal_rejection(
        self,
        *,
        correlation: HookCorrelation,
        trace_id: str,
        final_response: str,
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        """Bind the first invalid response as a loud, non-corrective failure."""

        if verification.get("delegation_strength") == "strongly_preferred":
            action = "delegation_declined"
        else:
            action = "response_invalid"
        status = TERMINAL_ACTION_STATUS[action]
        missing = (
            [str(item) for item in verification["missing"]]
            if isinstance(verification.get("missing"), list)
            and all(isinstance(item, str) for item in verification["missing"])
            else []
        )
        committed = self._commit_terminal_finalization(
            session_id=correlation.session_id,
            trace_id=trace_id,
            action=action,
            status=status,
            response_text=final_response,
            expected_evidence_revision=verification.get("evidence_revision"),
            missing=missing,
        )
        if not committed:
            return self._verification_failed(correlation.session_id, trace_id)
        return self._terminal_completion_result(action)

    def _verification_failed(self, session_id: str, trace_id: str) -> dict[str, Any]:
        self._close_turn(session_id, trace_id, "verification_failed")
        return self._reject_completion(_VERIFICATION_UNAVAILABLE, retry=True)

    def _commit_terminal_finalization(
        self,
        *,
        session_id: str,
        trace_id: str,
        action: str,
        status: str,
        response_text: str,
        expected_evidence_revision: Any,
        missing: list[str] | None = None,
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
            "missing": list(missing or []),
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
            return {
                "action": "continue",
                "message": _VERIFICATION_UNAVAILABLE,
                "verification_unavailable": True,
            }
        if not isinstance(verification, dict) or verification.get("action") not in {
            "accept",
            "continue",
        }:
            return {
                "action": "continue",
                "message": _VERIFICATION_UNAVAILABLE,
                "verification_unavailable": True,
            }
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
        if self.host == "zcode":
            # ZCode's Stop event only recognizes {"decision": "block", ...};
            # the {"continue": False, "stopReason": ...} lifecycle shape is an
            # unknown field that it silently ignores, which would collapse a
            # rejection into a pass-through accept. Always emit decision:block
            # regardless of the caller's retry state. See AR-127.
            return _completion_rejection(reason, retry=False)
        return _completion_rejection(reason, retry=retry)

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


def _run_hook_stdio(
    host: str,
    *,
    store: Store | None = None,
    db_path: str | None = None,
    config_path: str | None = None,
    runtime_control_path: str | None = None,
    expected_event: str = "",
    input_stream: BinaryIO | TextIO | None = None,
    output_stream: BinaryIO | TextIO | None = None,
    error_stream: TextIO | None = None,
) -> int:
    """Read one bounded event using its installer-bound expected event."""
    source = input_stream or sys.stdin.buffer
    sink = output_stream or sys.stdout.buffer
    errors = error_stream or sys.stderr

    from agency_runtime.core.runtime_control import (
        read_bound_enforcement_runtime_control,
        read_enforcement_runtime_control,
    )

    master, _master_transport = (
        read_bound_enforcement_runtime_control(runtime_control_path)
        if runtime_control_path
        else read_enforcement_runtime_control()
    )
    if not master["enabled"]:
        # Keep the native hook a true pass-through while Agency is off. In
        # particular, malformed or oversized Stop envelopes must not reach the
        # fail-closed completion policy and block an otherwise publishable host
        # response. Drain only the already bounded hook input for pipe hygiene;
        # its contents are deliberately neither parsed nor validated.
        with suppress(Exception):
            source.read(MAX_HOOK_INPUT_BYTES + 1)
        mark_current_observation("bypassed", "runtime_disabled")
        _write_output(sink, {})
        return 0

    payload: Any = None
    raw_bytes = b""
    oversized = False
    planned = False
    diagnostic_event = ""
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
        payload_event = payload.get("hook_event_name")
        if _codex_hook_event_diagnostic_enabled(host, payload_event):
            diagnostic_event = str(payload_event)
            _emit_codex_hook_event_diagnostic(errors, diagnostic_event, "accepted")
        for field in ("turn_id", "trace_id", "tool_use_id", "session_id"):
            correlation_value = _optional_string(payload, field)
            if not correlation_value:
                continue
            with suppress(ValueError):
                correlate_current_observation(correlation_value)
            break
        planned = bool(
            _planned_native_work_unit_id(host, payload)
            or _agency_owned_native_child_pre_tool_use(payload, host)
        )
        active_store = store
        from agency_runtime.core.codex_activation_verification import (
            is_restricted_codex_activation_canary_environment,
        )

        require_existing_store = is_restricted_codex_activation_canary_environment(os.environ)
        if active_store is None and (db_path or config_path or require_existing_store):
            active_store = Store(
                db_path,
                config_path=config_path,
                require_existing_current=require_existing_store,
            )
        result = HookBridge(host, store=active_store, _master=master).handle(payload)
        if not isinstance(result, dict):
            raise RuntimeError("hook bridge returned a non-object result")
        hook_output = _dict_or_empty(result.get("hookSpecificOutput"))
        blocked = (
            result.get("continue") is False
            or result.get("decision") == "block"
            or hook_output.get("permissionDecision") == "deny"
        )
        if blocked:
            mark_current_observation(
                "denied",
                "planned_hook_denied" if planned else "hook_denied",
            )
        elif result:
            mark_current_observation("ok", "hook_response")
        else:
            mark_current_observation("ok", "pass_through")
        _emit_codex_hook_event_diagnostic(errors, diagnostic_event, "completed")
    except (
        HookInputError,
        BoundedJSONError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RuntimeError,
    ) as exc:
        _emit_codex_hook_event_diagnostic(errors, diagnostic_event, "failed")
        result = _boundary_failure_result(
            payload,
            raw_bytes=raw_bytes,
            oversized=oversized,
            expected_event=expected_event,
            host=host,
        )
        outcome = "response publication blocked" if result else "host operation continues"
        mark_current_observation(
            "denied" if result else "degraded",
            "planned_hook_failure" if planned else "boundary_failure",
        )
        print(f"agency hook {host}: {type(exc).__name__}; {outcome}", file=errors)
    except Exception as exc:  # Defensive boundary around adapters and storage.
        _emit_codex_hook_event_diagnostic(errors, diagnostic_event, "failed")
        result = _boundary_failure_result(
            payload,
            raw_bytes=raw_bytes,
            oversized=oversized,
            expected_event=expected_event,
            host=host,
        )
        outcome = "response publication blocked" if result else "host operation continues"
        mark_current_observation(
            "denied" if result else "degraded",
            "planned_hook_failure" if planned else "boundary_failure",
        )
        print(
            f"agency hook {host}: {type(exc).__name__}; {outcome}",
            file=errors,
        )

    _write_output(sink, result)
    return 0


def _hook_observation_operation(host: str, expected_event: str) -> str:
    """Return one fixed label without logging caller-controlled host/event text."""

    known_hosts = {"claude", "codex", "zcode"}
    known_events = _CODEX_EVENTS | _CLAUDE_EVENTS
    host_label = host if host in known_hosts else "unknown"
    event_label = expected_event.casefold() if expected_event in known_events else "event"
    return f"{host_label}.{event_label}"


def run_hook_stdio(
    host: str,
    *,
    store: Store | None = None,
    db_path: str | None = None,
    config_path: str | None = None,
    runtime_control_path: str | None = None,
    expected_event: str = "",
    input_stream: BinaryIO | TextIO | None = None,
    output_stream: BinaryIO | TextIO | None = None,
    error_stream: TextIO | None = None,
) -> int:
    """Observe one host-hook boundary without admitting envelope content."""

    operation = _hook_observation_operation(host, expected_event)
    with RuntimeBoundary(surface="hook", operation=operation):
        return _run_hook_stdio(
            host,
            store=store,
            db_path=db_path,
            config_path=config_path,
            runtime_control_path=runtime_control_path,
            expected_event=expected_event,
            input_stream=input_stream,
            output_stream=output_stream,
            error_stream=error_stream,
        )


__all__ = [
    "MAX_HOOK_INPUT_BYTES",
    "MAX_HOOK_OUTPUT_BYTES",
    "HookBridge",
    "HookCorrelation",
    "HookInputError",
    "run_hook_stdio",
]
