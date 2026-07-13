"""Link-resistant bounded reads for security-sensitive local state."""

from __future__ import annotations

import os
import stat
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


__all__ = [
    "BoundedFileError",
    "FileSizeLimitError",
    "UnsafeFileError",
    "read_bounded_regular_file",
]
