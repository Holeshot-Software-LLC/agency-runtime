"""Transactional OpenClaw final-only delivery configuration.

Agency's terminal hook can authorize only a complete response.  OpenClaw's
native preview and block-streaming paths therefore have to be disabled before
the plugin is enabled.  This module deliberately treats the OpenClaw CLI as
the sole config writer; it never reads or rewrites ``openclaw.json`` directly.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.configuration_persistence import (
    atomic_write_yaml,
    config_lock,
    ensure_config_parent,
    is_link_or_reparse_point,
    read_document,
    restrict_permissions,
)
from agency_runtime.core.installer_contracts import NativeCommandResult

BACKUP_SCHEMA_VERSION = 2
BACKUP_ROOT = Path("openclaw") / "config-identities"
BACKUP_FILENAME = "final-only-streaming-backup.yaml"
_MAX_CONFIG_SNAPSHOT_BYTES = 256 * 1024
_SAFE_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

# These bundled channels expose a preview mode as well as the common block
# delivery override.  QQ Bot exposes only its provider-native preview mode.
# Other configured channels still get any streaming leaves they explicitly
# expose plus the global block-streaming default.
_PREVIEW_AND_BLOCK_CHANNELS = frozenset(
    {"discord", "feishu", "matrix", "mattermost", "msteams", "slack", "telegram"}
)
_MODE_ONLY_CHANNELS = frozenset({"qqbot"})
_BLOCK_ONLY_CHANNELS = frozenset({"googlechat", "imessage", "signal", "whatsapp"})
_RESERVED_CHANNEL_KEYS = frozenset({"defaults", "modelByChannel"})

PathParts = tuple[str, ...]
RunCommand = Callable[[str, Sequence[str]], NativeCommandResult]


def _environment_value(
    name: str,
    environment: Mapping[str, str] | None = None,
) -> str | None:
    value = (os.environ if environment is None else environment).get(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _normalized_path(value: str | Path) -> str:
    return os.path.normcase(os.path.abspath(os.path.expanduser(str(value))))


def _effective_config_identity(environment: Mapping[str, str] | None = None) -> str:
    """Hash the effective profile, state directory, and config file identity."""

    openclaw_home = _normalized_path(
        _environment_value("OPENCLAW_HOME", environment) or Path.home()
    )
    profile = _environment_value("OPENCLAW_PROFILE", environment) or "default"
    default_state = Path(openclaw_home) / (
        ".openclaw" if profile == "default" else f".openclaw-{profile}"
    )
    state_dir = _normalized_path(
        _environment_value("OPENCLAW_STATE_DIR", environment) or default_state
    )
    config_path = _normalized_path(
        _environment_value("OPENCLAW_CONFIG_PATH", environment) or Path(state_dir) / "openclaw.json"
    )
    identity = {
        "profile": profile,
        "state_dir": state_dir,
        "config_path": config_path,
    }
    return hashlib.sha256(_canonical(identity)).hexdigest()


def backup_path(runtime_home: Path, *, config_identity: str | None = None) -> Path:
    """Return the owner-private, config-identity-bound backup path."""

    identity = config_identity or _effective_config_identity()
    if not _SHA256.fullmatch(identity):
        raise ValueError("OpenClaw config identity is invalid")
    return runtime_home / BACKUP_ROOT / identity / BACKUP_FILENAME


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(document: Mapping[str, Any]) -> str:
    body = {key: value for key, value in document.items() if key != "sha256"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def _validate_entries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 10_000:
        raise ValueError("OpenClaw streaming backup entries are invalid")
    normalized: list[dict[str, Any]] = []
    seen: set[PathParts] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {"path", "present", "value"}:
            raise ValueError("OpenClaw streaming backup entry is invalid")
        path = raw.get("path")
        present = raw.get("present")
        entry_value = raw.get("value")
        if (
            not isinstance(path, list)
            or not path
            or len(path) > 12
            or any(not isinstance(part, str) or not part or len(part) > 512 for part in path)
        ):
            raise ValueError("OpenClaw streaming backup path is invalid")
        parts = tuple(path)
        if parts in seen or parts[-1] not in {"blockStreamingDefault", "mode", "enabled"}:
            raise ValueError("OpenClaw streaming backup path is not an owned streaming leaf")
        if not isinstance(present, bool):
            raise ValueError("OpenClaw streaming backup presence flag is invalid")
        if present and not isinstance(entry_value, (bool, str)):
            raise ValueError("OpenClaw streaming backup value is invalid")
        if not present and entry_value is not None:
            raise ValueError("OpenClaw streaming backup absent value must be null")
        seen.add(parts)
        normalized.append({"path": list(parts), "present": present, "value": entry_value})
    return normalized


def _validate_containers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 20_000:
        raise ValueError("OpenClaw streaming backup containers are invalid")
    normalized: list[dict[str, Any]] = []
    seen: set[PathParts] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != {"path", "present"}:
            raise ValueError("OpenClaw streaming backup container is invalid")
        path = raw.get("path")
        present = raw.get("present")
        if (
            not isinstance(path, list)
            or not path
            or len(path) > 11
            or any(not isinstance(part, str) or not part or len(part) > 512 for part in path)
        ):
            raise ValueError("OpenClaw streaming backup container path is invalid")
        parts = tuple(path)
        if (
            parts in seen
            or parts[-1] not in {"streaming", "block"}
            or not isinstance(present, bool)
        ):
            raise ValueError("OpenClaw streaming backup container is invalid")
        seen.add(parts)
        normalized.append({"path": list(parts), "present": present})
    return normalized


def _validate_backup(
    document: Mapping[str, Any],
    *,
    config_identity: str | None = None,
) -> dict[str, Any]:
    allowed = {
        "schema_version",
        "kind",
        "config_identity",
        "created_at",
        "updated_at",
        "entries",
        "containers",
        "sha256",
    }
    if set(document) != allowed:
        raise ValueError("OpenClaw streaming backup has an invalid schema")
    if document.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise ValueError("OpenClaw streaming backup version is unsupported")
    if document.get("kind") != "openclaw-final-only-streaming-values":
        raise ValueError("OpenClaw streaming backup kind is invalid")
    stored_identity = document.get("config_identity")
    if not isinstance(stored_identity, str) or not _SHA256.fullmatch(stored_identity):
        raise ValueError("OpenClaw streaming backup config identity is invalid")
    if config_identity is not None and stored_identity != config_identity:
        raise ValueError("OpenClaw streaming backup belongs to a different config identity")
    if not isinstance(document.get("created_at"), str) or not isinstance(
        document.get("updated_at"), str
    ):
        raise ValueError("OpenClaw streaming backup timestamp is invalid")
    normalized = _validate_entries(document.get("entries"))
    normalized_containers = _validate_containers(document.get("containers"))
    if not isinstance(document.get("sha256"), str) or document["sha256"] != _digest(document):
        raise ValueError("OpenClaw streaming backup integrity check failed")
    return {
        **dict(document),
        "entries": normalized,
        "containers": normalized_containers,
    }


def _read_backup(path: Path, *, config_identity: str | None = None) -> dict[str, Any] | None:
    if not path.exists():
        return None
    if is_link_or_reparse_point(path):
        raise ValueError("refusing OpenClaw streaming backup symlink or reparse point")
    document, _raw = read_document(path)
    return _validate_backup(document, config_identity=config_identity)


def _write_backup(
    path: Path,
    document: Mapping[str, Any],
    *,
    config_identity: str,
) -> None:
    validated = _validate_backup(document, config_identity=config_identity)
    atomic_write_yaml(
        path,
        validated,
        ensure_parent=ensure_config_parent,
        restrict=restrict_permissions,
        preflight=lambda candidate: _validate_backup(
            read_document(candidate)[0],
            config_identity=config_identity,
        ),
    )


def _parse_snapshot(result: NativeCommandResult, label: str) -> dict[str, Any]:
    if not result.ok:
        raise ValueError(f"OpenClaw {label} config inspection failed")
    try:
        value = safe_load_bounded_json(
            result.stdout,
            maximum_bytes=_MAX_CONFIG_SNAPSHOT_BYTES,
            maximum_depth=64,
            maximum_nodes=50_000,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"OpenClaw {label} config inspection was not bounded JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"OpenClaw {label} config inspection was not an object")
    return value


def _snapshot(run: RunCommand, phase: str) -> dict[str, Any]:
    agents = run(
        f"streaming_config_{phase}_agents",
        ["openclaw", "config", "get", "agents.defaults", "--json"],
    )
    channels = run(
        f"streaming_config_{phase}_channels",
        ["openclaw", "config", "get", "channels", "--json"],
    )
    return {
        "agents": {"defaults": _parse_snapshot(agents, "agents.defaults")},
        "channels": _parse_snapshot(channels, "channels"),
    }


def _lookup(root: Mapping[str, Any], path: PathParts) -> tuple[bool, Any]:
    value: Any = root
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _streaming_mapping(value: Any, label: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(
            f"OpenClaw {label} uses a legacy streaming shape; "
            "run 'openclaw doctor --fix' before installing Agency Runtime"
        )
    return value


def _channel_bases(channel_id: str, raw_channel: Mapping[str, Any]) -> list[PathParts]:
    bases: list[PathParts] = [("channels", channel_id)]
    accounts = raw_channel.get("accounts")
    if accounts is None:
        return bases
    if not isinstance(accounts, Mapping):
        raise ValueError(f"OpenClaw channel {channel_id!r} accounts config is invalid")
    for account_id, account in accounts.items():
        if not isinstance(account_id, str) or not account_id:
            raise ValueError(f"OpenClaw channel {channel_id!r} account id is invalid")
        if account is not None and not isinstance(account, Mapping):
            raise ValueError(f"OpenClaw channel {channel_id!r} account {account_id!r} is invalid")
        _streaming_mapping(
            account.get("streaming") if isinstance(account, Mapping) else None,
            f"channel {channel_id!r} account {account_id!r}",
        )
        bases.append(("channels", channel_id, "accounts", account_id))
    return bases


def _streaming_paths(snapshot: Mapping[str, Any]) -> dict[PathParts, Any]:
    desired: dict[PathParts, Any] = {("agents", "defaults", "blockStreamingDefault"): "off"}
    channels = snapshot.get("channels")
    if not isinstance(channels, Mapping):
        raise ValueError("OpenClaw channels config is invalid")
    for channel_id, raw_channel in channels.items():
        if channel_id in _RESERVED_CHANNEL_KEYS:
            continue
        if not isinstance(channel_id, str) or not channel_id:
            raise ValueError("OpenClaw channel id is invalid")
        if raw_channel is None:
            raw_channel = {}
        if not isinstance(raw_channel, Mapping):
            raise ValueError(f"OpenClaw channel {channel_id!r} config is invalid")
        preview = channel_id in _PREVIEW_AND_BLOCK_CHANNELS | _MODE_ONLY_CHANNELS
        block = channel_id in _PREVIEW_AND_BLOCK_CHANNELS | _BLOCK_ONLY_CHANNELS
        streaming = _streaming_mapping(
            raw_channel.get("streaming"),
            f"channel {channel_id!r}",
        )
        if streaming is not None:
            preview = preview or "mode" in streaming
            block = block or "block" in streaming
        for base in _channel_bases(channel_id, raw_channel):
            if preview:
                desired[(*base, "streaming", "mode")] = "off"
            if block:
                desired[(*base, "streaming", "block", "enabled")] = False
    return desired


def _render_path(path: PathParts) -> str:
    rendered = path[0]
    for part in path[1:]:
        rendered += f".{part}" if _SAFE_SEGMENT.fullmatch(part) else f"[{json.dumps(part)}]"
    return rendered


def _set_command(path: PathParts, value: Any) -> list[str]:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return ["openclaw", "config", "set", _render_path(path), encoded, "--strict-json"]


def _restore_command(entry: Mapping[str, Any]) -> list[str]:
    path = tuple(str(part) for part in entry["path"])
    if entry["present"]:
        return _set_command(path, entry["value"])
    return ["openclaw", "config", "unset", _render_path(path)]


def _backup_with_current(
    existing: Mapping[str, Any] | None,
    snapshot: Mapping[str, Any],
    desired: Mapping[PathParts, Any],
    *,
    config_identity: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    changed = existing is None
    prior = {
        tuple(str(part) for part in entry["path"]): dict(entry)
        for entry in (existing or {}).get("entries", [])
    }
    containers = {
        tuple(str(part) for part in item["path"]): dict(item)
        for item in (existing or {}).get("containers", [])
    }
    for path in desired:
        if path not in prior:
            changed = True
            present, value = _lookup(snapshot, path)
            if present and not isinstance(value, (bool, str)):
                raise ValueError(f"OpenClaw streaming value at {_render_path(path)!r} is invalid")
            prior[path] = {
                "path": list(path),
                "present": present,
                "value": value if present else None,
            }
        for container in (path[:-1], path[:-2]):
            if container[-1] not in {"streaming", "block"} or container in containers:
                continue
            changed = True
            container_present, _value = _lookup(snapshot, container)
            containers[container] = {
                "path": list(container),
                "present": container_present,
            }
    if existing is not None and not changed:
        return _validate_backup(existing, config_identity=config_identity)
    document: dict[str, Any] = {
        "schema_version": BACKUP_SCHEMA_VERSION,
        "kind": "openclaw-final-only-streaming-values",
        "config_identity": config_identity,
        "created_at": (existing or {}).get("created_at", now),
        "updated_at": now,
        "entries": [prior[path] for path in sorted(prior)],
        "containers": [containers[path] for path in sorted(containers)],
    }
    document["sha256"] = _digest(document)
    return _validate_backup(document, config_identity=config_identity)


def _matches(
    snapshot: Mapping[str, Any],
    expected: Mapping[PathParts, Any],
) -> bool:
    return all(_lookup(snapshot, path) == (True, value) for path, value in expected.items())


def _prior_expected(
    entries: Mapping[PathParts, Mapping[str, Any]],
    paths: Sequence[PathParts],
) -> tuple[dict[PathParts, Any], list[PathParts]]:
    present: dict[PathParts, Any] = {}
    absent: list[PathParts] = []
    for path in paths:
        entry = entries[path]
        if entry["present"]:
            present[path] = entry["value"]
        else:
            absent.append(path)
    return present, absent


def _rollback_matches(
    snapshot: Mapping[str, Any],
    entries: Mapping[PathParts, Mapping[str, Any]],
    containers: Mapping[PathParts, Mapping[str, Any]],
    paths: Sequence[PathParts],
) -> bool:
    present, absent = _prior_expected(entries, paths)
    absent_containers = {
        container
        for container, entry in containers.items()
        if not entry["present"] and any(path[: len(container)] == container for path in paths)
    }
    return (
        _matches(snapshot, present)
        and all(not _lookup(snapshot, path)[0] for path in absent)
        and all(not _lookup(snapshot, path)[0] for path in absent_containers)
    )


def _recovery(path: Path, *, rollback_ok: bool) -> str:
    if rollback_ok:
        return (
            "OpenClaw rejected or could not verify an owned config write. If the config is "
            "Nix-managed or immutable, declare agents.defaults.blockStreamingDefault=off and "
            "each configured channel/account streaming.mode=off and "
            "streaming.block.enabled=false in its source, apply it while the gateway is stopped, "
            f"verify with 'openclaw config get ... --json', then rerun. Prior values are retained at {path}."
        )
    return (
        "OpenClaw streaming rollback could not be proven. Keep the gateway stopped. Restore the "
        f"values-only entries in {path} with 'openclaw config set/unset', verify both config "
        "sections, and rerun installation."
    )


def enforce_final_only_delivery(
    run: RunCommand,
    *,
    runtime_home: Path,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Apply and verify final-only delivery, rolling back on any failed write.

    The caller must already have proven that the OpenClaw gateway is stopped.
    Returned metadata is safe to expose: it contains paths and counts, never a
    config snapshot or prior values.
    """

    config_identity = _effective_config_identity(environment)
    path = backup_path(runtime_home, config_identity=config_identity)
    try:
        with config_lock(
            path,
            ensure_parent=ensure_config_parent,
            restrict=restrict_permissions,
        ):
            before = _snapshot(run, "before")
            desired = _streaming_paths(before)
            existing = _read_backup(path, config_identity=config_identity)
            backup = _backup_with_current(
                existing,
                before,
                desired,
                config_identity=config_identity,
            )
            if backup != existing:
                _write_backup(path, backup, config_identity=config_identity)
            entries = {
                tuple(str(part) for part in entry["path"]): entry for entry in backup["entries"]
            }
            containers = {
                tuple(str(part) for part in item["path"]): item for item in backup["containers"]
            }
            attempted: list[PathParts] = []
            failed_result: NativeCommandResult | None = None
            for index, (owned_path, value) in enumerate(desired.items(), start=1):
                if _lookup(before, owned_path) == (True, value):
                    continue
                attempted.append(owned_path)
                result = run(
                    f"streaming_config_set_{index}",
                    _set_command(owned_path, value),
                )
                if not result.ok:
                    failed_result = result
                    break
            after: dict[str, Any] | None = None
            if failed_result is None:
                try:
                    after = _snapshot(run, "after")
                except ValueError:
                    after = None
                if after is not None and _matches(after, desired):
                    return {
                        "ok": True,
                        "changed": len(attempted),
                        "managed_paths": len(desired),
                        "backup_path": str(path),
                        "backup_retained": True,
                        "idempotent": not attempted,
                        "rollback_attempted": False,
                        "rollback_verified": None,
                        "recovery": (
                            "The values-only backup remains retained. Native disable/enable does "
                            "not restore it automatically because those paths do not prove the "
                            "gateway is stopped."
                        ),
                    }
            rollback_paths = list(reversed(attempted))
            for index, owned_path in enumerate(rollback_paths, start=1):
                run(
                    f"streaming_config_rollback_{index}",
                    _restore_command(entries[owned_path]),
                )
            cleanup = sorted(
                (
                    container
                    for container, entry in containers.items()
                    if not entry["present"]
                    and any(path[: len(container)] == container for path in attempted)
                ),
                key=len,
                reverse=True,
            )
            for index, container in enumerate(cleanup, start=1):
                run(
                    f"streaming_config_rollback_container_{index}",
                    ["openclaw", "config", "unset", _render_path(container)],
                )
            try:
                rolled_back = _snapshot(run, "rollback")
            except ValueError:
                rolled_back = None
            rollback_ok = rolled_back is not None and _rollback_matches(
                rolled_back,
                entries,
                containers,
                attempted,
            )
            detail = (
                "OpenClaw final-only config write failed"
                if failed_result is not None
                else "postcondition verification failed"
            )
            return {
                "ok": False,
                "changed": len(attempted),
                "managed_paths": len(desired),
                "backup_path": str(path),
                "backup_retained": True,
                "idempotent": False,
                "rollback_attempted": bool(attempted),
                "rollback_verified": rollback_ok,
                "error": detail,
                "recovery": _recovery(path, rollback_ok=rollback_ok),
            }
    except Exception as exc:
        return {
            "ok": False,
            "changed": 0,
            "managed_paths": 0,
            "backup_path": str(path),
            "backup_retained": path.is_file(),
            "idempotent": False,
            "rollback_attempted": False,
            "rollback_verified": None,
            "error": f"{type(exc).__name__}: {exc}",
            "recovery": _recovery(path, rollback_ok=True),
        }


