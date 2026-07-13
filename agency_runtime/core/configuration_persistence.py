"""Bounded reads, private atomic writes, and cross-process config locking."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

import yaml

from agency_runtime.core.bounded_io import FileSizeLimitError, read_bounded_regular_file
from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded
from agency_runtime.core.configuration_contracts import (
    LOCK_TIMEOUT_SECONDS,
    MAX_CONFIG_BYTES,
    ConfigLockError,
    ConfigurationError,
    ConfigValidationError,
)
from agency_runtime.core.windows_acl import (
    WindowsACLSafetyError,
    restrict_windows_acl,
)

PermissionRestrictor = Callable[..., bool]
PathCheck = Callable[[Path], bool]


def resolve_config_path(path: str | Path | None = None) -> Path:
    """Resolve the write target, including a nonexistent env-overridden path."""

    if path is not None:
        return Path(path).expanduser()
    configured = os.environ.get("AGENCY_CONFIG_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".agency-runtime" / "agency.yaml"


def revision(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def read_raw(path: Path) -> bytes:
    """Read at most one byte beyond the accepted config size."""

    try:
        raw = read_bounded_regular_file(
            path,
            limit=MAX_CONFIG_BYTES,
            label="configuration file",
        )
    except FileNotFoundError:
        return b""
    except FileSizeLimitError as exc:
        raise ConfigValidationError("configuration file exceeds the size limit") from exc
    except OSError as exc:
        raise ConfigurationError("configuration file could not be read") from exc
    return raw


def parse_document(raw: bytes) -> dict[str, Any]:
    try:
        loaded = safe_load_bounded(raw)
    except (BoundedYAMLError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigValidationError("configuration file is not valid UTF-8 YAML") from exc
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigValidationError("configuration root must be a mapping")
    return loaded


def read_document(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = read_raw(path)
    return parse_document(raw), raw


def is_link_or_reparse_point(path: Path) -> bool:
    """Return whether a path can redirect a security-sensitive operation."""

    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def restrict_permissions(
    path: Path,
    *,
    required: bool = False,
    directory: bool = False,
    is_windows: bool | None = None,
    windows_acl: Callable[..., bool] | None = None,
    path_check: PathCheck = is_link_or_reparse_point,
) -> bool:
    if path_check(path):
        raise ConfigurationError("refusing to modify a symlink or reparse point")
    windows = os.name == "nt" if is_windows is None else is_windows
    if windows:
        acl = windows_acl or restrict_windows_acl
        try:
            restricted = acl(path, directory=True) if directory else acl(path)
        except WindowsACLSafetyError as exc:
            raise ConfigurationError(str(exc)) from exc
        if required and not restricted:
            raise ConfigurationError("owner-only file permissions could not be enforced")
        return restricted
    expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
    os.chmod(path, expected_mode)
    if stat.S_IMODE(path.stat().st_mode) != expected_mode:
        if required:
            raise ConfigurationError("owner-only file permissions could not be enforced")
        return False
    return True


def ensure_config_parent(
    path: Path,
    *,
    restrict: PermissionRestrictor = restrict_permissions,
    path_check: PathCheck = is_link_or_reparse_point,
) -> None:
    """Create a private target directory without taking over arbitrary parents."""

    parent = path.parent
    try:
        parent.mkdir(parents=True, exist_ok=False, mode=0o700)
    except FileExistsError:
        created = False
    else:
        created = True
    if path_check(parent):
        raise ConfigurationError("refusing configuration directory symlink or reparse point")
    default_parent = Path.home() / ".agency-runtime"
    owned = bool(created or os.path.abspath(parent) == os.path.abspath(default_parent))
    if owned:
        restrict(parent, required=True, directory=True)


def atomic_write_yaml(
    path: Path,
    document: Mapping[str, Any],
    *,
    ensure_parent: Callable[[Path], None],
    restrict: PermissionRestrictor,
    preflight: Callable[[Path], None],
    path_check: PathCheck = is_link_or_reparse_point,
    is_windows: bool | None = None,
) -> None:
    """Securely validate and atomically replace a YAML configuration."""

    path = path.expanduser()
    if path_check(path):
        raise ConfigurationError("refusing to replace a configuration symlink or reparse point")
    ensure_parent(path)
    payload = yaml.safe_dump(
        dict(document),
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_CONFIG_BYTES:
        raise ConfigValidationError("configuration exceeds the size limit")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)
        restrict(temporary, required=True)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            fd = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        restrict(temporary, required=True)
        preflight(temporary)
        os.replace(temporary, path)
        windows = os.name == "nt" if is_windows is None else is_windows
        if not windows:
            restrict(path, required=True)
            try:
                directory_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
    finally:
        if fd >= 0:
            os.close(fd)
        with suppress(FileNotFoundError):
            temporary.unlink()


@contextmanager
def config_lock(
    path: Path,
    *,
    timeout: float = LOCK_TIMEOUT_SECONDS,
    ensure_parent: Callable[[Path], None],
    restrict: PermissionRestrictor,
    path_check: PathCheck = is_link_or_reparse_point,
    is_windows: bool | None = None,
) -> Iterator[None]:
    """Acquire a cooperative one-byte lock adjacent to the config file."""

    ensure_parent(path)
    lock_path = path.with_name(f".{path.name}.lock")
    if path_check(lock_path):
        raise ConfigLockError("refusing configuration lock symlink or reparse point")
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        raise ConfigLockError("configuration lock could not be opened safely") from exc
    handle = os.fdopen(descriptor, "r+b")
    windows = os.name == "nt" if is_windows is None else is_windows
    try:
        if path_check(lock_path) or not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ConfigLockError("refusing configuration lock symlink or non-regular file")
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        if hasattr(os, "fchmod"):
            os.fchmod(handle.fileno(), stat.S_IRUSR | stat.S_IWUSR)
        elif windows:
            restrict(lock_path)
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                handle.seek(0)
                if windows:
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise ConfigLockError("configuration is busy; retry the operation") from exc
                time.sleep(0.025)
        try:
            yield
        finally:
            handle.seek(0)
            if windows:
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()
