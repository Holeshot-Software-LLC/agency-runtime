"""Filesystem security primitives for the SQLite canonical store."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agency_runtime.core.bounded_io import (
    UnsafeFileError,
    restrict_posix_path_permissions,
)
from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.filesystem_trust import (
    absolute_path as _absolute_path,
)
from agency_runtime.core.filesystem_trust import (
    directory_chain as _directory_chain,
)
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point,
    posix_directory_chain_is_trusted,
    posix_directory_has_default_acl,
)
from agency_runtime.core.path_authority import private_path_authority_covers
from agency_runtime.core.windows_acl import (
    restrict_windows_acl as _restrict_windows_acl,
)
from agency_runtime.core.windows_acl import (
    windows_directory_prevents_untrusted_writes,
)


@dataclass(frozen=True, slots=True)
class CreatedStoragePath:
    """Identity receipt for one product-created file or directory."""

    path: Path
    device: int
    inode: int
    directory: bool


def capture_created_storage_path(path: Path, *, directory: bool) -> CreatedStoragePath:
    """Capture a newly created real path before any later operation can fail."""

    metadata = os.lstat(path)
    inode = int(getattr(metadata, "st_ino", 0) or 0)
    expected_kind = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if metadata_is_link_or_reparse_point(metadata) or not expected_kind or inode <= 0:
        raise PermissionError("Agency Runtime could not capture a created storage identity")
    if not directory and int(getattr(metadata, "st_nlink", 0) or 0) != 1:
        raise PermissionError("Agency Runtime created storage file is not single-link")
    return CreatedStoragePath(
        path=_absolute_path(path),
        device=int(metadata.st_dev),
        inode=inode,
        directory=directory,
    )


def _created_storage_path_is_current(identity: CreatedStoragePath) -> bool:
    try:
        metadata = os.lstat(identity.path)
    except FileNotFoundError:
        return False
    expected_kind = (
        stat.S_ISDIR(metadata.st_mode) if identity.directory else stat.S_ISREG(metadata.st_mode)
    )
    return bool(
        not metadata_is_link_or_reparse_point(metadata)
        and expected_kind
        and int(metadata.st_dev) == identity.device
        and int(getattr(metadata, "st_ino", 0) or 0) == identity.inode
        and (identity.directory or int(getattr(metadata, "st_nlink", 0) or 0) == 1)
    )


def cleanup_created_storage_paths(
    identities: list[CreatedStoragePath] | tuple[CreatedStoragePath, ...],
    *,
    is_windows: bool,
) -> None:
    """Remove unchanged product-created paths in reverse creation order."""

    for identity in reversed(identities):
        try:
            os.lstat(identity.path)
        except FileNotFoundError:
            continue
        if not storage_creation_boundary_is_trusted(
            identity.path.parent,
            identity.path.parent,
            is_windows=is_windows,
        ):
            raise PermissionError("refusing storage rollback through an untrusted parent")
        if not _created_storage_path_is_current(identity):
            raise PermissionError("refusing storage rollback after identity replacement")
        if identity.directory:
            os.rmdir(identity.path)
        else:
            os.unlink(identity.path)


def assert_storage_parent_chain(path: Path, *, allow_missing: bool) -> None:
    """Reject links and special files in an explicit database parent chain."""

    for candidate in _directory_chain(path):
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            if allow_missing:
                return
            raise PermissionError("Agency Runtime storage parent does not exist") from None
        if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise PermissionError(
                "Agency Runtime storage parent must contain only real directories"
            )


def nearest_existing_storage_parent(path: Path) -> Path:
    """Return the nearest real existing ancestor without following a link."""

    candidate = _absolute_path(path)
    while True:
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            parent = candidate.parent
            if parent == candidate:
                raise PermissionError("Agency Runtime storage has no existing parent") from None
            candidate = parent
            continue
        if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise PermissionError(
                "Agency Runtime storage parent must contain only real directories"
            )
        return candidate


def storage_parent_is_trusted(
    path: Path,
    *,
    is_windows: bool,
    windows_acl_probe: Callable[[Path, bool, bool], bool] | None = None,
    effective_uid: int | None = None,
    final_parent: bool = True,
    prospective_child: bool = False,
) -> bool:
    """Return whether another OS account cannot substitute storage paths."""

    if final_parent and prospective_child:
        return False
    normalized = _absolute_path(path)
    if is_windows and windows_acl_probe is None and private_path_authority_covers(normalized):
        return not (final_parent and prospective_child)
    try:
        chain = tuple(
            (candidate, os.lstat(candidate)) for candidate in _directory_chain(normalized)
        )
    except OSError:
        return False
    if any(
        metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _candidate, metadata in chain
    ):
        return False
    if is_windows:
        probe = windows_acl_probe or (
            lambda candidate, final_parent, prospective_child: (
                windows_directory_prevents_untrusted_writes(
                    candidate,
                    is_windows=True,
                    final_parent=final_parent,
                    prospective_child=prospective_child,
                    private_access=final_parent,
                )
            )
        )
        try:
            return all(
                probe(
                    candidate,
                    final_parent and candidate == normalized,
                    prospective_child and candidate == normalized,
                )
                for candidate, _metadata in chain
            )
        except Exception:
            return False

    uid_getter = getattr(os, "geteuid", None)
    uid = int(uid_getter()) if effective_uid is None and callable(uid_getter) else effective_uid
    if uid is None:
        return False
    return posix_directory_chain_is_trusted(
        chain,
        effective_uid=uid,
        final_path=normalized,
        final_owner_must_match=final_parent,
        forbidden_final_mode=(stat.S_IRWXG | stat.S_IRWXO) if final_parent else 0,
        default_acl_probe=posix_directory_has_default_acl if final_parent else None,
    )


def storage_creation_boundary_is_trusted(
    boundary: Path,
    intended_parent: Path,
    *,
    is_windows: bool,
) -> bool:
    """Validate an existing boundary before creating any missing descendants."""

    boundary_is_intended_parent = _absolute_path(boundary) == _absolute_path(intended_parent)
    if not storage_parent_is_trusted(
        boundary,
        is_windows=is_windows,
        final_parent=False,
        prospective_child=is_windows and not boundary_is_intended_parent,
    ):
        return False
    if boundary_is_intended_parent or is_windows:
        return True
    try:
        metadata = os.lstat(boundary)
    except OSError:
        return False
    writable_by_others = stat.S_IMODE(metadata.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
    return not writable_by_others or bool(metadata.st_mode & stat.S_ISVTX)


def storage_artifact_parent_is_trusted(
    path: Path,
    *,
    is_windows: bool,
    windows_acl_probe: Callable[[Path, bool], bool] | None = None,
    effective_uid: int | None = None,
    default_acl_probe: Callable[[Path], bool] | None = None,
    owner_private_group_probe: Callable[[Path, os.stat_result], bool] | None = None,
) -> bool:
    """Require integrity, not confidentiality, for a foreign artifact parent.

    Host tools choose their own umask. Codex, for example, writes rollout date
    directories at 0755 and the rollout itself at 0644. Read and traversal
    grants do not let another account replace that artifact; mutation grants
    do. Every component is therefore link-free and substitution-resistant,
    while the final directory must be current-user owned and non-writable by
    group or other.
    """

    normalized = _absolute_path(path)
    if is_windows and windows_acl_probe is None and private_path_authority_covers(normalized):
        return True
    try:
        chain = tuple(
            (candidate, os.lstat(candidate)) for candidate in _directory_chain(normalized)
        )
    except (OSError, ValueError):
        return False
    if not chain or any(
        metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _candidate, metadata in chain
    ):
        return False
    if is_windows:
        probe = windows_acl_probe or (
            lambda candidate, final_parent: windows_directory_prevents_untrusted_writes(
                candidate,
                is_windows=True,
                final_parent=final_parent,
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
    private_group_probe = owner_private_group_probe or _posix_owner_private_group_is_exclusive
    return posix_directory_chain_is_trusted(
        chain,
        effective_uid=uid,
        final_path=normalized,
        final_owner_must_match=True,
        forbidden_final_mode=stat.S_IWOTH,
        default_acl_probe=acl_probe,
        owner_private_group_probe=private_group_probe,
    )


def _posix_owner_private_group_is_exclusive(
    _path: Path,
    metadata: os.stat_result,
) -> bool:
    """Prove a POSIX user-private group has no second account member."""

    try:
        import grp
        import pwd

        effective_uid = int(os.geteuid())
        owner = pwd.getpwuid(effective_uid)
        group = grp.getgrgid(int(metadata.st_gid))
        primary_members = {
            int(account.pw_uid)
            for account in pwd.getpwall()
            if int(account.pw_gid) == int(metadata.st_gid)
        }
    except (AttributeError, ImportError, KeyError, OSError, TypeError, ValueError):
        return False
    return bool(
        int(metadata.st_uid) == effective_uid
        and int(owner.pw_gid) == int(metadata.st_gid)
        and group.gr_name == owner.pw_name
        and set(group.gr_mem).issubset({owner.pw_name})
        and primary_members == {effective_uid}
    )


def storage_artifact_file_is_trusted(
    path: Path,
    *,
    is_windows: bool,
    owner_private_group_probe: Callable[[Path, os.stat_result], bool] | None = None,
) -> bool:
    """Require foreign host-file integrity, including an exclusive user group."""

    if is_windows:
        return storage_file_is_trusted(path, is_windows=True)
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISREG(metadata.st_mode)
        or int(getattr(metadata, "st_nlink", 0) or 0) != 1
        or int(getattr(metadata, "st_ino", 0) or 0) <= 0
    ):
        return False
    uid_getter = getattr(os, "geteuid", None)
    if not callable(uid_getter) or int(metadata.st_uid) != int(uid_getter()):
        return False
    mode = stat.S_IMODE(metadata.st_mode)
    if mode & stat.S_IWOTH:
        return False
    private_group_probe = owner_private_group_probe or _posix_owner_private_group_is_exclusive
    return not mode & stat.S_IWGRP or private_group_probe(path, metadata)


def storage_file_is_trusted(path: Path, *, is_windows: bool) -> bool:
    """Require one current-user-owned, non-writable storage file identity.

    Every caller reads a file some *other* program wrote: a Claude sub-agent
    transcript, a Codex rollout, a host wiring file. Agency does not own those
    writers and cannot choose their umask, so the property that can be required
    is integrity -- nobody but the owner could have substituted the bytes --
    and not confidentiality of the host's own transcript.

    Requiring the group and other *read* bits to be clear as well demanded mode
    0600 from files hosts write at 0644. On Windows a different branch accepted
    the same artifact, so one host artifact was trusted there and refused on
    Linux, and the Rule 4 host-artifact proof was unobtainable on Linux for any
    host with a normal umask.
    """

    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
        return False
    if int(getattr(metadata, "st_nlink", 0) or 0) != 1:
        return False
    if int(getattr(metadata, "st_ino", 0) or 0) <= 0:
        return False
    if is_windows:
        return windows_directory_prevents_untrusted_writes(
            path,
            is_windows=True,
            final_parent=True,
            private_access=True,
        )
    uid_getter = getattr(os, "geteuid", None)
    # Writability is the integrity boundary. The parent chain is already proven
    # private, so an owner-only-writable regular file with one link cannot have
    # been substituted by another account.
    return bool(
        callable(uid_getter)
        and int(metadata.st_uid) == int(uid_getter())
        and not stat.S_IMODE(metadata.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
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
    try:
        restrict_posix_path_permissions(path, directory=directory)
    except UnsafeFileError as exc:
        raise PermissionError(str(exc)) from exc
    except OSError as exc:
        raise PermissionError(
            f"could not enforce private permissions on Agency Runtime storage: {path}"
        ) from exc


def _secure_storage_parent_component(candidate: Path, *, is_windows: bool) -> None:
    """Validate and harden one just-created or pre-existing parent component."""

    assert_storage_parent_chain(candidate, allow_missing=False)
    if not storage_parent_is_trusted(
        candidate,
        is_windows=is_windows,
        final_parent=True,
    ):
        raise PermissionError("Agency Runtime storage parent is unsafe before permission repair")
    restrict_path_permissions(
        candidate,
        directory=True,
        is_windows=is_windows,
        link_checker=is_link_or_reparse_point,
        windows_acl=lambda path, *, directory: restrict_windows_acl(
            path,
            directory=directory,
            is_windows=is_windows,
        ),
    )
    if not storage_parent_is_trusted(
        candidate,
        is_windows=is_windows,
        final_parent=True,
    ):
        raise PermissionError("Agency Runtime storage parent is unsafe after permission repair")


def _discard_created_receipts(
    created_paths: list[CreatedStoragePath] | None,
    local_created: list[CreatedStoragePath],
) -> None:
    if created_paths is None:
        return
    for identity in local_created:
        if identity in created_paths:
            created_paths.remove(identity)


def create_private_storage_parent(
    boundary: Path,
    intended_parent: Path,
    *,
    is_windows: bool,
    created_paths: list[CreatedStoragePath] | None = None,
) -> bool:
    """Create missing parent components privately from one validated boundary.

    Path.mkdir(parents=True) applies the requested mode only to the final
    component. Creating and hardening each component before descending keeps a
    permissive umask, POSIX default ACL, or Windows inherited ACL from exposing
    the next pathname operation to another account.
    """

    normalized_boundary = _absolute_path(boundary)
    normalized_parent = _absolute_path(intended_parent)
    try:
        relative = normalized_parent.relative_to(normalized_boundary)
    except ValueError as exc:
        raise PermissionError(
            "Agency Runtime storage parent is outside its validated boundary"
        ) from exc
    if not relative.parts:
        return False

    current = normalized_boundary
    created_any = False
    local_created: list[CreatedStoragePath] = []
    try:
        for component in relative.parts:
            if not storage_creation_boundary_is_trusted(
                current,
                normalized_parent,
                is_windows=is_windows,
            ):
                raise PermissionError(
                    "Agency Runtime storage ancestor permits cross-account path substitution"
                )
            candidate = current / component
            try:
                os.mkdir(candidate, 0o777 if is_windows else stat.S_IRWXU)
            except FileExistsError:
                pass
            except OSError as exc:
                raise PermissionError(
                    "Agency Runtime could not create its private storage parent"
                ) from exc
            else:
                created_any = True
                identity = capture_created_storage_path(candidate, directory=True)
                local_created.append(identity)
                if created_paths is not None:
                    created_paths.append(identity)

            _secure_storage_parent_component(candidate, is_windows=is_windows)
            current = candidate
        return created_any
    except BaseException as error:
        try:
            cleanup_created_storage_paths(local_created, is_windows=is_windows)
        except Exception as cleanup_error:
            add_exception_note(
                error,
                f"Agency Runtime storage parent rollback failed: {cleanup_error}",
            )
        _discard_created_receipts(created_paths, local_created)
        raise


def default_db_path(config_path: str | Path | None = None) -> Path:
    """Resolve the DB owned by one config identity, propagating invalid config."""

    from agency_runtime.core.config import load_config

    cfg = load_config(config_path) if config_path is not None else load_config()
    return cfg.store.resolved_path()


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


def sqlite_storage_paths(db_path: Path) -> tuple[Path, ...]:
    """Return every deterministic file SQLite may open beside one database."""

    return (
        db_path,
        Path(f"{db_path}-journal"),
        Path(f"{db_path}-wal"),
        Path(f"{db_path}-shm"),
    )
