from __future__ import annotations

import sqlite3
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import config
from agency_runtime.core.store import projections, schema, security
from agency_runtime.core.store import sqlite as sqlite_store
from agency_runtime.core.store.evidence import EvidenceStoreMixin
from agency_runtime.core.store.sqlite import Store


def test_projection_fallbacks_redact_malformed_endpoints_and_classify_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config,
        "load_config",
        lambda: (_ for _ in ()).throw(RuntimeError("invalid config")),
    )
    assert projections.capture_content_enabled() is False
    assert (
        projections.sanitize_api_base("http://user:secret@host:bad/path?token=x")
        == "http://host/path"
    )
    assert projections.sanitize_api_base("http://[invalid?api_key=secret") == "http://[invalid"
    assert projections.sanitize_api_base("opaque://user@host/path?secret=x") == (
        "opaque://host/path"
    )
    assert projections.sanitize_api_base("http://user@[invalid/path") == ("http://[invalid/path")
    assert projections.sanitize_api_base("secret@host") == "host"
    assert projections.sanitize_api_base("secret=value") == "secret=[REDACTED]"
    assert (
        projections.project_delegation_detail(
            "dependency did not complete successfully: build_1",
            field="error",
            capture_content=False,
        )
        == "dependency did not complete successfully: build_1"
    )
    assert (
        projections.project_delegation_detail(
            "the executable disappeared",
            field="error",
            capture_content=False,
        )
        == "executable_unavailable"
    )


class _PermissionPath:
    def __init__(self, metadata: Any, after: Any | None = None) -> None:
        self.metadata = metadata
        self.after = after or metadata

    def lstat(self) -> Any:
        return self.metadata

    def stat(self) -> Any:
        return self.after

    def __str__(self) -> str:
        return "storage"


def test_store_permission_security_rejects_links_kinds_and_failed_repairs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    security.restrict_path_permissions(
        missing,
        directory=False,
        is_windows=False,
        link_checker=lambda _path: False,
        windows_acl=lambda *_args, **_kwargs: True,
    )

    regular = SimpleNamespace(st_mode=stat.S_IFREG | 0o600)
    with pytest.raises(PermissionError, match="symlink"):
        security.restrict_path_permissions(
            _PermissionPath(regular),  # type: ignore[arg-type]
            directory=False,
            is_windows=False,
            link_checker=lambda _path: True,
            windows_acl=lambda *_args, **_kwargs: True,
        )
    with pytest.raises(PermissionError, match="must be a directory"):
        security.restrict_path_permissions(
            _PermissionPath(regular),  # type: ignore[arg-type]
            directory=True,
            is_windows=False,
            link_checker=lambda _path: False,
            windows_acl=lambda *_args, **_kwargs: True,
        )
    with pytest.raises(PermissionError, match="Windows ACL"):
        security.restrict_path_permissions(
            _PermissionPath(regular),  # type: ignore[arg-type]
            directory=False,
            is_windows=True,
            link_checker=lambda _path: False,
            windows_acl=lambda *_args, **_kwargs: False,
        )

    monkeypatch.setattr(security.os, "chmod", lambda *_args: None)
    with pytest.raises(PermissionError, match="private permissions"):
        security.restrict_path_permissions(
            _PermissionPath(
                regular,
                SimpleNamespace(st_mode=stat.S_IFREG | 0o644),
            ),  # type: ignore[arg-type]
            directory=False,
            is_windows=False,
            link_checker=lambda _path: False,
            windows_acl=lambda *_args, **_kwargs: True,
        )
    security.restrict_path_permissions(
        _PermissionPath(regular),  # type: ignore[arg-type]
        directory=False,
        is_windows=False,
        link_checker=lambda _path: False,
        windows_acl=lambda *_args, **_kwargs: True,
    )


