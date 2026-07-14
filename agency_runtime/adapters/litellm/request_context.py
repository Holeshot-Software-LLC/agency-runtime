"""Request-shape and content-safety helpers for LiteLLM callbacks."""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from .evidence import clean

AGENCY_PREFLIGHT_MARKER = "[AGENCY PREFLIGHT]"
MAX_CAPTURE_CHARS = 2_000
MAX_REDACTION_SCAN_CHARS = 8_192
MAX_ROUTING_INPUT_CHARS = 32_000

_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}")
_QUOTED_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<prefix>[\"']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"token|password|passwd|secret)[\"']?\s*[:=]\s*)"
    r"(?P<quote>[\"'])(?P<value>[^\r\n]*?)(?P=quote)"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<key>[\"']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|"
    r"token|password|passwd|secret)[\"']?)\s*(?P<sep>[:=])\s*"
    r"(?P<quote>[\"']?)(?P<value>[^\s,;&\"']{4,})(?P=quote)"
)
_PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?"
    r"(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
    re.DOTALL,
)
_URL_USERINFO_RE = re.compile(r"(?i)(https?://)[^/\s:@]+:[^@/\s]+@")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_KEY_RE = re.compile(
    r"\b(?:"
    r"(?:sk|rk|pk)-(?:proj-)?[A-Za-z0-9_-]{8,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_-]{30,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}"
    r")\b"
)
_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def _redact_secret_assignment(match: re.Match[str]) -> str:
    quote = match.group("quote")
    return f"{match.group('key')}{match.group('sep')}{quote}[REDACTED]{quote}"


def _redact_quoted_secret_assignment(match: re.Match[str]) -> str:
    quote = match.group("quote")
    return f"{match.group('prefix')}{quote}[REDACTED]{quote}"


def redact_content(value: str) -> str:
    """Return a tightly bounded excerpt with common secrets and PII removed."""

    text = value[:MAX_REDACTION_SCAN_CHARS]
    text = _PRIVATE_KEY_RE.sub("[REDACTED_PRIVATE_KEY]", text)
    text = _URL_USERINFO_RE.sub(r"\1[REDACTED]@", text)
    text = _BEARER_RE.sub(r"\1 [REDACTED]", text)
    text = _QUOTED_SECRET_ASSIGNMENT_RE.sub(
        _redact_quoted_secret_assignment,
        text,
    )
    text = _SECRET_ASSIGNMENT_RE.sub(_redact_secret_assignment, text)
    text = _JWT_RE.sub("[REDACTED_JWT]", text)
    text = _KEY_RE.sub("[REDACTED_KEY]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _CARD_RE.sub("[REDACTED_NUMBER]", text)
    return text[:MAX_CAPTURE_CHARS]


def content_text(content: Any) -> str:
    """Extract bounded text from OpenAI/Anthropic string or block content."""

    if isinstance(content, str):
        return content[:MAX_ROUTING_INPUT_CHARS]
    if not isinstance(content, Sequence) or isinstance(content, (bytes, bytearray)):
        return ""

    parts: list[str] = []
    length = 0
    for block in content:
        if isinstance(block, str):
            part = block
        elif isinstance(block, Mapping) and clean(block.get("type")).casefold() in {
            "text",
            "input_text",
        }:
            part = clean(block.get("text") or block.get("content"))
        else:
            continue
        remaining = MAX_ROUTING_INPUT_CHARS - length
        if remaining <= 0:
            break
        if parts:
            remaining -= 1
        if remaining <= 0:
            break
        part = part[:remaining]
        if part:
            parts.append(part)
            length += len(part) + (1 if len(parts) > 1 else 0)
    return "\n".join(parts)


def user_message(request_input: Any) -> str:
    """Extract the final user/prompt text from supported LiteLLM request forms."""

    if isinstance(request_input, str):
        return request_input[:MAX_ROUTING_INPUT_CHARS]
    if not isinstance(request_input, Sequence) or isinstance(request_input, (bytes, bytearray)):
        return ""
    for item in reversed(request_input):
        if isinstance(item, str):
            return item[:MAX_ROUTING_INPUT_CHARS]
        if not isinstance(item, Mapping):
            continue
        if clean(item.get("role")).casefold() == "user":
            return content_text(item.get("content"))
    return ""


def _has_agency_system_context(messages: Sequence[Any]) -> bool:
    """Only trusted system messages may suppress another context injection."""

    return any(
        isinstance(message, Mapping)
        and clean(message.get("role")).casefold() == "system"
        and AGENCY_PREFLIGHT_MARKER in content_text(message.get("content"))
        for message in messages
    )


def inject_message_context(messages: Any, context: str) -> list[Any]:
    """Add one system context while preserving caller-owned message objects."""

    copied = (
        list(messages)
        if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes, bytearray))
        else []
    )
    if not context or _has_agency_system_context(copied):
        return copied
    position = 0
    while position < len(copied):
        message = copied[position]
        if not isinstance(message, Mapping) or clean(message.get("role")).casefold() != "system":
            break
        position += 1
    copied.insert(position, {"role": "system", "content": context})
    return copied


