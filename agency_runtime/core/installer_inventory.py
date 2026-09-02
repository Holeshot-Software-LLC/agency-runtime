"""Managed bundle inventory, attestations, and host maturity inspection."""

from __future__ import annotations

import hashlib
import os
import platform
import re
import sqlite3
import stat
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _is_link_or_reparse,
)
from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
    CODEX_HOOK_TRUST_ACTION,
    CODEX_HOOK_TRUST_COMMAND,
    CODEX_HOOK_TRUST_SURFACE,
    HOSTS,
    INSTALL_MANIFEST,
    MINIMUM_OPENCLAW_VERSION,
    PLUGIN_ID,
    PLUGIN_VERSION,
    BinaryResolver,
    CommandRunner,
    NativeCommandResult,
    openclaw_version_supported,
)
from agency_runtime.core.process_argv import (
    persistent_artifacts_from_manifest,
    snapshot_persistent_artifacts,
)

_MAX_INSPECTION_WORKERS = len(HOSTS)
_VERSION_TIMEOUT_SECONDS = 8
_INVENTORY_TIMEOUT_SECONDS = 12
_MARKETPLACE_TIMEOUT_SECONDS = 12
_RUNTIME_TIMEOUT_SECONDS = 20
_MAX_INSTALL_MANIFEST_BYTES = 64 * 1024
_MAX_MANAGED_BUNDLE_BYTES = 8 * 1024 * 1024
_MAX_MANAGED_FILES = 512


@dataclass
class _HostInspection:
    """Mutable state for one host while its independent probes run."""

    host: str
    root: Path
    target: Path
    executable: str | None
    root_exists: bool
    current_root: bool
    stale_config: bool
    owned_manifest: Path
    staged: bool
    managed_version: str | None
    install_id: str | None
    bundle_digest: str | None
    launcher_artifacts_current: bool | None
    native_record: dict[str, Any] | None = None
    inventory_result: NativeCommandResult | None = None
    registered: bool | None = None
    enabled: bool | None = None
    loaded: bool | None = None
    marketplace_registered: bool | None = None
    host_version: str | None = None
    host_version_supported: bool | None = None
    evidence: list[str] = field(default_factory=list)


