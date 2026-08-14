"""Bounded JSON subprocess bridge for the generated Hermes plugin.

Hermes may run under a different Python installation from Agency Runtime.  The
generated plugin therefore contains only standard-library code and invokes this
module with the absolute interpreter captured during installation.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, BinaryIO
from uuid import uuid4

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.config import load_config
from agency_runtime.core.configuration_persistence import resolve_config_path
from agency_runtime.core.header.finalize import response_hash
from agency_runtime.core.host_control import handle_host_control_command
from agency_runtime.core.store.sqlite import Store

MAX_INPUT_BYTES = 1_048_576
MAX_OUTPUT_BYTES = 131_072
MAX_DEPTH = 20
MAX_NODES = 8_192
MAX_TEXT_BYTES = 65_536
MAX_PREFLIGHT_CONTEXT_BYTES = 48_000

FINALIZATION_BLOCK_RESPONSE = (
    "Agency Runtime blocked an unverified draft because turn-scoped finalization "
    "did not accept it. Restore correlation and evidence, then start a new turn."
)


def _bounded_text(value: object, *, maximum_bytes: int = MAX_TEXT_BYTES) -> str:
    text = value if isinstance(value, str) else "" if value is None else str(value)
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= maximum_bytes:
        return text
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore")


def _header_snapshot_context(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    model: str,
) -> str:
    """Render exact first-pass header guidance from current-turn Store evidence."""

    if not session_id or not trace_id:
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
                adapter.store,
                model,
                trace_id,
            )
        )
    except (
        AttributeError,
        EvidenceCorrelationError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return ""
    return (
        "[AGENCY INITIAL HEADER SNAPSHOT v1]\n"
        "Use these exact seven lines for substantive progress until Agency evidence "
        "changes. Immediately before the natural final response, call `agency.finalize` "
        f"exactly once with session_id `{session_id}`, trace_id `{trace_id}`, and the "
        "response body as draft_text; emit its returned text byte-for-byte. That local "
        "tool constructs the first visible header from current Store evidence. Never "
        "guess changed values and never wait for a host correction.\n"
        f"{header}"
    )


def _append_header_snapshot(
    result: Any,
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    model: str,
) -> Any:
    """Append an exact snapshot without exceeding Hermes's context budget."""

    if not isinstance(result, Mapping):
        return result
    snapshot = _header_snapshot_context(
        adapter,
        session_id=session_id,
        trace_id=trace_id,
        model=model,
    )
    if not snapshot:
        return result
    current = result.get("context")
    base = current.rstrip() if isinstance(current, str) else ""
    combined = f"{base}\n\n{snapshot}" if base else snapshot
    if len(combined.encode("utf-8")) > MAX_PREFLIGHT_CONTEXT_BYTES:
        return result
    return {**dict(result), "context": combined}


def _native_child_outcome(value: object) -> str:
    normalized = _bounded_text(value, maximum_bytes=32).strip().lower()
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


def _read_payload(stream: BinaryIO | None = None) -> dict[str, Any]:
    source = stream if stream is not None else sys.stdin.buffer
    raw = source.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise BoundedJSONError("Hermes bridge input exceeds the byte limit")
    loaded = safe_load_bounded_json(
        raw,
        maximum_bytes=MAX_INPUT_BYTES,
        maximum_depth=MAX_DEPTH,
        maximum_nodes=MAX_NODES,
    )
    if not isinstance(loaded, dict):
        raise BoundedJSONError("Hermes bridge input must be an object")
    return loaded


def _config_path(arguments: Sequence[str]) -> Path | None:
    if not arguments:
        return None
    if len(arguments) != 2 or arguments[0] != "--config":
        raise ValueError("Hermes bridge accepts only --config <absolute-path>")
    value = Path(arguments[1]).expanduser()
    if not value.is_absolute():
        raise ValueError("Hermes bridge config path must be absolute")
    return resolve_config_path(value, use_environment=False)


def _adapter(config_path: Path | None) -> HermesAdapter:
    cfg = load_config(config_path, reload=True) if config_path is not None else load_config()
    bound_config = cfg.config_path or None
    store = Store(config_path=bound_config)
    return HermesAdapter(store)


