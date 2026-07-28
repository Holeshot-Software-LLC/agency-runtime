"""Durable, owner-private master switch for Agency Runtime.

The switch intentionally lives outside the normal configuration document so a
host can bypass Agency before config loading, hook correlation, routing, or
delegation begins.  A missing document means enabled.  Any unreadable or
invalid document also means enabled to the enforcement fast path, while the
diagnostic reader reports the underlying fault.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import stat
import threading
import time
from collections import OrderedDict
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import (
    BoundedFileError,
    FileSizeLimitError,
    read_bounded_regular_file,
)
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.filesystem_trust import absolute_path as _lexical_absolute_path
from agency_runtime.core.filesystem_trust import same_file_identity as _same_file
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    create_private_storage_parent,
    metadata_is_link_or_reparse_point,
    nearest_existing_storage_parent,
    storage_creation_boundary_is_trusted,
    storage_parent_is_trusted,
)
from agency_runtime.core.windows_acl import (
    WindowsACLSafetyError,
    current_process_has_control_forgery_access,
    current_process_token_is_restricted,
    restrict_windows_acl,
    windows_directory_prevents_untrusted_writes,
)

RUNTIME_CONTROL_SCHEMA_VERSION = 1
MAX_RUNTIME_CONTROL_BYTES = 4 * 1024
DEFAULT_LOCK_TIMEOUT_SECONDS = 5.0
MAX_LOCK_TIMEOUT_SECONDS = 300.0

_CONTROL_KEYS = frozenset({"schema_version", "enabled", "generation", "updated_at", "source"})
_DEFAULT_UPDATED_AT = "1970-01-01T00:00:00Z"
_MAX_GENERATION = (1 << 63) - 1
_MAX_SOURCE_BYTES = 64
_MAX_TIMESTAMP_BYTES = 64
_CACHE_LIMIT = 64
_WINDOWS_REPLACE_DELAYS = (0.002, 0.004, 0.008, 0.016, 0.032, 0.064)
_DASHBOARD_BROKER_TIMEOUT_SECONDS = 0.25
_CANARY_CONTROL_PATH_ENV = "AGENCY_CANARY_CONTROL_PATH"


class RuntimeControlError(RuntimeError):
    """Base class for a durable master-switch failure."""


class RuntimeControlValidationError(RuntimeControlError):
    """The persisted control document or requested update is invalid."""


class RuntimeControlSecurityError(RuntimeControlError):
    """The control path does not satisfy the owner-private trust contract."""


class RuntimeControlBrokerError(RuntimeControlSecurityError):
    """The canonical restricted reader could not obtain owner-service state."""


class RuntimeControlConflictError(RuntimeControlError):
    """A compare-and-swap update observed a different generation."""


class RuntimeControlBusyError(RuntimeControlError):
    """Another process retained the control lock past the bounded deadline."""


@dataclass(frozen=True, slots=True)
class RuntimeControlSnapshot:
    """One validated master-control document plus its materialization state."""

    schema_version: int
    enabled: bool
    generation: int
    updated_at: str
    source: str
    materialized: bool

    def as_document(self) -> dict[str, Any]:
        """Return the strict persisted-document projection."""

        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "generation": self.generation,
            "updated_at": self.updated_at,
            "source": self.source,
        }


@dataclass(frozen=True)
class _CacheEntry:
    file_identity: tuple[int, ...]
    directory_identities: tuple[tuple[int, ...], ...]
    document: dict[str, Any]


_cache_lock = threading.RLock()
_state_cache: OrderedDict[str, _CacheEntry] = OrderedDict()


def _default_document() -> dict[str, Any]:
    return {
        "schema_version": RUNTIME_CONTROL_SCHEMA_VERSION,
        "enabled": True,
        "generation": 0,
        "updated_at": _DEFAULT_UPDATED_AT,
        "source": "default",
    }


def _control_snapshot(
    document: Mapping[str, Any],
    *,
    materialized: bool,
) -> RuntimeControlSnapshot:
    """Project one already validated document into immutable lifecycle evidence."""

    return RuntimeControlSnapshot(
        schema_version=int(document["schema_version"]),
        enabled=bool(document["enabled"]),
        generation=int(document["generation"]),
        updated_at=str(document["updated_at"]),
        source=str(document["source"]),
        materialized=materialized,
    )


def _absolute_path(path: str | Path) -> Path:
    try:
        text = os.fspath(path)
    except TypeError as exc:
        raise RuntimeControlValidationError("runtime control path must be text") from exc
    if not isinstance(text, str):
        raise RuntimeControlValidationError("runtime control path must be text")
    try:
        encoded = text.encode("utf-8")
    except UnicodeError as exc:
        raise RuntimeControlValidationError("runtime control path is invalid") from exc
    if (
        not text
        or len(encoded) > 4096
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        raise RuntimeControlValidationError("runtime control path is invalid")
    return _lexical_absolute_path(Path(text))


def runtime_control_path(*, home_dir: str | Path | None = None) -> Path:
    """Return the canonical per-user durable master-switch path."""

    home = Path.home() if home_dir is None else _absolute_path(home_dir)
    return _absolute_path(home / ".agency-runtime" / "run" / "control.json")


def _target_path(
    *,
    path: str | Path | None,
    home_dir: str | Path | None,
) -> Path:
    if path is not None:
        return _absolute_path(path)
    if home_dir is not None:
        return runtime_control_path(home_dir=home_dir)
    if os.environ.get("AGENCY_CANARY_MODE") == "1":
        canary_path = os.environ.get(_CANARY_CONTROL_PATH_ENV, "").strip()
        if canary_path:
            if not Path(canary_path).is_absolute():
                raise RuntimeControlValidationError("canary runtime control path must be absolute")
            target = _absolute_path(canary_path)
            expected_suffix = Path(".agency-runtime") / "run" / "control.json"
            if target.parts[-3:] != expected_suffix.parts:
                raise RuntimeControlValidationError("canary runtime control path is not canonical")
            return target
    return runtime_control_path()


def _metadata_identity(metadata: os.stat_result) -> tuple[int, ...]:
    """Capture fields that change for replacement and in-place mutation."""

    return (
        int(metadata.st_dev),
        int(getattr(metadata, "st_ino", 0) or 0),
        int(metadata.st_mode),
        int(getattr(metadata, "st_uid", -1)),
        int(getattr(metadata, "st_nlink", 0) or 0),
        int(metadata.st_size),
        int(getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000))),
        int(getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1_000_000_000))),
    )


def _directory_candidates(path: Path) -> tuple[Path, ...]:
    anchor = Path(path.anchor)
    parts = path.parts[1:]
    return (anchor, *(anchor.joinpath(*parts[:index]) for index in range(1, len(parts) + 1)))


def _current_uid() -> int | None:
    getter = getattr(os, "geteuid", None)
    return int(getter()) if callable(getter) else None


def _owner_private_metadata(
    path: Path,
    metadata: os.stat_result,
    *,
    directory: bool,
) -> bool:
    expected_kind = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not expected_kind
        or int(getattr(metadata, "st_ino", 0) or 0) <= 0
        or (not directory and int(getattr(metadata, "st_nlink", 0) or 0) != 1)
    ):
        return False
    if os.name == "nt":
        return windows_directory_prevents_untrusted_writes(
            path,
            is_windows=True,
            final_parent=True,
            private_access=True,
        )
    uid = _current_uid()
    expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
    return bool(
        uid is not None
        and int(metadata.st_uid) == uid
        and stat.S_IMODE(metadata.st_mode) == expected_mode
    )


def _snapshot_private_parent(path: Path) -> tuple[tuple[Path, os.stat_result], ...]:
    try:
        snapshot = tuple(
            (candidate, os.lstat(candidate)) for candidate in _directory_candidates(path)
        )
    except OSError as exc:
        raise RuntimeControlSecurityError("runtime control parent could not be inspected") from exc
    if any(
        metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _candidate, metadata in snapshot
    ):
        raise RuntimeControlSecurityError(
            "runtime control parent chain must contain only real directories"
        )
    if not storage_parent_is_trusted(path, is_windows=os.name == "nt"):
        raise RuntimeControlSecurityError(
            "runtime control parent permits cross-account path substitution"
        )
    if not _owner_private_metadata(path, snapshot[-1][1], directory=True):
        raise RuntimeControlSecurityError("runtime control parent must be owner-private")
    return snapshot


def _validate_directory_snapshot(
    snapshot: tuple[tuple[Path, os.stat_result], ...],
) -> None:
    for candidate, expected in snapshot:
        try:
            current = os.lstat(candidate)
        except OSError as exc:
            raise RuntimeControlSecurityError(
                "runtime control parent changed during operation"
            ) from exc
        if (
            metadata_is_link_or_reparse_point(current)
            or not stat.S_ISDIR(current.st_mode)
            or not _same_file(expected, current)
        ):
            raise RuntimeControlSecurityError("runtime control parent changed during operation")


def _prepare_parent(target: Path) -> tuple[tuple[Path, os.stat_result], ...]:
    try:
        assert_storage_parent_chain(target.parent, allow_missing=True)
        boundary = nearest_existing_storage_parent(target.parent)
        if not storage_creation_boundary_is_trusted(
            boundary,
            target.parent,
            is_windows=os.name == "nt",
        ):
            raise RuntimeControlSecurityError(
                "runtime control parent has an untrusted creation boundary"
            )
        create_private_storage_parent(
            boundary,
            target.parent,
            is_windows=os.name == "nt",
        )
    except RuntimeControlError:
        raise
    except (OSError, PermissionError) as exc:
        raise RuntimeControlSecurityError(
            "runtime control parent could not be created securely"
        ) from exc
    return _snapshot_private_parent(target.parent)


def _validate_absent_parent(target: Path) -> None:
    """Prove a missing state cannot be hidden behind an unsafe path."""

    try:
        assert_storage_parent_chain(target.parent, allow_missing=True)
        boundary = nearest_existing_storage_parent(target.parent)
    except (OSError, PermissionError) as exc:
        raise RuntimeControlSecurityError("runtime control parent is unsafe") from exc
    if boundary == target.parent:
        _snapshot_private_parent(target.parent)
        return
    if not storage_creation_boundary_is_trusted(
        boundary,
        target.parent,
        is_windows=os.name == "nt",
    ):
        raise RuntimeControlSecurityError(
            "runtime control parent has an untrusted creation boundary"
        )


def _validate_regular_private_file(path: Path, metadata: os.stat_result) -> None:
    if not _owner_private_metadata(path, metadata, directory=False):
        raise RuntimeControlSecurityError(
            "runtime control file must be owner-private, regular, and single-link"
        )


def _validate_source(value: object) -> str:
    if not isinstance(value, str):
        raise RuntimeControlValidationError("runtime control source must be text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise RuntimeControlValidationError("runtime control source is invalid") from exc
    if (
        not value
        or len(encoded) > _MAX_SOURCE_BYTES
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise RuntimeControlValidationError("runtime control source is invalid")
    return value


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise RuntimeControlValidationError("runtime control timestamp must be text")
    try:
        encoded = value.encode("utf-8")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (UnicodeError, ValueError) as exc:
        raise RuntimeControlValidationError("runtime control timestamp is invalid") from exc
    if (
        not value
        or len(encoded) > _MAX_TIMESTAMP_BYTES
        or parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise RuntimeControlValidationError("runtime control timestamp is invalid")
    return value


def _validate_document(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _CONTROL_KEYS:
        raise RuntimeControlValidationError("runtime control document has an invalid schema")
    schema_version = value.get("schema_version")
    enabled = value.get("enabled")
    generation = value.get("generation")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != RUNTIME_CONTROL_SCHEMA_VERSION
    ):
        raise RuntimeControlValidationError("runtime control schema version is unsupported")
    if not isinstance(enabled, bool):
        raise RuntimeControlValidationError("runtime control enabled value must be boolean")
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or not 0 <= generation <= _MAX_GENERATION
    ):
        raise RuntimeControlValidationError("runtime control generation is invalid")
    return {
        "schema_version": RUNTIME_CONTROL_SCHEMA_VERSION,
        "enabled": enabled,
        "generation": generation,
        "updated_at": _validate_timestamp(value.get("updated_at")),
        "source": _validate_source(value.get("source")),
    }


def validate_runtime_control_document(value: object) -> dict[str, Any]:
    """Validate and normalize one untrusted runtime-control API payload."""

    return _validate_document(value)


def _parse_document(raw: bytes) -> dict[str, Any]:
    try:
        value = safe_load_bounded_json(
            raw,
            maximum_bytes=MAX_RUNTIME_CONTROL_BYTES,
            maximum_depth=4,
            maximum_nodes=16,
        )
    except (BoundedJSONError, UnicodeError, ValueError) as exc:
        raise RuntimeControlValidationError(
            "runtime control document is not valid bounded UTF-8 JSON"
        ) from exc
    return _validate_document(value)


def _cache_key(target: Path) -> str:
    return os.path.normcase(str(target))


def _cache_get(
    target: Path,
    metadata: os.stat_result,
    directory_snapshot: tuple[tuple[Path, os.stat_result], ...],
) -> dict[str, Any] | None:
    key = _cache_key(target)
    file_identity = _metadata_identity(metadata)
    directory_identities = tuple(_metadata_identity(item) for _path, item in directory_snapshot)
    with _cache_lock:
        entry = _state_cache.get(key)
        if (
            entry is None
            or entry.file_identity != file_identity
            or entry.directory_identities != directory_identities
        ):
            return None
        _state_cache.move_to_end(key)
        return dict(entry.document)


def _cache_put(
    target: Path,
    metadata: os.stat_result,
    directory_snapshot: tuple[tuple[Path, os.stat_result], ...],
    document: Mapping[str, Any],
) -> None:
    key = _cache_key(target)
    entry = _CacheEntry(
        file_identity=_metadata_identity(metadata),
        directory_identities=tuple(_metadata_identity(item) for _path, item in directory_snapshot),
        document=dict(document),
    )
    with _cache_lock:
        _state_cache[key] = entry
        _state_cache.move_to_end(key)
        while len(_state_cache) > _CACHE_LIMIT:
            _state_cache.popitem(last=False)


def clear_runtime_control_cache() -> None:
    """Drop process-local state snapshots (primarily useful for diagnostics/tests)."""

    with _cache_lock:
        _state_cache.clear()


def _read_existing(
    target: Path,
    *,
    use_cache: bool,
) -> dict[str, Any]:
    directory_snapshot = _snapshot_private_parent(target.parent)
    try:
        before = os.lstat(target)
    except OSError as exc:
        raise RuntimeControlSecurityError("runtime control file could not be inspected") from exc
    _validate_regular_private_file(target, before)
    if use_cache:
        cached = _cache_get(target, before, directory_snapshot)
        if cached is not None:
            _validate_directory_snapshot(directory_snapshot)
            current = os.lstat(target)
            if _metadata_identity(current) == _metadata_identity(before):
                return cached
    try:
        raw = read_bounded_regular_file(
            target,
            limit=MAX_RUNTIME_CONTROL_BYTES,
            label="runtime control file",
        )
    except FileSizeLimitError as exc:
        raise RuntimeControlValidationError(
            "runtime control document exceeds the 4 KiB limit"
        ) from exc
    except (BoundedFileError, OSError) as exc:
        raise RuntimeControlSecurityError("runtime control file could not be read safely") from exc
    try:
        after = os.lstat(target)
    except OSError as exc:
        raise RuntimeControlSecurityError("runtime control file changed during read") from exc
    if _metadata_identity(after) != _metadata_identity(before):
        raise RuntimeControlSecurityError("runtime control file changed during read")
    _validate_directory_snapshot(directory_snapshot)
    document = _parse_document(raw)
    _cache_put(target, after, directory_snapshot, document)
    return document


def read_runtime_control_snapshot(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    use_cache: bool = True,
) -> RuntimeControlSnapshot:
    """Read strict master state while preserving whether it exists durably."""

    target = _target_path(path=path, home_dir=home_dir)
    try:
        os.lstat(target)
    except FileNotFoundError:
        _validate_absent_parent(target)
        return _control_snapshot(_default_document(), materialized=False)
    except OSError as exc:
        raise RuntimeControlSecurityError("runtime control file could not be inspected") from exc
    return _control_snapshot(
        _read_existing(target, use_cache=use_cache),
        materialized=True,
    )


def read_runtime_control(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Read the strict control document; a genuinely absent document is enabled."""

    return read_runtime_control_snapshot(
        path=path,
        home_dir=home_dir,
        use_cache=use_cache,
    ).as_document()


