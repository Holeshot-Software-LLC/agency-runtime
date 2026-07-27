"""Fail-closed operator-presence boundary for persistent CLI mutations.

Parser leaves opt in explicitly.  The shared dispatch boundary binds one
verification request to a canonical digest of the parsed operation, invokes a
result-only OS verifier, and rechecks the digest immediately before dispatch.
No phrase, environment variable, stdin value, or reusable bearer token can
satisfy this boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from agency_runtime.core.codex_activation_verification import (
    CODEX_ACTIVATION_VERIFICATION_ACTION,
)

_OPERATION_DOMAIN = b"agency.operator-presence.v1\x00"
_MAX_OPERATION_BYTES = 128 * 1024
_MAX_COLLECTION_ITEMS = 512
_MAX_VALUE_DEPTH = 8
_COMMAND_PART = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
_COMMAND_PATH_FIELDS = (
    "command",
    "config_command",
    "config_provider_command",
    "source_command",
    "roster_command",
    "remediation_command",
    "upstream_command",
    "candidate_command",
    "agents_command",
    "workforce_command",
    "contractor_command",
    "hiring_command",
    "db_command",
    "dashboard_command",
    "dashboard_service_action",
)
_ROSTER_ROLLBACK_ACTION = "roster.rollback.v1"
_ROSTER_ROLLBACK_PATH = ("roster", "rollback")
_CODEX_INSTALL_ACTION = "install.codex.v1"
_CODEX_INSTALL_PATH = ("install",)
OPERATOR_PRESENCE_FAMILIES = frozenset(
    {
        "agent-governance",
        "configuration",
        "dashboard-service",
        "database-maintenance",
        "hiring-governance",
        "installation",
        "roster-governance",
        "runtime-control",
        "workforce-governance",
    }
)


class OperatorPresenceError(RuntimeError):
    """Raised before dispatch when result-only OS verification is unavailable or denied."""


@dataclass(frozen=True, slots=True)
class OperatorPresenceRequest:
    """A secret-free, operation-bound request suitable for an OS verification prompt."""

    family: str
    command_path: tuple[str, ...]
    operation_digest: str
    prompt: str


@dataclass(frozen=True, slots=True)
class OperatorPresenceReceipt:
    """Ephemeral evidence that the immediately following dispatch was verified."""

    family: str
    command_path: tuple[str, ...]
    operation_digest: str
    mechanism: str
    verified_at: str


class _PresenceStatus(Enum):
    VERIFIED = "verified"
    CANCELED = "canceled"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class _PresenceResult:
    status: _PresenceStatus
    mechanism: str
    detail: str


def _normalize_value(value: Any, *, depth: int = 0) -> Any:
    if depth > _MAX_VALUE_DEPTH:
        raise OperatorPresenceError("operator-presence operation exceeds the nesting limit")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise OperatorPresenceError("operator-presence operation contains a non-finite number")
        return value
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_COLLECTION_ITEMS:
            raise OperatorPresenceError("operator-presence operation exceeds the collection limit")
        return [_normalize_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > _MAX_COLLECTION_ITEMS or any(not isinstance(key, str) for key in value):
            raise OperatorPresenceError("operator-presence operation contains an invalid mapping")
        return {key: _normalize_value(item, depth=depth + 1) for key, item in sorted(value.items())}
    raise OperatorPresenceError(
        f"operator-presence operation contains unsupported value type {type(value).__name__}"
    )


def _command_path(namespace: argparse.Namespace) -> tuple[str, ...]:
    parts: list[str] = []
    for field in _COMMAND_PATH_FIELDS:
        value = getattr(namespace, field, None)
        if value is None:
            continue
        if not isinstance(value, str) or not _COMMAND_PART.fullmatch(value):
            raise OperatorPresenceError("operator-presence command path is invalid")
        parts.append(value)
    if not parts:
        raise OperatorPresenceError("operator-presence command path is unavailable")
    return tuple(parts)


def _uses_prepared_operator_presence(namespace: argparse.Namespace) -> bool:
    """Recognize the one parser leaf whose handler owns prepared verification.

    The marker is an internal parser default, not an authorization value.  A
    copied or malformed marker fails closed unless the parsed command path and
    mutation family are the one reviewed prepared-mutation integration.
    """

    action = getattr(namespace, "_operator_presence_prepared_action", "")
    if not action:
        return False
    family = getattr(namespace, "_operator_presence_family", "")
    path = _command_path(namespace)
    if action == _ROSTER_ROLLBACK_ACTION:
        if family != "roster-governance" or path != _ROSTER_ROLLBACK_PATH:
            raise OperatorPresenceError("prepared operator-presence parser binding is invalid")
        return True
    if action in {_CODEX_INSTALL_ACTION, CODEX_ACTIVATION_VERIFICATION_ACTION}:
        if family != "installation" or path != _CODEX_INSTALL_PATH:
            raise OperatorPresenceError("prepared operator-presence parser binding is invalid")
        from agency_runtime.core.codex_activation_verification import (
            is_exact_codex_activation_verification,
        )
        from agency_runtime.core.prepared_codex_install import (
            is_exact_prepared_codex_install,
        )

        # The marker is attached to the install parser, but only this exact
        # prepared mutation or the exact verification-only shape delegates its
        # own authority boundary. Every other install mode retains the generic
        # fail-closed boundary.
        if action == _CODEX_INSTALL_ACTION:
            return is_exact_prepared_codex_install(namespace)
        if not is_exact_codex_activation_verification(namespace):
            raise OperatorPresenceError("Codex activation-verification parser binding is invalid")
        return True
    raise OperatorPresenceError("prepared operator-presence parser binding is invalid")


def request_for_namespace(namespace: argparse.Namespace) -> OperatorPresenceRequest | None:
    """Build a request for an explicitly annotated mutating parser leaf."""

    if _uses_prepared_operator_presence(namespace):
        return None
    family = getattr(namespace, "_operator_presence_family", "")
    if not family:
        return None
    if family not in OPERATOR_PRESENCE_FAMILIES:
        raise OperatorPresenceError("operator-presence mutation family is invalid")
    if bool(getattr(namespace, "_operator_presence_dry_run_exempt", False)) and bool(
        getattr(namespace, "dry_run", False)
    ):
        return None

    command_path = _command_path(namespace)
    arguments = {
        key: _normalize_value(value)
        for key, value in sorted(vars(namespace).items())
        if key != "func" and not key.startswith("_")
    }
    payload = json.dumps(
        {
            "arguments": arguments,
            "command_path": command_path,
            "family": family,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(payload) > _MAX_OPERATION_BYTES:
        raise OperatorPresenceError("operator-presence operation exceeds the size limit")
    digest = hashlib.sha256(_OPERATION_DOMAIN + payload).hexdigest()
    prompt = (
        "Agency Runtime operator verification\n"
        f"Action: {' '.join(command_path)}\n"
        f"Family: {family}\n"
        f"Operation digest: {digest}\n"
        "Approve only if you initiated this exact persistent change."
    )
    return OperatorPresenceRequest(
        family=family,
        command_path=command_path,
        operation_digest=digest,
        prompt=prompt,
    )


def _request_os_operator_presence(_prompt: str) -> _PresenceResult:
    """Return only OS-verifier status; production remains closed until a safe backend exists."""

    return _PresenceResult(
        status=_PresenceStatus.UNAVAILABLE,
        mechanism="unavailable",
        detail="a non-exporting OS operator-presence verifier is not available",
    )


def require_operator_presence(request: OperatorPresenceRequest) -> OperatorPresenceReceipt:
    """Require one fresh result-only OS verification for ``request``."""

    result = _request_os_operator_presence(request.prompt)
    if result.status is not _PresenceStatus.VERIFIED:
        raise OperatorPresenceError(
            "operator presence was not verified; no persistent change was dispatched "
            f"({result.status.value}: {result.detail})"
        )
    return OperatorPresenceReceipt(
        family=request.family,
        command_path=request.command_path,
        operation_digest=request.operation_digest,
        mechanism=result.mechanism,
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


def enforce_for_namespace(namespace: argparse.Namespace) -> OperatorPresenceReceipt | None:
    """Verify an annotated mutation and reject any operation change during verification."""

    request = request_for_namespace(namespace)
    if request is None:
        return None
    receipt = require_operator_presence(request)
    if request_for_namespace(namespace) != request:
        raise OperatorPresenceError(
            "operator-presence operation changed during verification; no persistent change "
            "was dispatched"
        )
    return receipt


__all__ = [
    "OPERATOR_PRESENCE_FAMILIES",
    "OperatorPresenceError",
    "OperatorPresenceReceipt",
    "OperatorPresenceRequest",
    "enforce_for_namespace",
    "request_for_namespace",
    "require_operator_presence",
]
