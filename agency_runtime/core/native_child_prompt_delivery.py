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
CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION: Final[int] = 2
CODEX_NATIVE_CHILD_EXECUTION_VERSION: Final[int] = 1
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
_CODEX_OPAQUE_SECTION = (
    "[AGENCY EXACT SPECIALIST ACTIVATION v2]\n"
    "The decrypted native child message is the exact work-unit goal, but this first "
    "spawn turn establishes specialist context only. Do not execute, analyze, or modify "
    "the workspace during this activation turn; return one bounded readiness "
    "acknowledgement. Execute the goal exactly once only when a later newest inter-agent "
    "task contains a valid [AGENCY EXACT TASK EXECUTION v1] envelope matching this "
    "work-unit and goal hash. Do not answer the specialist prompt as a standalone "
    "request. The host "
    "hook bound the exact audited specialist below and Store-backed mutation authority "
    "to that persisted work-unit row. Use workspace tools when the goal requires them; "
    "hook policy will enforce the exact scope. Treat the text below as turn-scoped "
    "specialist instructions; do not copy it into the parent, another worker, status "
    "text, or the final response.\n"
)
_CODEX_OPAQUE_MARKER_PREFIX = "<!-- agency-native-child-delivery:v2:"
_CODEX_OPAQUE_MARKER_PATTERN = re.compile(
    re.escape(_CODEX_OPAQUE_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_CODEX_EXECUTION_SECTION = "[AGENCY EXACT TASK EXECUTION v1]\n"
_CODEX_EXECUTION_INSTRUCTION = (
    "Execute the exact work-unit goal delivered in your immediately preceding activation "
    "turn now. Do not re-delegate, broaden, or repeat it. Return one bounded "
    "evidence-backed result."
)
_CODEX_EXECUTION_MARKER_PREFIX = "<!-- agency-native-child-execution:v1:"
_CODEX_EXECUTION_MARKER_PATTERN = re.compile(
    re.escape(_CODEX_EXECUTION_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_V1_FIELDS = frozenset(
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
_V2_FIELDS = frozenset(
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
        "goal_hash",
    }
)
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_CODEX_EXECUTION_FIELDS = frozenset({"version", "work_unit_id", "native_task_name", "goal_hash"})


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
    goal_hash: str
    original_task: str
    prompt_body: str


@dataclass(frozen=True, slots=True)
class CodexNativeChildExecutionDelivery:
    """One content-free second-turn authorization for an exact Codex child."""

    work_unit_id: str
    native_task_name: str
    goal_hash: str


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


def _decoded_metadata(
    value: str,
    *,
    expected_fields: frozenset[str],
) -> dict[str, Any] | None:
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
    if not isinstance(result, dict) or frozenset(result) != expected_fields:
        return None
    return result


def _identity_metadata(
    *,
    envelope_version: int,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
) -> dict[str, Any]:
    normalized_host = str(host or "").strip().casefold()
    if normalized_host not in {"codex", "claude", "zcode"}:
        raise ValueError("native-child prompt delivery host is unsupported")
    session_id = validate_correlation_id(parent_session_id, field="parent_session_id")
    trace_id = validate_correlation_id(parent_trace_id, field="parent_trace_id")
    use_id = validate_correlation_id(tool_use_id, field="tool_use_id")
    unit_id = validate_correlation_id(work_unit_id, field="work_unit_id")
    slug = normalize_agent_slug(specialist_slug)
    normalized_specialist_version = str(specialist_version or "").strip()
    if (
        not normalized_specialist_version
        or normalize_version_identity(normalized_specialist_version)
        != normalized_specialist_version
    ):
        raise ValueError("specialist_version is invalid")
    content_hash = str(specialist_prompt_hash or "").strip().casefold()
    if content_digest_identity(content_hash) is None:
        raise ValueError("specialist_prompt_hash is invalid")
    return {
        "version": envelope_version,
        "host": normalized_host,
        "parent_session_id": session_id,
        "parent_trace_id": trace_id,
        "tool_use_id": use_id,
        "work_unit_id": unit_id,
        "specialist_slug": slug,
        "specialist_version": normalized_specialist_version,
        "specialist_prompt_hash": content_hash,
    }


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
    metadata = _identity_metadata(
        envelope_version=NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    token = str(activation_token or "").strip()
    if not token or len(token) > MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS:
        raise ValueError("activation_token is invalid")
    metadata["activation_token"] = token
    return metadata


def _codex_opaque_metadata(
    *,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
) -> dict[str, Any]:
    metadata = _identity_metadata(
        envelope_version=CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
        host="codex",
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    digest = str(goal_hash or "").strip().casefold()
    if _DIGEST_PATTERN.fullmatch(digest) is None:
        raise ValueError("goal_hash is invalid")
    metadata["goal_hash"] = digest
    return metadata


def _codex_execution_metadata(
    *,
    work_unit_id: object,
    goal_hash: object,
) -> dict[str, Any]:
    from agency_runtime.core.delegation.native_labels import (
        codex_task_name_for_work_unit,
    )

    unit_id = validate_correlation_id(work_unit_id, field="work_unit_id")
    digest = str(goal_hash or "").strip().casefold()
    if _DIGEST_PATTERN.fullmatch(digest) is None:
        raise ValueError("goal_hash is invalid")
    return {
        "version": CODEX_NATIVE_CHILD_EXECUTION_VERSION,
        "work_unit_id": unit_id,
        "native_task_name": codex_task_name_for_work_unit(unit_id),
        "goal_hash": digest,
    }


def render_codex_native_child_execution_message(
    *,
    work_unit_id: object,
    goal_hash: object,
) -> str:
    """Render the one exact actionable turn for a previously activated Codex child."""

    metadata = _codex_execution_metadata(
        work_unit_id=work_unit_id,
        goal_hash=goal_hash,
    )
    marker = f"{_CODEX_EXECUTION_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{_CODEX_EXECUTION_SECTION}{marker}\n{_CODEX_EXECUTION_INSTRUCTION}"


def parse_codex_native_child_execution_message(
    value: object,
) -> CodexNativeChildExecutionDelivery | None:
    """Recover one canonical execution envelope from a host message or transcript item."""

    if not isinstance(value, str) or not value:
        return None
    for match in reversed(list(_CODEX_EXECUTION_MARKER_PATTERN.finditer(value))):
        metadata = _decoded_metadata(
            match.group(1),
            expected_fields=_CODEX_EXECUTION_FIELDS,
        )
        if metadata is None:
            continue
        try:
            normalized = _codex_execution_metadata(
                work_unit_id=metadata.get("work_unit_id"),
                goal_hash=metadata.get("goal_hash"),
            )
        except ValueError:
            continue
        if metadata != normalized:
            continue
        section_start = value.rfind(_CODEX_EXECUTION_SECTION, 0, match.start())
        if section_start < 0 or section_start + len(_CODEX_EXECUTION_SECTION) != match.start():
            continue
        message_end = match.end() + 1 + len(_CODEX_EXECUTION_INSTRUCTION)
        if value[match.end() : message_end] != f"\n{_CODEX_EXECUTION_INSTRUCTION}":
            continue
        return CodexNativeChildExecutionDelivery(
            work_unit_id=normalized["work_unit_id"],
            native_task_name=normalized["native_task_name"],
            goal_hash=normalized["goal_hash"],
        )
    return None


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


def render_codex_opaque_native_child_prompt_delivery(
    prompt_body: object,
    *,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
) -> str:
    """Render content-free Codex child context bound to one persisted goal hash."""

    if not isinstance(prompt_body, str) or not prompt_body:
        raise ValueError("specialist prompt body must be a non-empty string")
    metadata = _codex_opaque_metadata(
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
        goal_hash=goal_hash,
    )
    if not content_identity_matches(prompt_body, metadata["specialist_prompt_hash"]):
        raise ValueError("specialist prompt body failed exact identity verification")
    marker = f"{_CODEX_OPAQUE_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{_CODEX_OPAQUE_SECTION}{marker}\n{prompt_body}"


def parse_native_child_prompt_delivery(value: object) -> NativeChildPromptDelivery | None:
    """Recover the last valid exact envelope from a rewritten native child task."""

    if not isinstance(value, str) or not value:
        return None
    matches = [
        (match.start(), NATIVE_CHILD_PROMPT_DELIVERY_VERSION, match)
        for match in _MARKER_PATTERN.finditer(value)
    ]
    matches.extend(
        (
            match.start(),
            CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
            match,
        )
        for match in _CODEX_OPAQUE_MARKER_PATTERN.finditer(value)
    )
    for _start, envelope_version, match in sorted(matches, reverse=True):
        fields = _V1_FIELDS if envelope_version == 1 else _V2_FIELDS
        metadata = _decoded_metadata(match.group(1), expected_fields=fields)
        if metadata is None:
            continue
        try:
            if envelope_version == NATIVE_CHILD_PROMPT_DELIVERY_VERSION:
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
            else:
                normalized = _codex_opaque_metadata(
                    parent_session_id=metadata.get("parent_session_id"),
                    parent_trace_id=metadata.get("parent_trace_id"),
                    tool_use_id=metadata.get("tool_use_id"),
                    work_unit_id=metadata.get("work_unit_id"),
                    specialist_slug=metadata.get("specialist_slug"),
                    specialist_version=metadata.get("specialist_version"),
                    specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
                    goal_hash=metadata.get("goal_hash"),
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
        if envelope_version == NATIVE_CHILD_PROMPT_DELIVERY_VERSION:
            section_start = value.rfind(_SECTION, 0, match.start())
            if section_start < 0 or section_start + len(_SECTION) != match.start():
                continue
            original_task = value[:section_start]
            from agency_runtime.core.unit_assignment import work_unit_goal_hash

            goal_hash = work_unit_goal_hash(original_task)
            activation_token = normalized["activation_token"]
        else:
            section_start = value.rfind(_CODEX_OPAQUE_SECTION, 0, match.start())
            if section_start != 0 or len(_CODEX_OPAQUE_SECTION) != match.start():
                continue
            original_task = ""
            goal_hash = normalized["goal_hash"]
            activation_token = ""
        return NativeChildPromptDelivery(
            host=normalized["host"],
            parent_session_id=normalized["parent_session_id"],
            parent_trace_id=normalized["parent_trace_id"],
            tool_use_id=normalized["tool_use_id"],
            work_unit_id=normalized["work_unit_id"],
            specialist_slug=normalized["specialist_slug"],
            specialist_version=normalized["specialist_version"],
            specialist_prompt_hash=normalized["specialist_prompt_hash"],
            activation_token=activation_token,
            goal_hash=goal_hash,
            original_task=original_task,
            prompt_body=prompt_body,
        )
    return None


__all__ = [
    "CODEX_NATIVE_CHILD_EXECUTION_VERSION",
    "CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION",
    "MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS",
    "MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES",
    "NATIVE_CHILD_PROMPT_DELIVERY_VERSION",
    "CodexNativeChildExecutionDelivery",
    "NativeChildPromptDelivery",
    "parse_codex_native_child_execution_message",
    "parse_native_child_prompt_delivery",
    "render_codex_native_child_execution_message",
    "render_codex_opaque_native_child_prompt_delivery",
    "render_native_child_prompt_delivery",
]
