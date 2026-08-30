"""Access-preserving owner-only Windows DACL enforcement."""

from __future__ import annotations

import ctypes
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


def restricted_windows_token_cause(
    error: BaseException,
) -> RestrictedWindowsTokenError | None:
    """Find an exact restricted-token refusal through typed wrapper causes.

    Configuration and storage boundaries intentionally translate low-level ACL
    failures into their domain exception types.  Restricted-aware callers must
    still distinguish this one capability failure from ordinary permission or
    validation errors without brittle message matching.
    """

    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        identity = id(current)
        if identity in seen:
            continue
        seen.add(identity)
        if isinstance(current, RestrictedWindowsTokenError):
            return current
        pending.extend(
            nested
            for nested in (current.__cause__, current.__context__)
            if isinstance(nested, BaseException)
        )
    return None


def require_restricted_windows_token(
    error: BaseException,
) -> RestrictedWindowsTokenError:
    """Return the typed refusal or re-raise an unrelated wrapped failure."""

    restricted = restricted_windows_token_cause(error)
    if restricted is None:
        raise error
    return restricted


TokenRestrictionProbe = Callable[[], bool]
ACLApplier = Callable[..., bool]
ACLPrivacyProbe = Callable[..., bool]
TrustedSIDProbe = Callable[[], frozenset[str]]

_RESTRICTED_TOKEN_MESSAGE = (
    "owner-only Windows ACL cannot be changed from a restricted process token"
)
_TOKEN_PROBE_MESSAGE = (
    "owner-only Windows ACL safety check could not inspect the current process token"
)

_OWNER_ONLY_SDDL = re.compile(
    r"^O:(?P<owner>S-[0-9-]+)(?:G:[^D]*)?D:(?P<control>[A-Z]*)(?P<aces>.*)$"
)
_SDDL_ACE_FLAGS = re.compile(r"^(?:(?:CI|OI|NP|IO|ID|CR|TP|SA|FA))*$")
_SDDL_GUID = re.compile(
    r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$",
    re.IGNORECASE,
)
_SDDL_MUTATING_MASK = (
    0x10000000  # GENERIC_ALL
    | 0x40000000  # GENERIC_WRITE
    | 0x00010000  # DELETE
    | 0x00040000  # WRITE_DAC
    | 0x00080000  # WRITE_OWNER
    | 0x00000002  # FILE_WRITE_DATA / FILE_ADD_FILE
    | 0x00000004  # FILE_APPEND_DATA / FILE_ADD_SUBDIRECTORY
    | 0x00000010  # FILE_WRITE_EA
    | 0x00000040  # FILE_DELETE_CHILD
    | 0x00000100  # FILE_WRITE_ATTRIBUTES
)
_SDDL_MUTATING_RIGHTS = frozenset({"FA", "FW", "GA", "GW", "SD", "WD", "WO"})
_SDDL_READ_ONLY_RIGHTS = frozenset({"FR", "GR", "GX", "RC"})
_SDDL_NAMESPACE_REPLACEMENT_MASK = (
    0x10000000  # GENERIC_ALL
    | 0x00010000  # DELETE
    | 0x00040000  # WRITE_DAC
    | 0x00080000  # WRITE_OWNER
    | 0x00000040  # FILE_DELETE_CHILD
)
_SDDL_NAMESPACE_REPLACEMENT_RIGHTS = frozenset({"DT", "FA", "GA", "SD", "WD", "WO"})
_SDDL_ANCESTOR_SAFE_RIGHTS = frozenset(
    {"CC", "CR", "DC", "FR", "FW", "FX", "GR", "GW", "GX", "LC", "LO", "RC", "RP", "SW", "WP"}
)
_SDDL_DENY_TYPES = frozenset({"D", "OD", "XD"})
_SDDL_ALLOW_TYPES = frozenset({"A", "OA", "XA", "ZA"})
# Keep these tokens aligned with the public Sddl.h contract. Windows defines
# callback-object deny/audit ACE structures, but no ZD/ZU textual SDDL tokens;
# treating those invented strings as deny ACEs would accept malformed input.
_SDDL_CONDITIONAL_TYPES = frozenset({"XA", "XD", "XU", "ZA"})
_SDDL_STANDARD_TYPES = frozenset(
    {
        "A",
        "AL",
        "AU",
        "D",
        "FL",
        "ML",
        "OA",
        "OD",
        "OL",
        "OU",
        "SP",
        "TL",
    }
)
_SDDL_APPLICATION_DATA_TYPES = _SDDL_CONDITIONAL_TYPES | {"RA"}
_SDDL_TYPES = _SDDL_STANDARD_TYPES | _SDDL_APPLICATION_DATA_TYPES
_SDDL_DACL_CONTROL = re.compile(r"^(?:(?:P|AI|AR))*$")
_TRUSTED_INSTALLER_SID = "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464"
_TRUSTED_WINDOWS_OWNERS = frozenset(
    {
        "BA",  # Builtin Administrators
        "SY",  # Local System
        "S-1-5-18",
        "S-1-5-32-544",
        _TRUSTED_INSTALLER_SID,
    }
)
_TRUSTED_WINDOWS_PRINCIPALS = frozenset(
    {
        "BA",  # Builtin Administrators
        "CO",  # Creator Owner (inheritance placeholder)
        "OW",  # Owner Rights
        "SY",  # Local System
        "S-1-3-0",
        "S-1-3-4",
        "S-1-5-18",
        "S-1-5-32-544",
        _TRUSTED_INSTALLER_SID,
    }
)


