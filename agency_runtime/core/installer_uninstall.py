"""Ownership-bound native host uninstallation and reversible bundle retirement."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.installer_contracts import (
    HOSTS,
    MARKETPLACE_ID,
    PLUGIN_ID,
    BinaryResolver,
    CommandRunner,
    NativeCommandResult,
)
from agency_runtime.core.private_paths import (
    ensure_private_directory,
    validate_private_directory,
)
from agency_runtime.core.store.security import metadata_is_link_or_reparse_point

_SCHEMA_VERSION = "agency.host-uninstall.v1"
_BINDING_SCHEMA_VERSION = "agency.host-uninstall-binding.v1"


class UninstallRetirementError(RuntimeError):
    """A retired bundle needs an explicit recovery path after a failed move check."""

    def __init__(self, message: str, *, retained_path: Path | None = None) -> None:
        super().__init__(message)
        self.retained_path = str(retained_path) if retained_path is not None else None


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _directory_binding(path: Path, *, label: str) -> dict[str, Any]:
    metadata = os.lstat(path)
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise PermissionError(f"{label} is not a real directory")
    return {
        "path": str(path.resolve()),
        "device": int(metadata.st_dev),
        "inode": int(getattr(metadata, "st_ino", 0) or 0),
    }


def _prospective_directory_binding(path: Path, *, root: Path, label: str) -> dict[str, Any]:
    """Bind the nearest real ancestor plus the exact missing directory suffix."""

    target = path.resolve()
    root = root.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PermissionError(f"{label} is outside Agency runtime state") from exc
    current = target
    missing: list[str] = []
    while True:
        try:
            os.lstat(current)
            break
        except FileNotFoundError as exc:
            if current == root:
                raise PermissionError(f"{label} has no existing trusted ancestor") from exc
            missing.append(current.name)
            current = current.parent
    return {
        "path": str(target),
        "existing_parent": _directory_binding(current, label=label),
        "missing_suffix": list(reversed(missing)),
    }


def _facade():
    """Resolve facade dependencies at call time for compatibility and tests."""

    from agency_runtime.core import installer

    return installer


def _dispatch(name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(_facade(), name)(*args, **kwargs)


def _bounded_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}".replace("\n", " ").replace("\r", " ")[:500]


def _recovery_command(host: str, retained_path: str) -> str:
    argv = [
        "agency",
        "install",
        "--rollback",
        "--agent",
        host,
        "--backup",
        retained_path,
    ]
    if os.name != "nt":
        return shlex.join(argv)

    # Recovery is displayed for an attended PowerShell session.  Python's
    # list2cmdline targets CreateProcess/CommandLineToArgvW rather than a shell,
    # so characters such as ``&`` can otherwise be interpreted as operators.
    def _powershell_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    return "& " + " ".join(_powershell_literal(value) for value in argv)


def _safe_native_step(
    name: str,
    result: NativeCommandResult,
    **extra: Any,
) -> dict[str, Any]:
    """Expose useful command telemetry without native stdout or stderr content."""

    executable = Path(result.command[0]).name if result.command else ""
    step = {
        "name": name,
        "command": [executable, *result.command[1:]],
        "returncode": result.returncode,
        "ok": result.ok,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
        **extra,
    }
    if not result.ok:
        step["error"] = "native command failed"
    return step


def _prepared_launcher(
    command: list[str],
    *,
    runtime_root: Path,
    forbidden_roots: tuple[Path, ...],
):
    """Freeze every artifact that can participate in the actual host launch."""

    from agency_runtime.core.process_argv import prepare_process_argv

    prepared = prepare_process_argv(
        command,
        current_directory=runtime_root,
        forbidden_roots=forbidden_roots,
    )
    prepared.freeze_persistent(
        platform_name=os.name,
        forbidden_roots=forbidden_roots,
    )
    identities = prepared.persistent_artifact_identities
    if not identities or prepared.frozen_launcher is None:
        raise PermissionError("Native host launcher identity is unavailable")
    projection = {
        "platform": prepared.frozen_platform,
        "launcher": list(prepared.frozen_launcher),
        "artifact_paths": list(prepared.artifact_paths),
        "artifacts": [identity.manifest() for identity in identities],
    }
    return prepared, projection


def _host_command_forbidden_roots(runtime_root: Path) -> tuple[Path, ...]:
    """Exclude the ambient repository from every bound host command."""

    from agency_runtime.core.process_argv import repository_forbidden_roots

    return tuple(
        dict.fromkeys(
            (
                *repository_forbidden_roots(runtime_root),
                *repository_forbidden_roots(Path.cwd(), include_current=False),
            )
        )
    )


def _optional_file_binding(path: Path, *, limit: int, label: str) -> dict[str, Any]:
    try:
        payload = read_bounded_regular_file(path, limit=limit, label=label)
    except FileNotFoundError:
        return {"path": str(path), "present": False}
    metadata = os.lstat(path)
    return {
        "path": str(path),
        "present": True,
        "device": int(metadata.st_dev),
        "inode": int(getattr(metadata, "st_ino", 0) or 0),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _unknown_host(host: str) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "ok": False,
        "complete": False,
        "exit_code": 2,
        "host": host,
        "status": "unknown_host",
        "changed": False,
        "error": f"Unknown host: {host}. Supported: {', '.join(HOSTS)}",
    }


def _owned_target_state(host: str, target: Path) -> dict[str, Any]:
    """Prove that one real directory carries this host's exact ownership marker."""

    try:
        metadata = os.lstat(target)
    except FileNotFoundError:
        return {
            "present": False,
            "owned": False,
            "plugin_version": None,
            "error": None,
        }
    except OSError as exc:
        return {
            "present": True,
            "owned": False,
            "plugin_version": None,
            "error": _bounded_error(exc),
        }
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        return {
            "present": True,
            "owned": False,
            "plugin_version": None,
            "error": "Managed target is not a real directory",
        }
    valid, error, manifest = _dispatch(
        "_validate_owned_install_tree",
        target,
        host=host,
        target=target,
    )
    _version, managed_install_id, bundle_digest = _dispatch(
        "_managed_bundle_identity",
        target,
        host,
    )
    if valid and managed_install_id != manifest.get("install_id"):
        valid = False
        error = "Managed bundle identity does not match its ownership manifest"
    return {
        "present": True,
        "owned": bool(valid),
        "plugin_version": manifest.get("plugin_version") if manifest else None,
        "install_id": manifest.get("install_id") if manifest else None,
        "bundle_digest": bundle_digest if valid else None,
        "error": error,
    }


