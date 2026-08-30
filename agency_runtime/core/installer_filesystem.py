"""Transactional and ownership-aware installer filesystem operations."""

from __future__ import annotations

import json
import os
import re
import stat
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.installer_contracts import (
    HERMES_BYTECODE_GUARD,
    INSTALL_MANIFEST,
    PLUGIN_ID,
    PLUGIN_VERSION,
)
from agency_runtime.core.private_paths import (
    allocate_private_directory,
    ensure_private_directory,
    remove_private_directory,
)
from agency_runtime.core.process_argv import PersistentArtifactIdentity
from agency_runtime.core.store.security import metadata_is_link_or_reparse_point

_MAX_INSTALL_MANIFEST_BYTES = 64 * 1024
_HERMES_BYTECODE_POLICY = "python-bytecode-cache-denied-v1"


class AtomicInstallTreeError(RuntimeError):
    """An atomic install failed and retained state that needs inspection."""

    def __init__(
        self,
        message: str,
        *,
        backup_path: Path | None,
        stage_path: Path | None,
        recovery_errors: Sequence[str],
    ) -> None:
        super().__init__(message)
        self.backup_path = backup_path
        self.stage_path = stage_path
        self.recovery_errors = tuple(recovery_errors)


def _facade():
    """Resolve facade dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import installer

    return installer


def _safe_relative(*args: Any, **kwargs: Any) -> Path:
    return _facade()._safe_relative(*args, **kwargs)


def _bundle_digest(*args: Any, **kwargs: Any) -> str:
    return _facade()._bundle_digest(*args, **kwargs)


def _managed_bundle_matches(*args: Any, **kwargs: Any) -> bool:
    return _facade()._managed_bundle_matches(*args, **kwargs)


def _runtime_home(*args: Any, **kwargs: Any) -> Path:
    return _facade()._runtime_home(*args, **kwargs)


def _utc_stamp(*args: Any, **kwargs: Any) -> str:
    return _facade()._utc_stamp(*args, **kwargs)


def safe_relative(path: str) -> Path:
    candidate = Path(path)
    if candidate.anchor or ".." in candidate.parts:
        raise ValueError(f"unsafe generated file path: {path}")
    return candidate


def _hermes_bytecode_guard_is_sealed(path: Path) -> bool:
    """Return whether the exact generated cache namespace denies POSIX writes."""

    if os.name == "nt":
        return False
    directory = path / Path(HERMES_BYTECODE_GUARD).parent
    marker = path / HERMES_BYTECODE_GUARD
    try:
        directory_metadata = os.lstat(directory)
        marker_metadata = os.lstat(marker)
    except OSError:
        return False
    return bool(
        not metadata_is_link_or_reparse_point(directory_metadata)
        and stat.S_ISDIR(directory_metadata.st_mode)
        and stat.S_IMODE(directory_metadata.st_mode) == 0o500
        and not metadata_is_link_or_reparse_point(marker_metadata)
        and stat.S_ISREG(marker_metadata.st_mode)
        and stat.S_IMODE(marker_metadata.st_mode) == 0o400
    )


def _set_hermes_bytecode_guard_modes(path: Path, *, readonly: bool) -> None:
    """Seal or unseal only the generated cache guard inside private staging."""

    if os.name == "nt":
        return
    directory = path / Path(HERMES_BYTECODE_GUARD).parent
    marker = path / HERMES_BYTECODE_GUARD
    directory_metadata = os.lstat(directory)
    marker_metadata = os.lstat(marker)
    if (
        metadata_is_link_or_reparse_point(directory_metadata)
        or not stat.S_ISDIR(directory_metadata.st_mode)
        or metadata_is_link_or_reparse_point(marker_metadata)
        or not stat.S_ISREG(marker_metadata.st_mode)
    ):
        raise PermissionError("managed Hermes bytecode guard is unsafe")
    os.chmod(marker, 0o400 if readonly else 0o600, follow_symlinks=False)
    os.chmod(directory, 0o500 if readonly else 0o700, follow_symlinks=False)


def _managed_content_is_current(
    target: Path,
    host: str,
    files: Mapping[str, str],
    *,
    guarded_hermes: bool,
) -> bool:
    current = target.exists() and _managed_bundle_matches(target, host, files)
    return bool(current and (not guarded_hermes or _hermes_bytecode_guard_is_sealed(target)))


def _apply_install_tree_policy(
    path: Path,
    *,
    guarded_hermes: bool,
    readonly: bool,
) -> None:
    if guarded_hermes:
        _set_hermes_bytecode_guard_modes(path, readonly=readonly)


def atomic_install_tree(
    target: Path,
    files: Mapping[str, str],
    *,
    host: str,
    dry_run: bool,
    home_dir: str | Path | None,
    launcher_artifacts: Sequence[PersistentArtifactIdentity] = (),
    force_replace: bool = False,
    target_precondition: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    owned_files = sorted(files)
    guarded_hermes = bool(host == "hermes" and os.name != "nt" and HERMES_BYTECODE_GUARD in files)
    backup_path: Path | None = None
    content_current = _managed_content_is_current(
        target,
        host,
        files,
        guarded_hermes=guarded_hermes,
    )
    unchanged = content_current and not force_replace
    plan = {
        "target": str(target),
        "owned_files": [*owned_files, INSTALL_MANIFEST],
        "bundle_digest": _bundle_digest(files),
        "unchanged": unchanged,
        "would_backup": target.exists() and not unchanged,
        "force_replace": force_replace,
    }
    if dry_run or unchanged:
        return plan

    install_parent = ensure_private_directory(target.parent, product_owned=False)
    stage_identity = allocate_private_directory(
        install_parent,
        prefix=f".{target.name}.staging",
    )
    stage = stage_identity.path
    stamp = _utc_stamp()
    try:
        for relative, content in files.items():
            destination = stage / _safe_relative(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")

        target_present = target.exists()
        if target_present:
            backup_root = ensure_private_directory(
                _runtime_home(home_dir=home_dir) / "backups" / host,
                product_owned=True,
            )
            backup_path = backup_root / stamp

        manifest: dict[str, Any] = {
            "schema_version": 2,
            "owner": "agency-runtime",
            "host": host,
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "install_id": str(uuid.uuid4()),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "target": str(target),
            "owned_files": owned_files,
            "backup_path": str(backup_path) if backup_path else None,
            "launcher_artifacts": [item.manifest() for item in launcher_artifacts],
        }
        if guarded_hermes:
            manifest["tree_write_policy"] = _HERMES_BYTECODE_POLICY
        (stage / INSTALL_MANIFEST).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        _apply_install_tree_policy(stage, guarded_hermes=guarded_hermes, readonly=True)
        if target_precondition is not None:
            target_precondition(target)
        if target_present:
            os.replace(target, backup_path)
        os.replace(stage, target)
    except Exception as exc:
        recovery_errors: list[str] = []
        if backup_path is not None and backup_path.exists() and not target.exists():
            try:
                os.replace(backup_path, target)
            except Exception as recovery_exc:
                recovery_errors.append(
                    f"target restoration failed: {type(recovery_exc).__name__}: {recovery_exc}"
                )
        if stage.exists():
            try:
                _apply_install_tree_policy(
                    stage,
                    guarded_hermes=guarded_hermes,
                    readonly=False,
                )
                remove_private_directory(stage_identity)
            except Exception as cleanup_exc:
                recovery_errors.append(
                    f"stage cleanup failed: {type(cleanup_exc).__name__}: {cleanup_exc}"
                )
        retained_backup = backup_path if backup_path is not None and backup_path.exists() else None
        retained_stage = stage if stage.exists() else None
        if retained_backup is not None or retained_stage is not None or recovery_errors:
            raise AtomicInstallTreeError(
                "atomic install recovery is incomplete",
                backup_path=retained_backup,
                stage_path=retained_stage,
                recovery_errors=recovery_errors,
            ) from exc
        raise

    return {**plan, "backup_path": str(backup_path) if backup_path else None}


def validate_owned_backup(
    path: Path,
    *,
    host: str,
    target: Path,
) -> tuple[bool, str | None, str | None]:
    """Validate that ``path`` is an Agency Runtime bundle for this target."""
    if not path.is_dir():
        return False, "Backup source is not a directory", None
    manifest_path = path / INSTALL_MANIFEST
    try:
        manifest = safe_load_bounded_json(
            read_bounded_regular_file(
                manifest_path,
                limit=_MAX_INSTALL_MANIFEST_BYTES,
                label="backup ownership manifest",
            )
        )
    except FileNotFoundError:
        return (
            False,
            "Backup does not contain an Agency Runtime ownership manifest",
            None,
        )
    except (BoundedJSONError, OSError, UnicodeError, json.JSONDecodeError):
        return False, "Backup ownership manifest is unreadable or invalid", None
    if not isinstance(manifest, dict):
        return False, "Backup ownership manifest must be a JSON object", None

    expected = {
        "owner": "agency-runtime",
        "host": host,
        "plugin_id": PLUGIN_ID,
    }
    if manifest.get("schema_version") not in {1, 2}:
        return False, "Backup ownership manifest has an unexpected schema_version", None
    for field, value in expected.items():
        if manifest.get(field) != value:
            return False, f"Backup ownership manifest has an unexpected {field}", None

    plugin_version = manifest.get("plugin_version")
    if not isinstance(plugin_version, str) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?",
        plugin_version,
    ):
        return False, "Backup ownership manifest has an invalid plugin_version", None

    manifest_target = manifest.get("target")
    if not isinstance(manifest_target, str) or not manifest_target.strip():
        return False, "Backup ownership manifest has no target", None
    try:
        recorded_target = Path(manifest_target).expanduser().resolve()
    except (OSError, RuntimeError):
        return False, "Backup ownership manifest target is invalid", None
    if recorded_target != target.resolve():
        return False, "Backup ownership manifest target does not match this host", None

    owned_files = manifest.get("owned_files")
    if not isinstance(owned_files, list) or not all(isinstance(item, str) for item in owned_files):
        return False, "Backup ownership manifest has an invalid owned_files list", None
    return True, None, plugin_version


def _strict_install_manifest(
    path: Path,
    *,
    host: str,
    target: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    valid, error, _version = validate_owned_backup(path, host=host, target=target)
    if not valid:
        return None, error
    try:
        manifest = safe_load_bounded_json(
            read_bounded_regular_file(
                path / INSTALL_MANIFEST,
                limit=_MAX_INSTALL_MANIFEST_BYTES,
                label="install ownership manifest",
            )
        )
    except (BoundedJSONError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"Install ownership manifest is unreadable: {type(exc).__name__}"
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
        return None, "Install ownership manifest is not an uninstallable schema"
    install_id = manifest.get("install_id")
    try:
        canonical_install_id = str(uuid.UUID(str(install_id)))
    except (AttributeError, ValueError):
        return None, "Install ownership manifest has an invalid install_id"
    if install_id != canonical_install_id:
        return None, "Install ownership manifest has a noncanonical install_id"
    return dict(manifest), None


def _expected_install_entries(
    manifest: Mapping[str, Any],
) -> tuple[set[str] | None, set[str] | None, str | None]:
    owned = manifest.get("owned_files")
    if (
        not isinstance(owned, list)
        or not owned
        or len(owned) > 512
        or not all(isinstance(item, str) for item in owned)
        or len(set(owned)) != len(owned)
    ):
        return None, None, "Install ownership manifest has an invalid owned_files set"
    try:
        expected_files = {_safe_relative(item).as_posix() for item in owned}
    except (TypeError, ValueError):
        return None, None, "Install ownership manifest contains an unsafe owned file"
    comparison = [item.casefold() if os.name == "nt" else item for item in expected_files]
    if len(set(comparison)) != len(comparison) or any(
        not item
        or any(ord(character) < 32 for character in item)
        or (os.name == "nt" and ":" in item)
        for item in expected_files
    ):
        return None, None, "Install ownership manifest contains an ambiguous owned file"
    if INSTALL_MANIFEST in expected_files:
        return None, None, "Install ownership manifest lists itself as an owned file"
    expected_files.add(INSTALL_MANIFEST)
    expected_directories: set[str] = set()
    for relative in expected_files:
        parent = Path(relative).parent
        while parent != Path("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    return expected_files, expected_directories, None


def _observed_install_entries(
    path: Path,
) -> tuple[set[str] | None, set[str] | None, str | None]:
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    stack: list[tuple[Path, Path]] = [(path, Path())]
    entries = 0
    try:
        while stack:
            directory, relative_root = stack.pop()
            with os.scandir(directory) as children:
                for child in children:
                    entries += 1
                    if entries > 1024:
                        return None, None, "Install tree exceeds the bounded entry count"
                    metadata = child.stat(follow_symlinks=False)
                    if metadata_is_link_or_reparse_point(metadata):
                        return None, None, "Install tree contains a link or reparse point"
                    relative = relative_root / child.name
                    normalized = relative.as_posix()
                    if stat.S_ISDIR(metadata.st_mode):
                        actual_directories.add(normalized)
                        stack.append((Path(child.path), relative))
                    elif stat.S_ISREG(metadata.st_mode):
                        actual_files.add(normalized)
                    else:
                        return None, None, "Install tree contains a non-regular entry"
    except OSError as exc:
        return None, None, f"Install tree could not be inspected: {type(exc).__name__}"
    return actual_files, actual_directories, None


def validate_owned_install_tree(
    path: Path,
    *,
    host: str,
    target: Path,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Validate one exact current install without requiring the current version.

    Uninstall may remove an older legitimate Agency bundle, but it must never
    move a tree containing unlisted user files or links.  Schema 2 provides the
    unique install identity required for that destructive boundary.
    """

    manifest, error = _strict_install_manifest(path, host=host, target=target)
    if manifest is None:
        return False, error, None
    expected_files, expected_directories, error = _expected_install_entries(manifest)
    if expected_files is None or expected_directories is None:
        return False, error, None
    actual_files, actual_directories, error = _observed_install_entries(path)
    if actual_files is None or actual_directories is None:
        return False, error, None
    if actual_files != expected_files or actual_directories != expected_directories:
        return False, "Install tree contains missing or unexpected entries", None
    if manifest.get("tree_write_policy") == _HERMES_BYTECODE_POLICY and not (
        os.name != "nt" and _hermes_bytecode_guard_is_sealed(path)
    ):
        return False, "Install tree violates its Hermes bytecode-cache policy", None
    return True, None, manifest
