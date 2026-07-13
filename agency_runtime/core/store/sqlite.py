"""SQLite canonical store for Agency Runtime.

All runtime state — runs, model receipts, skills, specialists, delegations,
roster — lives here. No loose JSON files.
"""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.store.evidence import EvidenceStoreMixin
from agency_runtime.core.store.maintenance import MaintenanceStoreMixin
from agency_runtime.core.store.projections import (
    API_BASE_LIMIT,
    DELEGATION_DETAIL_LIMIT,
    DIAGNOSTIC_REASON_LIMIT,
    RUN_CONTENT_LIMIT,
    bounded_text,
    capture_content_enabled,
    project_delegation_detail,
    project_run_metadata,
    redact_sensitive_text,
    sanitize_api_base,
)
from agency_runtime.core.store.roster import RosterStoreMixin
from agency_runtime.core.store.schema import (
    ALL_TABLES,
    RUNTIME_DELETE_ORDER,
    RUNTIME_TABLE_TIMESTAMPS,
    SCHEMA_V1,
    SCHEMA_VERSION,
    ensure_column,
    migrate_private_projections,
    migrate_schema,
    migrate_trace_integrity,
    runs_trace_is_unique,
)
from agency_runtime.core.store.security import (
    default_db_path,
    default_runtime_directory,
    is_link_or_reparse_point,
    metadata_is_link_or_reparse_point,
    restrict_path_permissions,
    restrict_windows_acl,
    sqlite_storage_paths,
)

_RUN_CONTENT_LIMIT = RUN_CONTENT_LIMIT
_DELEGATION_DETAIL_LIMIT = DELEGATION_DETAIL_LIMIT
_DIAGNOSTIC_REASON_LIMIT = DIAGNOSTIC_REASON_LIMIT
_API_BASE_LIMIT = API_BASE_LIMIT
_IS_WINDOWS = os.name == "nt"
_STORAGE_PERMISSION_REPAIR_LOCK = threading.RLock()


# Compatibility wrappers intentionally resolve dependencies through this module.
# Existing embedders and tests monkeypatch these seams to exercise fail-closed
# behavior without mutating process-wide configuration.
def _capture_content_enabled() -> bool:
    return capture_content_enabled()


def _bounded(value: object, limit: int) -> str:
    return bounded_text(value, limit)


def _sanitize_api_base(value: object) -> str:
    return sanitize_api_base(value)


def _redact_sensitive_text(value: object, limit: int) -> str:
    return redact_sensitive_text(value, limit)


def _project_delegation_detail(
    value: object,
    *,
    field: str,
    capture_content: bool | None = None,
) -> str:
    if capture_content is None:
        capture_content = _capture_content_enabled()
    return project_delegation_detail(
        value,
        field=field,
        capture_content=capture_content,
    )


def _project_run_metadata(metadata: dict[str, Any] | None) -> str | None:
    return project_run_metadata(metadata)


def _restrict_windows_acl(path: Path, *, directory: bool) -> bool:
    return restrict_windows_acl(
        path,
        directory=directory,
        is_windows=_IS_WINDOWS,
    )


def _restrict_path_permissions(path: Path, *, directory: bool) -> None:
    restrict_path_permissions(
        path,
        directory=directory,
        is_windows=_IS_WINDOWS,
        link_checker=_is_link_or_reparse_point,
        windows_acl=_restrict_windows_acl,
    )


def _default_db_path() -> Path:
    return default_db_path()


def _default_runtime_directory() -> Path:
    return default_runtime_directory()


def _is_link_or_reparse_point(path: Path) -> bool:
    return is_link_or_reparse_point(path)


def _metadata_is_link_or_reparse_point(metadata: os.stat_result) -> bool:
    return metadata_is_link_or_reparse_point(metadata)


def _sqlite_storage_paths(db_path: Path) -> tuple[Path, ...]:
    return sqlite_storage_paths(db_path)


_SCHEMA_VERSION = SCHEMA_VERSION


_SCHEMA_V1 = SCHEMA_V1
_ALL_TABLES = ALL_TABLES
_RUNTIME_TABLE_TIMESTAMPS = RUNTIME_TABLE_TIMESTAMPS
_RUNTIME_DELETE_ORDER = RUNTIME_DELETE_ORDER


