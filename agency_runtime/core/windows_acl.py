"""Access-preserving owner-only Windows DACL enforcement."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from pathlib import Path


class WindowsACLSafetyError(PermissionError):
    """Raised before a DACL write when process-token safety is unknown."""


class RestrictedWindowsTokenError(WindowsACLSafetyError):
    """Raised when an owner-only DACL could lock out the current process."""


class WindowsTokenProbeError(WindowsACLSafetyError):
    """Raised when the current process token cannot be inspected safely."""


TokenRestrictionProbe = Callable[[], bool]
ACLApplier = Callable[..., bool]
ACLPrivacyProbe = Callable[..., bool]

_RESTRICTED_TOKEN_MESSAGE = (
    "owner-only Windows ACL cannot be changed from a restricted process token"
)
_TOKEN_PROBE_MESSAGE = (
    "owner-only Windows ACL safety check could not inspect the current process token"
)

_OWNER_ONLY_SDDL = re.compile(
    r"^O:(?P<owner>S-[0-9-]+)(?:G:[^D]*)?D:(?P<control>[A-Z]*)(?P<aces>.*)$"
)


def current_process_token_is_restricted(
    *,
    is_windows: bool | None = None,
) -> bool:
    """Return ``IsTokenRestricted`` for the current process token.

    Opening the token requires query access only. Failure is distinct from an
    unrestricted token so callers can refuse to mutate the DACL.
    """

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        open_process_token = advapi32.OpenProcessToken
        open_process_token.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        open_process_token.restype = wintypes.BOOL
        is_token_restricted = advapi32.IsTokenRestricted
        is_token_restricted.argtypes = [wintypes.HANDLE]
        is_token_restricted.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        token = wintypes.HANDLE()
        if not open_process_token(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE)
        try:
            return bool(is_token_restricted(token))
        finally:
            kernel32.CloseHandle(token)
    except WindowsACLSafetyError:
        raise
    except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
        raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE) from exc


def _apply_owner_only_acl(path: Path, *, directory: bool) -> bool:
    """Apply one replacement DACL after token safety has been established."""

    try:
        import ctypes
        from ctypes import wintypes

        class TrusteeW(ctypes.Structure):
            _fields_ = [
                ("pMultipleTrustee", ctypes.c_void_p),
                ("MultipleTrusteeOperation", wintypes.DWORD),
                ("TrusteeForm", wintypes.DWORD),
                ("TrusteeType", wintypes.DWORD),
                ("ptstrName", wintypes.LPWSTR),
            ]

        class ExplicitAccessW(ctypes.Structure):
            _fields_ = [
                ("grfAccessPermissions", wintypes.DWORD),
                ("grfAccessMode", wintypes.DWORD),
                ("grfInheritance", wintypes.DWORD),
                ("Trustee", TrusteeW),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_security = advapi32.GetNamedSecurityInfoW
        get_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        get_security.restype = wintypes.DWORD
        set_entries = advapi32.SetEntriesInAclW
        set_entries.argtypes = [
            wintypes.ULONG,
            ctypes.POINTER(ExplicitAccessW),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        set_entries.restype = wintypes.DWORD
        set_security = advapi32.SetNamedSecurityInfoW
        set_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        set_security.restype = wintypes.DWORD
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        owner_sid = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        acl = ctypes.c_void_p()
        try:
            code = get_security(
                str(path),
                1,
                0x00000001,
                ctypes.byref(owner_sid),
                None,
                None,
                None,
                ctypes.byref(descriptor),
            )
            if code:
                return False
            trustee = TrusteeW(
                None,
                0,
                0,
                1,
                ctypes.cast(owner_sid, wintypes.LPWSTR),
            )
            access = ExplicitAccessW(
                0x001F01FF,
                2,
                0x3 if directory else 0,
                trustee,
            )
            code = set_entries(1, ctypes.byref(access), None, ctypes.byref(acl))
            if code:
                return False
            code = set_security(
                str(path),
                1,
                0x00000004 | 0x80000000,
                None,
                None,
                acl,
                None,
            )
            return code == 0
        finally:
            if acl:
                kernel32.LocalFree(acl)
            if descriptor:
                kernel32.LocalFree(descriptor)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return False


def _read_windows_sddl(path: Path) -> str:
    """Read owner and DACL SDDL without mutating the target."""

    descriptor = None
    kernel32 = None
    sddl = None
    try:
        import ctypes
        from ctypes import wintypes

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_security = advapi32.GetNamedSecurityInfoW
        get_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        get_security.restype = wintypes.DWORD
        convert = advapi32.ConvertSecurityDescriptorToStringSecurityDescriptorW
        convert.argtypes = [
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.DWORD),
        ]
        convert.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        owner_sid = ctypes.c_void_p()
        dacl = ctypes.c_void_p()
        descriptor = ctypes.c_void_p()
        security_information = 0x00000001 | 0x00000004
        code = get_security(
            str(path),
            1,
            security_information,
            ctypes.byref(owner_sid),
            None,
            ctypes.byref(dacl),
            None,
            ctypes.byref(descriptor),
        )
        if code or not descriptor:
            return ""
        sddl = ctypes.c_void_p()
        length = wintypes.DWORD()
        if not convert(
            descriptor,
            1,
            security_information,
            ctypes.byref(sddl),
            ctypes.byref(length),
        ):
            return ""
        return ctypes.wstring_at(sddl, length.value).rstrip("\0")
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return ""
    finally:
        if kernel32 is not None and sddl:
            kernel32.LocalFree(sddl)
        if kernel32 is not None and descriptor:
            kernel32.LocalFree(descriptor)


def _owner_only_acl_is_present(path: Path, *, directory: bool) -> bool:
    """Recognize only the exact protected DACL shape written by this module."""

    match = _OWNER_ONLY_SDDL.fullmatch(_read_windows_sddl(path))
    if match is None:
        return False
    owner = match.group("owner")
    ace = match.group("aces")
    flags = "OICI" if directory else ""
    if "P" in match.group("control"):
        return ace == f"(A;{flags};FA;;;{owner})"
    inherited_flags = "OICIID" if directory else "ID"
    if ace != f"(A;{inherited_flags};FA;;;{owner})":
        return False
    return path.parent != path and _owner_only_acl_is_present(path.parent, directory=True)


def restrict_windows_acl(
    path: Path,
    *,
    directory: bool = False,
    is_windows: bool | None = None,
    token_restriction_probe: TokenRestrictionProbe | None = None,
    acl_applier: ACLApplier | None = None,
    acl_privacy_probe: ACLPrivacyProbe | None = None,
) -> bool:
    """Ensure an owner-only DACL without rewriting an already-private target."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return False
    privacy_probe = acl_privacy_probe or _owner_only_acl_is_present
    try:
        if privacy_probe(path, directory=directory):
            return True
    except Exception:
        # Inspection is an optimization only. Unknown state still follows the
        # original fail-before-mutation token gate below.
        pass
    probe = token_restriction_probe or (
        lambda: current_process_token_is_restricted(is_windows=True)
    )
    try:
        restricted = bool(probe())
    except WindowsACLSafetyError:
        raise
    except Exception as exc:
        raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE) from exc
    if restricted:
        raise RestrictedWindowsTokenError(_RESTRICTED_TOKEN_MESSAGE)
    apply_acl = acl_applier or _apply_owner_only_acl
    return bool(apply_acl(path, directory=directory))


__all__ = [
    "RestrictedWindowsTokenError",
    "WindowsACLSafetyError",
    "WindowsTokenProbeError",
    "current_process_token_is_restricted",
    "restrict_windows_acl",
]
