"""Prepared refresh for an existing Codex adapter through Codex-native trust.

This module intentionally does not implement generic installation.  It admits
one exact positive slice: an already-owned, registered, and enabled Codex
marketplace can be refreshed to the bytes from the running Agency Runtime
distribution.  Preparation is read-only, the native verifier consumes its
result in this call stack, and every effect is revalidated and conditionally
compensated.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.filesystem_trust import absolute_path as _absolute_path
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _metadata_is_link_or_reparse,
)
from agency_runtime.core.installer_contracts import (
    ADAPTER_LAUNCHER_MANIFEST,
    INSTALL_MANIFEST,
    MARKETPLACE_ID,
    MAX_NATIVE_OUTPUT_CHARS,
    PLUGIN_ID,
    PLUGIN_VERSION,
    NativeCommandResult,
)
from agency_runtime.core.installer_filesystem import AtomicInstallTreeError, atomic_install_tree
from agency_runtime.core.installer_inventory import (
    _bundle_digest,
    _managed_bundle_identity,
    _managed_bundle_matches,
)
from agency_runtime.core.installer_native import (
    _command_environment,
    plugin_target,
    runtime_home,
)
from agency_runtime.core.installer_payloads import (
    bind_launcher_artifact_paths,
    bundle_files,
    hook_timeout_seconds,
    launcher_artifact_paths,
)
from agency_runtime.core.launcher_bootstrap import (
    PrivateRuntimePlan,
    persistent_python_executable,
    plan_private_package_runtime,
    prepare_private_package_runtime,
    verify_private_package_runtime,
)
from agency_runtime.core.private_paths import ensure_private_directory, validate_private_directory
from agency_runtime.core.process_argv import (
    PersistentArtifactIdentity,
    PreparedProcessArgv,
    prepare_process_argv,
    repository_forbidden_roots,
    revalidate_persistent_artifacts,
    snapshot_persistent_artifact,
)
from agency_runtime.core.runtime_control import (
    RuntimeControlSnapshot,
    read_runtime_control_snapshot,
    runtime_control_path,
)

_ACTION = "install.codex.v1"
_HOST = "codex"
_SELECTOR = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
_MAX_MANIFEST_BYTES = 64 * 1024
_MAX_TREE_FILES = 512
_MAX_TREE_FILE_BYTES = 64 * 1024 * 1024
_MAX_TREE_BYTES = 256 * 1024 * 1024
_LOCK_TIMEOUT_SECONDS = 30.0
_VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CONFIG_REVISION = re.compile(r"sha256:[0-9a-f]{64}\Z")


class PreparedCodexInstallError(RuntimeError):
    """The exact prepared Codex refresh could not be proven safe."""


class _CodexInstallBinding(NamedTuple):
    action: str
    host: str
    config_path: str
    config_revision: str
    database_path: str
    database_device: int
    database_inode: int
    roster_generation: int
    host_control_generation: int
    runtime_control_generation: int
    target_path: str
    target_parent_device: int
    target_parent_inode: int
    current_install_id: str
    current_plugin_version: str
    candidate_plugin_version: str
    current_bundle_sha256: str
    current_tree_sha256: str
    candidate_plan_sha256: str
    launcher_plan_sha256: str
    codex_executable_path: str
    codex_executable_sha256: str
    codex_executable_identity_sha256: str
    codex_environment_sha256: str
    codex_version: str
    marketplace_state_sha256: str
    plugin_state_sha256: str
    binding_sha256: str


_STRING_BINDING_FIELDS = frozenset(
    set(_CodexInstallBinding._fields)
    - {
        "database_device",
        "database_inode",
        "roster_generation",
        "host_control_generation",
        "runtime_control_generation",
        "target_parent_device",
        "target_parent_inode",
    }
)
_INTEGER_BINDING_FIELDS = frozenset(
    {
        "database_device",
        "database_inode",
        "roster_generation",
        "host_control_generation",
        "runtime_control_generation",
        "target_parent_device",
        "target_parent_inode",
    }
)


@dataclass(frozen=True, slots=True)
class _ManagedTargetSnapshot:
    install_id: str
    plugin_version: str
    bundle_sha256: str
    tree_sha256: str
    parent_device: int
    parent_inode: int


@dataclass(frozen=True, slots=True)
class _CodexNativeState:
    plugin_present: bool
    plugin_enabled: bool | None
    plugin_version: str
    plugin_state_sha256: str
    marketplace_state_sha256: str


@dataclass(frozen=True, slots=True)
class _PreparedCodexInstall:
    binding: _CodexInstallBinding
    target: Path
    target_snapshot: _ManagedTargetSnapshot
    runtime_plan: PrivateRuntimePlan
    component_files: Mapping[str, str]
    primary_file: str
    python_identity: PersistentArtifactIdentity
    codex_argv: PreparedProcessArgv
    codex_environment: Mapping[str, str]
    codex_working_directory: str
    native_state: _CodexNativeState


def is_exact_prepared_codex_install(namespace: object) -> bool:
    """Recognize only the reviewed Codex refresh CLI shape."""

    try:
        timeout = float(getattr(namespace, "activation_timeout", 180.0))
    except (TypeError, ValueError):
        return False
    return bool(
        getattr(namespace, "command", None) == "install"
        and getattr(namespace, "agent", None) == _HOST
        and getattr(namespace, "profile", None) is None
        and not bool(getattr(namespace, "all", False))
        and not bool(getattr(namespace, "dry_run", False))
        and not bool(getattr(namespace, "rollback", False))
        and not bool(getattr(namespace, "verify_activation", False))
        and getattr(namespace, "backup", None) is None
        and bool(getattr(namespace, "no_dashboard", False))
        and math.isfinite(timeout)
        and timeout == 180.0
    )


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _binding_digest(values: Sequence[str | int]) -> str:
    return hashlib.sha256(
        b"agency.prepared-codex-install.v1\0" + _canonical_json(list(values))
    ).hexdigest()


def _codex_install_binding_primitives(binding: object) -> tuple[str | int, ...]:
    """Return exact primitive fields and reject forged or malformed bindings."""

    if type(binding) is not _CodexInstallBinding:
        raise PreparedCodexInstallError("prepared Codex install binding is invalid")
    for field, value in zip(_CodexInstallBinding._fields, binding, strict=True):
        if field in _STRING_BINDING_FIELDS:
            if type(value) is not str:
                raise PreparedCodexInstallError("prepared Codex install binding is invalid")
        elif field in _INTEGER_BINDING_FIELDS:
            if type(value) is not int or value < 0:
                raise PreparedCodexInstallError("prepared Codex install binding is invalid")
        else:  # pragma: no cover - exhaustive field classification invariant
            raise RuntimeError(f"unclassified prepared Codex install field: {field}")
    values = tuple(binding)
    if (
        binding.action != _ACTION
        or binding.host != _HOST
        or not Path(binding.target_path).is_absolute()
        or not Path(binding.config_path).is_absolute()
        or not Path(binding.database_path).is_absolute()
        or not Path(binding.codex_executable_path).is_absolute()
        or _CONFIG_REVISION.fullmatch(binding.config_revision) is None
        or _VERSION.fullmatch(binding.current_plugin_version) is None
        or _VERSION.fullmatch(binding.candidate_plugin_version) is None
        or any(
            _SHA256.fullmatch(value) is None
            for value in (
                binding.current_bundle_sha256,
                binding.current_tree_sha256,
                binding.candidate_plan_sha256,
                binding.launcher_plan_sha256,
                binding.codex_executable_sha256,
                binding.codex_executable_identity_sha256,
                binding.codex_environment_sha256,
                binding.marketplace_state_sha256,
                binding.plugin_state_sha256,
                binding.binding_sha256,
            )
        )
        or _binding_digest(values[:-1]) != binding.binding_sha256
    ):
        raise PreparedCodexInstallError("prepared Codex install binding is invalid")
    return values


def _make_binding(**values: str | int) -> _CodexInstallBinding:
    fields = _CodexInstallBinding._fields[:-1]
    if set(values) != set(fields):
        raise PreparedCodexInstallError("prepared Codex install binding is incomplete")
    ordered = tuple(values[field] for field in fields)
    binding = _CodexInstallBinding(*ordered, _binding_digest(ordered))
    _codex_install_binding_primitives(binding)
    return binding


def _path_key(value: str | Path) -> str:
    raw = os.fspath(value)
    if raw.startswith("\\\\?\\"):
        raw = raw[4:]
    candidate = Path(raw)
    if not candidate.is_absolute():
        return ""
    return os.path.normcase(str(_absolute_path(candidate)))


def _codex_target_path(*, home_dir: str | Path | None) -> Path:
    home = Path.home() if home_dir is None else Path(home_dir).expanduser()
    if not home.is_absolute():
        raise PreparedCodexInstallError("prepared Codex home boundary must be absolute")
    lexical = _absolute_path(home / ".agency-runtime" / "marketplaces" / _HOST)
    try:
        resolved = lexical.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PreparedCodexInstallError("prepared Codex marketplace target is unavailable") from exc
    if _path_key(lexical) != _path_key(resolved):
        raise PreparedCodexInstallError(
            "prepared Codex marketplace must not cross a link or reparse boundary"
        )
    configured = plugin_target(_HOST, home_dir=home_dir)
    if _path_key(configured) != _path_key(lexical):
        raise PreparedCodexInstallError(
            "prepared Codex marketplace escaped its expected Agency runtime boundary"
        )
    for candidate in (lexical.parent.parent, lexical.parent, lexical):
        _directory_identity(candidate, label="prepared Codex marketplace boundary")
    return lexical


def _directory_identity(path: Path, *, label: str) -> tuple[int, int]:
    metadata = os.lstat(path)
    if not stat.S_ISDIR(metadata.st_mode) or _metadata_is_link_or_reparse(metadata):
        raise PreparedCodexInstallError(f"{label} must be a real directory")
    return int(metadata.st_dev), int(metadata.st_ino)


def _metadata_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_file_attributes", 0)),
    )


def _managed_tree_digest(target: Path) -> str:
    digest = hashlib.sha256(b"agency.managed-codex-tree.v2\0")
    total = 0
    root_before = os.lstat(target)
    paths: list[tuple[Path, os.stat_result, bool]] = []
    for index, path in enumerate(target.rglob("*")):
        if index >= _MAX_TREE_FILES:
            raise PreparedCodexInstallError("managed Codex tree exceeds its file-count limit")
        metadata = os.lstat(path)
        if _metadata_is_link_or_reparse(metadata):
            raise PreparedCodexInstallError("managed Codex tree contains a linked path")
        if stat.S_ISDIR(metadata.st_mode):
            paths.append((path, metadata, True))
        elif stat.S_ISREG(metadata.st_mode):
            paths.append((path, metadata, False))
        else:
            raise PreparedCodexInstallError("managed Codex tree contains a special file")
    digest.update(_canonical_json(_metadata_identity(root_before)))
    digest.update(b"\0")
    for path, before, is_directory in sorted(
        paths,
        key=lambda item: item[0].relative_to(target).as_posix(),
    ):
        relative = path.relative_to(target).as_posix().encode("utf-8")
        digest.update(b"d\0" if is_directory else b"f\0")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(_canonical_json(_metadata_identity(before)))
        digest.update(b"\0")
        if is_directory:
            continue
        payload = read_bounded_regular_file(
            path,
            limit=_MAX_TREE_FILE_BYTES,
            label="managed Codex file",
        )
        total += len(payload)
        if total > _MAX_TREE_BYTES:
            raise PreparedCodexInstallError("managed Codex tree exceeds its byte limit")
        after = os.lstat(path)
        if _metadata_identity(after) != _metadata_identity(before):
            raise PreparedCodexInstallError("managed Codex tree changed during snapshot")
        digest.update(payload)
        digest.update(b"\0")
    for path, before, _is_directory in paths:
        try:
            after = os.lstat(path)
        except OSError as exc:
            raise PreparedCodexInstallError("managed Codex tree changed during snapshot") from exc
        if _metadata_identity(after) != _metadata_identity(before):
            raise PreparedCodexInstallError("managed Codex tree changed during snapshot")
    root_after = os.lstat(target)
    if _metadata_identity(root_after) != _metadata_identity(root_before):
        raise PreparedCodexInstallError("managed Codex tree changed during snapshot")
    return digest.hexdigest()


def _target_snapshot(target: Path) -> _ManagedTargetSnapshot:
    if not target.is_dir():
        raise PreparedCodexInstallError(
            "prepared Codex refresh requires an existing Agency-owned marketplace"
        )
    validate_private_directory(target.parent)
    _directory_identity(target, label="managed Codex marketplace")
    version, install_id, bundle = _managed_bundle_identity(target, _HOST)
    if not version or not install_id or not bundle:
        raise PreparedCodexInstallError(
            "prepared Codex refresh requires an intact Agency-owned install manifest"
        )
    manifest_payload = read_bounded_regular_file(
        target / INSTALL_MANIFEST,
        limit=_MAX_MANIFEST_BYTES,
        label="managed Codex install manifest",
    )
    manifest = safe_load_bounded_json(manifest_payload)
    if not isinstance(manifest, dict):
        raise PreparedCodexInstallError("managed Codex install manifest is invalid")
    owned = manifest.get("owned_files")
    if not isinstance(owned, list) or not owned or not all(isinstance(item, str) for item in owned):
        raise PreparedCodexInstallError("managed Codex install manifest is invalid")
    expected_files = {Path(item).as_posix() for item in owned}
    expected_files.add(INSTALL_MANIFEST)
    expected_directories = {
        parent.as_posix()
        for item in expected_files
        for parent in Path(item).parents
        if parent != Path(".")
    }
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in target.rglob("*"):
        metadata = os.lstat(path)
        if _metadata_is_link_or_reparse(metadata):
            raise PreparedCodexInstallError("managed Codex tree contains a linked path")
        relative = path.relative_to(target).as_posix()
        if stat.S_ISDIR(metadata.st_mode):
            actual_directories.add(relative)
        elif stat.S_ISREG(metadata.st_mode):
            actual_files.add(relative)
        else:
            raise PreparedCodexInstallError("managed Codex tree contains a special file")
    if actual_files != expected_files or actual_directories != expected_directories:
        raise PreparedCodexInstallError("managed Codex marketplace has unowned or missing files")
    parent_device, parent_inode = _directory_identity(
        target.parent,
        label="managed Codex marketplace parent",
    )
    return _ManagedTargetSnapshot(
        install_id=install_id,
        plugin_version=version,
        bundle_sha256=bundle,
        tree_sha256=_managed_tree_digest(target),
        parent_device=parent_device,
        parent_inode=parent_inode,
    )


def _database_snapshot(
    cfg: AgencyConfig,
) -> tuple[Path, PersistentArtifactIdentity, int, int, bool]:
    database = Path(cfg.store.resolved_path()).expanduser().resolve()
    identity = snapshot_persistent_artifact(database)
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        connection.execute("PRAGMA query_only = ON")
        connection.execute("BEGIN")
        roster = connection.execute(
            "SELECT value FROM store_counters WHERE name = 'roster-generation'"
        ).fetchone()
        control = connection.execute(
            "SELECT enabled, generation FROM host_controls WHERE host = ?",
            (_HOST,),
        ).fetchone()
        if roster is None or control is None:
            raise PreparedCodexInstallError(
                "prepared Codex refresh requires materialized roster and host-control state"
            )
        roster_generation = int(roster[0])
        host_enabled = int(control[0])
        host_generation = int(control[1])
        if roster_generation < 0 or host_generation < 0 or host_enabled not in {0, 1}:
            raise PreparedCodexInstallError("Codex Store prerequisite state is invalid")
        connection.commit()
    finally:
        connection.close()
    observed = snapshot_persistent_artifact(database)
    if observed != identity:
        raise PreparedCodexInstallError("Codex Store changed during refresh preparation")
    return database, identity, roster_generation, host_generation, bool(host_enabled)


def _configuration_projection(
    cfg: AgencyConfig,
    *,
    database: Path,
    control_path: Path,
    control: RuntimeControlSnapshot,
) -> str:
    """Bind only non-secret behavior that affects the generated adapter."""

    return "sha256:" + _sha256_json(
        {
            "config_path": str(Path(cfg.config_path).resolve()),
            "database_path": str(database),
            "hook_timeout_seconds": hook_timeout_seconds(cfg),
            "profile": cfg.profile,
            "runtime_control": {
                "enabled": control.enabled,
                "generation": control.generation,
                "materialized": control.materialized,
                "path": str(control_path),
            },
        }
    )


def _persistent_identity_digest(identity: PersistentArtifactIdentity) -> str:
    return _sha256_json(identity.manifest())


def _prepared_codex_argv(
    *,
    home_dir: str | Path | None,
) -> tuple[PreparedProcessArgv, dict[str, str], str, str]:
    working_directory = runtime_home(home_dir=home_dir)
    validate_private_directory(working_directory)
    ambient_repository_roots = repository_forbidden_roots(
        Path.cwd(),
        include_current=False,
    )
    forbidden = tuple(
        dict.fromkeys(
            (
                *repository_forbidden_roots(working_directory),
                *ambient_repository_roots,
            )
        )
    )
    argv = prepare_process_argv(
        [_HOST],
        current_directory=working_directory,
        forbidden_roots=forbidden,
    )
    argv.freeze_persistent(platform_name=os.name, forbidden_roots=forbidden)
    environment = _command_environment(
        _HOST,
        home_dir=home_dir,
        current_directory=working_directory,
        forbidden_roots=forbidden,
    )
    version_result = _run_prepared(
        argv.with_arguments(["--version"]),
        environment=environment,
        working_directory=working_directory,
        timeout=10,
    )
    version = (version_result.stdout or version_result.stderr).strip()
    if not version_result.ok or not version or len(version) > 256:
        raise PreparedCodexInstallError("Codex executable version could not be proven")
    if any(ord(character) < 32 and character not in "\t" for character in version):
        raise PreparedCodexInstallError("Codex executable version is invalid")
    return argv, environment, version, str(working_directory)


def _run_prepared(
    argv: PreparedProcessArgv,
    *,
    environment: Mapping[str, str],
    working_directory: str | Path | None = None,
    timeout: float = 30,
) -> NativeCommandResult:
    from agency_runtime.core.delegation.backends import run_bounded_process

    argv.revalidate()
    if working_directory is None:
        launch_directory = Path(argv[0]).parent
        _directory_identity(launch_directory, label="Codex executable directory")
    else:
        launch_directory = Path(working_directory)
        validate_private_directory(launch_directory)
    bounded = run_bounded_process(
        argv,
        timeout=timeout,
        cwd=str(launch_directory),
        env=dict(environment),
        max_output_chars=MAX_NATIVE_OUTPUT_CHARS,
    )
    stderr = bounded.stderr
    if bounded.timed_out:
        stderr = "\n".join(
            part for part in (stderr.strip(), f"timed out after {timeout:g}s") if part
        )
    return NativeCommandResult(
        tuple(argv),
        bounded.returncode,
        bounded.stdout,
        stderr,
        bounded.stdout_truncated,
        bounded.stderr_truncated,
    )


def _decoded_native_json(result: NativeCommandResult, *, label: str) -> object:
    if not result.ok or not result.stdout.strip():
        raise PreparedCodexInstallError(f"{label} is unavailable")
    try:
        value = safe_load_bounded_json(
            result.stdout,
            maximum_bytes=MAX_NATIVE_OUTPUT_CHARS,
            maximum_depth=64,
            maximum_nodes=50_000,
        )
    except (TypeError, ValueError) as exc:
        raise PreparedCodexInstallError(f"{label} is malformed") from exc
    if not isinstance(value, dict):
        raise PreparedCodexInstallError(f"{label} must be a JSON object")
    return value


def _strict_native_state(
    argv: PreparedProcessArgv,
    *,
    environment: Mapping[str, str],
    working_directory: str | Path | None = None,
    target: Path,
    steps: list[dict[str, Any]] | None = None,
) -> _CodexNativeState:
    inventory_result = _run_prepared(
        argv.with_arguments(["plugin", "list", "--json"]),
        environment=environment,
        working_directory=working_directory,
    )
    marketplace_result = _run_prepared(
        argv.with_arguments(["plugin", "marketplace", "list", "--json"]),
        environment=environment,
        working_directory=working_directory,
    )
    if steps is not None:
        steps.extend(
            [
                {"name": "inventory", **inventory_result.to_dict()},
                {"name": "marketplace_inventory", **marketplace_result.to_dict()},
            ]
        )
    inventory = _decoded_native_json(inventory_result, label="Codex plugin inventory")
    marketplaces = _decoded_native_json(
        marketplace_result,
        label="Codex marketplace inventory",
    )
    installed = inventory.get("installed")
    available = inventory.get("available")
    market_rows = marketplaces.get("marketplaces")
    if (
        set(inventory) != {"installed", "available"}
        or set(marketplaces) != {"marketplaces"}
        or not isinstance(installed, list)
        or not isinstance(available, list)
        or not isinstance(market_rows, list)
        or any(not isinstance(row, dict) for row in installed)
        or any(not isinstance(row, dict) for row in available)
        or any(not isinstance(row, dict) for row in market_rows)
    ):
        raise PreparedCodexInstallError("Codex native inventory schema is invalid")
    plugin_candidates = [
        row
        for row in installed
        if (
            row.get("pluginId") == _SELECTOR
            or row.get("name") == PLUGIN_ID
            or row.get("marketplaceName") == MARKETPLACE_ID
        )
    ]
    if len(plugin_candidates) > 1:
        raise PreparedCodexInstallError("Codex Agency plugin inventory is ambiguous")
    plugin = plugin_candidates[0] if plugin_candidates else None
    market_candidates = [row for row in market_rows if row.get("name") == MARKETPLACE_ID]
    if len(market_candidates) != 1:
        raise PreparedCodexInstallError("Codex Agency marketplace inventory is ambiguous")
    market = market_candidates[0]
    if set(market) != {"name", "root"} or _path_key(str(market.get("root", ""))) != _path_key(
        target
    ):
        raise PreparedCodexInstallError("Codex Agency marketplace root is not exact")
    market_digest = _sha256_json(market)
    if plugin is None:
        return _CodexNativeState(False, None, "", _sha256_json(None), market_digest)
    source = plugin.get("source")
    marketplace_source = plugin.get("marketplaceSource")
    version = plugin.get("version")
    if (
        set(plugin)
        != {
            "pluginId",
            "name",
            "marketplaceName",
            "version",
            "installed",
            "enabled",
            "source",
            "marketplaceSource",
            "installPolicy",
            "authPolicy",
        }
        or plugin.get("pluginId") != _SELECTOR
        or plugin.get("name") != PLUGIN_ID
        or plugin.get("marketplaceName") != MARKETPLACE_ID
        or plugin.get("installed") is not True
        or not isinstance(plugin.get("enabled"), bool)
        or plugin.get("installPolicy") != "AVAILABLE"
        or plugin.get("authPolicy") != "ON_INSTALL"
        or not isinstance(version, str)
        or _VERSION.fullmatch(version) is None
        or not isinstance(source, dict)
        or set(source) != {"source", "path"}
        or source.get("source") != "local"
        or _path_key(str(source.get("path", ""))) != _path_key(target / "plugins" / PLUGIN_ID)
        or not isinstance(marketplace_source, dict)
        or set(marketplace_source) != {"sourceType", "source"}
        or marketplace_source.get("sourceType") != "local"
        or _path_key(str(marketplace_source.get("source", ""))) != _path_key(target)
    ):
        raise PreparedCodexInstallError("Codex Agency plugin inventory is not exact")
    return _CodexNativeState(
        True,
        bool(plugin["enabled"]),
        version,
        _sha256_json(plugin),
        market_digest,
    )


def _candidate_version(files: Mapping[str, str], primary: str) -> str:
    try:
        manifest = safe_load_bounded_json(files[primary])
    except (TypeError, ValueError) as exc:
        raise PreparedCodexInstallError("generated Codex plugin manifest is invalid") from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or _VERSION.fullmatch(version) is None:
        raise PreparedCodexInstallError("generated Codex plugin version is invalid")
    return version


def _launcher_plan_digest(
    *,
    python_identity: PersistentArtifactIdentity,
    runtime_plan: PrivateRuntimePlan,
) -> str:
    return _sha256_json(
        {
            "bootstrap_path": runtime_plan.bootstrap_path,
            "bootstrap_sha256": runtime_plan.bootstrap_sha256,
            "bootstrap_size": runtime_plan.bootstrap_size,
            "manifest_sha256": runtime_plan.manifest_sha256,
            "python": python_identity.manifest(),
            "runtime_root": runtime_plan.runtime_root,
        }
    )


def _candidate_plan_digest(
    files: Mapping[str, str],
    *,
    launcher_plan_sha256: str,
) -> str:
    return _sha256_json(
        {
            "component_bundle_sha256": _bundle_digest(files),
            "launcher_plan_sha256": launcher_plan_sha256,
        }
    )


def _prepare(
    cfg: AgencyConfig | None = None,
    *,
    home_dir: str | Path | None = None,
) -> _PreparedCodexInstall:
    effective = cfg or load_config(reload=True)
    if not effective.config_path:
        raise PreparedCodexInstallError("prepared Codex refresh requires a bound config path")
    config_path = Path(effective.config_path).resolve()
    target = _codex_target_path(home_dir=home_dir)
    target_snapshot = _target_snapshot(target)
    database, database_identity, roster_generation, host_generation, host_enabled = (
        _database_snapshot(effective)
    )
    if not host_enabled:
        raise PreparedCodexInstallError("prepared Codex refresh requires Codex runtime enabled")
    control_path = runtime_control_path(home_dir=home_dir).resolve()
    control = read_runtime_control_snapshot(path=control_path, use_cache=False)
    if not control.materialized or not control.enabled:
        raise PreparedCodexInstallError(
            "prepared Codex refresh requires an enabled materialized master control"
        )
    source_python, source_bootstrap = launcher_artifact_paths()
    persistent_python = persistent_python_executable(source_python)
    python_identity = snapshot_persistent_artifact(
        persistent_python,
        require_executable=True,
    )
    runtime_plan = plan_private_package_runtime(source_bootstrap)
    planned_paths = (python_identity.lexical_path, runtime_plan.bootstrap_path)
    with bind_launcher_artifact_paths(planned_paths):
        files, primary = bundle_files(
            _HOST,
            effective,
            runtime_control_path_value=str(control_path),
        )
    candidate_version = _candidate_version(files, primary)
    launcher_digest = _launcher_plan_digest(
        python_identity=python_identity,
        runtime_plan=runtime_plan,
    )
    candidate_digest = _candidate_plan_digest(
        files,
        launcher_plan_sha256=launcher_digest,
    )
    argv, environment, codex_version, working_directory = _prepared_codex_argv(home_dir=home_dir)
    native = _strict_native_state(
        argv,
        environment=environment,
        working_directory=working_directory,
        target=target,
    )
    if not native.plugin_present or native.plugin_enabled is not True:
        raise PreparedCodexInstallError(
            "prepared Codex refresh requires the existing Agency plugin enabled"
        )
    executable_identity = argv.persistent_artifact_identities[0]
    binding = _make_binding(
        action=_ACTION,
        host=_HOST,
        config_path=str(config_path),
        config_revision=_configuration_projection(
            effective,
            database=database,
            control_path=control_path,
            control=control,
        ),
        database_path=str(database),
        database_device=database_identity.lexical_device,
        database_inode=database_identity.lexical_inode,
        roster_generation=roster_generation,
        host_control_generation=host_generation,
        runtime_control_generation=control.generation,
        target_path=str(target),
        target_parent_device=target_snapshot.parent_device,
        target_parent_inode=target_snapshot.parent_inode,
        current_install_id=target_snapshot.install_id,
        current_plugin_version=native.plugin_version,
        candidate_plugin_version=candidate_version,
        current_bundle_sha256=target_snapshot.bundle_sha256,
        current_tree_sha256=target_snapshot.tree_sha256,
        candidate_plan_sha256=candidate_digest,
        launcher_plan_sha256=launcher_digest,
        codex_executable_path=executable_identity.lexical_path,
        codex_executable_sha256=executable_identity.sha256,
        codex_executable_identity_sha256=_persistent_identity_digest(executable_identity),
        codex_environment_sha256=_sha256_json(dict(sorted(environment.items()))),
        codex_version=codex_version,
        marketplace_state_sha256=native.marketplace_state_sha256,
        plugin_state_sha256=native.plugin_state_sha256,
    )
    return _PreparedCodexInstall(
        binding=binding,
        target=target,
        target_snapshot=target_snapshot,
        runtime_plan=runtime_plan,
        component_files=dict(files),
        primary_file=primary,
        python_identity=python_identity,
        codex_argv=argv,
        codex_environment=dict(environment),
        codex_working_directory=working_directory,
        native_state=native,
    )


def _published_candidate(
    prepared: _PreparedCodexInstall,
    *,
    publish_runtime: bool,
) -> tuple[dict[str, str], tuple[PersistentArtifactIdentity, ...]] | None:
    runtime_root = Path(prepared.runtime_plan.runtime_root)
    if not runtime_root.exists() and not publish_runtime:
        return None
    bootstrap = (
        prepare_private_package_runtime(prepared.runtime_plan.source_path)
        if publish_runtime
        else verify_private_package_runtime(prepared.runtime_plan.bootstrap_path)
    )
    if _path_key(bootstrap) != _path_key(prepared.runtime_plan.bootstrap_path):
        raise PreparedCodexInstallError("published private runtime does not match its plan")
    bootstrap_identity = snapshot_persistent_artifact(bootstrap)
    if (
        bootstrap_identity.sha256 != prepared.runtime_plan.bootstrap_sha256
        or bootstrap_identity.resolved_size != prepared.runtime_plan.bootstrap_size
    ):
        raise PreparedCodexInstallError("published private runtime content does not match its plan")
    revalidate_persistent_artifacts((prepared.python_identity, bootstrap_identity))
    identities = (prepared.python_identity, bootstrap_identity)
    marker = {
        "schema_version": 1,
        "artifacts": [identity.manifest() for identity in identities],
    }
    files = {
        **prepared.component_files,
        ADAPTER_LAUNCHER_MANIFEST: json.dumps(marker, indent=2) + "\n",
    }
    observed_launcher_digest = _launcher_plan_digest(
        python_identity=prepared.python_identity,
        runtime_plan=prepared.runtime_plan,
    )
    if (
        observed_launcher_digest != prepared.binding.launcher_plan_sha256
        or _candidate_plan_digest(
            prepared.component_files,
            launcher_plan_sha256=observed_launcher_digest,
        )
        != prepared.binding.candidate_plan_sha256
    ):
        raise PreparedCodexInstallError("published Codex candidate changed after preparation")
    return files, identities


def _is_noop(prepared: _PreparedCodexInstall) -> bool:
    candidate = _published_candidate(prepared, publish_runtime=False)
    if candidate is None:
        return False
    files, _identities = candidate
    return bool(
        prepared.native_state.plugin_version == prepared.binding.candidate_plugin_version
        and prepared.native_state.plugin_enabled is True
        and _managed_bundle_matches(prepared.target, _HOST, files)
    )


@contextmanager
def _install_lock(*, home_dir: str | Path | None) -> Iterator[None]:
    from agency_runtime.core.host_lifecycle_lock import (
        HostLifecycleLockError,
        host_integrations_lock,
    )

    try:
        with host_integrations_lock(home_dir=home_dir):
            yield
    except HostLifecycleLockError as exc:
        raise PreparedCodexInstallError("another Codex install transaction is active") from exc


def _native_command(
    prepared: _PreparedCodexInstall,
    arguments: Sequence[str],
    *,
    name: str,
    steps: list[dict[str, Any]],
    timeout: float = 30,
) -> NativeCommandResult:
    result = _run_prepared(
        prepared.codex_argv.with_arguments(arguments),
        environment=prepared.codex_environment,
        working_directory=prepared.codex_working_directory,
        timeout=timeout,
    )
    steps.append({"name": name, **result.to_dict()})
    return result


def _same_frozen_target(
    observed: _ManagedTargetSnapshot,
    expected: _ManagedTargetSnapshot,
    *,
    include_parent: bool,
) -> bool:
    return bool(
        observed.install_id == expected.install_id
        and observed.plugin_version == expected.plugin_version
        and observed.bundle_sha256 == expected.bundle_sha256
        and observed.tree_sha256 == expected.tree_sha256
        and (
            not include_parent
            or (
                observed.parent_device == expected.parent_device
                and observed.parent_inode == expected.parent_inode
            )
        )
    )


def _require_frozen_target(
    target: Path,
    expected: _ManagedTargetSnapshot,
) -> None:
    observed = _target_snapshot(target)
    if not _same_frozen_target(observed, expected, include_parent=True):
        raise PreparedCodexInstallError(
            "managed Codex target changed immediately before atomic publication"
        )


def _frozen_backup_error(
    prepared: _PreparedCodexInstall,
    backup_path: Path,
) -> str | None:
    try:
        observed = _target_snapshot(backup_path)
    except Exception as exc:
        return f"exact Codex backup could not be verified: {type(exc).__name__}: {exc}"
    if not _same_frozen_target(
        observed,
        prepared.target_snapshot,
        include_parent=False,
    ):
        return "exact Codex backup changed after target publication"
    return None


def _published_target_snapshot(
    prepared: _PreparedCodexInstall,
    *,
    expected_bundle: object,
) -> _ManagedTargetSnapshot:
    observed = _target_snapshot(prepared.target)
    if (
        observed.plugin_version != PLUGIN_VERSION
        or observed.bundle_sha256 != expected_bundle
        or observed.parent_device != prepared.target_snapshot.parent_device
        or observed.parent_inode != prepared.target_snapshot.parent_inode
    ):
        raise PreparedCodexInstallError(
            "published Codex target does not match the authorized candidate"
        )
    return observed


def _require_operation_target(
    prepared: _PreparedCodexInstall,
    installed_snapshot: _ManagedTargetSnapshot,
    *,
    message: str,
) -> None:
    observed = _target_snapshot(prepared.target)
    if not _same_frozen_target(
        observed,
        installed_snapshot,
        include_parent=True,
    ):
        raise PreparedCodexInstallError(message)


def _conditional_restore_target(
    prepared: _PreparedCodexInstall,
    *,
    home_dir: str | Path | None,
    backup_path: Path,
    installed_snapshot: _ManagedTargetSnapshot,
) -> tuple[bool, str | None, str | None]:
    try:
        current = _target_snapshot(prepared.target)
    except Exception as exc:
        return (
            False,
            None,
            f"published Codex candidate could not be verified: {type(exc).__name__}: {exc}",
        )
    backup_error = _frozen_backup_error(prepared, backup_path)
    if (
        not _same_frozen_target(current, installed_snapshot, include_parent=True)
        or backup_error is not None
    ):
        return False, None, backup_error or "managed Codex target changed during compensation"
    backup_root = ensure_private_directory(
        runtime_home(home_dir=home_dir) / "backups" / _HOST,
        product_owned=True,
    )
    displaced = backup_root / f"failed-refresh-{time.time_ns()}"
    try:
        os.replace(prepared.target, displaced)
        try:
            os.replace(backup_path, prepared.target)
        except Exception:
            os.replace(displaced, prepared.target)
            raise
    except Exception as exc:
        return False, str(displaced) if displaced.exists() else None, f"{type(exc).__name__}: {exc}"
    try:
        restored = _target_snapshot(prepared.target)
        restored_matches = _same_frozen_target(
            restored,
            prepared.target_snapshot,
            include_parent=True,
        )
    except Exception:
        restored_matches = False
    if not restored_matches:
        reversal_error: str | None = None
        try:
            displaced_snapshot = _target_snapshot(displaced)
            if not _same_frozen_target(
                displaced_snapshot,
                installed_snapshot,
                include_parent=False,
            ):
                raise PreparedCodexInstallError(
                    "displaced Codex candidate changed during compensation"
                )
            if backup_path.exists():
                raise PreparedCodexInstallError(
                    "exact backup path was recreated during compensation"
                )
            os.replace(prepared.target, backup_path)
            os.replace(displaced, prepared.target)
            reversed_candidate = _target_snapshot(prepared.target)
            if not _same_frozen_target(
                reversed_candidate,
                installed_snapshot,
                include_parent=True,
            ):
                raise PreparedCodexInstallError(
                    "reversed Codex candidate does not match its operation receipt"
                )
        except Exception as exc:
            reversal_error = f"{type(exc).__name__}: {exc}"
        if reversal_error is not None:
            return (
                False,
                str(displaced) if displaced.exists() else str(backup_path),
                "restored Codex target was unproven and candidate reversal failed: "
                + reversal_error,
            )
        return (
            False,
            None,
            "restored Codex target was unproven; candidate was restored and backup retained",
        )
    return True, str(displaced), None


def _native_state_or_none(
    prepared: _PreparedCodexInstall,
    *,
    steps: list[dict[str, Any]],
) -> _CodexNativeState | None:
    try:
        return _strict_native_state(
            prepared.codex_argv,
            environment=prepared.codex_environment,
            working_directory=prepared.codex_working_directory,
            target=prepared.target,
            steps=steps,
        )
    except (OSError, RuntimeError, ValueError):
        return None


def _native_state_after_swap_is_safe(
    observed: _CodexNativeState,
    prepared: _PreparedCodexInstall,
) -> bool:
    return bool(
        observed.plugin_present
        and observed.plugin_enabled is True
        and observed.plugin_version
        in {
            prepared.binding.current_plugin_version,
            prepared.binding.candidate_plugin_version,
        }
        and observed.marketplace_state_sha256 == prepared.native_state.marketplace_state_sha256
    )


def _compensate(
    prepared: _PreparedCodexInstall,
    *,
    home_dir: str | Path | None,
    backup_path: Path,
    installed_snapshot: _ManagedTargetSnapshot,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    state = _native_state_or_none(prepared, steps=steps)
    if state is None:
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "error": "Codex native state is ambiguous; retained the candidate and exact backup",
        }
    try:
        current_candidate = _target_snapshot(prepared.target)
    except Exception as exc:
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "error": (
                "published Codex candidate could not be verified before compensation: "
                f"{type(exc).__name__}: {exc}"
            ),
        }
    if not _same_frozen_target(
        current_candidate,
        installed_snapshot,
        include_parent=True,
    ):
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "error": "published Codex candidate changed before compensation",
        }
    prior = prepared.native_state
    candidate_version = prepared.binding.candidate_plugin_version
    candidate_present = bool(
        state.plugin_present
        and state.plugin_enabled is True
        and state.plugin_version == candidate_version
    )
    if (
        state.plugin_present
        and not candidate_present
        and (state.plugin_version != prior.plugin_version or state.plugin_enabled is not True)
    ):
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "error": "Codex plugin state conflicts with both the prior and candidate state",
        }
    backup_error = _frozen_backup_error(prepared, backup_path)
    if backup_error is not None:
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "error": backup_error,
        }
    if candidate_present:
        removed = _native_command(
            prepared,
            ["plugin", "remove", _SELECTOR, "--json"],
            name="compensation_remove_candidate",
            steps=steps,
        )
        if not removed.ok:
            return {
                "compensated": False,
                "manual_recovery_required": True,
                "error": "Codex candidate plugin could not be removed during compensation",
            }
        state = _native_state_or_none(prepared, steps=steps)
        if state is None or state.plugin_present:
            return {
                "compensated": False,
                "manual_recovery_required": True,
                "error": "Codex candidate removal could not be proven during compensation",
            }
    restored, displaced, restore_error = _conditional_restore_target(
        prepared,
        home_dir=home_dir,
        backup_path=backup_path,
        installed_snapshot=installed_snapshot,
    )
    if not restored:
        return {
            "compensated": False,
            "manual_recovery_required": True,
            "displaced_path": displaced,
            "error": restore_error or "Codex marketplace restoration failed",
        }
    if not state.plugin_present:
        added = _native_command(
            prepared,
            ["plugin", "add", _SELECTOR, "--json"],
            name="compensation_restore_plugin",
            steps=steps,
            timeout=60,
        )
        if not added.ok:
            return {
                "compensated": False,
                "manual_recovery_required": True,
                "displaced_path": displaced,
                "error": "prior Codex plugin could not be restored; plugin remains absent",
            }
    final = _native_state_or_none(prepared, steps=steps)
    proven = final == prior
    proof_error = "prior Codex native state could not be proven after restoration"
    if proven:
        try:
            _require_frozen_target(prepared.target, prepared.target_snapshot)
        except Exception:
            proven = False
            proof_error = "prior Codex target changed before compensation completed"
    return {
        "compensated": proven,
        "manual_recovery_required": not proven,
        "displaced_path": displaced,
        "error": None if proven else proof_error,
    }


def _success_result(
    prepared: _PreparedCodexInstall,
    *,
    no_op: bool,
    filesystem: Mapping[str, Any] | None = None,
    native_steps: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "ok": True,
        "complete": True,
        "exit_code": 0,
        "host": _HOST,
        "action": _ACTION,
        "status": "already_current" if no_op else "registered",
        "maturity": "enabled-runtime-unverified",
        "target": str(prepared.target),
        "plugin_path": str(prepared.target / prepared.primary_file),
        "current_plugin_version": prepared.binding.current_plugin_version,
        "candidate_plugin_version": prepared.binding.candidate_plugin_version,
        "candidate_plan_sha256": prepared.binding.candidate_plan_sha256,
        "published_bundle_sha256": (
            (filesystem or {}).get("bundle_digest")
            if filesystem
            else prepared.target_snapshot.bundle_sha256
            if no_op
            else None
        ),
        "binding_sha256": prepared.binding.binding_sha256,
        "filesystem": dict(filesystem or {}),
        "backup_path": (filesystem or {}).get("backup_path"),
        "native_steps": [dict(step) for step in native_steps],
        "registered": True,
        "enabled": True,
        "transaction_complete": True,
        "activation_complete": False,
        "activation_required": True,
        "loaded": None,
        "canary": None,
        "hook_trust_status": "unverified",
        "canary_attestation_invalidated": False,
        "restart_required": not no_op,
        "no_op": no_op,
    }


def _failure_result(
    prepared: _PreparedCodexInstall,
    *,
    exc: Exception,
    backup_path: Path | None,
    steps: Sequence[Mapping[str, Any]],
    partial: bool,
    compensation: Mapping[str, Any],
) -> dict[str, Any]:
    compensated = bool(compensation.get("compensated"))
    manual_recovery = bool(compensation.get("manual_recovery_required"))
    return {
        "ok": False,
        "complete": False,
        "exit_code": 1,
        "host": _HOST,
        "action": _ACTION,
        "status": "compensated_failure" if compensated else "manual_recovery_required",
        "maturity": "activation-required",
        "target": str(prepared.target),
        "backup_path": str(backup_path) if backup_path is not None else None,
        "native_steps": [dict(step) for step in steps],
        "partial": partial and not compensated,
        "error": f"{type(exc).__name__}: {exc}",
        "compensation": dict(compensation),
        "manual_recovery_required": manual_recovery,
        "displaced_path": compensation.get("displaced_path"),
        "stage_path": compensation.get("stage_path"),
        "loaded": None,
        "canary": None,
        "hook_trust_status": "unverified",
    }


def _handle_post_publish_failure(
    prepared: _PreparedCodexInstall,
    *,
    home_dir: str | Path | None,
    backup_path: Path | None,
    installed_snapshot: _ManagedTargetSnapshot | None,
    steps: list[dict[str, Any]],
    exc: Exception,
) -> dict[str, Any]:
    if backup_path is not None and installed_snapshot is None:
        return _failure_result(
            prepared,
            exc=exc,
            backup_path=backup_path,
            steps=steps,
            partial=True,
            compensation={
                "compensated": False,
                "manual_recovery_required": True,
                "error": (
                    "the published target identity is unproven; retained the exact backup "
                    "instead of overwriting ambiguous state"
                ),
            },
        )
    if backup_path is None:
        return _failure_result(
            prepared,
            exc=exc,
            backup_path=None,
            steps=steps,
            partial=True,
            compensation={
                "compensated": False,
                "manual_recovery_required": True,
                "error": (
                    "prepared Codex refresh did not retain its required exact backup; "
                    "refusing native recovery"
                ),
            },
        )
    try:
        compensation = _compensate(
            prepared,
            home_dir=home_dir,
            backup_path=backup_path,
            installed_snapshot=installed_snapshot,
            steps=steps,
        )
    except Exception as recovery_exc:
        compensation = {
            "compensated": False,
            "manual_recovery_required": True,
            "error": (
                "Codex compensation raised before exact recovery could be proven: "
                f"{type(recovery_exc).__name__}: {recovery_exc}"
            ),
        }
    return _failure_result(
        prepared,
        exc=exc,
        backup_path=backup_path,
        steps=steps,
        partial=True,
        compensation=compensation,
    )


def _confirm_noop_under_lock(
    prepared: _PreparedCodexInstall,
    *,
    home_dir: str | Path | None,
) -> dict[str, Any]:
    with _install_lock(home_dir=home_dir):
        current_cfg = load_config(prepared.binding.config_path, reload=True)
        current = _prepare(current_cfg, home_dir=home_dir)
        if current.binding != prepared.binding or not _is_noop(current):
            raise PreparedCodexInstallError(
                "Codex no-op state changed during confirmation; prepare again"
            )
        return _success_result(current, no_op=True)


def _record_published_runtime(
    launcher_identities: Sequence[PersistentArtifactIdentity],
) -> None:
    """Record which projection this refresh published, for drift reports.

    Advisory only: the pointer is read to warn that a hook runs an older
    projection, never to choose what one executes, so a failed write must not
    fail an otherwise complete install.

    This path publishes a runtime but used to record nothing, while the pointer
    it omitted was shared with every other host.  ``agency status`` therefore
    kept reporting Codex as behind after a fully successful Codex install --
    quoting whichever digest the last generic install had left there, and
    naming that host in the remedy.
    """

    from agency_runtime.core.runtime_staleness import record_installed_runtime

    with suppress(IndexError, OSError, ValueError):
        record_installed_runtime(launcher_identities[1].lexical_path, host=_HOST)


def refresh_existing_codex_adapter(
    cfg: AgencyConfig | None = None,
    *,
    home_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Refresh one existing Codex adapter through the prepared positive slice."""

    prepared = _prepare(cfg, home_dir=home_dir)
    if _is_noop(prepared):
        return _confirm_noop_under_lock(prepared, home_dir=home_dir)
    with _install_lock(home_dir=home_dir):
        current_cfg = load_config(prepared.binding.config_path, reload=True)
        current = _prepare(current_cfg, home_dir=home_dir)
        if current.binding != prepared.binding:
            raise PreparedCodexInstallError(
                "prepared Codex install state changed before native registration; prepare again"
            )
        candidate = _published_candidate(prepared, publish_runtime=True)
        if candidate is None:  # pragma: no cover - publication contract
            raise PreparedCodexInstallError("Codex candidate runtime was not published")
        files, launcher_identities = candidate
        revalidate_persistent_artifacts(launcher_identities)
        mutation_cfg = load_config(prepared.binding.config_path, reload=True)
        mutation_current = _prepare(mutation_cfg, home_dir=home_dir)
        if mutation_current.binding != prepared.binding:
            raise PreparedCodexInstallError(
                "prepared Codex install state changed before target publication; prepare again"
            )
        _require_frozen_target(prepared.target, prepared.target_snapshot)
        steps: list[dict[str, Any]] = []
        try:
            filesystem = atomic_install_tree(
                prepared.target,
                files,
                host=_HOST,
                dry_run=False,
                home_dir=home_dir,
                launcher_artifacts=launcher_identities,
                force_replace=True,
                target_precondition=lambda target: _require_frozen_target(
                    target,
                    prepared.target_snapshot,
                ),
            )
        except AtomicInstallTreeError as exc:
            backup_error = (
                _frozen_backup_error(prepared, exc.backup_path)
                if exc.backup_path is not None
                else None
            )
            return _failure_result(
                prepared,
                exc=exc,
                backup_path=exc.backup_path,
                steps=steps,
                partial=True,
                compensation={
                    "compensated": False,
                    "manual_recovery_required": True,
                    "backup_verified": bool(exc.backup_path is not None and backup_error is None),
                    "stage_path": (str(exc.stage_path) if exc.stage_path is not None else None),
                    "recovery_errors": [*exc.recovery_errors],
                    "error": backup_error or str(exc),
                },
            )
        backup_raw = filesystem.get("backup_path")
        backup_path = Path(str(backup_raw)) if backup_raw else None
        installed_snapshot: _ManagedTargetSnapshot | None = None
        try:
            installed_snapshot = _published_target_snapshot(
                prepared,
                expected_bundle=filesystem.get("bundle_digest"),
            )
            native_after_swap = _strict_native_state(
                prepared.codex_argv,
                environment=prepared.codex_environment,
                working_directory=prepared.codex_working_directory,
                target=prepared.target,
                steps=steps,
            )
            if not _native_state_after_swap_is_safe(native_after_swap, prepared):
                raise PreparedCodexInstallError(
                    "Codex native state changed after target publication"
                )
            removed = _native_command(
                prepared,
                ["plugin", "remove", _SELECTOR, "--json"],
                name="plugin_remove_for_refresh",
                steps=steps,
            )
            if not removed.ok:
                raise PreparedCodexInstallError("Codex plugin removal failed")
            absent = _strict_native_state(
                prepared.codex_argv,
                environment=prepared.codex_environment,
                working_directory=prepared.codex_working_directory,
                target=prepared.target,
                steps=steps,
            )
            if (
                absent.plugin_present
                or absent.marketplace_state_sha256 != prepared.native_state.marketplace_state_sha256
            ):
                raise PreparedCodexInstallError("Codex plugin removal was not proven")
            added = _native_command(
                prepared,
                ["plugin", "add", _SELECTOR, "--json"],
                name="plugin_add",
                steps=steps,
                timeout=60,
            )
            if not added.ok:
                raise PreparedCodexInstallError("Codex plugin registration failed")
            final = _strict_native_state(
                prepared.codex_argv,
                environment=prepared.codex_environment,
                working_directory=prepared.codex_working_directory,
                target=prepared.target,
                steps=steps,
            )
            if (
                not final.plugin_present
                or final.plugin_enabled is not True
                or final.plugin_version != prepared.binding.candidate_plugin_version
                or final.marketplace_state_sha256 != prepared.native_state.marketplace_state_sha256
            ):
                raise PreparedCodexInstallError(
                    "Codex plugin postcondition does not match the prepared candidate"
                )
            _require_operation_target(
                prepared,
                installed_snapshot,
                message="published Codex candidate changed before success",
            )
            revalidate_persistent_artifacts(launcher_identities)
            _record_published_runtime(launcher_identities)
            return _success_result(
                prepared,
                no_op=False,
                filesystem=filesystem,
                native_steps=steps,
            )
        except Exception as exc:
            return _handle_post_publish_failure(
                prepared,
                home_dir=home_dir,
                backup_path=backup_path,
                installed_snapshot=installed_snapshot,
                steps=steps,
                exc=exc,
            )


__all__ = [
    "PreparedCodexInstallError",
    "is_exact_prepared_codex_install",
    "refresh_existing_codex_adapter",
]
