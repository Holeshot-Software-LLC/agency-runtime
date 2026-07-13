"""Windows DACL safety regressions for restricted process tokens."""

from __future__ import annotations

import os
from pathlib import Path

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

    assert (
        restrict_windows_acl(
            Path("private-directory"),
            directory=True,
            is_windows=True,
            token_restriction_probe=lambda: False,
            acl_applier=lambda path, *, directory: calls.append((path, directory)) or True,
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

    assert restrict_windows_acl(
        Path("private"),
        is_windows=True,
        acl_privacy_probe=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("denied")),
        token_restriction_probe=lambda: calls.append("token") or False,
        acl_applier=lambda *_args, **_kwargs: calls.append("mutation") or True,
    )
    assert calls == ["token", "mutation"]


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
    monkeypatch.setattr(windows_acl, "_read_windows_sddl", values.get)

    assert windows_acl._owner_only_acl_is_present(parent, directory=True)
    assert windows_acl._owner_only_acl_is_present(child, directory=False)
    assert windows_acl._owner_only_acl_is_present(protected_file, directory=False)
    assert windows_acl._owner_only_acl_is_present(inherited_directory, directory=True)
    assert not windows_acl._owner_only_acl_is_present(root, directory=True)

    values[child] = f"O:{owner}D:AI(A;ID;FR;;;{owner})"
    assert not windows_acl._owner_only_acl_is_present(child, directory=False)
    values[child] = "malformed"
    assert not windows_acl._owner_only_acl_is_present(child, directory=False)


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


def test_configuration_restricted_token_preserves_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    original = b"profile: standard\n"
    path.write_bytes(original)
    monkeypatch.setattr(configuration, "_IS_WINDOWS", True)
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

    if windows_acl._owner_only_acl_is_present(path, directory=False):
        assert restrict_windows_acl(path, is_windows=True)
    else:
        with pytest.raises(RestrictedWindowsTokenError, match="restricted process token"):
            restrict_windows_acl(path, is_windows=True)

    assert path.read_bytes() == original