def _same_real_directory(metadata: os.stat_result, expected: os.stat_result) -> bool:
    return bool(
        not metadata_is_link_or_reparse_point(metadata)
        and stat.S_ISDIR(metadata.st_mode)
        and int(metadata.st_dev) == int(expected.st_dev)
        and int(getattr(metadata, "st_ino", 0) or 0) == int(getattr(expected, "st_ino", 0) or 0)
    )


def _validated_retained_path(backup_root: Path, retained_path: Path) -> Path:
    import uuid

    retained = retained_path.resolve()
    if retained.parent != backup_root or not retained.name.startswith("uninstall-"):
        raise PermissionError("Retained bundle destination is outside the managed rollback root")
    try:
        operation_id = retained.name.removeprefix("uninstall-")
        if str(uuid.UUID(operation_id)) != operation_id:
            raise ValueError
    except (AttributeError, ValueError) as exc:
        raise PermissionError("Retained bundle destination has an invalid operation ID") from exc
    try:
        os.lstat(retained)
    except FileNotFoundError:
        return retained
    raise FileExistsError("Retained bundle destination already exists")


def _verify_retained_identity(
    retained: Path,
    target: Path,
    *,
    before: os.stat_result,
) -> None:
    try:
        if not _same_real_directory(os.lstat(retained), before):
            raise PermissionError("Retained bundle identity changed during retirement")
    except BaseException as exc:
        if retained.exists() and not target.exists():
            try:
                os.replace(retained, target)
            except OSError as restore_exc:
                raise UninstallRetirementError(
                    "Retained bundle identity check failed and automatic restoration failed",
                    retained_path=retained if retained.exists() else None,
                ) from restore_exc
        if retained.exists():
            raise UninstallRetirementError(
                "Retained bundle identity check failed; use the reported retained path",
                retained_path=retained,
            ) from exc
        raise


def _retire_owned_target(
    host: str,
    target: Path,
    *,
    home_dir: str | Path | None,
    expected_install_id: str,
    expected_bundle_digest: str,
    expected_retention_binding: Mapping[str, Any],
    retained_path: Path,
) -> dict[str, Any]:
    """Atomically move one still-owned bundle into the managed rollback root."""

    ownership = _owned_target_state(host, target)
    if not ownership["owned"]:
        raise PermissionError(ownership["error"] or "Managed target ownership is unproven")
    if (
        ownership["install_id"] != expected_install_id
        or ownership["bundle_digest"] != expected_bundle_digest
    ):
        raise PermissionError("Managed target identity changed before retirement")
    validate_private_directory(target)
    before = os.lstat(target)
    runtime_root = _dispatch("_runtime_home", home_dir=home_dir).resolve()
    requested_backup_root = (runtime_root / "backups" / host).resolve()
    observed_retention_binding = _prospective_directory_binding(
        requested_backup_root,
        root=runtime_root,
        label="managed uninstall retention root",
    )
    if observed_retention_binding != dict(expected_retention_binding):
        raise PermissionError("Managed uninstall retention root changed after planning")
    backup_root = ensure_private_directory(
        requested_backup_root,
        product_owned=True,
    )
    backup_identity = _directory_binding(
        backup_root,
        label="managed uninstall retention root",
    )
    retained = _validated_retained_path(backup_root, retained_path)

    def validate_final_target() -> None:
        current_ownership = _owned_target_state(host, target)
        if (
            not current_ownership["owned"]
            or current_ownership["install_id"] != expected_install_id
            or current_ownership["bundle_digest"] != expected_bundle_digest
        ):
            raise PermissionError("Managed target identity changed before retirement")
        validate_private_directory(target)

    if os.name == "nt":
        from agency_runtime.core.windows_handle_rename import (
            WindowsHandleRenameError,
            rename_directory_handle_bound,
        )

        try:
            rename_directory_handle_bound(
                target,
                retained,
                expected_device=int(before.st_dev),
                expected_inode=int(getattr(before, "st_ino", 0) or 0),
                expected_destination_device=int(backup_identity["device"]),
                expected_destination_inode=int(backup_identity["inode"]),
                validate=validate_final_target,
            )
        except WindowsHandleRenameError as exc:
            if retained.exists():
                raise UninstallRetirementError(
                    "Handle-bound retirement failed; use the reported retained path",
                    retained_path=retained,
                ) from exc
            raise
    else:
        validate_final_target()
        current = os.lstat(target)
        if not _same_real_directory(current, before):
            raise PermissionError("Managed target identity changed before retirement")
        os.replace(target, retained)
    if os.name != "nt":
        _verify_retained_identity(retained, target, before=before)
    return {
        "target": str(target),
        "retained_path": str(retained),
        "plugin_version": ownership["plugin_version"],
        "previous_install_id": ownership["install_id"],
    }


