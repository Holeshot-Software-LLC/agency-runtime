"""Base adapter interface — all adapters implement this contract."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.store.sqlite import Store

_MAX_EMBEDDED_RESULT_BYTES = 256 * 1024
_MAX_NATIVE_DELEGATION_TASKS = 16
_NATIVE_DELEGATION_TASK_KEYS = (
    "goal",
    "task",
    "prompt",
    "description",
    "work_unit_id",
    "workUnitId",
    "unit_id",
    "task_id",
    "backend",
)


class AdapterFinalizationRejected(RuntimeError):
    """Carry the exact non-accepted candidate without exposing it in the error."""

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__("Agency Runtime finalization did not accept the correlated response")
        self.finalization_result = dict(result)


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


_FAILURE_STATUSES = {
    "cancelled",
    "canceled",
    "error",
    "failed",
    "failure",
    "interrupted",
    "rejected",
    "skipped",
    "timed_out",
    "timeout",
}
_FALSE_FAILURE_KEYS = ("success", "ok", "delegated", "loaded")
_TRUE_FAILURE_KEYS = (
    "isError",
    "is_error",
    "cancelled",
    "canceled",
    "timed_out",
)
_EXIT_CODE_KEYS = ("returncode", "return_code", "exit_code", "exitCode")
_NESTED_RESULT_KEYS = ("result", "output", "data", "content", "text")


def _failure_message(payload: dict[str, Any], default: str = "tool call failed") -> str:
    for key in ("message", "error", "reason", "detail", "stderr", "exit_reason"):
        value = payload.get(key)
        if value not in (None, "", False):
            if isinstance(value, dict):
                return _failure_message(value, default)
            return _clean(value, default)
    content = payload.get("content")
    if isinstance(content, (list, tuple)):
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                return _clean(item["text"], default)
    return default


def _sequence_failure_reason(result: list[Any] | tuple[Any, ...], depth: int) -> str:
    for item in result:
        reason = _tool_failure_reason(item, _depth=depth + 1)
        if reason:
            return reason
    return ""


def _text_failure_reason(result: str, depth: int) -> str:
    text = result.strip()
    if not text:
        return ""
    try:
        parsed = safe_load_bounded_json(
            text,
            maximum_bytes=_MAX_EMBEDDED_RESULT_BYTES,
            maximum_depth=32,
            maximum_nodes=5_000,
        )
    except Exception:
        if text.startswith(("{", "[")):
            return "tool call returned invalid structured output"
    else:
        # Successful JSON parsing necessarily changes the source representation:
        # containers and scalars become Python values, while JSON strings lose
        # their required quoting. Recurse directly instead of retaining an
        # unreachable parsed-equals-source branch.
        return _tool_failure_reason(parsed, _depth=depth + 1)
    if text.lower().startswith(("error:", "failed:", "failure:", "exception:", "tool error:")):
        return text
    return ""


def _direct_mapping_failure(payload: dict[str, Any]) -> str:
    if payload.get("error") not in (None, "", False):
        return _failure_message(payload)
    if any(payload.get(key) is False for key in _FALSE_FAILURE_KEYS):
        return _failure_message(payload)
    if any(payload.get(key) is True for key in _TRUE_FAILURE_KEYS):
        return _failure_message(payload)
    if _clean(payload.get("status")).lower() in _FAILURE_STATUSES:
        return _failure_message(payload)
    for key in _EXIT_CODE_KEYS:
        value = payload.get(key)
        if value not in (None, "", 0, "0"):
            return _failure_message(payload, f"tool call exited with {value}")
    return ""


def _mapping_failure_reason(payload: dict[str, Any], depth: int) -> str:
    direct = _direct_mapping_failure(payload)
    if direct:
        return direct
    for key in _NESTED_RESULT_KEYS:
        if key not in payload:
            continue
        reason = _tool_failure_reason(payload.get(key), _depth=depth + 1)
        if reason:
            return reason
    return ""


def _tool_failure_reason(result: Any, *, _depth: int = 0) -> str:
    """Return an explicit tool failure reason without guessing from prose.

    Host hooks expose several result envelopes.  Failure flags are checked at
    every structured nesting level, including JSON strings and MCP-style
    ``content`` lists.  Missing results remain backward-compatible: absence of
    telemetry is not treated as proof of failure.
    """
    if _depth > 6 or result is None or result is True:
        return ""
    if result is False:
        return "tool call returned false"
    if isinstance(result, (list, tuple)):
        return _sequence_failure_reason(result, _depth)
    if isinstance(result, str):
        return _text_failure_reason(result, _depth)
    return _mapping_failure_reason(result, _depth) if isinstance(result, dict) else ""


def _tool_result(kwargs: dict[str, Any]) -> Any:
    for key in ("result", "tool_result", "output", "response"):
        if key in kwargs and kwargs.get(key) is not None:
            return kwargs.get(key)
    return None


def _native_delegation_batch(
    tool_name: str,
    args: dict[str, Any],
    result: Any,
) -> list[tuple[dict[str, Any], Any]] | None:
    """Project an official bounded Hermes ``delegate_task`` batch by task identity."""

    if tool_name != "delegate_task":
        return None
    tasks = args.get("tasks")
    if not isinstance(tasks, (list, tuple)):
        return None
    bounded_tasks = list(tasks[:_MAX_NATIVE_DELEGATION_TASKS])
    structured_result = result
    if isinstance(result, str):
        try:
            structured_result = safe_load_bounded_json(
                result,
                maximum_bytes=_MAX_EMBEDDED_RESULT_BYTES,
                maximum_depth=32,
                maximum_nodes=5_000,
            )
        except Exception:
            structured_result = result
    raw_results = structured_result.get("results") if isinstance(structured_result, dict) else None
    batch_native_run_id = (
        _clean(
            _nested_value(
                structured_result,
                ("delegation_id", "delegationId", "run_id", "runId"),
            )
        )
        if isinstance(structured_result, dict)
        else ""
    )
    indexed_results: dict[int, Any] = {}
    if isinstance(raw_results, (list, tuple)):
        for position, item in enumerate(raw_results[:_MAX_NATIVE_DELEGATION_TASKS]):
            task_index = item.get("task_index") if isinstance(item, dict) else position
            if (
                isinstance(task_index, bool)
                or not isinstance(task_index, int)
                or not 0 <= task_index < len(bounded_tasks)
            ):
                task_index = position
            if 0 <= task_index < len(bounded_tasks):
                indexed_results.setdefault(task_index, item)
    global_failure = _tool_failure_reason(structured_result)
    projected: list[tuple[dict[str, Any], Any]] = []
    for index, task in enumerate(bounded_tasks):
        if not isinstance(task, dict):
            continue
        task_args = {key: task[key] for key in _NATIVE_DELEGATION_TASK_KEYS if key in task}
        task_result = indexed_results.get(index)
        if task_result is None and global_failure:
            task_result = {"status": "failed", "error": global_failure}
        if batch_native_run_id:
            task_result = {
                **(task_result if isinstance(task_result, dict) else {}),
                "native_run_id": batch_native_run_id,
            }
        projected.append((task_args, task_result))
    return projected


def _record_native_delegation_observation(
    store: Store,
    *,
    session_id: str,
    host: str,
    agent: str,
    backend: str,
    goal: str,
    work_unit_id: str,
    trace_id: str,
    failure_reason: str,
    executed_worker_kind: str,
    executed_worker_id: str,
    native_run_id: str,
) -> None:
    """Persist failure or identity-complete native execution, never inference."""

    from agency_runtime.core.delegation.events import (
        mark_delegation_executed,
        mark_delegation_skipped,
    )

    arguments = {
        "store": store,
        "session_id": session_id,
        "host": host,
        "agent": agent,
        "backend": backend,
        "goal": goal,
        "work_unit_id": work_unit_id,
        "trace_id": trace_id,
        "executed_worker_kind": executed_worker_kind,
        "executed_worker_id": executed_worker_id,
        "native_run_id": native_run_id,
    }
    if failure_reason:
        mark_delegation_skipped(**arguments, reason=failure_reason)
        return
    if not executed_worker_id or not native_run_id:
        return
    mark_delegation_executed(**arguments)


def _tool_call_failure_reason(kwargs: dict[str, Any]) -> str:
    for key in ("result", "tool_result", "output", "response"):
        if key in kwargs:
            reason = _tool_failure_reason(kwargs.get(key))
            if reason:
                return reason
    envelope = {
        key: kwargs[key]
        for key in (
            "error",
            "success",
            "ok",
            "delegated",
            "loaded",
            "isError",
            "is_error",
            "status",
            "returncode",
            "return_code",
            "exit_code",
            "exitCode",
            "message",
            "reason",
            "detail",
            "stderr",
        )
        if key in kwargs
    }
    return _tool_failure_reason(envelope) if envelope else ""


def _nested_value(value: Any, keys: tuple[str, ...], *, _depth: int = 0) -> Any:
    if _depth > 5:
        return None
    if isinstance(value, str):
        try:
            value = safe_load_bounded_json(
                value,
                maximum_bytes=_MAX_EMBEDDED_RESULT_BYTES,
                maximum_depth=32,
                maximum_nodes=5_000,
            )
        except Exception:
            return None
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        for key in ("result", "output", "data"):
            found = _nested_value(value.get(key), keys, _depth=_depth + 1)
            if found not in (None, ""):
                return found
    return None


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


class BaseAdapter(ABC):
    """Base class for host/runtime adapters.

    Adapters are thin I/O shims. They translate between host events and
    the agency-runtime core. They should NOT reimplement routing,
    categorization, or delegation policy.
    """

    host_name: str = "unknown"

    def __init__(self, store: Store | None = None):
        self._store = store

    @property
    def store(self) -> Store:
        """Materialize storage only after the global master gate permits work."""

        if self._store is None:
            self._store = Store()
        return self._store

    @store.setter
    def store(self, value: Store) -> None:
        self._store = value

    def _uses_explicit_config(self) -> bool:
        """Return whether the adapter owns a caller-supplied immutable config."""

        return False

    def _was_nontrivial_turn(self, session_id: str, trace_id: str) -> bool:
        """Read authoritative request-kind evidence for exactly one turn.

        None is deliberately distinct from False in the Store API: unknown,
        corrupt, or mismatched evidence cannot silently downgrade a non-trivial
        turn to a trivial one at the completion boundary.
        """
        getter = getattr(self.store, "is_nontrivial_turn", None)
        if not callable(getter):
            raise RuntimeError("evidence store cannot verify turn request kind")
        result = getter(session_id, trace_id)
        if not isinstance(result, bool):
            raise RuntimeError("turn request kind could not be verified")
        return result

    def runtime_enabled(self) -> bool:
        """Return the current persistent soft-control state for this host."""
        from agency_runtime.core.runtime_control import master_enabled

        if not master_enabled():
            return False
        from agency_runtime.core.config_binding import assert_store_config_binding

        runtime_store = self.store
        if not self._uses_explicit_config():
            assert_store_config_binding(runtime_store)
        return bool(runtime_store.get_host_control(self.host_name).get("enabled", True))

    def resolve_turn_trace(self, session_id: str, trace_id: str = "") -> str:
        """Return an explicit trace or one unambiguous active trace."""
        explicit = _clean(trace_id)
        if explicit:
            return explicit
        getter = getattr(self.store, "get_open_traces_for_session", None)
        if not callable(getter) or not session_id:
            return ""
        try:
            candidates = list(getter(session_id))
        except Exception:
            return ""
        return str(candidates[0]) if len(candidates) == 1 else ""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter's runtime is installed and available."""
        ...

    @abstractmethod
    def get_delegate_backend(self) -> str | None:
        """Return the delegate backend name this adapter provides, or None."""
        ...

    def apply_finalization(
        self,
        draft_text: str,
        session_id: str,
        model: str = "",
        *,
        trace_id: str = "",
    ) -> str:
        """Apply header/finalization to the final visible reply."""
        if not self.runtime_enabled():
            return draft_text
        from agency_runtime.core.header.finalize import finalize_response

        trace_id = self.resolve_turn_trace(session_id, trace_id)
        result = finalize_response(
            draft_text,
            trace_metadata={
                "session_id": session_id,
                "trace_id": trace_id,
                "host": self.host_name,
            },
            store=self.store,
            model=model,
        )
        if result["action"] != "accept":
            raise AdapterFinalizationRejected(result)
        return result["text"]

    def _suggested_delegations(
        self,
        session_id: str,
        trace_id: str,
    ) -> list[dict[str, Any]]:
        from agency_runtime.core.delegation.events import suggested_delegations

        return suggested_delegations(self.store, session_id, trace_id=trace_id)

    def record_tool_call(self, **kwargs: Any) -> None:
        """Record skills, specialist loads, and actual delegation tool use."""
        if not self.runtime_enabled():
            return
        from agency_runtime.core.resident_managers import is_resident_manager_slug

        tool_name = kwargs.get("tool_name") or ""
        args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
        session_id = _clean(kwargs.get("session_id"))
        trace_id = self.resolve_turn_trace(session_id, _clean(kwargs.get("trace_id")))
        result = _tool_result(kwargs)
        failure_reason = _tool_call_failure_reason(kwargs)

        if tool_name == "skill_view":
            skill_name = args.get("name") or ""
            if skill_name and not failure_reason:
                self.store.record_skill_loaded(
                    session_id,
                    skill_name,
                    trace_id=trace_id,
                )

        elif tool_name in ("agency_agents_load", "agency_agents_inspect"):
            agent = args.get("agent") or args.get("slug") or ""
            if agent and not failure_reason and not is_resident_manager_slug(agent):
                self.store.record_specialist_loaded(
                    session_id,
                    agent,
                    trace_id=trace_id,
                )

        elif tool_name in (
            "agency.delegate",
            "agency_agents_delegate",
            "delegate_task",
            "delegate_async",
            "spawn_agent",
            "followup_task",
            "sessions_spawn",
        ):
            if not session_id or not trace_id:
                return
            native_batch = _native_delegation_batch(tool_name, args, result)
            if native_batch is not None:
                for task_args, task_result in native_batch:
                    self.record_tool_call(
                        tool_name=tool_name,
                        args=task_args,
                        result=task_result,
                        session_id=session_id,
                        trace_id=trace_id,
                    )
                return
            # Keep the caller's requested role only as a correlation hint and
            # immutable recommendation.  It is not proof of which native
            # worker executed the work unit; headers use executed_worker_kind.
            agency_agent_values = (
                (
                    args.get("agent"),
                    args.get("slug"),
                    args.get("recommended_agent"),
                    kwargs.get("agent"),
                    kwargs.get("recommended_agent"),
                    _nested_value(result, ("recommended_agent", "slug")),
                )
                if tool_name == "sessions_spawn"
                else (
                    args.get("agent"),
                    args.get("agentId"),
                    args.get("agent_id"),
                    args.get("slug"),
                    args.get("recommended_agent"),
                    kwargs.get("agent"),
                    kwargs.get("recommended_agent"),
                    _nested_value(result, ("agent", "slug", "recommended_agent")),
                )
            )
            agent = _clean(
                _first_value(
                    *agency_agent_values,
                )
            )
            goal = _clean(
                _first_value(
                    args.get("goal"),
                    args.get("task"),
                    args.get("prompt"),
                    args.get("description"),
                    kwargs.get("goal"),
                    kwargs.get("task"),
                    _nested_value(result, ("goal", "task", "prompt", "description")),
                )
            )
            native_unit_values = (
                (args.get("taskName"), args.get("task_name"))
                if tool_name == "sessions_spawn"
                else ()
            )
            work_unit_id = _clean(
                _first_value(
                    args.get("work_unit_id"),
                    args.get("workUnitId"),
                    args.get("unit_id"),
                    args.get("task_id"),
                    *native_unit_values,
                    kwargs.get("work_unit_id"),
                    kwargs.get("workUnitId"),
                    _nested_value(
                        result,
                        (
                            "work_unit_id",
                            "workUnitId",
                            "unit_id",
                            "task_id",
                            "taskId",
                        ),
                    ),
                )
            )
            executed_worker_kind = "generic-worker"
            worker_identity_keys = (
                (
                    "child_session_key",
                    "childSessionKey",
                    "session_id",
                    "sessionId",
                    "worker_id",
                    "workerId",
                    "agent_id",
                    "agentId",
                )
                if tool_name == "sessions_spawn"
                else (
                    "agent_id",
                    "agentId",
                    "child_session_key",
                    "childSessionKey",
                    "session_id",
                    "sessionId",
                    "worker_id",
                    "workerId",
                )
            )
            executed_worker_id = _clean(
                _first_value(
                    _nested_value(result, worker_identity_keys),
                    kwargs.get("agent_id"),
                    kwargs.get("worker_id"),
                )
            )
            native_run_id = _clean(
                _nested_value(
                    result,
                    (
                        "native_run_id",
                        "nativeRunId",
                        "delegation_id",
                        "delegationId",
                        "run_id",
                        "runId",
                    ),
                ),
                kwargs.get("tool_use_id"),
            )
            backend = (
                _clean(args.get("backend")) or "agency.delegate"
                if tool_name == "agency.delegate"
                else tool_name
            )
            _record_native_delegation_observation(
                self.store,
                session_id=session_id,
                host=self.host_name,
                agent=agent,
                backend=backend,
                goal=goal,
                work_unit_id=work_unit_id,
                trace_id=trace_id,
                failure_reason=failure_reason,
                executed_worker_kind=executed_worker_kind,
                executed_worker_id=executed_worker_id,
                native_run_id=native_run_id,
            )
            has_child_identity = bool(executed_worker_id and native_run_id)
            if tool_name == "sessions_spawn" and has_child_identity:
                child_recorder = getattr(self.store, "record_native_child_started", None)
                if callable(child_recorder):
                    child_recorder(
                        host=self.host_name,
                        backend=backend,
                        session_id=session_id,
                        trace_id=trace_id,
                        work_unit_id=work_unit_id,
                        worker_id=executed_worker_id,
                        native_run_id=native_run_id,
                    )
            elif self.host_name == "claude" and tool_name == "delegate_task" and has_child_identity:
                child_recorder = getattr(self.store, "record_native_child_ended", None)
                if callable(child_recorder):
                    child_recorder(
                        host=self.host_name,
                        backend=backend,
                        session_id=session_id,
                        trace_id=trace_id,
                        work_unit_id=work_unit_id,
                        worker_id=executed_worker_id,
                        native_run_id=native_run_id,
                        outcome="error" if failure_reason else "ok",
                        error=failure_reason,
                    )

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        """Host hook alias for tool-call evidence capture."""
        self.record_tool_call(**kwargs)

    def post_api_request_handler(self, **kwargs: Any) -> None:
        """Record a model receipt when a host exposes response telemetry.

        Hosts with richer telemetry can override this method. The default keeps
        generated plugins safe for OpenClaw, Codex, Claude, and generic wrappers:
        absent model data records an honest unavailable receipt; present
        response["model"] is stored as the concrete model that actually ran.
        """
        if not self.runtime_enabled():
            return

        from agency_runtime.core.receipts.normalize import normalize_host_receipt

        response = kwargs.get("response") if isinstance(kwargs.get("response"), dict) else {}
        requested_model = _clean(kwargs.get("model") or kwargs.get("requested_model"))
        session_id = _clean(kwargs.get("session_id"))
        trace_id = self.resolve_turn_trace(session_id, _clean(kwargs.get("trace_id")))
        if not session_id or not trace_id:
            return
        run_getter = getattr(self.store, "get_run", None)
        if not callable(run_getter):
            return
        try:
            run = run_getter(trace_id)
        except Exception:
            return
        if (
            not isinstance(run, dict)
            or _clean(run.get("session_id")) != session_id
            or _clean(run.get("status")) not in {"active", "evidence_only"}
        ):
            return
        resolved_model = _clean(
            kwargs.get("response_model") or kwargs.get("resolved_model") or response.get("model")
        )
        resolved_provider = _clean(kwargs.get("resolved_provider"))
        receipt_source = _clean(kwargs.get("source")) or "host"
        model_group = _clean(kwargs.get("model_group")) or requested_model
        router_backed = resolved_provider.casefold() == "litellm" or (
            "litellm" in receipt_source.casefold() and not resolved_provider
        )
        if router_backed:
            # A host-level callback can prove which LiteLLM route was
            # requested, but only the LiteLLM callback can reconcile the
            # provider/model that actually served it. Never promote an alias
            # echo into actual-model evidence.
            resolved_provider = ""
            resolved_model = ""
        actual_model = resolved_model
        if "/" in resolved_model:
            detected_provider, detected_model = resolved_model.split("/", 1)
            actual_model = detected_model
            if not resolved_provider:
                resolved_provider = detected_provider

        receipt_metadata = {
            "host": self.host_name,
            "session_id": session_id,
            "requested_model": requested_model,
            "model_group": model_group,
            "resolved_provider": resolved_provider,
            "resolved_model": actual_model,
            "api_base": _clean(kwargs.get("api_base")),
            "attempted_fallbacks": kwargs.get("attempted_fallbacks", 0),
            "model_id": _clean(kwargs.get("model_id")),
            "source": receipt_source,
            "started_at": _clean(kwargs.get("started_at")),
            "ended_at": _clean(kwargs.get("ended_at")),
            "status": _clean(kwargs.get("status")) or "success",
        }
        if not resolved_model:
            receipt_metadata.update(
                {
                    "resolved_model": "unavailable",
                    "source": "unknown",
                    "status": _clean(kwargs.get("status")) or "unavailable",
                    "model_id": _clean(kwargs.get("model_id")) or "no host response model",
                }
            )

        receipt = normalize_host_receipt(receipt_metadata)
        self.store.record_model_receipt(
            trace_id=trace_id,
            session_id=session_id,
            host=self.host_name,
            requested_model=requested_model,
            model_group=receipt.get("model_group", ""),
            resolved_provider=receipt.get("resolved_provider", ""),
            resolved_model=receipt.get("resolved_model", ""),
            api_base=receipt.get("api_base", ""),
            attempted_fallbacks=int(receipt.get("attempted_fallbacks", 0)),
            model_id=receipt.get("model_id", ""),
            source=receipt.get("source", "host"),
            started_at=receipt.get("started_at", ""),
            ended_at=receipt.get("ended_at", ""),
            status=receipt.get("status", "success"),
        )

    def build_preflight_context(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
        *,
        config: Any | None = None,
        persisted_user_message: str | None = None,
        reservation_token: str = "",
        capabilities_restricted: bool = False,
        origin_receipt: Any | None = None,
        parent_session_id: str = "",
        parent_trace_id: str = "",
        native_worker_id: str = "",
        native_run_id: str = "",
    ) -> dict[str, Any] | None:
        """Run selector preflight and persist suggested delegations."""
        if not self.runtime_enabled():
            return None
        del model
        from agency_runtime.core.host_capabilities import (
            EXECUTION_HOSTS,
            native_adapter_capability_receipt,
        )
        from agency_runtime.core.preflight import run_preflight
        from agency_runtime.core.turn_origin import native_adapter_turn_origin

        current_trace_id = trace_id or str(uuid4())
        if origin_receipt is None:
            origin_receipt = native_adapter_turn_origin(
                "external_user",
                host=self.host_name,
                event="adapter_preflight",
                session_id=session_id,
                trace_id=current_trace_id,
            )
        capability_receipt = None
        if self.host_name in EXECUTION_HOSTS:
            capability_receipt = native_adapter_capability_receipt(
                self.host_name,
                platform="windows" if os.name == "nt" else "linux",
                session_id=session_id,
                trace_id=current_trace_id,
                restricted=capabilities_restricted,
            )

        result = run_preflight(
            self.store,
            session_id=session_id,
            user_message=user_message,
            host=self.host_name,
            trace_id=current_trace_id,
            config=config,
            persisted_user_message=persisted_user_message,
            reservation_token=reservation_token,
            capability_receipt=capability_receipt,
            origin_receipt=origin_receipt,
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            native_worker_id=native_worker_id,
            native_run_id=native_run_id,
        )
        return result.as_dict()

    def pre_llm_call_handler(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
        *,
        reservation_token: str = "",
        origin_receipt: Any | None = None,
        parent_session_id: str = "",
        parent_trace_id: str = "",
        native_worker_id: str = "",
        native_run_id: str = "",
    ) -> dict[str, Any] | None:
        """Host hook alias for pre-LLM routing context."""
        return self.build_preflight_context(
            session_id,
            user_message,
            model,
            trace_id,
            reservation_token=reservation_token,
            origin_receipt=origin_receipt,
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            native_worker_id=native_worker_id,
            native_run_id=native_run_id,
        )

    def enforce_pre_verify(
        self,
        final_response: str,
        session_id: str = "",
        model: str = "",
        attempt: int = 0,
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Gate response completion on header, specialist, and delegation evidence."""
        del attempt

        decision = self.evaluate_completion_policy(
            final_response,
            session_id=session_id,
            model=model,
            trace_id=trace_id,
        )
        if decision.get("action") == "continue":
            return {
                "action": "continue",
                "message": str(
                    decision.get("message")
                    or "Agency Runtime evidence verification requires another pass."
                ),
            }
        return None

    def evaluate_completion_policy(
        self,
        final_response: str,
        *,
        session_id: str = "",
        model: str = "",
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Return an internal decision bound to one atomic evidence revision."""

        if not self.runtime_enabled():
            return {"action": "accept", "runtime_disabled": True}
        from agency_runtime.core.header.contract import (
            evaluate_completion_policy as evaluate_contract,
        )

        trace_id = self.resolve_turn_trace(session_id, trace_id)
        return dict(
            evaluate_contract(
                final_response,
                session_id=session_id,
                trace_id=trace_id,
                store=self.store,
                model=model,
            )
        )

    def pre_verify_handler(
        self,
        final_response: str,
        session_id: str = "",
        model: str = "",
        attempt: int = 0,
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Host hook alias for final-response verification."""
        return self.enforce_pre_verify(
            final_response,
            session_id,
            model,
            attempt,
            trace_id,
        )