def test_windows_permission_repair_reports_a_vanished_target(
    tmp_path: Path,
) -> None:
    sidecar = tmp_path / "agency.db-shm"
    sidecar.write_bytes(b"transient")

    def disappear(path: Path, *, directory: bool) -> bool:
        del directory
        path.unlink()
        return False

    with pytest.raises(FileNotFoundError):
        security.restrict_path_permissions(
            sidecar,
            directory=False,
            is_windows=True,
            link_checker=lambda _path: False,
            windows_acl=disappear,
        )
    assert not sidecar.exists()

    regular = SimpleNamespace(st_mode=stat.S_IFREG | 0o600)
    link_checks = 0

    def replaced_by_link(_path: Path) -> bool:
        nonlocal link_checks
        link_checks += 1
        return link_checks == 2

    with pytest.raises(PermissionError, match="symlink"):
        security.restrict_path_permissions(
            _PermissionPath(regular),  # type: ignore[arg-type]
            directory=False,
            is_windows=True,
            link_checker=replaced_by_link,
            windows_acl=lambda *_args, **_kwargs: False,
        )


def test_default_store_path_falls_back_when_config_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(
        config,
        "load_config",
        lambda: (_ for _ in ()).throw(RuntimeError("invalid")),
    )
    assert security.default_db_path() == tmp_path / ".agency-runtime" / "agency.db"


def test_store_evidence_and_roster_persistence_error_and_update_paths(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="host is required"):
        store.set_host_control("", enabled=True)
    with pytest.raises(ValueError, match="complete host canary"):
        store.record_host_canary_attestation(
            host="",
            profile_scope="current-profile",
            platform_system="Windows",
            platform_release="11",
            platform_machine="x86_64",
            host_version="1",
            plugin_version="1",
            install_id="install",
            bundle_digest="digest",
            trace_id="trace",
        )
    with pytest.raises(ValueError, match="profile_scope"):
        store.record_host_canary_attestation(
            host="codex",
            profile_scope="invalid",
            platform_system="Windows",
            platform_release="11",
            platform_machine="x86_64",
            host_version="1",
            plugin_version="1",
            install_id="install",
            bundle_digest="digest",
            trace_id="trace",
        )

    run_id = store.create_run(
        trace_id="trace",
        session_id="session",
        host="codex",
        user_message="message",
    )
    store.complete_run(run_id)
    store.record_specialist_loaded("", "")

    first = store.add_agent_source("https://example.test/agents", "first")
    second = store.add_agent_source(
        "https://example.test/agents",
        "updated",
        trusted_for_auto_approve=True,
    )
    assert second == first
    store.record_import_event("imported", "agent", "detail")
    store.deactivate_agent("missing")

    with pytest.raises(ValueError, match="older_than_days"):
        store.trim_runtime_tables(older_than_days=-1)
    with pytest.raises(ValueError, match="keep_last"):
        store.trim_runtime_tables(keep_last=-1)


class _Cursor:
    rowcount = 1


class _Connection:
    def __init__(self) -> None:
        self.closed = False
        self.committed = False

    def execute(self, *_args: Any, **_kwargs: Any) -> _Cursor:
        return _Cursor()

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


class _AttestationStore(EvidenceStoreMixin):
    def __init__(self) -> None:
        self.connection = _Connection()

    def _connect(self) -> _Connection:
        return self.connection

    def _now(self) -> str:
        return "2026-07-12T00:00:00+00:00"

    def get_host_canary_attestation(self, host: str) -> None:
        return None


def test_canary_attestation_postcondition_fails_closed() -> None:
    store = _AttestationStore()
    with pytest.raises(RuntimeError, match="postcondition"):
        store.record_host_canary_attestation(
            host="codex",
            profile_scope="current-profile",
            platform_system="Windows",
            platform_release="11",
            platform_machine="x86_64",
            host_version="1",
            plugin_version="1",
            install_id="install",
            bundle_digest="digest",
            trace_id="trace",
        )
    assert store.connection.committed is True
    assert store.connection.closed is True


