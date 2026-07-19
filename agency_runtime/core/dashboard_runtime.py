"""Private runtime discovery for the authenticated dashboard service."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import stat
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import (
    FileSizeLimitError,
    read_bounded_regular_file,
    restrict_posix_path_permissions,
)
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.configuration import (
    ConfigurationError,
    restrict_private_file,
)
from agency_runtime.core.http_safety import open_no_redirect

DESCRIPTOR_SCHEMA_VERSION = 1
_MAX_DESCRIPTOR_BYTES = 64 * 1024
_MAX_HEALTH_RESPONSE_BYTES = 4 * 1024
_MAX_CONTROL_REQUEST_BYTES = 64 * 1024
_MAX_CONTROL_RESPONSE_BYTES = 2 * 1024 * 1024
_MAX_CONTROL_RESPONSE_NODES = 20_000
_CONTROL_ENDPOINT_METHODS = {
    "/api/agents/lookup": "GET",
    "/api/agents/toggle": "POST",
    "/api/hosts": "GET",
    "/api/hosts/toggle": "POST",
    "/api/policy": "GET",
    "/api/roster": "GET",
    "/api/route": "POST",
    "/api/search": "POST",
    "/api/runtime": "GET",
    "/api/runtime/toggle": "POST",
}
_QUERY_CONTROL_ENDPOINTS = {"/api/agents/lookup", "/api/roster"}
_LOCK_TIMEOUT_SECONDS = 5.0
_MAX_LOCK_TIMEOUT_SECONDS = 300.0


def _link_like(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    left_inode = int(getattr(left, "st_ino", 0) or 0)
    right_inode = int(getattr(right, "st_ino", 0) or 0)
    return bool(
        left_inode
        and right_inode
        and int(left.st_dev) == int(right.st_dev)
        and left_inode == right_inode
    )


def _absolute_target(path: str | Path) -> Path:
    """Freeze one path spelling without dereferencing a link component."""

    return Path(os.path.abspath(Path(path).expanduser()))


def _directory_candidates(path: Path) -> tuple[Path, ...]:
    anchor = Path(path.anchor)
    parts = path.parts[1:]
    return (anchor, *(anchor.joinpath(*parts[:index]) for index in range(1, len(parts) + 1)))


def _directory_snapshot(path: Path) -> tuple[tuple[Path, os.stat_result], ...]:
    """Capture a real-directory identity chain for later race checks."""

    snapshot: list[tuple[Path, os.stat_result]] = []
    for candidate in _directory_candidates(_absolute_target(path)):
        metadata = os.lstat(candidate)
        if _link_like(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise OSError("dashboard runtime state directories must be real directories")
        snapshot.append((candidate, metadata))
    return tuple(snapshot)


def _inspect_existing_directory_chain(path: Path) -> None:
    """Reject linked existing ancestors while allowing a missing suffix."""

    for candidate in _directory_candidates(_absolute_target(path)):
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            return
        if _link_like(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise OSError("dashboard runtime state directories must be real directories")


def _validate_directory_snapshot(snapshot: tuple[tuple[Path, os.stat_result], ...]) -> None:
    for candidate, expected in snapshot:
        try:
            current = os.lstat(candidate)
        except OSError as exc:
            raise OSError("dashboard runtime state directory changed during operation") from exc
        if (
            _link_like(current)
            or not stat.S_ISDIR(current.st_mode)
            or not _same_file(expected, current)
        ):
            raise OSError("dashboard runtime state directory changed during operation")


def _prepare_runtime_parent(target: Path) -> tuple[tuple[Path, os.stat_result], ...]:
    """Create and secure the descriptor parent without following substitutions."""

    _inspect_existing_directory_chain(target.parent)
    if os.name == "nt":
        from agency_runtime.core.private_paths import ensure_private_directory

        ensure_private_directory(target.parent)
    else:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = _directory_snapshot(target.parent)
    if os.name != "nt":
        restrict_posix_path_permissions(target.parent, directory=True)
    _validate_directory_snapshot(snapshot)
    return snapshot


def _regular_lock_metadata(metadata: os.stat_result) -> bool:
    return bool(
        not _link_like(metadata)
        and stat.S_ISREG(metadata.st_mode)
        and int(getattr(metadata, "st_nlink", 1) or 0) == 1
    )


def _open_runtime_lock(
    lock_path: Path,
    directory_snapshot: tuple[tuple[Path, os.stat_result], ...],
) -> Any:
    """Open one single-link regular lock and validate it before any write."""

    try:
        before = os.lstat(lock_path)
    except FileNotFoundError:
        before = None
    if before is not None and not _regular_lock_metadata(before):
        raise OSError("dashboard runtime lock must be a regular non-link file")

    flags = os.O_CREAT | os.O_RDWR | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise OSError("dashboard runtime lock could not be opened safely") from exc
    try:
        opened = os.fstat(descriptor)
        current = os.lstat(lock_path)
        if (
            not _regular_lock_metadata(opened)
            or not _regular_lock_metadata(current)
            or not _same_file(opened, current)
            or (before is not None and not _same_file(before, opened))
        ):
            raise OSError("dashboard runtime lock changed while it was opened")
        _validate_directory_snapshot(directory_snapshot)
        if os.name == "nt" or not hasattr(os, "fchmod"):
            # The lock contains no credentials. Preserve the existing
            # best-effort Windows ACL behavior, then prove that the path still
            # names the descriptor before writing its sentinel.
            with suppress(ConfigurationError, OSError):
                restrict_private_file(lock_path)
        else:
            os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
            if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o600:
                raise OSError("dashboard runtime lock permissions are unsafe")
        current = os.lstat(lock_path)
        if not _regular_lock_metadata(current) or not _same_file(opened, current):
            raise OSError("dashboard runtime lock changed before initialization")
        _validate_directory_snapshot(directory_snapshot)
        return os.fdopen(descriptor, "r+b")
    except Exception:
        os.close(descriptor)
        raise


def _assert_replaceable_runtime_file(path: Path) -> None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return
    if _link_like(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise OSError("dashboard runtime descriptor must be a regular non-link file")


def _secure_temporary_descriptor(path: Path, descriptor: int) -> os.stat_result:
    """Secure an empty descriptor before its bearer token is serialized."""

    opened = os.fstat(descriptor)
    current = os.lstat(path)
    if (
        not _regular_lock_metadata(opened)
        or not _regular_lock_metadata(current)
        or not _same_file(opened, current)
    ):
        raise OSError("dashboard runtime temporary file changed during creation")
    if os.name == "nt" or not hasattr(os, "fchmod"):
        restrict_private_file(path)
    else:
        os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
        if stat.S_IMODE(os.fstat(descriptor).st_mode) != 0o600:
            raise OSError("dashboard runtime descriptor permissions are unsafe")
    current = os.lstat(path)
    if not _regular_lock_metadata(current) or not _same_file(opened, current):
        raise OSError("dashboard runtime temporary file changed before serialization")
    return opened


def dashboard_runtime_path(
    *,
    home_dir: str | Path | None = None,
) -> Path:
    """Return the current user's owner-private dashboard descriptor path."""

    home = Path(home_dir).expanduser() if home_dir is not None else Path.home()
    return home / ".agency-runtime" / "run" / "dashboard.json"


