"""Ownership manifest, private-file, and transaction-lock primitives."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import tempfile
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any

from agency_runtime import __version__ as PACKAGE_VERSION
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.dashboard_service_core import (
    MANIFEST_SCHEMA_VERSION,
    OWNER_ID,
    SERVICE_ID,
    _Context,
)

_SERVICE_LOCK_TIMEOUT_SECONDS = 5.0
_MAX_LOCK_TIMEOUT_SECONDS = 300.0
_MAX_MANIFEST_BYTES = 64 * 1024
_MAX_SERVICE_FILE_BYTES = 256 * 1024
_WINDOWS_REPARSE_POINT = 0x400


def _runtime_fingerprint(ctx: _Context) -> str:
    payload = json.dumps(
        {
            "package_version": PACKAGE_VERSION,
            "python_executable": str(ctx.python_executable),
            "worker_argv": list(ctx.worker_argv),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _manifest_value(ctx: _Context) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "owner": OWNER_ID,
        "service": SERVICE_ID,
        "platform": ctx.platform,
        "manager": ctx.manager,
        "registration": ctx.registration,
        "worker_argv": list(ctx.worker_argv),
        "config_path": str(ctx.config_path),
        "package_version": PACKAGE_VERSION,
        "runtime_fingerprint": _runtime_fingerprint(ctx),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }


def _path_present(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _link_like(file_stat: os.stat_result) -> bool:
    attributes = int(getattr(file_stat, "st_file_attributes", 0) or 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & _WINDOWS_REPARSE_POINT)


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return bool(
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and left.st_mode == right.st_mode
    )


def _read_bounded_file(path: Path, *, limit: int, label: str) -> bytes:
    before = os.lstat(path)
    if _link_like(before) or not stat.S_ISREG(before.st_mode):
        raise OSError(f"{label} must be a regular file, not a link or special file")
    if before.st_size > limit:
        raise OSError(f"{label} exceeds the size limit")
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not _same_file(before, opened) or not stat.S_ISREG(opened.st_mode):
            raise OSError(f"{label} changed while it was opened")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            raw = stream.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > limit:
        raise OSError(f"{label} exceeds the size limit")
    return raw


def _read_service_file(path: Path) -> bytes:
    return _read_bounded_file(path, limit=_MAX_SERVICE_FILE_BYTES, label="service registration")


def _decode_service_file(raw: bytes) -> str:
    """Decode a unit while matching ``Path.read_text`` newline semantics."""

    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _file_matches(path: Path, expected: bytes | None) -> bool:
    if expected is None:
        return not _path_present(path)
    try:
        return (
            _read_bounded_file(
                path,
                limit=max(_MAX_SERVICE_FILE_BYTES, len(expected)),
                label="dashboard service file",
            )
            == expected
        )
    except (FileNotFoundError, OSError):
        return False


def _read_manifest_bytes(ctx: _Context) -> bytes | None:
    try:
        _assert_real_directory_chain(ctx.manifest_path.parent, anchor=ctx.home)
        return _read_bounded_file(
            ctx.manifest_path,
            limit=_MAX_MANIFEST_BYTES,
            label="dashboard service ownership manifest",
        )
    except FileNotFoundError:
        return None


def _read_manifest(ctx: _Context) -> dict[str, Any] | None:
    try:
        raw = _read_manifest_bytes(ctx)
        if raw is None:
            return None
        value = safe_load_bounded_json(raw)
    except (BoundedJSONError, OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _manifest_owned(ctx: _Context, value: Mapping[str, Any] | None = None) -> bool:
    candidate = value if value is not None else _read_manifest(ctx)
    schema_version = candidate.get("schema_version") if candidate else None
    return bool(
        candidate
        and isinstance(schema_version, int)
        and not isinstance(schema_version, bool)
        and schema_version == MANIFEST_SCHEMA_VERSION
        and candidate.get("owner") == OWNER_ID
        and candidate.get("service") == SERVICE_ID
        and candidate.get("platform") == ctx.platform
        and candidate.get("manager") == ctx.manager
        and candidate.get("registration") == ctx.registration
    )


def _manifest_current(ctx: _Context, value: Mapping[str, Any] | None = None) -> bool:
    candidate = value if value is not None else _read_manifest(ctx)
    return bool(
        _manifest_owned(ctx, candidate)
        and candidate is not None
        and candidate.get("worker_argv") == list(ctx.worker_argv)
        and candidate.get("config_path") == str(ctx.config_path)
        and candidate.get("package_version") == PACKAGE_VERSION
        and candidate.get("runtime_fingerprint") == _runtime_fingerprint(ctx)
    )


def _assert_replaceable(path: Path, *, label: str) -> None:
    try:
        current = os.lstat(path)
    except FileNotFoundError:
        return
    if _link_like(current) or not stat.S_ISREG(current.st_mode):
        raise OSError(f"{label} must be a regular file, not a link or special file")


def _assert_real_directory_chain(path: Path, *, anchor: Path) -> None:
    try:
        relative = path.relative_to(anchor)
    except ValueError as exc:
        raise OSError("dashboard service state escaped its home directory") from exc
    current = anchor
    for part in relative.parts:
        current /= part
        try:
            current_stat = os.lstat(current)
        except FileNotFoundError:
            return
        if _link_like(current_stat) or not stat.S_ISDIR(current_stat.st_mode):
            raise OSError("dashboard service state directories must not be links or special files")


def _prepare_private_parent(path: Path, *, trusted_root: Path | None = None) -> None:
    if trusted_root is not None:
        _assert_real_directory_chain(path.parent, anchor=trusted_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if trusted_root is not None:
        _assert_real_directory_chain(path.parent, anchor=trusted_root)
    parent = os.lstat(path.parent)
    if _link_like(parent) or not stat.S_ISDIR(parent.st_mode):
        raise OSError("dashboard service state directory must be a real directory")
    if os.name != "nt":
        path.parent.chmod(0o700)


def _sync_parent(path: Path) -> None:
    """Persist directory-entry changes on Linux after replace or unlink."""

    if os.name == "nt":
        return
    flags = os.O_RDONLY | int(getattr(os, "O_DIRECTORY", 0))
    descriptor = os.open(path.parent, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write(
    path: Path,
    content: str,
    *,
    mode: int = 0o600,
    trusted_root: Path | None = None,
) -> None:
    _prepare_private_parent(path, trusted_root=trusted_root)
    _assert_replaceable(path, label="dashboard service file")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = Path(temporary_name)
    handle = descriptor
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(handle, mode)
        restrict_private_file(temporary)
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            handle = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        _assert_replaceable(path, label="dashboard service file")
        os.replace(temporary, path)
        _sync_parent(path)
        restrict_private_file(path)
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


def _open_lock(path: Path) -> Any:
    flags = os.O_RDWR | os.O_CREAT | int(getattr(os, "O_BINARY", 0))
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        path_stat = os.lstat(path)
        handle_stat = os.fstat(descriptor)
        if (
            _link_like(path_stat)
            or not stat.S_ISREG(path_stat.st_mode)
            or not _same_file(path_stat, handle_stat)
        ):
            raise OSError("dashboard service lock must be a regular file")
        return os.fdopen(descriptor, "r+b")
    except Exception:
        os.close(descriptor)
        raise


@contextmanager
def _service_lock(
    ctx: _Context, *, timeout: float = _SERVICE_LOCK_TIMEOUT_SECONDS
) -> Iterator[None]:
    """Serialize ownership checks and mutations without following lock links."""

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or float(timeout) < 0
        or float(timeout) > _MAX_LOCK_TIMEOUT_SECONDS
    ):
        raise ValueError("service lock timeout must be finite and between 0 and 300 seconds")
    _prepare_private_parent(ctx.manifest_path, trusted_root=ctx.home)
    lock_path = ctx.manifest_path.with_name(".dashboard-service.lock")
    handle = _open_lock(lock_path)
    locked = False
    try:
        restrict_private_file(lock_path)
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        restrict_private_file(lock_path)
        deadline = time.monotonic() + float(timeout)
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError("dashboard service is busy; retry the operation") from exc
                time.sleep(0.025)
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _safe_unlink(path: Path, *, missing_ok: bool = False) -> bool:
    try:
        current = os.lstat(path)
    except FileNotFoundError:
        if missing_ok:
            return False
        raise
    if _link_like(current) or not stat.S_ISREG(current.st_mode):
        raise OSError("refusing to remove a linked or special dashboard service file")
    path.unlink()
    return True


def _restore_file(path: Path, prior: bytes | None) -> None:
    if prior is None:
        _safe_unlink(path, missing_ok=True)
        return
    _prepare_private_parent(path)
    _assert_replaceable(path, label="dashboard service file")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temporary = Path(temporary_name)
    handle = descriptor
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(handle, 0o600)
        restrict_private_file(temporary)
        with os.fdopen(handle, "wb") as stream:
            handle = -1
            stream.write(prior)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        _assert_replaceable(path, label="dashboard service file")
        os.replace(temporary, path)
        _sync_parent(path)
        restrict_private_file(path)
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


def _write_manifest(ctx: _Context) -> bool:
    current = _read_manifest(ctx)
    if _path_present(ctx.manifest_path) and not _manifest_owned(ctx, current):
        raise RuntimeError("refusing to replace an invalid dashboard service ownership manifest")
    if _manifest_current(ctx, current):
        return False
    _atomic_write(
        ctx.manifest_path,
        json.dumps(_manifest_value(ctx), indent=2) + "\n",
        trusted_root=ctx.home,
    )
    return True


__all__ = [
    "_atomic_write",
    "_decode_service_file",
    "_file_matches",
    "_manifest_current",
    "_manifest_owned",
    "_path_present",
    "_prepare_private_parent",
    "_read_manifest",
    "_read_manifest_bytes",
    "_read_service_file",
    "_restore_file",
    "_safe_unlink",
    "_service_lock",
    "_sync_parent",
    "_write_manifest",
]
