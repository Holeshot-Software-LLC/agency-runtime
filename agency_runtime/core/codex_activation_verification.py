"""Exact CLI-shape recognition for Codex activation verification.

The bounded current-profile verification form runs a canary against an already
installed Codex adapter and must never fall through to installation, roster,
runtime-control, or dashboard work.
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Mapping

CODEX_ACTIVATION_EXISTING_STORE_ENV = "AGENCY_CANARY_REQUIRE_EXISTING_STORE"
CODEX_ACTIVATION_QUERY_HASH_ENV = "AGENCY_CANARY_REQUEST_SHA256"
CODEX_HOOK_EVENT_DIAGNOSTICS_ENV = "AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS"
CODEX_HOOK_DIAGNOSTICS_PATH_ENV = "AGENCY_CODEX_HOOK_DIAGNOSTICS_PATH"
CODEX_HOOK_EVENT_DIAGNOSTIC_STAGES = ("accepted", "completed", "failed")
MAX_CODEX_HOOK_EVENT_DIAGNOSTIC_COUNT = 999
MAX_CODEX_HOOK_JOIN_DIAGNOSTIC_BYTES = 16_384
MAX_CODEX_HOOK_JOIN_DIAGNOSTIC_ENTRIES = 8
_JOIN_DIAGNOSTIC_NAME = re.compile(r"[A-Za-z0-9_]{1,64}\Z")
_JOIN_DIAGNOSTIC_SLUG = re.compile(r"[a-z_]{1,64}\Z")
CODEX_RECONCILIATION_DIAGNOSTIC_REASONS = frozenset(
    {
        "boundary_mismatch",
        "identity_invalid",
        "identity_synthetic",
        "lineage_mismatch",
        "lineage_reader_unavailable",
        "lineage_unavailable",
        "plan_cardinality_mismatch",
        "reference_activation_cardinality_mismatch",
        "reference_activation_mismatch",
        "response_identity_unavailable",
        "response_shape_mismatch",
        "session_unavailable",
        "snapshot_unavailable",
        "task_label_mismatch",
    }
)
_PUBLIC_FIELDS = frozenset(
    {
        "activation_timeout",
        "agent",
        "all",
        "autonomous",
        "backup",
        "command",
        "config",
        "dry_run",
        "json",
        "no_dashboard",
        "profile",
        "production_container",
        "rollback",
        "verify_activation",
    }
)
_BOUND_FIELDS = _PUBLIC_FIELDS | frozenset({"func"})
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def is_restricted_codex_activation_canary_environment(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether this process is the exact non-bootstrapping canary child."""

    values = os.environ if environ is None else environ
    return bool(
        values.get("AGENCY_CANARY_MODE") == "1"
        and values.get(CODEX_ACTIVATION_EXISTING_STORE_ENV) == "1"
    )