def _attempt_number(value: object) -> int:
    try:
        normalized = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return 1
    return normalized if normalized >= 0 else 1


def _terminalize_policy_rejection(
    adapter: HermesAdapter,
    final_response: str,
    session_id: str,
    trace_id: str,
    model: str,
) -> bool:
    """Bind the safe replacement only to a fresh authoritative rejection."""

    try:
        effective_trace = adapter.resolve_turn_trace(session_id, trace_id)
        if not session_id or not effective_trace:
            return False
        decision = adapter.evaluate_completion_policy(
            final_response,
            session_id=session_id,
            model=model,
            trace_id=effective_trace,
        )
        revision = decision.get("evidence_revision")
        if (
            decision.get("action") != "continue"
            or isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision <= 0
        ):
            return False
        missing = decision.get("missing")
        normalized_missing = (
            [_bounded_text(item, maximum_bytes=128) for item in missing[:16]]
            if isinstance(missing, list)
            else ["completion_policy"]
        )
        replacement_hash = response_hash(FINALIZATION_BLOCK_RESPONSE)
        rejection_action = (
            "delegation_declined"
            if decision.get("delegation_strength") == "strongly_preferred"
            else "response_invalid"
        )
        committed = adapter.store.commit_terminal_finalization(
            session_id=session_id,
            trace_id=effective_trace,
            host="hermes",
            action=rejection_action,
            response_hash=replacement_hash,
            policy_response_hash=response_hash(final_response),
            status=rejection_action,
            expected_evidence_revision=revision,
            missing=normalized_missing,
        )
        return bool(
            isinstance(committed, Mapping)
            and committed.get("authoritative") is True
            and committed.get("outcome") in {"committed", "replay"}
            and committed.get("action") == rejection_action
            and committed.get("response_hash") == replacement_hash
            and committed.get("status") == rejection_action
        )
    except Exception:
        return False


def _pre_verify(adapter: HermesAdapter, payload: Mapping[str, Any]) -> dict[str, str] | None:
    final_response = _bounded_text(payload.get("final_response"))
    session_id = _bounded_text(payload.get("session_id"), maximum_bytes=512)
    trace_id = _bounded_text(payload.get("trace_id"), maximum_bytes=512)
    model = _bounded_text(payload.get("model"), maximum_bytes=512)
    attempt = _attempt_number(payload.get("attempt"))
    try:
        decision = adapter.pre_verify_handler(
            final_response=final_response,
            session_id=session_id,
            model=model,
            attempt=attempt,
            trace_id=trace_id,
        )
    except Exception:
        return None
    if not isinstance(decision, dict) or decision.get("action") != "continue":
        return None
    _terminalize_policy_rejection(
        adapter,
        final_response,
        session_id,
        trace_id,
        model,
    )
    return None


def _transform_output(adapter: HermesAdapter, payload: Mapping[str, Any]) -> str:
    response_text = _bounded_text(payload.get("response_text"))
    session_id = _bounded_text(payload.get("session_id"), maximum_bytes=512)
    trace_id = _bounded_text(payload.get("trace_id"), maximum_bytes=512)
    model = _bounded_text(payload.get("model"), maximum_bytes=512)
    try:
        effective_trace = adapter.resolve_turn_trace(session_id, trace_id)
        from agency_runtime.core.header.finalize import accepted_response_run

        replay = accepted_response_run(
            adapter.store,
            session_id,
            effective_trace,
            response_text,
        )
        if (
            isinstance(replay, Mapping)
            and replay.get("authoritative") is True
            and replay.get("action") == "accept"
            and replay.get("terminal_status") == "completed"
            and replay.get("status") == "completed"
        ):
            return response_text
        decision = adapter.evaluate_completion_policy(
            response_text,
            session_id=session_id,
            model=model,
            trace_id=effective_trace,
        )
        if decision.get("action") != "accept":
            _terminalize_policy_rejection(
                adapter,
                response_text,
                session_id,
                effective_trace,
                model,
            )
            return FINALIZATION_BLOCK_RESPONSE
        finalized = adapter.apply_finalization(
            response_text,
            session_id,
            model,
            trace_id=effective_trace,
        )
    except Exception as error:
        del error
        # Agency's own unavailability is not a finding about the response.  A
        # verifier that evaluated and rejected still withholds above; reaching
        # here means Agency could not verify or persist at all, so the host's
        # draft is returned unchanged rather than replaced with a block.
        return response_text
    if isinstance(finalized, str) and finalized.strip():
        return _bounded_text(finalized)
    return response_text


