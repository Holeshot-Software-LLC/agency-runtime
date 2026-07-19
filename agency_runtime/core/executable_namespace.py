"""Cross-account namespace trust checks for executable artifacts."""

from __future__ import annotations

import errno
import os
import stat
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path

from agency_runtime.core.path_authority import private_path_authority_covers
from agency_runtime.core.windows_acl import windows_directory_prevents_untrusted_writes

WindowsNamespaceProbe = Callable[[Path, bool], bool]
DefaultACLProbe = Callable[[Path], bool]


def _absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _directory_chain(path: Path) -> tuple[Path, ...]:
    normalized = _absolute_path(path)
    anchor = Path(normalized.anchor)
    parts = normalized.parts[1:]
    return (
        anchor,
        *(anchor.joinpath(*parts[:index]) for index in range(1, len(parts) + 1)),
    )


def _metadata_is_link_or_reparse_point(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse)


def posix_directory_has_default_acl(path: Path) -> bool:
    """Fail closed when a default ACL could grant executable-parent writes."""

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


def executable_namespace_is_trusted(
    executable_parent: Path,
    *,
    is_windows: bool,
    windows_acl_probe: WindowsNamespaceProbe | None = None,
    effective_uid: int | None = None,
    default_acl_probe: DefaultACLProbe | None = None,
) -> bool:
    """Return whether another OS account cannot replace an executable artifact.

    Every existing component is inspected without following links. POSIX permits
    root- and current-user-owned system paths, including a sticky shared ancestor
    such as ``/tmp``, but the executable's immediate parent must itself be
    non-writable by group/other and have no default ACL. Windows applies the
    repository's DACL classifier to every component and treats the final parent
    as a prospective-child boundary so OS-owned installation directories remain
    valid while untrusted effective or inheritable mutation grants do not.
    """

    normalized = _absolute_path(executable_parent)
    if is_windows and windows_acl_probe is None and private_path_authority_covers(normalized):
        return True
    try:
        chain = tuple(
            (candidate, os.lstat(candidate)) for candidate in _directory_chain(normalized)
        )
    except (OSError, ValueError):
        return False
    if not chain or any(
        _metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _candidate, metadata in chain
    ):
        return False

    if is_windows:
        probe = windows_acl_probe or (
            lambda candidate, final_parent: windows_directory_prevents_untrusted_writes(
                candidate,
                is_windows=True,
                final_parent=False,
                prospective_child=final_parent,
                allow_inheritable_read=final_parent,
            )
        )
        try:
            return all(probe(candidate, candidate == normalized) for candidate, _metadata in chain)
        except Exception:
            return False

    uid_getter = getattr(os, "geteuid", None)
    uid = int(uid_getter()) if effective_uid is None and callable(uid_getter) else effective_uid
    if uid is None:
        return False
    trusted_owners = {0, int(uid)}
    if any(int(metadata.st_uid) not in trusted_owners for _candidate, metadata in chain):
        return False

    final = chain[-1][1]
    if stat.S_IMODE(final.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    acl_probe = default_acl_probe or posix_directory_has_default_acl
    try:
        if acl_probe(normalized):
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


def assert_executable_namespace(
    executable_path: str | Path,
    *,
    is_windows: bool,
) -> None:
    """Raise before launch when an artifact's parent namespace is replaceable."""

    path = Path(executable_path)
    if not executable_namespace_is_trusted(path.parent, is_windows=is_windows):
        raise PermissionError(
            f"executable parent namespace permits cross-account substitution: {path}"
        )


__all__ = [
    "assert_executable_namespace",
    "executable_namespace_is_trusted",
    "posix_directory_has_default_acl",
]
