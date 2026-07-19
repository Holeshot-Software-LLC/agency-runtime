"""Windows DACL safety regressions for restricted process tokens."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import configuration, windows_acl
from agency_runtime.core.canary import _copy_bounded_auth
from agency_runtime.core.configuration_contracts import ConfigurationError
from agency_runtime.core.configuration_persistence import restrict_permissions
from agency_runtime.core.store.security import restrict_path_permissions
from agency_runtime.core.windows_acl import (
    RestrictedWindowsTokenError,
    WindowsTokenProbeError,
    current_process_token_is_restricted,
    restrict_windows_acl,
    windows_directory_prevents_untrusted_writes,
    windows_file_prevents_untrusted_mutation,
)


def test_non_windows_acl_path_does_not_probe_or_mutate() -> None:
    calls: list[str] = []

    assert (
        restrict_windows_acl(
            Path("unused"),
            is_windows=False,
            token_restriction_probe=lambda: calls.append("probe") or False,
            acl_applier=lambda *_args, **_kwargs: calls.append("apply") or True,
        )
        is False
    )
    assert calls == []


def test_windows_executable_file_allows_reads_but_rejects_untrusted_mutation() -> None:
    current = "S-1-5-21-1-2-3-1001"
    trusted = f"O:{current}D:(A;;FA;;;{current})(A;;FRGX;;;BU)"
    writable = f"O:{current}D:(A;;FA;;;{current})(A;;FW;;;BU)"

    common = {
        "is_windows": True,
        "current_sid_reader": lambda: current,
        "trusted_sid_reader": lambda: set(),
    }
    assert windows_file_prevents_untrusted_mutation(
        Path("tool.exe"),
        sddl_reader=lambda _path: trusted,
        **common,
    )
    assert not windows_file_prevents_untrusted_mutation(
        Path("tool.exe"),
        sddl_reader=lambda _path: writable,
        **common,
    )
    assert not windows_file_prevents_untrusted_mutation(
        Path("tool.exe"),
        sddl_reader=lambda _path: "O:S-1-5-21-9D:(A;;FR;;;BU)",
        **common,
    )


def test_restricted_token_is_rejected_before_acl_mutation() -> None:
    mutations: list[Path] = []

    with pytest.raises(RestrictedWindowsTokenError, match="restricted process token"):
        restrict_windows_acl(
            Path("restricted"),
            is_windows=True,
            token_restriction_probe=lambda: True,
            acl_applier=lambda path, **_kwargs: mutations.append(path) or True,
        )

    assert mutations == []


def test_unknown_token_state_is_rejected_before_acl_mutation() -> None:
    mutations: list[Path] = []

    def unavailable_probe() -> bool:
        raise OSError("token query denied")

    with pytest.raises(WindowsTokenProbeError, match="could not inspect"):
        restrict_windows_acl(
            Path("unknown"),
            is_windows=True,
            token_restriction_probe=unavailable_probe,
            acl_applier=lambda path, **_kwargs: mutations.append(path) or True,
        )

    assert mutations == []


def test_unrestricted_token_applies_requested_file_or_directory_acl() -> None:
    calls: list[tuple[Path, bool]] = []
    inspections = iter((False, True))

    assert (
        restrict_windows_acl(
            Path("private-directory"),
            directory=True,
            is_windows=True,
            token_restriction_probe=lambda: False,
            acl_applier=lambda path, *, directory: calls.append((path, directory)) or True,
            acl_privacy_probe=lambda *_args, **_kwargs: next(inspections),
            acl_owner_probe=lambda _path: True,
        )
        is True
    )
    assert calls == [(Path("private-directory"), True)]


def test_existing_private_acl_skips_token_probe_and_mutation() -> None:
    calls: list[str] = []

    assert restrict_windows_acl(
        Path("private"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: True,
        token_restriction_probe=lambda: calls.append("token") or False,
        acl_applier=lambda *_args, **_kwargs: calls.append("mutation") or True,
    )
    assert calls == []


def test_failed_acl_inspection_falls_back_to_safe_token_gate() -> None:
    calls: list[str] = []

    def inspect(*_args: object, **_kwargs: object) -> bool:
        calls.append("inspect")
        if calls.count("inspect") == 1:
            raise OSError("denied")
        return True

    assert restrict_windows_acl(
        Path("private"),
        is_windows=True,
        acl_privacy_probe=inspect,
        token_restriction_probe=lambda: calls.append("token") or False,
        acl_applier=lambda *_args, **_kwargs: calls.append("mutation") or True,
        acl_owner_probe=lambda _path: True,
    )
    assert calls == ["inspect", "token", "mutation", "inspect"]


def test_failed_acl_mutation_accepts_a_concurrently_private_postcondition() -> None:
    inspections = 0

    def inspect(_path: Path, *, directory: bool) -> bool:
        nonlocal inspections
        del directory
        inspections += 1
        return inspections == 2

    assert restrict_windows_acl(
        Path("private"),
        is_windows=True,
        acl_privacy_probe=inspect,
        token_restriction_probe=lambda: False,
        acl_applier=lambda *_args, **_kwargs: False,
        acl_owner_probe=lambda _path: True,
    )
    assert inspections == 2


def test_failed_acl_mutation_remains_failed_when_postcondition_is_unknown() -> None:
    inspections = 0

    def inspect(_path: Path, *, directory: bool) -> bool:
        nonlocal inspections
        del directory
        inspections += 1
        if inspections == 2:
            raise OSError("sidecar disappeared")
        return False

    assert not restrict_windows_acl(
        Path("private"),
        is_windows=True,
        acl_privacy_probe=inspect,
        token_restriction_probe=lambda: False,
        acl_applier=lambda *_args, **_kwargs: False,
        acl_owner_probe=lambda _path: True,
    )

    assert not restrict_windows_acl(
        Path("still-public"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: False,
        token_restriction_probe=lambda: False,
        acl_applier=lambda *_args, **_kwargs: False,
        acl_owner_probe=lambda _path: True,
    )


def test_successful_acl_api_result_still_requires_a_private_postcondition() -> None:
    inspections = iter((False, False))

    assert not restrict_windows_acl(
        Path("state"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: next(inspections),
        token_restriction_probe=lambda: False,
        acl_owner_probe=lambda _path: True,
        acl_applier=lambda *_args, **_kwargs: True,
    )


def test_foreign_owner_is_rejected_before_acl_mutation() -> None:
    calls: list[str] = []

    assert not restrict_windows_acl(
        Path("state"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: False,
        token_restriction_probe=lambda: False,
        acl_owner_probe=lambda _path: False,
        acl_applier=lambda *_args, **_kwargs: calls.append("mutation") or True,
    )
    assert calls == []


def test_owner_only_acl_recognizes_protected_and_private_inherited_shapes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    owner = "S-1-5-21-1001"
    parent = tmp_path / "private"
    child = parent / "state.db-wal"
    protected_file = parent / "state.db"
    inherited_directory = parent / "nested"
    root = Path(tmp_path.anchor)
    values = {
        parent: f"O:{owner}D:PAI(A;OICI;FA;;;{owner})",
        child: f"O:{owner}D:AI(A;ID;FA;;;{owner})",
        protected_file: f"O:{owner}D:PAI(A;;FA;;;{owner})",
        inherited_directory: f"O:{owner}D:AI(A;OICIID;FA;;;{owner})",
        root: f"O:{owner}D:AI(A;OICIID;FA;;;{owner})",
    }
    monkeypatch.setattr(windows_acl, "read_windows_sddl", values.get)

    assert windows_acl._owner_only_acl_is_present(parent, directory=True)
    assert windows_acl._owner_only_acl_is_present(child, directory=False)
    assert windows_acl._owner_only_acl_is_present(protected_file, directory=False)
    assert windows_acl._owner_only_acl_is_present(inherited_directory, directory=True)
    assert not windows_acl._owner_only_acl_is_present(root, directory=True)

    values[child] = f"O:{owner}D:AI(A;ID;FR;;;{owner})"
    assert not windows_acl._owner_only_acl_is_present(child, directory=False)
    values[child] = "malformed"
    assert not windows_acl._owner_only_acl_is_present(child, directory=False)


@pytest.mark.parametrize(
    ("sddl", "expected"),
    [
        (
            "O:S-1-5-21-1001D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;OW)",
            True,
        ),
        (
            "O:S-1-5-21-1001D:PAI(A;OICI;FA;;;S-1-5-21-1001)(A;OICI;0x1200a9;;;BU)",
            False,
        ),
        ("O:S-1-5-21-1001D:AI(A;OICI;FA;;;S-1-5-21-1001)", True),
        (
            "O:S-1-5-21-1001D:P(A;OICI;FW;;;S-1-5-21-2002)",
            False,
        ),
        (
            "O:S-1-5-21-1001D:P(A;OICI;0x1301bf;;;S-1-5-21-2002)",
            False,
        ),
        (
            "O:S-1-5-21-1001D:P(D;OICI;FA;;;S-1-5-21-2002)(A;OICI;FR;;;S-1-5-21-2002)",
            False,
        ),
        ("O:S-1-5-21-1001D:P(A;OICI;ZZ;;;S-1-5-21-2002)", False),
        ("O:S-1-5-21-1001D:P(malformed)", False),
        ("D:P(A;OICI;FA;;;SY)", False),
        ("O:S-1-5-21-1001", False),
        ("", False),
    ],
)
def test_windows_parent_acl_probe_accepts_only_trusted_mutation_grants(
    sddl: str,
    expected: bool,
) -> None:
    assert (
        windows_directory_prevents_untrusted_writes(
            Path("state"),
            is_windows=True,
            sddl_reader=lambda _path: sddl,
            current_sid_reader=lambda: "S-1-5-21-1001",
        )
        is expected
    )


def test_windows_parent_acl_probe_is_non_windows_and_error_safe() -> None:
    assert not windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=False,
        sddl_reader=lambda _path: (_ for _ in ()).throw(AssertionError("called")),
    )
    assert not windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: (_ for _ in ()).throw(OSError("denied")),
    )
    assert windows_acl._sddl_rights_can_mutate("0x-not-hex")
    assert windows_acl._sddl_rights_can_mutate("F")
    assert not windows_acl._sddl_rights_can_mutate("")


@pytest.mark.parametrize(
    ("owner", "expected"),
    [
        ("BA", True),
        ("SY", True),
        ("S-1-5-18", True),
        ("S-1-5-32-544", True),
        (
            "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464",
            True,
        ),
        ("CO", False),
        ("OW", False),
        ("S-1-5-21-1001", False),
        ("", False),
    ],
)
def test_windows_system_owner_classifier_is_narrow(owner: str, expected: bool) -> None:
    assert windows_acl.windows_system_owner_is_trusted(owner) is expected


@pytest.mark.parametrize("owner", ["CO", "OW", "S-1-3-0", "S-1-3-4"])
def test_windows_parent_acl_probe_rejects_pseudo_principal_owners(owner: str) -> None:
    assert not windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: f"O:{owner}D:P(A;OICI;FA;;;S-1-5-21-1001)",
        current_sid_reader=lambda: "S-1-5-21-1001",
        final_parent=False,
        prospective_child=True,
        private_access=True,
    )


@pytest.mark.parametrize("control", ["", "AI", "AR", "AIAR"])
def test_windows_bootstrap_acl_probe_requires_protection(control: str) -> None:
    assert not windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: f"O:BAD:{control}(A;OICI;FA;;;SY)(A;OICI;FA;;;S-1-5-21-1001)",
        current_sid_reader=lambda: "S-1-5-21-1001",
        final_parent=False,
        prospective_child=True,
        private_access=True,
        require_protected_dacl=True,
    )


def test_windows_bootstrap_acl_probe_accepts_a_protected_private_dacl() -> None:
    assert windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: "O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;S-1-5-21-1001)",
        current_sid_reader=lambda: "S-1-5-21-1001",
        final_parent=False,
        prospective_child=True,
        private_access=True,
        require_protected_dacl=True,
    )


def test_unrecorded_capability_sid_is_never_implicitly_trusted() -> None:
    owner = "S-1-5-21-1001"
    capability = "S-1-15-3-123-456"

    assert not windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: f"O:{owner}D:P(A;OICI;FA;;;{capability})",
        current_sid_reader=lambda: owner,
        trusted_sid_reader=lambda: frozenset({"S-1-5-21-999"}),
        private_access=True,
    )


def test_shared_restricting_group_is_not_a_private_principal() -> None:
    owner = "S-1-5-21-1001"
    shared_group = "S-1-5-21-2002"

    assert not windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: f"O:{owner}D:P(A;OICI;FA;;;{shared_group})",
        current_sid_reader=lambda: owner,
        trusted_sid_reader=lambda: frozenset({shared_group}),
        private_access=True,
    )


def test_current_logon_sid_may_remain_a_private_token_principal() -> None:
    owner = "S-1-5-21-1001"
    logon_sid = "S-1-5-5-42-9001"

    assert windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: f"O:{owner}D:P(A;OICI;FA;;;{logon_sid})",
        current_sid_reader=lambda: owner,
        trusted_sid_reader=lambda: frozenset({logon_sid}),
        private_access=True,
    )


def test_current_process_logon_sid_requires_the_same_enabled_sid_in_all_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sid = "S-1-5-5-42-9001"
    required = windows_acl._SE_GROUP_ENABLED | windows_acl._SE_GROUP_LOGON_ID
    entries = {
        28: ((sid, required),),
        2: ((sid, required),),
        11: ((sid, windows_acl._SE_GROUP_ENABLED),),
    }
    monkeypatch.setattr(
        windows_acl,
        "_current_process_token_sid_entries",
        lambda information_class, **_kwargs: entries[information_class],
    )

    assert windows_acl.current_process_logon_sid(is_windows=True) == sid


@pytest.mark.parametrize(
    "entries",
    (
        {28: (), 2: (), 11: ()},
        {28: (("S-1-5-5-1-2", 0),), 2: (), 11: ()},
        {
            28: (("S-1-5-5-1-2", windows_acl._SE_GROUP_ENABLED | windows_acl._SE_GROUP_LOGON_ID),),
            2: (),
            11: (),
        },
        {
            28: (("S-1-5-5-1-2", windows_acl._SE_GROUP_ENABLED | windows_acl._SE_GROUP_LOGON_ID),),
            2: (("S-1-5-5-1-2", windows_acl._SE_GROUP_ENABLED | windows_acl._SE_GROUP_LOGON_ID),),
            11: (("S-1-5-5-1-2", 0),),
        },
        {
            28: (
                ("S-1-5-5-1-2", windows_acl._SE_GROUP_ENABLED | windows_acl._SE_GROUP_LOGON_ID),
                ("S-1-5-5-3-4", windows_acl._SE_GROUP_ENABLED | windows_acl._SE_GROUP_LOGON_ID),
            ),
            2: (),
            11: (),
        },
    ),
)
def test_current_process_logon_sid_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    entries: dict[int, tuple[tuple[str, int], ...]],
) -> None:
    monkeypatch.setattr(
        windows_acl,
        "_current_process_token_sid_entries",
        lambda information_class, **_kwargs: entries[information_class],
    )

    assert windows_acl.current_process_logon_sid(is_windows=True) is None


class _TokenApi:
    def __init__(self, function: object) -> None:
        self.function = function
        self.argtypes: object = None
        self.restype: object = None

    def __call__(self, *args: object) -> object:
        assert callable(self.function)
        return self.function(*args)


class _FakeCtypes:
    def __init__(self) -> None:
        self.last_error = 0

    @staticmethod
    def POINTER(_value: object) -> object:
        return object

    @staticmethod
    def byref(value: object) -> object:
        return value

    def set_last_error(self, value: int) -> None:
        self.last_error = value

    def get_last_error(self) -> int:
        return self.last_error


class _FakeWinTypes:
    class HANDLE:
        pass

    DWORD = int
    BOOL = bool


def _effective_token_apis(
    *,
    thread_result: bool,
    process_result: bool,
    thread_error: int,
) -> tuple[SimpleNamespace, SimpleNamespace, _FakeCtypes, list[str]]:
    fake_ctypes = _FakeCtypes()
    calls: list[str] = []

    def open_thread(*_args: object) -> bool:
        calls.append("thread")
        fake_ctypes.set_last_error(thread_error)
        return thread_result

    def open_process(*_args: object) -> bool:
        calls.append("process")
        return process_result

    advapi32 = SimpleNamespace(
        OpenThreadToken=_TokenApi(open_thread),
        OpenProcessToken=_TokenApi(open_process),
    )
    kernel32 = SimpleNamespace(
        GetCurrentThread=_TokenApi(lambda: 1),
        GetCurrentProcess=_TokenApi(lambda: 2),
    )
    return advapi32, kernel32, fake_ctypes, calls


def test_effective_token_prefers_the_current_thread_token() -> None:
    advapi32, kernel32, fake_ctypes, calls = _effective_token_apis(
        thread_result=True,
        process_result=False,
        thread_error=0,
    )

    token = windows_acl._open_effective_token(
        advapi32,
        kernel32,
        fake_ctypes,
        _FakeWinTypes,
    )

    assert isinstance(token, _FakeWinTypes.HANDLE)
    assert calls == ["thread"]


def test_effective_token_uses_process_only_when_the_thread_has_no_token() -> None:
    advapi32, kernel32, fake_ctypes, calls = _effective_token_apis(
        thread_result=False,
        process_result=True,
        thread_error=windows_acl._ERROR_NO_TOKEN,
    )

    token = windows_acl._open_effective_token(
        advapi32,
        kernel32,
        fake_ctypes,
        _FakeWinTypes,
    )

    assert isinstance(token, _FakeWinTypes.HANDLE)
    assert calls == ["thread", "process"]


@pytest.mark.parametrize(
    ("thread_error", "process_result", "expected_calls"),
    (
        (5, True, ["thread"]),
        (windows_acl._ERROR_NO_TOKEN, False, ["thread", "process"]),
    ),
)
def test_effective_token_fails_closed_on_probe_errors(
    thread_error: int,
    process_result: bool,
    expected_calls: list[str],
) -> None:
    advapi32, kernel32, fake_ctypes, calls = _effective_token_apis(
        thread_result=False,
        process_result=process_result,
        thread_error=thread_error,
    )

    with pytest.raises(WindowsTokenProbeError, match="could not inspect"):
        windows_acl._open_effective_token(
            advapi32,
            kernel32,
            fake_ctypes,
            _FakeWinTypes,
        )

    assert calls == expected_calls


@pytest.mark.parametrize(("error_code", "expected"), [(5, False), (32, None), (0, None)])
def test_requested_access_negative_proof_requires_access_denied(
    monkeypatch: pytest.MonkeyPatch,
    error_code: int,
    expected: bool | None,
) -> None:
    last_error = 0

    def set_last_error(value: int) -> None:
        nonlocal last_error
        last_error = value

    def create_file(*_args: object) -> int:
        nonlocal last_error
        last_error = error_code
        return ctypes.c_void_p(-1).value

    create_file.argtypes = None  # type: ignore[attr-defined]
    create_file.restype = None  # type: ignore[attr-defined]

    def close_handle(_handle: object) -> bool:
        return True

    close_handle.argtypes = None  # type: ignore[attr-defined]
    kernel = SimpleNamespace(CreateFileW=create_file, CloseHandle=close_handle)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    monkeypatch.setattr(ctypes, "set_last_error", set_last_error, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)

    assert (
        windows_acl._current_process_has_requested_access(
            Path("state"),
            directory=False,
            requested_rights=(0x00000002,),
            is_windows=True,
        )
        is expected
    )


def test_control_forgery_probe_excludes_delete_only_rights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[int, ...]] = []

    def capture(
        _path: Path,
        *,
        directory: bool,
        requested_rights: tuple[int, ...],
        is_windows: bool | None,
    ) -> bool:
        del directory, is_windows
        observed.append(requested_rights)
        return False

    monkeypatch.setattr(windows_acl, "_current_process_has_requested_access", capture)

    assert (
        windows_acl.current_process_has_any_mutation_access(
            Path("state"), directory=True, is_windows=True
        )
        is False
    )
    assert (
        windows_acl.current_process_has_control_forgery_access(
            Path("state"), directory=True, is_windows=True
        )
        is False
    )
    assert 0x00010000 in observed[0]
    assert 0x00000040 in observed[0]
    assert 0x00010000 not in observed[1]
    assert 0x00000040 not in observed[1]


@pytest.mark.skipif(os.name != "nt", reason="requires Windows access checks")
def test_real_forgery_probe_recognizes_writable_test_identity(tmp_path: Path) -> None:
    target = tmp_path / "writable.txt"
    target.write_text("state", encoding="utf-8")

    assert windows_acl.current_process_has_control_forgery_access(
        tmp_path,
        directory=True,
        is_windows=True,
    )
    assert windows_acl.current_process_has_control_forgery_access(
        target,
        directory=False,
        is_windows=True,
    )
    assert (
        windows_acl.current_process_has_control_forgery_access(
            target,
            directory=False,
            is_windows=False,
        )
        is None
    )


def test_configuration_surfaces_restricted_token_without_fallback_mutation() -> None:
    path = Path("agency.yaml")

    def restricted_acl(_path: Path, *, directory: bool = False) -> bool:
        del directory
        raise RestrictedWindowsTokenError(
            "owner-only Windows ACL cannot be changed from a restricted process token"
        )

    with pytest.raises(ConfigurationError, match="restricted process token"):
        restrict_permissions(
            path,
            required=True,
            is_windows=True,
            windows_acl=restricted_acl,
            path_check=lambda _path: False,
        )


def test_restricted_token_cause_survives_typed_domain_wrappers() -> None:
    restricted = RestrictedWindowsTokenError("restricted process token")
    try:
        raise ConfigurationError("configuration unavailable") from restricted
    except ConfigurationError as wrapped:
        assert windows_acl.restricted_windows_token_cause(wrapped) is restricted
        assert windows_acl.require_restricted_windows_token(wrapped) is restricted


def test_restricted_token_guard_reraises_unrelated_errors() -> None:
    unrelated = ConfigurationError("ordinary invalid configuration")

    assert windows_acl.restricted_windows_token_cause(unrelated) is None
    with pytest.raises(ConfigurationError, match="ordinary invalid configuration") as raised:
        windows_acl.require_restricted_windows_token(unrelated)
    assert raised.value is unrelated


def test_configuration_restricted_token_preserves_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    original = b"profile: standard\n"
    path.write_bytes(original)
    monkeypatch.setattr(configuration, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        configuration._persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    monkeypatch.setattr(
        configuration,
        "_restrict_windows_acl",
        lambda _path, **_kwargs: (_ for _ in ()).throw(
            RestrictedWindowsTokenError(
                "owner-only Windows ACL cannot be changed from a restricted process token"
            )
        ),
    )

    with pytest.raises(ConfigurationError, match="restricted process token"):
        configuration._atomic_write_yaml(path, {"profile": "power"})

    assert path.read_bytes() == original
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


def test_store_surfaces_restricted_token_and_preserves_file_access(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    original = b"existing database bytes"
    path.write_bytes(original)

    def restricted_acl(_path: Path, *, directory: bool) -> bool:
        del directory
        raise RestrictedWindowsTokenError(
            "owner-only Windows ACL cannot be changed from a restricted process token"
        )

    with pytest.raises(PermissionError, match="restricted process token"):
        restrict_path_permissions(
            path,
            directory=False,
            is_windows=True,
            link_checker=lambda _path: False,
            windows_acl=restricted_acl,
        )

    assert path.read_bytes() == original


def test_canary_restricted_token_removes_empty_destination_without_copying_auth(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "auth.json"
    source.write_bytes(b'{"token":"private"}')
    destination = tmp_path / "isolated" / "auth.json"
    monkeypatch.setattr(configuration, "restrict_private_directory", lambda _path: None)
    monkeypatch.setattr(
        configuration,
        "restrict_private_file",
        lambda _path: (_ for _ in ()).throw(
            ConfigurationError(
                "owner-only Windows ACL cannot be changed from a restricted process token"
            )
        ),
    )

    with pytest.raises(ConfigurationError, match="restricted process token"):
        _copy_bounded_auth(source, destination, host="Codex")

    assert source.read_bytes() == b'{"token":"private"}'
    assert not destination.exists()


@pytest.mark.skipif(os.name != "nt", reason="requires a real Windows process token")
def test_real_restricted_token_never_changes_an_unverified_acl(
    tmp_path: Path,
) -> None:
    if not current_process_token_is_restricted():
        pytest.skip("current Windows process token is unrestricted")
    path = tmp_path / "restricted-token.txt"
    original = b"still accessible"
    path.write_bytes(original)
    original_sddl = windows_acl.read_windows_sddl(path)

    try:
        accepted = restrict_windows_acl(path, is_windows=True)
    except RestrictedWindowsTokenError as exc:
        assert "restricted process token" in str(exc)
    else:
        assert accepted is True

    assert path.read_bytes() == original
    assert windows_acl.read_windows_sddl(path) == original_sddl