def _close_session(adapter: HermesAdapter, payload: Mapping[str, Any]) -> None:
    session_id = _bounded_text(payload.get("session_id"), maximum_bytes=512)
    trace_id = _bounded_text(payload.get("trace_id"), maximum_bytes=512)
    if not session_id or not trace_id:
        return
    status = (
        "interrupted"
        if payload.get("interrupted") is True
        else "session_ended"
        if payload.get("completed") is True
        else "abandoned"
    )
    adapter.store.close_turn_evidence(session_id, trace_id, status=status)


def _runtime_disabled_result(payload: Mapping[str, Any], action: str) -> Any:
    """Return one exact Hermes pass-through without config, Store, or evidence work."""

    if action == "transform_llm_output":
        return _bounded_text(payload.get("response_text"))
    if action in {
        "pre_llm_call",
        "post_tool_call",
        "post_api_request",
        "native_child_started",
        "native_child_ended",
        "pre_verify",
        "on_session_end",
    }:
        return None
    raise ValueError("unknown Hermes bridge action")


def _pre_llm_call(
    adapter: HermesAdapter,
    payload: Mapping[str, Any],
    *,
    session_id: str,
    trace_id: str,
) -> Any:
    """Classify only a verified external Hermes event at the adapter boundary."""

    resolved_trace_id = trace_id or str(uuid4())
    resolver = getattr(adapter.store, "resolve_pending_internal_retry", None)
    internal_retry = False
    if callable(resolver) and session_id:
        try:
            internal_retry = resolver(session_id, resolved_trace_id) == resolved_trace_id
        except Exception:
            internal_retry = False

    from agency_runtime.core.turn_origin import native_adapter_turn_origin

    origin_receipt = native_adapter_turn_origin(
        "internal_retry" if internal_retry else "external_user",
        host="hermes",
        event="pre_llm_call_retry" if internal_retry else "pre_llm_call",
        session_id=session_id,
        trace_id=resolved_trace_id,
    )
    if internal_retry:
        return None
    handler_kwargs: dict[str, Any] = {
        "session_id": session_id,
        "user_message": _bounded_text(payload.get("user_message")),
        "model": _bounded_text(payload.get("model"), maximum_bytes=512),
        "trace_id": resolved_trace_id,
        "origin_receipt": origin_receipt,
    }
    parent_session_id = _bounded_text(payload.get("parent_session_id"), maximum_bytes=512)
    parent_trace_id = _bounded_text(payload.get("parent_trace_id"), maximum_bytes=512)
    native_worker_id = _bounded_text(payload.get("native_worker_id"), maximum_bytes=256)
    native_run_id = _bounded_text(payload.get("native_run_id"), maximum_bytes=256)
    if parent_session_id and parent_trace_id:
        handler_kwargs.update(
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            native_worker_id=native_worker_id,
            native_run_id=native_run_id,
        )
    result = adapter.pre_llm_call_handler(**handler_kwargs)
    return _append_header_snapshot(
        result,
        adapter,
        session_id=session_id,
        trace_id=resolved_trace_id,
        model=str(handler_kwargs["model"]),
    )


