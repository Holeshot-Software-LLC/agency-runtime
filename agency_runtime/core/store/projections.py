"""Privacy-preserving projections for values persisted by the runtime store."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit

from agency_runtime.core.bounded_json import safe_load_bounded_json

RUN_CONTENT_LIMIT = 2_000
DELEGATION_DETAIL_LIMIT = 2_000
DIAGNOSTIC_REASON_LIMIT = 160
API_BASE_LIMIT = 512
SNAPSHOT_MANIFEST_LIMIT = 32 * 1024 * 1024

_SAFE_RUN_METADATA_FIELDS = frozenset(
    {
        "callback",
        "content_capture",
        "event_type",
        "reason_code",
        "request_kind",
        "source",
        "transport",
    }
)
_SAFE_METADATA_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_REASON_CODE = re.compile(r"[a-z][a-z0-9_.-]{0,95}\Z")
_URL_IN_TEXT = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s<>\"']+")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|authorization|password|passwd|secret|token)"
    r"\b\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")

_SAFE_DIAGNOSTIC_MESSAGES = {
    "agency_agents_delegate unavailable",
    "backend command failed",
    "delegate depth limit reached",
    "delegate_task requires a parent agent context.",
    "delegate_task unavailable",
    "delegation not requested",
    "host delegate backend is unavailable",
    "no backend available",
    "no command configured",
    "worker crashed",
}


def capture_content_enabled() -> bool:
    """Read the explicit content-capture opt-in, failing closed."""

    try:
        from agency_runtime.core.config import load_config

        return bool(load_config().observability.capture_content)
    except Exception:
        return False


def bounded_text(value: object, limit: int) -> str:
    """Return bounded text without NULs that can confuse operator surfaces."""

    return str(value or "").replace("\x00", "")[:limit]


def sanitize_api_base(value: object) -> str:
    """Keep an endpoint useful for diagnostics without credentials or queries."""

    raw = bounded_text(value, API_BASE_LIMIT * 2).strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        if parts.scheme and parts.netloc:
            hostname = parts.hostname or ""
            if ":" in hostname and not hostname.startswith("["):
                hostname = f"[{hostname}]"
            try:
                port = parts.port
            except ValueError:
                port = None
            netloc = hostname + (f":{port}" if port is not None else "")
            return bounded_text(
                urlunsplit(SplitResult(parts.scheme, netloc, parts.path, "", "")),
                API_BASE_LIMIT,
            )
    except (TypeError, ValueError):
        pass

    endpoint = raw.split("#", 1)[0].split("?", 1)[0]
    if "@" in endpoint:
        prefix, endpoint = endpoint.rsplit("@", 1)
        if "://" in prefix:
            endpoint = prefix.split("://", 1)[0] + "://" + endpoint
    endpoint = _BEARER_TOKEN.sub("Bearer [REDACTED]", endpoint)
    endpoint = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", endpoint)
    return bounded_text(endpoint, API_BASE_LIMIT)


def redact_sensitive_text(value: object, limit: int) -> str:
    """Bound opt-in diagnostic content and redact common credential forms."""

    text = bounded_text(value, limit * 2)
    text = _BEARER_TOKEN.sub("Bearer [REDACTED]", text)
    text = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", text)

    def sanitize_url(match: re.Match[str]) -> str:
        token = match.group(0)
        suffix = ""
        while token and token[-1] in ".,;)]}":
            suffix = token[-1] + suffix
            token = token[:-1]
        return sanitize_api_base(token) + suffix

    return _URL_IN_TEXT.sub(sanitize_url, text)[:limit]


def project_delegation_detail(
    value: object,
    *,
    field: str,
    capture_content: bool,
) -> str:
    """Project a delegation detail into bounded content or a safe reason code."""

    raw = str(value or "").strip()
    if not raw:
        return ""
    if capture_content:
        return redact_sensitive_text(raw, DELEGATION_DETAIL_LIMIT)

    normalized = " ".join(raw.split()).lower()
    if normalized in _SAFE_DIAGNOSTIC_MESSAGES:
        return normalized
    if _REASON_CODE.fullmatch(normalized):
        return normalized

    timeout = re.fullmatch(r"backend command timed out after ([0-9]+(?:\.[0-9]+)?)s", normalized)
    if timeout:
        return f"backend command timed out after {timeout.group(1)}s"[:DIAGNOSTIC_REASON_LIMIT]
    exit_code = re.search(r"\bexited with (-?[0-9]+)\b", normalized)
    if exit_code:
        return f"backend exited with {exit_code.group(1)}"[:DIAGNOSTIC_REASON_LIMIT]
    dependency = re.fullmatch(
        r"dependency did not complete successfully:\s*([a-z0-9_.-]{1,64})",
        normalized,
    )
    if dependency:
        return f"dependency did not complete successfully: {dependency.group(1)}"

    classifications = (
        (("timed out", "timeout"), "backend_timeout"),
        (("permission", "denied"), "permission_denied"),
        (("not found", "disappeared", "executable"), "executable_unavailable"),
        (("unavailable",), "backend_unavailable"),
        (("not configured", "no command"), "backend_not_configured"),
        (("dependency", "predecessor"), "dependency_failed"),
        (("merge",), "merge_failed"),
        (("confidence", "threshold"), "below_confidence_threshold"),
        (("policy",), "policy_denied"),
        (("cancel",), "cancelled"),
        (("invalid",), "invalid_request"),
    )
    for needles, reason_code in classifications:
        if any(needle in normalized for needle in needles):
            return reason_code
    return "unspecified_skip" if field == "skip_reason" else "execution_failed"


def project_run_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Return the fixed metadata projection used even when content is enabled."""

    if not isinstance(metadata, dict):
        return None
    projected: dict[str, bool | int | float | str] = {}
    for key in sorted(_SAFE_RUN_METADATA_FIELDS):
        if key not in metadata:
            continue
        value = metadata[key]
        if (
            isinstance(value, bool)
            or (isinstance(value, (int, float)) and not isinstance(value, bool))
            or (isinstance(value, str) and _SAFE_METADATA_LABEL.fullmatch(value))
        ):
            projected[key] = value
    return json.dumps(projected, sort_keys=True, separators=(",", ":")) if projected else None


def project_snapshot_summary(value: object) -> dict[str, bool | int]:
    """Project only dashboard-safe roster snapshot metadata.

    Current roster manifests keep change sets under ``diff``; early embedders
    wrote them at the top level. Both shapes are accepted so a schema upgrade
    can materialize stable counts once without exposing candidate prompts on
    every dashboard read.
    """

    if isinstance(value, Mapping):
        manifest: Mapping[str, Any] = value
    else:
        try:
            parsed = safe_load_bounded_json(
                value or "{}",
                maximum_bytes=SNAPSHOT_MANIFEST_LIMIT,
                maximum_depth=64,
                maximum_nodes=50_000,
            )
        except (TypeError, ValueError):
            parsed = {}
        manifest = parsed if isinstance(parsed, Mapping) else {}

    raw_diff = manifest.get("diff")
    diff = raw_diff if isinstance(raw_diff, Mapping) else {}

    def change_count(field: str) -> int:
        changes = diff.get(field, manifest.get(field, []))
        return len(changes) if isinstance(changes, (list, Mapping)) else 0

    return {
        "approved": bool(manifest.get("approved")),
        "added": change_count("added"),
        "changed": change_count("changed"),
        "removed": change_count("removed"),
    }
