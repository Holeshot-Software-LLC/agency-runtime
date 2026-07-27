"""Exact CLI-shape recognition for Codex activation verification.

The install parser also owns persistent installation modes.  Only the bounded
current-profile verification form may bypass that mutation boundary: it runs a
canary against an already installed Codex adapter and must never fall through
to installation, roster, runtime-control, or dashboard work.
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping

CODEX_ACTIVATION_VERIFICATION_ACTION = "install.codex.verify-activation.v1"
CODEX_ACTIVATION_EXISTING_STORE_ENV = "AGENCY_CANARY_REQUIRE_EXISTING_STORE"
_PUBLIC_FIELDS = frozenset(
    {
        "activation_timeout",
        "agent",
        "all",
        "backup",
        "command",
        "dry_run",
        "json",
        "no_dashboard",
        "profile",
        "rollback",
        "verify_activation",
    }
)
_BOUND_FIELDS = _PUBLIC_FIELDS | frozenset(
    {
        "func",
        "_operator_presence_family",
        "_operator_presence_dry_run_exempt",
        "_operator_presence_prepared_action",
    }
)


def is_restricted_codex_activation_canary_environment(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether this process is the exact non-bootstrapping canary child."""

    values = os.environ if environ is None else environ
    return bool(
        values.get("AGENCY_CANARY_MODE") == "1"
        and values.get(CODEX_ACTIVATION_EXISTING_STORE_ENV) == "1"
    )


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
        and getattr(namespace, "_operator_presence_family", None) == "installation"
        and getattr(namespace, "_operator_presence_dry_run_exempt", None) is True
        and getattr(namespace, "_operator_presence_prepared_action", None)
        == CODEX_ACTIVATION_VERIFICATION_ACTION
        and getattr(namespace, "agent", None) == "codex"
        and getattr(namespace, "profile", None) is None
        and getattr(namespace, "all", False) is False
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
    "CODEX_ACTIVATION_VERIFICATION_ACTION",
    "is_exact_codex_activation_verification",
    "is_restricted_codex_activation_canary_environment",
]