def windows_system_owner_is_trusted(value: str) -> bool:
    """Classify a durable Windows system authority for compatibility.

    This predicate is not sufficient authorization for a private final root;
    those roots require exact current-user SID identity. It remains public so
    existing integrations can classify ordinary system-owned ancestors and
    executable artifacts without a breaking import.
    """

    return str(value or "") in _TRUSTED_WINDOWS_OWNERS


_BROAD_WINDOWS_SIDS = frozenset(
    {
        "S-1-1-0",  # Everyone
        "S-1-5-7",  # Anonymous
        "S-1-5-11",  # Authenticated Users
        "S-1-5-32-545",  # Builtin Users
    }
)
_WINDOWS_LOGON_SID = re.compile(r"^S-1-5-5-[0-9]+-[0-9]+$")
_WINDOWS_NUMERIC_SID = re.compile(r"^S-[0-9]+(?:-[0-9]+)+$")
_ERROR_ACCESS_DENIED = 5
_ERROR_NO_TOKEN = 1008
_SE_GROUP_ENABLED = 0x00000004
_SE_GROUP_LOGON_ID = 0xC0000000


def _open_effective_token(advapi32: object, kernel32: object, ctypes: object, wintypes: object):
    """Open the effective thread token, falling back only when none exists."""

    token = wintypes.HANDLE()
    open_thread_token = advapi32.OpenThreadToken
    open_thread_token.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.BOOL,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    open_thread_token.restype = wintypes.BOOL
    kernel32.GetCurrentThread.argtypes = []
    kernel32.GetCurrentThread.restype = wintypes.HANDLE
    ctypes.set_last_error(0)
    if open_thread_token(
        kernel32.GetCurrentThread(),
        0x0008,
        True,
        ctypes.byref(token),
    ):
        return token
    if ctypes.get_last_error() != _ERROR_NO_TOKEN:
        raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE)
    open_process_token = advapi32.OpenProcessToken
    open_process_token.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    open_process_token.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    if not open_process_token(
        kernel32.GetCurrentProcess(),
        0x0008,
        ctypes.byref(token),
    ):
        raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE)
    return token


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
        is_token_restricted = advapi32.IsTokenRestricted
        is_token_restricted.argtypes = [wintypes.HANDLE]
        is_token_restricted.restype = wintypes.BOOL
        get_token = advapi32.GetTokenInformation
        get_token.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_token.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.argtypes = []
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        token = _open_effective_token(advapi32, kernel32, ctypes, wintypes)
        try:
            ctypes.set_last_error(0)
            has_restricting_sids = bool(is_token_restricted(token))
            if not has_restricting_sids and ctypes.get_last_error() != 0:
                raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE)

            def token_dword(information_class: int) -> bool:
                value = wintypes.DWORD()
                returned = wintypes.DWORD()
                if not get_token(
                    token,
                    information_class,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                    ctypes.byref(returned),
                ):
                    raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE)
                return bool(value.value)

            # TokenHasRestrictions also catches tokens filtered by disabled
            # groups/privileges with no restricting SID list. AppContainer
            # tokens are never safe DACL writers even when both older probes
            # report a clean-looking value.
            return bool(
                has_restricting_sids
                or token_dword(21)  # TokenHasRestrictions
                or token_dword(29)  # TokenIsAppContainer
            )
        finally:
            kernel32.CloseHandle(token)
    except WindowsACLSafetyError:
        raise
    except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
        raise WindowsTokenProbeError(_TOKEN_PROBE_MESSAGE) from exc


