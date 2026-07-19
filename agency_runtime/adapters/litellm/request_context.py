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


_AGENCY_LOADED_CAPSULE_MARKER = (
    "[AGENCY LOADED] Complete current-turn specialist instruction capsule:"
)
_AGENCY_CONTEXT_PREFIXES = (
    "[AGENCY PREFLIGHT] Default specialist routing suggestion ",
    "[AGENCY PREFLIGHT] No high-confidence specialist match found ",
    "[AGENCY PREFLIGHT] Specialist routing suggestion ",
)


def _agency_header_instruction() -> str:
    """Load the canonical rendered tail lazily to keep this adapter lightweight."""

    from agency_runtime.core.selector.pipeline import HEADER_INSTRUCTION

    return HEADER_INSTRUCTION


def _owned_agency_context(value: str) -> bool:
    """Return whether ``value`` is an exact runtime-rendered context suffix."""

    if not value.startswith(_AGENCY_CONTEXT_PREFIXES):
        return False
    header = _agency_header_instruction()
    header_at = value.find(header)
    if header_at < 0:
        return False
    tail = value[header_at + len(header) :]
    return not tail or tail.startswith(f"\n\n{_AGENCY_LOADED_CAPSULE_MARKER}")


def _copy_content(content: Any) -> Any:
    """Copy mutable message content without attempting to clone opaque values."""

    if not isinstance(content, Sequence) or isinstance(content, (str, bytes, bytearray)):
        return content
    return [dict(block) if isinstance(block, Mapping) else block for block in content]


def _strip_agency_suffix(value: str) -> tuple[str, bool]:
    """Remove only an exact legacy Agency-owned suffix.

    A bare marker can be ordinary caller text.  Agency's rendered context has a
    constrained first line and the complete six-line-header trailer, so both
    are required before this boundary treats a suffix as runtime-owned.
    """

    marker = value.find(AGENCY_PREFLIGHT_MARKER)
    while marker >= 0:
        candidate = value[marker:]
        if _owned_agency_context(candidate):
            preserved = value[:marker]
            if preserved.endswith("\n\n"):
                preserved = preserved[:-2]
            return preserved, True
        marker = value.find(AGENCY_PREFLIGHT_MARKER, marker + len(AGENCY_PREFLIGHT_MARKER))
    return value, False


def _strip_agency_blocks(content: Sequence[Any]) -> tuple[list[Any], bool]:
    """Remove Agency text blocks from a copied OpenAI/Anthropic content list."""

    cleaned: list[Any] = []
    found = False
    for original in content:
        if isinstance(original, str):
            value, removed = _strip_agency_suffix(original)
            found = found or removed
            if value:
                cleaned.append(value)
            continue
        if not isinstance(original, Mapping):
            cleaned.append(original)
            continue
        block = dict(original)
        block_type = clean(block.get("type")).casefold()
        if block_type not in {"text", "input_text"}:
            cleaned.append(block)
            continue
        field = "text" if "text" in block else "content"
        text = block.get(field)
        if not isinstance(text, str):
            cleaned.append(block)
            continue
        value, removed = _strip_agency_suffix(text)
        found = found or removed
        if value:
            block[field] = value
            cleaned.append(block)
    return cleaned, found


def _strip_agency_system_content(content: Any) -> tuple[Any, bool]:
    if isinstance(content, str):
        return _strip_agency_suffix(content)
    if isinstance(content, Sequence) and not isinstance(content, (str, bytes, bytearray)):
        return _strip_agency_blocks(content)
    return content, False


def inject_message_context(messages: Any, context: str) -> list[Any]:
    """Replace stale system context in an outbound, caller-independent copy."""

    source = (
        messages
        if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes, bytearray))
        else ()
    )
    copied: list[Any] = []
    for original in source:
        if not isinstance(original, Mapping):
            copied.append(original)
            continue
        message = dict(original)
        if "content" in message:
            message["content"] = _copy_content(message["content"])
        if clean(message.get("role")).casefold() == "system":
            cleaned, removed = _strip_agency_system_content(message.get("content"))
            if removed:
                if cleaned is None or cleaned == "" or cleaned == []:
                    continue
                message["content"] = cleaned
        copied.append(message)
    if not context:
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
        if context:
            payload[field] = context
        return
    if not isinstance(existing, str):
        return
    preserved, removed = _strip_agency_suffix(existing)
    if not removed:
        preserved = existing
    if context:
        payload[field] = f"{preserved}\n\n{context}" if preserved else context
    elif removed:
        if preserved:
            payload[field] = preserved
        else:
            payload.pop(field, None)


def _strip_completion_context(prompt: str) -> str:
    """Remove an Agency prefix previously injected into a legacy prompt."""

    if not prompt.startswith(_AGENCY_CONTEXT_PREFIXES):
        return prompt
    header = _agency_header_instruction()
    header_at = prompt.find(header)
    if header_at < 0:
        return prompt
    separator = prompt.find("\n\n", header_at + len(header))
    if separator < 0:
        return ""
    remainder = prompt[separator + 2 :]
    if remainder.startswith(_AGENCY_LOADED_CAPSULE_MARKER):
        capsule_separator = remainder.find("\n\n", len(_AGENCY_LOADED_CAPSULE_MARKER))
        return remainder[capsule_separator + 2 :] if capsule_separator >= 0 else ""
    return remainder


def _with_completion_context(prompt: str, context: str) -> str:
    preserved = _strip_completion_context(prompt)
    if not context:
        return preserved
    return f"{context}\n\n{preserved}" if preserved else context


def _inject_completion_context(
    payload: MutableMapping[str, Any],
    context: str,
) -> None:
    """Prepend context to legacy text prompts without inventing chat fields."""

    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        payload["prompt"] = _with_completion_context(prompt, context)
        return
    if isinstance(prompt, Sequence) and not isinstance(prompt, (str, bytes, bytearray)):
        payload["prompt"] = [
            _with_completion_context(item, context) if isinstance(item, str) else item
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
        blocks, _removed = _strip_agency_blocks(system)
        if context:
            blocks.append({"type": "text", "text": context})
        if blocks:
            payload["system"] = blocks
        else:
            payload.pop("system", None)


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
