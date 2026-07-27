"""Canonical path-identity and POSIX namespace trust primitives."""

from __future__ import annotations

import errno
import os
import stat
from collections.abc import Callable, Sequence
from itertools import pairwise
from pathlib import Path

PathMetadata = tuple[Path, os.stat_result]


def absolute_path(path: Path) -> Path:
    """Return one expanded absolute path without resolving links."""

    return Path(os.path.abspath(path.expanduser()))


def directory_chain(path: Path) -> tuple[Path, ...]:
    """Return every lexical directory component from anchor through ``path``."""

    normalized = absolute_path(path)
    anchor = Path(normalized.anchor)
    parts = normalized.parts[1:]
    return (
        anchor,
        *(anchor.joinpath(*parts[:index]) for index in range(1, len(parts) + 1)),
    )


def metadata_is_link_or_reparse_point(metadata: os.stat_result) -> bool:
    """Return whether metadata identifies a POSIX link or Windows reparse point."""

    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse)


def same_file_identity(
    left: os.stat_result,
    right: os.stat_result,
    *,
    require_nonzero_inode: bool = True,
) -> bool:
    """Compare device/inode identity, requiring a stable inode by default."""

    left_inode = int(getattr(left, "st_ino", 0) or 0)
    right_inode = int(getattr(right, "st_ino", 0) or 0)
    return bool(
        (not require_nonzero_inode or (left_inode and right_inode))
        and int(left.st_dev) == int(right.st_dev)
        and left_inode == right_inode
    )


def posix_directory_has_default_acl(path: Path) -> bool:
    """Fail closed when a Linux default ACL could grant descendant access."""

    getxattr = getattr(os, "getxattr", None)
    if not callable(getxattr):
        return False
    try:
        return bool(getxattr(path, "system.posix_acl_default", follow_symlinks=False))
    except OSError as exc:
        return exc.errno not in {
            errno.ENODATA,
            getattr(errno, "ENOATTR", errno.ENODATA),
            errno.ENOTSUP,
            getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
        }


def posix_directory_chain_is_trusted(
    chain: Sequence[PathMetadata],
    *,
    effective_uid: int | None,
    final_path: Path,
    final_owner_must_match: bool,
    forbidden_final_mode: int,
    default_acl_probe: Callable[[Path], bool] | None,
) -> bool:
    """Validate one already-lstat'd POSIX directory chain.

    Root and the effective account may own ancestors. A writable shared
    ancestor is accepted only when sticky-bit ownership protects the next
    component. Callers select whether the final directory must be current-user
    owned, which permission bits are forbidden, and whether its default ACL is
    relevant to their artifact type.
    """

    if effective_uid is None or not chain:
        return False
    uid = int(effective_uid)
    trusted_owners = {0, uid}
    if any(
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
        or int(metadata.st_uid) not in trusted_owners
        for _path, metadata in chain
    ):
        return False

    final = chain[-1][1]
    if final_owner_must_match and int(final.st_uid) != uid:
        return False
    if stat.S_IMODE(final.st_mode) & forbidden_final_mode:
        return False
    if default_acl_probe is not None:
        try:
            if default_acl_probe(final_path):
                return False
        except Exception:
            return False

    for (_ancestor_path, ancestor), (_child_path, child) in pairwise(chain):
        writable = stat.S_IMODE(ancestor.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
        if writable and not (
            ancestor.st_mode & stat.S_ISVTX and int(child.st_uid) in trusted_owners
        ):
            return False
    return True


__all__ = [
    "absolute_path",
    "directory_chain",
    "metadata_is_link_or_reparse_point",
    "posix_directory_chain_is_trusted",
    "posix_directory_has_default_acl",
    "same_file_identity",
]