def proxy_request_input(payload: Mapping[str, Any], call_type: str) -> Any:
    """Return the user-bearing field for a LiteLLM Proxy call type."""

    normalized = clean(call_type).casefold()
    if normalized == "responses":
        return payload.get("input")
    messages = payload.get("messages")
    if messages is not None:
        return messages
    if normalized == "completion":
        return payload.get("prompt")
    return None


def _append_string_context(
    payload: MutableMapping[str, Any],
    field: str,
    context: str,
) -> None:
    existing = payload.get(field)
    if existing is None or existing == "":
        payload[field] = context
    elif isinstance(existing, str) and AGENCY_PREFLIGHT_MARKER not in existing:
        payload[field] = f"{existing}\n\n{context}"


def _inject_completion_context(
    payload: MutableMapping[str, Any],
    context: str,
) -> None:
    """Prepend context to legacy text prompts without inventing chat fields."""

    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        if not prompt.startswith(context):
            payload["prompt"] = f"{context}\n\n{prompt}"
        return
    if isinstance(prompt, Sequence) and not isinstance(prompt, (str, bytes, bytearray)):
        payload["prompt"] = [
            item
            if not isinstance(item, str) or item.startswith(context)
            else f"{context}\n\n{item}"
            for item in prompt
        ]


def inject_proxy_context(
    payload: MutableMapping[str, Any],
    messages: Any,
    context: str,
    call_type: str,
) -> None:
    """Inject context without violating provider-specific request schemas."""

    normalized = clean(call_type).casefold()
    if normalized == "responses":
        # OpenAI Responses accepts top-level ``instructions`` while ``input``
        # may be either a string or typed items.  Never synthesize ``messages``.
        _append_string_context(payload, "instructions", context)
        return
    if normalized == "completion" and "messages" not in payload:
        _inject_completion_context(payload, context)
        return
    if normalized != "anthropic_messages":
        payload["messages"] = inject_message_context(messages, context)
        return

    system = payload.get("system")
    if isinstance(system, str) or system is None:
        _append_string_context(payload, "system", context)
        return
    if isinstance(system, Sequence) and not isinstance(system, (str, bytes, bytearray)):
        blocks = list(system)
        if not any(
            isinstance(block, Mapping) and AGENCY_PREFLIGHT_MARKER in content_text([block])
            for block in blocks
        ):
            blocks.append({"type": "text", "text": context})
        payload["system"] = blocks


__all__ = [
    "AGENCY_PREFLIGHT_MARKER",
    "MAX_ROUTING_INPUT_CHARS",
    "content_text",
    "inject_message_context",
    "inject_proxy_context",
    "proxy_request_input",
    "redact_content",
    "user_message",
]
