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
from typing import Any, BinaryIO

import yaml

from agency_runtime.core.bounded_io import (
    FileSizeLimitError,
    UnsafeFileError,
    read_bounded_regular_file,
    restrict_posix_path_permissions,
)
from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded
from agency_runtime.core.configuration_contracts import (
    LOCK_TIMEOUT_SECONDS,
    MAX_CONFIG_BYTES,
    ConfigLockError,
    ConfigurationError,
    ConfigValidationError,
)
from agency_runtime.core.configuration_identity import resolve_config_identity_path
from agency_runtime.core.filesystem_trust import (
    absolute_path as _absolute,
)
from agency_runtime.core.filesystem_trust import (
    directory_chain as _directory_chain,
)
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _metadata_is_link_or_reparse,
)
from agency_runtime.core.filesystem_trust import (
    posix_directory_chain_is_trusted,
)
from agency_runtime.core.filesystem_trust import (
    posix_directory_has_default_acl as _posix_directory_has_default_acl,
)
from agency_runtime.core.path_authority import private_path_authority_covers
from agency_runtime.core.windows_acl import (
    WindowsACLSafetyError,
    restrict_windows_acl,
    windows_directory_prevents_untrusted_writes,
)

PermissionRestrictor = Callable[..., bool]
PathCheck = Callable[[Path], bool]
NamespaceProbe = Callable[[Path, bool, bool], bool]

_WINDOWS_REPLACE_RETRY_DELAYS = (0.002, 0.004, 0.008, 0.016, 0.032, 0.064)


def _effective_posix_uid(metadata: os.stat_result) -> int | None:
    getter = getattr(os, "geteuid", None)
    if callable(getter):
        return int(getter())
    # Windows-hosted tests intentionally exercise POSIX branches. Real POSIX
    # runtimes always expose geteuid; st_uid is the only simulation identity.
    return int(metadata.st_uid) if os.name == "nt" else None


def config_namespace_is_trusted(
    path: Path,
    *,
    is_windows: bool,
    windows_acl_probe: NamespaceProbe | None = None,
    effective_uid: int | None = None,
) -> bool:
    """Return whether another account cannot replace one configuration path."""

    parent = _absolute(path).parent
    if is_windows and windows_acl_probe is None and private_path_authority_covers(parent):
        return True
    existing: list[tuple[Path, os.stat_result]] = []
    missing = False
    for candidate in _directory_chain(parent):
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            missing = True
            break
        except OSError:
            return False
        if _metadata_is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
            return False
        existing.append((candidate, metadata))
    if not existing:
        return False

    if is_windows:
        try:
            probe = windows_acl_probe or (
                lambda candidate, final_parent, prospective_child: (
                    windows_directory_prevents_untrusted_writes(
                        candidate,
                        is_windows=True,
                        final_parent=final_parent,
                        prospective_child=prospective_child,
                        allow_inheritable_read=final_parent,
                    )
                )
            )
            return all(
                probe(
                    candidate,
                    not missing and candidate == parent,
                    missing and index == len(existing) - 1,
                )
                for index, (candidate, _metadata) in enumerate(existing)
            )
        except Exception:
            return False

    uid = _effective_posix_uid(existing[-1][1]) if effective_uid is None else effective_uid
    if uid is None:
        return False
    boundary_path, _boundary = existing[-1]
    # A final/prospective parent may be readable and traversable (0755), but it
    # may not let another account create, delete, or rename the config name.
    return posix_directory_chain_is_trusted(
        existing,
        effective_uid=uid,
        final_path=boundary_path,
        final_owner_must_match=False,
        forbidden_final_mode=stat.S_IWGRP | stat.S_IWOTH,
        default_acl_probe=_posix_directory_has_default_acl,
    )


def assert_config_namespace(
    path: Path,
    *,
    is_windows: bool | None = None,
    windows_acl_probe: NamespaceProbe | None = None,
    effective_uid: int | None = None,
) -> None:
    windows = os.name == "nt" if is_windows is None else is_windows
    if not config_namespace_is_trusted(
        path,
        is_windows=windows,
        windows_acl_probe=windows_acl_probe,
        effective_uid=effective_uid,
    ):
        raise ConfigurationError("configuration parent permits cross-account path substitution")


def resolve_config_path(
    path: str | Path | None = None,
    *,
    home_dir: str | Path | None = None,
    use_environment: bool = True,
    platform_name: str | None = None,
) -> Path:
    """Resolve one durable config identity shared by every local control surface."""

    home = Path.home() if home_dir is None else home_dir
    return resolve_config_identity_path(
        path,
        home_dir=home,
        use_environment=use_environment,
        platform_name=platform_name,
    )


def revision(raw: bytes) -> str:
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _ensure_config_file_private(
    path: Path,
    *,
    restrict: PermissionRestrictor | None = None,
    path_check: PathCheck | None = None,
    is_windows: bool | None = None,
) -> bool:
    """Harden a current-user config file before any content is consumed."""

    checker = path_check or is_link_or_reparse_point
    restrictor = restrict or restrict_permissions
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    if (
        checker(path)
        or not stat.S_ISREG(metadata.st_mode)
        or int(getattr(metadata, "st_nlink", 0) or 0) != 1
    ):
        raise ConfigurationError("configuration file must be one regular non-link file")
    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        uid = _effective_posix_uid(metadata)
        if uid is None or int(metadata.st_uid) != uid:
            raise ConfigurationError("configuration file must be owned by the current user")
    restrictor(path, required=True)
    return True


