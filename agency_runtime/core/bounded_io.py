"""Link-resistant bounded reads for security-sensitive local state."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path


class BoundedFileError(OSError):
    """A security-sensitive local file could not be read safely."""


class FileSizeLimitError(BoundedFileError):
    """A local file exceeds its caller-defined byte limit."""


class UnsafeFileError(BoundedFileError):
    """A local path is linked, special, or changed during open."""


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    # Reconstructed ``os.stat_result`` instances (and some alternative Python
    # runtimes) expose the Windows extension field as ``None`` rather than
    # omitting it. Treat that the same as no file attributes so the stable
    # identity check can reject the changed file.
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    """Return whether two POSIX metadata snapshots name one provable object."""

    left_inode = int(getattr(left, "st_ino", 0) or 0)
    right_inode = int(getattr(right, "st_ino", 0) or 0)
    return bool(
        left_inode
        and right_inode
        and int(left.st_dev) == int(right.st_dev)
        and left_inode == right_inode
    )


def restrict_posix_path_permissions(path: Path, *, directory: bool) -> None:
    """Apply owner-only mode through a verified descriptor, never a path race.

    The initial ``lstat`` classifies the intended object. The descriptor is
    opened without following a final link where the platform supports it, then
    matched to that snapshot before ``fchmod``. A final ``lstat`` also proves
    the pathname still identifies the repaired object before returning.
    """

    before = os.lstat(path)
    expected_kind = stat.S_ISDIR(before.st_mode) if directory else stat.S_ISREG(before.st_mode)
    if _is_link_or_reparse(before) or not expected_kind:
        kind = "directory" if directory else "regular file"
        raise UnsafeFileError(f"permission target must be a real {kind}")

    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    if directory:
        flags |= int(getattr(os, "O_DIRECTORY", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise UnsafeFileError("permission target could not be opened safely") from exc
    try:
        opened = os.fstat(descriptor)
        opened_kind = stat.S_ISDIR(opened.st_mode) if directory else stat.S_ISREG(opened.st_mode)
        if _is_link_or_reparse(opened) or not opened_kind or not _same_identity(before, opened):
            raise UnsafeFileError("permission target changed while it was opened")

        expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
        os.fchmod(descriptor, expected_mode)
        repaired = os.fstat(descriptor)
        if not _same_identity(opened, repaired) or stat.S_IMODE(repaired.st_mode) != expected_mode:
            raise UnsafeFileError("owner-only permissions could not be enforced")
        try:
            current = os.lstat(path)
        except OSError as exc:
            raise UnsafeFileError("permission target changed after repair") from exc
        if (
            _is_link_or_reparse(current)
            or not _same_identity(repaired, current)
            or stat.S_IMODE(current.st_mode) != expected_mode
        ):
            raise UnsafeFileError("permission target changed after repair")
    finally:
        os.close(descriptor)


def read_bounded_regular_file(
    path: Path,
    *,
    limit: int,
    label: str = "file",
) -> bytes:
    """Read a stable regular file without following links or exceeding *limit*."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("file read limit must be a positive integer")

    before = path.lstat()
    if _is_link_or_reparse(before) or not stat.S_ISREG(before.st_mode):
        raise UnsafeFileError(f"{label} must be a regular non-link file")
    if before.st_size > limit:
        raise FileSizeLimitError(f"{label} exceeds the size limit")

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if _is_link_or_reparse(opened) or not stat.S_ISREG(opened.st_mode):
            raise UnsafeFileError(f"{label} changed during open")
        if (
            before.st_ino
            and opened.st_ino
            and (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise UnsafeFileError(f"{label} changed during open")
        if opened.st_size > limit:
            raise FileSizeLimitError(f"{label} exceeds the size limit")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            payload = stream.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(payload) > limit:
        raise FileSizeLimitError(f"{label} exceeds the size limit")
    return payload


def atomic_write_text(path: Path, content: str) -> None:
    """Durably replace a text artifact without exposing a partial final file."""

    target = path.expanduser()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        if os.name != "nt":
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


__all__ = [
    "BoundedFileError",
    "FileSizeLimitError",
    "UnsafeFileError",
    "atomic_write_text",
    "read_bounded_regular_file",
    "restrict_posix_path_permissions",
]
