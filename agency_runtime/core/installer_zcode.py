"""Direct, ownership-aware ZCode 3.5 hook configuration lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.installer_contracts import PLUGIN_ID, PLUGIN_VERSION
from agency_runtime.core.private_paths import ensure_private_directory

ZCODE_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PostToolUseFailure",
    "Stop",
)
ZCODE_FRAGMENT = "zcode-hooks.json"
_MAX_CONFIG_BYTES = 2 * 1024 * 1024
_MAX_STATE_BYTES = 256 * 1024
_STATE_SCHEMA_VERSION = 1


class ZCodeRegistrationError(RuntimeError):
    """A ZCode config transaction could not prove safe ownership."""


def _home(home_dir: str | Path | None) -> Path:
    return Path(home_dir).expanduser().resolve() if home_dir is not None else Path.home().resolve()


def zcode_config_path(*, home_dir: str | Path | None) -> Path:
    return (_home(home_dir) / ".zcode" / "cli" / "config.json").resolve()


def zcode_registration_state_path(*, home_dir: str | Path | None) -> Path:
    return (_home(home_dir) / ".agency-runtime" / "zcode-registration.json").resolve()


def _read_optional(path: Path, *, limit: int, label: str) -> bytes | None:
    try:
        return read_bounded_regular_file(path, limit=limit, label=label)
    except FileNotFoundError:
        return None


def _load_object(raw: bytes | None, *, label: str) -> dict[str, Any]:
    if raw is None:
        return {}
    value = safe_load_bounded_json(
        raw,
        maximum_bytes=len(raw),
        maximum_depth=48,
        maximum_nodes=50_000,
    )
    if not isinstance(value, dict):
        raise ZCodeRegistrationError(f"{label} must be a JSON object")
    return value


def _render(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _atomic_json_replace(
    path: Path,
    value: Mapping[str, Any],
    *,
    expected: bytes | None,
    product_owned_parent: bool,
    label: str,
) -> bytes:
    parent = ensure_private_directory(path.parent, product_owned=product_owned_parent)
    observed = _read_optional(path, limit=_MAX_CONFIG_BYTES, label=label)
    if observed != expected:
        raise ZCodeRegistrationError(f"{label} changed concurrently; refusing to overwrite it")
    payload = _render(value)
    temporary = parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        with suppress(OSError):
            os.chmod(temporary, 0o600)
        observed = _read_optional(path, limit=_MAX_CONFIG_BYTES, label=label)
        if observed != expected:
            raise ZCodeRegistrationError(f"{label} changed concurrently; refusing to overwrite it")
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    return payload


def _restore_config(path: Path, *, current: bytes, prior: bytes | None) -> None:
    observed = _read_optional(path, limit=_MAX_CONFIG_BYTES, label="ZCode config")
    if observed != current:
        raise ZCodeRegistrationError(
            "ZCode config changed while rolling back a failed registration transaction"
        )
    if prior is None:
        path.unlink()
        return
    prior_value = _load_object(prior, label="prior ZCode config")
    _atomic_json_replace(
        path,
        prior_value,
        expected=current,
        product_owned_parent=False,
        label="ZCode config",
    )


def _argument_event(args: object) -> str | None:
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        return None
    expected_prefix = ["agency_runtime.cli", "hook", "zcode", "--event"]
    for index in range(max(0, len(args) - len(expected_prefix))):
        if args[index : index + 4] == expected_prefix and index + 4 < len(args):
            return args[index + 4]
    return None


def _agency_registration_event(registration: object) -> str | None:
    if not isinstance(registration, dict):
        return None
    handlers = registration.get("hooks")
    if not isinstance(handlers, list):
        return None
    events = {
        event
        for handler in handlers
        if isinstance(handler, dict)
        if (event := _argument_event(handler.get("args"))) is not None
    }
    return next(iter(events)) if len(events) == 1 else None


def _validate_registration(registration: object, event: str) -> dict[str, Any]:
    if not isinstance(registration, dict):
        raise ZCodeRegistrationError(f"ZCode {event} registration must be an object")
    handlers = registration.get("hooks")
    if not isinstance(handlers, list) or len(handlers) != 1:
        raise ZCodeRegistrationError(f"ZCode {event} must have one Agency handler")
    handler = handlers[0]
    if not isinstance(handler, dict):
        raise ZCodeRegistrationError(f"ZCode {event} handler must be an object")
    command = handler.get("command")
    if handler.get("type") != "process" or not isinstance(command, str):
        raise ZCodeRegistrationError(f"ZCode {event} must use a process handler")
    if not Path(command).is_absolute():
        raise ZCodeRegistrationError(f"ZCode {event} process command must be absolute")
    if _argument_event(handler.get("args")) != event:
        raise ZCodeRegistrationError(f"ZCode {event} handler argv is not event-bound")
    timeout = handler.get("timeoutMs")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ZCodeRegistrationError(f"ZCode {event} handler timeoutMs is invalid")
    if not isinstance(handler.get("enabled"), bool):
        raise ZCodeRegistrationError(f"ZCode {event} handler enabled flag is invalid")
    expected_matcher = (
        "Agent"
        if event == "PreToolUse"
        else "*"
        if event
        in {
            "PermissionRequest",
            "PostToolUse",
            "PostToolUseFailure",
        }
        else None
    )
    if expected_matcher is not None and registration.get("matcher") != expected_matcher:
        raise ZCodeRegistrationError(f"ZCode {event} matcher is invalid")
    return dict(registration)


def load_zcode_fragment(target: Path) -> dict[str, Any]:
    raw = read_bounded_regular_file(
        target / ZCODE_FRAGMENT,
        limit=_MAX_CONFIG_BYTES,
        label="managed ZCode hook fragment",
    )
    fragment = _load_object(raw, label="managed ZCode hook fragment")
    hooks = fragment.get("hooks")
    if not isinstance(hooks, dict):
        raise ZCodeRegistrationError("managed ZCode fragment has no hooks object")
    if not isinstance(hooks.get("enabled"), bool):
        raise ZCodeRegistrationError("managed ZCode hooks.enabled must be boolean")
    timeout = hooks.get("timeoutMs")
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise ZCodeRegistrationError("managed ZCode hooks.timeoutMs is invalid")
    events = hooks.get("events")
    if not isinstance(events, dict) or set(events) != set(ZCODE_EVENTS):
        raise ZCodeRegistrationError("managed ZCode fragment has an invalid event set")
    for event in ZCODE_EVENTS:
        registrations = events[event]
        if not isinstance(registrations, list) or len(registrations) != 1:
            raise ZCodeRegistrationError(f"managed ZCode {event} registration is invalid")
        _validate_registration(registrations[0], event)
    return hooks


def _handlers_from_hooks(hooks: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    events = hooks["events"]
    return {event: dict(events[event][0]) for event in ZCODE_EVENTS}


def _state_handlers(state: Mapping[str, Any]) -> dict[str, dict[str, Any]] | None:
    if not state:
        return None
    if state.get("schema_version") != _STATE_SCHEMA_VERSION:
        raise ZCodeRegistrationError("ZCode registration state schema is unsupported")
    if state.get("owner") != "agency-runtime" or state.get("plugin_id") != PLUGIN_ID:
        raise ZCodeRegistrationError("ZCode registration state ownership is invalid")
    for field in ("config_path", "target"):
        value = state.get(field)
        if not isinstance(value, str) or not value or not Path(value).is_absolute():
            raise ZCodeRegistrationError(f"ZCode registration state {field} is invalid")
    handlers = state.get("handlers")
    if not isinstance(handlers, dict) or set(handlers) != set(ZCODE_EVENTS):
        raise ZCodeRegistrationError("ZCode registration state has an invalid event set")
    return {event: _validate_registration(handlers[event], event) for event in ZCODE_EVENTS}


def _config_parts(config: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    hooks_value = config.get("hooks", {})
    if not isinstance(hooks_value, dict):
        raise ZCodeRegistrationError("ZCode config hooks must be an object")
    hooks = dict(hooks_value)
    enabled = hooks.get("enabled")
    if enabled is not None and not isinstance(enabled, bool):
        raise ZCodeRegistrationError("ZCode config hooks.enabled must be boolean")
    timeout = hooks.get("timeoutMs")
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0
    ):
        raise ZCodeRegistrationError("ZCode config hooks.timeoutMs is invalid")
    events_value = hooks.get("events", {})
    if not isinstance(events_value, dict):
        raise ZCodeRegistrationError("ZCode config hooks.events must be an object")
    return hooks, dict(events_value)


def _owned_registrations(events: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    owned = {event: [] for event in ZCODE_EVENTS}
    for configured_event, registrations in events.items():
        if not isinstance(registrations, list):
            raise ZCodeRegistrationError(
                f"ZCode config event {configured_event} registrations must be a list"
            )
        for registration in registrations:
            agency_event = _agency_registration_event(registration)
            if agency_event is None:
                continue
            if agency_event not in owned or agency_event != configured_event:
                raise ZCodeRegistrationError(
                    "Agency ZCode handler is registered under the wrong event"
                )
            owned[agency_event].append(dict(registration))
    return owned


def _registration_facts(
    config: Mapping[str, Any],
    expected: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    hooks, events = _config_parts(config)
    owned = _owned_registrations(events)
    exact = all(owned[event] == [expected[event]] for event in ZCODE_EVENTS)
    any_owned = any(owned[event] for event in ZCODE_EVENTS)
    handler_enabled = all(
        all(handler.get("enabled") is True for handler in expected[event].get("hooks", []))
        for event in ZCODE_EVENTS
    )
    globally_enabled = hooks.get("enabled") is True
    return {
        "registered": exact,
        "enabled": bool(exact and globally_enabled and handler_enabled),
        "global_hooks_enabled": hooks.get("enabled"),
        "drifted": bool(any_owned and not exact),
        "owned_handler_count": sum(len(items) for items in owned.values()),
        "config_path": "",
    }


def inspect_zcode_registration(
    target: Path,
    *,
    home_dir: str | Path | None,
) -> dict[str, Any]:
    config_path = zcode_config_path(home_dir=home_dir)
    state_path = zcode_registration_state_path(home_dir=home_dir)
    config_raw = _read_optional(config_path, limit=_MAX_CONFIG_BYTES, label="ZCode config")
    state_raw = _read_optional(
        state_path,
        limit=_MAX_STATE_BYTES,
        label="ZCode registration state",
    )
    config = _load_object(config_raw, label="ZCode config")
    state = _load_object(state_raw, label="ZCode registration state")
    expected = _state_handlers(state)
    if expected is None and (target / ZCODE_FRAGMENT).is_file():
        expected = _handlers_from_hooks(load_zcode_fragment(target))
    if expected is None:
        facts = {
            "registered": False,
            "enabled": False,
            "global_hooks_enabled": config.get("hooks", {}).get("enabled")
            if isinstance(config.get("hooks"), dict)
            else None,
            "drifted": False,
            "owned_handler_count": 0,
        }
    else:
        facts = _registration_facts(config, expected)
    return {
        **facts,
        "config_path": str(config_path),
        "state_path": str(state_path),
        "version": str(state.get("plugin_version") or PLUGIN_VERSION)
        if state or facts["registered"]
        else None,
    }


def _merged_config(
    config: Mapping[str, Any],
    desired_hooks: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(config)
    hooks, events = _config_parts(config)
    hooks.setdefault("enabled", True)
    hooks.setdefault("timeoutMs", desired_hooks["timeoutMs"])
    for configured_event, registrations in list(events.items()):
        events[configured_event] = [
            registration
            for registration in registrations
            if _agency_registration_event(registration) is None
        ]
    for event in ZCODE_EVENTS:
        registrations = list(events.get(event, []))
        registrations.append(dict(desired_hooks["events"][event][0]))
        events[event] = registrations
    hooks["events"] = events
    merged["hooks"] = hooks
    return merged


def register_zcode_config(
    target: Path,
    *,
    home_dir: str | Path | None,
    force_refresh: bool = False,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    del force_refresh
    config_path = zcode_config_path(home_dir=home_dir)
    state_path = zcode_registration_state_path(home_dir=home_dir)
    config_raw = _read_optional(config_path, limit=_MAX_CONFIG_BYTES, label="ZCode config")
    state_raw = _read_optional(
        state_path,
        limit=_MAX_STATE_BYTES,
        label="ZCode registration state",
    )
    try:
        desired_hooks = load_zcode_fragment(target)
        desired_handlers = _handlers_from_hooks(desired_hooks)
        config = _load_object(config_raw, label="ZCode config")
        state = _load_object(state_raw, label="ZCode registration state")
        prior_handlers = _state_handlers(state)
        if state and (
            Path(str(state["config_path"])).resolve() != config_path
            or Path(str(state["target"])).resolve() != target.resolve()
        ):
            raise ZCodeRegistrationError("ZCode registration state path identity changed")
        _hooks, current_events = _config_parts(config)
        current_owned = _owned_registrations(current_events)
        if prior_handlers is not None:
            prior_facts = _registration_facts(config, prior_handlers)
            if not prior_facts["registered"]:
                raise ZCodeRegistrationError(
                    "Agency-owned ZCode handlers drifted since the last transaction"
                )
        elif any(len(items) > 1 for items in current_owned.values()):
            raise ZCodeRegistrationError("duplicate legacy Agency ZCode handlers require review")

        merged = _merged_config(config, desired_hooks)
        merged_raw = _render(merged)
        new_state = {
            "schema_version": _STATE_SCHEMA_VERSION,
            "owner": "agency-runtime",
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "config_path": str(config_path),
            "target": str(target.resolve()),
            "handlers": desired_handlers,
            "config_digest": hashlib.sha256(merged_raw).hexdigest(),
        }
        new_state_raw = _render(new_state)
        config_changed = merged_raw != config_raw
        state_changed = new_state_raw != state_raw
        written_config = config_raw
        if config_changed:
            written_config = _atomic_json_replace(
                config_path,
                merged,
                expected=config_raw,
                product_owned_parent=False,
                label="ZCode config",
            )
        try:
            if state_changed:
                _atomic_json_replace(
                    state_path,
                    new_state,
                    expected=state_raw,
                    product_owned_parent=True,
                    label="ZCode registration state",
                )
        except Exception:
            if config_changed and written_config is not None:
                _restore_config(config_path, current=written_config, prior=config_raw)
            raise
        facts = _registration_facts(merged, desired_handlers)
        steps = [
            {
                "name": "config_merge",
                "ok": True,
                "changed": config_changed,
                "config_path": str(config_path),
                "preserved_global_hooks_enabled": facts["global_hooks_enabled"],
            },
            {"name": "config_inventory", "ok": facts["registered"], **facts},
        ]
        return steps, bool(facts["registered"]), None if facts["registered"] else "config_inventory"
    except Exception as exc:
        step = {
            "name": "config_merge",
            "ok": False,
            "config_path": str(config_path),
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }
        return (
            [step],
            False,
            "config_drift" if isinstance(exc, ZCodeRegistrationError) else "config_merge",
        )


def toggle_zcode_registration(
    target: Path,
    enabled: bool,
    *,
    home_dir: str | Path | None,
    dry_run: bool = False,
) -> dict[str, Any]:
    config_path = zcode_config_path(home_dir=home_dir)
    state_path = zcode_registration_state_path(home_dir=home_dir)
    config_raw = _read_optional(config_path, limit=_MAX_CONFIG_BYTES, label="ZCode config")
    state_raw = _read_optional(
        state_path,
        limit=_MAX_STATE_BYTES,
        label="ZCode registration state",
    )
    try:
        config = _load_object(config_raw, label="ZCode config")
        state = _load_object(state_raw, label="ZCode registration state")
        handlers = _state_handlers(state)
        if handlers is None:
            raise ZCodeRegistrationError("ZCode has no Agency registration state")
        if (
            Path(str(state["config_path"])).resolve() != config_path
            or Path(str(state["target"])).resolve() != target.resolve()
        ):
            raise ZCodeRegistrationError("ZCode registration state path identity changed")
        facts = _registration_facts(config, handlers)
        if not facts["registered"]:
            raise ZCodeRegistrationError("Agency-owned ZCode handlers are missing or drifted")
        if enabled and facts["global_hooks_enabled"] is not True:
            raise ZCodeRegistrationError(
                "ZCode global hooks are disabled; refusing to enable unrelated user hooks"
            )
        if dry_run:
            return {
                "ok": True,
                "exit_code": 0,
                "dry_run": True,
                "host": "zcode",
                "enabled": enabled,
                "action": "config_enable" if enabled else "config_disable",
                "config_path": str(config_path),
            }
        hooks, events = _config_parts(config)
        updated_handlers: dict[str, dict[str, Any]] = {}
        for event in ZCODE_EVENTS:
            expected = handlers[event]
            registrations = events[event]
            index = registrations.index(expected)
            updated = dict(expected)
            updated["hooks"] = [
                {**dict(handler), "enabled": enabled} for handler in expected["hooks"]
            ]
            registrations[index] = updated
            updated_handlers[event] = updated
        hooks["events"] = events
        merged = {**config, "hooks": hooks}
        new_config_raw = _atomic_json_replace(
            config_path,
            merged,
            expected=config_raw,
            product_owned_parent=False,
            label="ZCode config",
        )
        new_state = {
            **state,
            "handlers": updated_handlers,
            "config_digest": hashlib.sha256(new_config_raw).hexdigest(),
        }
        try:
            _atomic_json_replace(
                state_path,
                new_state,
                expected=state_raw,
                product_owned_parent=True,
                label="ZCode registration state",
            )
        except Exception:
            _restore_config(config_path, current=new_config_raw, prior=config_raw)
            raise
        observed = _registration_facts(merged, updated_handlers)
        postcondition = observed["registered"] and observed["enabled"] is enabled
        return {
            "ok": postcondition,
            "exit_code": 0 if postcondition else 1,
            "host": "zcode",
            "enabled": observed["enabled"] if postcondition else None,
            "action": "enabled"
            if enabled and postcondition
            else "disabled"
            if postcondition
            else "postcondition_mismatch",
            "config_path": str(config_path),
            "postcondition_verified": postcondition,
            "verification_state": "verified" if postcondition else "postcondition_mismatch",
            "partial": not postcondition,
            "restart_required": True,
            "global_hooks_enabled": observed["global_hooks_enabled"],
        }
    except Exception as exc:
        return {
            "ok": False,
            "exit_code": 1,
            "host": "zcode",
            "enabled": None,
            "action": "config_refused",
            "config_path": str(config_path),
            "postcondition_verified": False,
            "verification_state": "config_drift",
            "partial": False,
            "error": f"{type(exc).__name__}: {exc}"[:500],
            "restart_required": False,
        }