def current_process_user_sid(*, is_windows: bool | None = None) -> str | None:
    """Return the current process token SID without invoking a shell."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class SidAndAttributes(ctypes.Structure):
            _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

        class TokenUser(ctypes.Structure):
            _fields_ = [("User", SidAndAttributes)]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_token = advapi32.GetTokenInformation
        get_token.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_token.restype = wintypes.BOOL
        convert_sid = advapi32.ConvertSidToStringSidW
        convert_sid.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        convert_sid.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]

        token = _open_effective_token(advapi32, kernel32, ctypes, wintypes)
        sid_string = wintypes.LPWSTR()
        try:
            required = wintypes.DWORD()
            get_token(token, 1, None, 0, ctypes.byref(required))
            if required.value == 0:
                return None
            buffer = ctypes.create_string_buffer(required.value)
            if not get_token(token, 1, buffer, required, ctypes.byref(required)):
                return None
            token_user = ctypes.cast(buffer, ctypes.POINTER(TokenUser)).contents
            if not convert_sid(token_user.User.Sid, ctypes.byref(sid_string)):
                return None
            return str(sid_string.value)
        finally:
            if sid_string:
                kernel32.LocalFree(sid_string)
            kernel32.CloseHandle(token)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def current_process_restricted_sids(
    *,
    is_windows: bool | None = None,
) -> frozenset[str]:
    """Return exact non-broad restricting SIDs for this process token."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return frozenset()
    try:
        import ctypes
        from ctypes import wintypes

        class SidAndAttributes(ctypes.Structure):
            _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

        class TokenGroups(ctypes.Structure):
            _fields_ = [
                ("GroupCount", wintypes.DWORD),
                ("Groups", SidAndAttributes * 1),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_token = advapi32.GetTokenInformation
        get_token.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_token.restype = wintypes.BOOL
        convert_sid = advapi32.ConvertSidToStringSidW
        convert_sid.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        convert_sid.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]

        token = _open_effective_token(advapi32, kernel32, ctypes, wintypes)

        def render_sid(pointer: int | None) -> str:
            if not pointer:
                return ""
            value = wintypes.LPWSTR()
            if not convert_sid(pointer, ctypes.byref(value)):
                return ""
            try:
                return str(value.value or "")
            finally:
                kernel32.LocalFree(value)

        observed: set[str] = set()
        try:
            for information_class in (11,):
                required = wintypes.DWORD()
                get_token(token, information_class, None, 0, ctypes.byref(required))
                if required.value == 0:
                    continue
                buffer = ctypes.create_string_buffer(required.value)
                if not get_token(
                    token,
                    information_class,
                    buffer,
                    required,
                    ctypes.byref(required),
                ):
                    continue
                groups = ctypes.cast(buffer, ctypes.POINTER(TokenGroups)).contents
                count = int(groups.GroupCount)
                if count <= 0:
                    continue
                array_type = SidAndAttributes * count
                address = ctypes.addressof(groups) + TokenGroups.Groups.offset
                entries = ctypes.cast(address, ctypes.POINTER(array_type)).contents
                observed.update(filter(None, (render_sid(entry.Sid) for entry in entries)))

        finally:
            kernel32.CloseHandle(token)
        return frozenset(observed - _BROAD_WINDOWS_SIDS)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return frozenset()