def _canonical_local_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 4096:
        return None
    text = value
    if os.name == "nt" and text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[8:]
    elif os.name == "nt" and text.startswith("\\\\?\\"):
        text = text[4:]
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        return None
    try:
        return candidate.resolve()
    except (OSError, RuntimeError):
        return None


def _walk_objects(value: Any) -> list[dict[str, Any]]:
    return _dispatch("_walk_objects", value)


def _marketplace_records(value: Any) -> list[dict[str, Any]]:
    return [
        item
        for item in _walk_objects(value)
        if str(item.get("name") or item.get("marketplace") or item.get("id") or "").casefold()
        == MARKETPLACE_ID
    ]


def _plugin_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    for item in _walk_objects(value):
        identity = str(
            item.get("pluginId")
            or item.get("id")
            or item.get("name")
            or item.get("plugin")
            or item.get("pluginName")
            or ""
        ).casefold()
        if identity in {PLUGIN_ID, selector}:
            records.append(item)
    return records


def _direct_record_paths(record: Mapping[str, Any]) -> set[Path] | None:
    """Read only documented path fields from one exact native record."""

    values: list[object] = [record[key] for key in ("root", "path", "directory") if key in record]
    source = record.get("source")
    if isinstance(source, Mapping):
        values.extend(source[key] for key in ("path", "root") if key in source)
        # Codex/Claude use source="local" as a discriminator when a path is
        # also present.  A lone source value is path-bearing and must parse.
        if "source" in source and not any(key in source for key in ("path", "root")):
            values.append(source["source"])
    elif "source" in record:
        if source == "local" and any(key in record for key in ("root", "path", "directory")):
            pass
        else:
            values.append(source)
    marketplace_source = record.get("marketplaceSource")
    if isinstance(marketplace_source, Mapping):
        values.extend(
            marketplace_source[key]
            for key in ("path", "source", "root")
            if key in marketplace_source
        )
    elif "marketplaceSource" in record:
        values.append(marketplace_source)
    paths: set[Path] = set()
    for value in values:
        parsed = _canonical_local_path(value)
        if parsed is None:
            return None
        paths.add(parsed)
    return paths


def _marketplace_is_bound(record: Mapping[str, Any], target: Path) -> bool:
    # A native record with one expected alias and one conflicting alias is
    # ambiguous, not partially trustworthy.
    return _direct_record_paths(record) == {target.resolve()}


def _plugin_is_bound(
    host: str,
    record: Mapping[str, Any],
    target: Path,
) -> bool:
    paths = _direct_record_paths(record)
    if paths is None:
        return False
    root = target.resolve()
    if host == "hermes":
        # Hermes' text inventory does not expose a source path.  Its parser
        # emits this closed shape only after matching the exact plugin id; the
        # command environment fixes HERMES_HOME and drops project-plugin
        # enablement, while the owned target proves the user-plugin source.
        return (
            set(record) == {"id", "enabled"}
            and record.get("id") == PLUGIN_ID
            and type(record.get("enabled")) is bool
            and not paths
        )
    if host == "openclaw":
        return paths == {root}
    marketplace = str(
        record.get("marketplaceName")
        or record.get("marketplace")
        or record.get("marketplaceId")
        or ""
    ).casefold()
    if marketplace and marketplace != MARKETPLACE_ID:
        return False
    if marketplace != MARKETPLACE_ID or not paths:
        return False
    plugin_root = root / "plugins" / PLUGIN_ID
    return plugin_root in paths and paths <= {root, plugin_root}


def _native_result(
    command: list[str],
    *,
    host: str,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    timeout: float = 20,
) -> NativeCommandResult:
    try:
        return _dispatch(
            "_run_native",
            command,
            host=host,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=timeout,
        )
    except Exception as exc:
        return NativeCommandResult(
            tuple(command),
            124 if isinstance(exc, TimeoutError) else 70,
            "",
            _bounded_error(exc),
        )


