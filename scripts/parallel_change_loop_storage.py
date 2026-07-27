"""Identity-safe storage and lock primitives for the local parallel test loop."""

from __future__ import annotations

import os
import re
import secrets
import stat
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import BinaryIO

from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.private_paths import (
    PrivateDirectoryIdentity,
    ensure_private_directory,
    remove_private_directory,
    validate_private_directory,
)
from agency_runtime.core.windows_acl import (
    restrict_windows_acl,
    windows_file_prevents_untrusted_mutation,
)

_LOCK_POLL_SECONDS = 0.025
_MAX_TEMP_CREATE_ATTEMPTS = 16
_LATEST_LOG_NAME = re.compile(r"pytest-shard-[0-9]{2,6}\.latest\.log")


class PrivateRuntimeLockCleanupError(RuntimeError):
    """Bounded public signal that a private lock could not be released cleanly."""

    failure_category = "cleanup"
    cleanup_component = "lock"


def capture_private_directory_identity(path: Path) -> PrivateDirectoryIdentity:
    private = validate_private_directory(path)
    metadata = os.lstat(private)
    inode = int(getattr(metadata, "st_ino", 0) or 0)
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
        or inode <= 0
    ):
        raise RuntimeError("parallel test directory identity is unavailable")
    return PrivateDirectoryIdentity(path=private, device=int(metadata.st_dev), inode=inode)


def _file_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(getattr(metadata, "st_ino", 0) or 0),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_nlink", 0) or 0),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
    )


def _owner_trusted_file(path: Path, metadata: os.stat_result) -> bool:
    if os.name == "nt":
        return windows_file_prevents_untrusted_mutation(path, is_windows=True)
    uid_getter = getattr(os, "geteuid", None)
    return bool(callable(uid_getter) and int(metadata.st_uid) == int(uid_getter()))


def exact_private_file_is_valid(path: Path, expected: bytes) -> bool:
    """Read an exact owner-trusted receipt through one bounded no-follow handle."""

    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.lstat(path)
        if (
            metadata_is_link_or_reparse_point(before)
            or not stat.S_ISREG(before.st_mode)
            or int(getattr(before, "st_nlink", 0) or 0) != 1
            or int(before.st_size) != len(expected)
            or not _owner_trusted_file(path, before)
        ):
            return False
        descriptor = os.open(path, flags)
    except OSError:
        return False
    try:
        opened = os.fstat(descriptor)
        if _file_identity(opened) != _file_identity(before):
            return False
        payload = os.read(descriptor, len(expected) + 1)
        after_handle = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = os.lstat(path)
    except OSError:
        return False
    return bool(
        payload == expected
        and _file_identity(after_handle) == _file_identity(opened)
        and _file_identity(after_path) == _file_identity(opened)
        and _owner_trusted_file(path, after_path)
    )


def _write_all(descriptor: int, payload: bytes) -> None:
    pending = memoryview(payload)
    while pending:
        written = os.write(descriptor, pending)
        if written <= 0:
            raise OSError("short private file write")
        pending = pending[written:]


def _rollback_created_file(
    path: Path,
    identity: tuple[int, int],
    error: BaseException,
) -> None:
    try:
        current = os.lstat(path)
        if (
            metadata_is_link_or_reparse_point(current)
            or not stat.S_ISREG(current.st_mode)
            or (int(current.st_dev), int(getattr(current, "st_ino", 0) or 0)) != identity
        ):
            raise RuntimeError("created private file identity changed")
        path.unlink()
    except BaseException as cleanup_error:
        add_exception_note(
            error,
            f"private receipt rollback failed ({type(cleanup_error).__name__})",
        )