def _current_process_token_sid_entries(
    information_class: int,
    *,
    is_windows: bool | None = None,
) -> tuple[tuple[str, int], ...]:
    """Read one ``TOKEN_GROUPS`` information class without a shell helper."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return ()
    try:
        import ctypes
        from ctypes import wintypes

        class SidAndAttributes(ctypes.Structure):
            _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

        class TokenGroups(ctypes.Structure):
            _fields_ = [("GroupCount", wintypes.DWORD), ("Groups", SidAndAttributes * 1)]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_token = advapi32.GetTokenInformation
        get_token.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_token.restype = wintypes.BOOL
        convert_sid = advapi32.ConvertSidToStringSidW
        convert_sid.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        convert_sid.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]

        token = _open_effective_token(advapi32, kernel32, ctypes, wintypes)
        try:
            required = wintypes.DWORD()
            get_token(token, information_class, None, 0, ctypes.byref(required))
            if required.value == 0:
                return ()
            buffer = ctypes.create_string_buffer(required.value)
            if not get_token(
                token,
                information_class,
                buffer,
                required,
                ctypes.byref(required),
            ):
                return ()
            groups = ctypes.cast(buffer, ctypes.POINTER(TokenGroups)).contents
            count = int(groups.GroupCount)
            if count <= 0:
                return ()
            array_type = SidAndAttributes * count
            address = ctypes.addressof(groups) + TokenGroups.Groups.offset
            entries = ctypes.cast(address, ctypes.POINTER(array_type)).contents
            rendered: list[tuple[str, int]] = []
            for entry in entries:
                value = wintypes.LPWSTR()
                if not entry.Sid or not convert_sid(entry.Sid, ctypes.byref(value)):
                    return ()
                try:
                    sid = str(value.value or "")
                finally:
                    kernel32.LocalFree(value)
                if not sid:
                    return ()
                rendered.append((sid, int(entry.Attributes)))
            return tuple(rendered)
        finally:
            kernel32.CloseHandle(token)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return ()


def current_process_logon_sid(*, is_windows: bool | None = None) -> str | None:
    """Return the exact enabled logon SID present in both token access passes.

    ``TokenLogonSid`` (class 28) is authoritative. The same SID must also be an
    enabled logon group in ``TokenGroups`` and an enabled restricting SID in
    ``TokenRestrictedSids``. A regex-shaped or arbitrary restricting SID is
    never accepted as a substitute.
    """

    logon = _current_process_token_sid_entries(28, is_windows=is_windows)
    if len(logon) != 1:
        return None
    sid, attributes = logon[0]
    if attributes & (_SE_GROUP_ENABLED | _SE_GROUP_LOGON_ID) != (
        _SE_GROUP_ENABLED | _SE_GROUP_LOGON_ID
    ):
        return None
    groups = dict(_current_process_token_sid_entries(2, is_windows=is_windows))
    restricting = dict(_current_process_token_sid_entries(11, is_windows=is_windows))
    group_attributes = groups.get(sid, 0)
    restricted_attributes = restricting.get(sid, 0)
    if group_attributes & (_SE_GROUP_ENABLED | _SE_GROUP_LOGON_ID) != (
        _SE_GROUP_ENABLED | _SE_GROUP_LOGON_ID
    ):
        return None
    if not restricted_attributes & _SE_GROUP_ENABLED:
        return None
    return sid


def current_process_can_mutate_path(
    path: Path,
    *,
    directory: bool,
    is_windows: bool | None = None,
) -> bool:
    """Prove the current token can open an existing path for required writes."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return False
    try:
        import ctypes
        from ctypes import wintypes

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
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        desired_access = (
            0x00000001 | 0x00000002 | 0x00000004 | 0x00000100
            if directory
            else 0x80000000 | 0x40000000
        )
        flags = 0x02000000 if directory else 0
        handle = create_file(
            str(path),
            desired_access,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            flags,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle in (None, invalid_handle):
            return False
        kernel32.CloseHandle(handle)
        return True
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return False


def _current_process_has_requested_access(
    path: Path,
    *,
    directory: bool,
    requested_rights: tuple[int, ...],
    is_windows: bool | None = None,
) -> bool | None:
    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return None
    try:
        import ctypes
        from ctypes import wintypes

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
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        flags = 0x02000000 if directory else 0
        invalid_handle = ctypes.c_void_p(-1).value
        for desired_access in requested_rights:
            ctypes.set_last_error(0)
            handle = create_file(
                str(path),
                desired_access,
                0x00000001 | 0x00000002 | 0x00000004,
                None,
                3,
                flags,
                None,
            )
            if handle not in (None, invalid_handle):
                kernel32.CloseHandle(handle)
                return True
            if ctypes.get_last_error() != _ERROR_ACCESS_DENIED:
                return None
        return False
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def current_process_has_any_mutation_access(
    path: Path,
    *,
    directory: bool,
    is_windows: bool | None = None,
) -> bool | None:
    """Probe individual mutation rights without treating API failure as safety.

    A combined access request is not sufficient for a negative proof: Windows
    rejects the whole request when just one requested permission is absent.
    This helper therefore opens the identity once per mutation class and
    returns ``None`` when the access check itself cannot be completed.
    """

    rights = (
        0x00000002,  # FILE_WRITE_DATA / FILE_ADD_FILE
        0x00000004,  # FILE_APPEND_DATA / FILE_ADD_SUBDIRECTORY
        0x00000010,  # FILE_WRITE_EA
        0x00000100,  # FILE_WRITE_ATTRIBUTES
        0x00010000,  # DELETE
        0x00040000,  # WRITE_DAC
        0x00080000,  # WRITE_OWNER
        *((0x00000040,) if directory else ()),  # FILE_DELETE_CHILD
    )
    return _current_process_has_requested_access(
        path,
        directory=directory,
        requested_rights=rights,
        is_windows=is_windows,
    )


def current_process_has_control_forgery_access(
    path: Path,
    *,
    directory: bool,
    is_windows: bool | None = None,
) -> bool | None:
    """Return whether this token can forge state rather than only remove it.

    Deletion of the master document fails Agency on; it cannot manufacture a
    disabled state. Creation, content writes, or ACL takeover can. Keeping
    these probes separate lets a sandbox consume an integrity-protected
    owner-written control file without granting it a write capability.
    """

    return _current_process_has_requested_access(
        path,
        directory=directory,
        requested_rights=(
            0x00000002,  # FILE_WRITE_DATA / FILE_ADD_FILE
            0x00000004,  # FILE_APPEND_DATA / FILE_ADD_SUBDIRECTORY
            0x00000010,  # FILE_WRITE_EA
            0x00000100,  # FILE_WRITE_ATTRIBUTES
            0x00040000,  # WRITE_DAC
            0x00080000,  # WRITE_OWNER
        ),
        is_windows=is_windows,
    )


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


def read_windows_sddl(path: Path) -> str:
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


def windows_sddl_owner_matches_sid(
    value: str,
    expected_sid: str,
    *,
    is_windows: bool | None = None,
) -> bool:
    """Compare a captured SDDL owner with one canonical SID by binary identity.

    Windows renders well-known account owners with aliases such as ``LA`` even
    when the creating descriptor supplied the account's full SID. Comparing
    those strings would reject the same principal or tempt callers to trust a
    broader group. Resolve both through native SID parsing and use ``EqualSid``.
    """

    windows = os.name == "nt" if is_windows is None else is_windows
    if (
        not windows
        or not value
        or "\0" in value
        or _WINDOWS_NUMERIC_SID.fullmatch(expected_sid) is None
    ):
        return False
    descriptor = None
    expected = None
    kernel32 = None
    try:
        from ctypes import wintypes

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        convert_descriptor = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
        convert_descriptor.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.ULONG),
        ]
        convert_descriptor.restype = wintypes.BOOL
        convert_sid = advapi32.ConvertStringSidToSidW
        convert_sid.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
        convert_sid.restype = wintypes.BOOL
        get_owner = advapi32.GetSecurityDescriptorOwner
        get_owner.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.BOOL),
        ]
        get_owner.restype = wintypes.BOOL
        equal_sid = advapi32.EqualSid
        equal_sid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        equal_sid.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        descriptor = ctypes.c_void_p()
        length = wintypes.ULONG()
        expected = ctypes.c_void_p()
        owner = ctypes.c_void_p()
        defaulted = wintypes.BOOL()
        if (
            not convert_descriptor(value, 1, ctypes.byref(descriptor), ctypes.byref(length))
            or not descriptor
        ):
            return False
        if not convert_sid(expected_sid, ctypes.byref(expected)) or not expected:
            return False
        if not get_owner(descriptor, ctypes.byref(owner), ctypes.byref(defaulted)) or not owner:
            return False
        return bool(equal_sid(owner, expected))
    except (
        AttributeError,
        ctypes.ArgumentError,
        ImportError,
        OSError,
        TypeError,
        ValueError,
    ):
        return False
    finally:
        if kernel32 is not None and expected:
            kernel32.LocalFree(expected)
        if kernel32 is not None and descriptor:
            kernel32.LocalFree(descriptor)