@contextmanager
def _runtime_lock(
    target: Path,
    *,
    timeout: float = _LOCK_TIMEOUT_SECONDS,
) -> Iterator[tuple[tuple[Path, os.stat_result], ...]]:
    """Serialize worker publication and identity-checked removal."""

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or not 0 <= float(timeout) <= _MAX_LOCK_TIMEOUT_SECONDS
    ):
        raise ValueError(
            "dashboard runtime lock timeout must be finite and between 0 and 300 seconds"
        )
    target = _absolute_target(target)
    directory_snapshot = _prepare_runtime_parent(target)
    lock_path = target.with_name(f".{target.name}.lock")
    with _open_runtime_lock(lock_path, directory_snapshot) as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
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
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "dashboard runtime descriptor is busy; retry the operation"
                    ) from exc
                time.sleep(0.025)
                continue
            current = os.lstat(lock_path)
            if not _regular_lock_metadata(current) or not _same_file(
                os.fstat(handle.fileno()), current
            ):
                raise OSError("dashboard runtime lock changed before acquisition")
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


def _validate_descriptor(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("dashboard runtime descriptor is invalid")
    allowed = {"schema_version", "pid", "port", "token", "started_at"}
    if set(value) != allowed:
        raise ValueError("dashboard runtime descriptor has an invalid schema")
    schema = value.get("schema_version")
    pid = value.get("pid")
    port = value.get("port")
    token = value.get("token")
    started_at = value.get("started_at")
    if schema != DESCRIPTOR_SCHEMA_VERSION:
        raise ValueError("dashboard runtime descriptor version is unsupported")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
        raise ValueError("dashboard runtime descriptor PID is invalid")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("dashboard runtime descriptor port is invalid")
    if (
        not isinstance(token, str)
        or not 32 <= len(token) <= 512
        or any(ord(character) < 33 or ord(character) == 127 for character in token)
    ):
        raise ValueError("dashboard runtime descriptor token is invalid")
    if not isinstance(started_at, str) or not started_at:
        raise ValueError("dashboard runtime descriptor timestamp is invalid")
    return {
        "schema_version": schema,
        "pid": pid,
        "port": port,
        "token": token,
        "started_at": started_at,
    }


def _publish_dashboard_runtime(
    target: Path,
    descriptor: Mapping[str, Any],
    *,
    expected_directory_snapshot: tuple[tuple[Path, os.stat_result], ...] | None = None,
) -> None:
    target = _absolute_target(target)
    if expected_directory_snapshot is not None:
        _validate_directory_snapshot(expected_directory_snapshot)
    directory_snapshot = _prepare_runtime_parent(target)
    if expected_directory_snapshot is not None:
        _validate_directory_snapshot(expected_directory_snapshot)
        if tuple(path for path, _metadata in expected_directory_snapshot) != tuple(
            path for path, _metadata in directory_snapshot
        ):
            raise OSError("dashboard runtime state directory identity changed after locking")
    _assert_replaceable_runtime_file(target)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    temporary_identity: os.stat_result | None = None
    try:
        _validate_directory_snapshot(directory_snapshot)
        temporary_identity = _secure_temporary_descriptor(temporary, handle)
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            handle = -1
            json.dump(descriptor, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            written = os.fstat(stream.fileno())
            if not _same_file(temporary_identity, written):
                raise OSError("dashboard runtime temporary file changed during serialization")
        _validate_directory_snapshot(directory_snapshot)
        current_temporary = os.lstat(temporary)
        if not _regular_lock_metadata(current_temporary) or not _same_file(
            temporary_identity, current_temporary
        ):
            raise OSError("dashboard runtime temporary file changed before publication")
        _assert_replaceable_runtime_file(target)
        os.replace(temporary, target)
        _validate_directory_snapshot(directory_snapshot)
        published = os.lstat(target)
        if not _regular_lock_metadata(published) or not _same_file(temporary_identity, published):
            raise OSError("dashboard runtime descriptor changed during publication")
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


def write_dashboard_runtime(
    *,
    token: str,
    port: int,
    pid: int | None = None,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Atomically publish a rotating token in an owner-only descriptor."""

    target = _absolute_target(
        Path(path) if path is not None else dashboard_runtime_path(home_dir=home_dir)
    )
    descriptor = _validate_descriptor(
        {
            "schema_version": DESCRIPTOR_SCHEMA_VERSION,
            "pid": os.getpid() if pid is None else pid,
            "port": port,
            "token": token,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    with _runtime_lock(target) as directory_snapshot:
        _publish_dashboard_runtime(
            target,
            descriptor,
            expected_directory_snapshot=directory_snapshot,
        )
    return descriptor


def read_dashboard_runtime(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Read and validate the descriptor without returning a public payload."""

    target = _absolute_target(
        Path(path) if path is not None else dashboard_runtime_path(home_dir=home_dir)
    )
    try:
        directory_snapshot = _directory_snapshot(target.parent)
        raw = read_bounded_regular_file(
            target,
            limit=_MAX_DESCRIPTOR_BYTES,
            label="dashboard runtime descriptor",
        )
        _validate_directory_snapshot(directory_snapshot)
    except FileNotFoundError as exc:
        raise ValueError("dashboard service has no runtime descriptor") from exc
    except FileSizeLimitError as exc:
        raise ValueError("dashboard runtime descriptor exceeds the size limit") from exc
    except OSError as exc:
        raise ValueError("dashboard runtime descriptor could not be read") from exc
    try:
        return _validate_descriptor(safe_load_bounded_json(raw))
    except (BoundedJSONError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("dashboard runtime descriptor is invalid") from exc


def dashboard_runtime_instance_fingerprint(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> str | None:
    """Return a non-secret identity for the currently published worker.

    The bearer token participates in the digest so a replacement process on
    the same PID and port is still a distinct generation.  The token itself is
    never returned.  Missing or invalid descriptors have no trustworthy
    generation and therefore return ``None``.
    """

    try:
        descriptor = read_dashboard_runtime(path=path, home_dir=home_dir)
    except ValueError:
        return None
    encoded = json.dumps(
        descriptor,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def remove_dashboard_runtime(
    *,
    token: str,
    pid: int,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> bool:
    """Remove only the descriptor still owned by the exiting worker."""

    target = _absolute_target(
        Path(path) if path is not None else dashboard_runtime_path(home_dir=home_dir)
    )
    try:
        with _runtime_lock(target) as directory_snapshot:
            _validate_directory_snapshot(directory_snapshot)
            descriptor_identity = os.lstat(target)
            if _link_like(descriptor_identity) or not stat.S_ISREG(descriptor_identity.st_mode):
                return False
            current = read_dashboard_runtime(path=target)
            if current["pid"] != pid or not hmac.compare_digest(current["token"], token):
                return False
            _validate_directory_snapshot(directory_snapshot)
            current_identity = os.lstat(target)
            if not _same_file(descriptor_identity, current_identity):
                return False
            target.unlink()
            return True
    except (OSError, RuntimeError, ValueError):
        # A missing, invalid, busy, or replaced descriptor is not ours to remove.
        return False


def dashboard_service_reachable(
    *,
    descriptor: Mapping[str, Any] | None = None,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    timeout: float = 1.0,
) -> bool:
    """Verify the private token against the worker's authenticated health API."""

    try:
        value = _validate_descriptor(
            descriptor
            if descriptor is not None
            else read_dashboard_runtime(path=path, home_dir=home_dir)
        )
        request = urllib.request.Request(
            f"http://127.0.0.1:{value['port']}/api/health",
            headers={"Authorization": f"Bearer {value['token']}"},
        )
        with open_no_redirect(request, timeout=timeout) as response:
            raw = response.read(_MAX_HEALTH_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_HEALTH_RESPONSE_BYTES:
                return False
            payload = safe_load_bounded_json(raw)
        return response.status == 200 and payload == {"status": "ok"}
    except (
        BoundedJSONError,
        OSError,
        ValueError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return False


def _dashboard_control_target(path: str) -> tuple[str, str]:
    """Return the exact endpoint and allowed method for one local control URL."""

    if not isinstance(path, str):
        raise ValueError("dashboard control endpoint must be a string")
    parsed_path = urllib.parse.urlsplit(path)
    canonical_path = parsed_path.path + (f"?{parsed_path.query}" if parsed_path.query else "")
    if (
        not parsed_path.path.startswith("/")
        or parsed_path.scheme
        or parsed_path.netloc
        or parsed_path.fragment
        or canonical_path != path
    ):
        raise ValueError("dashboard control endpoint is invalid")
    endpoint = parsed_path.path
    expected_method = _CONTROL_ENDPOINT_METHODS.get(endpoint)
    if expected_method is None:
        raise ValueError("unsupported dashboard control endpoint")
    if parsed_path.query and endpoint not in _QUERY_CONTROL_ENDPOINTS:
        raise ValueError("dashboard control endpoint does not accept a query")
    return endpoint, expected_method


def dashboard_api_request(
    path: str,
    *,
    method: str = "GET",
    payload: Mapping[str, Any] | None = None,
    descriptor: Mapping[str, Any] | None = None,
    home_dir: str | Path | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Call one authenticated loopback dashboard control endpoint safely."""

    _endpoint, expected_method = _dashboard_control_target(path)
    normalized_method = str(method or "").strip().upper()
    if normalized_method not in {"GET", "POST"}:
        raise ValueError("dashboard control method must be GET or POST")
    if normalized_method != expected_method:
        raise ValueError(f"dashboard control endpoint requires {expected_method}")
    if normalized_method == "GET" and payload is not None:
        raise ValueError("dashboard GET requests cannot include a payload")
    if normalized_method == "POST" and not isinstance(payload, Mapping):
        raise ValueError("dashboard POST requests require a JSON object")
    value = _validate_descriptor(
        descriptor if descriptor is not None else read_dashboard_runtime(home_dir=home_dir)
    )
    body = None
    headers = {
        "Authorization": f"Bearer {value['token']}",
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(
            dict(payload),
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(body) > _MAX_CONTROL_REQUEST_BYTES:
            raise ValueError("dashboard control request exceeds the size limit")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"http://127.0.0.1:{value['port']}{path}",
        data=body,
        headers=headers,
        method=normalized_method,
    )
    try:
        with open_no_redirect(request, timeout=timeout) as response:
            raw = response.read(_MAX_CONTROL_RESPONSE_BYTES + 1)
            if len(raw) > _MAX_CONTROL_RESPONSE_BYTES:
                raise ValueError("dashboard control response exceeds the size limit")
            if response.status != 200:
                raise ValueError("dashboard control request was rejected")
    except urllib.error.HTTPError as exc:
        raise ValueError(f"dashboard control request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ValueError("dashboard service is not reachable") from exc
    try:
        result = safe_load_bounded_json(
            raw,
            maximum_bytes=_MAX_CONTROL_RESPONSE_BYTES,
            maximum_depth=16,
            maximum_nodes=_MAX_CONTROL_RESPONSE_NODES,
        )
    except (BoundedJSONError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("dashboard control response is invalid") from exc
    if not isinstance(result, dict):
        raise ValueError("dashboard control response must be a JSON object")
    return result


def open_dashboard_service(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
    open_browser: bool = True,
) -> dict[str, Any]:
    """Open the running service without exposing its token in the result."""

    try:
        descriptor = read_dashboard_runtime(path=path, home_dir=home_dir)
    except ValueError as exc:
        return {"ok": False, "exit_code": 1, "error": str(exc)}
    if not dashboard_service_reachable(descriptor=descriptor):
        return {
            "ok": False,
            "exit_code": 1,
            "registered_runtime": True,
            "reachable": False,
            "error": "dashboard service is not reachable; inspect or restart it",
        }
    public_url = f"http://127.0.0.1:{descriptor['port']}/"
    if open_browser:
        webbrowser.open(
            f"{public_url}#token={descriptor['token']}",
            new=2,
        )
    return {
        "ok": True,
        "exit_code": 0,
        "reachable": True,
        "pid": descriptor["pid"],
        "port": descriptor["port"],
        "started_at": descriptor["started_at"],
        "url": public_url,
    }


__all__ = [
    "DESCRIPTOR_SCHEMA_VERSION",
    "dashboard_api_request",
    "dashboard_runtime_instance_fingerprint",
    "dashboard_runtime_path",
    "dashboard_service_reachable",
    "open_dashboard_service",
    "read_dashboard_runtime",
    "remove_dashboard_runtime",
    "write_dashboard_runtime",
]
