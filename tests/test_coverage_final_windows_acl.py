"""Exact fail-closed branch coverage for the native Windows ACL boundary."""

from __future__ import annotations

import ctypes
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
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", ctypes.wintypes.DWORD)]


class _TokenGroups(ctypes.Structure):
    _fields_ = [("GroupCount", ctypes.wintypes.DWORD), ("Groups", _SidAndAttributes * 1)]


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


def test_restricted_token_api_failures_are_not_reported_as_unrestricted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


@pytest.mark.parametrize("failure", ("empty", "read", "null_sid", "convert"))
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
        groups.GroupCount = 1
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


def test_owner_probe_exception_prevents_acl_mutation() -> None:
    assert not windows_acl.restrict_windows_acl(
        Path("state"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: False,
        token_restriction_probe=lambda: False,
        acl_owner_probe=lambda _path: (_ for _ in ()).throw(OSError("owner unavailable")),
        acl_applier=lambda *_args, **_kwargs: pytest.fail("ACL mutation must not run"),
    )