def read_raw(path: Path) -> bytes:
    """Read at most one byte beyond the accepted config size."""

    assert_config_namespace(path)
    if not _ensure_config_file_private(path):
        return b""
    try:
        raw = read_bounded_regular_file(
            path,
            limit=MAX_CONFIG_BYTES,
            label="configuration file",
        )
    except FileSizeLimitError as exc:
        raise ConfigValidationError("configuration file exceeds the size limit") from exc
    except OSError as exc:
        raise ConfigurationError("configuration file could not be read") from exc
    return raw


def parse_document(raw: bytes) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        loaded = safe_load_bounded(raw)
    except (BoundedYAMLError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ConfigValidationError("configuration file is not valid UTF-8 YAML") from exc
    if loaded is None:
        raise ConfigValidationError("configuration root must be a mapping")
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
    return _metadata_is_link_or_reparse(metadata)


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
    try:
        restrict_posix_path_permissions(path, directory=directory)
    except UnsafeFileError as exc:
        raise ConfigurationError(str(exc)) from exc
    except OSError as exc:
        if required:
            raise ConfigurationError("owner-only file permissions could not be enforced") from exc
        return False
    return True


def ensure_config_parent(
    path: Path,
    *,
    restrict: PermissionRestrictor = restrict_permissions,
    path_check: PathCheck = is_link_or_reparse_point,
    is_windows: bool | None = None,
) -> None:
    """Create a private target directory without taking over arbitrary parents."""

    parent = path.parent
    windows = os.name == "nt" if is_windows is None else is_windows
    if path_check(parent):
        raise ConfigurationError("refusing configuration directory symlink or reparse point")
    if windows and private_path_authority_covers(parent):
        try:
            os.lstat(parent)
        except FileNotFoundError:
            from agency_runtime.core.private_paths import ensure_private_directory

            try:
                ensure_private_directory(parent)
            except (OSError, PermissionError) as exc:
                raise ConfigurationError(
                    "configuration parent permits cross-account path substitution"
                ) from exc
        except OSError as exc:
            raise ConfigurationError("configuration parent identity is unavailable") from exc
    try:
        assert_config_namespace(path, is_windows=windows)
    except ConfigurationError:
        # Restricted Windows hosts can provide an identity-pinned private root
        # whose missing descendants do not yet have DACL evidence.  Let that
        # capability create each component privately, then subject the result
        # to the same namespace predicate.  Arbitrary external parents have no
        # such authority and still fail closed.
        if not windows:
            raise
        from agency_runtime.core.private_paths import ensure_private_directory

        try:
            ensure_private_directory(parent)
        except (OSError, PermissionError) as exc:
            raise ConfigurationError(
                "configuration parent permits cross-account path substitution"
            ) from exc
        assert_config_namespace(path, is_windows=windows)
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
    assert_config_namespace(path, is_windows=windows)


def _replace_atomically(source: Path, target: Path, *, is_windows: bool) -> None:
    """Replace ``target``, tolerating brief Windows reader share locks."""

    if not is_windows:
        os.replace(source, target)
        return
    for delay in _WINDOWS_REPLACE_RETRY_DELAYS:
        try:
            os.replace(source, target)
        except PermissionError:
            time.sleep(delay)
        else:
            return
    os.replace(source, target)


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
    windows = os.name == "nt" if is_windows is None else is_windows
    if path_check(path):
        raise ConfigurationError("refusing to replace a configuration symlink or reparse point")
    ensure_parent(path)
    assert_config_namespace(path, is_windows=windows)
    _ensure_config_file_private(
        path,
        restrict=restrict,
        path_check=path_check,
        is_windows=windows,
    )
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
        _replace_atomically(temporary, path, is_windows=windows)
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


def _prepare_config_lock_handle(
    handle: BinaryIO,
    *,
    lock_path: Path,
    path_check: PathCheck,
    restrict: PermissionRestrictor,
    windows: bool,
) -> None:
    """Validate, initialize, and privatize one already-open lock file."""

    metadata = os.fstat(handle.fileno())
    if path_check(lock_path) or not stat.S_ISREG(metadata.st_mode):
        raise ConfigLockError("refusing configuration lock symlink or non-regular file")
    if metadata.st_size == 0:
        handle.write(b"\0")
        handle.flush()
        metadata = os.fstat(handle.fileno())
    if int(getattr(metadata, "st_nlink", 0) or 0) != 1:
        raise ConfigLockError("refusing configuration lock with multiple links")
    if not windows:
        uid = _effective_posix_uid(metadata)
        if uid is None or int(metadata.st_uid) != uid:
            raise ConfigLockError("configuration lock must be owned by the current user")
    if hasattr(os, "fchmod"):
        os.fchmod(handle.fileno(), stat.S_IRUSR | stat.S_IWUSR)
    elif windows:
        restrict(lock_path, required=True)


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
        assert_config_namespace(path, is_windows=windows)
        _ensure_config_file_private(
            path,
            restrict=restrict,
            path_check=path_check,
            is_windows=windows,
        )
        _prepare_config_lock_handle(
            handle,
            lock_path=lock_path,
            path_check=path_check,
            restrict=restrict,
            windows=windows,
        )
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