def _facade():
    """Resolve facade dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import installer

    return installer


def _host_root(*args: Any, **kwargs: Any) -> Path:
    return _facade()._host_root(*args, **kwargs)


def _plugin_target(*args: Any, **kwargs: Any) -> Path:
    return _facade()._plugin_target(*args, **kwargs)


def _resolve_binary(*args: Any, **kwargs: Any) -> str | None:
    return _facade()._resolve_binary(*args, **kwargs)


def _root_state(*args: Any, **kwargs: Any) -> tuple[bool, bool, list[str]]:
    return _facade()._root_state(*args, **kwargs)


def _run_native(*args: Any, **kwargs: Any) -> NativeCommandResult:
    return _facade()._run_native(*args, **kwargs)


def _bool_field(*args: Any, **kwargs: Any) -> bool | None:
    return _facade()._bool_field(*args, **kwargs)


def _can_execute_native(*args: Any, **kwargs: Any) -> bool:
    return _facade()._can_execute_native(*args, **kwargs)


def _hermes_text_plugin_record(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return _facade()._hermes_text_plugin_record(*args, **kwargs)


def _json_output(*args: Any, **kwargs: Any) -> Any:
    return _facade()._json_output(*args, **kwargs)


def _marketplace_registered(*args: Any, **kwargs: Any) -> bool:
    return _facade()._marketplace_registered(*args, **kwargs)


def _plugin_record(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return _facade()._plugin_record(*args, **kwargs)


def _inventory_command(host: str) -> list[str]:
    binary = str(HOSTS[host]["binary"])
    if host == "hermes":
        return [binary, "plugins", "list"]
    if host == "openclaw":
        return [binary, "plugins", "list", "--json"]
    if host == "zcode":
        raise ValueError("ZCode inventory is read directly from its hooks config")
    return [binary, "plugin", "list", "--json"]


def _read_canary_attestation(host: str) -> dict[str, Any] | None:
    """Read a canary attestation without creating or migrating the database."""
    path = _facade()._default_db_path()
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'host_canary_attestations'"
            ).fetchone()
            if table is None:
                return None
            row = conn.execute(
                "SELECT host, proof_contract, proof_digest, profile_scope, "
                "platform_system, platform_release, platform_machine, "
                "host_version, plugin_version, install_id, bundle_digest, "
                "passed_at, trace_id "
                "FROM host_canary_attestations WHERE host = ?",
                (host,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return None


def _invalidate_canary_attestation(
    host: str,
    *,
    home_dir: str | Path | None,
) -> bool:
    """Invalidate durable proof after a rollback changes the install lineage."""
    if home_dir is not None and "AGENCY_DB_PATH" not in os.environ:
        return False
    path = _facade()._default_db_path()
    if not path.is_file():
        return False
    try:
        return _facade().Store(path).clear_host_canary_attestation(host)
    except Exception:
        return False


def _stat_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
    )


def _checked_parent_directories(root: Path, path: Path) -> list[tuple[Path, tuple[int, ...]]]:
    relative = path.relative_to(root)
    current = root
    checked: list[tuple[Path, tuple[int, ...]]] = []
    for part in ("", *relative.parts[:-1]):
        if part:
            current /= part
        metadata = os.lstat(current)
        if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(metadata):
            raise OSError(f"unsafe managed bundle directory: {current}")
        checked.append((current, _stat_fingerprint(metadata)))
    return checked


def _verify_parent_directories(checked: Iterable[tuple[Path, tuple[int, ...]]]) -> None:
    for path, expected in checked:
        metadata = os.lstat(path)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or _is_link_or_reparse(metadata)
            or _stat_fingerprint(metadata) != expected
        ):
            raise OSError(f"managed bundle directory changed while reading: {path}")


def _read_regular_file_bounded(path: Path, *, root: Path, limit: int) -> bytes:
    """Read at most ``limit`` bytes from a stable regular file below ``root``."""
    if limit < 0:
        raise OSError("managed bundle byte limit exceeded")
    parents = _checked_parent_directories(root, path)
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or _is_link_or_reparse(before) or before.st_size > limit:
        raise OSError(f"unsafe or oversized managed bundle file: {path}")
    payload = read_bounded_regular_file(path, limit=max(1, limit))
    after_path = os.lstat(path)
    if _stat_fingerprint(after_path) != _stat_fingerprint(before) or _is_link_or_reparse(
        after_path
    ):
        raise OSError(f"managed bundle file changed while reading: {path}")
    _verify_parent_directories(parents)
    if len(payload) > limit:
        raise OSError(f"managed bundle file exceeds byte limit: {path}")
    return payload


def _owned_file_paths(value: Any) -> list[tuple[str, Path]] | None:
    if not isinstance(value, list) or not value or len(value) > _MAX_MANAGED_FILES:
        return None
    normalized: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            return None
        relative = item.replace("\\", "/")
        parts = relative.split("/")
        if (
            not relative
            or len(relative) > 512
            or relative.startswith("/")
            or re.match(r"^[A-Za-z]:", relative)
            or any(ord(character) < 32 for character in relative)
            or any(part in {"", ".", ".."} for part in parts)
            or relative in seen
        ):
            return None
        seen.add(relative)
        normalized.append((relative, Path(*parts)))
    return sorted(normalized)


def _managed_bundle_identity(
    target: Path,
    host: str,
) -> tuple[str | None, str | None, str | None]:
    try:
        raw_manifest = _read_regular_file_bounded(
            target / INSTALL_MANIFEST,
            root=target,
            limit=_MAX_INSTALL_MANIFEST_BYTES,
        )
        manifest = safe_load_bounded_json(raw_manifest)
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None, None, None
    if not isinstance(manifest, dict):
        return None, None, None
    if (
        manifest.get("owner") != "agency-runtime"
        or manifest.get("host") != host
        or manifest.get("plugin_id") != PLUGIN_ID
    ):
        return None, None, None
    version = manifest.get("plugin_version")
    install_id = manifest.get("install_id")
    owned_files = _owned_file_paths(manifest.get("owned_files"))
    if (
        not isinstance(version, str)
        or not version
        or len(version) > 128
        or any(ord(character) < 32 for character in version)
    ):
        return None, None, None
    if (
        not isinstance(install_id, str)
        or not install_id
        or len(install_id) > 128
        or any(ord(character) < 32 for character in install_id)
        or owned_files is None
    ):
        return None, None, None
    digest = hashlib.sha256()
    total_bytes = 0
    try:
        for relative, candidate in owned_files:
            payload = _read_regular_file_bounded(
                target / candidate,
                root=target,
                limit=_MAX_MANAGED_BUNDLE_BYTES - total_bytes,
            )
            total_bytes += len(payload)
            digest.update(relative.replace("\\", "/").encode("utf-8"))
            digest.update(b"\0")
            digest.update(payload)
            digest.update(b"\0")
    except (OSError, ValueError):
        return None, None, None
    return version, install_id, digest.hexdigest()


def _managed_launcher_artifacts_current(target: Path, host: str) -> bool | None:
    """Verify the persisted adapter launcher against live content and trust."""

    try:
        raw_manifest = _read_regular_file_bounded(
            target / INSTALL_MANIFEST,
            root=target,
            limit=_MAX_INSTALL_MANIFEST_BYTES,
        )
        manifest = safe_load_bounded_json(raw_manifest)
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None
    if not isinstance(manifest, dict) or any(
        (
            manifest.get("owner") != "agency-runtime",
            manifest.get("host") != host,
            manifest.get("plugin_id") != PLUGIN_ID,
        )
    ):
        return None
    raw_artifacts = manifest.get("launcher_artifacts")
    if raw_artifacts is None:
        return None
    try:
        expected = persistent_artifacts_from_manifest(raw_artifacts)
        observed = snapshot_persistent_artifacts([identity.lexical_path for identity in expected])
    except (OSError, ValueError):
        return False
    return observed == expected


def _bundle_digest(files: Mapping[str, str]) -> str:
    """Return the canonical digest used for managed bundle identity checks."""
    digest = hashlib.sha256()
    for relative in sorted(files):
        digest.update(relative.replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(files[relative].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _managed_bundle_matches(target: Path, host: str, files: Mapping[str, str]) -> bool:
    """Return whether ``target`` is exactly the requested owned bundle.

    Exactness matters: an unexpected executable file inside a plugin tree must
    force a clean replacement even when every file listed in the ownership
    manifest still has the expected bytes.
    """
    version, _install_id, digest = _managed_bundle_identity(target, host)
    if version != PLUGIN_VERSION or digest != _bundle_digest(files):
        return False
    expected = {Path(relative).as_posix() for relative in files}
    expected.add(INSTALL_MANIFEST)
    actual: set[str] = set()
    try:
        for index, path in enumerate(target.rglob("*")):
            if index >= 512 or path.is_symlink():
                return False
            if path.is_file():
                actual.add(path.relative_to(target).as_posix())
    except OSError:
        return False
    return actual == expected


def _native_plugin_version_matches(host: str, version: str) -> bool:
    """Accept the managed semantic version and Codex content cachebusters."""
    if version == PLUGIN_VERSION:
        return True
    if host != "codex":
        return False
    return bool(
        re.fullmatch(
            rf"{re.escape(PLUGIN_VERSION)}\+codex\.[0-9a-f]{{12}}",
            version,
        )
    )


def _sanitize_host_version(result: NativeCommandResult) -> str | None:
    """Return one bounded printable version line from an allowlisted probe."""
    if not result.ok:
        return None
    raw = result.stdout.strip() or result.stderr.strip()
    line = next((part.strip() for part in raw.splitlines() if part.strip()), "")
    if not line or not re.search(r"\d", line):
        return None
    printable = re.sub(r"[^A-Za-z0-9 ._+:/()\[\]-]", "?", line)
    return printable[:256] or None


def _canary_attestation_state(
    host: str,
    *,
    target: Path,
    registered: bool | None,
    enabled: bool | None,
    native_record: dict[str, Any] | None,
    host_version: str | None,
    managed_version: str | None,
    install_id: str | None,
    bundle_digest: str | None,
    allow_read: bool,
) -> tuple[bool | None, str, list[str], dict[str, Any] | None]:
    attestation = _read_canary_attestation(host) if allow_read else None
    if attestation is None:
        return None, "absent", [], None
    expected_platform = {
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
    }
    stale: list[str] = []
    if attestation.get("proof_contract") != CODEX_ACTIVATION_CANARY_PROOF_CONTRACT:
        stale.append("proof_contract")
    proof_digest = str(attestation.get("proof_digest") or "")
    if len(proof_digest) != 64 or any(
        character not in "0123456789abcdef" for character in proof_digest
    ):
        stale.append("proof_digest")
    if attestation.get("profile_scope") != "current-profile":
        stale.append("profile_scope")
    for platform_field, expected in expected_platform.items():
        if attestation.get(platform_field) != expected:
            stale.append(platform_field)
    if not host_version or attestation.get("host_version") != host_version:
        stale.append("host_version")
    if attestation.get("plugin_version") != PLUGIN_VERSION:
        stale.append("plugin_version")
    if managed_version != PLUGIN_VERSION:
        stale.append("managed_plugin_version")
    if not install_id or attestation.get("install_id") != install_id:
        stale.append("install_id")
    if not bundle_digest or attestation.get("bundle_digest") != bundle_digest:
        stale.append("bundle_digest")
    native_version = (
        str(native_record.get("version") or native_record.get("pluginVersion") or "")
        if native_record
        else ""
    )
    if native_version and not _native_plugin_version_matches(host, native_version):
        stale.append("native_plugin_version")
    if registered is not True or enabled is not True:
        stale.append("native_state")
    if stale:
        return None, "stale", sorted(set(stale)), attestation
    return True, "verified", [], attestation


def _select_hosts(hosts: Iterable[str] | None) -> list[str]:
    requested = set(HOSTS) if hosts is None else {str(host) for host in hosts}
    unknown = sorted(requested.difference(HOSTS))
    if unknown:
        raise ValueError(f"Unknown host(s): {', '.join(unknown)}")
    return [host for host in HOSTS if host in requested]


def _initial_inspection(
    host: str,
    *,
    home_dir: str | Path | None,
    binary_resolver: BinaryResolver | None,
) -> _HostInspection:
    root = _host_root(host, home_dir=home_dir)
    target = _plugin_target(host, home_dir=home_dir)
    executable = _resolve_binary(host, binary_resolver)
    root_exists, current_root, marker_hits = _root_state(host, home_dir=home_dir)
    stale_config = bool(root_exists and not executable and not current_root)
    owned_manifest = target / INSTALL_MANIFEST
    staged = owned_manifest.exists()
    managed_version, install_id, bundle_digest = _managed_bundle_identity(target, host)
    launcher_artifacts_current = _managed_launcher_artifacts_current(target, host)
    state = _HostInspection(
        host=host,
        root=root,
        target=target,
        executable=executable,
        root_exists=root_exists,
        current_root=current_root,
        stale_config=stale_config,
        owned_manifest=owned_manifest,
        staged=staged,
        managed_version=managed_version,
        install_id=install_id,
        bundle_digest=bundle_digest,
        launcher_artifacts_current=launcher_artifacts_current,
    )
    state.evidence = _filesystem_evidence(state, marker_hits)
    return state


def _filesystem_evidence(
    state: _HostInspection,
    marker_hits: Iterable[str | Path],
) -> list[str]:
    evidence = [f"native-marker:{path}" for path in marker_hits]
    if state.executable:
        evidence.insert(0, f"executable:{state.executable}")
    if state.stale_config:
        evidence.append(f"stale-root:{state.root}")
    if state.staged:
        evidence.append(f"owned-stage:{state.owned_manifest}")
        launcher_state = (
            "current"
            if state.launcher_artifacts_current is True
            else "drift"
            if state.launcher_artifacts_current is False
            else "unproven"
        )
        evidence.append(f"launcher-artifacts:{launcher_state}")
    return evidence


def _bounded_exception(exc: Exception) -> str:
    raw = f"{type(exc).__name__}: {exc}"
    return re.sub(r"[\x00-\x1f\x7f]+", " ", raw).strip()[:500]


def _call_native(
    command: list[str],
    *,
    host: str,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    timeout: float,
) -> NativeCommandResult:
    """Run one bounded probe without letting an injected runner abort fan-out."""
    try:
        return _run_native(
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
            _bounded_exception(exc),
        )


def _apply_inventory(state: _HostInspection, result: NativeCommandResult) -> None:
    state.inventory_result = result
    if not result.ok:
        state.evidence.append("native-inventory:error")
        return
    payload = _json_output(result)
    state.native_record = _plugin_record(payload)
    if state.host == "hermes" and payload is None:
        state.native_record = _hermes_text_plugin_record(result.stdout)
        state.registered = state.native_record is not None
        state.enabled = _bool_field(state.native_record, "enabled")
    else:
        state.registered = state.native_record is not None
        state.enabled = _bool_field(state.native_record, "enabled", "active", "isEnabled")
        state.loaded = _bool_field(
            state.native_record,
            "loaded",
            "runtimeLoaded",
            "isLoaded",
        )
    status = "registered" if state.registered else "absent"
    state.evidence.append(f"native-inventory:{status}")


def _probe_marketplace(
    state: _HostInspection,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> None:
    if state.host not in {"codex", "claude"}:
        return
    binary = str(HOSTS[state.host]["binary"])
    result = _call_native(
        [binary, "plugin", "marketplace", "list", "--json"],
        host=state.host,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=_MARKETPLACE_TIMEOUT_SECONDS,
    )
    if result.ok:
        state.marketplace_registered = _marketplace_registered(_json_output(result))


def _runtime_state(loaded: bool | None) -> str:
    if loaded is True:
        return "loaded"
    if loaded is False:
        return "not-loaded"
    return "unproven"


def _probe_openclaw_runtime(
    state: _HostInspection,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    probe_runtime: bool,
) -> None:
    if state.host != "openclaw" or not state.registered or not probe_runtime:
        return
    result = _call_native(
        ["openclaw", "plugins", "inspect", PLUGIN_ID, "--runtime", "--json"],
        host=state.host,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=_RUNTIME_TIMEOUT_SECONDS,
    )
    payload = _json_output(result)
    runtime_record = _plugin_record(payload) or (payload if isinstance(payload, dict) else None)
    state.loaded = (
        _bool_field(runtime_record, "loaded", "runtimeLoaded", "isLoaded") if result.ok else None
    )
    state.evidence.append(f"runtime-inspect:{_runtime_state(state.loaded)}")


def _probe_native_host(
    state: _HostInspection,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    probe_runtime: bool,
) -> None:
    binary = str(HOSTS[state.host]["binary"])
    version = _call_native(
        [binary, "--version"],
        host=state.host,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=_VERSION_TIMEOUT_SECONDS,
    )
    state.host_version = _sanitize_host_version(version)
    proof = "proven" if state.host_version else "unproven"
    state.evidence.append(f"host-version:{proof}")
    if state.host == "openclaw":
        state.host_version_supported = (
            openclaw_version_supported(state.host_version) if state.host_version else None
        )
        capability = (
            "supported"
            if state.host_version_supported is True
            else "unsupported"
            if state.host_version_supported is False
            else "unproven"
        )
        state.evidence.append(f"host-capability:{capability}")
    inventory = _call_native(
        _inventory_command(state.host),
        host=state.host,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=_INVENTORY_TIMEOUT_SECONDS,
    )
    _apply_inventory(state, inventory)
    _probe_marketplace(state, home_dir=home_dir, command_runner=command_runner)
    _probe_openclaw_runtime(
        state,
        home_dir=home_dir,
        command_runner=command_runner,
        probe_runtime=probe_runtime,
    )


def _probe_zcode_config(
    state: _HostInspection,
    *,
    home_dir: str | Path | None,
) -> None:
    from agency_runtime.core.installer_zcode import inspect_zcode_registration

    facts = inspect_zcode_registration(state.target, home_dir=home_dir)
    state.registered = bool(facts["registered"])
    state.enabled = bool(facts["enabled"]) if state.registered else False
    state.loaded = None
    state.native_record = (
        {
            "name": PLUGIN_ID,
            "version": facts.get("version"),
            "enabled": state.enabled,
            "configPath": facts["config_path"],
        }
        if state.registered
        else None
    )
    state.evidence.extend(
        [
            f"zcode-config:{'registered' if state.registered else 'absent'}",
            f"zcode-global-hooks:{facts.get('global_hooks_enabled')}",
            f"zcode-config-drift:{bool(facts.get('drifted'))}",
        ]
    )


def _normalize_registration(state: _HostInspection, *, can_execute: bool) -> None:
    # Staged files are not native registration.  A failed inventory remains
    # unknown, while an install surface that could not be queried is absent.
    native_inventory_ran = bool(
        state.executable and can_execute and state.inventory_result is not None
    )
    if state.registered is None and not native_inventory_ran:
        state.registered = False


def _maturity(state: _HostInspection) -> str:
    if state.staged and state.launcher_artifacts_current is not True:
        return (
            "launcher-artifact-drift"
            if state.launcher_artifacts_current is False
            else "launcher-artifact-unproven"
        )
    if state.host == "openclaw" and state.executable and state.host_version_supported is not True:
        return (
            "host-version-unsupported"
            if state.host_version_supported is False
            else "host-capability-unproven"
        )
    if state.registered is True and state.enabled is True and state.loaded is True:
        return "runtime-verified"
    if state.registered is True and state.enabled is True:
        return "enabled-runtime-unverified"
    if state.registered is True:
        return (
            "registered-enablement-unverified" if state.enabled is None else "registered-disabled"
        )
    if state.registered is None:
        return "staged-registration-unverified" if state.staged else "host-registration-unverified"
    if state.staged:
        return "staged-not-registered"
    if state.executable or state.current_root:
        return "host-discovered"
    if state.stale_config:
        return "stale-config"
    return "absent"


def _inventory_error(result: NativeCommandResult | None) -> str | None:
    if result is None or result.ok:
        return None
    return (result.stderr or result.stdout).strip()[:500]


def _serialize_inspection(
    state: _HostInspection,
    *,
    canary: bool | None,
    attestation_status: str,
    stale_reasons: list[str],
    attestation: dict[str, Any] | None,
) -> dict[str, Any]:
    codex_hooks_registered = state.host == "codex" and state.registered is True
    codex_activation_verified = codex_hooks_registered and canary is True
    native_maturity = _maturity(state)
    return {
        "host": state.host,
        "executable": state.executable,
        "executable_discovered": bool(state.executable),
        "native_root": str(state.root),
        "managed_target": str(state.target),
        "native_root_exists": state.root_exists,
        "current_native_root": state.current_root,
        "stale_config": state.stale_config,
        "discovered": bool(state.executable or state.current_root),
        "staged": state.staged,
        "registered": state.registered,
        "enabled": state.enabled,
        "loaded": state.loaded,
        "canary": canary,
        "canary_attestation_status": attestation_status,
        "canary_stale_reasons": stale_reasons,
        "canary_attestation": attestation,
        "host_version": state.host_version,
        "host_version_supported": state.host_version_supported,
        "minimum_supported_host_version": (
            MINIMUM_OPENCLAW_VERSION if state.host == "openclaw" else None
        ),
        "managed_plugin_version": state.managed_version,
        "install_id": state.install_id,
        "bundle_digest": state.bundle_digest,
        "launcher_artifacts_current": state.launcher_artifacts_current,
        "marketplace_registered": state.marketplace_registered,
        "hook_trust_status": ("trusted" if codex_activation_verified else "unverified")
        if codex_hooks_registered
        else None,
        "hook_trust_action": (
            None
            if codex_activation_verified
            else CODEX_HOOK_TRUST_ACTION
            if codex_hooks_registered
            else None
        ),
        "hook_trust_surface": CODEX_HOOK_TRUST_SURFACE if codex_hooks_registered else None,
        "hook_trust_command": CODEX_HOOK_TRUST_COMMAND if codex_hooks_registered else None,
        "maturity": (
            "runtime-verified"
            if codex_activation_verified
            else "activation-required"
            if codex_hooks_registered
            and state.enabled is True
            and native_maturity == "enabled-runtime-unverified"
            else native_maturity
        ),
        "native_lifecycle": HOSTS[state.host]["native_lifecycle"],
        "evidence": state.evidence,
        "inventory_error": _inventory_error(state.inventory_result),
    }


def _apply_codex_managed_policy_projection(result: dict[str, Any]) -> None:
    """Project system-managed Codex hook authority without confusing it with activation."""

    from agency_runtime.core.codex_managed_policy import inspect_managed_codex_policy

    try:
        policy = inspect_managed_codex_policy()
    except Exception as exc:
        policy = {
            "schema_version": "agency.codex.managed_hooks.inspection.v1",
            "status": "inspection_error",
            "current": False,
            "trust_mode": None,
            "drift_reasons": [f"inspection:{type(exc).__name__}"],
        }
    result["managed_hook_policy"] = policy
    status = str(policy.get("status") or "inspection_error")
    result["evidence"] = [*result.get("evidence", []), f"codex-managed-policy:{status}"]
    if policy.get("current") is True:
        result.update(
            trust_mode="managed_policy",
            hook_trust_status="managed",
            hook_trust_action=None,
            hook_trust_surface="codex-system-policy",
            hook_trust_command=None,
        )
        return
    if status == "absent":
        result["trust_mode"] = "attended"
        return
    reasons = result.get("canary_stale_reasons")
    stale_reasons = (
        [reason for reason in reasons if isinstance(reason, str) and reason]
        if isinstance(reasons, list)
        else []
    )
    if "managed_hook_policy" not in stale_reasons:
        stale_reasons.append("managed_hook_policy")
    if result.get("canary_attestation") is not None:
        result["canary_attestation_status"] = "stale"
    result.update(
        trust_mode="unknown",
        canary=None,
        canary_stale_reasons=stale_reasons,
        hook_trust_status="modified",
        hook_trust_action=(
            "Codex system-managed hook policy is not a current Agency document; repair the "
            "dedicated-container policy or use the attended profile contract."
        ),
        hook_trust_surface="codex-system-policy",
        hook_trust_command=None,
        maturity="activation-required",
    )


def _normalized_chain_evidence(
    host: str,
    executable: str | None,
    home_dir: str | Path | None,
) -> str | None:
    """Repair this host's own trust chains right before an executing probe (AR-368).

    Claude Code rewrites its npm package tree group-writable on every
    invocation, so a chain normalized at install time is broken again by the
    first probe that runs the host -- measured 2026-09-02, ctime moving to each
    invocation. Repairing here, immediately before the probe, is the only point
    where the chain is provably trusted when it is read. The repair is the same
    bounded, owner-only, registry-limited one AR-358 shipped, and it is recorded
    as evidence so it is never silent.
    """

    try:
        from agency_runtime.core.trust_chain_repair import (
            TRUST_CHAIN_HOSTS,
            repair_trust_chains,
            scan_trust_chains,
        )

        if host not in TRUST_CHAIN_HOSTS:
            return None
        inputs = {"home_dir": home_dir, "executables": {host: executable}}
        findings = scan_trust_chains(host, **inputs)
        if not findings:
            return None
        report = repair_trust_chains(findings, consent=True, **inputs)
    except Exception:
        return "trust-chain:unrepairable"
    if not report.applied:
        return "trust-chain:unrepairable"
    return f"trust-chain:normalized:{report.changed}"


def _inspect_host(
    host: str,
    *,
    home_dir: str | Path | None,
    binary_resolver: BinaryResolver | None,
    command_runner: CommandRunner | None,
    probe_runtime: bool,
    can_execute: bool,
    normalize_trust_chains: bool = False,
) -> dict[str, Any]:
    state = _initial_inspection(
        host,
        home_dir=home_dir,
        binary_resolver=binary_resolver,
    )
    normalized: str | None = None
    if host == "zcode":
        _probe_zcode_config(state, home_dir=home_dir)
    elif state.executable and can_execute:
        if normalize_trust_chains:
            normalized = _normalized_chain_evidence(host, state.executable, home_dir)
        _probe_native_host(
            state,
            home_dir=home_dir,
            command_runner=command_runner,
            probe_runtime=probe_runtime,
        )
    _normalize_registration(state, can_execute=can_execute)
    canary, status, stale_reasons, attestation = _canary_attestation_state(
        host,
        target=state.target,
        registered=state.registered,
        enabled=state.enabled,
        native_record=state.native_record,
        host_version=state.host_version,
        managed_version=state.managed_version,
        install_id=state.install_id,
        bundle_digest=state.bundle_digest,
        allow_read=home_dir is None or "AGENCY_DB_PATH" in os.environ,
    )
    if state.staged and state.launcher_artifacts_current is not True:
        canary = None
        status = "stale"
        stale_reasons = [*stale_reasons, "launcher_artifacts"]
        attestation = None
    if normalized is not None:
        state.evidence.append(normalized)
    if status != "absent":
        state.evidence.append(f"canary-attestation:{status}")
    result = _serialize_inspection(
        state,
        canary=canary,
        attestation_status=status,
        stale_reasons=stale_reasons,
        attestation=attestation,
    )
    if host == "codex" and home_dir is None:
        _apply_codex_managed_policy_projection(result)
    elif host == "codex":
        result["managed_hook_policy"] = None
        result["trust_mode"] = "uninspected"
    return result


def _failed_inspection(host: str, exc: Exception) -> dict[str, Any]:
    """Return the stable schema when any host-local inspection probe fails."""
    return {
        "host": host,
        "executable": None,
        "executable_discovered": False,
        "native_root": "",
        "managed_target": "",
        "native_root_exists": False,
        "current_native_root": False,
        "stale_config": False,
        "discovered": False,
        "staged": False,
        "registered": None,
        "enabled": None,
        "loaded": None,
        "canary": None,
        "canary_attestation_status": "inspection-unavailable",
        "canary_stale_reasons": ["host_inspection"],
        "canary_attestation": None,
        "host_version": None,
        "managed_plugin_version": None,
        "install_id": None,
        "bundle_digest": None,
        "launcher_artifacts_current": None,
        "marketplace_registered": None,
        "hook_trust_status": None,
        "hook_trust_action": None,
        "hook_trust_surface": None,
        "hook_trust_command": None,
        "managed_hook_policy": None,
        "trust_mode": None,
        "maturity": "inspection-error",
        "native_lifecycle": HOSTS[host]["native_lifecycle"],
        "evidence": [f"inspection:error:{type(exc).__name__}"],
        "inventory_error": _bounded_exception(exc),
    }


def _safe_inspect_host(host: str, **kwargs: Any) -> dict[str, Any]:
    try:
        return _inspect_host(host, **kwargs)
    except Exception as exc:
        return _failed_inspection(host, exc)


def inspect_host_installations(
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    probe_runtime: bool = False,
    hosts: Iterable[str] | None = None,
    normalize_trust_chains: bool = False,
) -> list[dict[str, Any]]:
    """Inspect hosts concurrently and return results in canonical host order.

    Native commands retain their individual deadlines.  A failure in one host
    becomes host-local evidence and cannot suppress healthy host results.
    ``loaded`` and ``canary`` remain unproven unless native evidence proves them.
    """
    selected_hosts = _select_hosts(hosts)
    if not selected_hosts:
        return []
    can_execute = _can_execute_native(home_dir=home_dir, command_runner=command_runner)
    kwargs = {
        "home_dir": home_dir,
        "binary_resolver": binary_resolver,
        "command_runner": command_runner,
        "probe_runtime": probe_runtime,
        "can_execute": can_execute,
        "normalize_trust_chains": normalize_trust_chains,
    }
    if len(selected_hosts) == 1:
        return [_safe_inspect_host(selected_hosts[0], **kwargs)]
    completed: dict[str, dict[str, Any]] = {}
    worker_count = min(len(selected_hosts), _MAX_INSPECTION_WORKERS)
    with ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="agency-host-inspection",
    ) as executor:
        futures = {
            executor.submit(_safe_inspect_host, host, **kwargs): host for host in selected_hosts
        }
        for future in as_completed(futures):
            host = futures[future]
            try:
                completed[host] = future.result()
            except Exception as exc:
                completed[host] = _failed_inspection(host, exc)
    return [completed[host] for host in selected_hosts]


def inspect_host_installation(
    host: str,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    probe_runtime: bool = False,
    normalize_trust_chains: bool = False,
) -> dict[str, Any]:
    """Inspect one host with the same evidence semantics as the bulk API."""
    return inspect_host_installations(
        home_dir=home_dir,
        binary_resolver=binary_resolver,
        command_runner=command_runner,
        probe_runtime=probe_runtime,
        hosts=(host,),
        normalize_trust_chains=normalize_trust_chains,
    )[0]
