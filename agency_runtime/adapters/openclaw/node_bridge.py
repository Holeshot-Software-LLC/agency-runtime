"""JSON bridge used by the OpenClaw JavaScript plugin.

OpenClaw plugins run in Node, while Agency Runtime routing lives in Python. Keep
this bridge tiny: stdin JSON in, stdout JSON out, shared SQLite store for state.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter


MAX_INPUT_BYTES = 1_048_576


def _read_payload() -> dict[str, Any]:
    try:
        stream = getattr(sys.stdin, "buffer", sys.stdin)
        raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return {"action": "", "error": "hook payload exceeds 1 MiB"}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = json.loads(raw)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return {"action": "", "error": f"invalid json: {exc}"}
    return payload if isinstance(payload, dict) else {"action": "", "error": "payload must be an object"}


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
    adapter = OpenClawAdapter()
    action = str(payload.get("action") or "")
    session_id = str(payload.get("sessionId") or "")
    model = str(payload.get("model") or "")

    if action == "preflight":
        user_message = str(payload.get("userMessage") or "")
        if _is_revision_instruction(user_message):
            return {}
        return adapter.pre_llm_call_handler(
            session_id=session_id,
            user_message=user_message,
            model=model,
        ) or {}

    if action == "pre_verify":
        return adapter.pre_verify_handler(
            final_response=str(payload.get("finalResponse") or ""),
            session_id=session_id,
            model=model,
            attempt=int(payload.get("attempt") or 0),
        ) or {}

    if action == "post_tool_call":
        tool_input = payload.get("toolInput")
        adapter.post_tool_call_handler(
            tool_name=str(payload.get("toolName") or ""),
            args=tool_input if isinstance(tool_input, dict) else {},
            result=payload.get("toolResult"),
            error=payload.get("error"),
            session_id=session_id,
        )
        return {}

    return {"error": f"unknown action: {action}"}


def main() -> int:
    payload = _read_payload()
    result = handle(payload) if not payload.get("error") else {"error": payload["error"]}
    json.dump(result, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0 if "error" not in result else 2


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(main())
