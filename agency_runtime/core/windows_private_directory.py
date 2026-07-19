"""Handle-bound, logon-private scratch directories for restricted Windows hosts."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

from agency_runtime.core.windows_acl import (
    RestrictedWindowsTokenError,
    WindowsACLSafetyError,
    WindowsTokenProbeError,
    current_process_can_mutate_path,
    current_process_logon_sid,
    current_process_token_is_restricted,
    current_process_user_sid,
    read_windows_sddl,
    windows_directory_prevents_untrusted_writes,
)

_ERROR_ALREADY_EXISTS = 183


@dataclass(slots=True)
class WindowsDirectoryGuard:
    """Open-handle and file-ID receipt for one real Windows directory."""

    path: Path
    device: int
    inode: int
    handle: int
    _identity_reader: Callable[[int], int | None] = field(repr=False)
    _closer: Callable[[int], None] = field(repr=False)
    closed: bool = False

    def is_current(self) -> bool:
        """Return whether both the pathname and open handle retain the receipt."""

        if self.closed:
            return False
        try:
            metadata = os.lstat(self.path)
        except OSError:
            return False
        attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        return bool(
            not attributes & reparse
            and int(metadata.st_dev) == self.device
            and int(getattr(metadata, "st_ino", 0) or 0) == self.inode
            and self._identity_reader(self.handle) == self.inode
        )

    def close(self) -> None:
        """Close the native handle exactly once."""

        if self.closed:
            return
        self._closer(self.handle)
        self.closed = True


def _windows_directory_handle_identity(handle: int) -> int | None:
    """Return the filesystem file index for one open directory handle."""

    try:
        import ctypes
        from ctypes import wintypes

        class FileTime(ctypes.Structure):
            _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

        class ByHandleFileInformation(ctypes.Structure):
            _fields_ = [
                ("attributes", wintypes.DWORD),
                ("creation_time", FileTime),
                ("access_time", FileTime),
                ("write_time", FileTime),
                ("volume_serial", wintypes.DWORD),
                ("size_high", wintypes.DWORD),
                ("size_low", wintypes.DWORD),
                ("links", wintypes.DWORD),
                ("index_high", wintypes.DWORD),
                ("index_low", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_information = kernel32.GetFileInformationByHandle
        get_information.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ByHandleFileInformation),
        ]
        get_information.restype = wintypes.BOOL
        information = ByHandleFileInformation()
        if not get_information(handle, ctypes.byref(information)):
            return None
        return (int(information.index_high) << 32) | int(information.index_low)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def _close_windows_handle(handle: int) -> None:
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        close_handle(handle)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return


def open_windows_directory_guard(
    path: Path,
    *,
    is_windows: bool | None = None,
) -> WindowsDirectoryGuard | None:
    """Open a real directory and bind its pathname to its native file index."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        metadata = os.lstat(path)
        attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        inode = int(getattr(metadata, "st_ino", 0) or 0)
        if attributes & reparse or not stat.S_ISDIR(metadata.st_mode) or inode <= 0:
            return None
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        create_file.restype = wintypes.HANDLE
        handle = create_file(
            str(path),
            0x00000080,
            0x00000001 | 0x00000002,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle in (None, invalid_handle):
            return None
        guard = WindowsDirectoryGuard(
            Path(path),
            int(metadata.st_dev),
            inode,
            int(handle),
            _windows_directory_handle_identity,
            _close_windows_handle,
        )
        if guard.is_current():
            return guard
        guard.close()
        return None
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def _logon_private_sddl(user_sid: str, logon_sid: str, *, deny_delete: bool) -> str:
    deny = "(D;;SD;;;AU)" if deny_delete else ""
    return f"O:{user_sid}D:P{deny}(A;OICI;FA;;;SY)(A;OICI;FA;;;{user_sid})(A;OICI;FA;;;{logon_sid})"


def _owner_private_sddl(user_sid: str) -> str:
    """Return the protected owner-only DACL for one persistent private root."""

    return f"O:{user_sid}D:P(D;;SD;;;AU)(A;OICI;FA;;;{user_sid})"


def _set_windows_file_security(path: Path, sddl: str) -> bool:
    """Replace owner and protected DACL from one bounded in-process SDDL."""

    descriptor = None
    kernel32 = None
    try:
        import ctypes
        from ctypes import wintypes

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
        convert.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.ULONG),
        ]
        convert.restype = wintypes.BOOL
        set_security = advapi32.SetFileSecurityW
        set_security.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
        set_security.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        descriptor = ctypes.c_void_p()
        length = wintypes.ULONG()
        if not convert(sddl, 1, ctypes.byref(descriptor), ctypes.byref(length)):
            return False
        return bool(set_security(str(path), 0x00000001 | 0x00000004, descriptor))
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return False
    finally:
        if kernel32 is not None and descriptor:
            kernel32.LocalFree(descriptor)