class Store(EvidenceStoreMixin, MaintenanceStoreMixin, RosterStoreMixin):
    """SQLite-backed canonical store for Agency Runtime."""

    @staticmethod
    def _capture_content_enabled() -> bool:
        """Resolve the patchable content-capture compatibility seam."""

        return _capture_content_enabled()

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(os.path.expanduser(str(db_path)))
        else:
            self.db_path = _default_db_path()
        self._permission_fingerprints: dict[Path, tuple[int, int]] = {}
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=False, mode=0o700)
        except FileExistsError:
            created_parent = False
        else:
            created_parent = True
        default_parent = _default_runtime_directory()
        self._harden_storage_parent = bool(
            created_parent
            or (
                not self.db_path.parent.is_symlink()
                and os.path.abspath(self.db_path.parent) == os.path.abspath(default_parent)
            )
        )
        self._ensure_private_storage_file()
        self._foreign_keys_ready = False
        schema_current, journal_ready = self._current_schema_state()
        self._journal_ready = journal_ready
        if not schema_current:
            self._init_schema()
        self._foreign_keys_ready = True
        self._repair_storage_permissions()

    def _ensure_private_storage_file(self) -> None:
        """Securely create the DB without taking ownership of arbitrary parents."""
        self._assert_storage_paths_safe()
        if self._harden_storage_parent:
            with _STORAGE_PERMISSION_REPAIR_LOCK:
                _restrict_path_permissions(self.db_path.parent, directory=True)
        if not self.db_path.exists():
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            try:
                fd = os.open(self.db_path, flags, stat.S_IRUSR | stat.S_IWUSR)
            except FileExistsError:
                if _is_link_or_reparse_point(self.db_path):
                    raise PermissionError(
                        "refusing Agency Runtime database symlink or reparse point"
                    ) from None
            else:
                os.close(fd)
        if _is_link_or_reparse_point(self.db_path):
            raise PermissionError("refusing Agency Runtime database symlink or reparse point")
        with _STORAGE_PERMISSION_REPAIR_LOCK:
            _restrict_path_permissions(self.db_path, directory=False)

    def _assert_storage_paths_safe(self) -> None:
        """Reject links and non-files before permission repair or SQLite access."""

        for path in _sqlite_storage_paths(self.db_path):
            if _is_link_or_reparse_point(path):
                raise PermissionError(
                    "refusing Agency Runtime database or sidecar symlink or reparse point"
                )
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise PermissionError(
                    "refusing Agency Runtime database or sidecar non-regular file"
                )

    @staticmethod
    def _storage_metadata(path: Path, *, optional: bool) -> os.stat_result | None:
        """Read one storage identity while tolerating only absent sidecars."""

        try:
            return path.lstat()
        except FileNotFoundError:
            if optional:
                return None
            raise

    def _repair_storage_target_once(
        self,
        path: Path,
        *,
        directory: bool,
        optional_sidecar: bool,
    ) -> bool:
        """Secure one target, returning whether its identity changed mid-repair."""

        current = self._storage_metadata(path, optional=optional_sidecar)
        if current is None:
            return False
        if _metadata_is_link_or_reparse_point(current):
            raise PermissionError(
                "refusing Agency Runtime database or sidecar symlink or reparse point"
            )
        fingerprint = (int(current.st_dev), int(current.st_ino))
        expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
        if not _IS_WINDOWS and stat.S_IMODE(current.st_mode) == expected_mode:
            return False
        if _IS_WINDOWS and self._permission_fingerprints.get(path) == fingerprint:
            return False
        try:
            _restrict_path_permissions(path, directory=directory)
        except FileNotFoundError:
            # SQLite removes WAL sidecars when the final connection closes.
            if optional_sidecar:
                return True
            raise
        except PermissionError:
            if not optional_sidecar:
                raise
            observed = self._storage_metadata(path, optional=True)
            if observed is None:
                return True
            if _metadata_is_link_or_reparse_point(observed):
                raise PermissionError(
                    "refusing Agency Runtime database or sidecar symlink or reparse point"
                ) from None
            observed_fingerprint = (int(observed.st_dev), int(observed.st_ino))
            if observed_fingerprint != fingerprint:
                return True
            # A stable object that still rejects owner-only permissions is a
            # real hardening failure, not benign SQLite sidecar churn.
            raise
        repaired = self._storage_metadata(path, optional=optional_sidecar)
        if repaired is None:
            return True
        if _metadata_is_link_or_reparse_point(repaired):
            raise PermissionError(
                "refusing Agency Runtime database or sidecar symlink or reparse point"
            )
        repaired_fingerprint = (int(repaired.st_dev), int(repaired.st_ino))
        if repaired_fingerprint != fingerprint:
            return True
        self._permission_fingerprints[path] = repaired_fingerprint
        return False

    def _repair_storage_target(
        self,
        path: Path,
        *,
        directory: bool,
        optional_sidecar: bool,
    ) -> None:
        """Secure one stable storage identity or fail before caching it."""

        with _STORAGE_PERMISSION_REPAIR_LOCK:
            changed = self._repair_storage_target_once(
                path,
                directory=directory,
                optional_sidecar=optional_sidecar,
            )
            if not changed:
                return
            if not optional_sidecar:
                raise PermissionError(
                    "refusing Agency Runtime storage that changed during permission repair"
                )
            changed_again = self._repair_storage_target_once(
                path,
                directory=directory,
                optional_sidecar=True,
            )
            if changed_again:
                raise PermissionError(
                    "refusing Agency Runtime storage that changed during permission repair"
                )

    def _repair_storage_permissions(self) -> None:
        """Keep owned storage files and, when applicable, its directory private."""

        targets = [(path, False) for path in _sqlite_storage_paths(self.db_path)]
        if self._harden_storage_parent:
            targets.insert(0, (self.db_path.parent, True))
        for path, directory in targets:
            self._repair_storage_target(
                path,
                directory=directory,
                optional_sidecar=not directory and path != self.db_path,
            )

    def _connect(self) -> sqlite3.Connection:
        self._assert_storage_paths_safe()
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            if not self._journal_ready:
                attempt = 0
                while True:
                    try:
                        journal = conn.execute("PRAGMA journal_mode=WAL").fetchone()
                        self._journal_ready = bool(journal and str(journal[0]).casefold() == "wal")
                        break
                    except sqlite3.OperationalError as exc:
                        if "locked" not in str(exc).casefold() or attempt == 19:
                            raise
                        time.sleep(min(0.02 * (attempt + 1), 0.25))
                        attempt += 1
            conn.execute("PRAGMA synchronous=NORMAL")
            if self._foreign_keys_ready:
                conn.execute("PRAGMA foreign_keys=ON")
            conn.row_factory = sqlite3.Row
            self._repair_storage_permissions()
            return conn
        except BaseException:
            conn.close()
            raise

    def _current_schema_state(self) -> tuple[bool, bool]:
        """Inspect schema and journal state without taking a write lock."""
        self._assert_storage_paths_safe()
        if not self.db_path.is_file() or self.db_path.stat().st_size == 0:
            return False, False
        try:
            conn = sqlite3.connect(
                self.db_path.resolve().as_uri() + "?mode=ro",
                uri=True,
                timeout=5.0,
            )
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            try:
                journal_row = conn.execute("PRAGMA journal_mode").fetchone()
                journal_ready = bool(journal_row and str(journal_row[0]).casefold() == "wal")
                table = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
                ).fetchone()
                if table is None:
                    return False, journal_ready
                version = conn.execute(
                    "SELECT MAX(version) AS version FROM schema_version"
                ).fetchone()
                observed_version = int(version["version"] or 0)
                if observed_version > _SCHEMA_VERSION:
                    raise RuntimeError(
                        "Agency Runtime database schema is newer than this "
                        f"runtime ({observed_version} > {_SCHEMA_VERSION})"
                    )
                return observed_version == _SCHEMA_VERSION, journal_ready
            finally:
                conn.close()
        except (OSError, sqlite3.Error):
            return False, False

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            migrate_schema(
                conn,
                now=self._now,
                capture_content=_capture_content_enabled,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        ensure_column(conn, table, column, definition)

    @staticmethod
    def _runs_trace_is_unique(conn: sqlite3.Connection) -> bool:
        return runs_trace_is_unique(conn)

    def _migrate_trace_integrity(self, conn: sqlite3.Connection) -> None:
        migrate_trace_integrity(conn, now=self._now)

    def _migrate_private_projections(self, conn: sqlite3.Connection) -> None:
        migrate_private_projections(
            conn,
            capture_content=_capture_content_enabled(),
        )

    def _ensure_run(
        self,
        conn: sqlite3.Connection,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
    ) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO runs "
            "(id, trace_id, session_id, host, started_at, status, user_message, metadata) "
            "VALUES (?, ?, ?, ?, ?, 'evidence_only', '', ?)",
            (
                self._uuid(),
                trace_id,
                session_id,
                host or "unknown",
                self._now(),
                json.dumps({"implicit": True}),
            ),
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4())

    # ── Finalization ───────────────────────────────────────────────

    def record_finalization(
        self, *, trace_id: str, host: str, action: str, missing: list[str] | None = None
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO finalization_events (id, trace_id, host, action, missing, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    trace_id,
                    host,
                    action,
                    json.dumps(missing) if missing else None,
                    self._now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