def test_private_projection_migration_discards_invalid_legacy_metadata() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(schema.SCHEMA_V1)
    connection.execute(
        "INSERT INTO runs (id, trace_id, started_at, metadata) VALUES (?, ?, ?, ?)",
        ("id", "trace", "now", "{invalid"),
    )
    schema.migrate_private_projections(connection, capture_content=False)
    row = connection.execute("SELECT user_message, metadata FROM runs").fetchone()
    assert dict(row) == {"user_message": "", "metadata": None}
    connection.close()


def test_sqlite_compatibility_wrappers_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlite_store, "bounded_text", lambda value, limit: f"{value}:{limit}")
    monkeypatch.setattr(sqlite_store, "sanitize_api_base", lambda value: f"safe:{value}")
    monkeypatch.setattr(
        sqlite_store,
        "redact_sensitive_text",
        lambda value, limit: f"redacted:{value}:{limit}",
    )
    monkeypatch.setattr(sqlite_store, "project_run_metadata", lambda metadata: "metadata")
    assert sqlite_store._bounded("value", 3) == "value:3"
    assert sqlite_store._sanitize_api_base("url") == "safe:url"
    assert sqlite_store._redact_sensitive_text("secret", 4) == "redacted:secret:4"
    assert sqlite_store._project_run_metadata({}) == "metadata"
    monkeypatch.setattr(sqlite_store, "_capture_content_enabled", lambda: True)
    monkeypatch.setattr(
        sqlite_store,
        "project_delegation_detail",
        lambda value, **kwargs: f"{value}:{kwargs['capture_content']}",
    )
    assert sqlite_store._project_delegation_detail("detail", field="error") == "detail:True"
    assert (
        sqlite_store._project_delegation_detail("detail", field="error", capture_content=False)
        == "detail:False"
    )


def test_sqlite_static_migration_wrappers_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(sqlite_store, "ensure_column", lambda *_args: calls.append("column"))
    monkeypatch.setattr(sqlite_store, "runs_trace_is_unique", lambda _conn: True)
    monkeypatch.setattr(
        sqlite_store, "migrate_trace_integrity", lambda *_args, **_kwargs: calls.append("trace")
    )
    monkeypatch.setattr(
        sqlite_store,
        "migrate_private_projections",
        lambda *_args, **_kwargs: calls.append("private"),
    )
    monkeypatch.setattr(sqlite_store, "_capture_content_enabled", lambda: False)
    store = Store.__new__(Store)
    store._ensure_column(object(), "table", "column", "TEXT")  # type: ignore[arg-type]
    assert store._runs_trace_is_unique(object()) is True  # type: ignore[arg-type]
    store._migrate_trace_integrity(object())  # type: ignore[arg-type]
    store._migrate_private_projections(object())  # type: ignore[arg-type]
    assert calls == ["column", "trace", "private"]