def _create_windows_directory_with_sddl(path: Path, sddl: str) -> bool | None:
    """Create one directory atomically; return ``None`` for an exact collision."""

    descriptor = None
    kernel32 = None
    try:
        import ctypes
        from ctypes import wintypes

        class SecurityAttributes(ctypes.Structure):
            _fields_ = [
                ("length", wintypes.DWORD),
                ("descriptor", ctypes.c_void_p),
                ("inherit_handle", wintypes.BOOL),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
        convert.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.ULONG),
        ]
        convert.restype = wintypes.BOOL
        create_directory = kernel32.CreateDirectoryW
        create_directory.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(SecurityAttributes)]
        create_directory.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        descriptor = ctypes.c_void_p()
        length = wintypes.ULONG()
        if not convert(sddl, 1, ctypes.byref(descriptor), ctypes.byref(length)):
            raise WindowsACLSafetyError("private Windows scratch descriptor is invalid")
        security = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
        ctypes.set_last_error(0)
        if create_directory(str(path), ctypes.byref(security)):
            return True
        if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
            return None
        raise WindowsACLSafetyError("private Windows scratch directory could not be created")
    except WindowsACLSafetyError:
        raise
    except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
        raise WindowsACLSafetyError(
            "private Windows scratch directory could not be created"
        ) from exc
    finally:
        if kernel32 is not None and descriptor:
            kernel32.LocalFree(descriptor)


def _logon_private_acl_is_present(
    path: Path,
    user_sid: str,
    logon_sid: str,
    *,
    deny_delete: bool,
) -> bool:
    return read_windows_sddl(path) == _logon_private_sddl(
        user_sid,
        logon_sid,
        deny_delete=deny_delete,
    )


def _owner_private_acl_is_present(
    path: Path,
    user_sid: str,
) -> bool:
    return read_windows_sddl(path) == _owner_private_sddl(user_sid)


def _persistent_root_acl_is_present(path: Path, user_sid: str) -> bool:
    """Accept the exact DACL or a protected, private canonical equivalent."""

    value = read_windows_sddl(path)
    if value == _owner_private_sddl(user_sid):
        return True
    dacl_offset = value.find("D:")
    if dacl_offset < 0:
        return False
    control = value[dacl_offset + 2 :].split("(", 1)[0]
    if "P" not in control:
        return False
    return windows_directory_prevents_untrusted_writes(
        path,
        is_windows=True,
        sddl_reader=lambda _path: value,
        current_sid_reader=lambda: user_sid,
        final_parent=True,
        private_access=True,
    )


