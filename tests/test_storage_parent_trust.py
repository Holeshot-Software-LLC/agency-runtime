"""Cross-account SQLite parent and pathname-open trust regressions."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import windows_acl
from agency_runtime.core.store import security as store_security
from agency_runtime.core.store import sqlite as sqlite_store
from agency_runtime.core.store.initialization_lock import initialization_lock_path
from agency_runtime.core.store.sqlite import Store

_CURRENT_SID = "S-1-5-21-1001"
_FOREIGN_SID = "S-1-5-21-2002"


@pytest.mark.parametrize(
    ("sddl", "final_parent", "expected"),
    [
        (f"O:{_CURRENT_SID}D:P(A;OICI;FA;;;{_CURRENT_SID})", True, True),
        (f"O:{_FOREIGN_SID}D:P(A;OICI;FA;;;{_FOREIGN_SID})", True, False),
        (f"O:{_CURRENT_SID}D:P(OD;OICI;FA;;;{_FOREIGN_SID})", True, True),
        (f"O:{_CURRENT_SID}D:P(A;OICI;GW;;;{_FOREIGN_SID})", True, False),
        (f"O:{_CURRENT_SID}D:(A;;GW;;;{_FOREIGN_SID})", False, True),
        (f"O:{_CURRENT_SID}D:(A;;DC;;;{_FOREIGN_SID})", False, True),
        (f"O:{_CURRENT_SID}D:(A;;DT;;;{_FOREIGN_SID})", False, False),
        (f"O:{_CURRENT_SID}D:(A;;0x00000040;;;{_FOREIGN_SID})", False, False),
        (f"O:{_CURRENT_SID}D:(A;;0x00010000;;;{_FOREIGN_SID})", False, False),
        (f"O:{_CURRENT_SID}D:(A;IO;FA;;;{_FOREIGN_SID})", False, True),
        (f"O:{_CURRENT_SID}D:(XA;;FA;;;{_FOREIGN_SID})", False, False),
        (f"O:{_CURRENT_SID}D:(XA;;FR;;;{_FOREIGN_SID})", False, True),
        (f"O:{_CURRENT_SID}D:(A;;ZZ;;;{_FOREIGN_SID})", False, False),
        (f"O:{_CURRENT_SID}D:(A;;KA;;;{_FOREIGN_SID})", False, False),
        (f"O:{_CURRENT_SID}D:NO_ACCESS_CONTROL", True, False),
        (f"O:{_CURRENT_SID}D:NO_ACCESS_CONTROL", False, False),
        ("O:SYD:P(A;OICI;FA;;;SY)", True, False),
        ("O:SYD:P(A;OICI;FA;;;SY)", False, True),
    ],
)
def test_windows_acl_distinguishes_final_mutation_from_ancestor_substitution(
    sddl: str,
    final_parent: bool,
    expected: bool,
) -> None:
    assert (
        windows_acl.windows_directory_prevents_untrusted_writes(
            Path("state"),
            is_windows=True,
            sddl_reader=lambda _path: sddl,
            current_sid_reader=lambda: _CURRENT_SID,
            final_parent=final_parent,
        )
        is expected
    )


def test_windows_config_parent_can_inherit_read_but_not_mutation() -> None:
    readonly = f"O:{_CURRENT_SID}D:P(A;OICI;FR;;;{_FOREIGN_SID})"
    writable = f"O:{_CURRENT_SID}D:P(A;OICI;GW;;;{_FOREIGN_SID})"

    assert windows_acl.windows_directory_prevents_untrusted_writes(
        Path("config"),
        is_windows=True,
        sddl_reader=lambda _path: readonly,
        current_sid_reader=lambda: _CURRENT_SID,
        final_parent=True,
        allow_inheritable_read=True,
    )
    assert not windows_acl.windows_directory_prevents_untrusted_writes(
        Path("config"),
        is_windows=True,
        sddl_reader=lambda _path: writable,
        current_sid_reader=lambda: _CURRENT_SID,
        final_parent=True,
        allow_inheritable_read=True,
    )


@pytest.mark.parametrize(
    ("ace", "expected"),
    [
        (f"(A;;GW;;;{_FOREIGN_SID})", False),
        (f"(A;;DC;;;{_FOREIGN_SID})", False),
        (f"(A;;LC;;;{_FOREIGN_SID})", False),
        (f"(A;;FW;;;{_FOREIGN_SID})", False),
        (f"(A;;0x00000002;;;{_FOREIGN_SID})", False),
        (f"(A;;0x00000004;;;{_FOREIGN_SID})", False),
        (f"(A;;0x40000000;;;{_FOREIGN_SID})", False),
        (f"(A;CI;GW;;;{_FOREIGN_SID})", False),
        (f"(A;CIIO;FA;;;{_FOREIGN_SID})", False),
        (f"(A;OICIIO;FA;;;{_FOREIGN_SID})", False),
        (f"(A;OICI;FR;;;{_FOREIGN_SID})", True),
        (f"(A;;DT;;;{_FOREIGN_SID})", False),
        ("(A;OICI;FA;;;SY)", True),
        (f"(A;OICI;FA;;;{_CURRENT_SID})", True),
    ],
)
def test_windows_creation_boundary_rejects_inheritable_mutation(
    ace: str,
    expected: bool,
) -> None:
    assert (
        windows_acl.windows_directory_prevents_untrusted_writes(
            Path("state"),
            is_windows=True,
            sddl_reader=lambda _path: f"O:{_CURRENT_SID}D:P{ace}",
            current_sid_reader=lambda: _CURRENT_SID,
            final_parent=False,
            prospective_child=True,
        )
        is expected
    )
    assert not windows_acl.windows_directory_prevents_untrusted_writes(
        Path("state"),
        is_windows=True,
        sddl_reader=lambda _path: f"O:{_CURRENT_SID}D:P{ace}",
        current_sid_reader=lambda: _CURRENT_SID,
        final_parent=True,
        prospective_child=True,
    )


def _directory_metadata(*, mode: int, uid: int = 1001) -> SimpleNamespace:
    return SimpleNamespace(
        st_mode=stat.S_IFDIR | mode,
        st_uid=uid,
        st_file_attributes=0,
    )


def test_posix_parent_trust_requires_private_or_sticky_protected_chain(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    os_facade,
) -> None:
    parent = tmp_path / "private"
    chain = store_security._directory_chain(parent)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    metadata[parent] = _directory_metadata(mode=0o700)
    monkeypatch.setattr(
        store_security,
        "os",
        os_facade(
            store_security.os,
            name="posix",
            missing=frozenset({"getxattr"}),
        ),
    )
    monkeypatch.setattr(store_security.os, "lstat", metadata.__getitem__)

    assert store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )

    shared = chain[-2]
    metadata[shared] = _directory_metadata(mode=0o777)
    assert not store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )

    metadata[shared] = _directory_metadata(mode=0o1777)
    assert store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )

    metadata[shared] = _directory_metadata(mode=0o755, uid=2002)
    assert not store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )
    metadata[shared] = _directory_metadata(mode=0o1777, uid=2002)
    assert not store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )
    metadata[shared] = _directory_metadata(mode=0o755)

    metadata[parent] = _directory_metadata(mode=0o700, uid=2002)
    assert not store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )
    metadata[parent] = _directory_metadata(mode=0o720)
    assert not store_security.storage_parent_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1001,
    )


def test_parent_chain_and_trust_probes_fail_closed_on_unknown_objects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    store_security.assert_storage_parent_chain(missing, allow_missing=True)
    with pytest.raises(PermissionError, match="does not exist"):
        store_security.assert_storage_parent_chain(missing, allow_missing=False)

    monkeypatch.setattr(
        store_security.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(OSError("denied")),
    )
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=False,
        effective_uid=1001,
    )


def test_parent_trust_rejects_non_directory_and_unknown_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    chain = store_security._directory_chain(tmp_path)
    metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
    metadata[tmp_path] = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o600,
        st_uid=1001,
        st_file_attributes=0,
    )
    monkeypatch.setattr(store_security.os, "lstat", metadata.__getitem__)
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=False,
        effective_uid=1001,
    )

    metadata[tmp_path] = _directory_metadata(mode=0o700)
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=True,
        windows_acl_probe=lambda *_args: (_ for _ in ()).throw(OSError("denied")),
    )
    monkeypatch.delattr(store_security.os, "geteuid", raising=False)
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=False,
        effective_uid=None,
    )


def test_storage_file_trust_requires_owner_mode_identity_and_single_link(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o644,
        st_uid=1001,
        st_dev=1,
        st_ino=2,
        st_nlink=1,
        st_file_attributes=0,
    )
    monkeypatch.setattr(store_security.os, "lstat", lambda _path: metadata)
    monkeypatch.setattr(
        store_security.os,
        "geteuid",
        lambda: int(metadata.st_uid),
        raising=False,
    )
    assert not store_security.storage_file_is_trusted(tmp_path, is_windows=False)
    metadata.st_mode = stat.S_IFREG | 0o600
    assert store_security.storage_file_is_trusted(tmp_path, is_windows=False)
    metadata.st_mode = stat.S_IFREG | 0o666
    assert not store_security.storage_file_is_trusted(tmp_path, is_windows=False)
    metadata.st_mode = stat.S_IFREG | 0o600
    metadata.st_nlink = 2
    assert not store_security.storage_file_is_trusted(tmp_path, is_windows=False)
    metadata.st_nlink = 1
    metadata.st_ino = 0
    assert not store_security.storage_file_is_trusted(tmp_path, is_windows=False)
    metadata.st_ino = 2
    monkeypatch.setattr(store_security.os, "geteuid", lambda: int(metadata.st_uid) + 1)
    assert not store_security.storage_file_is_trusted(tmp_path, is_windows=False)


def test_posix_final_parent_rejects_a_default_acl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = _directory_metadata(mode=0o700, uid=1001)
    monkeypatch.setattr(store_security, "_directory_chain", lambda _path: (tmp_path,))
    monkeypatch.setattr(store_security.os, "lstat", lambda _path: metadata)
    monkeypatch.setattr(
        store_security.os,
        "getxattr",
        lambda *_args, **_kwargs: b"inherited acl",
        raising=False,
    )

    assert store_security.posix_directory_has_default_acl(tmp_path)
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=False,
        effective_uid=1001,
    )


def test_windows_parent_trust_checks_every_ancestor_and_marks_only_final(
    tmp_path: Path,
) -> None:
    observed: list[tuple[Path, bool]] = []

    assert store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=True,
        windows_acl_probe=lambda path, final, _prospective: observed.append((path, final)) or True,
    )
    assert observed
    assert [final for _path, final in observed].count(True) == 1
    assert observed[-1] == (tmp_path, True)

    rejected = observed[-2][0]
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=True,
        windows_acl_probe=lambda path, _final, _prospective: path != rejected,
    )


def test_windows_parent_trust_marks_only_creation_boundary_as_prospective(
    tmp_path: Path,
) -> None:
    observed: list[tuple[Path, bool, bool]] = []
    assert store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=True,
        final_parent=False,
        prospective_child=True,
        windows_acl_probe=lambda path, final, prospective: (
            observed.append((path, final, prospective)) or True
        ),
    )
    assert observed
    assert all(not final for _path, final, _prospective in observed)
    assert [prospective for _path, _final, prospective in observed].count(True) == 1
    assert observed[-1] == (tmp_path, False, True)
    assert not store_security.storage_parent_is_trusted(
        tmp_path,
        is_windows=True,
        final_parent=True,
        prospective_child=True,
        windows_acl_probe=lambda *_args: True,
    )


def test_windows_private_authority_short_circuits_acl_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        store_security,
        "private_path_authority_covers",
        lambda _path: True,
    )

    assert store_security.storage_parent_is_trusted(tmp_path, is_windows=True)


def test_windows_parent_trust_marks_relative_final_after_normalization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "relative"
    parent.mkdir()
    monkeypatch.chdir(tmp_path)
    observed: list[tuple[Path, bool]] = []
    assert store_security.storage_parent_is_trusted(
        Path("relative"),
        is_windows=True,
        windows_acl_probe=lambda path, final, _prospective: observed.append((path, final)) or True,
    )
    assert observed[-1] == (parent, True)


def test_creation_boundary_rejects_nonsticky_shared_parent_before_mkdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    metadata = _directory_metadata(mode=0o777)
    observed: list[dict[str, object]] = []
    monkeypatch.setattr(
        store_security,
        "storage_parent_is_trusted",
        lambda *_a, **kwargs: observed.append(kwargs) or True,
    )
    monkeypatch.setattr(store_security.os, "lstat", lambda _path: metadata)
    monkeypatch.setattr(
        store_security,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    assert not store_security.storage_creation_boundary_is_trusted(
        tmp_path,
        tmp_path / "new",
        is_windows=False,
    )

    monkeypatch.setattr(
        store_security,
        "storage_parent_is_trusted",
        lambda *_a, **kwargs: observed.append(kwargs) or True,
    )
    assert not store_security.storage_creation_boundary_is_trusted(
        tmp_path,
        tmp_path / "new",
        is_windows=False,
    )

    metadata.st_mode = stat.S_IFDIR | 0o1777
    assert store_security.storage_creation_boundary_is_trusted(
        tmp_path,
        tmp_path / "new",
        is_windows=False,
    )
    metadata.st_mode = stat.S_IFDIR | 0o777
    assert store_security.storage_creation_boundary_is_trusted(
        tmp_path,
        tmp_path,
        is_windows=False,
    )
    assert store_security.storage_creation_boundary_is_trusted(
        tmp_path,
        tmp_path / "new",
        is_windows=True,
    )
    assert observed[-1]["final_parent"] is False
    assert observed[-1]["prospective_child"] is True
    assert store_security.storage_creation_boundary_is_trusted(
        tmp_path,
        tmp_path,
        is_windows=True,
    )
    assert observed[-1]["prospective_child"] is False


def test_private_parent_creation_hardens_each_component_before_descending(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "one" / "two"
    mkdir_calls: list[tuple[Path, int]] = []
    repairs: list[Path] = []
    real_mkdir = store_security.os.mkdir

    def mkdir(path: Path, mode: int) -> None:
        mkdir_calls.append((path, mode))
        real_mkdir(path, mode)

    monkeypatch.setattr(store_security.os, "mkdir", mkdir)
    monkeypatch.setattr(
        store_security,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        store_security,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        store_security,
        "restrict_path_permissions",
        lambda path, **_kwargs: repairs.append(path),
    )

    assert store_security.create_private_storage_parent(
        tmp_path,
        parent,
        is_windows=False,
    )
    assert mkdir_calls == [
        (tmp_path / "one", stat.S_IRWXU),
        (parent, stat.S_IRWXU),
    ]
    assert repairs == [tmp_path / "one", parent]


def test_private_parent_creation_stops_before_unsafe_intermediate_repair(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "one" / "two"
    repairs: list[Path] = []
    monkeypatch.setattr(
        store_security,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        store_security,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        store_security,
        "restrict_path_permissions",
        lambda path, **_kwargs: repairs.append(path),
    )

    with pytest.raises(PermissionError, match="unsafe before permission repair"):
        store_security.create_private_storage_parent(
            tmp_path,
            parent,
            is_windows=False,
        )
    assert not (tmp_path / "one").exists()
    assert not parent.exists()
    assert repairs == []


def test_private_parent_creation_rolls_back_every_unchanged_component(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "one" / "two"
    trust_results = iter((True, True, False))
    monkeypatch.setattr(
        store_security,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        store_security,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: next(trust_results),
    )
    monkeypatch.setattr(store_security, "restrict_path_permissions", lambda *_args, **_kwargs: None)

    with pytest.raises(PermissionError, match="unsafe before permission repair"):
        store_security.create_private_storage_parent(tmp_path, parent, is_windows=False)

    assert not (tmp_path / "one").exists()


def test_private_parent_creation_rejects_path_outside_validated_boundary(
    tmp_path: Path,
) -> None:
    with pytest.raises(PermissionError, match="outside its validated boundary"):
        store_security.create_private_storage_parent(
            tmp_path / "nested",
            tmp_path,
            is_windows=False,
        )


def test_explicit_untrusted_parent_fails_before_database_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "shared"
    parent.mkdir()
    database = parent / "agency.db"
    mutations: list[Path] = []
    monkeypatch.setattr(sqlite_store, "_storage_parent_is_trusted", lambda _path: False)
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: mutations.append(path),
    )

    with pytest.raises(PermissionError, match="cross-account path substitution"):
        Store(database)

    assert not database.exists()
    assert mutations == []


def test_untrusted_existing_ancestor_receives_no_new_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "new" / "private" / "agency.db"
    monkeypatch.setattr(
        sqlite_store,
        "_storage_creation_boundary_is_trusted",
        lambda *_args: False,
    )
    with pytest.raises(PermissionError, match="storage ancestor"):
        Store(database)
    assert not (tmp_path / "new").exists()


def test_product_owned_parent_rejects_unsafe_state_before_acl_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent = tmp_path / "runtime"
    parent.mkdir()
    database = parent / "agency.db"
    mutations: list[Path] = []
    monkeypatch.setattr(sqlite_store, "_default_runtime_directory", lambda: parent)
    monkeypatch.setattr(sqlite_store, "_storage_parent_is_trusted", lambda _path: False)
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: mutations.append(path),
    )

    with pytest.raises(PermissionError, match="cross-account path substitution"):
        Store(database)

    assert not database.exists()
    assert mutations == []


def test_existing_foreign_owned_database_is_not_repermissioned(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "agency.db"
    database.write_bytes(b"foreign")
    mutations: list[Path] = []
    monkeypatch.setattr(sqlite_store, "_storage_file_is_trusted", lambda _path: False)
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: mutations.append(path),
    )
    with pytest.raises(PermissionError, match="trusted single-link"):
        Store(database)
    assert database.read_bytes() == b"foreign"
    assert mutations == []


def test_store_freezes_relative_database_path_without_resolving_links(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    store = Store(Path("private") / "agency.db")
    assert store.db_path == tmp_path / "private" / "agency.db"

    monkeypatch.setattr(
        Path,
        "resolve",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not resolve")),
    )
    assert store._current_schema_state() == (True, True)


class _ClosableConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _RollbackFailureConnection(_ClosableConnection):
    in_transaction = True

    def __init__(self) -> None:
        super().__init__()
        self.row_factory = None

    def execute(self, sql: str) -> SimpleNamespace | None:
        if sql == "PRAGMA journal_mode":
            return SimpleNamespace(fetchone=lambda: ("wal",))
        if "sqlite_master" in sql:
            return SimpleNamespace(fetchone=lambda: None)
        return None

    def rollback(self) -> None:
        raise RuntimeError("rollback failed")


def test_sqlite_write_open_rejects_changed_database_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _ClosableConnection()
    identities = iter(((1, 1), (1, 2)))
    monkeypatch.setattr(store, "_database_identity", lambda: next(identities))
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: connection)

    with pytest.raises(PermissionError, match="changed during SQLite open"):
        store._connect()
    assert connection.closed


def test_sqlite_read_open_closes_connection_on_identity_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _ClosableConnection()
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(
        store,
        "_require_database_identity",
        lambda _expected: (_ for _ in ()).throw(
            PermissionError("Agency Runtime database changed during SQLite open")
        ),
    )

    with pytest.raises(PermissionError, match="changed during SQLite open"):
        store._current_schema_state()
    assert connection.closed


def test_sqlite_read_open_closes_even_when_cleanup_rollback_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _RollbackFailureConnection()
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(store, "_require_database_identity", lambda _expected: None)
    with pytest.raises(RuntimeError, match="rollback failed"):
        store._current_schema_state()
    assert connection.closed


def test_database_identity_rejects_missing_and_non_regular_targets(tmp_path: Path) -> None:
    store = Store.__new__(Store)
    store.db_path = tmp_path / "missing.db"
    with pytest.raises(PermissionError, match="disappeared before open"):
        store._database_identity()

    store.db_path.mkdir()
    with pytest.raises(PermissionError, match="regular non-link"):
        store._database_identity()

    store.db_path = SimpleNamespace(
        lstat=lambda: SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600,
            st_dev=1,
            st_ino=0,
            st_nlink=1,
            st_file_attributes=0,
        )
    )
    with pytest.raises(PermissionError, match="identity is unavailable"):
        store._database_identity()


def test_current_sid_reader_non_windows_and_unknown_rights() -> None:
    assert windows_acl.current_process_user_sid(is_windows=False) is None
    assert windows_acl._sddl_rights_can_replace_child("0x-not-hex")
    assert windows_acl._sddl_rights_can_replace_child("F")
    assert not windows_acl._sddl_rights_can_replace_child("")


def test_new_store_failure_rolls_back_database_and_sidecar_under_durable_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "new" / "nested"
    database = parent / "agency.db"
    monkeypatch.setattr(Store, "_current_schema_state", lambda _self: (False, False))

    def fail_schema(self: Store, **_kwargs: object) -> None:
        sidecar = self.db_path.with_name(f"{self.db_path.name}-wal")
        sidecar.write_bytes(b"new sidecar")
        sidecar.chmod(0o600)
        raise RuntimeError("schema failed")

    monkeypatch.setattr(Store, "_init_schema", fail_schema)

    with pytest.raises(RuntimeError, match="schema failed"):
        Store(database)

    assert not database.exists()
    assert parent.is_dir()
    assert set(parent.iterdir()) == {initialization_lock_path(database)}
    assert initialization_lock_path(database).stat().st_size == 1


def test_existing_store_failure_preserves_database_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "existing.db"
    Store(database)
    before = database.read_bytes()
    monkeypatch.setattr(
        Store,
        "_current_schema_state",
        lambda _self: (_ for _ in ()).throw(RuntimeError("inspection failed")),
    )

    with pytest.raises(RuntimeError, match="inspection failed"):
        Store(database)

    assert database.read_bytes() == before


def test_created_storage_cleanup_refuses_identity_replacement(tmp_path: Path) -> None:
    target = tmp_path / "created"
    target.mkdir()
    identity = store_security.capture_created_storage_path(target, directory=True)
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    target.rmdir()
    replacement.rename(target)

    with pytest.raises(PermissionError, match="identity replacement"):
        store_security.cleanup_created_storage_paths([identity], is_windows=os.name == "nt")

    assert target.is_dir()


def test_storage_trust_cache_returns_consistent_verdict(tmp_path: Path) -> None:
    """PERF-02: the trust verdict is cached and reused for a stable file
    identity (same inode + mtime), avoiding the lstat/DACL probe on every
    store connection. This is the hook-hot-path optimization."""
    db_path = tmp_path / "cached.db"
    db_path.write_bytes(b"")
    # Establish an owner-private file so the verdict is True on POSIX.
    if os.name == "nt":
        store_security.restrict_windows_acl(db_path, directory=False, is_windows=True)
    else:
        os.chmod(db_path, stat.S_IRUSR | stat.S_IWUSR)

    first = sqlite_store._storage_file_is_trusted(db_path)
    second = sqlite_store._storage_file_is_trusted(db_path)
    assert first is True
    assert second is first  # cached, identical verdict
    assert str(db_path) in {str(p) for p in sqlite_store._trust_cache}


def test_storage_trust_cache_invalidates_after_permission_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PERF-02 safety: the cache MUST invalidate when permissions change, so a
    file that was repaired from untrusted to trusted is re-checked rather than
    returning a stale negative verdict. Permission repair (chmod/DACL rewrite)
    does not change inode or mtime, so invalidation is driven by the restrict
    chokepoint, not the identity key."""
    db_path = tmp_path / "repaired.db"
    db_path.write_bytes(b"")

    # Force an initial untrusted verdict into the cache.
    monkeypatch.setattr(
        sqlite_store,
        "storage_file_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    assert sqlite_store._storage_file_is_trusted(db_path) is False
    assert str(db_path) in {str(p) for p in sqlite_store._trust_cache}

    # Simulate the repair chokepoint clearing the cache.
    sqlite_store._invalidate_storage_trust_cache(db_path)
    assert str(db_path) not in {str(p) for p in sqlite_store._trust_cache}

    # After invalidation the real (authoritative) check runs again.
    monkeypatch.undo()
    assert sqlite_store._storage_file_is_trusted(db_path) is True
