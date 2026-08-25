"""Hermes host plugin payload rendering."""

from __future__ import annotations

from pathlib import Path

from agency_runtime.core.config import AgencyConfig

_HERMES_BRIDGE_PLUGIN = r'''"""Agency Runtime native Hermes bridge plugin (managed file)."""

from __future__ import annotations

import json
import math
import subprocess
import threading
from collections import OrderedDict
from collections.abc import Mapping, Sequence

_PYTHON = __AGENCY_PYTHON__
_BOOTSTRAP = __AGENCY_BOOTSTRAP__
_CONFIG_PATH = __AGENCY_CONFIG__
_TIMEOUT_SECONDS = __AGENCY_TIMEOUT__
_MODULE_ARGS = ("-I", "-S", _BOOTSTRAP, "agency_runtime.adapters.hermes.bridge")
_MAX_INPUT_BYTES = 1024 * 1024
_MAX_OUTPUT_BYTES = 128 * 1024
_MAX_TEXT_BYTES = 64 * 1024
_MAX_FINALIZER_RESULT_CHARS = 4_096
_MAX_DEPTH = 20
_MAX_NODES = 8192
_MAX_ITEMS = 128
_MAX_ACTIVE_TURNS = 1024
_ACTIVE_TURN_TRACES = OrderedDict()
_ACTIVE_TURN_LOCK = threading.RLock()
_ACTIVE_CHILD_TRACES = OrderedDict()
_AMBIGUOUS_CHILD_BINDING = object()
_FINALIZATION_BLOCK_RESPONSE = (
    "Agency Runtime blocked an unverified draft because turn-scoped finalization "
    "did not accept it. Restore correlation and evidence, then start a new turn."
)
_PRE_VERIFY_UNAVAILABLE = (
    "Agency Runtime could not verify this draft. Restore turn correlation and "
    "evidence, then start a new turn."
)


def _bounded_text(value, maximum_bytes=_MAX_TEXT_BYTES):
    if isinstance(value, str):
        text = value
    elif value is None:
        text = ""
    elif isinstance(value, (bool, int, float)):
        text = str(value)
    else:
        text = "<" + type(value).__name__ + ">"
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= maximum_bytes:
        return text
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore")


def _project(value, depth=0, budget=None):
    if budget is None:
        budget = [0]
    budget[0] += 1
    if budget[0] > _MAX_NODES or depth > _MAX_DEPTH:
        return "[truncated]"
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, Mapping):
        projected = {}
        for index, (key, nested) in enumerate(value.items()):
            if index >= _MAX_ITEMS or budget[0] >= _MAX_NODES:
                projected["__truncated__"] = True
                break
            name = _bounded_text(key, 512)
            if not name or name in projected:
                continue
            projected[name] = _project(nested, depth + 1, budget)
        return projected
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        projected = []
        for index, nested in enumerate(value):
            if index >= _MAX_ITEMS or budget[0] >= _MAX_NODES:
                projected.append("[truncated]")
                break
            projected.append(_project(nested, depth + 1, budget))
        return projected
    if isinstance(value, (bytes, bytearray)):
        return "<bytes>"
    return "<" + type(value).__name__ + ">"


def _invoke(action, payload=None):
    document = {"action": action}
    if isinstance(payload, Mapping):
        document.update(payload)
    encoded = json.dumps(
        _project(document),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    if len(encoded) > _MAX_INPUT_BYTES:
        raise RuntimeError("Agency Runtime Hermes bridge input exceeds its limit")
    argv = [_PYTHON, *_MODULE_ARGS]
    if _CONFIG_PATH:
        argv.extend(("--config", _CONFIG_PATH))
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    completed = subprocess.run(
        argv,
        input=encoded,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=_TIMEOUT_SECONDS,
        check=False,
        shell=False,
        close_fds=True,
        creationflags=creationflags,
    )
    if completed.returncode != 0 or len(completed.stdout) > _MAX_OUTPUT_BYTES:
        raise RuntimeError("Agency Runtime Hermes bridge unavailable")
    try:
        # JSON_LOAD_OWNERSHIP: this dependency-isolated generated plugin cannot
        # import Agency helpers; stdout is byte-capped and validated below.
        response = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise RuntimeError("Agency Runtime Hermes bridge returned invalid JSON") from exc
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError("Agency Runtime Hermes bridge rejected the operation")
    return response.get("result")


def _session_id(kwargs):
    return _bounded_text(
        kwargs.get("session_id")
        or kwargs.get("conversation_id")
        or kwargs.get("thread_id")
        or kwargs.get("task_id")
        or "",
        512,
    )


def _provided_trace_id(kwargs):
    # ``task_id`` is Hermes' documented session/task identifier on tool
    # callbacks. It is not a turn trace and must never become one.
    return _bounded_text(
        kwargs.get("turn_id")
        or kwargs.get("trace_id")
        or kwargs.get("request_id")
        or "",
        512,
    )


def _remember_turn(session_id, trace_id):
    if not session_id or not trace_id:
        return
    with _ACTIVE_TURN_LOCK:
        _ACTIVE_TURN_TRACES[session_id] = trace_id
        _ACTIVE_TURN_TRACES.move_to_end(session_id)
        while len(_ACTIVE_TURN_TRACES) > _MAX_ACTIVE_TURNS:
            _ACTIVE_TURN_TRACES.popitem(last=False)


def _forget_turn(session_id, trace_id=""):
    if not session_id:
        return
    with _ACTIVE_TURN_LOCK:
        current = _ACTIVE_TURN_TRACES.get(session_id)
        if current is not None and (not trace_id or current == trace_id):
            _ACTIVE_TURN_TRACES.pop(session_id, None)


def _correlation(kwargs, include_active=True):
    session_id = _session_id(kwargs)
    provided_trace_id = _provided_trace_id(kwargs)
    if not include_active or not session_id:
        return session_id, provided_trace_id
    with _ACTIVE_TURN_LOCK:
        active_trace_id = _ACTIVE_TURN_TRACES.get(session_id, "")
        if active_trace_id:
            _ACTIVE_TURN_TRACES.move_to_end(session_id)
    strong_trace_id = _bounded_text(
        kwargs.get("turn_id") or kwargs.get("trace_id") or "",
        512,
    )
    if active_trace_id and strong_trace_id and strong_trace_id != active_trace_id:
        return session_id, ""
    return session_id, active_trace_id or provided_trace_id


def _remember_preflight_result(session_id, result):
    if not isinstance(result, Mapping):
        return
    result_session_id = _bounded_text(result.get("session_id"), 512)
    result_trace_id = _bounded_text(result.get("trace_id"), 512)
    if session_id and result_session_id == session_id and result_trace_id:
        _remember_turn(session_id, result_trace_id)


def _pre_llm_call(**kwargs):
    session_id, trace_id = _correlation(kwargs, include_active=False)
    worker_id, _child_session_id, parent_session_id, parent_trace_id = _child_binding(
        worker_id=_bounded_text(
            kwargs.get("child_subagent_id") or kwargs.get("subagent_id"), 256
        ),
        child_session_id=session_id,
        parent_session_id=_bounded_text(kwargs.get("parent_session_id"), 512),
        child_role=_bounded_text(kwargs.get("child_role"), 256),
    )
    native_run_id = "hermes-subagent:" + worker_id if worker_id else ""
    _forget_turn(session_id)
    try:
        result = _invoke(
            "pre_llm_call",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "user_message": kwargs.get("user_message"),
                "model": kwargs.get("model"),
                "parent_session_id": parent_session_id,
                "parent_trace_id": parent_trace_id,
                "native_worker_id": worker_id,
                "native_run_id": native_run_id,
            },
        )
        _remember_preflight_result(session_id, result)
        return result
    except Exception:
        return None


def _post_tool_call(tool_name="", args=None, result=None, **kwargs):
    session_id, trace_id = _correlation(kwargs)
    if not session_id or not trace_id:
        return None
    try:
        _invoke(
            "post_tool_call",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "tool_name": tool_name,
                "args": args or {},
                "result": result,
            },
        )
    except Exception:
        pass
    return None


def _post_api_request(**kwargs):
    session_id, trace_id = _correlation(kwargs)
    if not session_id or not trace_id:
        return None
    payload = {
        key: value
        for key, value in kwargs.items()
        if key not in {
            "session_id",
            "conversation_id",
            "thread_id",
            "turn_id",
            "trace_id",
            "request_id",
            "task_id",
        }
    }
    try:
        _invoke(
            "post_api_request",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "payload": payload,
            },
        )
    except Exception:
        pass
    return None


def _hermes_child_identity(value):
    child_id = _bounded_text(value, 256).strip()
    if not child_id:
        return "", ""
    return child_id, "hermes-subagent:" + child_id


def _hermes_child_outcome(value):
    normalized = _bounded_text(value, 32).strip().lower()
    if normalized in {"ok", "success", "succeeded", "completed", "complete"}:
        return "ok"
    if normalized in {"error", "failed", "failure"}:
        return "error"
    if normalized in {"timeout", "timed_out", "timed-out"}:
        return "timeout"
    if normalized in {"killed", "cancelled", "canceled", "aborted"}:
        return "killed"
    if normalized in {"reset", "deleted"}:
        return normalized
    return "unknown"


def _remember_child_trace(
    worker_id,
    child_session_id,
    parent_session_id,
    trace_id,
    child_role="",
):
    normalized_worker = _bounded_text(worker_id, 256)
    normalized_child_session = _bounded_text(child_session_id, 512)
    normalized_parent_session = _bounded_text(parent_session_id, 512)
    if (
        not normalized_worker
        or not normalized_child_session
        or not normalized_parent_session
        or not trace_id
    ):
        return
    correlation = (
        normalized_worker,
        normalized_parent_session,
        trace_id,
        _bounded_text(child_role, 256),
    )
    with _ACTIVE_TURN_LOCK:
        existing = _ACTIVE_CHILD_TRACES.get(normalized_child_session)
        if existing is None or existing == correlation:
            _ACTIVE_CHILD_TRACES[normalized_child_session] = correlation
        else:
            _ACTIVE_CHILD_TRACES[normalized_child_session] = _AMBIGUOUS_CHILD_BINDING
        _ACTIVE_CHILD_TRACES.move_to_end(normalized_child_session)
        while len(_ACTIVE_CHILD_TRACES) > _MAX_ACTIVE_TURNS:
            _ACTIVE_CHILD_TRACES.popitem(last=False)


def _child_binding(
    worker_id="",
    child_session_id="",
    parent_session_id="",
    parent_trace_id="",
    child_role="",
):
    normalized_worker = _bounded_text(worker_id, 256)
    normalized_child_session = _bounded_text(child_session_id, 512)
    normalized_parent_session = _bounded_text(parent_session_id, 512)
    normalized_parent_trace = _bounded_text(parent_trace_id, 512)
    normalized_role = _bounded_text(child_role, 256)
    with _ACTIVE_TURN_LOCK:
        if normalized_child_session:
            correlation = _ACTIVE_CHILD_TRACES.get(normalized_child_session)
            if correlation is None or correlation is _AMBIGUOUS_CHILD_BINDING:
                return "", "", "", ""
            matches = [(normalized_child_session, correlation)]
        elif normalized_worker:
            matches = [
                (candidate_session, values)
                for candidate_session, values in _ACTIVE_CHILD_TRACES.items()
                if values is not _AMBIGUOUS_CHILD_BINDING
                and values[0] == normalized_worker
            ]
        elif normalized_parent_session and normalized_role:
            matches = [
                (candidate_session, values)
                for candidate_session, values in _ACTIVE_CHILD_TRACES.items()
                if values is not _AMBIGUOUS_CHILD_BINDING
                and values[1] == normalized_parent_session
                and values[3] == normalized_role
            ]
        else:
            return "", "", "", ""
        if len(matches) != 1:
            return "", "", "", ""
        resolved_child_session, values = matches[0]
        resolved_worker, bound_parent_session, trace_id, _bound_role = values
        if normalized_worker and normalized_worker != resolved_worker:
            return "", "", "", ""
        if normalized_parent_session and normalized_parent_session != bound_parent_session:
            return "", "", "", ""
        if normalized_parent_trace and normalized_parent_trace != trace_id:
            return "", "", "", ""
        _ACTIVE_CHILD_TRACES.move_to_end(resolved_child_session)
        return resolved_worker, resolved_child_session, bound_parent_session, trace_id


def _forget_child_trace(worker_id, child_session_id):
    normalized_worker = _bounded_text(worker_id, 256)
    normalized_child_session = _bounded_text(child_session_id, 512)
    with _ACTIVE_TURN_LOCK:
        correlation = _ACTIVE_CHILD_TRACES.get(normalized_child_session)
        if (
            correlation is not None
            and correlation is not _AMBIGUOUS_CHILD_BINDING
            and correlation[0] == normalized_worker
        ):
            _ACTIVE_CHILD_TRACES.pop(normalized_child_session, None)


def _subagent_start(
    parent_session_id="",
    parent_turn_id="",
    child_session_id="",
    child_subagent_id="",
    child_role="",
    child_goal="",
    **kwargs,
):
    """Record only host-issued Hermes child lineage and the exact child goal."""

    worker_id, native_run_id = _hermes_child_identity(
        child_subagent_id or kwargs.get("subagent_id")
    )
    session_id = _bounded_text(parent_session_id, 512)
    trace_id = _bounded_text(parent_turn_id, 512)
    normalized_child_session_id = _bounded_text(child_session_id, 512)
    goal = _bounded_text(child_goal)
    if (
        not session_id
        or not trace_id
        or not normalized_child_session_id
        or not worker_id
        or not goal
    ):
        return None
    try:
        _invoke(
            "native_child_started",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "worker_id": worker_id,
                "native_run_id": native_run_id,
                "child_session_id": normalized_child_session_id,
                "goal": goal,
                "work_unit_id": _bounded_text(
                    kwargs.get("work_unit_id") or kwargs.get("task_id"),
                    160,
                ),
            },
        )
        _remember_child_trace(
            worker_id,
            normalized_child_session_id,
            session_id,
            trace_id,
            child_role,
        )
    except Exception:
        pass
    return None


def _subagent_stop(
    parent_session_id="",
    parent_turn_id="",
    child_session_id="",
    child_role="",
    child_status="",
    child_subagent_id="",
    subagent_id="",
    **kwargs,
):
    """Close a Hermes child only when the stop hook carries exact identity."""

    provided_worker_id, _native_run_id = _hermes_child_identity(
        child_subagent_id or subagent_id or kwargs.get("child_subagent_id")
    )
    worker_id, resolved_child_session_id, session_id, trace_id = _child_binding(
        worker_id=provided_worker_id,
        child_session_id=_bounded_text(child_session_id, 512),
        parent_session_id=_bounded_text(parent_session_id, 512),
        parent_trace_id=_bounded_text(parent_turn_id, 512),
        child_role=child_role,
    )
    if not worker_id:
        return None
    _resolved_worker, native_run_id = _hermes_child_identity(worker_id)
    try:
        _invoke(
            "native_child_ended",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "worker_id": worker_id,
                "native_run_id": native_run_id,
                "outcome": _hermes_child_outcome(child_status),
                "error": _bounded_text(kwargs.get("error") or kwargs.get("reason"), 4096),
            },
        )
    except Exception:
        pass
    finally:
        _forget_child_trace(worker_id, resolved_child_session_id)
        _forget_turn(resolved_child_session_id)
    return None


def _attempt_number(value):
    try:
        normalized = int(value)
    except (TypeError, ValueError, OverflowError):
        return 1
    return normalized if normalized >= 0 else 1


def _pre_verify(final_response="", attempt=0, **kwargs):
    normalized_attempt = _attempt_number(attempt)
    session_id, trace_id = _correlation(kwargs)
    try:
        return _invoke(
            "pre_verify",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "final_response": final_response,
                "model": kwargs.get("model"),
                "attempt": normalized_attempt,
            },
        )
    except Exception:
        return None


def _transform_llm_output(response_text="", **kwargs):
    session_id, trace_id = _correlation(kwargs)
    try:
        result = _invoke(
            "transform_llm_output",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "response_text": response_text,
                "model": kwargs.get("model"),
            },
        )
    except Exception:
        # Agency could not run at all for this turn.  Its own unavailability is
        # not a finding about the response, so the draft is returned unchanged.
        # An evaluated rejection still arrives as a replacement from the bridge.
        return response_text
    return result if isinstance(result, str) and result.strip() else response_text


def _finalize_tool_result(draft_text, missing):
    return json.dumps(
        {
            "action": "continue",
            "text": draft_text,
            "missing": list(missing),
        },
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _agency_finalize(args=None, **kwargs):
    arguments = args if isinstance(args, Mapping) else {}
    draft_text = _bounded_text(arguments.get("draft_text"))
    session_id, trace_id = _correlation(kwargs)
    try:
        result = _invoke(
            "finalize",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "draft_text": draft_text,
                "model": kwargs.get("model"),
            },
        )
    except Exception:
        return _finalize_tool_result("", ["agency_runtime"])
    if isinstance(result, str):
        return _bounded_text(result)
    if not isinstance(result, Mapping):
        return _finalize_tool_result("", ["agency_runtime"])
    finalized_text = result.get("text")
    if result.get("action") == "accept" and isinstance(finalized_text, str):
        # The bridge already byte-caps and validates its JSON envelope.  Do not
        # truncate an accepted response after its exact digest was committed.
        if len(finalized_text) <= _MAX_FINALIZER_RESULT_CHARS:
            return finalized_text
        return _finalize_tool_result("", ["host_transport"])
    return json.dumps(
        _project(result),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _on_session_end(**kwargs):
    session_id, trace_id = _correlation(kwargs)
    if not session_id or not trace_id:
        _forget_turn(session_id)
        return None
    try:
        _invoke(
            "on_session_end",
            {
                "session_id": session_id,
                "trace_id": trace_id,
                "completed": kwargs.get("completed") is True,
                "interrupted": kwargs.get("interrupted") is True,
            },
        )
    except Exception:
        pass
    finally:
        _forget_turn(session_id, trace_id)
    return None


def _agency_command(*args, **kwargs):
    raw_args = kwargs.get("args") or kwargs.get("raw_args") or ""
    if not raw_args:
        raw_args = next(
            (value for value in reversed(args) if isinstance(value, str)),
            "",
        )
    try:
        result = _invoke("control", {"raw_args": raw_args})
    except Exception:
        return "Agency Runtime control is unavailable. Restore the installed runtime and retry."
    return result if isinstance(result, str) else "Agency Runtime returned no control status."


def register(ctx):
    ctx.register_tool(
        name="agency_finalize",
        toolset="agency-runtime",
        schema={
            "name": "agency_finalize",
            "description": (
                "Construct the exact Agency final response from current turn evidence. "
                "Call exactly once with at most 3,000 draft characters immediately "
                "before answering, then emit the tool result byte-for-byte."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_text": {
                        "type": "string",
                        "description": (
                            "The complete substantive response body, at most 3,000 "
                            "characters, without a guessed Agency header."
                        ),
                    },
                },
                "required": ["draft_text"],
            },
        },
        handler=_agency_finalize,
        description="Construct one evidence-bound Agency final response.",
        check_fn=lambda: True,
    )
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("post_api_request", _post_api_request)
    ctx.register_hook("subagent_start", _subagent_start)
    ctx.register_hook("subagent_stop", _subagent_stop)
    ctx.register_hook("pre_verify", _pre_verify)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_command(
        "agency",
        _agency_command,
        description="Agency Runtime read-only status; persistent on/off commands are denied",
    )
'''


def render_hermes_plugin(
    timeout_seconds: int,
    cfg: AgencyConfig,
    *,
    python_executable: str,
    bootstrap_path: str,
) -> str:
    """Render a stdlib-only bridge bound to the installed Agency interpreter."""

    python = repr(python_executable)
    bootstrap = repr(bootstrap_path)
    config_path = repr(str(Path(cfg.config_path))) if cfg.config_path else repr("")
    return (
        _HERMES_BRIDGE_PLUGIN.replace("__AGENCY_PYTHON__", python)
        .replace("__AGENCY_BOOTSTRAP__", bootstrap)
        .replace("__AGENCY_CONFIG__", config_path)
        .replace("__AGENCY_TIMEOUT__", repr(timeout_seconds))
    )
