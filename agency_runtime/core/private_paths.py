"""Private per-user runtime directories for ephemeral and retained state."""

from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import stat
import tempfile
import threading
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import cast

from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.path_authority import (
    discard_private_path_authority,
    register_private_path_authority,
)
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    create_private_storage_parent,
    is_link_or_reparse_point,
    metadata_is_link_or_reparse_point,
    nearest_existing_storage_parent,
    restrict_path_permissions,
    restrict_windows_acl,
    storage_creation_boundary_is_trusted,
    storage_parent_is_trusted,
)
from agency_runtime.core.windows_acl import (
    current_process_restricted_sids,
    current_process_user_sid,
    windows_directory_prevents_untrusted_writes,
    windows_restricted_host_boundary_is_trusted,
)
from agency_runtime.core.windows_private_directory import (
    WindowsDirectoryGuard,
    create_or_validate_windows_owner_private_directory,
    create_windows_logon_private_directory,
    open_windows_directory_guard,
    prepare_windows_logon_private_directory_cleanup,
)

_IS_WINDOWS = os.name == "nt"
_RUNTIME_ROOT_NAME = ".agency-runtime"
_SAFE_COMPONENT_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)
_HOST_AUTHORITIES: dict[Path, PrivateDirectoryIdentity] = {}
_HOST_AUTHORITIES_LOCK = threading.RLock()


@dataclass(frozen=True, slots=True)
class PrivateDirectoryIdentity:
    """Stable identity captured for one private directory cleanup boundary."""

    path: Path
    device: int
    inode: int
    guard: WindowsDirectoryGuard | None = None
    parent_guard: WindowsDirectoryGuard | None = None


class PrivateDirectoryCleanupError(RuntimeError):
    """Raised when an Agency-owned private directory cannot be removed safely."""


def _register_host_authority(identity: PrivateDirectoryIdentity) -> None:
    with _HOST_AUTHORITIES_LOCK:
        _HOST_AUTHORITIES[_absolute(identity.path)] = identity
    register_private_path_authority(
        identity.path,
        lambda target: bool(
            _identity_is_current(identity)
            and _host_descendant_namespace_is_private(target, identity)
        ),
    )


def _discard_host_authority(identity: PrivateDirectoryIdentity) -> None:
    discard_private_path_authority(identity.path)
    with _HOST_AUTHORITIES_LOCK:
        if _HOST_AUTHORITIES.get(_absolute(identity.path)) is identity:
            _HOST_AUTHORITIES.pop(_absolute(identity.path), None)


def _host_authority_for(path: Path) -> PrivateDirectoryIdentity | None:
    target = _absolute(path)
    with _HOST_AUTHORITIES_LOCK:
        candidates = tuple(_HOST_AUTHORITIES.values())
    for identity in candidates:
        try:
            target.relative_to(_absolute(identity.path))
        except ValueError:
            continue
        if _identity_is_current(identity):
            return identity
        _discard_host_authority(identity)
    return None


def _host_descendant_is_private(path: Path, authority: PrivateDirectoryIdentity) -> bool:
    target = _absolute(path)
    root = _absolute(authority.path)
    try:
        relative = target.relative_to(root)
    except ValueError:
        return False
    current = root
    for component in relative.parts:
        current /= component
        try:
            metadata = os.lstat(current)
        except OSError:
            return False
        if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
            return False
        if not windows_directory_prevents_untrusted_writes(
            current,
            is_windows=True,
            final_parent=True,
            private_access=True,
        ):
            return False
    return True


def _host_descendant_namespace_is_private(
    path: Path,
    authority: PrivateDirectoryIdentity,
) -> bool:
    """Validate existing components while allowing a missing prospective suffix."""

    target = _absolute(path)
    root = _absolute(authority.path)
    try:
        relative = target.relative_to(root)
    except ValueError:
        return False
    current = root
    for component in relative.parts:
        current /= component
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
            return False
        if not windows_directory_prevents_untrusted_writes(
            current,
            is_windows=True,
            final_parent=True,
            private_access=True,
        ):
            return False
    return True


