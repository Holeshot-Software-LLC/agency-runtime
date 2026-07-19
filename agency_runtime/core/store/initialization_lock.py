"""Secure, bounded interprocess serialization for SQLite initialization."""

from __future__ import annotations

import hashlib
import math
import os
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import BinaryIO

from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    is_link_or_reparse_point,
    metadata_is_link_or_reparse_point,
    restrict_path_permissions,
    restrict_windows_acl,
    storage_file_is_trusted,
    storage_parent_is_trusted,
)

DEFAULT_INITIALIZATION_LOCK_TIMEOUT_SECONDS = 15.0
MAX_INITIALIZATION_LOCK_TIMEOUT_SECONDS = 300.0
_LOCK_RETRY_SECONDS = 0.025
_OPEN_RETRIES = 8
_IS_WINDOWS = os.name == "nt"


class StorageInitializationLockError(RuntimeError):
    """Base class for a SQLite initialization-lock failure."""


class StorageInitializationBusyError(StorageInitializationLockError):
    """Raised when another constructor owns the lock past the deadline."""


class StorageInitializationLockSecurityError(StorageInitializationLockError):
    """Raised when the durable lock identity or parent is unsafe."""


@dataclass(frozen=True, slots=True)
class _LockIdentity:
    path: Path
    device: int
    inode: int


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def initialization_lock_path(db_path: Path) -> Path:
    """Return one bounded, deterministic lock name adjacent to the database."""

    target = _absolute(db_path)
    normalized = os.path.normcase(str(target)).encode("utf-8", errors="surrogatepass")
    digest = hashlib.sha256(normalized).hexdigest()
    return target.parent / f".agency-init-{digest}.lock"


def _validate_timeout(timeout: float) -> float:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or not 0 <= float(timeout) <= MAX_INITIALIZATION_LOCK_TIMEOUT_SECONDS
    ):
        raise ValueError("initialization lock timeout must be finite and between 0 and 300 seconds")
    return float(timeout)


def _validate_parent(parent: Path) -> None:
    try:
        assert_storage_parent_chain(parent, allow_missing=False)
    except (OSError, PermissionError) as exc:
        raise StorageInitializationLockSecurityError(
            "SQLite initialization lock parent is not a stable directory chain"
        ) from exc
    if not storage_parent_is_trusted(parent, is_windows=_IS_WINDOWS):
        raise StorageInitializationLockSecurityError(
            "SQLite initialization lock parent is not owner-private"
        )


def _valid_lock_metadata(metadata: os.stat_result) -> bool:
    return bool(
        not metadata_is_link_or_reparse_point(metadata)
        and stat.S_ISREG(metadata.st_mode)
        and int(getattr(metadata, "st_ino", 0) or 0) > 0
        and int(getattr(metadata, "st_nlink", 0) or 0) == 1
    )


def _capture_open_identity(
    path: Path,
    handle: BinaryIO,
) -> _LockIdentity:
    try:
        opened = os.fstat(handle.fileno())
        current = os.lstat(path)
    except OSError as exc:
        raise StorageInitializationLockSecurityError(
            "SQLite initialization lock identity could not be inspected"
        ) from exc
    if (
        not _valid_lock_metadata(opened)
        or not _valid_lock_metadata(current)
        or not os.path.samestat(opened, current)
    ):
        raise StorageInitializationLockSecurityError(
            "SQLite initialization lock changed during open"
        )
    return _LockIdentity(path, int(opened.st_dev), int(opened.st_ino))


def _identity_is_current(identity: _LockIdentity, handle: BinaryIO) -> bool:
    try:
        opened = os.fstat(handle.fileno())
        current = os.lstat(identity.path)
    except OSError:
        return False
    return bool(
        _valid_lock_metadata(opened)
        and _valid_lock_metadata(current)
        and int(opened.st_dev) == identity.device
        and int(getattr(opened, "st_ino", 0) or 0) == identity.inode
        and os.path.samestat(opened, current)
        and storage_file_is_trusted(identity.path, is_windows=_IS_WINDOWS)
    )


def _restrict_lock(path: Path) -> None:
    restrict_path_permissions(
        path,
        directory=False,
        is_windows=_IS_WINDOWS,
        link_checker=is_link_or_reparse_point,
        windows_acl=lambda candidate, *, directory: restrict_windows_acl(
            candidate,
            directory=directory,
            is_windows=_IS_WINDOWS,
        ),
    )


