"""Credential minimization, prompt validation, and evidence redaction."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

ERROR_PREVIEW_CHARS = 2_000
MAX_TASK_CHARS = 16 * 1024
MAX_SPECIALIST_CHARS = 256
TASK_REDACTION = "<task>"
SAFE_DELEGATION_ENVIRONMENT_NAMES = frozenset(
    {
        "ALL_PROXY",
        "COMSPEC",
        "CURL_CA_BUNDLE",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "NODE_EXTRA_CA_CERTS",
        "NO_PROXY",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "REQUESTS_CA_BUNDLE",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USER",
        "USERNAME",
        "USERPROFILE",
        "WINDIR",
    }
)
AUTH_HOME_BY_BACKEND = {
    "claude": ("CLAUDE_CONFIG_DIR", ".claude"),
    "codex": ("CODEX_HOME", ".codex"),
    "hermes": ("HERMES_HOME", ".hermes"),
    "openclaw": ("OPENCLAW_HOME", ".openclaw"),
}


def delegation_environment(
    backend_name: str,
    extra_env: Mapping[str, str],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the least-privilege environment required by one host CLI."""
    source = os.environ if environ is None else environ
    safe = {
        key: value
        for key, value in source.items()
        if key.upper() in SAFE_DELEGATION_ENVIRONMENT_NAMES and isinstance(value, str)
    }
    auth_home = AUTH_HOME_BY_BACKEND.get(backend_name.strip().lower())
    if auth_home is not None:
        variable, default_name = auth_home
        user_home = source.get("USERPROFILE") or source.get("HOME") or str(Path.home())
        safe[variable] = source.get(variable, str(Path(user_home) / default_name))
    safe["NO_COLOR"] = "1"
    safe.update(extra_env)
    return safe


def sensitive_variants(values: Iterable[str]) -> tuple[str, ...]:
    """Return raw and JSON-escaped spellings ordered longest first."""
    variants: set[str] = set()
    for value in values:
        if not value:
            continue
        variants.add(value)
        variants.add(json.dumps(value, ensure_ascii=True)[1:-1])
        variants.add(json.dumps(value, ensure_ascii=False)[1:-1])
    variants.discard("")
    return tuple(sorted(variants, key=len, reverse=True))


def redact_text(value: str, variants: Iterable[str]) -> str:
    """Replace every sensitive spelling in a text value."""
    redacted = value
    for variant in variants:
        redacted = redacted.replace(variant, TASK_REDACTION)
    return redacted


def redact_value(value: Any, variants: Iterable[str]) -> Any:
    """Recursively redact strings in JSON-compatible response structures."""
    if isinstance(value, str):
        return redact_text(value, variants)
    if isinstance(value, list):
        return [redact_value(item, variants) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item, variants) for item in value)
    if isinstance(value, dict):
        return {
            redact_value(key, variants): redact_value(item, variants) for key, item in value.items()
        }
    return value


def specialist_prompt(task: str, recommended_agent: str | None) -> str:
    """Add Agency expertise context without treating a roster slug as a host id."""
    if recommended_agent is None:
        return task
    if not isinstance(recommended_agent, str):
        raise TypeError("recommended_agent must be a string")
    specialist = recommended_agent.strip()
    if not specialist:
        return task
    if "\x00" in specialist:
        raise ValueError("recommended_agent must not contain NUL bytes")
    if any(ord(character) < 32 or ord(character) == 127 for character in specialist):
        raise ValueError("recommended_agent must not contain control characters")
    if len(specialist) > MAX_SPECIALIST_CHARS:
        raise ValueError("recommended_agent exceeds the delegation display-token limit")
    return f"Agency specialist perspective requested: {specialist}\n\nDelegated task:\n{task}"