def create_or_validate_windows_owner_private_directory(
    path: Path,
    *,
    parent_guard: WindowsDirectoryGuard,
    is_windows: bool | None = None,
) -> WindowsDirectoryGuard:
    """Create or reopen one deterministic, deny-delete owner-private root.

    The DACL is attached by ``CreateDirectoryW`` instead of being repaired
    after a permissive inherited directory becomes visible. An exact existing
    root is reusable; every other collision is left untouched and rejected.
    """

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows or not parent_guard.is_current() or Path(path).parent != parent_guard.path:
        raise WindowsACLSafetyError("private Windows root parent identity is unavailable")
    user_sid = current_process_user_sid(is_windows=True)
    if not user_sid:
        raise WindowsTokenProbeError("private Windows root owner identity is unavailable")
    if current_process_token_is_restricted(is_windows=True):
        raise RestrictedWindowsTokenError(
            "owner-only Windows ACL cannot be created from a restricted process token"
        )

    sealed = _owner_private_sddl(user_sid)
    _create_windows_directory_with_sddl(path, sealed)
    guard = open_windows_directory_guard(path, is_windows=True)
    failure = "root handle unavailable"
    if guard is not None:
        if not parent_guard.is_current():
            failure = "parent identity changed before verification"
        elif not guard.is_current():
            failure = "root identity changed before verification"
        elif not _persistent_root_acl_is_present(path, user_sid):
            failure = "durable ACL receipt mismatch"
        elif not current_process_can_mutate_path(
            path,
            directory=True,
            is_windows=True,
        ):
            failure = "current token cannot use protected root"
        elif not guard.is_current():
            failure = "root identity changed after verification"
        elif not parent_guard.is_current():
            failure = "parent identity changed after verification"
        else:
            return guard
    if guard is not None:
        guard.close()

    # There is no safe path-based repair or rollback through the untrusted
    # parent. Both an existing collision and a failed fresh creation remain
    # untouched; an exact newly created object is already sealed and private.
    raise WindowsACLSafetyError(f"private Windows root identity verification failed: {failure}")


def create_windows_logon_private_directory(
    path: Path,
    *,
    parent_guard: WindowsDirectoryGuard,
    is_windows: bool | None = None,
) -> WindowsDirectoryGuard | None:
    """Atomically create and verify one deny-delete, logon-private child."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows or not parent_guard.is_current() or Path(path).parent != parent_guard.path:
        raise WindowsACLSafetyError("private Windows scratch parent identity is unavailable")
    user_sid = current_process_user_sid(is_windows=True)
    logon_sid = current_process_logon_sid(is_windows=True)
    if not user_sid or not logon_sid:
        raise WindowsTokenProbeError("private Windows scratch logon identity is unavailable")
    sddl = _logon_private_sddl(user_sid, logon_sid, deny_delete=True)
    created = _create_windows_directory_with_sddl(path, sddl)
    if created is None:
        return None
    guard = open_windows_directory_guard(path, is_windows=True)
    if (
        guard is not None
        and parent_guard.is_current()
        and guard.is_current()
        and _logon_private_acl_is_present(
            path,
            user_sid,
            logon_sid,
            deny_delete=True,
        )
    ):
        return guard
    if guard is not None:
        guard.close()
    if _logon_private_acl_is_present(path, user_sid, logon_sid, deny_delete=True):
        _set_windows_file_security(
            path,
            _logon_private_sddl(user_sid, logon_sid, deny_delete=False),
        )
        with suppress(OSError):
            os.rmdir(path)
    raise WindowsACLSafetyError("private Windows scratch identity verification failed")


def prepare_windows_logon_private_directory_cleanup(
    guard: WindowsDirectoryGuard,
) -> bool:
    """Remove the deny-delete seal only from the exact still-open identity."""

    if not guard.is_current():
        return False
    user_sid = current_process_user_sid(is_windows=True)
    logon_sid = current_process_logon_sid(is_windows=True)
    if (
        not user_sid
        or not logon_sid
        or not _logon_private_acl_is_present(
            guard.path,
            user_sid,
            logon_sid,
            deny_delete=True,
        )
    ):
        return False
    if not _set_windows_file_security(
        guard.path,
        _logon_private_sddl(user_sid, logon_sid, deny_delete=False),
    ):
        return False
    return bool(
        guard.is_current()
        and _logon_private_acl_is_present(
            guard.path,
            user_sid,
            logon_sid,
            deny_delete=False,
        )
    )


__all__ = [
    "WindowsDirectoryGuard",
    "create_or_validate_windows_owner_private_directory",
    "create_windows_logon_private_directory",
    "open_windows_directory_guard",
    "prepare_windows_logon_private_directory_cleanup",
]
