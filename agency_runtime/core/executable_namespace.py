"""Cross-account namespace trust checks for executable artifacts."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path

from agency_runtime.core.filesystem_trust import (
    absolute_path as _absolute_path,
)
from agency_runtime.core.filesystem_trust import (
    directory_chain as _directory_chain,
)
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _metadata_is_link_or_reparse_point,
)
from agency_runtime.core.filesystem_trust import (
    posix_directory_chain_is_trusted,
    posix_directory_has_default_acl,
)
from agency_runtime.core.path_authority import private_path_authority_covers
from agency_runtime.core.windows_acl import windows_directory_prevents_untrusted_writes

WindowsNamespaceProbe = Callable[[Path, bool], bool]
DefaultACLProbe = Callable[[Path], bool]


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
    acl_probe = default_acl_probe or posix_directory_has_default_acl
    return posix_directory_chain_is_trusted(
        chain,
        effective_uid=uid,
        final_path=normalized,
        final_owner_must_match=False,
        forbidden_final_mode=stat.S_IWGRP | stat.S_IWOTH,
        default_acl_probe=acl_probe,
    )


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
