"""Codex-readable, DPAPI-protected dashboard broker discovery on Windows."""

from __future__ import annotations

import base64
import ctypes
import hmac
import json
import os
import stat
import tempfile
import uuid
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import FileSizeLimitError, read_bounded_regular_file
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _link_like,
)
from agency_runtime.core.store.security import storage_parent_is_trusted
from agency_runtime.core.windows_acl import current_process_token_is_restricted

BROKER_DESCRIPTOR_SCHEMA_VERSION = 1
_MAX_DESCRIPTOR_BYTES = 16 * 1024
_MAX_PROTECTED_TOKEN_BYTES = 8 * 1024
_DPAPI_ENTROPY = b"agency-runtime/dashboard-broker/v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob(value: bytes) -> tuple[_DataBlob, Any]:
    buffer = ctypes.create_string_buffer(value)
    pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    return _DataBlob(len(value), pointer), buffer


def _windows_dpapi(value: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise OSError("Windows DPAPI is unavailable on this platform")
    from ctypes import wintypes

    crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    operation = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    operation.argtypes = (
        [
            ctypes.POINTER(_DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        if protect
        else [
            ctypes.POINTER(_DataBlob),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
    )
    operation.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    source, source_buffer = _blob(value)
    entropy, entropy_buffer = _blob(_DPAPI_ENTROPY)
    destination = _DataBlob()
    description = wintypes.LPWSTR()
    description_argument: Any = None if protect else ctypes.byref(description)
    try:
        if not operation(
            ctypes.byref(source),
            None if protect else description_argument,
            ctypes.byref(entropy),
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(destination),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        # Keep input buffers alive through the native call.
        _ = source_buffer, entropy_buffer
        if destination.pbData:
            kernel32.LocalFree(destination.pbData)
        if description:
            kernel32.LocalFree(description)


def _protect_token(token: str) -> str:
    protected = _windows_dpapi(token.encode("utf-8"), protect=True)
    return base64.b64encode(protected).decode("ascii")


def _unprotect_token(value: str) -> str:
    try:
        protected = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("dashboard broker credential is invalid") from exc
    if not protected or len(protected) > _MAX_PROTECTED_TOKEN_BYTES:
        raise ValueError("dashboard broker credential is invalid")
    try:
        token = _windows_dpapi(protected, protect=False).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("dashboard broker credential could not be decrypted") from exc
    return token


def codex_dashboard_broker_path(*, home_dir: str | Path | None = None) -> Path:
    home = Path(home_dir).expanduser() if home_dir is not None else Path.home()
    return Path(os.path.abspath(home / ".codex" / "agency-runtime" / "dashboard-broker.json"))


def _real_directory(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(metadata.st_mode) and not _link_like(metadata)


def _prepare_parent(target: Path) -> None:
    codex_root = target.parent.parent
    if not _real_directory(codex_root) or not storage_parent_is_trusted(
        codex_root,
        is_windows=True,
    ):
        raise PermissionError("Codex broker root is not trusted")
    with suppress(FileExistsError):
        os.mkdir(target.parent)
    if not _real_directory(target.parent) or not storage_parent_is_trusted(
        target.parent,
        is_windows=True,
    ):
        raise PermissionError("Codex broker directory is not trusted")


def _regular_file(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and not _link_like(metadata)
        and int(getattr(metadata, "st_nlink", 1) or 0) == 1
    )


def _write_atomic(target: Path, value: Mapping[str, Any]) -> None:
    _prepare_parent(target)
    if target.exists() and not _regular_file(target):
        raise PermissionError("Codex broker descriptor is not replaceable")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        if not _regular_file(temporary):
            raise PermissionError("Codex broker temporary descriptor is unsafe")
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = -1
            json.dump(value, stream, allow_nan=False, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if not _regular_file(temporary):
            raise PermissionError("Codex broker temporary descriptor changed")
        if target.exists() and not _regular_file(target):
            raise PermissionError("Codex broker descriptor changed before publication")
        os.replace(temporary, target)
        if not _regular_file(target):
            raise PermissionError("Codex broker descriptor publication failed")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _validate_public_descriptor(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "audience",
        "pid",
        "port",
        "protected_token",
        "schema_version",
        "started_at",
    }:
        raise ValueError("dashboard broker descriptor is invalid")
    pid = value.get("pid")
    port = value.get("port")
    protected = value.get("protected_token")
    started_at = value.get("started_at")
    if value.get("schema_version") != BROKER_DESCRIPTOR_SCHEMA_VERSION:
        raise ValueError("dashboard broker descriptor version is unsupported")
    if value.get("audience") != "codex-restricted-windows":
        raise ValueError("dashboard broker descriptor audience is invalid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
        raise ValueError("dashboard broker descriptor PID is invalid")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("dashboard broker descriptor port is invalid")
    if not isinstance(protected, str) or not 32 <= len(protected) <= _MAX_PROTECTED_TOKEN_BYTES:
        raise ValueError("dashboard broker descriptor credential is invalid")
    if not isinstance(started_at, str) or not started_at:
        raise ValueError("dashboard broker descriptor timestamp is invalid")
    return {
        "schema_version": BROKER_DESCRIPTOR_SCHEMA_VERSION,
        "audience": "codex-restricted-windows",
        "pid": pid,
        "port": port,
        "protected_token": protected,
        "started_at": started_at,
    }


def _token_is_valid(token: str) -> bool:
    return bool(32 <= len(token) <= 512 and all(33 <= ord(character) != 127 for character in token))


def _attested_codex_client(environment: Mapping[str, str]) -> bool:
    if environment.get("CODEX_SHELL", "").strip() != "1":
        return False
    thread_id = environment.get("CODEX_THREAD_ID", "").strip()
    try:
        return thread_id == str(uuid.UUID(thread_id)) and current_process_token_is_restricted()
    except (ValueError, OSError):
        return False


def write_codex_dashboard_broker(
    *,
    token: str,
    port: int,
    pid: int,
    started_at: str,
    home_dir: str | Path | None = None,
    is_windows: bool | None = None,
    protector: Callable[[str], str] | None = None,
) -> Path | None:
    """Publish a host-scoped encrypted credential without exposing the owner token."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return None
    if not _token_is_valid(token):
        raise ValueError("dashboard broker token is invalid")
    protected = (protector or _protect_token)(token)
    value = _validate_public_descriptor(
        {
            "schema_version": BROKER_DESCRIPTOR_SCHEMA_VERSION,
            "audience": "codex-restricted-windows",
            "pid": pid,
            "port": port,
            "protected_token": protected,
            "started_at": started_at,
        }
    )
    target = codex_dashboard_broker_path(home_dir=home_dir)
    _write_atomic(target, value)
    return target


def read_codex_dashboard_broker(
    *,
    home_dir: str | Path | None = None,
    environment: Mapping[str, str] | None = None,
    require_attestation: bool = True,
    is_windows: bool | None = None,
    unprotector: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Return a standard private descriptor only to an attested Codex client."""

    windows = os.name == "nt" if is_windows is None else is_windows
    source = os.environ if environment is None else environment
    if not windows or (require_attestation and not _attested_codex_client(source)):
        raise ValueError("Codex dashboard brokerage is unavailable")
    target = codex_dashboard_broker_path(home_dir=home_dir)
    try:
        if not storage_parent_is_trusted(target.parent, is_windows=True):
            raise PermissionError("Codex broker directory is not trusted")
        raw = read_bounded_regular_file(
            target,
            limit=_MAX_DESCRIPTOR_BYTES,
            label="dashboard broker descriptor",
        )
        value = _validate_public_descriptor(safe_load_bounded_json(raw))
    except FileNotFoundError as exc:
        raise ValueError("dashboard broker descriptor is unavailable") from exc
    except (BoundedJSONError, FileSizeLimitError, OSError, PermissionError) as exc:
        raise ValueError("dashboard broker descriptor could not be read safely") from exc
    token = (unprotector or _unprotect_token)(value["protected_token"])
    if not _token_is_valid(token):
        raise ValueError("dashboard broker token is invalid")
    return {
        "schema_version": 1,
        "pid": value["pid"],
        "port": value["port"],
        "token": token,
        "started_at": value["started_at"],
    }


def remove_codex_dashboard_broker(
    *,
    token: str,
    pid: int,
    home_dir: str | Path | None = None,
) -> bool:
    """Remove only the bridge descriptor still bound to this worker generation."""

    target = codex_dashboard_broker_path(home_dir=home_dir)
    try:
        before = os.lstat(target)
        current = read_codex_dashboard_broker(
            home_dir=home_dir,
            require_attestation=False,
        )
        after = os.lstat(target)
        if (
            current["pid"] != pid
            or not hmac.compare_digest(current["token"], token)
            or before.st_dev != after.st_dev
            or before.st_ino != after.st_ino
        ):
            return False
        target.unlink()
        return True
    except (OSError, ValueError):
        return False


__all__ = [
    "BROKER_DESCRIPTOR_SCHEMA_VERSION",
    "codex_dashboard_broker_path",
    "read_codex_dashboard_broker",
    "remove_codex_dashboard_broker",
    "write_codex_dashboard_broker",
]