def is_codex_hook_event_diagnostics_environment(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether fixed, content-free Codex hook-stage evidence is enabled."""

    values = os.environ if environ is None else environ
    return bool(
        is_restricted_codex_activation_canary_environment(values)
        and values.get(CODEX_HOOK_EVENT_DIAGNOSTICS_ENV) == "1"
    )


def restricted_codex_activation_query_hash(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the exact invocation digest only inside the restricted canary."""

    values = os.environ if environ is None else environ
    if not is_restricted_codex_activation_canary_environment(values):
        return ""
    candidate = values.get(CODEX_ACTIVATION_QUERY_HASH_ENV)
    if not isinstance(candidate, str) or _LOWER_SHA256.fullmatch(candidate) is None:
        return ""
    return candidate


def sanitize_codex_hook_event_diagnostics(value: object) -> dict[str, dict[str, int]]:
    """Project only bounded counts for the canonical Codex hook inventory."""

    if not isinstance(value, Mapping):
        return {}
    from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS

    expected_stages = frozenset(CODEX_HOOK_EVENT_DIAGNOSTIC_STAGES)
    projected: dict[str, dict[str, int]] = {}
    for event in CODEX_HOOK_EVENTS:
        candidate = value.get(event)
        if not isinstance(candidate, Mapping) or frozenset(candidate) != expected_stages:
            continue
        counts: dict[str, int] = {}
        valid = True
        for stage in CODEX_HOOK_EVENT_DIAGNOSTIC_STAGES:
            count = candidate.get(stage)
            if type(count) is not int or count < 0 or count > MAX_CODEX_HOOK_EVENT_DIAGNOSTIC_COUNT:
                valid = False
                break
            counts[stage] = count
        if valid and any(counts.values()):
            projected[event] = counts
    return projected


def codex_hook_join_diagnostics_path(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the private join-diagnostics sink path, or "" when not armed.

    The sink is honored only inside the restricted canary with hook-event
    diagnostics enabled, and only for an absolute path, because codex swallows
    hook stderr and encrypts hook stdout on 0.151: without a host-side sink
    the join's content-free refusal evidence is unobservable (AR-334).
    """

    values = os.environ if environ is None else environ
    if not is_codex_hook_event_diagnostics_environment(values):
        return ""
    candidate = values.get(CODEX_HOOK_DIAGNOSTICS_PATH_ENV) or ""
    return candidate if os.path.isabs(candidate) else ""


def sanitize_codex_hook_join_diagnostics(lines: object) -> list[dict[str, object]]:
    """Project bounded content-free join-diagnostic entries from raw JSONL."""

    import json

    if not isinstance(lines, str):
        return []
    entries: list[dict[str, object]] = []
    for line in lines.splitlines():
        if len(entries) >= MAX_CODEX_HOOK_JOIN_DIAGNOSTIC_ENTRIES:
            break
        line = line.strip()
        if not line or len(line) > 4096:
            continue
        try:
            candidate = json.loads(line)
        except ValueError:
            continue
        if not isinstance(candidate, Mapping):
            continue
        event = candidate.get("event")
        refusal = candidate.get("refusal")
        joined = candidate.get("joined")
        agent_type_admitted = candidate.get("agent_type_admitted")
        fields = candidate.get("fields")
        if not (
            isinstance(event, str)
            and _JOIN_DIAGNOSTIC_NAME.fullmatch(event)
            and isinstance(refusal, str)
            and (refusal == "" or _JOIN_DIAGNOSTIC_SLUG.fullmatch(refusal))
            and type(joined) is bool
            and type(agent_type_admitted) is bool
            and isinstance(fields, list)
            and len(fields) <= 32
            and all(
                isinstance(name, str) and _JOIN_DIAGNOSTIC_NAME.fullmatch(name) for name in fields
            )
        ):
            continue
        entries.append(
            {
                "event": event,
                "fields": sorted(fields),
                "refusal": refusal,
                "joined": joined,
                "agent_type_admitted": agent_type_admitted,
            }
        )
    return entries


def is_exact_codex_activation_verification(namespace: object) -> bool:
    """Return whether ``namespace`` is the reviewed verification-only form."""

    try:
        values = vars(namespace)
    except TypeError:
        return False
    if frozenset(values) != _BOUND_FIELDS:
        return False
    raw_timeout = getattr(namespace, "activation_timeout", 180.0)
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
        return False
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        return False
    return bool(
        getattr(namespace, "command", None) == "install"
        and getattr(namespace, "agent", None) == "codex"
        and getattr(namespace, "profile", None) is None
        and getattr(namespace, "config", None) is None
        and getattr(namespace, "all", False) is False
        and getattr(namespace, "autonomous", False) is False
        and getattr(namespace, "production_container", False) is False
        and getattr(namespace, "dry_run", False) is False
        and getattr(namespace, "rollback", False) is False
        and getattr(namespace, "verify_activation", False) is True
        and getattr(namespace, "backup", None) is None
        and getattr(namespace, "no_dashboard", None) is False
        and type(getattr(namespace, "json", None)) is bool
        and math.isfinite(timeout)
        and 0 < timeout <= 600
    )


__all__ = [
    "CODEX_ACTIVATION_EXISTING_STORE_ENV",
    "CODEX_ACTIVATION_QUERY_HASH_ENV",
    "CODEX_HOOK_DIAGNOSTICS_PATH_ENV",
    "CODEX_HOOK_EVENT_DIAGNOSTICS_ENV",
    "CODEX_HOOK_EVENT_DIAGNOSTIC_STAGES",
    "CODEX_RECONCILIATION_DIAGNOSTIC_REASONS",
    "MAX_CODEX_HOOK_EVENT_DIAGNOSTIC_COUNT",
    "MAX_CODEX_HOOK_JOIN_DIAGNOSTIC_BYTES",
    "MAX_CODEX_HOOK_JOIN_DIAGNOSTIC_ENTRIES",
    "codex_hook_join_diagnostics_path",
    "is_codex_hook_event_diagnostics_environment",
    "is_exact_codex_activation_verification",
    "is_restricted_codex_activation_canary_environment",
    "restricted_codex_activation_query_hash",
    "sanitize_codex_hook_event_diagnostics",
    "sanitize_codex_hook_join_diagnostics",
]
