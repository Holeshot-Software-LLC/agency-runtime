"""Content-free durable projection of one inference-owned child staffing decision.

The projection is Agency-authored routing evidence, not proof that a native host
delivered anything.  Its purpose is to give the independent host-artifact reader
an exact expected decision: one ordered team, one managed installation, one
parent/launch/child binding, and one credential-free provider receipt.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Final

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.roster.revisions import content_digest_identity
from agency_runtime.core.selector.receipt_projection import project_model_receipt_attempts
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.version_identity import normalize_version_identity

NATIVE_CHILD_STAFFING_DECISION_SCHEMA: Final[str] = "agency.native-child-staffing-decision.v1"
MAX_NATIVE_CHILD_STAFFING_CARDS: Final[int] = 3
MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS: Final[int] = 300

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_BINDING_KIND = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_HOSTS = frozenset({"claude", "codex", "hermes", "openclaw", "zcode"})
_FIELDS = frozenset(
    {
        "schema",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "binding_kind",
        "binding_id",
        "provider_attempts",
        "provider_receipt_digest",
        "task_sha256",
        "team_digest",
        "candidate_digest",
        "runtime_digest",
        "install_id",
        "bundle_digest",
        "issued_at",
        "expires_at",
        "nonce",
        "cards",
    }
)
_CARD_FIELDS = frozenset(
    {
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "body_character_length",
    }
)


def _digest(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    return normalized if _DIGEST.fullmatch(normalized) is not None else ""


def _timestamp(value: object) -> tuple[str, datetime] | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    utc = parsed.astimezone(timezone.utc)
    timespec = "microseconds" if utc.microsecond else "seconds"
    canonical = utc.isoformat(timespec=timespec).replace("+00:00", "Z")
    return (canonical, utc) if value == canonical else None


def _cards(value: object) -> list[dict[str, Any]] | None:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or not 1 <= len(value) <= MAX_NATIVE_CHILD_STAFFING_CARDS
    ):
        return None
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping) or frozenset(item) != _CARD_FIELDS:
            return None
        try:
            slug = normalize_agent_slug(item.get("specialist_slug"))
        except (TypeError, ValueError):
            return None
        version = str(item.get("specialist_version") or "").strip()
        prompt_hash = _digest(item.get("specialist_prompt_hash"))
        body_length = item.get("body_character_length")
        if (
            slug in seen
            or not version
            or normalize_version_identity(version) != version
            or content_digest_identity(prompt_hash) != prompt_hash
            or type(body_length) is not int
            or not 1 <= body_length <= MAX_SPECIALIST_PROMPT_CHARS
        ):
            return None
        seen.add(slug)
        result.append(
            {
                "specialist_slug": slug,
                "specialist_version": version,
                "specialist_prompt_hash": prompt_hash,
                "body_character_length": body_length,
            }
        )
    return result


def canonical_native_child_provider_receipt_digest(value: object) -> str | None:
    """Return the identity of one bounded, credential-free provider attempt list."""

    attempts = project_model_receipt_attempts(value)
    if (
        attempts is None
        or not attempts
        or attempts[-1].get("status") != "applied"
        or sum(item.get("status") == "applied" for item in attempts) != 1
        or any(item.get("status") not in {"applied", "failed", "skipped"} for item in attempts)
    ):
        return None
    return sha256(
        json.dumps(
            attempts,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def project_native_child_staffing_decision(value: object) -> dict[str, Any] | None:
    """Validate one exact content-free child staffing decision projection.

    This function does not establish delivery.  A host-artifact validator must
    later match every returned field and independently establish pre-speech
    placement before it may set ``verified_delivery``.
    """

    if not isinstance(value, Mapping) or frozenset(value) != _FIELDS:
        return None
    if value.get("schema") != NATIVE_CHILD_STAFFING_DECISION_SCHEMA:
        return None
    host = str(value.get("host") or "").strip().casefold()
    kind = str(value.get("binding_kind") or "").strip().casefold()
    if host not in _HOSTS or _BINDING_KIND.fullmatch(kind) is None:
        return None
    try:
        parent_session_id = validate_correlation_id(
            value.get("parent_session_id"), field="parent_session_id"
        )
        parent_trace_id = validate_correlation_id(
            value.get("parent_trace_id"), field="parent_trace_id"
        )
        launch_id = validate_correlation_id(value.get("launch_id"), field="launch_id")
        binding_id = validate_correlation_id(value.get("binding_id"), field="binding_id")
        install_id = validate_correlation_id(value.get("install_id"), field="install_id")
        nonce = validate_correlation_id(value.get("nonce"), field="nonce")
    except (TypeError, ValueError):
        return None

    attempts = project_model_receipt_attempts(value.get("provider_attempts"))
    receipt_digest = canonical_native_child_provider_receipt_digest(attempts)
    cards = _cards(value.get("cards"))
    issued = _timestamp(value.get("issued_at"))
    expires = _timestamp(value.get("expires_at"))
    candidate_digest = _digest(value.get("candidate_digest"))
    runtime_digest = _digest(value.get("runtime_digest"))
    if (
        attempts is None
        or receipt_digest is None
        or value.get("provider_receipt_digest") != receipt_digest
        or cards is None
        or issued is None
        or expires is None
        or expires[1] <= issued[1]
        or (expires[1] - issued[1]).total_seconds() > MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS
        or candidate_digest == ""
        or candidate_digest != runtime_digest
    ):
        return None
    team_digest = sha256(
        json.dumps(
            cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if value.get("team_digest") != team_digest:
        return None
    task_sha256 = _digest(value.get("task_sha256"))
    bundle_digest = _digest(value.get("bundle_digest"))
    if not task_sha256 or not bundle_digest:
        return None
    return {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": host,
        "parent_session_id": parent_session_id,
        "parent_trace_id": parent_trace_id,
        "launch_id": launch_id,
        "binding_kind": kind,
        "binding_id": binding_id,
        "provider_attempts": attempts,
        "provider_receipt_digest": receipt_digest,
        "task_sha256": task_sha256,
        "team_digest": team_digest,
        "candidate_digest": candidate_digest,
        "runtime_digest": runtime_digest,
        "install_id": install_id,
        "bundle_digest": bundle_digest,
        "issued_at": issued[0],
        "expires_at": expires[0],
        "nonce": nonce,
        "cards": cards,
    }


__all__ = [
    "MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS",
    "MAX_NATIVE_CHILD_STAFFING_CARDS",
    "NATIVE_CHILD_STAFFING_DECISION_SCHEMA",
    "canonical_native_child_provider_receipt_digest",
    "project_native_child_staffing_decision",
]
