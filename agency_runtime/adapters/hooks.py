"""Native Codex and Claude Code hook protocol bridge.

Both hosts send one JSON object on stdin.  This module translates their
documented event fields into the shared adapter operations without depending on
a shell, transcript parsing, or host-private Python APIs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
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
    CODEX_NATIVE_FOLLOWUP_HOOK_TOOL_NAMES,
    CODEX_NATIVE_SPAWN_HOOK_TOOL_NAMES,
    CODEX_NATIVE_WAIT_HOOK_TOOL_NAMES,
)
from agency_runtime.core.native_child_activation import (
    NativeChildRunIdentity,
    build_native_child_run_identity,
)
from agency_runtime.core.observability import (
    RuntimeBoundary,
    correlate_current_observation,
    mark_current_observation,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import work_unit_id_from_text

logger = logging.getLogger(__name__)
# A hook speaks one JSON object on stdout and must leave stderr clean; the host
# and the stdio tests both treat stderr output as a boundary violation. Without
# a handler, logging.lastResort would print every WARNING+ record straight to
# stderr. A NullHandler suppresses that while still delivering records to an
# operator who explicitly configures logging for this logger.
logger.addHandler(logging.NullHandler())

MAX_HOOK_INPUT_BYTES = 1_048_576
MAX_HOOK_OUTPUT_BYTES = 65_536
MAX_CONTEXT_CHARS = 48_000
MAX_HOOK_MODEL_BYTES = 512

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
    "agency_agents_delegate": "agency_agents_delegate",
    "mcp__agency__agency_agents_delegate": "agency_agents_delegate",
    "delegate_task": "delegate_task",
    "delegate_async": "delegate_async",
    "spawn_agent": "spawn_agent",
    "functions.collaboration.spawn_agent": "spawn_agent",
    "followup_task": "followup_task",
    "functions.collaboration.followup_task": "followup_task",
    "collaborationfollowup_task": "followup_task",
    "sessions_spawn": "sessions_spawn",
}
_CODEX_SPAWN_TOOL_NAMES = frozenset(
    {
        "Agent",
        "functions.collaboration.spawn_agent",
        *CODEX_NATIVE_SPAWN_HOOK_TOOL_NAMES,
    }
)
_CODEX_FOLLOWUP_TOOL_NAMES = frozenset(
    {
        "functions.collaboration.followup_task",
        *CODEX_NATIVE_FOLLOWUP_HOOK_TOOL_NAMES,
    }
)
_CLAUDE_AGENT_TOOL_NAME = "Agent"
_CLAUDE_CHILD_IDENTITY_MARKER = "[AGENCY NATIVE CHILD IDENTITY v1]"
_PLANNED_NATIVE_WORK_UNIT_PATTERN = re.compile(r"^unit-[0-9a-f]{10}$")


def _encoded_hook_output(payload: dict[str, Any]) -> bytes | None:
    """Return the exact stdout bytes for one hook response, including newline."""

    try:
        return (
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, UnicodeError, ValueError):
        return None


def _native_child_staffing_response(
    args: dict[str, Any],
    *,
    task_field: str,
    rewritten_task: str,
) -> dict[str, Any]:
    """Build the one exact prospective and returned native-child hook response."""

    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**args, task_field: rewritten_task},
        }
    }


def _native_child_delivery_fits_hook(
    args: dict[str, Any],
    *,
    task_field: str,
    rewritten_task: str,
) -> bool:
    """Validate the exact serialized hook output without writing or persisting."""

    encoded = _encoded_hook_output(
        _native_child_staffing_response(
            args,
            task_field=task_field,
            rewritten_task=rewritten_task,
        )
    )
    return encoded is not None and len(encoded) <= MAX_HOOK_OUTPUT_BYTES


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
    reason: str = "",
) -> dict[str, Any]:
    """Block Agency-owned malformed Stop events; never block a turn Agency cannot check."""

    parsed_user_prompt = (
        isinstance(payload, dict) and payload.get("hook_event_name") == "UserPromptSubmit"
    )
    if expected_event == "UserPromptSubmit" or parsed_user_prompt:
        # Rule 8: Agency never withholds a turn because Agency is unavailable.
        #
        # Staffing failures already failed open here (ADR-0122). What was left
        # was the integrity half -- store/lifecycle/RuntimeError -- which is the
        # SAME class the Stop path stopped blocking on, just on a different
        # event: Agency failing to check something is not a finding about the
        # user's prompt. Nothing has been verified and rejected at this point in
        # the turn; there is only Agency's own machinery failing, so denying the
        # prompt costs the user a turn to report an Agency fault.
        #
        # This is also what wrote `preflight_failed` onto the parent run, which
        # then denied the parent scope to every harness-spawned child of that
        # turn -- one broken store took down staffing for the whole session.
        #
        # The failure stays loud without being fatal: `run_hook` marks the
        # observation `degraded` and prints the exact cause to stderr, and
        # `agency evidence rejections` lists it under "published anyway".
        logger.error(
            "preflight_unavailable_publishing_anyway",
            extra={
                "host": host,
                "cause": " ".join(str(reason or "").split())[:180],
                "event": "UserPromptSubmit",
            },
        )
        return {}

    # A child launch is never denied. There is no plan to verify it against and
    # no grant to check, so an unreadable payload means Agency does not staff
    # this child -- not that the harness may not launch it (rules 5 and 8).
    if oversized and expected_event == "PreToolUse":
        return {}

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
    #
    # NOTE (rule 8): this boundary is still fail-closed on purpose, and it is the
    # last Stop path that can withhold a turn. Unlike the verification failures
    # above, an unreadable envelope means Agency cannot even tell whether this is
    # a Stop it owns, so failing open here would make the evidence contract
    # bypassable by sending a malformed payload. Deliberate open question, not an
    # oversight -- see the handoff.
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


def _optional_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise HookInputError(f"{key} must be a string or null")
    return value


def _bounded_optional_utf8_string(
    payload: dict[str, Any],
    key: str,
    *,
    maximum_bytes: int,
) -> str:
    """Read one optional host string without admitting an oversized UTF-8 value."""

    value = _optional_string(payload, key)
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise HookInputError(f"{key} must be valid UTF-8") from exc
    if len(encoded) > maximum_bytes:
        raise HookInputError(f"{key} exceeds the size limit")
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


def hook_host_adapter(host: str, store: Store) -> Any:
    """Build the adapter a hook-driven host actually runs on.

    This is the single place that knows a host reaches Agency through the
    shared hooks boundary rather than through an adapter class of its own.
    Anything that wants to observe such a host -- the hook bridge itself, or a
    parity evaluation that must speak for every supported host -- builds it
    here, so an evaluation cannot silently observe some neighbouring host's
    construction and report it as parity.
    """

    normalized_host = str(host or "").strip().casefold()
    if normalized_host == "codex":
        from agency_runtime.adapters.codex.wrapper import CodexAdapter

        return CodexAdapter(store=store)
    if normalized_host not in {"claude", "zcode"}:
        raise ValueError(f"unsupported hook host: {host}")
    from agency_runtime.adapters.claude.wrapper import ClaudeAdapter

    # ADR-0087: zcode reuses the Claude hook model and Agent-tool delegation
    # primitive, so it shares the ClaudeAdapter behavior. But it must keep
    # its own host identity so runtime-control reads the zcode row (not
    # claude's) and all evidence receipts are attributed to zcode rather
    # than masqueraded as claude.
    adapter = ClaudeAdapter(store=store)
    if normalized_host == "zcode":
        adapter.host_name = "zcode"
    return adapter


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
        return hook_host_adapter(self.host, self.store)

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
        model = _bounded_optional_utf8_string(
            payload,
            "model",
            maximum_bytes=MAX_HOOK_MODEL_BYTES,
        )
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
        """Resolve the parent turn a native child belongs to.

        An explicit host turn must name an existing live run in the same session.
        It is never replaced by a different open trace when invalid. Only a host
        that omitted ``turn_id`` may use the exactly-one-open-trace fallback.
        """

        correlation = self._correlation(payload)
        trace_id = correlation.turn_id
        run_reader = getattr(self.store, "get_run", None)
        if trace_id and callable(run_reader):
            try:
                candidate = run_reader(trace_id)
            except Exception:
                candidate = None
            correlated = (
                isinstance(candidate, dict)
                and candidate.get("session_id") == correlation.session_id
            )
            live = correlated and candidate.get("status") in {"active", "evidence_only"}
            if not live:
                return correlation.session_id, "", correlation.work_unit_id
        if not trace_id:
            trace_id = self._unambiguous_open_trace(correlation.session_id)
        return correlation.session_id, trace_id, correlation.work_unit_id

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
        # A child is identified by the specialist it carries. There is no unit plan
        # to resolve a label against.
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

    def _native_child_staffing_parent(
        self,
        payload: dict[str, Any],
        args: dict[str, Any],
    ) -> tuple[HookCorrelation, str]:
        """Resolve exactly one existing live parent; never substitute a tool ID."""

        correlation = self._correlation(payload, args)
        if not correlation.tool_use_id:
            return correlation, ""
        run_reader = getattr(self.store, "get_run", None)
        if correlation.turn_id:
            if not callable(run_reader):
                return correlation, ""
            try:
                candidate = run_reader(correlation.turn_id)
            except Exception:
                return correlation, ""
            if not (
                isinstance(candidate, dict)
                and candidate.get("session_id") == correlation.session_id
                and candidate.get("status") in {"active", "evidence_only"}
            ):
                # An explicit but invalid/cross-session/terminal turn is not
                # permission to attach this launch to a different open trace.
                return correlation, ""
            return correlation, correlation.turn_id
        trace_id = self._unambiguous_open_trace(correlation.session_id)
        if not trace_id or not callable(run_reader):
            return correlation, ""
        try:
            candidate = run_reader(trace_id)
        except Exception:
            return correlation, ""
        if not (
            isinstance(candidate, dict)
            and candidate.get("session_id") == correlation.session_id
            and candidate.get("status") in {"active", "evidence_only"}
        ):
            return correlation, ""
        return correlation, trace_id

    def _record_native_child_unstaffed(
        self,
        *,
        payload: dict[str, Any],
        args: dict[str, Any],
        task: str,
        reason_code: str,
    ) -> None:
        """Persist one content-free reason only when its parent is exact and live."""

        correlation, trace_id = self._native_child_staffing_parent(payload, args)
        if not trace_id:
            return
        try:
            from agency_runtime.core.native_child_staffing import (
                record_native_child_staffing_failure,
            )

            record_native_child_staffing_failure(
                self.store,
                host=self.host,
                task=task,
                parent_session_id=correlation.session_id,
                parent_trace_id=trace_id,
                launch_id=correlation.tool_use_id,
                reason_code=reason_code,
            )
        except Exception:
            logger.debug(
                "native-child staffing failure could not be projected",
                exc_info=True,
            )

    def _exact_native_child_delivery_retry(
        self,
        *,
        payload: dict[str, Any],
        args: dict[str, Any],
        delivery: Any,
    ) -> bool:
        """Accept only the exact still-current Store-bound launch as a retry."""

        correlation, trace_id = self._native_child_staffing_parent(payload, args)
        if not trace_id:
            return False
        if not (
            delivery.host == self.host
            and delivery.parent_session_id == correlation.session_id
            and delivery.parent_trace_id == trace_id
            and delivery.launch_id == correlation.tool_use_id
            and delivery.binding_kind == "launch_id"
            and delivery.binding_id == correlation.tool_use_id
        ):
            return False
        try:
            expires_at = datetime.fromisoformat(
                delivery.expires_at[:-1] + "+00:00"
                if delivery.expires_at.endswith("Z")
                else delivery.expires_at
            )
            if expires_at.tzinfo is None or expires_at <= datetime.now(timezone.utc):
                return False
        except (AttributeError, TypeError, ValueError):
            return False
        getter = getattr(self.store, "get_native_child_staffing_decision", None)
        if not callable(getter):
            return False
        try:
            expected = getter(delivery.decision_id)
            from agency_runtime.core.native_child_install_identity import (
                current_runtime_managed_host_install_identity,
            )

            install = current_runtime_managed_host_install_identity(self.host)
        except Exception:
            return False
        cards = [
            {
                "specialist_slug": card.specialist_slug,
                "specialist_version": card.specialist_version,
                "specialist_prompt_hash": card.specialist_prompt_hash,
                "body_character_length": card.body_character_length,
            }
            for card in delivery.cards
        ]
        exact = {
            "decision_id": delivery.decision_id,
            "host": delivery.host,
            "parent_session_id": delivery.parent_session_id,
            "parent_trace_id": delivery.parent_trace_id,
            "launch_id": delivery.launch_id,
            "provider_receipt_digest": delivery.provider_receipt_digest,
            "task_sha256": delivery.task_sha256,
            "team_digest": delivery.team_digest,
            "candidate_digest": delivery.candidate_digest,
            "runtime_digest": delivery.runtime_digest,
            "install_id": delivery.install_id,
            "bundle_digest": delivery.bundle_digest,
            "issued_at": delivery.issued_at,
            "expires_at": delivery.expires_at,
            "nonce": delivery.nonce,
            "binding_kind": delivery.binding_kind,
            "binding_id": delivery.binding_id,
            "cards": cards,
        }
        return bool(
            isinstance(expected, dict)
            and all(expected.get(key) == value for key, value in exact.items())
            and getattr(install, "host", "") == delivery.host
            and getattr(install, "install_id", "") == delivery.install_id
            and getattr(install, "bundle_digest", "") == delivery.bundle_digest
            and getattr(install, "candidate_digest", "") == delivery.candidate_digest
            and getattr(install, "running_runtime_digest", "") == delivery.runtime_digest
        )

    @staticmethod
    def _scrub_native_child_delivery(task: str, delivery: Any | None = None) -> str:
        """Remove an unauthorized Agency namespace without blocking the host spawn."""

        if delivery is not None and isinstance(delivery.original_task, str):
            original = delivery.original_task
        else:
            reserved = (
                "\n\n[AGENCY INFERENCE TEAM v6]\n",
                "[AGENCY INFERENCE TEAM v6]",
                "<!-- agency-native-child-team:v6:",
                "<!-- agency-native-child-team-end:v6:",
            )
            positions = [position for token in reserved if (position := task.find(token)) >= 0]
            original = task[: min(positions)].rstrip() if positions else ""
        try:
            safe = bool(original and len(original.encode("utf-8")) <= MAX_CONTEXT_CHARS)
        except UnicodeError:
            safe = False
        return original if safe else "Proceed as an unstaffed generalist without Agency context."

    def _staff_plaintext_native_child(
        self,
        *,
        payload: dict[str, Any],
        args: dict[str, Any],
        task_field: str,
        task: str,
        channel_attestation: Any | None = None,
    ) -> dict[str, Any]:
        """Carry one inference-owned atomic team to a host-owned spawn."""

        if self.host == "codex" and channel_attestation is None:
            # Keep the shared helper safe if a future Codex caller bypasses the
            # public pre-tool attestation gate.
            return {}

        from agency_runtime.core.native_child_install_identity import (
            current_runtime_managed_host_install_identity,
        )
        from agency_runtime.core.native_child_prompt_delivery import (
            parse_inference_team_delivery,
        )
        from agency_runtime.core.native_child_staffing import staff_native_child

        try:
            serialized_args = json.dumps(
                args,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            frozen_args = json.loads(serialized_args)
        except (TypeError, UnicodeError, ValueError):
            self._record_native_child_unstaffed(
                payload=payload,
                args=args,
                task=task,
                reason_code="native_child_host_serialization_invalid",
            )
            return {}
        if not isinstance(frozen_args, dict):
            return {}

        def channel_is_current() -> bool:
            if channel_attestation is None:
                return True
            try:
                from agency_runtime.core.codex_spawn_provenance import (
                    codex_plaintext_spawn_attestation_is_current,
                )

                return (
                    codex_plaintext_spawn_attestation_is_current(
                        channel_attestation,
                        tool_input=frozen_args,
                    )
                    is True
                )
            except Exception:
                logger.debug(
                    "native-child channel attestation could not be revalidated",
                    exc_info=True,
                )
                return False

        existing_delivery = parse_inference_team_delivery(task)
        if existing_delivery is not None:
            if self._exact_native_child_delivery_retry(
                payload=payload,
                args=args,
                delivery=existing_delivery,
            ):
                # Only an exact current Store- and install-bound retry keeps the
                # already-rewritten host input unchanged.
                return {}
            self._record_native_child_unstaffed(
                payload=payload,
                args=args,
                task=existing_delivery.original_task,
                reason_code="native_child_existing_delivery_invalid",
            )
            return _native_child_staffing_response(
                frozen_args,
                task_field=task_field,
                rewritten_task=self._scrub_native_child_delivery(task, existing_delivery),
            )
        if any(
            marker in task
            for marker in (
                "[AGENCY INFERENCE TEAM v6]",
                "<!-- agency-native-child-team:v6:",
                "<!-- agency-native-child-team-end:v6:",
            )
        ):
            self._record_native_child_unstaffed(
                payload=payload,
                args=args,
                task=task,
                reason_code="native_child_existing_delivery_invalid",
            )
            return _native_child_staffing_response(
                frozen_args,
                task_field=task_field,
                rewritten_task=self._scrub_native_child_delivery(task),
            )
        correlation, trace_id = self._native_child_staffing_parent(payload, args)
        if not trace_id:
            return {}
        try:
            install_identity_reader = current_runtime_managed_host_install_identity
            result = staff_native_child(
                self.store,
                host=self.host,
                task=task,
                parent_session_id=correlation.session_id,
                parent_trace_id=trace_id,
                launch_id=correlation.tool_use_id,
                binding_kind="launch_id",
                binding_id=correlation.tool_use_id,
                install_identity=install_identity_reader(self.host),
                install_identity_reader=install_identity_reader,
                maximum_delivery_bytes=MAX_CONTEXT_CHARS,
                delivery_validator=lambda rewritten_task: (
                    channel_is_current()
                    and _native_child_delivery_fits_hook(
                        frozen_args,
                        task_field=task_field,
                        rewritten_task=rewritten_task,
                    )
                ),
                final_delivery_validator=(
                    channel_is_current if channel_attestation is not None else None
                ),
            )
        except Exception:
            logger.debug(
                "inference-owned native-child staffing failed open",
                exc_info=True,
            )
            return {}
        if not result.staffed:
            return {}
        # The exact same frozen JSON input and serializer were accepted by the
        # pre-persistence validator, so this mapping serializes byte-for-byte to
        # the already-validated prospective response.
        response = _native_child_staffing_response(
            frozen_args,
            task_field=task_field,
            rewritten_task=result.rewritten_task,
        )
        if not _native_child_delivery_fits_hook(
            frozen_args,
            task_field=task_field,
            rewritten_task=result.rewritten_task,
        ):
            # Defense in depth for a mutated or substituted staffing service.
            # The production service validates this exact output before its
            # applied route commit; the hook still refuses an oversized return.
            self._record_native_child_unstaffed(
                payload=payload,
                args=args,
                task=task,
                reason_code="native_child_delivery_exceeds_host_limit",
            )
            return {}
        return response

    def _handle_native_child_pre_tool_use(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Staff plaintext host launches; fail opaque Codex launches open."""

        tool_name = _required_string(payload, "tool_name")
        if self.host == "codex" and tool_name in _CODEX_FOLLOWUP_TOOL_NAMES:
            # Codex owns dispatch of its own follow-up turns. Agency has no plan
            # to authorize one against and never blocks one (rules 5 and 8).
            return {}
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
        if self.host == "codex":
            try:
                from agency_runtime.core.codex_spawn_provenance import (
                    attest_codex_plaintext_spawn,
                )

                correlation = self._correlation(payload, args)
                channel_attestation = attest_codex_plaintext_spawn(
                    payload.get("transcript_path"),
                    session_id=correlation.session_id,
                    turn_id=correlation.turn_id,
                    tool_use_id=correlation.tool_use_id,
                    tool_input=args,
                    environ=os.environ,
                )
            except Exception:
                logger.debug(
                    "Codex plaintext spawn could not be authenticated",
                    exc_info=True,
                )
                channel_attestation = None
            if channel_attestation is None:
                restricted_parent = self._restricted_codex_activation_parent_scope(payload)
                if restricted_parent is not None and self._restricted_codex_spawn_input(args):
                    # ADR-0179 owns this one repository-authored canary spawn at
                    # SubagentStart.  It is not an ordinary unsupported opaque
                    # child, so do not append a contradictory failure route.
                    return {}
                # Encrypted, unmarked, ambiguous, or stale Codex calls remain
                # ordinary host spawns. The diagnostic is content-free and the
                # hook never blocks the child.
                self._record_native_child_unstaffed(
                    payload=payload,
                    args=args,
                    task=task,
                    reason_code="unsupported_opaque_interagent_channel",
                )
                return {}
            return self._staff_plaintext_native_child(
                payload=payload,
                args=args,
                task_field=task_field,
                task=task,
                channel_attestation=channel_attestation,
            )
        return self._staff_plaintext_native_child(
            payload=payload,
            args=args,
            task_field=task_field,
            task=task,
        )

    def _handle_claude_subagent_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Give this child its own identity without assigning any specialist."""

        lifecycle = self._record_native_child_lifecycle(payload, event="started")
        if lifecycle is None:
            return {}
        _session_id, _trace_id, _work_unit_id, identity = lifecycle
        context_lines = [
            _CLAUDE_CHILD_IDENTITY_MARKER,
            "This identity belongs only to the current native child. It does not "
            "load, select, or inherit an Agency specialist.",
            f"worker_kind={json.dumps(identity.worker_kind)}",
            f"worker_id={json.dumps(identity.worker_id, ensure_ascii=True)}",
            f"native_run_id={json.dumps(identity.native_run_id, ensure_ascii=True)}",
            "If Agency supplied a valid inference-selected team, its complete atomic "
            "context is already part of the host-owned launch prompt. This identity "
            "message supplies no card and does not ask the child to repair staffing.",
        ]
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
        """Inject one exact canary team or an unstaffed child identity."""

        restricted_parent = self._restricted_codex_activation_child_parent_scope(payload)
        if restricted_parent is not None:
            session_id, trace_id = restricted_parent
            try:
                agent_type = _required_string(payload, "agent_type")
                identity = _native_child_identity(
                    self.host,
                    _required_string(payload, "agent_id"),
                )
            except (HookInputError, ValueError):
                return {}
            from agency_runtime.core.activation_canary_contract import (
                CODEX_ACTIVATION_CANARY_NATIVE_AGENT_TYPE,
            )

            if agent_type == CODEX_ACTIVATION_CANARY_NATIVE_AGENT_TYPE:
                context = self._staff_restricted_codex_activation_child(
                    session_id=session_id,
                    trace_id=trace_id,
                    identity=identity,
                )
                if context:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "SubagentStart",
                            "additionalContext": context,
                        }
                    }

        lifecycle = self._record_native_child_lifecycle(payload, event="started")
        if lifecycle is None:
            return {}
        _session_id, _trace_id, _work_unit_id, identity = lifecycle
        context_lines = [
            _CLAUDE_CHILD_IDENTITY_MARKER,
            "This identity belongs only to the current native Codex child. It does not "
            "load, select, or inherit an Agency specialist.",
            f"worker_kind={json.dumps(identity.worker_kind)}",
            f"worker_id={json.dumps(identity.worker_id, ensure_ascii=True)}",
            f"native_run_id={json.dumps(identity.native_run_id, ensure_ascii=True)}",
            "The authenticated Codex hook contract did not expose this child's decrypted "
            "inter-agent assignment, so Agency supplied no specialist card. The host "
            "may proceed with its native child unstaffed; this child is not asked to "
            "call preflight or repair the missing channel.",
        ]
        context = "\n".join(context_lines)
        if len(context) > MAX_CONTEXT_CHARS:
            context = (
                _CLAUDE_CHILD_IDENTITY_MARKER
                + "\nAgency supplied no specialist card to this native Codex child."
            )
        return {
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": context,
            }
        }

    def _restricted_codex_activation_parent_scope(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, str] | None:
        """Resolve the parent hook's sole open restricted Codex canary turn."""

        if self.host != "codex":
            return None
        from agency_runtime.core.codex_activation_verification import (
            is_restricted_codex_activation_canary_environment,
        )

        if not is_restricted_codex_activation_canary_environment(os.environ):
            return None
        correlation = self._correlation(payload)
        trace_id = self._unambiguous_open_trace(correlation.session_id)
        getter = getattr(self.store, "get_codex_activation_canary_parent_snapshot", None)
        if not trace_id or not callable(getter):
            return None
        try:
            snapshot = getter(
                session_id=correlation.session_id,
                trace_id=trace_id,
            )
        except Exception:
            return None
        route = snapshot.get("route") if isinstance(snapshot, dict) else None
        from agency_runtime.core.activation_canary_contract import (
            CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
            CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE,
        )

        if not (
            isinstance(route, dict)
            and snapshot.get("proven") is True
            and snapshot.get("session_id") == correlation.session_id
            and snapshot.get("trace_id") == trace_id
            and route.get("status") == "accepted"
            and route.get("source") == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
            and route.get("selected_ids") == ["code-reviewer"]
            and route.get("semantic_ids") == ["code-reviewer"]
            and route.get("companion_ids") == []
            and route.get("work_units")
            == {
                "delegate": True,
                "count": 1,
                "confidence": "high",
                "source": CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE,
            }
        ):
            return None
        return correlation.session_id, trace_id

    def _restricted_codex_activation_child_parent_scope(
        self,
        payload: dict[str, Any],
    ) -> tuple[str, str] | None:
        """Bind a real Codex child to one host-authored canary parent lineage."""

        if self.host != "codex":
            return None
        from agency_runtime.core.codex_activation_verification import (
            CODEX_ACTIVATION_QUERY_HASH_ENV,
            is_restricted_codex_activation_canary_environment,
            restricted_codex_activation_query_hash,
        )

        if not is_restricted_codex_activation_canary_environment(os.environ):
            return None
        try:
            hook_parent_session_id = validate_correlation_id(
                _required_string(payload, "session_id"),
                field="session_id",
            )
            child_session_id = validate_correlation_id(
                _required_string(payload, "agent_id"),
                field="agent_id",
            )
        except (HookInputError, ValueError):
            return None

        try:
            event = _required_string(payload, "hook_event_name")
            cwd = _required_string(payload, "cwd")
            if event == "SubagentStart":
                artifact_path = _required_string(payload, "transcript_path")
            elif event == "SubagentStop":
                artifact_path = _required_string(payload, "agent_transcript_path")
            else:
                return None
        except HookInputError:
            return None
        from agency_runtime.core.child_delivery_evidence import (
            codex_v1491_child_parent_session,
        )

        try:
            parent_session_id = codex_v1491_child_parent_session(
                artifact_path,
                child_id=child_session_id,
                cwd=cwd,
            )
        except Exception:
            return None
        if not parent_session_id or parent_session_id != hook_parent_session_id:
            return None
        parent_trace_id = self._unambiguous_open_trace(parent_session_id)
        getter = getattr(self.store, "get_codex_activation_canary_parent_snapshot", None)
        if not parent_trace_id or not callable(getter):
            return None
        try:
            snapshot = getter(
                session_id=parent_session_id,
                trace_id=parent_trace_id,
            )
        except Exception:
            return None
        route = snapshot.get("route") if isinstance(snapshot, dict) else None
        run = snapshot.get("run") if isinstance(snapshot, dict) else None
        query_hash = restricted_codex_activation_query_hash(os.environ)
        supplied_query_hash = os.environ.get(CODEX_ACTIVATION_QUERY_HASH_ENV)
        if supplied_query_hash is not None and not query_hash:
            return None
        route_query_hash = route.get("query_hash") if isinstance(route, dict) else None
        from agency_runtime.core.activation_canary_contract import (
            CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
            CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE,
        )

        if not (
            isinstance(route, dict)
            and isinstance(run, dict)
            and snapshot.get("proven") is True
            and snapshot.get("status") == "resolved"
            and snapshot.get("reason") == "exact_route_resolved"
            and snapshot.get("host") == "codex"
            and snapshot.get("query_hash") == route_query_hash
            and snapshot.get("session_id") == parent_session_id
            and snapshot.get("trace_id") == parent_trace_id
            and run.get("session_id") == parent_session_id
            and run.get("trace_id") == parent_trace_id
            and route.get("session_id") == parent_session_id
            and route.get("trace_id") == parent_trace_id
            and isinstance(route_query_hash, str)
            and re.fullmatch(r"[0-9a-f]{64}", route_query_hash) is not None
            and (not query_hash or route_query_hash == query_hash)
            and route.get("status") == "accepted"
            and route.get("source") == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
            and route.get("selected_ids") == ["code-reviewer"]
            and route.get("semantic_ids") == ["code-reviewer"]
            and route.get("companion_ids") == []
            and route.get("work_units")
            == {
                "delegate": True,
                "count": 1,
                "confidence": "high",
                "source": CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE,
            }
            and run.get("host") == "codex"
            and run.get("status") in {"active", "evidence_only"}
            and run.get("preflight_state") == "ready"
            and run.get("request_fingerprint") == route_query_hash
            and run.get("ended_at") is None
            and run.get("terminal_finalization_id") is None
        ):
            return None
        try:
            validated_parent_session_id = validate_correlation_id(
                snapshot.get("session_id"),
                field="parent_session_id",
            )
            validated_parent_trace_id = validate_correlation_id(
                snapshot.get("trace_id"),
                field="parent_trace_id",
            )
        except ValueError:
            return None
        if (
            validated_parent_session_id != parent_session_id
            or validated_parent_trace_id != parent_trace_id
        ):
            return None
        return validated_parent_session_id, validated_parent_trace_id

    def _staff_restricted_codex_activation_child(
        self,
        *,
        session_id: str,
        trace_id: str,
        identity: NativeChildRunIdentity,
    ) -> str:
        """Staff the fixed canary unit against the real 0.149 child UUID."""

        from agency_runtime.core.activation_canary_contract import (
            CODEX_ACTIVATION_CANARY_WORK_UNIT,
        )
        from agency_runtime.core.child_delivery_evidence import (
            _restricted_codex_canary_route,
        )
        from agency_runtime.core.native_child_install_identity import (
            current_runtime_managed_host_install_identity,
        )
        from agency_runtime.core.native_child_staffing import staff_native_child

        try:
            result = staff_native_child(
                self.store,
                host="codex",
                task=CODEX_ACTIVATION_CANARY_WORK_UNIT,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                launch_id=identity.worker_id,
                binding_kind="child_id",
                binding_id=identity.worker_id,
                install_identity=current_runtime_managed_host_install_identity("codex"),
                install_identity_reader=current_runtime_managed_host_install_identity,
                maximum_delivery_bytes=MAX_CONTEXT_CHARS,
                delivery_validator=lambda value: bool(
                    isinstance(value, str) and len(value.encode("utf-8")) <= MAX_CONTEXT_CHARS
                ),
            )
            route = _restricted_codex_canary_route(
                self.store,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
            )
            if not (
                result.staffed
                and result.selected_ids == ("code-reviewer",)
                and isinstance(route, dict)
                and route.get("decision_id") == result.decision_id
                and route.get("binding_id") == identity.worker_id
                and route.get("launch_id") == identity.worker_id
                and result.rewritten_task
                and len(result.rewritten_task.encode("utf-8")) <= MAX_CONTEXT_CHARS
            ):
                return ""
            promoter = getattr(self.store, "promote_codex_activation_canary_child", None)
            if callable(promoter):
                promoter(
                    session_id=session_id,
                    trace_id=trace_id,
                    work_unit_id=work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT),
                    worker_id=identity.worker_id,
                    native_run_id=identity.native_run_id,
                )
            recorder = getattr(self.store, "record_native_child_started", None)
            if not callable(recorder):
                return ""
            started = recorder(
                host="codex",
                backend="spawn_agent",
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT),
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
            if not isinstance(started, dict):
                return ""
            return result.rewritten_task
        except Exception:
            logger.debug("restricted Codex canary child staffing failed open", exc_info=True)
            return ""

    @staticmethod
    def _restricted_codex_spawn_input(tool_input: Any) -> bool:
        """Recognize only the fixed native call shape emitted by the canary plan."""

        from agency_runtime.core.native_child_prompt_delivery import (
            is_codex_opaque_collaboration_message,
        )

        args = _dict_or_empty(tool_input)
        return bool(
            set(args) == {"fork_turns", "message", "task_name"}
            and args.get("fork_turns") == "none"
            and args.get("task_name") == "code_reviewer"
            and is_codex_opaque_collaboration_message(args.get("message"))
        )

    @staticmethod
    def _restricted_codex_spawn_response(tool_response: Any) -> bool:
        """Recognize the exact identity-free Codex 0.149 spawn response."""

        response = _native_child_response_mapping("codex", tool_response)
        return bool(
            isinstance(response, dict)
            and set(response) == {"task_name"}
            and response.get("task_name") == "/root/code_reviewer"
        )

    def _restricted_codex_spawn_reconciliation(
        self,
        *,
        session_id: str,
        trace_id: str,
        tool_input: Any,
        tool_response: Any,
    ) -> tuple[Any, str, NativeChildRunIdentity | None]:
        """Join the post-spawn path to the child UUID bound at SubagentStart."""

        from agency_runtime.core.codex_activation_verification import (
            is_restricted_codex_activation_canary_environment,
        )

        if not is_restricted_codex_activation_canary_environment(os.environ):
            return tool_response, "", None
        from agency_runtime.core.activation_canary_contract import (
            CODEX_ACTIVATION_CANARY_WORK_UNIT,
        )
        from agency_runtime.core.child_delivery_evidence import (
            _restricted_codex_canary_route,
        )

        route = _restricted_codex_canary_route(
            self.store,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
        )
        if not (
            isinstance(route, dict)
            and self._restricted_codex_spawn_input(tool_input)
            and self._restricted_codex_spawn_response(tool_response)
        ):
            return tool_response, "", None
        response = _native_child_response_mapping("codex", tool_response)
        if response is None:
            return tool_response, "", None
        try:
            identity = _native_child_identity("codex", route["binding_id"])
        except (KeyError, ValueError):
            return tool_response, "", None
        return (
            {
                "task_name": response["task_name"],
                "agent_id": identity.worker_id,
                "native_run_id": identity.native_run_id,
                "work_unit_id": work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT),
            },
            work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT),
            identity,
        )

    def _handle_codex_subagent_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Close a planned Codex child only after its exact execution turn."""

        restricted_parent = self._restricted_codex_activation_child_parent_scope(payload)
        if restricted_parent is None:
            session_id, trace_id, work_unit_id = self._native_child_parent_scope(payload)
        else:
            session_id, trace_id = restricted_parent
            from agency_runtime.core.activation_canary_contract import (
                CODEX_ACTIVATION_CANARY_WORK_UNIT,
            )

            work_unit_id = work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT)
        _required_string(payload, "agent_type")
        try:
            identity = _native_child_identity(
                self.host,
                _required_string(payload, "agent_id"),
            )
        except ValueError:
            return {}
        final_message = _optional_string(payload, "last_assistant_message")
        # The harness spawned this child itself, so there is no planned
        # execution receipt to reconcile against -- just close its lifecycle.
        stopped = getattr(self.store, "record_native_child_stopped", None)
        if callable(stopped) and trace_id:
            stopped(
                host=self.host,
                backend=_native_child_backend(self.host),
                session_id=session_id,
                trace_id=trace_id,
                work_unit_id=work_unit_id,
                worker_id=identity.worker_id,
                native_run_id=identity.native_run_id,
            )
        if not final_message.strip():
            return {}
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
        if restricted_parent is not None:
            try:
                from agency_runtime.core.child_delivery_evidence import (
                    _collect_restricted_codex_canary_child_delivery,
                )

                _collect_restricted_codex_canary_child_delivery(
                    self.store,
                    parent_session_id=session_id,
                    parent_trace_id=trace_id,
                )
            except Exception:
                logger.debug(
                    "restricted Codex child delivery could not be collected at stop",
                    exc_info=True,
                )
        return {}

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

    def _handle_post_tool_use(  # noqa: C901 - one ordered native observation boundary
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
        observed_codex_identity: NativeChildRunIdentity | None = None
        reconciled_codex_identity: NativeChildRunIdentity | None = None
        reconciled_codex_unit = ""
        restricted_codex_spawn = False
        if (
            self.host == "codex"
            and event == "PostToolUse"
            and tool_name in _CODEX_SPAWN_TOOL_NAMES
            and correlation.session_id
            and trace_id
        ):
            restricted_codex_spawn = bool(
                self._restricted_codex_activation_parent_scope(payload)
                == (correlation.session_id, trace_id)
                and self._restricted_codex_spawn_input(tool_input)
                and self._restricted_codex_spawn_response(observed_tool_response)
            )
            (
                tool_response,
                reconciled_codex_unit,
                reconciled_codex_identity,
            ) = self._restricted_codex_spawn_reconciliation(
                session_id=correlation.session_id,
                trace_id=trace_id,
                tool_input=tool_input,
                tool_response=observed_tool_response,
            )
        resolved_codex_unit = self._resolve_codex_post_tool_unit(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_response=observed_tool_response,
            session_id=correlation.session_id,
            trace_id=trace_id,
        )
        if self.host in {"claude", "zcode"} and tool_name == _CLAUDE_AGENT_TOOL_NAME:
            # ``subagent_type`` is a native Claude worker profile, not an Agency
            # specialist identity, and there is no persisted plan row to
            # authorize a specialist projection from. Both stay empty.
            canonical_args["work_unit_id"] = ""
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
            if not isinstance(tool_response, dict) or not _first_string(
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
            if not isinstance(tool_response, dict) or not _first_string(
                tool_response, "native_run_id"
            ):
                tool_response, observed_codex_identity = _native_child_tool_identity(
                    "codex",
                    tool_response,
                )
            if restricted_codex_spawn:
                from agency_runtime.core.activation_canary_contract import (
                    CODEX_ACTIVATION_CANARY_WORK_UNIT,
                )

                canonical_args["agent"] = "code-reviewer"
                canonical_args["goal"] = CODEX_ACTIVATION_CANARY_WORK_UNIT
        if resolved_codex_unit:
            canonical_args["work_unit_id"] = resolved_codex_unit
        if reconciled_codex_unit:
            canonical_args["work_unit_id"] = reconciled_codex_unit
        elif restricted_codex_spawn:
            from agency_runtime.core.activation_canary_contract import (
                CODEX_ACTIVATION_CANARY_WORK_UNIT,
            )

            canonical_args["work_unit_id"] = work_unit_id_from_text(
                CODEX_ACTIVATION_CANARY_WORK_UNIT
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
            trace_id=trace_id,
            turn_id=correlation.turn_id,
            work_unit_id=correlation.work_unit_id,
            model=correlation.model,
            tool_use_id=correlation.tool_use_id,
            agent_id=_optional_string(payload, "agent_id"),
        )
        claim_identity = reconciled_codex_identity
        claim_unit = reconciled_codex_unit
        if claim_identity is None and restricted_codex_spawn:
            claim_identity = observed_codex_identity
            from agency_runtime.core.activation_canary_contract import (
                CODEX_ACTIVATION_CANARY_WORK_UNIT,
            )

            claim_unit = work_unit_id_from_text(CODEX_ACTIVATION_CANARY_WORK_UNIT)
        if claim_identity is not None and claim_unit:
            try:
                started = self.store.record_native_child_started(
                    host="codex",
                    backend="spawn_agent",
                    session_id=correlation.session_id,
                    trace_id=trace_id,
                    work_unit_id=claim_unit,
                    worker_id=claim_identity.worker_id,
                    native_run_id=claim_identity.native_run_id,
                )
                claimed = self.store.claim_codex_native_child_execution(
                    session_id=correlation.session_id,
                    trace_id=trace_id,
                    work_unit_id=claim_unit,
                    worker_id=claim_identity.worker_id,
                    native_run_id=claim_identity.native_run_id,
                    tool_use_id=correlation.tool_use_id,
                )
                if not isinstance(started, dict) or claimed is not True:
                    logger.debug("restricted Codex spawn reconciliation was incomplete")
            except Exception:
                logger.debug("restricted Codex spawn reconciliation failed", exc_info=True)
        if restricted_codex_spawn and reconciled_codex_identity is None:
            # Close the only concurrent interleaving: SubagentStart may commit
            # its route between the first route read and this pending dispatch.
            # Whichever callback finishes second performs the same atomic
            # promotion, so neither host callback order nor overlap loses it.
            try:
                _late_response, late_unit, late_identity = (
                    self._restricted_codex_spawn_reconciliation(
                        session_id=correlation.session_id,
                        trace_id=trace_id,
                        tool_input=tool_input,
                        tool_response=observed_tool_response,
                    )
                )
                promoter = getattr(self.store, "promote_codex_activation_canary_child", None)
                if late_identity is not None and late_unit and callable(promoter):
                    promoter(
                        session_id=correlation.session_id,
                        trace_id=trace_id,
                        work_unit_id=late_unit,
                        worker_id=late_identity.worker_id,
                        native_run_id=late_identity.native_run_id,
                    )
            except Exception:
                logger.debug("restricted Codex late spawn promotion failed", exc_info=True)
        return self._codex_post_tool_header_output(
            event=event,
            tool_name=tool_name,
            tool_response=observed_tool_response,
            session_id=correlation.session_id,
            trace_id=trace_id,
            model=correlation.model,
        )

    def _handle_codex_followup_post_tool_use(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Observe a child turn trigger without recording a second delegation."""

        tool_input = payload.get("tool_input")
        tool_response: Any = payload.get("tool_response")
        if event == "PostToolUseFailure":
            tool_response = {
                "status": "failed",
                "error": _required_string(payload, "error"),
                "is_interrupt": _optional_bool(payload, "is_interrupt"),
            }
        correlation = self._correlation(payload, tool_input, tool_response)
        trace_id = (
            correlation.turn_id
            or self._unambiguous_open_trace(correlation.session_id)
            or correlation.tool_use_id
        )
        return self._codex_post_tool_header_output(
            event=event,
            tool_name=_required_string(payload, "tool_name"),
            tool_response=tool_response,
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
            context = self._header_snapshot_context(
                session_id=session_id,
                trace_id=trace_id,
                model=model,
                marker="UPDATED",
                instruction=(
                    "Agency recorded the preceding tool observation. Start the next "
                    "substantive or final parent response with these exact five lines, "
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
        try:
            from agency_runtime.core.child_delivery_evidence import (
                _collect_restricted_codex_canary_child_delivery,
            )

            _collect_restricted_codex_canary_child_delivery(
                self.store,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
            )
        except Exception:
            logger.debug(
                "restricted Codex child delivery could not be collected after wait",
                exc_info=True,
            )
        return self._header_snapshot_context(
            session_id=session_id,
            trace_id=trace_id,
            model=model,
            marker="FINAL",
            instruction=(
                "The native wait completed. Start the next substantive or final parent "
                "response with these exact five lines, unchanged, then add the response "
                "body. This is current-turn Store evidence, not a suggested draft."
            ),
        )

    def _header_snapshot_context(
        self,
        *,
        session_id: str,
        trace_id: str,
        model: str,
        marker: str,
        instruction: str,
    ) -> str:
        """Render one exact current-turn header without manufacturing evidence."""

        # Codex, Claude, and ZCode all deliver parent-turn context through this
        # hook. Keep the exact Store-backed header on that shared path even
        # though their native child lifecycle surfaces differ.
        if self.host not in {"codex", "claude", "zcode"} or not session_id or not trace_id:
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
        plan_context = self._restricted_codex_activation_plan_context(
            payload,
            result,
            session_id=correlation.session_id,
            trace_id=trace_id,
        )
        header_context = self._header_snapshot_context(
            session_id=correlation.session_id,
            trace_id=trace_id,
            model=correlation.model,
            marker="INITIAL",
            instruction=(
                "Start each substantive progress update and the final parent response "
                "with these exact five lines, unchanged, then add the response body. "
                "A later Agency header snapshot for this turn supersedes this one."
            ),
        )
        context_segments = [context.rstrip()]
        if plan_context:
            context_segments.append(plan_context)
        if header_context:
            context_segments.append(header_context)
        combined_context = "\n\n".join(context_segments)
        if len(combined_context) > MAX_CONTEXT_CHARS:
            combined_context = context
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": combined_context[:MAX_CONTEXT_CHARS],
            }
        }

    def _restricted_codex_activation_plan_context(
        self,
        payload: dict[str, Any],
        result: Any,
        *,
        session_id: str,
        trace_id: str,
    ) -> str:
        """Expose one fixed execution row only for the proven canary parent."""

        if self.host != "codex" or not isinstance(result, dict):
            return ""
        if result.get("session_id") != session_id or result.get("trace_id") != trace_id:
            return ""
        if self._restricted_codex_activation_parent_scope(payload) != (session_id, trace_id):
            return ""
        try:
            from agency_runtime.core.activation_canary_contract import (
                render_codex_activation_canary_delegation_plan,
            )

            return render_codex_activation_canary_delegation_plan(result.get("routing"))
        except (TypeError, ValueError):
            return ""

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
            if (
                self.host == "codex"
                and _required_string(payload, "tool_name") in _CODEX_FOLLOWUP_TOOL_NAMES
            ):
                return self._handle_codex_followup_post_tool_use(event, payload)
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
        # A stale installed runtime is reported once per session rather than on
        # every tool call: the pointer read is cheap but not free, and an
        # operator only needs to be told once that a reinstall is due.
        notice = self._runtime_staleness_notice() if event == "SessionStart" else {}
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
            return notice
        if not callable(operation):
            raise RuntimeError(failure)
        operation(session_id=correlation.session_id, host=self.host)
        return notice

    def _runtime_staleness_notice(self) -> dict[str, Any]:
        """Report a stale installed hook runtime loudly without blocking work.

        The drift is advisory: it names a reinstall the operator must run, but
        it never denies an event.  A stale runtime still enforces old code
        paths, so silently continuing was the original defect -- what changes
        here is that the operator is told why, not whether work proceeds.
        """

        from agency_runtime.core.runtime_staleness import runtime_staleness

        try:
            drift = runtime_staleness(host=self.host)
        except Exception:
            return {}
        if drift is None:
            return {}
        with suppress(Exception):
            print(f"agency_runtime_stale_runtime {drift.message}", file=sys.stderr)
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": drift.message[:MAX_CONTEXT_CHARS],
            }
        }

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
            return self._publish_unverified(
                correlation.session_id, trace_id, "terminal_lifecycle_unreadable"
            )

        verification = self._verify_final_response(
            final_response,
            correlation=correlation,
            trace_id=trace_id,
            retry=retry,
        )
        if verification.get("verification_unavailable") is True:
            self._close_turn(correlation.session_id, trace_id, "verification_failed")
            return self._publish_unverified(
                correlation.session_id, trace_id, "verification_unavailable"
            )
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
            return self._publish_unverified(
                correlation.session_id, trace_id, "terminal_finalization_not_persisted"
            )
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

        logger.debug(
            "handle_terminal_rejection_start",
            extra={
                "session_id": correlation.session_id,
                "trace_id": trace_id,
                "action": action,
                "status": status,
                "delegation_strength": verification.get("delegation_strength"),
                "evidence_revision": verification.get("evidence_revision"),
                "missing_count": len(missing),
            },
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
            logger.error(
                "handle_terminal_rejection_commit_failed",
                extra={
                    "session_id": correlation.session_id,
                    "trace_id": trace_id,
                    "action": action,
                    "status": status,
                },
            )
            return self._verification_failed(correlation.session_id, trace_id)

        logger.info(
            "handle_terminal_rejection_committed",
            extra={
                "session_id": correlation.session_id,
                "trace_id": trace_id,
                "action": action,
                "status": status,
            },
        )
        return self._terminal_completion_result(action)

    def _verification_failed(self, session_id: str, trace_id: str) -> dict[str, Any]:
        logger.error(
            "verification_failed_closing_turn",
            extra={
                "session_id": session_id,
                "trace_id": trace_id,
            },
        )
        closed = self._close_turn(session_id, trace_id, "verification_failed")
        if not closed:
            logger.error(
                "verification_failed_close_turn_failed",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                },
            )
        return self._publish_unverified(session_id, trace_id, "terminal_rejection_not_persisted")

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
            logger.error(
                "commit_terminal_finalization store method unavailable",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "action": action,
                    "status": status,
                },
            )
            return False
        digest = response_hash(response_text)

        # Validate expected_evidence_revision early and log issues
        if isinstance(expected_evidence_revision, bool):
            logger.error(
                "evidence_revision_validation_failed: bool_type",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_evidence_revision_type": type(expected_evidence_revision).__name__,
                    "expected_evidence_revision_value": str(expected_evidence_revision),
                },
            )
            return False
        if not isinstance(expected_evidence_revision, int):
            logger.error(
                "evidence_revision_validation_failed: not_int",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_evidence_revision_type": type(expected_evidence_revision).__name__,
                    "expected_evidence_revision_value": str(expected_evidence_revision),
                },
            )
            return False
        if expected_evidence_revision <= 0:
            logger.error(
                "evidence_revision_validation_failed: non_positive",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_evidence_revision_value": expected_evidence_revision,
                },
            )
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

        logger.debug(
            "store_commit_terminal_finalization_call",
            extra={
                "session_id": session_id,
                "trace_id": trace_id,
                "action": action,
                "status": status,
                "expected_evidence_revision": expected_evidence_revision,
                "response_hash": digest[:16],
            },
        )

        try:
            result = committer(**arguments)
        except Exception as exc:
            logger.error(
                "store_commit_terminal_finalization_exception",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "action": action,
                    "status": status,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            return False

        # Validate the result from Store and log which constraint fails
        if not isinstance(result, dict):
            logger.error(
                "store_result_validation_failed: not_dict",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "result_type": type(result).__name__,
                    "result_value": str(result)[:200],
                },
            )
            return False

        result_authoritative = result.get("authoritative")
        if result_authoritative is not True:
            logger.error(
                "store_result_validation_failed: authoritative_constraint",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_authoritative": True,
                    "actual_authoritative": result_authoritative,
                    "actual_authoritative_type": type(result_authoritative).__name__,
                },
            )
            return False

        result_outcome = result.get("outcome")
        if result_outcome not in {"committed", "replay"}:
            logger.error(
                "store_result_validation_failed: outcome_constraint",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_outcomes": ["committed", "replay"],
                    "actual_outcome": result_outcome,
                    "full_result": str(result)[:500],
                },
            )
            return False

        result_action = result.get("action")
        if result_action != action:
            logger.error(
                "store_result_validation_failed: action_constraint",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_action": action,
                    "actual_action": result_action,
                },
            )
            return False

        result_response_hash = result.get("response_hash")
        if result_response_hash != digest:
            logger.error(
                "store_result_validation_failed: response_hash_constraint",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_response_hash": digest[:16],
                    "actual_response_hash": (str(result_response_hash) or "")[:16],
                },
            )
            return False

        result_status = result.get("status")
        if result_status != status:
            logger.error(
                "store_result_validation_failed: status_constraint",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_status": status,
                    "actual_status": result_status,
                },
            )
            return False

        logger.info(
            "store_terminal_finalization_committed",
            extra={
                "session_id": session_id,
                "trace_id": trace_id,
                "action": action,
                "status": status,
                "outcome": result_outcome,
            },
        )
        return True

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

    def _publish_unverified(self, session_id: str, trace_id: str, cause: str) -> dict[str, Any]:
        """Let the turn publish when Agency could not verify or persist its evidence.

        Agency failing to check something is not a finding about the response. It
        is Agency being unavailable, and rule 8 is explicit that Agency gets out of
        the way rather than withholding the host's answer -- the same reasoning the
        just-in-time path already applies to a child ("a compatibility check that
        cannot run must not cost the child its specialists") and that
        ``_boundary_failure_result`` already applies to every non-Stop event.

        The failure is recorded at error level so it stays diagnosable; what it no
        longer does is cost the user a completed turn.
        """

        logger.error(
            "evidence_unavailable_publishing_anyway",
            extra={
                "session_id": session_id,
                "trace_id": trace_id,
                "cause": cause,
                "host": self.host,
            },
        )
        return {}

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
            # Ordinary, not a fault: hosts that omit turn_id leave the trace
            # deliberately uncorrelated, so there is no turn to close.
            logger.debug(
                "close_turn_skipped: no correlated turn",
                extra={
                    "session_id_empty": not session_id,
                    "trace_id_empty": not trace_id,
                },
            )
            return False
        closer = getattr(self.store, "close_turn_evidence", None)
        getter = getattr(self.store, "get_run", None)
        if not callable(closer) or not callable(getter):
            logger.error(
                "close_turn_store_method_unavailable",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "closer_available": callable(closer),
                    "getter_available": callable(getter),
                },
            )
            return False
        try:
            closer(session_id, trace_id, status=status)
            run = getter(trace_id)
        except Exception as exc:
            logger.error(
                "close_turn_store_call_exception",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "status": status,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )
            return False

        # Validate the result
        if not isinstance(run, dict):
            logger.error(
                "close_turn_result_validation_failed: not_dict",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "status": status,
                    "result_type": type(run).__name__,
                },
            )
            return False

        run_session_id = str(run.get("session_id") or "")
        if run_session_id != session_id:
            logger.error(
                "close_turn_result_validation_failed: session_id_mismatch",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "status": status,
                    "expected_session_id": session_id,
                    "actual_session_id": run_session_id,
                },
            )
            return False

        run_status = str(run.get("status") or "")
        if run_status != status:
            logger.error(
                "close_turn_result_validation_failed: status_mismatch",
                extra={
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "expected_status": status,
                    "actual_status": run_status,
                },
            )
            return False

        logger.info(
            "close_turn_success",
            extra={
                "session_id": session_id,
                "trace_id": trace_id,
                "status": status,
            },
        )
        return True

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

    encoded = _encoded_hook_output(payload)
    if encoded is None or len(encoded) > MAX_HOOK_OUTPUT_BYTES:
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
                "hook_denied",
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
            reason=str(exc),
        )
        outcome = "response publication blocked" if result else "host operation continues"
        mark_current_observation(
            "denied" if result else "degraded",
            "boundary_failure",
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
            reason=str(exc),
        )
        outcome = "response publication blocked" if result else "host operation continues"
        mark_current_observation(
            "denied" if result else "degraded",
            "boundary_failure",
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

    from agency_runtime.core.hook_logging import install_hook_log_sink

    # Opt-in and file-only; absent AGENCY_HOOK_LOG this is a no-op and stderr
    # stays clean either way.  Installed here because this is the one entry
    # every hook event passes through.
    if install_hook_log_sink():
        logger.debug("hook stdio start host=%s event=%s", host, expected_event or "<any>")
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
    "MAX_HOOK_MODEL_BYTES",
    "MAX_HOOK_OUTPUT_BYTES",
    "HookBridge",
    "HookCorrelation",
    "HookInputError",
    "hook_host_adapter",
    "run_hook_stdio",
]