def test_store_private_file_races_and_link_checks_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store.__new__(Store)
    store.db_path = tmp_path / "race.db"
    store._harden_storage_parent = False
    monkeypatch.setattr(store, "_assert_storage_paths_safe", lambda: None)
    monkeypatch.setattr(
        sqlite_store.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    monkeypatch.setattr(sqlite_store, "_is_link_or_reparse_point", lambda _path: True)
    with pytest.raises(PermissionError, match="symlink"):
        store._ensure_private_storage_file()

    store.db_path.write_bytes(b"database")
    with pytest.raises(PermissionError, match="symlink"):
        store._ensure_private_storage_file()


def test_store_private_file_race_to_regular_file_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store.__new__(Store)
    store.db_path = tmp_path / "race.db"
    store._harden_storage_parent = False
    monkeypatch.setattr(store, "_assert_storage_paths_safe", lambda: None)
    monkeypatch.delattr(sqlite_store.os, "O_BINARY", raising=False)
    monkeypatch.setattr(
        sqlite_store.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    monkeypatch.setattr(sqlite_store, "_is_link_or_reparse_point", lambda _path: False)
    monkeypatch.setattr(sqlite_store, "_restrict_path_permissions", lambda *_args, **_kwargs: None)
    store._ensure_private_storage_file()


def test_store_permission_repair_rejects_link_and_tolerates_sidecar_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store.__new__(Store)
    store.db_path = tmp_path / "agency.db"
    sidecar = Path(f"{store.db_path}-shm")
    sidecar.write_bytes(b"sidecar")
    store._harden_storage_parent = False
    store._permission_fingerprints = {}
    monkeypatch.setattr(sqlite_store, "_sqlite_storage_paths", lambda _path: (sidecar,))
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: True,
    )
    with pytest.raises(PermissionError, match="symlink"):
        store._repair_storage_permissions()

    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )

    def vanish_sidecar(path: Path, **_kwargs: Any) -> None:
        path.unlink()
        raise FileNotFoundError

    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        vanish_sidecar,
    )
    store._repair_storage_permissions()

    sidecar.write_bytes(b"sidecar")
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: path.unlink(),
    )
    store._repair_storage_permissions()
    assert store._permission_fingerprints == {}

    sidecar.write_bytes(b"sidecar")
    link_checks = 0

    def replaced_by_link(_metadata: Any) -> bool:
        nonlocal link_checks
        link_checks += 1
        return link_checks == 2

    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        replaced_by_link,
    )
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(PermissionError, match="symlink"):
        store._repair_storage_permissions()

    sidecar.unlink()
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )
    store._repair_storage_permissions()

    monkeypatch.setattr(
        sqlite_store,
        "_sqlite_storage_paths",
        lambda _path: (store.db_path,),
    )
    with pytest.raises(FileNotFoundError):
        store._repair_storage_permissions()

    store.db_path.write_bytes(b"database")
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    with pytest.raises(FileNotFoundError):
        store._repair_storage_permissions()

    store.db_path.write_bytes(b"database")
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: path.unlink(),
    )
    with pytest.raises(FileNotFoundError):
        store._repair_storage_permissions()

    class PermissionDeniedAfterRepair:
        def __init__(self) -> None:
            self.calls = 0

        def lstat(self) -> Any:
            self.calls += 1
            if self.calls == 2:
                raise PermissionError("ACL metadata denied")
            return SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_dev=1, st_ino=2)

    denied = PermissionDeniedAfterRepair()
    monkeypatch.setattr(
        sqlite_store,
        "_sqlite_storage_paths",
        lambda _path: (denied,),
    )
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(PermissionError, match="metadata denied"):
        store._repair_storage_permissions()

    class ReplacedDuringRepair:
        def __init__(self, fingerprints: list[tuple[int, int]]) -> None:
            self.fingerprints = iter(fingerprints)
            self.current = fingerprints[0]

        def lstat(self) -> Any:
            self.current = next(self.fingerprints, self.current)
            return SimpleNamespace(
                st_mode=stat.S_IFREG | 0o600,
                st_dev=self.current[0],
                st_ino=self.current[1],
            )

    replaced_once = ReplacedDuringRepair([(1, 2), (3, 4), (3, 4), (3, 4)])
    repairs: list[Any] = []
    monkeypatch.setattr(
        sqlite_store,
        "_sqlite_storage_paths",
        lambda _path: (replaced_once,),
    )
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: repairs.append(path),
    )
    store._repair_storage_permissions()
    assert repairs == [replaced_once, replaced_once]
    assert store._permission_fingerprints[replaced_once] == (3, 4)

    reappearing = ReplacedDuringRepair([(1, 2), (3, 4), (3, 4)])
    repair_attempts = 0

    def disappear_then_reappear(*_args: Any, **_kwargs: Any) -> None:
        nonlocal repair_attempts
        repair_attempts += 1
        if repair_attempts == 1:
            raise FileNotFoundError

    monkeypatch.setattr(sqlite_store, "_restrict_path_permissions", disappear_then_reappear)
    store._repair_storage_target(
        reappearing,  # type: ignore[arg-type]
        directory=False,
        optional_sidecar=True,
    )
    assert repair_attempts == 2
    assert store._permission_fingerprints[reappearing] == (3, 4)

    replaced_twice = ReplacedDuringRepair([(1, 2), (3, 4), (3, 4), (5, 6)])
    monkeypatch.setattr(
        sqlite_store,
        "_sqlite_storage_paths",
        lambda _path: (replaced_twice,),
    )
    with pytest.raises(PermissionError, match="changed during permission repair"):
        store._repair_storage_permissions()

    replaced_database = ReplacedDuringRepair([(1, 2), (3, 4)])
    with pytest.raises(PermissionError, match="changed during permission repair"):
        store._repair_storage_target(
            replaced_database,  # type: ignore[arg-type]
            directory=False,
            optional_sidecar=False,
        )


