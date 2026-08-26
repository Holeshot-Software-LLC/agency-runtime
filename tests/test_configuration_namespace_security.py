"""Cross-account configuration namespace and file-privacy regressions."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import configuration_persistence as persistence
from agency_runtime.core import windows_acl
from agency_runtime.core.configuration import read_config_state
from agency_runtime.core.configuration_contracts import ConfigurationError


def _directory_metadata(*, mode: int, uid: int = 1001) -> SimpleNamespace:
    return SimpleNamespace(
        st_mode=stat.S_IFDIR | mode,
        st_uid=uid,
        st_file_attributes=0,
    )


def test_posix_config_namespace_accepts_0755_but_rejects_writable_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "shared" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    monkeypatch.setattr(persistence.os, "lstat", metadata.__getitem__)
    monkeypatch.setattr(
        persistence,
        "_posix_directory_has_default_acl",
        lambda _path: False,
    )

    assert persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )

    metadata[target.parent] = _directory_metadata(mode=0o777)
    assert not persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )
    metadata[target.parent] = _directory_metadata(mode=0o775)
    assert not persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )


def test_posix_config_namespace_rejects_genuine_overflow_uid_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "overflow-owned" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    metadata = {candidate: _directory_metadata(mode=0o755, uid=0) for candidate in chain}
    metadata[target.parent] = _directory_metadata(mode=0o700, uid=65534)
    monkeypatch.setattr(persistence.os, "lstat", metadata.__getitem__)
    monkeypatch.setattr(
        persistence,
        "_posix_directory_has_default_acl",
        lambda _path: False,
    )

    assert not persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )


def test_posix_config_namespace_rejects_replaceable_ancestor_and_default_acl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "owned" / "config" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    acl_paths: set[Path] = set()
    monkeypatch.setattr(persistence.os, "lstat", metadata.__getitem__)
    monkeypatch.setattr(
        persistence,
        "_posix_directory_has_default_acl",
        lambda candidate: candidate in acl_paths,
    )

    replaceable = chain[-2]
    metadata[replaceable] = _directory_metadata(mode=0o777)
    assert not persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )

    metadata[replaceable] = _directory_metadata(mode=0o1777)
    assert persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )

    acl_paths.add(target.parent)
    assert not persistence.config_namespace_is_trusted(
        target,
        is_windows=False,
        effective_uid=1001,
    )


def test_windows_config_namespace_uses_mutation_only_final_parent_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "shared" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    calls: list[tuple[Path, bool, bool]] = []
    monkeypatch.setattr(persistence.os, "lstat", metadata.__getitem__)

    def safe(candidate: Path, final_parent: bool, prospective_child: bool) -> bool:
        calls.append((candidate, final_parent, prospective_child))
        return True

    assert persistence.config_namespace_is_trusted(
        target,
        is_windows=True,
        windows_acl_probe=safe,
    )
    assert calls[-1] == (target.parent, True, False)

    assert not persistence.config_namespace_is_trusted(
        target,
        is_windows=True,
        windows_acl_probe=lambda candidate, final, prospective: candidate != target.parent,
    )


def test_windows_config_namespace_rechecks_effective_token_and_every_dacl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "shared" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    sid_checks = 0
    restricted_checks = 0
    observed: list[Path] = []
    monkeypatch.setattr(persistence.os, "lstat", metadata.__getitem__)
    monkeypatch.setattr(persistence, "private_path_authority_covers", lambda _path: False)

    def current_sid(*, is_windows: bool) -> str:
        nonlocal sid_checks
        assert is_windows
        sid_checks += 1
        return f"S-1-5-21-{sid_checks}"

    def restricted_sids(*, is_windows: bool) -> frozenset[str]:
        nonlocal restricted_checks
        assert is_windows
        restricted_checks += 1
        return frozenset({f"S-1-5-5-{restricted_checks}-1"})

    def read_sddl(candidate: Path) -> str:
        observed.append(candidate)
        index = chain.index(candidate) + 1
        sid = f"S-1-5-21-{index}"
        return f"O:{sid}D:P(A;OICI;FA;;;{sid})"

    monkeypatch.setattr(windows_acl, "current_process_user_sid", current_sid)
    monkeypatch.setattr(windows_acl, "current_process_restricted_sids", restricted_sids)
    monkeypatch.setattr(windows_acl, "read_windows_sddl", read_sddl)

    assert persistence.config_namespace_is_trusted(target, is_windows=True)

    assert sid_checks == len(chain)
    assert restricted_checks == len(chain)
    assert observed == [*chain]


def test_windows_config_namespace_fails_closed_when_token_probe_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "shared" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    monkeypatch.setattr(persistence.os, "lstat", metadata.__getitem__)
    monkeypatch.setattr(persistence, "private_path_authority_covers", lambda _path: False)
    monkeypatch.setattr(
        persistence,
        "windows_directory_prevents_untrusted_writes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("token denied")),
    )

    assert not persistence.config_namespace_is_trusted(target, is_windows=True)


def test_missing_config_parent_requires_a_safe_creation_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "missing" / "nested" / "agency.yaml"
    chain = persistence._directory_chain(target.parent)
    existing = set(chain[:-2])
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in existing}

    def lstat(candidate: Path) -> SimpleNamespace:
        try:
            return metadata[candidate]
        except KeyError:
            raise FileNotFoundError(candidate) from None

    calls: list[tuple[Path, bool, bool]] = []
    monkeypatch.setattr(persistence.os, "lstat", lstat)

    assert persistence.config_namespace_is_trusted(
        target,
        is_windows=True,
        windows_acl_probe=lambda candidate, final, prospective: (
            calls.append((candidate, final, prospective)) or True
        ),
    )
    assert calls[-1] == (chain[-3], False, True)


def test_assert_config_namespace_fails_closed() -> None:
    with pytest.raises(ConfigurationError, match="cross-account"):
        persistence.assert_config_namespace(
            Path("unsafe/agency.yaml"),
            is_windows=True,
            windows_acl_probe=lambda *_args: False,
        )


def test_existing_posix_config_is_hardened_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    observed: list[Path] = []
    monkeypatch.setattr(
        persistence.os,
        "geteuid",
        lambda: int(path.lstat().st_uid),
        raising=False,
    )

    assert persistence._ensure_config_file_private(
        path,
        restrict=lambda candidate, **_kwargs: observed.append(candidate) or True,
        path_check=lambda _path: False,
        is_windows=False,
    )
    assert observed == [path]


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode regression")
@pytest.mark.parametrize("mode", [0o777, 0o775])
def test_public_config_read_rejects_writable_posix_parent(
    tmp_path: Path,
    mode: int,
) -> None:
    parent = tmp_path / "shared"
    parent.mkdir(mode=mode)
    parent.chmod(mode)

    with pytest.raises(ConfigurationError, match="cross-account"):
        read_config_state(parent / "agency.yaml")


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode regression")
def test_public_config_read_hardens_current_user_file(tmp_path: Path) -> None:
    parent = tmp_path / "shared"
    parent.mkdir(mode=0o755)
    path = parent / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    path.chmod(0o644)

    assert read_config_state(path).persisted["profile"] == "standard"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
