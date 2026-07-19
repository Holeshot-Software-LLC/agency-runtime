"""Exact fail-closed branch coverage for the native Windows ACL boundary."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import windows_acl


class _Api:
    def __init__(self, function: Any) -> None:
        self.function = function
        self.argtypes: Any = None
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.function(*args)


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class _TokenGroups(ctypes.Structure):
    _fields_ = [("GroupCount", wintypes.DWORD), ("Groups", _SidAndAttributes * 1)]


def _native_libraries(
    monkeypatch: pytest.MonkeyPatch,
    *,
    get_token: Any,
    convert_sid: Any | None = None,
) -> list[Any]:
    freed: list[Any] = []
    advapi = SimpleNamespace(
        GetTokenInformation=_Api(get_token),
        ConvertSidToStringSidW=_Api(convert_sid or (lambda *_args: False)),
    )
    kernel = SimpleNamespace(
        GetCurrentProcess=_Api(lambda: 1),
        CloseHandle=_Api(lambda _handle: True),
        LocalFree=_Api(lambda value: freed.append(value)),
    )
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    monkeypatch.setattr(windows_acl, "_open_effective_token", lambda *_args: 7)
    return freed


def _owner_match_libraries(
    monkeypatch: pytest.MonkeyPatch,
    *,
    descriptor_ok: bool = True,
    descriptor_present: bool = True,
    sid_ok: bool = True,
    sid_present: bool = True,
    owner_ok: bool = True,
    owner_present: bool = True,
    equal: bool = True,
    raise_at: str | None = None,
) -> tuple[list[int | None], list[tuple[int | None, int | None]]]:
    freed: list[int | None] = []
    comparisons: list[tuple[int | None, int | None]] = []

    def convert_descriptor(_value: Any, _revision: Any, output: Any, _length: Any) -> bool:
        if raise_at == "descriptor":
            output._obj.value = 101
            raise ctypes.ArgumentError("descriptor")
        if descriptor_ok and descriptor_present:
            output._obj.value = 101
        return descriptor_ok

    def convert_sid(_value: Any, output: Any) -> bool:
        if raise_at == "sid":
            output._obj.value = 202
            raise ctypes.ArgumentError("sid")
        if sid_ok and sid_present:
            output._obj.value = 202
        return sid_ok

    def get_owner(_descriptor: Any, output: Any, _defaulted: Any) -> bool:
        if raise_at == "owner":
            raise ctypes.ArgumentError("owner")
        if owner_ok and owner_present:
            output._obj.value = 303
        return owner_ok

    def equal_sid(owner: Any, expected: Any) -> bool:
        if raise_at == "equal":
            raise ctypes.ArgumentError("equal")
        comparisons.append((owner.value, expected.value))
        return equal

    advapi = SimpleNamespace(
        ConvertStringSecurityDescriptorToSecurityDescriptorW=_Api(convert_descriptor),
        ConvertStringSidToSidW=_Api(convert_sid),
        GetSecurityDescriptorOwner=_Api(get_owner),
        EqualSid=_Api(equal_sid),
    )
    kernel = SimpleNamespace(LocalFree=_Api(lambda value: freed.append(value.value)))
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    return freed, comparisons


@pytest.mark.parametrize(
    ("value", "expected_sid", "is_windows"),
    [
        ("O:LAD:P(A;;FA;;;LA)", "S-1-5-21-42", False),
        ("", "S-1-5-21-42", True),
        ("O:LA", "", True),
        ("O:LA\0D:P(A;;FA;;;LA)", "S-1-5-21-42", True),
        ("O:LA", "LA", True),
        ("O:LA", "S-1-5-21-42\0BAD", True),
    ],
)
def test_owner_sid_matcher_rejects_unavailable_inputs_without_native_calls(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    expected_sid: str,
    is_windows: bool,
) -> None:
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("native call")),
        raising=False,
    )

    assert not windows_acl.windows_sddl_owner_matches_sid(
        value,
        expected_sid,
        is_windows=is_windows,
    )


@pytest.mark.parametrize(
    ("failure", "expected_freed"),
    [
        ("descriptor", []),
        ("missing_descriptor", []),
        ("sid", [101]),
        ("missing_sid", [101]),
        ("owner", [202, 101]),
        ("missing_owner", [202, 101]),
    ],
)
def test_owner_sid_matcher_fails_closed_and_releases_allocations(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_freed: list[int],
) -> None:
    freed, comparisons = _owner_match_libraries(
        monkeypatch,
        descriptor_ok=failure != "descriptor",
        descriptor_present=failure != "missing_descriptor",
        sid_ok=failure != "sid",
        sid_present=failure != "missing_sid",
        owner_ok=failure != "owner",
        owner_present=failure != "missing_owner",
    )

    assert not windows_acl.windows_sddl_owner_matches_sid(
        "O:LAD:P(A;;FA;;;LA)",
        "S-1-5-21-42",
        is_windows=True,
    )
    assert comparisons == []
    assert freed == expected_freed


@pytest.mark.parametrize("equal", [False, True])
def test_owner_sid_matcher_uses_binary_sid_identity(
    monkeypatch: pytest.MonkeyPatch,
    equal: bool,
) -> None:
    freed, comparisons = _owner_match_libraries(monkeypatch, equal=equal)

    assert (
        windows_acl.windows_sddl_owner_matches_sid(
            "O:LAD:P(A;;FA;;;LA)",
            "S-1-5-21-42",
            is_windows=True,
        )
        is equal
    )
    assert comparisons == [(303, 202)]
    assert freed == [202, 101]


def test_owner_sid_matcher_native_exceptions_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
        raising=False,
    )

    assert not windows_acl.windows_sddl_owner_matches_sid(
        "O:LAD:P(A;;FA;;;LA)",
        "S-1-5-21-42",
        is_windows=True,
    )


@pytest.mark.parametrize(
    ("raise_at", "expected_freed"),
    [
        ("descriptor", [101]),
        ("sid", [202, 101]),
        ("owner", [202, 101]),
        ("equal", [202, 101]),
    ],
)
def test_owner_sid_matcher_ctypes_errors_fail_closed_after_allocation(
    monkeypatch: pytest.MonkeyPatch,
    raise_at: str,
    expected_freed: list[int],
) -> None:
    freed, comparisons = _owner_match_libraries(monkeypatch, raise_at=raise_at)

    assert not windows_acl.windows_sddl_owner_matches_sid(
        "O:LAD:P(A;;FA;;;LA)",
        "S-1-5-21-42",
        is_windows=True,
    )
    assert comparisons == []
    assert freed == expected_freed


def test_restricted_token_api_failures_are_not_reported_as_unrestricted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    last_error = 0

    def set_last_error(value: int) -> None:
        nonlocal last_error
        last_error = value

    monkeypatch.setattr(ctypes, "set_last_error", set_last_error, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)
    advapi = SimpleNamespace(
        IsTokenRestricted=_Api(lambda _token: ctypes.set_last_error(5) or False),
        GetTokenInformation=_Api(lambda *_args: True),
    )
    kernel = SimpleNamespace(
        GetCurrentProcess=_Api(lambda: 1),
        CloseHandle=_Api(lambda _handle: True),
    )
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    monkeypatch.setattr(windows_acl, "_open_effective_token", lambda *_args: 7)

    with pytest.raises(windows_acl.WindowsTokenProbeError):
        windows_acl.current_process_token_is_restricted(is_windows=True)

    advapi.IsTokenRestricted = _Api(lambda _token: False)
    advapi.GetTokenInformation = _Api(lambda *_args: False)
    with pytest.raises(windows_acl.WindowsTokenProbeError):
        windows_acl.current_process_token_is_restricted(is_windows=True)


@pytest.mark.parametrize("failure", ("empty", "read", "convert"))
def test_current_user_sid_fails_closed_at_each_native_boundary(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    def get_token(
        _token: Any,
        _kind: int,
        output: Any,
        _size: Any,
        required: Any,
    ) -> bool:
        if output is None:
            required._obj.value = 0 if failure == "empty" else 32
            return True
        if failure == "read":
            return False
        ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = 101
        return True

    _native_libraries(
        monkeypatch,
        get_token=get_token,
        convert_sid=lambda *_args: failure != "convert",
    )

    assert windows_acl.current_process_user_sid(is_windows=True) is None


def test_current_user_sid_success_releases_the_native_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered = ctypes.create_unicode_buffer("S-1-5-21-42")

    def get_token(
        _token: Any,
        _kind: int,
        output: Any,
        _size: Any,
        required: Any,
    ) -> bool:
        if output is None:
            required._obj.value = 32
        else:
            ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = 101
        return True

    def convert_sid(_sid: Any, output: Any) -> bool:
        ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(rendered)
        return True

    freed = _native_libraries(monkeypatch, get_token=get_token, convert_sid=convert_sid)

    assert windows_acl.current_process_user_sid(is_windows=True) == "S-1-5-21-42"
    assert len(freed) == 1


@pytest.mark.parametrize("failure", ("empty", "read", "count", "null_sid", "convert"))
def test_restricted_sid_reader_handles_empty_or_unrenderable_native_results(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    def get_token(
        _token: Any,
        _kind: int,
        output: Any,
        _size: Any,
        required: Any,
    ) -> bool:
        if output is None:
            required._obj.value = 0 if failure == "empty" else ctypes.sizeof(_TokenGroups)
            return True
        if failure == "read":
            return False
        groups = ctypes.cast(output, ctypes.POINTER(_TokenGroups)).contents
        groups.GroupCount = 0 if failure == "count" else 1
        groups.Groups[0].Sid = None if failure == "null_sid" else 101
        return True

    _native_libraries(
        monkeypatch,
        get_token=get_token,
        convert_sid=lambda *_args: failure != "convert",
    )

    assert windows_acl.current_process_restricted_sids(is_windows=True) == frozenset()


@pytest.mark.parametrize(
    "failure",
    ("empty", "read", "count", "null_sid", "convert", "empty_sid", "exception"),
)
def test_token_group_entry_reader_fails_closed_for_malformed_native_results(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    rendered = ctypes.create_unicode_buffer("" if failure == "empty_sid" else "S-1-5-5-1-2")

    def get_token(
        _token: Any,
        _kind: int,
        output: Any,
        _size: Any,
        required: Any,
    ) -> bool:
        if output is None:
            required._obj.value = 0 if failure == "empty" else ctypes.sizeof(_TokenGroups)
            return True
        if failure == "read":
            return False
        groups = ctypes.cast(output, ctypes.POINTER(_TokenGroups)).contents
        groups.GroupCount = 0 if failure == "count" else 1
        groups.Groups[0].Sid = None if failure == "null_sid" else 101
        groups.Groups[0].Attributes = 4
        return True

    def convert_sid(_sid: Any, output: Any) -> bool:
        if failure == "convert":
            return False
        ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(rendered)
        return True

    if failure == "exception":
        monkeypatch.setattr(
            ctypes,
            "WinDLL",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
            raising=False,
        )
    else:
        _native_libraries(monkeypatch, get_token=get_token, convert_sid=convert_sid)

    assert windows_acl._current_process_token_sid_entries(11, is_windows=True) == ()


def test_non_windows_native_probes_return_their_documented_sentinels() -> None:
    assert windows_acl.current_process_restricted_sids(is_windows=False) == frozenset()
    assert windows_acl._current_process_token_sid_entries(11, is_windows=False) == ()
    assert not windows_acl.current_process_can_mutate_path(
        Path("unused"), directory=True, is_windows=False
    )
    assert (
        windows_acl._current_process_has_requested_access(
            Path("unused"),
            directory=True,
            requested_rights=(2,),
            is_windows=False,
        )
        is None
    )


def test_native_path_probes_fail_closed_when_the_api_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
        raising=False,
    )

    assert not windows_acl.current_process_can_mutate_path(
        Path("state"), directory=False, is_windows=True
    )
    assert (
        windows_acl._current_process_has_requested_access(
            Path("state"),
            directory=False,
            requested_rights=(2,),
            is_windows=True,
        )
        is None
    )


def test_native_mutation_probe_rejects_the_invalid_handle_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = SimpleNamespace(
        CreateFileW=_Api(lambda *_args: ctypes.c_void_p(-1).value),
        CloseHandle=_Api(lambda _handle: True),
    )
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)

    assert not windows_acl.current_process_can_mutate_path(
        Path("state"),
        directory=False,
        is_windows=True,
    )


def test_native_path_probes_close_successful_windows_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    last_error = 0

    def set_last_error(value: int) -> None:
        nonlocal last_error
        last_error = value

    kernel = SimpleNamespace(
        CreateFileW=_Api(lambda *_args: 7),
        CloseHandle=_Api(lambda handle: closed.append(handle) or True),
    )
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    monkeypatch.setattr(ctypes, "set_last_error", set_last_error, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)

    assert windows_acl.current_process_can_mutate_path(
        Path("state"),
        directory=True,
        is_windows=True,
    )
    assert windows_acl._current_process_has_requested_access(
        Path("state"),
        directory=False,
        requested_rights=(2,),
        is_windows=True,
    )
    assert closed == [7, 7]


def test_restricted_host_boundary_handles_probe_failure_and_invalid_acls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        windows_acl,
        "read_windows_sddl",
        lambda _path: (_ for _ in ()).throw(windows_acl.WindowsTokenProbeError("denied")),
    )
    assert not windows_acl.windows_restricted_host_boundary_is_trusted(Path("host"))

    monkeypatch.setattr(windows_acl, "current_process_user_sid", lambda **_kwargs: "S-1-5-21-42")
    monkeypatch.setattr(
        windows_acl, "current_process_restricted_sids", lambda **_kwargs: frozenset({"S-1-5-5-1-2"})
    )
    monkeypatch.setattr(windows_acl, "read_windows_sddl", lambda _path: "malformed")
    assert not windows_acl.windows_restricted_host_boundary_is_trusted(Path("host"))

    owner = "S-1-5-21-42"
    for dacl in (
        "(malformed)",
        "(D;OICI;FA;;;S-1-1-0)",
        "(XA;OICI;FA;;;S-1-5-5-1-2)",
        "(A;OICI;;;;S-1-5-5-1-2)",
    ):
        monkeypatch.setattr(
            windows_acl, "read_windows_sddl", lambda _path, dacl=dacl: f"O:{owner}D:P{dacl}"
        )
        assert not windows_acl.windows_restricted_host_boundary_is_trusted(Path("host"))


def test_restricted_host_boundary_accepts_one_restricting_logon_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = "S-1-5-21-42"
    restricting = "S-1-5-5-1-2"
    monkeypatch.setattr(windows_acl, "current_process_user_sid", lambda **_kwargs: owner)
    monkeypatch.setattr(
        windows_acl,
        "current_process_restricted_sids",
        lambda **_kwargs: frozenset({restricting}),
    )
    monkeypatch.setattr(
        windows_acl,
        "read_windows_sddl",
        lambda _path: (
            f"O:{owner}D:P"
            f"(A;OICI;FA;;;{owner})"
            "(A;OICI;FA;;;SY)"
            "(A;OICI;FA;;;BA)"
            f"(A;OICI;FA;;;{restricting})"
        ),
    )
    monkeypatch.setattr(
        windows_acl,
        "current_process_can_mutate_path",
        lambda *_args, **_kwargs: True,
    )

    assert windows_acl.windows_restricted_host_boundary_is_trusted(Path("host"))


def test_owner_probe_exception_prevents_acl_mutation() -> None:
    assert not windows_acl.restrict_windows_acl(
        Path("state"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: False,
        token_restriction_probe=lambda: False,
        acl_owner_probe=lambda _path: (_ for _ in ()).throw(OSError("owner unavailable")),
        acl_applier=lambda *_args, **_kwargs: pytest.fail("ACL mutation must not run"),
    )