def _ensure_host_private_descendant(
    target: Path,
    authority: PrivateDirectoryIdentity,
    *,
    product_owned: bool,
) -> Path:
    root = _absolute(authority.path)
    relative = _absolute(target).relative_to(root)
    current = root
    for component in relative.parts:
        if not _identity_is_current(authority) or not _host_descendant_is_private(
            current,
            authority,
        ):
            raise PermissionError("Codex private scratch ancestor changed")
        candidate = current / component
        with suppress(FileExistsError):
            os.mkdir(candidate, 0o777)
        if product_owned:
            _restrict_private_directory(candidate)
        if not _host_descendant_is_private(candidate, authority):
            raise PermissionError("Codex private scratch descendant is not private")
        current = candidate
    return _absolute(target)


def _codex_thread_id(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, ValueError) as exc:
        raise PermissionError("Codex scratch identity is unavailable") from exc
    canonical = str(parsed)
    if value != canonical:
        raise PermissionError("Codex scratch identity is not canonical")
    return canonical


def _pin_codex_host_private_parent(
    candidate: Path,
    visualizations: Path,
) -> WindowsDirectoryGuard | None:
    candidate = _absolute(candidate)
    try:
        relative = candidate.relative_to(visualizations)
        if len(relative.parts) != 4:
            return None
        uuid.UUID(relative.name)
        validate_private_directory(candidate.parent)
        metadata = os.lstat(candidate)
    except (OSError, PermissionError, ValueError):
        return None
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
        or int(getattr(metadata, "st_ino", 0) or 0) <= 0
        or not windows_restricted_host_boundary_is_trusted(candidate)
    ):
        return None
    guard = open_windows_directory_guard(candidate, is_windows=True)
    if guard is not None and guard.is_current():
        return guard
    if guard is not None:
        guard.close()
    return None


def _close_directory_guards(guards: list[WindowsDirectoryGuard]) -> None:
    for guard in guards:
        guard.close()


def _unique_codex_host_private_parent(visualizations: Path) -> WindowsDirectoryGuard:
    eligible: list[WindowsDirectoryGuard] = []
    for index, candidate in enumerate(visualizations.glob("*/*/*/*")):
        if index >= 4096:
            _close_directory_guards(eligible)
            raise PermissionError("Codex host scratch search exceeded its bound")
        guard = _pin_codex_host_private_parent(candidate, visualizations)
        if guard is not None:
            eligible.append(guard)
    if len(eligible) == 1:
        return eligible[0]
    _close_directory_guards(eligible)
    raise PermissionError("Codex host scratch capability is unavailable or ambiguous")