def _compensate_final_only(
    run: RunCommand,
    desired: Mapping[PathParts, Any],
) -> bool:
    commands_ok = True
    for index, (target, value) in enumerate(desired.items(), start=1):
        result = run(
            f"streaming_config_restore_compensate_{index}",
            _set_command(target, value),
        )
        commands_ok = result.ok and commands_ok
    try:
        compensated = _snapshot(run, "restore_compensate")
    except ValueError:
        compensated = None
    return bool(commands_ok and compensated is not None and _matches(compensated, desired))


def restore_prior_delivery(
    run: RunCommand,
    *,
    runtime_home: Path,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Restore backed-up streaming values or re-establish final-only safety.

    The caller must prove both that the gateway is stopped and that the Agency
    plugin is disabled or absent.  A failed restore is compensated by
    reapplying the final-only policy before returning.
    """

    config_identity = _effective_config_identity(environment)
    path = backup_path(runtime_home, config_identity=config_identity)
    try:
        with config_lock(
            path,
            ensure_parent=ensure_config_parent,
            restrict=restrict_permissions,
        ):
            backup = _read_backup(path, config_identity=config_identity)
            if backup is None:
                raise ValueError("OpenClaw streaming backup is missing")
            current = _snapshot(run, "restore_before")
            desired_final = _streaming_paths(current)
            entries = {
                tuple(str(part) for part in entry["path"]): entry for entry in backup["entries"]
            }
            containers = {
                tuple(str(part) for part in item["path"]): item for item in backup["containers"]
            }
            targets = list(desired_final)
            if any(target not in entries for target in targets):
                raise ValueError("OpenClaw streaming backup does not cover the active policy")
            restore_failed = False
            changed = 0
            for index, target in enumerate(reversed(targets), start=1):
                entry = entries[target]
                present, value = _lookup(current, target)
                if (present, value if present else None) == (
                    entry["present"],
                    entry["value"],
                ):
                    continue
                changed += 1
                result = run(
                    f"streaming_config_restore_{index}",
                    _restore_command(entry),
                )
                if not result.ok:
                    restore_failed = True
                    break
            cleanup = sorted(
                (
                    container
                    for container, entry in containers.items()
                    if not entry["present"]
                    and any(target[: len(container)] == container for target in targets)
                ),
                key=len,
                reverse=True,
            )
            if not restore_failed:
                for index, container in enumerate(cleanup, start=1):
                    if not _lookup(current, container)[0]:
                        continue
                    result = run(
                        f"streaming_config_restore_container_{index}",
                        ["openclaw", "config", "unset", _render_path(container)],
                    )
                    if not result.ok:
                        restore_failed = True
                        break
            restored: dict[str, Any] | None = None
            if not restore_failed:
                try:
                    restored = _snapshot(run, "restore_after")
                except ValueError:
                    restored = None
                if restored is not None and _rollback_matches(
                    restored,
                    entries,
                    containers,
                    targets,
                ):
                    return {
                        "ok": True,
                        "restored": True,
                        "changed": changed,
                        "backup_path": str(path),
                        "backup_retained": True,
                        "final_only_reapplied": False,
                        "recovery": "Prior OpenClaw streaming values were restored and verified.",
                    }
            reapply_ok = _compensate_final_only(run, desired_final)
            return {
                "ok": False,
                "restored": False,
                "changed": changed,
                "backup_path": str(path),
                "backup_retained": True,
                "final_only_reapplied": reapply_ok,
                "error": "OpenClaw prior streaming values could not be restored and verified",
                "recovery": (
                    "Final-only delivery was re-established. Keep the gateway stopped and retry "
                    f"the values-only restore from {path}."
                    if reapply_ok
                    else "Neither prior-value restoration nor final-only compensation was proven. "
                    f"Keep the gateway stopped and recover from {path}."
                ),
            }
    except Exception as exc:
        return {
            "ok": False,
            "restored": False,
            "changed": 0,
            "backup_path": str(path),
            "backup_retained": path.is_file(),
            "final_only_reapplied": None,
            "error": f"{type(exc).__name__}: {exc}",
            "recovery": (
                "Keep the gateway stopped. Repair or restore the values-only OpenClaw streaming "
                f"backup at {path}, then retry."
            ),
        }


def retained_backup_status(
    *,
    runtime_home: Path,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Describe safe lifecycle behavior without exposing backed-up values."""

    config_identity = _effective_config_identity(environment)
    path = backup_path(runtime_home, config_identity=config_identity)
    state = "missing"
    try:
        retained = _read_backup(path, config_identity=config_identity) is not None
        if retained:
            state = "valid"
    except (OSError, ValueError):
        retained = False
        state = "invalid"
    return {
        "backup_path": str(path),
        "backup_retained": retained,
        "backup_state": state,
        "automatic_restore": False,
        "recovery": (
            "Agency keeps final-only delivery applied across native disable/enable. To restore "
            "pre-install streaming values, stop the gateway and apply the values-only backup "
            "with OpenClaw config set/unset commands."
            if retained
            else "Stop the gateway and rerun native Agency installation to establish final-only delivery."
        ),
    }
