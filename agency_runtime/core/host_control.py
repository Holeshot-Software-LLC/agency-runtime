"""Persistent host-scoped runtime control.

This is deliberately a soft control: native plugins stay registered and loaded
so their command surface can turn Agency Runtime back on. Adapter event
boundaries consult this state before doing work.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from agency_runtime.core.host_capabilities import (
    host_capability_receipt_from_native_evidence,
)
from agency_runtime.core.runtime_control_command import parse_host_control_arguments
from agency_runtime.core.store.evidence import HostControlConflictError
from agency_runtime.core.store.sqlite import Store

SUPPORTED_HOSTS: tuple[str, ...] = ("hermes", "openclaw", "codex", "claude", "zcode")


def normalize_host(host: str) -> str:
    """Return a supported normalized host or raise a useful error."""
    normalized = str(host or "").strip().lower()
    if normalized not in SUPPORTED_HOSTS:
        raise ValueError(f"unsupported host {host!r}; expected one of {', '.join(SUPPORTED_HOSTS)}")
    return normalized


def get_runtime_control(store: Store, host: str) -> dict[str, Any]:
    """Read the persistent soft-control record for a supported host."""
    return store.get_host_control(normalize_host(host))


def set_runtime_control(
    store: Store,
    host: str,
    *,
    enabled: bool,
    source: str,
    expected_generation: int | None = None,
) -> dict[str, Any]:
    """Persist and verify a host soft-control compare-and-swap transition."""
    normalized = normalize_host(host)
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean")
    desired = enabled
    if expected_generation is None:
        expected_generation = int(get_runtime_control(store, normalized).get("generation", 0))
    written = store.set_host_control(
        normalized,
        enabled=desired,
        expected_generation=expected_generation,
        source=source,
    )
    if bool(written.get("enabled")) != desired:
        raise RuntimeError(
            f"host control postcondition failed for {normalized}: "
            f"wanted enabled={desired}, committed enabled={written.get('enabled')!r}"
        )
    return written


def inspect_host_status(
    store: Store,
    host: str,
    *,
    native_record: dict[str, Any] | None = None,
    inspector: Callable[[], list[dict[str, Any]]] | None = None,
    global_enabled: bool | None = None,
) -> dict[str, Any]:
    """Merge non-mutating native installation facts with runtime control."""
    normalized = normalize_host(host)
    if native_record is None:
        if inspector is None:
            from agency_runtime.core.installer import inspect_host_installations

            inspector = inspect_host_installations
        native_record = next(
            (
                item
                for item in inspector()
                if str(item.get("host") or "").strip().lower() == normalized
            ),
            {"host": normalized},
        )
    control = get_runtime_control(store, normalized)
    if global_enabled is None:
        from agency_runtime.core.runtime_control import master_enabled

        global_enabled = master_enabled()
    registered = native_record.get("registered")
    native_enabled = native_record.get("enabled")
    if not global_enabled or not bool(control["enabled"]):
        effective: bool | None = False
    elif registered is False or native_enabled is False:
        effective = False
    elif registered is True and native_enabled is True:
        effective = True
    else:
        effective = None
    capability_receipt = host_capability_receipt_from_native_evidence(
        normalized,
        platform="windows" if os.name == "nt" else "linux",
        native_record=native_record,
    )
    return {
        **native_record,
        "host": normalized,
        "runtime_enabled": bool(control["enabled"]),
        "master_enabled": bool(global_enabled),
        "runtime_control_updated_at": control.get("updated_at"),
        "runtime_control_source": control.get("source"),
        "runtime_control_generation": int(control.get("generation", 0)),
        "effective_enabled": effective,
        "execution_capabilities": capability_receipt.as_dict(),
    }


def inspect_all_host_statuses(
    store: Store,
    *,
    inspector: Callable[[], list[dict[str, Any]]] | None = None,
    global_enabled: bool | None = None,
) -> list[dict[str, Any]]:
    """Inspect each supported host without mutating native or runtime state."""
    if inspector is None:
        from agency_runtime.core.installer import inspect_host_installations

        inspector = inspect_host_installations
    native = {str(item.get("host") or "").strip().lower(): item for item in inspector()}
    if global_enabled is None:
        from agency_runtime.core.runtime_control import master_enabled

        global_enabled = master_enabled()
    return [
        inspect_host_status(
            store,
            host,
            native_record=native.get(host, {"host": host}),
            global_enabled=global_enabled,
        )
        for host in SUPPORTED_HOSTS
    ]


def handle_host_control_command(
    host: str,
    raw_args: str = "",
    *,
    store: Store | None = None,
    source: str = "host-command",
) -> dict[str, Any]:
    """Handle a host-native agency status/on/off command."""
    normalized = normalize_host(host)
    action = parse_host_control_arguments(raw_args).action
    runtime_store = store or Store()
    if action in {"on", "off"}:
        current = get_runtime_control(runtime_store, normalized)
        control = set_runtime_control(
            runtime_store,
            normalized,
            enabled=action == "on",
            source=source,
            expected_generation=int(current["generation"]),
        )
    else:
        control = get_runtime_control(runtime_store, normalized)
    from agency_runtime.core.runtime_control import master_enabled

    global_enabled = master_enabled()
    state = "enabled" if control["enabled"] else "disabled"
    effective = bool(global_enabled and control["enabled"])
    global_note = "" if global_enabled else " Agency is globally paused."
    return {
        "ok": True,
        "host": normalized,
        "action": action,
        "runtime_enabled": bool(control["enabled"]),
        "master_enabled": global_enabled,
        "effective_enabled": effective,
        "updated_at": control.get("updated_at"),
        "source": control.get("source"),
        "generation": int(control.get("generation", 0)),
        "message": f"Agency Runtime is {state} for {normalized}.{global_note}",
    }


__all__ = [
    "SUPPORTED_HOSTS",
    "HostControlConflictError",
    "get_runtime_control",
    "handle_host_control_command",
    "inspect_all_host_statuses",
    "inspect_host_status",
    "normalize_host",
    "set_runtime_control",
]
