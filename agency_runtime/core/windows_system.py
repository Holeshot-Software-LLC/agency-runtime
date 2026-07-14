"""Trusted resolution for allowlisted Windows system executables."""

from __future__ import annotations

import ctypes
import os
import stat
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

_SYSTEM_EXECUTABLE_PATHS = {
    "powershell.exe": Path("WindowsPowerShell") / "v1.0" / "powershell.exe",
    "schtasks.exe": Path("schtasks.exe"),
}
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_WINDOWS_PLATFORM_NAMES = frozenset({"nt", "win32", "windows"})
_MAX_WINDOWS_PATH_CHARS = 32_768


def _is_windows(platform_name: str | None) -> bool:
    return str(platform_name or os.name).strip().casefold() in _WINDOWS_PLATFORM_NAMES


def _allowlisted_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or any(mark in name for mark in ("/", "\\", ":", "\x00"))
    ):
        raise ValueError("Windows system executable name is invalid")
    canonical = name.casefold()
    if canonical not in _SYSTEM_EXECUTABLE_PATHS:
        raise ValueError(f"Windows system executable is not allowlisted: {name}")
    return canonical


def _native_system_directory(*, kernel32: Any | None = None) -> Path:
    """Read the actual Windows system directory without trusting environment state."""
    library = kernel32 or ctypes.WinDLL("kernel32", use_last_error=True)
    get_directory = library.GetSystemDirectoryW
    get_directory.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
    get_directory.restype = ctypes.c_uint
    buffer = ctypes.create_unicode_buffer(_MAX_WINDOWS_PATH_CHARS)
    length = int(get_directory(buffer, len(buffer)))
    if length <= 0:
        get_last_error = getattr(ctypes, "get_last_error", lambda: 0)
        raise OSError(get_last_error(), "GetSystemDirectoryW failed")
    if length >= len(buffer):
        raise OSError("Windows system directory exceeds the supported path bound")
    return Path(buffer.value)


def _candidate_directories(
    system_directory: Path,
    environ: Mapping[str, str],
) -> tuple[Path, ...]:
    """Prefer Sysnative only for a 32-bit process on 64-bit Windows."""
    if not environ.get("PROCESSOR_ARCHITEW6432"):
        return (system_directory,)
    windows_root = system_directory.parent
    return (windows_root / "Sysnative", system_directory)


def _validated_system_file(
    path: Path,
    *,
    lstat: Callable[[str | os.PathLike[str]], os.stat_result],
) -> str | None:
    try:
        metadata = lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise OSError(f"trusted Windows system executable is unavailable: {path}") from exc
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    if not stat.S_ISREG(metadata.st_mode) or attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise OSError(f"trusted Windows system executable is unsafe: {path}")
    return str(path)


def trusted_windows_system_executable(
    name: str,
    *,
    platform_name: str | None = None,
    system_directory: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    lstat: Callable[[str | os.PathLike[str]], os.stat_result] | None = None,
) -> str:
    """Resolve an allowlisted system binary without CWD or ``PATH`` lookup."""
    canonical = _allowlisted_name(name)
    if not _is_windows(platform_name):
        return canonical

    directory = (
        Path(system_directory) if system_directory is not None else _native_system_directory()
    )
    if not directory.is_absolute():
        raise OSError("Windows system directory must be absolute")
    environment = os.environ if environ is None else environ
    stat_reader = os.lstat if lstat is None else lstat
    relative_path = _SYSTEM_EXECUTABLE_PATHS[canonical]
    for candidate_directory in _candidate_directories(directory, environment):
        candidate = candidate_directory / relative_path
        resolved = _validated_system_file(candidate, lstat=stat_reader)
        if resolved is not None:
            return resolved
    raise FileNotFoundError(f"trusted Windows system executable not found: {canonical}")


def windows_system_command(
    name: str,
    *arguments: str,
    command_runner: object | None = None,
    platform_name: str | None = None,
) -> list[str]:
    """Build one system command while preserving data-only injected runners."""
    canonical = _allowlisted_name(name)
    executable = (
        canonical
        if command_runner is not None
        else trusted_windows_system_executable(canonical, platform_name=platform_name)
    )
    return [executable, *arguments]


__all__ = ["trusted_windows_system_executable", "windows_system_command"]