def _restricted_windows_control_target(target: Path) -> bool:
    """Limit the reduced-privilege reader to the canonical per-user identity."""

    if os.name != "nt" or _cache_key(target) != _cache_key(runtime_control_path()):
        return False
    try:
        return current_process_token_is_restricted(is_windows=True)
    except Exception:
        return False


def _read_restricted_windows_control(
    target: Path,
    *,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Read canonical state from a sandbox that cannot request ``READ_CONTROL``.

    Windows application sandboxes can retain read access to a user-owned file
    while being denied ACL inspection. The authoritative writer still uses the
    strict owner-private path. This reduced-privilege reader accepts only the
    canonical home-relative identity, proves every component is a stable real
    object, and separately verifies that the current sandbox has none of the
    individual rights that could alter or replace it.
    """

    if not _restricted_windows_control_target(target):
        raise RuntimeControlSecurityError("restricted control reader is unavailable")
    home = _absolute_path(Path.home())
    directory_paths = (
        home,
        home / ".agency-runtime",
        home / ".agency-runtime" / "run",
    )
    try:
        directory_snapshot = tuple(
            (candidate, os.lstat(candidate)) for candidate in directory_paths
        )
        before = os.lstat(target)
    except OSError as exc:
        raise RuntimeControlSecurityError(
            "restricted runtime control identity could not be inspected"
        ) from exc
    if any(
        metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _candidate, metadata in directory_snapshot
    ):
        raise RuntimeControlSecurityError(
            "restricted runtime control parent must contain only real directories"
        )
    if (
        metadata_is_link_or_reparse_point(before)
        or not stat.S_ISREG(before.st_mode)
        or int(getattr(before, "st_ino", 0) or 0) <= 0
        or int(getattr(before, "st_nlink", 0) or 0) != 1
    ):
        raise RuntimeControlSecurityError(
            "restricted runtime control must be one real regular file"
        )
    mutation_probes = (
        *(
            current_process_has_control_forgery_access(
                candidate,
                directory=True,
                is_windows=True,
            )
            for candidate, _metadata in directory_snapshot
        ),
        current_process_has_control_forgery_access(
            target,
            directory=False,
            is_windows=True,
        ),
    )
    if any(result is not False for result in mutation_probes):
        raise RuntimeControlSecurityError(
            "restricted runtime control path is mutable or could not be proven read-only"
        )
    if use_cache:
        cached = _cache_get(target, before, directory_snapshot)
        if cached is not None:
            _validate_directory_snapshot(directory_snapshot)
            current = os.lstat(target)
            if _metadata_identity(current) == _metadata_identity(before):
                return cached
    try:
        raw = read_bounded_regular_file(
            target,
            limit=MAX_RUNTIME_CONTROL_BYTES,
            label="runtime control file",
        )
        after = os.lstat(target)
    except FileSizeLimitError as exc:
        raise RuntimeControlValidationError(
            "runtime control document exceeds the 4 KiB limit"
        ) from exc
    except (BoundedFileError, OSError) as exc:
        raise RuntimeControlSecurityError(
            "restricted runtime control file could not be read safely"
        ) from exc
    if _metadata_identity(after) != _metadata_identity(before):
        raise RuntimeControlSecurityError("restricted runtime control changed during read")
    _validate_directory_snapshot(directory_snapshot)
    document = _parse_document(raw)
    _cache_put(target, after, directory_snapshot, document)
    return document


def read_effective_runtime_control_snapshot(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    use_cache: bool = True,
) -> RuntimeControlSnapshot:
    """Read effective state and its materialization through the trusted boundary."""

    target = _target_path(path=path, home_dir=home_dir)
    try:
        return read_runtime_control_snapshot(path=target, use_cache=use_cache)
    except RuntimeControlSecurityError:
        if not _restricted_windows_control_target(target):
            raise
    try:
        os.lstat(target)
    except FileNotFoundError:
        return _control_snapshot(_default_document(), materialized=False)
    except OSError as exc:
        raise RuntimeControlSecurityError("runtime control file could not be inspected") from exc
    return _control_snapshot(
        _read_restricted_windows_control(target, use_cache=use_cache),
        materialized=True,
    )


def read_effective_runtime_control(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Read effective state through the strict or reduced-privilege boundary."""

    return read_effective_runtime_control_snapshot(
        path=path,
        home_dir=home_dir,
        use_cache=use_cache,
    ).as_document()


def read_authoritative_runtime_control(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    use_cache: bool = True,
) -> tuple[dict[str, Any], str]:
    """Read master state directly or through the canonical owner service.

    The authenticated dashboard is a recovery boundary only for the implicit
    per-user identity when Windows positively identifies the caller as
    restricted. Explicit ``path`` and ``home_dir`` arguments, validation
    failures, and lock contention are never redirected because the service
    cannot prove that it owns those identities. The dashboard handler itself
    deliberately uses :func:`read_runtime_control` so this fallback cannot
    recurse through ``/api/runtime``.
    """

    direct_arguments: dict[str, Any] = {}
    if path is not None:
        direct_arguments["path"] = path
    if home_dir is not None:
        direct_arguments["home_dir"] = home_dir
    if not use_cache:
        direct_arguments["use_cache"] = False
    try:
        return (
            read_effective_runtime_control(**direct_arguments),
            "direct",
        )
    except RuntimeControlSecurityError:
        target = _target_path(path=path, home_dir=home_dir)
        if (
            path is not None
            or home_dir is not None
            or not _restricted_windows_control_target(target)
        ):
            raise
        try:
            from agency_runtime.core.dashboard_runtime import dashboard_api_request

            response = dashboard_api_request(
                "/api/runtime",
                timeout=_DASHBOARD_BROKER_TIMEOUT_SECONDS,
            )
            if not isinstance(response, Mapping) or set(response) != {"master"}:
                raise ValueError("dashboard master response shape is invalid")
            return validate_runtime_control_document(response.get("master")), "dashboard"
        except (OSError, RuntimeError, ValueError) as broker_error:
            raise RuntimeControlBrokerError(
                "canonical runtime control is inaccessible and the authenticated "
                "dashboard service could not broker it"
            ) from broker_error


def read_enforcement_runtime_control(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    use_cache: bool = True,
) -> tuple[dict[str, Any], str]:
    """Return one authoritative request snapshot, failing enabled on faults."""

    try:
        return read_authoritative_runtime_control(
            path=path,
            home_dir=home_dir,
            use_cache=use_cache,
        )
    except (RuntimeControlError, OSError, UnicodeError, ValueError):
        return (
            {
                **_default_document(),
                "source": "fail-enabled",
            },
            "fail-enabled",
        )


def read_bound_enforcement_runtime_control(
    path: str | Path,
) -> tuple[dict[str, Any], str]:
    """Read an installer-bound control identity with restricted-host recovery."""

    try:
        if not Path(path).is_absolute():
            raise RuntimeControlValidationError("bound runtime control path must be absolute")
        target = _absolute_path(path)
        expected_suffix = Path(".agency-runtime") / "run" / "control.json"
        if target.parts[-3:] != expected_suffix.parts:
            raise RuntimeControlValidationError("bound runtime control path is not canonical")
        return read_authoritative_runtime_control(path=target, use_cache=False)
    except RuntimeControlSecurityError:
        try:
            if not current_process_token_is_restricted(is_windows=os.name == "nt"):
                raise RuntimeControlSecurityError("bound runtime control broker is unavailable")
            from agency_runtime.core.dashboard_runtime import dashboard_api_request

            response = dashboard_api_request(
                "/api/runtime",
                timeout=_DASHBOARD_BROKER_TIMEOUT_SECONDS,
            )
            if not isinstance(response, Mapping) or set(response) != {"master"}:
                raise ValueError("dashboard master response shape is invalid")
            return validate_runtime_control_document(response.get("master")), "dashboard"
        except (OSError, RuntimeControlError, UnicodeError, ValueError):
            pass
    except (OSError, RuntimeControlError, UnicodeError, ValueError):
        pass
    return ({**_default_document(), "source": "fail-enabled"}, "fail-enabled")


def master_enabled(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> bool:
    """Return the enforcement state, defaulting safely to enabled on any fault."""

    document, _transport = read_enforcement_runtime_control(
        path=path,
        home_dir=home_dir,
    )
    return bool(document["enabled"])


def _validate_lock_timeout(timeout: float) -> float:
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or not 0 <= float(timeout) <= MAX_LOCK_TIMEOUT_SECONDS
    ):
        raise RuntimeControlValidationError(
            "runtime control lock timeout must be finite and between 0 and 300 seconds"
        )
    return float(timeout)


def _secure_open_lock(
    lock_path: Path,
    directory_snapshot: tuple[tuple[Path, os.stat_result], ...],
) -> tuple[Any, bool]:
    flags = os.O_RDWR | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    created = False
    try:
        descriptor = os.open(lock_path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
    except FileExistsError:
        try:
            before = os.lstat(lock_path)
        except OSError as exc:
            raise RuntimeControlSecurityError(
                "runtime control lock could not be inspected"
            ) from exc
        _validate_regular_private_file(lock_path, before)
        try:
            descriptor = os.open(lock_path, flags)
        except OSError as exc:
            raise RuntimeControlSecurityError(
                "runtime control lock could not be opened safely"
            ) from exc
    except OSError as exc:
        raise RuntimeControlSecurityError(
            "runtime control lock could not be created safely"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        current = os.lstat(lock_path)
        if not _same_file(opened, current):
            raise RuntimeControlSecurityError("runtime control lock changed during open")
        if created:
            if os.name == "nt":
                if not restrict_windows_acl(lock_path, is_windows=True):
                    raise RuntimeControlSecurityError(
                        "runtime control lock ACL could not be restricted"
                    )
            else:
                os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
        current = os.lstat(lock_path)
        _validate_regular_private_file(lock_path, current)
        if not _same_file(opened, current):
            raise RuntimeControlSecurityError("runtime control lock changed during open")
        _validate_directory_snapshot(directory_snapshot)
        return os.fdopen(descriptor, "r+b"), created
    except Exception:
        os.close(descriptor)
        if created:
            with suppress(OSError):
                lock_path.unlink()
        raise


@contextmanager
def _control_lock(
    target: Path, *, timeout: float
) -> Iterator[tuple[tuple[Path, os.stat_result], ...]]:
    deadline_seconds = _validate_lock_timeout(timeout)
    directory_snapshot = _prepare_parent(target)
    lock_path = target.with_name(f".{target.name}.lock")
    handle, _created = _secure_open_lock(lock_path, directory_snapshot)
    try:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        deadline = time.monotonic() + deadline_seconds
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeControlBusyError(
                        "runtime control is busy; retry the operation"
                    ) from exc
                time.sleep(0.025)
                continue
            current = os.lstat(lock_path)
            _validate_regular_private_file(lock_path, current)
            if not _same_file(os.fstat(handle.fileno()), current):
                raise RuntimeControlSecurityError("runtime control lock changed before acquisition")
            _validate_directory_snapshot(directory_snapshot)
            break
        try:
            yield directory_snapshot
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _serialize_document(document: Mapping[str, Any]) -> bytes:
    payload = (
        json.dumps(dict(document), ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(payload) > MAX_RUNTIME_CONTROL_BYTES:
        raise RuntimeControlValidationError("runtime control document exceeds the 4 KiB limit")
    return payload


def _replace_atomically(source: Path, target: Path) -> None:
    if os.name != "nt":
        os.replace(source, target)
        return
    for delay in _WINDOWS_REPLACE_DELAYS:
        try:
            os.replace(source, target)
        except PermissionError:
            time.sleep(delay)
        else:
            return
    os.replace(source, target)


def _fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0))
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_document(
    target: Path,
    document: Mapping[str, Any],
    directory_snapshot: tuple[tuple[Path, os.stat_result], ...],
) -> None:
    payload = _serialize_document(document)
    temporary = target.with_name(f".{target.name}.{secrets.token_hex(16)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    descriptor = -1
    temporary_identity: os.stat_result | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        temporary_identity = os.fstat(descriptor)
        current = os.lstat(temporary)
        if not _same_file(temporary_identity, current):
            raise RuntimeControlSecurityError(
                "runtime control temporary file changed during creation"
            )
        if os.name == "nt":
            try:
                restricted = restrict_windows_acl(temporary, is_windows=True)
            except WindowsACLSafetyError as exc:
                raise RuntimeControlSecurityError(str(exc)) from exc
            if not restricted:
                raise RuntimeControlSecurityError(
                    "runtime control temporary file ACL could not be restricted"
                )
        else:
            os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
        _validate_regular_private_file(temporary, os.lstat(temporary))
        _validate_directory_snapshot(directory_snapshot)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("runtime control write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        written_identity = os.fstat(descriptor)
        current = os.lstat(temporary)
        if not _same_file(temporary_identity, written_identity) or not _same_file(
            temporary_identity, current
        ):
            raise RuntimeControlSecurityError("runtime control temporary file changed during write")
        _validate_regular_private_file(temporary, current)
        _validate_directory_snapshot(directory_snapshot)
        try:
            existing = os.lstat(target)
        except FileNotFoundError:
            pass
        else:
            _validate_regular_private_file(target, existing)
        os.close(descriptor)
        descriptor = -1
        _replace_atomically(temporary, target)
        _fsync_parent(target.parent)
        _validate_directory_snapshot(directory_snapshot)
        published = os.lstat(target)
        if temporary_identity is None or not _same_file(temporary_identity, published):
            raise RuntimeControlSecurityError(
                "runtime control file changed during atomic publication"
            )
        _validate_regular_private_file(target, published)
    except RuntimeControlError:
        raise
    except OSError as exc:
        raise RuntimeControlSecurityError(
            "runtime control document could not be published durably"
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        with suppress(OSError):
            temporary.unlink()


def _timestamp(now: datetime | None) -> str:
    current = datetime.now(timezone.utc) if now is None else now
    if not isinstance(current, datetime) or current.tzinfo is None or current.utcoffset() is None:
        raise RuntimeControlValidationError("runtime control update time must be timezone-aware")
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def set_master_enabled(
    enabled: bool,
    *,
    expected_generation: int | None = None,
    source: str = "api",
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply an atomic compare-and-swap update to the durable master switch."""

    if not isinstance(enabled, bool):
        raise RuntimeControlValidationError("runtime control enabled value must be boolean")
    if expected_generation is not None and (
        isinstance(expected_generation, bool)
        or not isinstance(expected_generation, int)
        or not 0 <= expected_generation <= _MAX_GENERATION
    ):
        raise RuntimeControlValidationError("expected runtime control generation is invalid")
    source_value = _validate_source(source)
    target = _target_path(path=path, home_dir=home_dir)
    with _control_lock(target, timeout=timeout) as directory_snapshot:
        try:
            current = _read_existing(target, use_cache=False)
        except FileNotFoundError:
            current = _default_document()
        except RuntimeControlSecurityError:
            try:
                os.lstat(target)
            except FileNotFoundError:
                current = _default_document()
            else:
                raise
        generation = int(current["generation"])
        if expected_generation is not None and expected_generation != generation:
            raise RuntimeControlConflictError(
                f"runtime control generation changed (expected {expected_generation}, found {generation})"
            )
        if bool(current["enabled"]) is enabled:
            return dict(current)
        if generation >= _MAX_GENERATION:
            raise RuntimeControlValidationError("runtime control generation is exhausted")
        updated = _validate_document(
            {
                "schema_version": RUNTIME_CONTROL_SCHEMA_VERSION,
                "enabled": enabled,
                "generation": generation + 1,
                "updated_at": _timestamp(now),
                "source": source_value,
            }
        )
        _publish_document(target, updated, directory_snapshot)
        postcondition = _read_existing(target, use_cache=False)
        if postcondition != updated:
            raise RuntimeControlSecurityError(
                "runtime control publication did not satisfy its postcondition"
            )
        return postcondition


def ensure_runtime_control_materialized(
    *,
    source: str = "install",
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create the enabled generation-zero document without changing existing state."""

    source_value = _validate_source(source)
    target = _target_path(path=path, home_dir=home_dir)
    with _control_lock(target, timeout=timeout) as directory_snapshot:
        try:
            return _read_existing(target, use_cache=False)
        except FileNotFoundError:
            pass
        except RuntimeControlSecurityError:
            try:
                os.lstat(target)
            except FileNotFoundError:
                pass
            else:
                raise
        document = _validate_document(
            {
                "schema_version": RUNTIME_CONTROL_SCHEMA_VERSION,
                "enabled": True,
                "generation": 0,
                "updated_at": _timestamp(now),
                "source": source_value,
            }
        )
        _publish_document(target, document, directory_snapshot)
        postcondition = _read_existing(target, use_cache=False)
        if postcondition != document:
            raise RuntimeControlSecurityError(
                "runtime control materialization did not satisfy its postcondition"
            )
        return postcondition


__all__ = [
    "DEFAULT_LOCK_TIMEOUT_SECONDS",
    "MAX_RUNTIME_CONTROL_BYTES",
    "RUNTIME_CONTROL_SCHEMA_VERSION",
    "RuntimeControlBrokerError",
    "RuntimeControlBusyError",
    "RuntimeControlConflictError",
    "RuntimeControlError",
    "RuntimeControlSecurityError",
    "RuntimeControlSnapshot",
    "RuntimeControlValidationError",
    "clear_runtime_control_cache",
    "ensure_runtime_control_materialized",
    "master_enabled",
    "read_authoritative_runtime_control",
    "read_bound_enforcement_runtime_control",
    "read_effective_runtime_control",
    "read_effective_runtime_control_snapshot",
    "read_enforcement_runtime_control",
    "read_runtime_control",
    "read_runtime_control_snapshot",
    "runtime_control_path",
    "set_master_enabled",
    "validate_runtime_control_document",
]