def windows_restricted_host_boundary_is_trusted(path: Path) -> bool:
    """Recognize one owner-scoped host leaf with exactly one restricting SID.

    This narrow predicate is valid only after the caller verifies that every
    namespace-defining parent is owner-private. It intentionally does not
    affect the general ACL trust predicate.
    """

    try:
        value = read_windows_sddl(path)
        user_sid = current_process_user_sid(is_windows=True)
        restricting = current_process_restricted_sids(is_windows=True)
    except WindowsACLSafetyError:
        return False
    if not user_sid or _sddl_owner(value) != user_sid or "D:" not in value:
        return False
    parsed_dacl = _parse_sddl_dacl(value)
    if parsed_dacl is None:
        return False
    _control, aces = parsed_dacl
    extras: set[str] = set()
    trusted = {*_TRUSTED_WINDOWS_PRINCIPALS, user_sid}
    for encoded in aces:
        fields = _parse_sddl_ace(encoded)
        if fields is None:
            return False
        ace_type, _flags, rights, _object_guid, _inherit_guid, principal = fields
        if ace_type in _SDDL_DENY_TYPES:
            continue
        if ace_type not in _SDDL_ALLOW_TYPES or not rights:
            return False
        if principal not in trusted:
            extras.add(principal)
    return bool(
        len(extras) == 1
        and extras <= restricting
        and not extras & _BROAD_WINDOWS_SIDS
        and current_process_can_mutate_path(path, directory=True, is_windows=True)
    )


def _owner_only_acl_is_present(path: Path, *, directory: bool) -> bool:
    """Recognize only the exact protected DACL shape written by this module."""

    match = _OWNER_ONLY_SDDL.fullmatch(read_windows_sddl(path))
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


def _sddl_owner(value: str) -> str:
    if not value.startswith("O:"):
        return ""
    remainder = value[2:]
    boundaries = [index for marker in ("G:", "D:") if (index := remainder.find(marker)) >= 0]
    end = min(boundaries) if boundaries else len(remainder)
    return remainder[:end]


