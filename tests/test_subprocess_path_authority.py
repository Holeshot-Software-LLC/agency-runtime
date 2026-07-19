"""Child-process re-attestation for Codex host-private namespaces."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import executable_namespace, path_authority, private_paths
from agency_runtime.core.private_paths import PrivateDirectoryIdentity

_THREAD_ID = "019f4c7c-64ea-7650-a414-2680b0efabc6"
_OTHER_THREAD_ID = "019f4c7c-64ea-7650-a414-2680b0efabc7"


class _Guard:
    def __init__(self, path: Path, *, current: bool = True) -> None:
        self.path = path
        self.current = current
        self.closed = 0

    def is_current(self) -> bool:
        return self.current

    def close(self) -> None:
        self.closed += 1


@pytest.fixture(autouse=True)
def _preserve_authorities() -> None:
    process_authorities = dict(path_authority._AUTHORITIES)
    host_authorities = dict(private_paths._HOST_AUTHORITIES)
    path_authority._AUTHORITIES.clear()
    private_paths._HOST_AUTHORITIES.clear()
    yield
    path_authority._AUTHORITIES.clear()
    path_authority._AUTHORITIES.update(process_authorities)
    private_paths._HOST_AUTHORITIES.clear()
    private_paths._HOST_AUTHORITIES.update(host_authorities)


def _allocation_root(home: Path, *, thread_id: str = _THREAD_ID) -> tuple[Path, Path]:
    parent = home / ".codex" / "visualizations" / "2026" / "07" / "16" / "root-task"
    root = parent / f".a-{thread_id.replace('-', '')}-pytest-c-{'a' * 24}"
    (root / "pytest-of-user" / "case").mkdir(parents=True)
    return parent, root


def _configure_success(
    monkeypatch: pytest.MonkeyPatch,
    parent: Path,
    root: Path,
) -> tuple[_Guard, _Guard]:
    parent_guard = _Guard(parent)
    root_guard = _Guard(root)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "_pin_codex_host_private_parent",
        lambda *_args, **_kwargs: parent_guard,
    )
    monkeypatch.setattr(
        private_paths,
        "windows_directory_prevents_untrusted_writes",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: root_guard,
    )
    return parent_guard, root_guard


def test_child_reattests_only_the_thread_bound_random_allocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, root = _allocation_root(tmp_path)
    target = root / "pytest-of-user" / "case" / "agency.db"
    parent_guard, root_guard = _configure_success(monkeypatch, parent, root)

    assert private_paths.reattest_codex_host_private_path(
        target,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert private_paths.reattest_codex_host_private_path(
        target.parent,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert path_authority.private_path_authority_covers(target)
    assert private_paths._HOST_AUTHORITIES[root].parent_guard is parent_guard
    assert private_paths._HOST_AUTHORITIES[root].guard is root_guard
    assert parent_guard.closed == root_guard.closed == 0


def test_non_codex_paths_never_invoke_the_host_root_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(private_paths, "_host_authority_for", lambda _path: None)

    def unexpected(*_args: object, **_kwargs: object) -> _Guard:
        raise AssertionError("ordinary runtime paths must not scan Codex task roots")

    monkeypatch.setattr(private_paths, "_pin_codex_host_private_parent", unexpected)

    assert not private_paths.reattest_codex_host_private_path(
        tmp_path / ".agency-runtime" / "state" / "agency.db",
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )


@pytest.mark.parametrize(
    "name",
    [
        f".a-{_OTHER_THREAD_ID.replace('-', '')}-pytest-c-{'a' * 24}",
        f".a-{_THREAD_ID.replace('-', '')}-pytest-c-{'A' * 24}",
        f".a-{_THREAD_ID.replace('-', '')}-too-long-prefix-{'a' * 24}",
        f".a-{_THREAD_ID.replace('-', '')}--{'a' * 24}",
        f".a-{_THREAD_ID.replace('-', '')}-pytest-c-{'g' * 24}",
        f".a-{_THREAD_ID.replace('-', '')}-pytest-c-{'a' * 23}",
        f".a-{_THREAD_ID.replace('-', '')}-{'a' * 24}",
        f".a-{_THREAD_ID.replace('-', '')}-bad@name-{'a' * 24}",
    ],
)
def test_child_rejects_unbound_or_malformed_allocation_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    parent = tmp_path / ".codex" / "visualizations" / "2026" / "07" / "16" / "root"
    root = parent / name
    root.mkdir(parents=True)
    parent_guard = _Guard(parent)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "_pin_codex_host_private_parent",
        lambda *_args, **_kwargs: parent_guard,
    )

    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert parent_guard.closed == 1


def test_child_rejects_wrong_root_and_invalid_host_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, root = _allocation_root(tmp_path)
    parent_guard = _Guard(parent)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "_pin_codex_host_private_parent",
        lambda *_args, **_kwargs: parent_guard,
    )

    assert not private_paths.reattest_codex_host_private_path(
        parent,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert parent_guard.closed == 0
    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": "not-a-uuid"},
    )
    assert parent_guard.closed == 0


def test_child_rejects_missing_host_attestation_and_unpinnable_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, root = _allocation_root(tmp_path)
    del parent
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)

    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_THREAD_ID": _THREAD_ID},
    )
    monkeypatch.setattr(
        private_paths,
        "_pin_codex_host_private_parent",
        lambda *_args, **_kwargs: None,
    )
    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )

    def fail_pin(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("changed root")

    monkeypatch.setattr(private_paths, "_pin_codex_host_private_parent", fail_pin)
    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", False)
    assert not private_paths.reattest_codex_host_private_path(root, home_dir=tmp_path)


def test_child_rejects_a_pinned_parent_that_does_not_contain_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _parent, root = _allocation_root(tmp_path)
    unrelated_guard = _Guard(tmp_path / "unrelated")
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "_pin_codex_host_private_parent",
        lambda *_args, **_kwargs: unrelated_guard,
    )

    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert unrelated_guard.closed == 1


def test_child_rejects_a_pinned_parent_equal_to_the_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _parent, root = _allocation_root(tmp_path)
    target_guard = _Guard(root)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "_pin_codex_host_private_parent",
        lambda *_args, **_kwargs: target_guard,
    )

    assert not private_paths.reattest_codex_host_private_path(
        root,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert target_guard.closed == 1


@pytest.mark.parametrize(
    "failure",
    [
        "acl",
        "link",
        "file",
        "inode",
        "missing_guard",
        "guard",
        "identity",
        "descendant",
        "lstat",
    ],
)
def test_child_rejects_acl_link_handle_and_descendant_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    parent, root = _allocation_root(tmp_path)
    target = root / "pytest-of-user" / "case" / "agency.db"
    parent_guard, root_guard = _configure_success(monkeypatch, parent, root)
    original_lstat = private_paths.os.lstat
    if failure == "acl":
        monkeypatch.setattr(
            private_paths,
            "windows_directory_prevents_untrusted_writes",
            lambda *_args, **_kwargs: False,
        )
    elif failure == "link":
        monkeypatch.setattr(
            private_paths,
            "metadata_is_link_or_reparse_point",
            lambda _metadata: True,
        )
    elif failure in {"file", "inode"}:
        metadata = original_lstat(root)
        replacement = SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600 if failure == "file" else metadata.st_mode,
            st_ino=metadata.st_ino if failure == "file" else 0,
            st_dev=metadata.st_dev,
            st_file_attributes=0,
        )
        monkeypatch.setattr(
            private_paths.os,
            "lstat",
            lambda path: replacement if Path(path) == root else original_lstat(path),
        )
    elif failure == "missing_guard":
        monkeypatch.setattr(
            private_paths,
            "open_windows_directory_guard",
            lambda *_args, **_kwargs: None,
        )
    elif failure == "guard":
        root_guard.current = False
    elif failure == "identity":
        monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: False)
    elif failure == "lstat":
        monkeypatch.setattr(
            private_paths.os,
            "lstat",
            lambda _path: (_ for _ in ()).throw(OSError("identity unavailable")),
        )
    else:
        monkeypatch.setattr(
            private_paths,
            "_host_descendant_namespace_is_private",
            lambda *_args: False,
        )

    assert not private_paths.reattest_codex_host_private_path(
        target,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert parent_guard.closed == 1
    if failure in {"guard", "identity", "descendant"}:
        assert root_guard.closed == 1


def test_child_uses_default_home_and_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, root = _allocation_root(tmp_path)
    target = root / "pytest-of-user" / "case"
    _configure_success(monkeypatch, parent, root)
    monkeypatch.setattr(private_paths.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("CODEX_SHELL", "1")
    monkeypatch.setenv("CODEX_THREAD_ID", _THREAD_ID)

    assert private_paths.reattest_codex_host_private_path(target)


@pytest.mark.parametrize("existing_current", [True, False])
def test_child_closes_racing_receipts_and_reuses_or_replaces_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing_current: bool,
) -> None:
    parent, root = _allocation_root(tmp_path)
    target = root / "pytest-of-user" / "case"
    parent_guard, new_root_guard = _configure_success(monkeypatch, parent, root)
    existing_root_guard = _Guard(root, current=existing_current)
    existing_parent_guard = _Guard(parent, current=existing_current)
    metadata = os.lstat(root)
    existing = PrivateDirectoryIdentity(
        root,
        int(metadata.st_dev),
        int(metadata.st_ino),
        guard=existing_root_guard,
        parent_guard=existing_parent_guard,
    )
    monkeypatch.setattr(private_paths, "_host_authority_for", lambda _path: None)

    def open_and_race(*_args: object, **_kwargs: object) -> _Guard:
        private_paths._HOST_AUTHORITIES[root] = existing
        return new_root_guard

    monkeypatch.setattr(private_paths, "open_windows_directory_guard", open_and_race)

    assert private_paths.reattest_codex_host_private_path(
        target,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    if existing_current:
        assert private_paths._HOST_AUTHORITIES[root] is existing
        assert parent_guard.closed == new_root_guard.closed == 1
        assert existing_root_guard.closed == existing_parent_guard.closed == 0
    else:
        assert private_paths._HOST_AUTHORITIES[root] is not existing
        assert parent_guard.closed == new_root_guard.closed == 0
        assert existing_root_guard.closed == existing_parent_guard.closed == 1


def test_child_revokes_authority_when_identity_drifts_after_registration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, root = _allocation_root(tmp_path)
    target = root / "pytest-of-user" / "case"
    parent_guard, root_guard = _configure_success(monkeypatch, parent, root)
    checks = iter((True, False))
    monkeypatch.setattr(
        private_paths,
        "_identity_is_current",
        lambda _identity: next(checks),
    )

    assert not private_paths.reattest_codex_host_private_path(
        target,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert root not in private_paths._HOST_AUTHORITIES
    assert root_guard.closed == parent_guard.closed == 1


def test_child_replaces_a_racing_stale_receipt_without_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, root = _allocation_root(tmp_path)
    target = root / "pytest-of-user" / "case"
    _configure_success(monkeypatch, parent, root)
    metadata = os.lstat(root)
    existing = PrivateDirectoryIdentity(
        root,
        int(metadata.st_dev),
        int(metadata.st_ino),
    )
    monkeypatch.setattr(private_paths, "_host_authority_for", lambda _path: None)
    original_open = private_paths.open_windows_directory_guard

    def open_and_race(*args: object, **kwargs: object) -> _Guard:
        private_paths._HOST_AUTHORITIES[root] = existing
        return original_open(*args, **kwargs)

    monkeypatch.setattr(private_paths, "open_windows_directory_guard", open_and_race)
    monkeypatch.setattr(
        private_paths,
        "_identity_is_current",
        lambda identity: identity is not existing,
    )

    assert private_paths.reattest_codex_host_private_path(
        target,
        home_dir=tmp_path,
        environment={"CODEX_SHELL": "1", "CODEX_THREAD_ID": _THREAD_ID},
    )
    assert private_paths._HOST_AUTHORITIES[root] is not existing


def test_lazy_resolver_is_non_recursive_and_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Path] = []

    def resolve(path: Path) -> bool:
        calls.append(path)
        assert not path_authority.private_path_authority_covers(path / "nested")
        return True

    monkeypatch.setattr(private_paths, "reattest_codex_host_private_path", resolve)
    assert path_authority.private_path_authority_covers(tmp_path / "candidate")
    assert calls == [tmp_path / "candidate"]

    monkeypatch.setattr(
        private_paths,
        "reattest_codex_host_private_path",
        lambda _path: (_ for _ in ()).throw(RuntimeError("attestation failed")),
    )
    assert not path_authority.private_path_authority_covers(tmp_path / "rejected")


def test_executable_namespace_accepts_only_default_live_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "private-bin"
    parent.mkdir()
    monkeypatch.setattr(
        executable_namespace,
        "private_path_authority_covers",
        lambda path: path == parent,
    )
    assert executable_namespace.executable_namespace_is_trusted(parent, is_windows=True)

    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=True,
        windows_acl_probe=lambda _path, _final: False,
    )

    monkeypatch.setattr(
        executable_namespace,
        "private_path_authority_covers",
        lambda _path: False,
    )
    assert not executable_namespace.executable_namespace_is_trusted(
        tmp_path / "missing-bin",
        is_windows=True,
    )
