"""Defensive secret and PII removal for opt-in runtime content capture.

This lives in core, not under an adapter, because every capture path needs it.
It previously lived under ``adapters/litellm/`` and only that adapter applied it,
so ``observability.capture_content`` scrubbed LiteLLM traffic while every native
host-hook turn wrote the raw user message to ``runs.user_message``.

Per ``docs/THREAT_MODEL.md``, redaction is defensive and cannot recognize every
secret or personal identifier. It reduces exposure; it is not a licence to
capture data that must never be stored.
"""

from __future__ import annotations

import re

MAX_CAPTURE_CHARS = 2_000
MAX_REDACTION_SCAN_CHARS = 8_192

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