def _tokenize_sddl_aces(value: str) -> tuple[str, ...] | None:
    """Split a complete SDDL ACE sequence without dropping nested content.

    Conditional and resource-attribute ACEs append parenthesized application
    data to the six ordinary fields. Parentheses inside quoted string values
    are data, while all other parentheses participate in balancing. Any
    unconsumed text, unterminated quote, or malformed nesting is rejected so a
    security classifier cannot accept an access-granting ACE by omission.
    """

    if "\0" in value:
        return None
    aces: list[str] = []
    offset = 0
    while offset < len(value):
        if value[offset] != "(":
            return None
        start = offset + 1
        offset = start
        depth = 1
        quoted = False
        while offset < len(value):
            character = value[offset]
            if character == '"':
                # Windows claim strings can contain parentheses, but SDDL
                # does not use doubled quotes as an escape convention. Empty
                # strings are valid; a new quote immediately after a closing
                # quote is an ambiguous, non-native shape and fails closed.
                if not quoted and offset > 0 and value[offset - 1] == '"':
                    return None
                quoted = not quoted
            elif not quoted:
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                    if depth == 0:
                        aces.append(value[start:offset])
                        offset += 1
                        break
            offset += 1
        else:
            return None
    return tuple(aces)


def _parse_sddl_dacl(value: str) -> tuple[str, tuple[str, ...]] | None:
    """Return one complete, structurally valid DACL or fail closed."""

    dacl_offset = value.find("D:")
    if dacl_offset < 0:
        return None
    dacl = value[dacl_offset + 2 :]
    ace_offset = dacl.find("(")
    if ace_offset < 0:
        control = dacl
        encoded_aces = ""
    else:
        control = dacl[:ace_offset]
        encoded_aces = dacl[ace_offset:]
    if control == "NO_ACCESS_CONTROL" or _SDDL_DACL_CONTROL.fullmatch(control) is None:
        return None
    aces = _tokenize_sddl_aces(encoded_aces)
    if aces is None:
        return None
    return control, aces


def _parse_sddl_ace(encoded: str) -> tuple[str, str, str, str, str, str] | None:
    """Parse one balanced ACE while treating application data as opaque.

    The classifier needs only the access-bearing first six fields. It does not
    evaluate conditional expressions; an untrusted conditional allow is
    classified by its maximum stated rights. Requiring exactly one balanced
    application-data group preserves valid callback/object callback and
    resource-attribute ACEs without letting their nested text become fake ACEs.
    """

    fields = [field.strip() for field in encoded.split(";", 5)]
    if len(fields) != 6:
        return None
    ace_type, flags, rights, object_guid, inherit_guid, principal_payload = fields
    if (
        ace_type not in _SDDL_TYPES
        or _SDDL_ACE_FLAGS.fullmatch(flags) is None
        or (object_guid and _SDDL_GUID.fullmatch(object_guid) is None)
        or (inherit_guid and _SDDL_GUID.fullmatch(inherit_guid) is None)
    ):
        return None
    principal, separator, application_data = principal_payload.partition(";")
    principal = principal.strip()
    if not principal or bool(separator) != (ace_type in _SDDL_APPLICATION_DATA_TYPES):
        return None
    if separator:
        payload = application_data.strip()
        nested = _tokenize_sddl_aces(payload)
        if nested is None or len(nested) != 1 or not nested[0].strip():
            return None
    return ace_type, flags, rights, object_guid, inherit_guid, principal


def _sddl_rights_can_mutate(value: str) -> bool:
    rights = value.strip().upper()
    if not rights:
        return False
    if rights.startswith("0X"):
        try:
            return bool(int(rights, 16) & _SDDL_MUTATING_MASK)
        except ValueError:
            return True
    if len(rights) % 2:
        return True
    tokens = {rights[index : index + 2] for index in range(0, len(rights), 2)}
    if tokens & _SDDL_MUTATING_RIGHTS:
        return True
    return not tokens <= _SDDL_READ_ONLY_RIGHTS


def _sddl_rights_can_replace_child(value: str) -> bool:
    """Return whether effective ancestor rights can replace a checked child."""

    rights = value.strip().upper()
    if not rights:
        return False
    if rights.startswith("0X"):
        try:
            return bool(int(rights, 16) & _SDDL_NAMESPACE_REPLACEMENT_MASK)
        except ValueError:
            return True
    if len(rights) % 2:
        return True
    tokens = {rights[index : index + 2] for index in range(0, len(rights), 2)}
    if tokens & _SDDL_NAMESPACE_REPLACEMENT_RIGHTS:
        return True
    return not tokens <= _SDDL_ANCESTOR_SAFE_RIGHTS


