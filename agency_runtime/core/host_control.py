"""Persistent host-scoped runtime control.

This is deliberately a soft control: native plugins stay registered and loaded
so their command surface can turn Agency Runtime back on. Adapter event
boundaries consult this state before doing work.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agency_runtime.core.store.sqlite import Store

SUPPORTED_HOSTS: tuple[str, ...] = ("hermes", "openclaw", "codex", "claude")


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
) -> dict[str, Any]:
    """Persist and verify a host soft-control transition."""
    normalized = normalize_host(host)
    desired = bool(enabled)
    written = store.set_host_control(normalized, enabled=desired, source=source)
    observed = store.get_host_control(normalized)
    if bool(written.get("enabled")) != desired or bool(observed.get("enabled")) != desired:
        raise RuntimeError(
            f"host control postcondition failed for {normalized}: "
            f"wanted enabled={desired}, observed enabled={observed.get('enabled')!r}"
        )
    return observed


def inspect_host_status(
    store: Store,
    host: str,
    *,
    native_record: dict[str, Any] | None = None,
    inspector: Callable[[], list[dict[str, Any]]] | None = None,
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
    registered = native_record.get("registered")
    native_enabled = native_record.get("enabled")
    if not bool(control["enabled"]):
        effective: bool | None = False
    elif registered is False or native_enabled is False:
        effective = False
    elif registered is True and native_enabled is True:
        effective = True
    else:
        effective = None
    return {
        **native_record,
        "host": normalized,
        "runtime_enabled": bool(control["enabled"]),
        "runtime_control_updated_at": control.get("updated_at"),
        "runtime_control_source": control.get("source"),
        "effective_enabled": effective,
    }


def inspect_all_host_statuses(
    store: Store,
    *,
    inspector: Callable[[], list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    """Inspect each supported host without mutating native or runtime state."""
    if inspector is None:
        from agency_runtime.core.installer import inspect_host_installations

        inspector = inspect_host_installations
    native = {str(item.get("host") or "").strip().lower(): item for item in inspector()}
    return [
        inspect_host_status(store, host, native_record=native.get(host, {"host": host}))
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
    tokens = str(raw_args or "").strip().lower().split()
    action = tokens[0] if tokens else "status"
    if len(tokens) > 1 or action not in {"status", "on", "off"}:
        raise ValueError("usage: /agency [status|on|off]")
    runtime_store = store or Store()
    if action in {"on", "off"}:
        control = set_runtime_control(
            runtime_store,
            normalized,
            enabled=action == "on",
            source=source,
        )
    else:
        control = get_runtime_control(runtime_store, normalized)
    state = "enabled" if control["enabled"] else "disabled"
    return {
        "ok": True,
        "host": normalized,
        "action": action,
        "runtime_enabled": bool(control["enabled"]),
        "updated_at": control.get("updated_at"),
        "source": control.get("source"),
        "message": f"Agency Runtime is {state} for {normalized}.",
    }
