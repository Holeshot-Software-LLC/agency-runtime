"""Exact parser contract for the operator-owned full-suite installer."""

from __future__ import annotations

import math

from agency_runtime.core.installer_contracts import HOSTS
from agency_runtime.core.policy.profiles import PROFILES

_FIELDS = frozenset(
    {
        "command",
        "profile",
        "all",
        "agent",
        "dry_run",
        "rollback",
        "verify_activation",
        "backup",
        "no_dashboard",
        "activation_timeout",
        "json",
        "_operator_presence_family",
        "_operator_presence_dry_run_exempt",
        "func",
    }
)


def is_exact_install_lifecycle(namespace: object) -> bool:
    """Return whether ``namespace`` is one complete parser-owned install shape."""

    try:
        values = vars(namespace)
    except TypeError:
        return False
    if frozenset(values) != _FIELDS:
        return False
    profile = getattr(namespace, "profile", None)
    all_hosts = getattr(namespace, "all", None)
    agent = getattr(namespace, "agent", None)
    dry_run = getattr(namespace, "dry_run", None)
    rollback = getattr(namespace, "rollback", None)
    verify_activation = getattr(namespace, "verify_activation", None)
    backup = getattr(namespace, "backup", None)
    no_dashboard = getattr(namespace, "no_dashboard", None)
    json_mode = getattr(namespace, "json", None)
    timeout = getattr(namespace, "activation_timeout", None)
    if (
        getattr(namespace, "command", None) != "install"
        or getattr(namespace, "_operator_presence_family", None) != "installation"
        or getattr(namespace, "_operator_presence_dry_run_exempt", None) is not True
        or (profile is not None and profile not in PROFILES)
        or type(all_hosts) is not bool
        or (agent is not None and agent not in HOSTS)
        or (all_hosts and agent is not None)
        or type(dry_run) is not bool
        or type(rollback) is not bool
        or type(verify_activation) is not bool
        or type(no_dashboard) is not bool
        or type(json_mode) is not bool
        or sum((dry_run, rollback, verify_activation)) > 1
        or (backup is not None and (not rollback or not isinstance(backup, str) or not backup))
        or isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
    ):
        return False
    normalized_timeout = float(timeout)
    if not math.isfinite(normalized_timeout) or not 0 < normalized_timeout <= 600:
        return False
    if verify_activation:
        return bool(
            agent == "codex"
            and not all_hosts
            and profile is None
            and backup is None
            and not no_dashboard
        )
    if rollback:
        return bool(agent is not None and not all_hosts)
    return backup is None


__all__ = ["is_exact_install_lifecycle"]