def _codex_host_private_parent(
    *,
    home_dir: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> WindowsDirectoryGuard:
    """Resolve the one host-attested Codex task root without recursive scanning."""

    if not _IS_WINDOWS:
        raise PermissionError("Codex host scratch is available only on Windows")
    source = os.environ if environment is None else environment
    if source.get("CODEX_SHELL", "").strip() != "1":
        raise PermissionError("Codex host scratch was not attested by the host")
    thread_id = _codex_thread_id(source.get("CODEX_THREAD_ID", "").strip())
    home = _absolute(Path.home() if home_dir is None else home_dir)
    visualizations = home / ".codex" / "visualizations"

    exact = list(islice(visualizations.glob(f"*/*/*/{thread_id}"), 2))
    if len(exact) > 1:
        raise PermissionError("Codex host scratch exact identity is ambiguous")
    if exact:
        guard = _pin_codex_host_private_parent(exact[0], visualizations)
        if guard is None:
            raise PermissionError("Codex host scratch exact boundary is not trusted")
        return guard

    # Nested Codex agents inherit the root task's OS capability but may receive
    # a child correlation ID with no leaf of its own. Search only the bounded,
    # fixed-depth, owner-private namespace and accept exactly one leaf whose
    # sole extra ACL principal is a current restricting SID.
    return _unique_codex_host_private_parent(visualizations)


def _codex_host_allocation_name_matches(name: str, thread_id: str) -> bool:
    """Bind one host-private allocation name to the inherited Codex turn."""

    expected = f".a-{uuid.UUID(thread_id).hex}-"
    if not name.startswith(expected):
        return False
    prefix, separator, token = name[len(expected) :].rpartition("-")
    return bool(
        separator
        and 1 <= len(prefix) <= 8
        and all(character in _SAFE_COMPONENT_CHARS for character in prefix)
        and len(token) == 24
        and token == token.lower()
        and all(character in "0123456789abcdef" for character in token)
    )


def _codex_reattest_parent(
    target: Path,
    *,
    home_dir: Path | None,
    environment: Mapping[str, str] | None,
) -> tuple[str, WindowsDirectoryGuard] | None:
    """Pin the fixed-depth host task root that lexically contains ``target``."""

    home = _absolute(Path.home() if home_dir is None else home_dir)
    visualizations = home / ".codex" / "visualizations"
    try:
        visualization_relative = target.relative_to(visualizations)
    except ValueError:
        return None
    if len(visualization_relative.parts) < 5:
        return None
    source = os.environ if environment is None else environment
    if source.get("CODEX_SHELL", "").strip() != "1":
        return None
    try:
        thread_id = _codex_thread_id(source.get("CODEX_THREAD_ID", "").strip())
    except PermissionError:
        return None

    parent = visualizations.joinpath(*visualization_relative.parts[:4])
    try:
        parent_guard = _pin_codex_host_private_parent(parent, visualizations)
    except (OSError, PermissionError, RuntimeError, ValueError):
        return None
    if parent_guard is None:
        return None
    return thread_id, parent_guard


def _capture_codex_reattested_identity(
    target: Path,
    *,
    thread_id: str,
    parent_guard: WindowsDirectoryGuard,
) -> PrivateDirectoryIdentity | None:
    """Open and validate the direct thread-bound allocation containing a path."""

    root_guard: WindowsDirectoryGuard | None = None
    identity: PrivateDirectoryIdentity | None = None
    try:
        try:
            relative = target.relative_to(_absolute(parent_guard.path))
        except ValueError:
            return None
        if not relative.parts:
            return None
        root_name = relative.parts[0]
        if not _codex_host_allocation_name_matches(root_name, thread_id):
            return None
        root = _absolute(parent_guard.path / root_name)
        metadata = os.lstat(root)
        inode = int(getattr(metadata, "st_ino", 0) or 0)
        if (
            metadata_is_link_or_reparse_point(metadata)
            or not stat.S_ISDIR(metadata.st_mode)
            or inode <= 0
            or not windows_directory_prevents_untrusted_writes(
                root,
                is_windows=True,
                final_parent=True,
                private_access=True,
            )
        ):
            return None
        root_guard = open_windows_directory_guard(root, is_windows=True)
        if root_guard is None or not root_guard.is_current():
            return None
        identity = PrivateDirectoryIdentity(
            path=root,
            device=int(metadata.st_dev),
            inode=inode,
            guard=root_guard,
            parent_guard=parent_guard,
        )
        if not _identity_is_current(identity) or not _host_descendant_namespace_is_private(
            target,
            identity,
        ):
            identity = None
        return identity
    except (OSError, PermissionError, RuntimeError, ValueError):
        return None
    finally:
        if identity is None and root_guard is not None:
            root_guard.close()


def _close_reattested_identity(identity: PrivateDirectoryIdentity) -> None:
    """Close both guards on an identity created by the re-attestation path."""

    cast(WindowsDirectoryGuard, identity.guard).close()
    cast(WindowsDirectoryGuard, identity.parent_guard).close()


def _install_codex_reattested_identity(
    target: Path,
    identity: PrivateDirectoryIdentity,
) -> bool:
    """Atomically reuse, replace, or install one independently pinned receipt."""

    root = _absolute(identity.path)
    with _HOST_AUTHORITIES_LOCK:
        existing = _HOST_AUTHORITIES.get(root)
        if existing is not None and _identity_is_current(existing):
            valid = _host_descendant_namespace_is_private(target, existing)
            _close_reattested_identity(identity)
            return valid
        if existing is not None:
            _discard_host_authority(existing)
            if existing.guard is not None:
                existing.guard.close()
            if existing.parent_guard is not None:
                existing.parent_guard.close()
        _register_host_authority(identity)
    valid = bool(
        _identity_is_current(identity) and _host_descendant_namespace_is_private(target, identity)
    )
    if not valid:
        _discard_host_authority(identity)
        _close_reattested_identity(identity)
    return valid


def reattest_codex_host_private_path(
    path: Path,
    *,
    home_dir: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Re-establish child-process authority for one exact Codex scratch root.

    Process-local authority callbacks cannot survive ``exec``.  A child may
    therefore reopen the host-attested task root and the direct random scratch
    allocation that contains ``path``.  The allocation name must be bound to
    the inherited canonical Codex thread ID, both directories remain pinned by
    native handles, and every existing descendant must retain its private DACL.
    No path supplied through an Agency environment variable is trusted merely
    because it was inherited.
    """

    if not _IS_WINDOWS:
        return False
    target = _absolute(path)
    current = _host_authority_for(target)
    if current is not None:
        return _host_descendant_namespace_is_private(target, current)
    resolved = _codex_reattest_parent(
        target,
        home_dir=home_dir,
        environment=environment,
    )
    if resolved is None:
        return False
    thread_id, parent_guard = resolved
    identity = _capture_codex_reattested_identity(
        target,
        thread_id=thread_id,
        parent_guard=parent_guard,
    )
    if identity is None:
        parent_guard.close()
        return False
    return _install_codex_reattested_identity(target, identity)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def _validate_component(value: str, *, label: str) -> str:
    component = str(value or "").strip()
    if (
        not component
        or component in {".", ".."}
        or len(component) > 80
        or any(character not in _SAFE_COMPONENT_CHARS for character in component)
    ):
        raise ValueError(f"{label} must be one safe filesystem component")
    return component


def _restrict_private_directory(path: Path) -> None:
    restrict_path_permissions(
        path,
        directory=True,
        is_windows=_IS_WINDOWS,
        link_checker=is_link_or_reparse_point,
        windows_acl=lambda candidate, *, directory: restrict_windows_acl(
            candidate,
            directory=directory,
            is_windows=_IS_WINDOWS,
        ),
    )


def _install_windows_bootstrap_authority(
    identity: PrivateDirectoryIdentity,
) -> PrivateDirectoryIdentity:
    """Install one guarded root without leaking a concurrent duplicate guard."""

    guard = identity.guard
    if guard is None:
        raise PermissionError("Agency Runtime protected Windows root guard is unavailable")
    root = _absolute(identity.path)
    with _HOST_AUTHORITIES_LOCK:
        existing = _HOST_AUTHORITIES.get(root)
        if existing is not None and existing.guard is not None and _identity_is_current(existing):
            guard.close()
            return existing
        if existing is not None:
            _close_identity_guards(existing)
        _register_host_authority(identity)
    return identity


def bootstrap_private_directory(path: Path) -> Path:
    """Create one private root beneath an existing real Windows parent.

    The ordinary storage path remains preferred. Windows may fall back to an
    atomic protected-DACL creation only for this exact root; its permissive
    ancestors are never treated as trusted. A native handle/file-ID receipt
    then provides process-local authority for validated descendants.
    """

    target = _absolute(path)
    try:
        return ensure_private_directory(target)
    except PermissionError:
        if not _IS_WINDOWS:
            raise

    # The exception is deliberately narrow: all ancestors must already exist
    # as real directories. Only the final root can be created atomically below
    # an otherwise untrusted namespace.
    assert_storage_parent_chain(target, allow_missing=True)
    assert_storage_parent_chain(target.parent, allow_missing=False)
    parent = target.parent
    if not storage_parent_is_trusted(
        parent,
        is_windows=True,
        final_parent=False,
    ):
        raise PermissionError("Agency Runtime protected Windows root parent is not trusted")
    parent_guard = open_windows_directory_guard(parent, is_windows=True)
    if parent_guard is None:
        raise PermissionError("Agency Runtime protected Windows root parent changed")
    try:
        if not parent_guard.is_current() or not storage_parent_is_trusted(
            parent,
            is_windows=True,
            final_parent=False,
        ):
            raise PermissionError("Agency Runtime protected Windows root parent changed")
        guard = create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent_guard,
            is_windows=True,
        )
        if not parent_guard.is_current() or not storage_parent_is_trusted(
            parent,
            is_windows=True,
            final_parent=False,
        ):
            guard.close()
            raise PermissionError("Agency Runtime protected Windows root parent changed")
    finally:
        parent_guard.close()
    identity = PrivateDirectoryIdentity(
        target,
        guard.device,
        guard.inode,
        guard=guard,
    )
    if not _identity_is_current(identity):
        guard.close()
        raise PermissionError("Agency Runtime protected Windows root changed")
    installed = _install_windows_bootstrap_authority(identity)
    if not _identity_is_current(installed):
        _close_identity_guards(installed)
        raise PermissionError("Agency Runtime protected Windows root changed")
    return target


def ensure_private_directory(path: Path, *, product_owned: bool = True) -> Path:
    """Create or validate one current-user directory without shared-temp trust."""

    target = _absolute(path)
    assert_storage_parent_chain(target, allow_missing=True)
    boundary = nearest_existing_storage_parent(target)
    if not storage_creation_boundary_is_trusted(
        boundary,
        target,
        is_windows=_IS_WINDOWS,
    ):
        if _IS_WINDOWS and (authority := _host_authority_for(target)) is not None:
            return _ensure_host_private_descendant(
                target,
                authority,
                product_owned=product_owned,
            )
        raise PermissionError("Agency Runtime private directory has an untrusted creation boundary")
    create_private_storage_parent(boundary, target, is_windows=_IS_WINDOWS)
    assert_storage_parent_chain(target, allow_missing=False)
    if not storage_parent_is_trusted(target, is_windows=_IS_WINDOWS):
        raise PermissionError("Agency Runtime private directory is not trusted")
    if product_owned:
        _restrict_private_directory(target)
        if not storage_parent_is_trusted(target, is_windows=_IS_WINDOWS):
            raise PermissionError(
                "Agency Runtime private directory is unsafe after permission repair"
            )
    return target


def validate_private_directory(path: Path) -> Path:
    """Validate one existing current-user directory without modifying it."""

    target = _absolute(path)
    assert_storage_parent_chain(target, allow_missing=False)
    if not storage_parent_is_trusted(target, is_windows=_IS_WINDOWS):
        if (
            _IS_WINDOWS
            and (authority := _host_authority_for(target)) is not None
            and _host_descendant_is_private(target, authority)
        ):
            return target
        raise PermissionError("Agency Runtime private directory is not trusted")
    return target


def private_runtime_root() -> Path:
    """Return the validated per-user root for Agency-owned private state."""

    primary = Path.home() / _RUNTIME_ROOT_NAME
    try:
        return ensure_private_directory(primary)
    except (OSError, PermissionError):
        if not _IS_WINDOWS:
            raise
    identities = {
        str(current_process_user_sid(is_windows=True) or ""),
        *current_process_restricted_sids(is_windows=True),
    }
    identities.discard("")
    if not identities:
        raise PermissionError("Agency Runtime cannot identify a private Windows token root")
    digest = hashlib.sha256("\n".join(sorted(identities)).encode()).hexdigest()[:16]
    fallback = Path(tempfile.gettempdir()) / f"agency-runtime-token-{digest}"
    return ensure_private_directory(fallback)


def private_runtime_directory(name: str) -> Path:
    """Return one validated named directory below the private runtime root."""

    component = _validate_component(name, label="runtime directory name")
    return ensure_private_directory(private_runtime_root() / component)


def _capture_directory_identity(path: Path) -> PrivateDirectoryIdentity:
    metadata = os.lstat(path)
    inode = int(getattr(metadata, "st_ino", 0) or 0)
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
        or inode <= 0
    ):
        raise PermissionError("Agency Runtime private directory identity is unavailable")
    validate_private_directory(path)
    return PrivateDirectoryIdentity(
        path=path,
        device=int(metadata.st_dev),
        inode=inode,
    )


def allocate_private_directory(
    root: Path,
    *,
    prefix: str,
) -> PrivateDirectoryIdentity:
    """Create one exclusive random child below an already-private root."""

    safe_prefix = _validate_component(prefix, label="private directory prefix")
    private_root = validate_private_directory(root)
    for _attempt in range(100):
        candidate = private_root / f"{safe_prefix}-{secrets.token_hex(16)}"
        try:
            os.mkdir(candidate, 0o777 if _IS_WINDOWS else stat.S_IRWXU)
        except FileExistsError:
            continue
        try:
            ensure_private_directory(candidate)
            return _capture_directory_identity(candidate)
        except BaseException:
            with suppress(OSError):
                os.rmdir(candidate)
            raise
    raise RuntimeError("could not allocate a private Agency Runtime directory")


def allocate_host_private_directory(
    *,
    prefix: str,
    home_dir: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> PrivateDirectoryIdentity:
    """Allocate one ephemeral child below an exact host-attested Codex root."""

    safe_prefix = _validate_component(prefix, label="private directory prefix")
    parent_guard = _codex_host_private_parent(
        home_dir=home_dir,
        environment=environment,
    )
    try:
        for _attempt in range(100):
            source = os.environ if environment is None else environment
            thread_id = _codex_thread_id(source.get("CODEX_THREAD_ID", "").strip())
            thread_hex = uuid.UUID(thread_id).hex
            candidate = parent_guard.path / (
                f".a-{thread_hex}-{safe_prefix[:8]}-{secrets.token_hex(12)}"
            )
            guard = create_windows_logon_private_directory(
                candidate,
                parent_guard=parent_guard,
                is_windows=True,
            )
            if guard is None:
                continue
            metadata = os.lstat(candidate)
            identity = PrivateDirectoryIdentity(
                candidate,
                int(metadata.st_dev),
                int(getattr(metadata, "st_ino", 0) or 0),
                guard=guard,
                parent_guard=parent_guard,
            )
            if _identity_is_current(identity):
                _register_host_authority(identity)
                return identity
            guard.close()
            raise PermissionError("Codex private scratch changed during allocation")
    except BaseException:
        parent_guard.close()
        raise
    parent_guard.close()
    raise RuntimeError("could not allocate a unique Codex private scratch directory")


def _filesystem_identity_is_current(identity: PrivateDirectoryIdentity) -> bool:
    try:
        metadata = os.lstat(identity.path)
    except OSError:
        return False
    return bool(
        not metadata_is_link_or_reparse_point(metadata)
        and stat.S_ISDIR(metadata.st_mode)
        and int(metadata.st_dev) == identity.device
        and int(getattr(metadata, "st_ino", 0) or 0) == identity.inode
    )


def _identity_is_current(identity: PrivateDirectoryIdentity) -> bool:
    if not _filesystem_identity_is_current(identity):
        return False
    guarded = identity.guard is not None
    guard_current = not guarded or identity.guard.is_current()
    parent_current = identity.parent_guard is None or identity.parent_guard.is_current()
    trusted = (
        windows_directory_prevents_untrusted_writes(
            identity.path,
            is_windows=True,
            final_parent=True,
            private_access=True,
        )
        if guarded
        else (
            storage_parent_is_trusted(identity.path, is_windows=_IS_WINDOWS)
            or (
                _IS_WINDOWS
                and (authority := _host_authority_for(identity.path)) is not None
                and _host_descendant_is_private(identity.path, authority)
            )
        )
    )
    return bool(guard_current and parent_current and trusted)


def _close_identity_guards(identity: PrivateDirectoryIdentity) -> None:
    _discard_host_authority(identity)
    if identity.guard is not None:
        identity.guard.close()
    if identity.parent_guard is not None:
        identity.parent_guard.close()


def _remove_private_tree(root: Path) -> None:
    """Remove a quarantined tree, retrying exact Windows read-only children."""

    def retry_readonly(
        function: Callable[..., object],
        path: str,
        exc_info: tuple[object, BaseException, object],
    ) -> None:
        error = exc_info[1]
        candidate = _absolute(Path(path))
        try:
            candidate.relative_to(_absolute(root))
            metadata = os.lstat(candidate)
        except (OSError, ValueError) as inspection_error:
            raise error from inspection_error
        if (
            not _IS_WINDOWS
            or not isinstance(error, PermissionError)
            or metadata_is_link_or_reparse_point(metadata)
        ):
            raise error
        os.chmod(candidate, stat.S_IWRITE)
        function(candidate)

    shutil.rmtree(root, onerror=retry_readonly)


def _private_cleanup_parent(
    identity: PrivateDirectoryIdentity,
) -> tuple[Path, bool]:
    guard = identity.guard
    parent_guard = identity.parent_guard
    if (guard is None) != (parent_guard is None):
        _close_identity_guards(identity)
        raise PermissionError("private directory guard receipt is incomplete")
    if guard is None:
        return validate_private_directory(identity.path.parent), False
    parent_guard = cast(WindowsDirectoryGuard, parent_guard)
    if not prepare_windows_logon_private_directory_cleanup(guard):
        _close_identity_guards(identity)
        raise PermissionError("refusing to unseal a changed Codex private directory")
    guard.close()
    if not parent_guard.is_current():
        _close_identity_guards(identity)
        raise PermissionError("refusing cleanup through a changed Codex task root")
    return parent_guard.path, True


def _quarantine_private_directory(
    identity: PrivateDirectoryIdentity,
    parent: Path,
) -> PrivateDirectoryIdentity:
    for _attempt in range(100):
        quarantine = parent / f".cleanup-{secrets.token_hex(16)}"
        try:
            os.rename(identity.path, quarantine)
        except FileExistsError:
            continue
        except OSError as exc:
            if not _filesystem_identity_is_current(identity):
                raise PermissionError(
                    "refusing to clean a replaced Agency Runtime private directory"
                ) from exc
            raise
        return PrivateDirectoryIdentity(
            path=quarantine,
            device=identity.device,
            inode=identity.inode,
        )
    raise PrivateDirectoryCleanupError("could not allocate an Agency Runtime cleanup quarantine")


def _cleanup_identity_is_current(
    identity: PrivateDirectoryIdentity,
    *,
    host_guarded: bool,
) -> bool:
    if host_guarded:
        return _filesystem_identity_is_current(identity)
    return _identity_is_current(identity)


def _restore_cleanup_quarantine(
    original: PrivateDirectoryIdentity,
    quarantined: PrivateDirectoryIdentity,
    *,
    host_guarded: bool,
    error: BaseException,
) -> None:
    try:
        metadata = os.lstat(quarantined.path)
        real_directory = bool(
            not metadata_is_link_or_reparse_point(metadata) and stat.S_ISDIR(metadata.st_mode)
        )
        parent_is_current = (
            original.parent_guard is not None and original.parent_guard.is_current()
            if host_guarded
            else validate_private_directory(original.path.parent) == original.path.parent
        )
    except (OSError, PermissionError):
        real_directory = False
        parent_is_current = False
    if not real_directory or not parent_is_current or original.path.exists():
        add_exception_note(
            error,
            "Agency Runtime cleanup quarantine could not be restored safely",
        )
        return
    try:
        os.rename(quarantined.path, original.path)
    except OSError as restore_error:
        add_exception_note(
            error,
            f"Agency Runtime cleanup quarantine restore failed: {restore_error}",
        )


def remove_private_directory(identity: PrivateDirectoryIdentity) -> None:
    """Quarantine then remove a tree only while its root identity is unchanged."""

    try:
        os.lstat(identity.path)
    except FileNotFoundError:
        _close_identity_guards(identity)
        return
    if not _identity_is_current(identity):
        _close_identity_guards(identity)
        raise PermissionError("refusing to clean a replaced Agency Runtime private directory")
    parent, host_guarded = _private_cleanup_parent(identity)
    try:
        quarantined = _quarantine_private_directory(identity, parent)
        try:
            if not _cleanup_identity_is_current(
                quarantined,
                host_guarded=host_guarded,
            ):
                raise PermissionError(
                    "refusing to clean a replaced Agency Runtime private directory"
                )
            _remove_private_tree(quarantined.path)
        except BaseException as error:
            _restore_cleanup_quarantine(
                identity,
                quarantined,
                host_guarded=host_guarded,
                error=error,
            )
            raise
    finally:
        _close_identity_guards(identity)


@contextmanager
def private_temporary_directory(
    *,
    prefix: str,
    category: str = "ephemeral",
) -> Iterator[Path]:
    """Yield an unpredictable owner-private directory outside ambient temp."""

    try:
        root = private_runtime_directory(category)
        identity = allocate_private_directory(root, prefix=prefix)
    except (OSError, PermissionError):
        if not _IS_WINDOWS:
            raise
        identity = allocate_host_private_directory(prefix=prefix)
    body_error: BaseException | None = None
    try:
        yield identity.path
    except BaseException as exc:
        body_error = exc
        raise
    finally:
        try:
            remove_private_directory(identity)
        except Exception as cleanup_error:
            if body_error is not None:
                add_exception_note(
                    body_error, f"Agency Runtime private temporary cleanup failed: {cleanup_error}"
                )
            else:
                raise PrivateDirectoryCleanupError(
                    "Agency Runtime private temporary cleanup failed"
                ) from cleanup_error


__all__ = [
    "PrivateDirectoryCleanupError",
    "PrivateDirectoryIdentity",
    "allocate_host_private_directory",
    "allocate_private_directory",
    "bootstrap_private_directory",
    "ensure_private_directory",
    "private_runtime_directory",
    "private_runtime_root",
    "private_temporary_directory",
    "reattest_codex_host_private_path",
    "remove_private_directory",
    "validate_private_directory",
]