def create_exact_private_file(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        if not exact_private_file_is_valid(path, payload):
            raise RuntimeError("parallel test ownership receipt is invalid") from exc
        return
    try:
        opened = os.fstat(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    identity = (int(opened.st_dev), int(getattr(opened, "st_ino", 0) or 0))
    try:
        try:
            if os.name != "nt":
                os.fchmod(descriptor, 0o600)
            _write_all(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if os.name == "nt" and not restrict_windows_acl(path, directory=False, is_windows=True):
            raise RuntimeError("parallel test ownership receipt ACL could not be restricted")
        if not exact_private_file_is_valid(path, payload):
            raise RuntimeError("parallel test ownership receipt could not be attested")
    except BaseException as exc:
        _rollback_created_file(path, identity, exc)
        raise


def _lock_metadata_is_safe(path: Path, handle: BinaryIO) -> bool:
    try:
        opened = os.fstat(handle.fileno())
        current = os.lstat(path)
    except OSError:
        return False
    return bool(
        _file_identity(opened) == _file_identity(current)
        and not metadata_is_link_or_reparse_point(opened)
        and stat.S_ISREG(opened.st_mode)
        and int(getattr(opened, "st_nlink", 0) or 0) == 1
        and int(opened.st_size) == 1
        and _owner_trusted_file(path, opened)
    )


def _try_lock(handle: BinaryIO) -> bool:
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def private_runtime_lock(path: Path, *, wait_seconds: float, busy_message: str) -> Iterator[None]:
    """Hold one non-inherited owner-private byte lock for a bounded interval."""

    flags = os.O_CREAT | os.O_RDWR
    flags |= int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    descriptor = os.open(path, flags, 0o600)
    try:
        handle = os.fdopen(descriptor, "r+b", buffering=0)
    except BaseException:
        os.close(descriptor)
        raise
    locked = False
    primary_error: BaseException | None = None
    try:
        if os.name != "nt":
            os.fchmod(handle.fileno(), 0o600)
        elif not restrict_windows_acl(path, directory=False, is_windows=True):
            raise RuntimeError("parallel test lock ACL could not be restricted")
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        if not _lock_metadata_is_safe(path, handle):
            raise RuntimeError("parallel test lock is unsafe")
        deadline = time.monotonic() + wait_seconds
        while not (locked := _try_lock(handle)):
            if time.monotonic() >= deadline:
                raise RuntimeError(busy_message)
            time.sleep(_LOCK_POLL_SECONDS)
        if not _lock_metadata_is_safe(path, handle):
            raise RuntimeError("parallel test lock changed while acquired")
        yield
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors: list[BaseException] = []
        if locked:
            try:
                _unlock(handle)
            except BaseException as exc:
                cleanup_errors.append(exc)
        try:
            handle.close()
        except BaseException as exc:
            cleanup_errors.append(exc)
        if cleanup_errors:
            if primary_error is not None:
                add_exception_note(
                    primary_error,
                    f"parallel lock cleanup failed ({type(cleanup_errors[0]).__name__})",
                )
            else:
                raise PrivateRuntimeLockCleanupError(
                    "parallel test lock cleanup failed"
                ) from cleanup_errors[0]


def ensure_owned_directory(parent: Path, name: str, receipt_name: str, receipt: bytes) -> Path:
    path = parent / name
    created = False
    try:
        path.mkdir(mode=0o700)
        created = True
    except FileExistsError:
        pass
    identity: PrivateDirectoryIdentity | None = None
    try:
        if created:
            path = ensure_private_directory(path).resolve(strict=True)
            identity = capture_private_directory_identity(path)
            create_exact_private_file(path / receipt_name, receipt)
        else:
            path = validate_private_directory(path).resolve(strict=True)
        if not exact_private_file_is_valid(path / receipt_name, receipt):
            raise RuntimeError("parallel test owned directory receipt is invalid")
        return path
    except BaseException:
        if created and identity is not None:
            with suppress(BaseException):
                remove_private_directory(identity)
        raise


def reset_private_scratch(
    root: Path,
    *,
    child_directories: Iterable[Path],
) -> PrivateDirectoryIdentity:
    try:
        os.lstat(root)
    except FileNotFoundError:
        pass
    else:
        remove_private_directory(capture_private_directory_identity(root))
    try:
        root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RuntimeError("parallel scratch root collided during exclusive execution") from exc
    identity = capture_private_directory_identity(ensure_private_directory(root))
    try:
        for path in child_directories:
            path.mkdir(mode=0o700)
            ensure_private_directory(path)
    except BaseException:
        with suppress(BaseException):
            remove_private_directory(identity)
        raise
    return identity


def bounded_head_tail(payload: bytes, maximum_bytes: int, marker: bytes) -> bytes:
    if len(payload) <= maximum_bytes:
        return payload
    if maximum_bytes <= len(marker):
        return marker[:maximum_bytes]
    retained = maximum_bytes - len(marker)
    head_bytes = retained // 2
    tail_bytes = retained - head_bytes
    return payload[:head_bytes] + marker + payload[-tail_bytes:]


def clear_reserved_latest_logs(
    root: Path,
    *,
    manifest_name: str,
    additional_names: Iterable[str] = (),
) -> None:
    """Remove only fixed Agency-reserved latest outputs from an owned log root."""

    private_root = validate_private_directory(root)
    reserved_names = {manifest_name, *additional_names}
    for candidate in private_root.iterdir():
        if candidate.name not in reserved_names and not _LATEST_LOG_NAME.fullmatch(candidate.name):
            continue
        metadata = os.lstat(candidate)
        if (
            metadata_is_link_or_reparse_point(metadata)
            or not stat.S_ISREG(metadata.st_mode)
            or int(getattr(metadata, "st_nlink", 0) or 0) != 1
            or not _owner_trusted_file(candidate, metadata)
        ):
            raise RuntimeError("parallel latest log path is unsafe")
        candidate.unlink()


def write_atomic_bounded_log(
    path: Path,
    payload: bytes,
    maximum_bytes: int,
    *,
    marker: bytes,
) -> None:
    bounded = bounded_head_tail(payload, maximum_bytes, marker)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    temporary: Path | None = None
    descriptor: int | None = None
    for _attempt in range(_MAX_TEMP_CREATE_ATTEMPTS):
        candidate = path.parent / f".{path.name}.{secrets.token_hex(12)}.tmp"
        try:
            descriptor = os.open(candidate, flags, 0o600)
        except FileExistsError:
            continue
        temporary = candidate
        break
    if descriptor is None or temporary is None:
        raise RuntimeError("could not reserve a private shard log temporary file")
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        _write_all(descriptor, bounded)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        if os.name == "nt" and not restrict_windows_acl(
            temporary, directory=False, is_windows=True
        ):
            raise RuntimeError("parallel shard log ACL could not be restricted")
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            with suppress(FileNotFoundError):
                temporary.unlink()


__all__ = [
    "PrivateRuntimeLockCleanupError",
    "bounded_head_tail",
    "capture_private_directory_identity",
    "clear_reserved_latest_logs",
    "create_exact_private_file",
    "ensure_owned_directory",
    "exact_private_file_is_valid",
    "private_runtime_lock",
    "reset_private_scratch",
    "write_atomic_bounded_log",
]