def _open_lock(path: Path) -> tuple[BinaryIO, _LockIdentity]:
    flags = os.O_RDWR | int(getattr(os, "O_CLOEXEC", 0))
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    for _attempt in range(_OPEN_RETRIES):
        try:
            descriptor = os.open(
                path,
                flags | os.O_CREAT | os.O_EXCL,
                stat.S_IRUSR | stat.S_IWUSR,
            )
        except FileExistsError:
            if is_link_or_reparse_point(path):
                raise StorageInitializationLockSecurityError(
                    "refusing SQLite initialization lock symlink or reparse point"
                ) from None
            try:
                descriptor = os.open(path, flags)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise StorageInitializationLockSecurityError(
                    "SQLite initialization lock could not be opened"
                ) from exc
        except OSError as exc:
            raise StorageInitializationLockSecurityError(
                "SQLite initialization lock could not be created"
            ) from exc

        handle = os.fdopen(descriptor, "r+b", buffering=0)
        try:
            identity = _capture_open_identity(path, handle)
            _restrict_lock(path)
            if not _identity_is_current(identity, handle):
                raise StorageInitializationLockSecurityError(
                    "SQLite initialization lock is not an unchanged owner-private file"
                )
            size = os.fstat(handle.fileno()).st_size
            if size == 0:
                handle.seek(0)
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            elif size != 1:
                raise StorageInitializationLockSecurityError(
                    "SQLite initialization lock has invalid content length"
                )
            if not _identity_is_current(identity, handle):
                raise StorageInitializationLockSecurityError(
                    "SQLite initialization lock changed during preparation"
                )
            return handle, identity
        except BaseException:
            handle.close()
            raise
    raise StorageInitializationLockSecurityError(
        "SQLite initialization lock changed repeatedly during open"
    )


def _try_acquire(handle: BinaryIO) -> None:
    handle.seek(0)
    if _IS_WINDOWS:
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _release(handle: BinaryIO) -> None:
    handle.seek(0)
    if _IS_WINDOWS:
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _acquire_bounded(handle: BinaryIO, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            _try_acquire(handle)
            return
        except OSError as exc:
            if time.monotonic() >= deadline:
                raise StorageInitializationBusyError(
                    "SQLite initialization is busy; retry the operation"
                ) from exc
            time.sleep(min(_LOCK_RETRY_SECONDS, max(0.0, deadline - time.monotonic())))


@contextmanager
def storage_initialization_lock(
    db_path: Path,
    *,
    timeout: float = DEFAULT_INITIALIZATION_LOCK_TIMEOUT_SECONDS,
) -> Iterator[Path]:
    """Hold one persistent path lock across creation, initialization, and rollback."""

    bounded_timeout = _validate_timeout(timeout)
    target = _absolute(db_path)
    _validate_parent(target.parent)
    lock_path = initialization_lock_path(target)
    handle, identity = _open_lock(lock_path)
    acquired = False
    body_error: BaseException | None = None
    cleanup_error: BaseException | None = None
    try:
        _acquire_bounded(handle, timeout=bounded_timeout)
        acquired = True
        if not _identity_is_current(identity, handle):
            raise StorageInitializationLockSecurityError(
                "SQLite initialization lock changed after acquisition"
            )
        try:
            yield lock_path
        except BaseException as exc:
            body_error = exc
            raise
    finally:
        if acquired:
            try:
                if not _identity_is_current(identity, handle):
                    raise StorageInitializationLockSecurityError(
                        "SQLite initialization lock changed while held"
                    )
            except BaseException as exc:
                cleanup_error = exc
            try:
                _release(handle)
            except BaseException as exc:
                if cleanup_error is None:
                    cleanup_error = exc
                else:
                    cleanup_error.add_note(f"SQLite initialization unlock also failed: {exc}")
        handle.close()
        if cleanup_error is not None:
            if body_error is not None:
                body_error.add_note(f"SQLite initialization lock cleanup failed: {cleanup_error}")
            else:
                raise cleanup_error


__all__ = [
    "DEFAULT_INITIALIZATION_LOCK_TIMEOUT_SECONDS",
    "MAX_INITIALIZATION_LOCK_TIMEOUT_SECONDS",
    "StorageInitializationBusyError",
    "StorageInitializationLockError",
    "StorageInitializationLockSecurityError",
    "initialization_lock_path",
    "storage_initialization_lock",
]
