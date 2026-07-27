"""Bounded transient envelopes for hook-owned native-child prompt delivery.

The envelope travels only in a host-native child launch input.  Durable evidence
stores immutable prompt identities and one-use receipts, never prompt bodies or
bearer tokens.  Post-tool hooks re-parse the exact rewritten input and consume
the grant only after the native host proves that it executed the launch.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any, Final

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.roster.revisions import content_digest_identity, content_identity_matches
from agency_runtime.core.store.version_identity import normalize_version_identity

NATIVE_CHILD_PROMPT_DELIVERY_VERSION: Final[int] = 1
MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES: Final[int] = 2_048
MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS: Final[int] = 256

_SECTION = (
    "\n\n[AGENCY EXACT SPECIALIST ACTIVATION v1]\n"
    "The host hook assigned the exact audited specialist below to this child only. "
    "Treat it as turn-scoped specialist instructions; do not copy it into the parent, "
    "another worker, status text, or the final response.\n"
)
_MARKER_PREFIX = "<!-- agency-native-child-delivery:v1:"
_MARKER_SUFFIX = " -->"
_MARKER_PATTERN = re.compile(
    re.escape(_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_FIELDS = frozenset(
    {
        "version",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "tool_use_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "activation_token",
    }
)


@dataclass(frozen=True, slots=True)
class NativeChildPromptDelivery:
    """One exact hook-delivered specialist and its original native assignment."""

    host: str
    parent_session_id: str
    parent_trace_id: str
    tool_use_id: str
    work_unit_id: str
    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str
    activation_token: str
    original_task: str
    prompt_body: str


def _encoded_metadata(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(payload) > MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES:
        raise ValueError("native-child delivery metadata exceeds its byte ceiling")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decoded_metadata(value: str) -> dict[str, Any] | None:
    try:
        padding = "=" * (-len(value) % 4)
        payload = base64.b64decode(value + padding, altchars=b"-_", validate=True)
        if not payload or len(payload) > MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES:
            return None
        result = safe_load_bounded_json(
            payload,
            maximum_bytes=MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES,
            maximum_depth=4,
            maximum_nodes=64,
        )
    except (TypeError, ValueError):
        return None
    if not isinstance(result, dict) or frozenset(result) != _FIELDS:
        return None
    return result


def _metadata(
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    activation_token: object,
) -> dict[str, Any]:
    normalized_host = str(host or "").strip().casefold()
    if normalized_host not in {"codex", "claude", "zcode"}:
        raise ValueError("native-child prompt delivery host is unsupported")
    session_id = validate_correlation_id(parent_session_id, field="parent_session_id")
    trace_id = validate_correlation_id(parent_trace_id, field="parent_trace_id")
    use_id = validate_correlation_id(tool_use_id, field="tool_use_id")
    unit_id = validate_correlation_id(work_unit_id, field="work_unit_id")
    slug = normalize_agent_slug(specialist_slug)
    version = str(specialist_version or "").strip()
    if not version or normalize_version_identity(version) != version:
        raise ValueError("specialist_version is invalid")
    content_hash = str(specialist_prompt_hash or "").strip().casefold()
    if content_digest_identity(content_hash) is None:
        raise ValueError("specialist_prompt_hash is invalid")
    token = str(activation_token or "").strip()
    if not token or len(token) > MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS:
        raise ValueError("activation_token is invalid")
    return {
        "version": NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
        "host": normalized_host,
        "parent_session_id": session_id,
        "parent_trace_id": trace_id,
        "tool_use_id": use_id,
        "work_unit_id": unit_id,
        "specialist_slug": slug,
        "specialist_version": version,
        "specialist_prompt_hash": content_hash,
        "activation_token": token,
    }


def render_native_child_prompt_delivery(
    original_task: object,
    prompt_body: object,
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    activation_token: object,
) -> str:
    """Append one exact prompt body and a self-verifying delivery marker."""

    if not isinstance(original_task, str) or not original_task:
        raise ValueError("native child task must be a non-empty string")
    if not isinstance(prompt_body, str) or not prompt_body:
        raise ValueError("specialist prompt body must be a non-empty string")
    metadata = _metadata(
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
        activation_token=activation_token,
    )
    if not content_identity_matches(prompt_body, metadata["specialist_prompt_hash"]):
        raise ValueError("specialist prompt body failed exact identity verification")
    marker = f"{_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{original_task}{_SECTION}{marker}\n{prompt_body}"


def parse_native_child_prompt_delivery(value: object) -> NativeChildPromptDelivery | None:
    """Recover the last valid exact envelope from a rewritten native child task."""

    if not isinstance(value, str) or not value:
        return None
    matches = list(_MARKER_PATTERN.finditer(value))
    for match in reversed(matches):
        metadata = _decoded_metadata(match.group(1))
        if metadata is None:
            continue
        try:
            normalized = _metadata(
                host=metadata.get("host"),
                parent_session_id=metadata.get("parent_session_id"),
                parent_trace_id=metadata.get("parent_trace_id"),
                tool_use_id=metadata.get("tool_use_id"),
                work_unit_id=metadata.get("work_unit_id"),
                specialist_slug=metadata.get("specialist_slug"),
                specialist_version=metadata.get("specialist_version"),
                specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
                activation_token=metadata.get("activation_token"),
            )
        except ValueError:
            continue
        if metadata != normalized:
            continue
        prompt_start = match.end()
        if value.startswith("\r\n", prompt_start):
            prompt_start += 2
        elif value.startswith("\n", prompt_start):
            prompt_start += 1
        else:
            continue
        prompt_body = value[prompt_start:]
        if not prompt_body or not content_identity_matches(
            prompt_body,
            normalized["specialist_prompt_hash"],
        ):
            continue
        section_start = value.rfind(_SECTION, 0, match.start())
        if section_start < 0 or section_start + len(_SECTION) != match.start():
            continue
        return NativeChildPromptDelivery(
            host=normalized["host"],
            parent_session_id=normalized["parent_session_id"],
            parent_trace_id=normalized["parent_trace_id"],
            tool_use_id=normalized["tool_use_id"],
            work_unit_id=normalized["work_unit_id"],
            specialist_slug=normalized["specialist_slug"],
            specialist_version=normalized["specialist_version"],
            specialist_prompt_hash=normalized["specialist_prompt_hash"],
            activation_token=normalized["activation_token"],
            original_task=value[:section_start],
            prompt_body=prompt_body,
        )
    return None


__all__ = [
    "MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS",
    "MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES",
    "NATIVE_CHILD_PROMPT_DELIVERY_VERSION",
    "NativeChildPromptDelivery",
    "parse_native_child_prompt_delivery",
    "render_native_child_prompt_delivery",
]