def handle(
    payload: Mapping[str, Any],
    *,
    config_path: Path | None = None,
    adapter: HermesAdapter | None = None,
) -> Any:
    """Dispatch one bounded Hermes hook operation."""

    action = _bounded_text(payload.get("action"), maximum_bytes=64)
    from agency_runtime.core.runtime_control import master_enabled

    if action != "control" and not master_enabled():
        return _runtime_disabled_result(payload, action)
    adapter = adapter if adapter is not None else _adapter(config_path)
    session_id = _bounded_text(payload.get("session_id"), maximum_bytes=512)
    trace_id = _bounded_text(payload.get("trace_id"), maximum_bytes=512)
    if action == "pre_llm_call":
        return _pre_llm_call(
            adapter,
            payload,
            session_id=session_id,
            trace_id=trace_id,
        )
    if action == "post_tool_call":
        args = payload.get("args")
        adapter.post_tool_call_handler(
            tool_name=_bounded_text(payload.get("tool_name"), maximum_bytes=512),
            args=args if isinstance(args, dict) else {},
            result=payload.get("result"),
            session_id=session_id,
            trace_id=trace_id,
        )
        return None
    if action == "post_api_request":
        forwarded = payload.get("payload")
        values = dict(forwarded) if isinstance(forwarded, Mapping) else {}
        values["session_id"] = session_id
        values["trace_id"] = trace_id
        adapter.post_api_request_handler(**values)
        return None
    if action == "native_child_started":
        worker_id = _bounded_text(payload.get("worker_id"), maximum_bytes=256)
        native_run_id = _bounded_text(payload.get("native_run_id"), maximum_bytes=256)
        goal = _bounded_text(payload.get("goal"))
        if not session_id or not trace_id or not worker_id or not native_run_id or not goal:
            return None
        adapter.post_tool_call_handler(
            tool_name="delegate_task",
            args={
                "goal": goal,
                "work_unit_id": _bounded_text(
                    payload.get("work_unit_id"),
                    maximum_bytes=160,
                ),
            },
            result={
                "status": "accepted",
                "agent_id": worker_id,
                "native_run_id": native_run_id,
            },
            session_id=session_id,
            trace_id=trace_id,
        )
        adapter.store.record_native_child_started(
            host="hermes",
            backend="delegate_task",
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=_bounded_text(
                payload.get("work_unit_id"),
                maximum_bytes=160,
            ),
            worker_id=worker_id,
            native_run_id=native_run_id,
        )
        return None
    if action == "native_child_ended":
        worker_id = _bounded_text(payload.get("worker_id"), maximum_bytes=256)
        native_run_id = _bounded_text(payload.get("native_run_id"), maximum_bytes=256)
        if not session_id or not trace_id or not worker_id or not native_run_id:
            return None
        adapter.store.record_native_child_ended(
            host="hermes",
            backend="delegate_task",
            session_id=session_id,
            trace_id=trace_id,
            worker_id=worker_id,
            native_run_id=native_run_id,
            outcome=_native_child_outcome(payload.get("outcome")),
            error=_bounded_text(payload.get("error"), maximum_bytes=4096),
        )
        return None
    if action == "pre_verify":
        return _pre_verify(adapter, payload)
    if action == "transform_llm_output":
        return _transform_output(adapter, payload)
    if action == "on_session_end":
        _close_session(adapter, payload)
        return None
    if action == "control":
        result = handle_host_control_command(
            "hermes",
            _bounded_text(payload.get("raw_args"), maximum_bytes=4096),
            store=adapter.store,
            source="hermes-command",
        )
        return _bounded_text(result.get("message"), maximum_bytes=4096)
    raise ValueError("unknown Hermes bridge action")


def _encode_result(result: Any) -> bytes:
    encoded = json.dumps(
        {"ok": True, "result": result},
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError("Hermes bridge output exceeds the byte limit")
    return encoded


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        payload = _read_payload()
        action = _bounded_text(payload.get("action"), maximum_bytes=64)
        from agency_runtime.core.runtime_control import master_enabled

        if action != "control" and not master_enabled():
            result = _runtime_disabled_result(payload, action)
        else:
            config_path = _config_path(arguments)
            result = handle(payload, config_path=config_path)
        encoded = _encode_result(result)
    except Exception as exc:  # Defensive host boundary.
        print(f"agency hermes bridge: {type(exc).__name__}", file=sys.stderr)
        encoded = json.dumps(
            {"ok": False, "error": "Agency Runtime Hermes bridge unavailable"},
            separators=(",", ":"),
        ).encode("ascii")
        sys.stdout.buffer.write(encoded + b"\n")
        return 2
    sys.stdout.buffer.write(encoded + b"\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through subprocess tests
    raise SystemExit(main())


__all__ = [
    "FINALIZATION_BLOCK_RESPONSE",
    "MAX_INPUT_BYTES",
    "MAX_OUTPUT_BYTES",
    "handle",
    "main",
]