def _untrusted_ace_is_unsafe(
    *,
    flags: str,
    rights: str,
    final_parent: bool,
    prospective_child: bool,
    private_access: bool,
    allow_inheritable_read: bool,
) -> bool:
    """Classify one untrusted grant for its filesystem role."""

    inheritable = "OI" in flags or "CI" in flags
    grants_access = bool(rights.strip())
    mutates = _sddl_rights_can_mutate(rights)
    if private_access:
        return grants_access
    if final_parent:
        return mutates or (inheritable and grants_access and not allow_inheritable_read)
    if prospective_child:
        return ("IO" not in flags and mutates) or (inheritable and mutates)
    return "IO" not in flags and _sddl_rights_can_replace_child(rights)


def windows_directory_prevents_untrusted_writes(
    path: Path,
    *,
    is_windows: bool | None = None,
    sddl_reader: Callable[[Path], str] | None = None,
    current_sid_reader: Callable[[], str | None] | None = None,
    trusted_sid_reader: TrustedSIDProbe | None = None,
    owner_sid_matcher: Callable[[str, str], bool] | None = None,
    final_parent: bool = True,
    prospective_child: bool = False,
    private_access: bool = False,
    allow_inheritable_read: bool = False,
    require_protected_dacl: bool = False,
) -> bool:
    """Recognize a current-user/OS-owned DACL that prevents path substitution.

    The final database parent must not grant another principal any effective or
    inheritable mutation right because SQLite may create journals and sidecars
    there. An inherited private DACL is valid only because every ancestor is
    checked separately by the Store. Ancestors may grant harmless sibling
    creation, but not an effective right that can rename, delete, or replace
    the already-validated next path component. A prospective creation boundary
    additionally rejects mutation rights that a missing child could inherit.
    Bootstrap authorities may additionally require a protected DACL so later
    inheritance changes cannot silently broaden a durable root.
    """

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows or (final_parent and prospective_child):
        return False
    reader = sddl_reader or read_windows_sddl
    sid_reader = current_sid_reader or (lambda: current_process_user_sid(is_windows=True))
    token_sid_reader = trusted_sid_reader or (
        lambda: current_process_restricted_sids(is_windows=True)
    )
    try:
        value = reader(path)
        current_sid = str(sid_reader() or "")
        # A restricting SID may be any shared local/domain group supplied to
        # CreateRestrictedToken. Only a Windows logon SID is unique to the
        # current authenticated logon and safe to treat like the owning user.
        process_sids = {
            str(sid) for sid in token_sid_reader() if _WINDOWS_LOGON_SID.fullmatch(str(sid))
        }
    except Exception:
        return False
    owner = _sddl_owner(value)
    dacl_offset = value.find("D:")
    matcher = owner_sid_matcher or (
        lambda captured, expected: windows_sddl_owner_matches_sid(
            captured,
            expected,
            is_windows=windows,
        )
    )
    try:
        owner_is_current = bool(
            owner and current_sid and (owner == current_sid or matcher(value, current_sid))
        )
    except Exception:
        return False
    owner_is_trusted = owner_is_current or (not final_parent and owner in _TRUSTED_WINDOWS_OWNERS)
    if not owner_is_trusted or dacl_offset < 0:
        return False
    parsed_dacl = _parse_sddl_dacl(value)
    if parsed_dacl is None:
        return False
    control, aces = parsed_dacl
    if require_protected_dacl and "P" not in control:
        return False
    trusted = {*_TRUSTED_WINDOWS_PRINCIPALS, owner, current_sid, *process_sids}
    for encoded in aces:
        fields = _parse_sddl_ace(encoded)
        if fields is None:
            return False
        ace_type, flags, rights, _object_guid, _inherit_guid, principal = fields
        if ace_type in _SDDL_DENY_TYPES:
            continue
        if ace_type not in _SDDL_ALLOW_TYPES:
            if _untrusted_ace_is_unsafe(
                flags=flags,
                rights=rights,
                final_parent=final_parent,
                prospective_child=prospective_child,
                private_access=private_access,
                allow_inheritable_read=allow_inheritable_read,
            ):
                return False
            continue
        if principal in trusted:
            continue
        if _untrusted_ace_is_unsafe(
            flags=flags,
            rights=rights,
            final_parent=final_parent,
            prospective_child=prospective_child,
            private_access=private_access,
            allow_inheritable_read=allow_inheritable_read,
        ):
            return False
    return True


