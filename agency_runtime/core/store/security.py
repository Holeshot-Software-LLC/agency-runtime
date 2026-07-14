"""Filesystem security primitives for the SQLite canonical store."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path

from agency_runtime.core.windows_acl import (
    restrict_windows_acl as _restrict_windows_acl,
)


def restrict_windows_acl(
    path: Path,
    *,
    directory: bool,
    is_windows: bool,
) -> bool:
    """Delegate Windows DACL enforcement to the shared access-safe primitive."""

    return _restrict_windows_acl(
        path,
        directory=directory,
        is_windows=is_windows,
    )


def restrict_path_permissions(
    path: Path,
    *,
    directory: bool,
    is_windows: bool,
    link_checker: Callable[[Path], bool],
    windows_acl: Callable[..., bool],
) -> None:
    """Repair storage permissions; unsupported filesystems fail closed enough."""

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if link_checker(path) or metadata_is_link_or_reparse_point(metadata):
        raise PermissionError("refusing Agency Runtime storage symlink or reparse point")
    expected_kind = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if not expected_kind:
        kind = "directory" if directory else "regular file"
        raise PermissionError(f"Agency Runtime storage must be a {kind}: {path}")
    if is_windows:
        if not windows_acl(path, directory=directory):
            current = path.lstat()
            if link_checker(path) or metadata_is_link_or_reparse_point(current):
                raise PermissionError("refusing Agency Runtime storage symlink or reparse point")
            raise PermissionError(
                f"could not enforce private Windows ACL on Agency Runtime storage: {path}"
            )
        return
    expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
    os.chmod(path, expected_mode)
    actual_mode = stat.S_IMODE(path.stat().st_mode)
    if actual_mode != expected_mode:
        raise PermissionError(
            f"could not enforce private permissions on Agency Runtime storage: {path}"
        )


def default_db_path() -> Path:
    """Resolve DB path from config, honoring the environment per call."""

    if env_path := os.environ.get("AGENCY_DB_PATH"):
        return Path(os.path.expanduser(env_path))
    try:
        from agency_runtime.core.config import load_config

        return load_config().store.resolved_path()
    except Exception:
        return Path.home() / ".agency-runtime" / "agency.db"


def default_runtime_directory() -> Path:
    """Return the one pre-existing directory Agency Runtime owns by convention."""

    return Path.home() / ".agency-runtime"


def is_link_or_reparse_point(path: Path) -> bool:
    """Reject links before permission repair or SQLite can follow their target."""

    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    return metadata_is_link_or_reparse_point(metadata)


def metadata_is_link_or_reparse_point(metadata: os.stat_result) -> bool:
    """Classify one lstat result without repeating a filesystem lookup."""

    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def sqlite_storage_paths(db_path: Path) -> tuple[Path, ...]:
    """Return every deterministic file SQLite may open beside one database."""

    return (
        db_path,
        Path(f"{db_path}-journal"),
        Path(f"{db_path}-wal"),
        Path(f"{db_path}-shm"),
    )