def _execution_binding(
    host: str,
    *,
    executable: str | None,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> dict[str, Any]:
    """Freeze the one cwd/environment/launcher context used by every host call."""

    runtime_root = _dispatch("_runtime_home", home_dir=home_dir).resolve()
    forbidden_roots = _host_command_forbidden_roots(runtime_root)
    if host == "zcode":
        executable_projection: object = {"kind": "config-only"}
        environment_projection: object = {"kind": "config-only"}
    else:
        if not executable:
            raise PermissionError("Native executable identity is unavailable")
        resolved = Path(executable).expanduser()
        if command_runner is None:
            _prepared, executable_projection = _prepared_launcher(
                [str(resolved)],
                runtime_root=runtime_root,
                forbidden_roots=forbidden_roots,
            )
        else:
            executable_projection = {
                "kind": "injected-test-runner",
                "path": str(resolved),
            }
        environment_projection = _dispatch(
            "_command_environment",
            host,
            home_dir=home_dir,
            current_directory=runtime_root,
            forbidden_roots=forbidden_roots,
        )
    return {
        "executable_identity_sha256": _sha256_json(executable_projection),
        "profile_environment_sha256": _sha256_json(environment_projection),
        "execution_working_directory": str(runtime_root),
        "forbidden_roots_sha256": _sha256_json([str(root) for root in forbidden_roots]),
    }


def _run_bound_native_command(
    command: list[str],
    *,
    host: str,
    binding: Mapping[str, Any],
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    timeout: float,
) -> NativeCommandResult:
    """Launch one command with the plan-bound executable, environment, and cwd."""

    if command_runner is not None:
        return _native_result(
            command,
            host=host,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=timeout,
        )
    try:
        from agency_runtime.core.delegation.backends import run_bounded_process

        runtime_root = _dispatch("_runtime_home", home_dir=home_dir).resolve()
        forbidden_roots = _host_command_forbidden_roots(runtime_root)
        if _sha256_json([str(root) for root in forbidden_roots]) != binding.get(
            "forbidden_roots_sha256"
        ):
            raise PermissionError("Native host forbidden roots changed after uninstall planning")
        prepared, launcher_projection = _prepared_launcher(
            command,
            runtime_root=runtime_root,
            forbidden_roots=forbidden_roots,
        )
        if _sha256_json(launcher_projection) != binding.get("executable_identity_sha256"):
            raise PermissionError("Native launcher changed after uninstall planning")
        environment = _dispatch(
            "_command_environment",
            host,
            home_dir=home_dir,
            current_directory=runtime_root,
            forbidden_roots=forbidden_roots,
        )
        if _sha256_json(environment) != binding.get("profile_environment_sha256"):
            raise PermissionError("Native host environment changed after uninstall planning")
        if str(runtime_root) != binding.get("execution_working_directory"):
            raise PermissionError("Native host working directory changed after uninstall planning")
        prepared.revalidate()
        bounded = run_bounded_process(
            prepared,
            timeout=timeout,
            cwd=str(runtime_root),
            env=environment,
            max_output_chars=256 * 1024,
        )
        stderr = bounded.stderr
        if bounded.timed_out:
            stderr = "native command timed out"
        elif bounded.stdout_truncated or bounded.stderr_truncated:
            stderr = "native command output exceeded the capture limit"
        return NativeCommandResult(
            tuple(command),
            bounded.returncode,
            bounded.stdout,
            stderr,
            bounded.stdout_truncated,
            bounded.stderr_truncated,
        )
    except Exception as exc:
        return NativeCommandResult(
            tuple(command),
            124 if isinstance(exc, TimeoutError) else 70,
            "",
            _bounded_error(exc),
        )


def _inventory_plugin_records(
    host: str,
    result: NativeCommandResult,
) -> list[dict[str, Any]]:
    if host == "hermes":
        return [
            record
            for line in result.stdout.splitlines()
            if (record := _dispatch("_hermes_text_plugin_record", line)) is not None
        ]
    return _plugin_records(_dispatch("_json_output", result))


def _openclaw_gateway_state(result: NativeCommandResult) -> bool | None:
    """Interpret only explicit live/stopped gateway signals from a bound probe."""

    payload = _dispatch("_json_output", result)
    if not result.ok or not isinstance(payload, dict):
        return None
    status = str(payload.get("status", "")).strip().lower()
    signals = {
        key: _dispatch("_bool_field", payload, key)
        for key in ("running", "reachable", "healthy", "rpcHealthy", "active")
    }
    if any(value is True for value in signals.values()) or status in {
        "running",
        "healthy",
        "ready",
        "online",
    }:
        return True
    if signals["running"] is False or status in {"stopped", "not-running", "not_running"}:
        return False
    return None


def _native_preflight(
    host: str,
    target: Path,
    *,
    executable: str | None,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    execution_binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Read and bind native registration facts before any uninstall mutation."""

    if host == "zcode":
        from agency_runtime.core.installer_zcode import inspect_zcode_registration

        facts = inspect_zcode_registration(target, home_dir=home_dir)
        if facts.get("drifted"):
            return {"ok": False, "error": "Agency-owned ZCode handlers are drifted"}
        return {
            "ok": True,
            "plugin_present": bool(facts.get("registered")),
            "marketplace_present": False,
            "facts": facts,
            "steps": [],
        }

    inventory_command = _dispatch("_inventory_command", host)
    inventory_command[0] = str(executable)
    inventory = _run_bound_native_command(
        inventory_command,
        host=host,
        binding=execution_binding,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=20,
    )
    steps = [_safe_native_step("inventory_before", inventory)]
    if not inventory.ok:
        return {"ok": False, "error": "Native plugin inventory is unavailable", "steps": steps}
    records = _inventory_plugin_records(host, inventory)
    if len(records) > 1:
        return {
            "ok": False,
            "error": "Native Agency plugin inventory is ambiguous",
            "steps": steps,
        }
    record = records[0] if records else None
    if host == "openclaw" and record is not None and not _plugin_is_bound(host, record, target):
        inspection = _run_bound_native_command(
            [str(executable), "plugins", "inspect", PLUGIN_ID, "--json"],
            host=host,
            binding=execution_binding,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=20,
        )
        steps.append(_safe_native_step("plugin_inspect_before", inspection))
        inspected = _inventory_plugin_records(host, inspection) if inspection.ok else []
        if len(inspected) != 1:
            return {
                "ok": False,
                "error": "Native Agency plugin provenance is unavailable or ambiguous",
                "steps": steps,
            }
        record = inspected[0]
    if record is not None and not _plugin_is_bound(host, record, target):
        return {
            "ok": False,
            "error": "Native plugin identity is not bound to the managed target",
            "steps": steps,
        }

    market_record: dict[str, Any] | None = None
    if host in {"codex", "claude"}:
        binary = str(executable)
        market = _run_bound_native_command(
            [binary, "plugin", "marketplace", "list", "--json"],
            host=host,
            binding=execution_binding,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=20,
        )
        steps.append(_safe_native_step("marketplace_inventory_before", market))
        if not market.ok:
            return {
                "ok": False,
                "error": "Native marketplace inventory is unavailable",
                "steps": steps,
            }
        market_payload = _dispatch("_json_output", market)
        market_records = _marketplace_records(market_payload)
        if len(market_records) > 1:
            return {
                "ok": False,
                "error": "Native Agency marketplace inventory is ambiguous",
                "steps": steps,
            }
        market_record = market_records[0] if market_records else None
        if market_record is not None and not _marketplace_is_bound(market_record, target):
            return {
                "ok": False,
                "error": "Native marketplace identity is not bound to the managed target",
                "steps": steps,
            }

    gateway_state: str | None = None
    if host == "openclaw":
        gateway = _run_bound_native_command(
            [
                str(executable),
                "gateway",
                "status",
                "--deep",
                "--require-rpc",
                "--json",
            ],
            host=host,
            binding=execution_binding,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=12,
        )
        gateway_live = _openclaw_gateway_state(gateway)
        steps.append(
            _safe_native_step(
                "gateway_status",
                gateway,
                gateway_state=(
                    "live"
                    if gateway_live is True
                    else "stopped"
                    if gateway_live is False
                    else "unknown"
                ),
            )
        )
        gateway_state = (
            "live" if gateway_live is True else "stopped" if gateway_live is False else "unknown"
        )
        if gateway_live is not False:
            return {
                "ok": False,
                "error": (
                    "OpenClaw gateway is live; stop it before uninstall"
                    if gateway_live is True
                    else "OpenClaw gateway state is unproven; uninstall is blocked"
                ),
                "steps": steps,
            }
    return {
        "ok": True,
        "plugin_present": record is not None,
        "marketplace_present": market_record is not None,
        "plugin_record": record,
        "marketplace_record": market_record,
        "executable": executable,
        "gateway_state": gateway_state,
        "steps": steps,
    }


def _plan_binding(
    host: str,
    target: Path,
    ownership: Mapping[str, Any],
    preflight: Mapping[str, Any],
    *,
    execution_binding: Mapping[str, Any],
    home_dir: str | Path | None,
) -> dict[str, Any]:
    """Bind filesystem, profile, executable, native, and retention identities."""

    runtime_root = _dispatch("_runtime_home", home_dir=home_dir).resolve()
    target_metadata = _directory_binding(target, label="managed uninstall target")
    parent_metadata = _directory_binding(target.parent, label="managed uninstall target parent")
    runtime_metadata = _directory_binding(runtime_root, label="Agency runtime home")
    native_projection = {
        "plugin_present": preflight.get("plugin_present") is True,
        "marketplace_present": preflight.get("marketplace_present") is True,
        "plugin_record": preflight.get("plugin_record"),
        "marketplace_record": preflight.get("marketplace_record"),
        "gateway_state": preflight.get("gateway_state"),
        "zcode_facts": preflight.get("facts") if host == "zcode" else None,
    }
    if host == "zcode":
        facts = preflight.get("facts")
        if not isinstance(facts, Mapping):
            raise PermissionError("ZCode registration identity is unavailable")
        config_path = Path(str(facts.get("config_path") or ""))
        state_path = Path(str(facts.get("state_path") or ""))
        if not config_path.is_absolute() or not state_path.is_absolute():
            raise PermissionError("ZCode registration paths are invalid")
        native_projection["zcode_config_file"] = _optional_file_binding(
            config_path,
            limit=2 * 1024 * 1024,
            label="ZCode config",
        )
        native_projection["zcode_state_file"] = _optional_file_binding(
            state_path,
            limit=256 * 1024,
            label="ZCode registration state",
        )
    binding = {
        "schema_version": _BINDING_SCHEMA_VERSION,
        "host": host,
        "target": target_metadata,
        "target_parent": parent_metadata,
        "install_id": ownership.get("install_id"),
        "bundle_digest": ownership.get("bundle_digest"),
        "plugin_version": ownership.get("plugin_version"),
        **dict(execution_binding),
        "native_state_sha256": _sha256_json(native_projection),
        "runtime_home": runtime_metadata,
        "retention_root": _prospective_directory_binding(
            runtime_root / "backups" / host,
            root=runtime_root,
            label="managed uninstall retention root",
        ),
    }
    return {**binding, "binding_digest": _sha256_json(binding)}


def _uninstall_command_plan(host: str, preflight: Mapping[str, Any]) -> list[dict[str, Any]]:
    binary = str(preflight.get("executable") or HOSTS[host]["binary"])
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    commands: list[dict[str, Any]] = []
    if preflight.get("plugin_present"):
        command = (
            [binary, "plugins", "disable", PLUGIN_ID]
            if host == "hermes"
            else [
                binary,
                "plugins",
                "uninstall",
                PLUGIN_ID,
                "--keep-files",
                "--force",
            ]
            if host == "openclaw"
            else [binary, "plugin", "remove", selector, "--json"]
            if host == "codex"
            else [binary, "plugin", "uninstall", selector, "--scope", "user"]
        )
        commands.append({"name": "plugin_unregister", "argv": command})
    if host == "zcode" and preflight.get("plugin_present"):
        commands.append({"name": "config_remove", "argv": None})
    return commands


def _run_native_uninstall(
    host: str,
    target: Path,
    preflight: Mapping[str, Any],
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    binding: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], bool, str | None, bool]:
    steps = list(preflight.get("steps", []))
    changed = False
    if host == "zcode":
        from agency_runtime.core.installer_zcode import unregister_zcode_config

        zcode_steps, ok, failed_step = unregister_zcode_config(target, home_dir=home_dir)
        steps.extend(zcode_steps)
        changed = any(step.get("changed") for step in zcode_steps)
        return steps, ok, failed_step, changed

    for planned in _uninstall_command_plan(host, preflight):
        command = planned["argv"]
        result = _run_bound_native_command(
            command,
            host=host,
            binding=binding,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=60 if host in {"openclaw", "claude"} else 20,
        )
        steps.append(_safe_native_step(str(planned["name"]), result))
        changed = True
        if not result.ok:
            return steps, False, str(planned["name"]), changed
    return steps, True, None, changed


def _verify_uninstalled(
    host: str,
    target: Path,
    *,
    executable: str | None,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    expected_marketplace_record: Mapping[str, Any] | None,
    binding: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], bool, str | None]:
    if host == "zcode":
        from agency_runtime.core.installer_zcode import inspect_zcode_registration

        facts = inspect_zcode_registration(target, home_dir=home_dir)
        proven = not facts.get("registered") and not facts.get("owned_handler_count")
        return (
            [{"name": "config_inventory_after", "ok": proven, **facts}],
            proven,
            None if proven else "config_inventory_after",
        )

    inventory_command = _dispatch("_inventory_command", host)
    inventory_command[0] = str(executable)
    inventory = _run_bound_native_command(
        inventory_command,
        host=host,
        binding=binding,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=20,
    )
    steps = [_safe_native_step("inventory_after", inventory)]
    if not inventory.ok:
        return steps, False, "inventory_after"
    records = _inventory_plugin_records(host, inventory)
    if len(records) > 1:
        return steps, False, "inventory_after_ambiguous"
    if records and not (
        host == "hermes"
        and _dispatch("_bool_field", records[0], "enabled", "active", "isEnabled") is False
    ):
        return steps, False, "inventory_after_present"
    market_steps, market_ok, market_failure = _verify_marketplace_unchanged(
        host,
        executable=executable,
        expected=expected_marketplace_record,
        home_dir=home_dir,
        command_runner=command_runner,
        phase="after",
        binding=binding,
    )
    steps.extend(market_steps)
    return steps, market_ok, market_failure


def _verify_marketplace_unchanged(
    host: str,
    *,
    executable: str | None,
    expected: Mapping[str, Any] | None,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    phase: str,
    binding: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], bool, str | None]:
    if host not in {"codex", "claude"}:
        return [], True, None
    market = _run_bound_native_command(
        [str(executable), "plugin", "marketplace", "list", "--json"],
        host=host,
        binding=binding,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=20,
    )
    step_name = f"marketplace_inventory_{phase}"
    steps = [_safe_native_step(step_name, market)]
    if not market.ok:
        return steps, False, step_name
    records = _marketplace_records(_dispatch("_json_output", market))
    if len(records) > 1:
        return steps, False, f"{step_name}_ambiguous"
    observed = records[0] if records else None
    if _sha256_json(observed) != _sha256_json(expected):
        return steps, False, f"{step_name}_changed"
    return steps, True, None


def _verify_native_detached(
    host: str,
    target: Path,
    *,
    executable: str | None,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    expected_marketplace_record: Mapping[str, Any] | None,
    binding: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], bool, str | None]:
    """Prove native detachment before moving the source bundle."""

    if host == "zcode":
        return _verify_uninstalled(
            host,
            target,
            executable=executable,
            home_dir=home_dir,
            command_runner=command_runner,
            expected_marketplace_record=expected_marketplace_record,
            binding=binding,
        )
    inventory_command = _dispatch("_inventory_command", host)
    inventory_command[0] = str(executable)
    inventory = _run_bound_native_command(
        inventory_command,
        host=host,
        binding=binding,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=20,
    )
    steps = [_safe_native_step("inventory_detached", inventory)]
    if not inventory.ok:
        return steps, False, "inventory_detached"
    records = _inventory_plugin_records(host, inventory)
    if len(records) > 1:
        return steps, False, "inventory_detached_ambiguous"
    record = records[0] if records else None
    detached = record is None or (
        host == "hermes"
        and _dispatch("_bool_field", record, "enabled", "active", "isEnabled") is False
    )
    if not detached:
        return steps, False, "inventory_detached_present"
    market_steps, market_ok, market_failure = _verify_marketplace_unchanged(
        host,
        executable=executable,
        expected=expected_marketplace_record,
        home_dir=home_dir,
        command_runner=command_runner,
        phase="detached",
        binding=binding,
    )
    steps.extend(market_steps)
    return steps, market_ok, market_failure


def _base_result(host: str, target: Path) -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "ok": False,
        "complete": False,
        "exit_code": 1,
        "host": host,
        "target": str(target),
        "changed": False,
        "retained_path": None,
        "native_steps": [],
        "package_removed": False,
        "dashboard_removed": False,
        "store_removed": False,
        "agency_configuration_removed": False,
        "backups_removed": False,
        "marketplace_registration_removed": False,
    }


def plan_agent_uninstall(
    host: str,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Return a write-free, ownership-bound uninstall plan for one host."""

    if host not in HOSTS:
        return _unknown_host(host)
    target = _dispatch("_plugin_target", host, home_dir=home_dir)
    result = {**_base_result(host, target), "dry_run": True}
    ownership = _owned_target_state(host, target)
    inspection = _dispatch(
        "inspect_host_installation",
        host,
        home_dir=home_dir,
        binary_resolver=binary_resolver,
        command_runner=command_runner,
    )
    result["inspection"] = inspection
    result["ownership"] = ownership
    native_present = inspection.get("registered") is True
    if not ownership["present"]:
        if native_present:
            result.update(
                {
                    "status": "blocked",
                    "error": "Native Agency state exists without an owned managed target",
                }
            )
            return result
        result.update(
            {
                "ok": True,
                "complete": True,
                "exit_code": 0,
                "status": "not_installed",
                "would_change": False,
            }
        )
        return result
    if not ownership["owned"]:
        result.update({"status": "blocked", "error": ownership["error"]})
        return result
    executable = _dispatch("_resolve_binary", host, binary_resolver)
    if host != "zcode" and (
        not executable
        or not _dispatch(
            "_can_execute_native",
            home_dir=home_dir,
            command_runner=command_runner,
        )
    ):
        result.update(
            {
                "status": "blocked",
                "error": "Native host lifecycle is unavailable; owned files were not touched",
            }
        )
        return result
    try:
        execution_binding = _execution_binding(
            host,
            executable=executable,
            home_dir=home_dir,
            command_runner=command_runner,
        )
        preflight = _native_preflight(
            host,
            target,
            executable=executable,
            home_dir=home_dir,
            command_runner=command_runner,
            execution_binding=execution_binding,
        )
    except Exception:
        result.update(
            {
                "status": "blocked",
                "error": "Uninstall plan execution context is unavailable",
            }
        )
        return result
    result["native_steps"] = preflight.get("steps", [])
    if not preflight.get("ok"):
        result.update({"status": "blocked", "error": preflight.get("error")})
        return result
    try:
        binding = _plan_binding(
            host,
            target,
            ownership,
            preflight,
            execution_binding=execution_binding,
            home_dir=home_dir,
        )
    except Exception:
        result.update(
            {
                "status": "blocked",
                "error": "Uninstall plan identity is unavailable",
            }
        )
        return result
    result.update(
        {
            "ok": True,
            "complete": True,
            "exit_code": 0,
            "status": "planned",
            "would_change": True,
            "native_command_plan": _uninstall_command_plan(host, preflight),
            "binding": binding,
            "binding_digest": binding["binding_digest"],
            "retention_policy": "move owned bundle into the managed rollback root",
            "restart_required": True,
        }
    )
    return result


def _commit_agent_uninstall(  # noqa: C901 - ordered fail-closed host transaction
    host: str,
    *,
    expected_install_id: str,
    expected_bundle_digest: str,
    expected_binding_digest: str,
    retained_path: Path,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Unregister one exact owned adapter and retain its files for rollback."""

    if host not in HOSTS:
        return _unknown_host(host)
    target = _dispatch("_plugin_target", host, home_dir=home_dir)
    result = _base_result(host, target)
    ownership = _owned_target_state(host, target)
    inspection = _dispatch(
        "inspect_host_installation",
        host,
        home_dir=home_dir,
        binary_resolver=binary_resolver,
        command_runner=command_runner,
    )
    native_present = inspection.get("registered") is True
    if not ownership["present"]:
        if native_present:
            result.update(
                {
                    "status": "blocked",
                    "error": "Native Agency state exists without an owned managed target",
                }
            )
            return result
        result.update(
            {
                "ok": True,
                "complete": True,
                "exit_code": 0,
                "status": "not_installed",
            }
        )
        return result
    if not ownership["owned"]:
        result.update({"status": "blocked", "error": ownership["error"]})
        return result
    if (
        ownership["install_id"] != expected_install_id
        or ownership["bundle_digest"] != expected_bundle_digest
    ):
        result.update(
            {
                "status": "blocked",
                "error": "Managed target identity changed after uninstall planning",
            }
        )
        return result
    executable = _dispatch("_resolve_binary", host, binary_resolver)
    if host != "zcode" and (
        not executable
        or not _dispatch(
            "_can_execute_native",
            home_dir=home_dir,
            command_runner=command_runner,
        )
    ):
        result.update(
            {
                "status": "blocked",
                "error": "Native host lifecycle is unavailable; owned files were not touched",
            }
        )
        return result
    try:
        execution_binding = _execution_binding(
            host,
            executable=executable,
            home_dir=home_dir,
            command_runner=command_runner,
        )
        preflight = _native_preflight(
            host,
            target,
            executable=executable,
            home_dir=home_dir,
            command_runner=command_runner,
            execution_binding=execution_binding,
        )
    except Exception:
        result.update(
            {
                "status": "blocked",
                "error": "Uninstall commit execution context is unavailable",
            }
        )
        return result
    result["native_steps"] = preflight.get("steps", [])
    if not preflight.get("ok"):
        result.update({"status": "blocked", "error": preflight.get("error")})
        return result
    try:
        current_binding = _plan_binding(
            host,
            target,
            ownership,
            preflight,
            execution_binding=execution_binding,
            home_dir=home_dir,
        )
    except Exception:
        result.update(
            {
                "status": "blocked",
                "error": "Uninstall commit identity is unavailable",
            }
        )
        return result
    if current_binding["binding_digest"] != expected_binding_digest:
        result.update(
            {
                "status": "blocked",
                "error": "Host profile or native state changed after uninstall planning",
            }
        )
        return result

    steps, native_ok, failed_step, native_changed = _run_native_uninstall(
        host,
        target,
        preflight,
        home_dir=home_dir,
        command_runner=command_runner,
        binding=current_binding,
    )
    result["native_steps"] = steps
    if native_changed:
        result["changed"] = True
        result["canary_attestation_invalidated"] = _dispatch(
            "_invalidate_canary_attestation",
            host,
            home_dir=home_dir,
        )
    if not native_ok:
        result.update(
            {
                "status": "partial_failure" if native_changed else "blocked",
                "failed_step": failed_step,
                "error": f"Native {host} unregistration failed at {failed_step}",
                "restart_required": native_changed,
            }
        )
        return result

    detached_steps, detached, detached_failure = _verify_native_detached(
        host,
        target,
        executable=executable,
        home_dir=home_dir,
        command_runner=command_runner,
        expected_marketplace_record=preflight.get("marketplace_record"),
        binding=current_binding,
    )
    result["native_steps"].extend(detached_steps)
    if not detached:
        result.update(
            {
                "status": "partial_failure",
                "failed_step": detached_failure,
                "error": "Native detachment could not be proven; owned files were retained",
                "restart_required": native_changed,
            }
        )
        return result

    if host == "codex":
        try:
            guidance = _dispatch(
                "_remove_codex_global_guidance",
                _dispatch("_host_root", "codex", home_dir=home_dir),
            )
        except Exception as exc:
            result.update(
                {
                    "status": "partial_failure",
                    "failed_step": "global_guidance_remove",
                    "error": (
                        "Native detachment succeeded, but Codex delegation guidance "
                        f"could not be removed: {type(exc).__name__}: {exc}"
                    ),
                    "restart_required": native_changed,
                }
            )
            return result
        result["global_guidance"] = guidance
        if guidance.get("changed") is True:
            result["changed"] = True

    try:
        retirement = _retire_owned_target(
            host,
            target,
            home_dir=home_dir,
            expected_install_id=expected_install_id,
            expected_bundle_digest=expected_bundle_digest,
            expected_retention_binding=current_binding["retention_root"],
            retained_path=retained_path,
        )
    except Exception as exc:
        retained_path = exc.retained_path if isinstance(exc, UninstallRetirementError) else None
        result.update(
            {
                "status": "partial_failure",
                "failed_step": "filesystem_retire",
                "error": (
                    str(exc)
                    if isinstance(exc, UninstallRetirementError)
                    else "Owned bundle retirement failed"
                ),
                "retained_path": retained_path,
                "restart_required": native_changed,
            }
        )
        return result
    result.update(retirement)
    result["changed"] = True
    result["canary_attestation_invalidated"] = _dispatch(
        "_invalidate_canary_attestation",
        host,
        home_dir=home_dir,
    )
    verification, verified, failed_step = _verify_uninstalled(
        host,
        target,
        executable=executable,
        home_dir=home_dir,
        command_runner=command_runner,
        expected_marketplace_record=preflight.get("marketplace_record"),
        binding=current_binding,
    )
    result["native_steps"].extend(verification)
    if not verified:
        result.update(
            {
                "status": "partial_failure",
                "failed_step": failed_step,
                "error": "Owned files were retained, but native absence could not be proven",
                "restart_required": True,
            }
        )
        return result
    result.update(
        {
            "ok": True,
            "complete": True,
            "exit_code": 0,
            "status": "uninstalled",
            "restart_required": True,
            "recovery": _recovery_command(host, str(result["retained_path"])),
            "recovery_backup": str(result["retained_path"]),
        }
    )
    return result


__all__ = ["plan_agent_uninstall"]
