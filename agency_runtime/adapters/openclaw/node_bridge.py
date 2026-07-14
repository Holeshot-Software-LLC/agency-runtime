"""JSON bridge used by the OpenClaw JavaScript plugin.

OpenClaw plugins run in Node, while Agency Runtime routing lives in Python. Keep
this bridge tiny: stdin JSON in, stdout JSON out, shared SQLite store for state.
"""

from __future__ import annotations

import json
import sys
from contextlib import suppress
from typing import Any

from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.bounded_json import safe_load_bounded_json

MAX_INPUT_BYTES = 1_048_576
MAX_ID_CHARS = 1_024
MAX_MODEL_CHARS = 512
MAX_TOOL_NAME_CHARS = 512


def _bounded_string(
    payload: dict[str, Any],
    key: str,
    *,
    limit: int,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or "\x00" in value:
        return ""
    return value[:limit]


def _attempt_number(payload: dict[str, Any]) -> int:
    value = payload.get("attempt", 0)
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return parsed if 0 <= parsed <= 100 else 0


def _read_payload() -> dict[str, Any]:
    try:
        stream = getattr(sys.stdin, "buffer", sys.stdin)
        raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return {"action": "", "error": "hook payload exceeds 1 MiB"}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = safe_load_bounded_json(raw)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return {"action": "", "error": f"invalid json: {exc}"}
    return (
        payload
        if isinstance(payload, dict)
        else {"action": "", "error": "payload must be an object"}
    )


def _is_revision_instruction(message: str) -> bool:
    """OpenClaw revision prompts are host instructions, not new user asks."""
    text = message.strip().lower()
    revision_markers = (
        "agency header invalid:",
        "your response is missing or has malformed agency header fields:",
        "delegation opportunity was detected",
    )
    return any(marker in text for marker in revision_markers)


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"error": "payload must be an object"}
    adapter = OpenClawAdapter()
    action = _bounded_string(payload, "action", limit=32).strip()
    session_id = _bounded_string(payload, "sessionId", limit=MAX_ID_CHARS)
    trace_id = _bounded_string(payload, "traceId", limit=MAX_ID_CHARS)
    model = _bounded_string(payload, "model", limit=MAX_MODEL_CHARS)

    if action == "control":
        from agency_runtime.core.host_control import handle_host_control_command

        return handle_host_control_command(
            "openclaw",
            _bounded_string(payload, "command", limit=64) or "status",
            store=adapter.store,
            source="openclaw-command",
        )

    if action == "preflight":
        user_message = _bounded_string(
            payload,
            "userMessage",
            limit=MAX_INPUT_BYTES,
        )
        if not user_message.strip():
            return {}
        if _is_revision_instruction(user_message):
            return {}
        return (
            adapter.pre_llm_call_handler(
                session_id=session_id,
                user_message=user_message,
                model=model,
                trace_id=trace_id,
            )
            or {}
        )

    if action == "pre_verify":
        final_response = _bounded_string(
            payload,
            "finalResponse",
            limit=MAX_INPUT_BYTES,
        )
        if not final_response.strip():
            return {}
        decision = (
            adapter.pre_verify_handler(
                final_response=final_response,
                session_id=session_id,
                model=model,
                attempt=_attempt_number(payload),
            )
            or {}
        )
        if trace_id and adapter.runtime_enabled():
            with suppress(Exception):
                adapter.store.record_finalization(
                    trace_id=trace_id,
                    host="openclaw",
                    action="continue" if decision.get("action") == "continue" else "accept",
                    missing=[],
                )
        return decision

    if action == "post_tool_call":
        tool_input = payload.get("toolInput")
        adapter.post_tool_call_handler(
            tool_name=_bounded_string(
                payload,
                "toolName",
                limit=MAX_TOOL_NAME_CHARS,
            ),
            args=tool_input if isinstance(tool_input, dict) else {},
            result=payload.get("toolResult"),
            error=payload.get("error"),
            session_id=session_id,
            trace_id=trace_id,
        )
        return {}

    return {"error": f"unknown action: {action}"}


def main() -> int:
    payload = _read_payload()
    try:
        result = handle(payload) if not payload.get("error") else {"error": payload["error"]}
    except Exception as exc:  # Defensive fail-open host boundary.
        print(
            f"agency openclaw bridge: {type(exc).__name__}; host operation continues",
            file=sys.stderr,
        )
        result = {}
    try:
        encoded = json.dumps(result, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError):
        encoded = "{}"
        result = {}
    sys.stdout.write(encoded)
    sys.stdout.write("\n")
    return 0 if "error" not in result else 2


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(main())
