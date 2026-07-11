"""Private runtime discovery for the authenticated dashboard service."""

from __future__ import annotations

import hmac
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from agency_runtime.core.configuration import (
    ConfigurationError,
    restrict_private_file,
)


DESCRIPTOR_SCHEMA_VERSION = 1
_MAX_DESCRIPTOR_BYTES = 64 * 1024
_LOCK_TIMEOUT_SECONDS = 5.0


def dashboard_runtime_path(
    *,
    home_dir: str | Path | None = None,
) -> Path:
    """Return the current user's owner-private dashboard descriptor path."""

    home = Path(home_dir).expanduser() if home_dir is not None else Path.home()
    return home / ".agency-runtime" / "run" / "dashboard.json"


@contextmanager
def _runtime_lock(
    target: Path, *, timeout: float = _LOCK_TIMEOUT_SECONDS
) -> Iterator[None]:
    """Serialize worker publication and identity-checked removal."""

    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(target.parent, 0o700)
    lock_path = target.with_name(f".{target.name}.lock")
    handle = open(lock_path, "a+b")
    try:
        if lock_path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
        # The lock contains one sentinel byte, never credentials. Keep lock
        # availability independent from optional ACL narrowing.
        try:
            restrict_private_file(lock_path)
        except (ConfigurationError, OSError):
            pass
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "dashboard runtime descriptor is busy; retry the operation"
                    ) from exc
                time.sleep(0.025)
        try:
            yield
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


def _publish_dashboard_runtime(target: Path, descriptor: Mapping[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(target.parent, 0o700)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(handle, 0o600)
        # Windows mkstemp inherits the parent DACL. Secure the empty descriptor
        # before the rotating bearer token is ever serialized.
        restrict_private_file(temporary)
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            handle = -1
            json.dump(descriptor, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Reassert the private policy after writing and before replacement.
        restrict_private_file(temporary)
        os.replace(temporary, target)
        restrict_private_file(target)
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

    target = (
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
    with _runtime_lock(target):
        _publish_dashboard_runtime(target, descriptor)
    return descriptor


def read_dashboard_runtime(
    *,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Read and validate the descriptor without returning a public payload."""

    target = (
        Path(path) if path is not None else dashboard_runtime_path(home_dir=home_dir)
    )
    try:
        raw = target.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError("dashboard service has no runtime descriptor") from exc
    except OSError as exc:
        raise ValueError("dashboard runtime descriptor could not be read") from exc
    if len(raw) > _MAX_DESCRIPTOR_BYTES:
        raise ValueError("dashboard runtime descriptor exceeds the size limit")
    try:
        return _validate_descriptor(json.loads(raw))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("dashboard runtime descriptor is invalid") from exc


def remove_dashboard_runtime(
    *,
    token: str,
    pid: int,
    path: str | Path | None = None,
    home_dir: str | Path | None = None,
) -> bool:
    """Remove only the descriptor still owned by the exiting worker."""

    target = (
        Path(path) if path is not None else dashboard_runtime_path(home_dir=home_dir)
    )
    try:
        with _runtime_lock(target):
            current = read_dashboard_runtime(path=target)
            if current["pid"] != pid or not hmac.compare_digest(
                current["token"], token
            ):
                return False
            target.unlink()
            return True
    except (FileNotFoundError, RuntimeError, ValueError):
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
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
        return response.status == 200 and payload == {"status": "ok"}
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError):
        return False


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
    "dashboard_runtime_path",
    "dashboard_service_reachable",
    "open_dashboard_service",
    "read_dashboard_runtime",
    "remove_dashboard_runtime",
    "write_dashboard_runtime",
]