def test_store_permission_repair_skips_already_private_posix_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = SimpleNamespace(
        lstat=lambda: SimpleNamespace(
            st_mode=stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR,
            st_dev=1,
            st_ino=2,
        )
    )
    store = Store.__new__(Store)
    store.db_path = Path("agency.db")
    store._harden_storage_parent = False
    store._permission_fingerprints = {}
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", False)
    monkeypatch.setattr(sqlite_store, "_sqlite_storage_paths", lambda _path: (path,))
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must skip")),
    )
    store._repair_storage_permissions()


class _JournalConnection:
    def __init__(self, *, terminal_error: str | None = None) -> None:
        self.terminal_error = terminal_error
        self.journal_attempts = 0
        self.closed = False
        self.row_factory: Any = None

    def execute(self, sql: str) -> Any:
        if sql == "PRAGMA journal_mode=WAL":
            self.journal_attempts += 1
            if self.journal_attempts == 1:
                raise sqlite3.OperationalError(self.terminal_error or "database is locked")
            return SimpleNamespace(fetchone=lambda: ("wal",))
        return SimpleNamespace(fetchone=lambda: None)

    def close(self) -> None:
        self.closed = True


def _uninitialized_store(tmp_path: Path) -> Store:
    store = Store.__new__(Store)
    store.db_path = tmp_path / "agency.db"
    store._journal_ready = False
    store._foreign_keys_ready = False
    store._permission_fingerprints = {}
    store._harden_storage_parent = False
    store._assert_storage_paths_safe = lambda: None  # type: ignore[method-assign]
    store._repair_storage_permissions = lambda: None  # type: ignore[method-assign]
    return store


def test_store_connect_retries_locks_and_closes_on_terminal_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = _uninitialized_store(tmp_path)
    retrying = _JournalConnection()
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: retrying)
    monkeypatch.setattr(sqlite_store.time, "sleep", lambda _delay: None)
    assert store._connect() is retrying
    assert retrying.journal_attempts == 2

    terminal = _JournalConnection(terminal_error="disk unavailable")
    store._journal_ready = False
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: terminal)
    with pytest.raises(sqlite3.OperationalError, match="disk unavailable"):
        store._connect()
    assert terminal.closed is True

    ready = _JournalConnection()
    store._journal_ready = True
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_args, **_kwargs: ready)
    assert store._connect() is ready
    assert ready.journal_attempts == 0


def test_store_schema_inspection_and_initialization_error_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = _uninitialized_store(tmp_path)
    store.db_path.write_bytes(b"database")
    monkeypatch.setattr(
        sqlite_store.sqlite3,
        "connect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(sqlite3.DatabaseError("invalid")),
    )
    assert store._current_schema_state() == (False, False)

    connection = SimpleNamespace(
        committed=False,
        rolled_back=False,
        closed=False,
        commit=lambda: None,
        rollback=lambda: None,
        close=lambda: None,
    )
    monkeypatch.setattr(store, "_connect", lambda: connection)
    monkeypatch.setattr(
        sqlite_store,
        "migrate_schema",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("migration failed")),
    )
    with pytest.raises(RuntimeError, match="migration failed"):
        store._init_schema()