def windows_file_prevents_untrusted_mutation(
    path: Path,
    *,
    is_windows: bool | None = None,
    sddl_reader: Callable[[Path], str] | None = None,
    current_sid_reader: Callable[[], str | None] | None = None,
    trusted_sid_reader: TrustedSIDProbe | None = None,
    owner_sid_matcher: Callable[[str, str], bool] | None = None,
) -> bool:
    """Return whether a current-user/OS-owned file has no untrusted write ACE.

    Executable artifacts may legitimately be owned by the current user,
    LocalSystem, Administrators, or TrustedInstaller. Read and execute grants
    to ordinary users are also normal. Only an effective untrusted mutation
    grant is disqualifying; inherit-only ACEs do not apply to the file itself.
    Unknown ACL shapes fail closed.
    """

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return False
    reader = sddl_reader or read_windows_sddl
    sid_reader = current_sid_reader or (lambda: current_process_user_sid(is_windows=True))
    token_sid_reader = trusted_sid_reader or (
        lambda: current_process_restricted_sids(is_windows=True)
    )
    try:
        value = reader(path)
        current_sid = str(sid_reader() or "")
        process_sids = {
            str(sid) for sid in token_sid_reader() if _WINDOWS_LOGON_SID.fullmatch(str(sid))
        }
    except Exception:
        return False
    owner = _sddl_owner(value)
    dacl_offset = value.find("D:")
    matcher = owner_sid_matcher or (
        lambda captured, expected: windows_sddl_owner_matches_sid(
            captured,
            expected,
            is_windows=windows,
        )
    )
    try:
        owner_is_current = bool(
            owner and current_sid and (owner == current_sid or matcher(value, current_sid))
        )
    except Exception:
        return False
    owner_is_trusted = owner_is_current or owner in _TRUSTED_WINDOWS_OWNERS
    if not owner or not current_sid or not owner_is_trusted or dacl_offset < 0:
        return False
    parsed_dacl = _parse_sddl_dacl(value)
    if parsed_dacl is None:
        return False
    _control, aces = parsed_dacl
    trusted = {*_TRUSTED_WINDOWS_PRINCIPALS, owner, current_sid, *process_sids}
    for encoded in aces:
        fields = _parse_sddl_ace(encoded)
        if fields is None:
            return False
        ace_type, flags, rights, _object_guid, _inherit_guid, principal = fields
        if ace_type in _SDDL_DENY_TYPES or principal in trusted or "IO" in flags:
            continue
        if ace_type not in _SDDL_ALLOW_TYPES or _sddl_rights_can_mutate(rights):
            return False
    return True


def restrict_windows_acl(
    path: Path,
    *,
    directory: bool = False,
    is_windows: bool | None = None,
    token_restriction_probe: TokenRestrictionProbe | None = None,
    acl_applier: ACLApplier | None = None,
    acl_privacy_probe: ACLPrivacyProbe | None = None,
    acl_owner_probe: Callable[[Path], bool] | None = None,
) -> bool:
    """Ensure an owner-only DACL without rewriting an already-private target."""

    windows = os.name == "nt" if is_windows is None else is_windows
    if not windows:
        return False
    privacy_probe = acl_privacy_probe or (
        lambda candidate, *, directory: (
            windows_directory_prevents_untrusted_writes(
                candidate,
                is_windows=True,
                final_parent=True,
                private_access=True,
            )
            and current_process_can_mutate_path(
                candidate,
                directory=directory,
                is_windows=True,
            )
        )
    )
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
    owner_probe = acl_owner_probe or (
        lambda candidate: (
            bool(current_sid := current_process_user_sid(is_windows=True))
            and _sddl_owner(read_windows_sddl(candidate)) == current_sid
        )
    )
    try:
        if not owner_probe(path):
            return False
    except Exception:
        return False
    apply_acl = acl_applier or _apply_owner_only_acl
    apply_acl(path, directory=directory)
    # Always verify the postcondition. A successful Win32 return alone cannot
    # prove that the same path still names the secured object.
    try:
        return bool(privacy_probe(path, directory=directory))
    except Exception:
        return False


__all__ = [
    "RestrictedWindowsTokenError",
    "WindowsACLSafetyError",
    "WindowsTokenProbeError",
    "current_process_can_mutate_path",
    "current_process_has_any_mutation_access",
    "current_process_has_control_forgery_access",
    "current_process_logon_sid",
    "current_process_restricted_sids",
    "current_process_token_is_restricted",
    "current_process_user_sid",
    "read_windows_sddl",
    "require_restricted_windows_token",
    "restrict_windows_acl",
    "restricted_windows_token_cause",
    "windows_directory_prevents_untrusted_writes",
    "windows_file_prevents_untrusted_mutation",
    "windows_restricted_host_boundary_is_trusted",
    "windows_sddl_owner_matches_sid",
    "windows_system_owner_is_trusted",
]
