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

from agency_runtime.core.config import load_config
from agency_runtime.core.configuration_persistence import resolve_config_path
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.store.child_routing import ChildRoutingStoreMixin
from agency_runtime.core.store.delegation_activation import DelegationActivationStoreMixin
from agency_runtime.core.store.evidence import EvidenceStoreMixin
from agency_runtime.core.store.initialization_lock import storage_initialization_lock
from agency_runtime.core.store.maintenance import MaintenanceStoreMixin
from agency_runtime.core.store.native_child import NativeChildStoreMixin
from agency_runtime.core.store.preflight import _decode_preflight_recipe
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
from agency_runtime.core.store.receipt_authority import MODEL_RECEIPT_AUTHORITY_ORDER_SQL
from agency_runtime.core.store.roster import RosterStoreMixin
from agency_runtime.core.store.schema import (
    ALL_TABLES,
    REMEDIATION_AUTHORITY_KEY_NAME,
    RUNTIME_DELETE_ORDER,
    RUNTIME_TABLE_TIMESTAMPS,
    SCHEMA_V1,
    SCHEMA_VERSION,
    STORE_CLOCK_SQL,
    agent_import_event_sequence_schema_is_current,
    ensure_column,
    ensure_remediation_authority_key_integrity,
    migrate_private_projections,
    migrate_schema,
    migrate_trace_integrity,
    remediation_authority_schema_is_current,
    remediation_indexes_are_current,
    remediation_receipt_has_dependency,
    remediation_scan_id,
    retired_barrier_integrity_error,
    runs_trace_is_unique,
    source_redaction_purge_pending,
    trace_tombstone_turn_sequence_is_unique,
    validate_stored_source_identities,
    verify_remediation_authority,
)
from agency_runtime.core.store.security import (
    CreatedStoragePath,
    assert_storage_parent_chain,
    capture_created_storage_path,
    cleanup_created_storage_paths,
    create_private_storage_parent,
    default_db_path,
    default_runtime_directory,
    is_link_or_reparse_point,
    metadata_is_link_or_reparse_point,
    nearest_existing_storage_parent,
    restrict_path_permissions,
    restrict_windows_acl,
    sqlite_storage_paths,
    storage_creation_boundary_is_trusted,
    storage_file_is_trusted,
    storage_parent_is_trusted,
)
from agency_runtime.core.store.trace_identity import (
    correlation_digest,
    ensure_correlation_key_integrity,
)

_RUN_CONTENT_LIMIT = RUN_CONTENT_LIMIT
_DELEGATION_DETAIL_LIMIT = DELEGATION_DETAIL_LIMIT
_DIAGNOSTIC_REASON_LIMIT = DIAGNOSTIC_REASON_LIMIT
_API_BASE_LIMIT = API_BASE_LIMIT
_IS_WINDOWS = os.name == "nt"
_STORAGE_PERMISSION_REPAIR_LOCK = threading.RLock()


def _enable_recursive_triggers(conn: sqlite3.Connection) -> None:
    """Enable and verify trigger cascades required by the store invariants."""

    conn.execute("PRAGMA recursive_triggers=ON")
    setting = conn.execute("PRAGMA recursive_triggers").fetchone()
    if setting is None or int(setting[0]) != 1:
        raise RuntimeError("SQLite recursive triggers are unavailable")


# Compatibility wrappers intentionally resolve dependencies through this module.
# Existing embedders and tests monkeypatch these seams to exercise fail-closed
# behavior without mutating process-wide configuration.
def _capture_content_enabled(config_path: str | Path | None = None) -> bool:
    return capture_content_enabled(config_path)


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


def _bounded_run_metadata(value: object) -> dict[str, Any]:
    raw = str(value or "")
    if not raw or len(raw.encode("utf-8", errors="replace")) > 16_384:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _merge_projected_run_metadata(
    value: object,
    updates: dict[str, Any],
) -> str | None:
    """Merge bounded content-free state into an existing run projection."""

    metadata = _bounded_run_metadata(value)
    metadata.update(updates)
    return project_run_metadata(metadata)


def _require_response_hash(value: object) -> str:
    """Return one canonical SHA-256 response identity or reject it."""

    normalized = str(value or "").strip()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("response_hash must be a lowercase SHA-256 digest")
    return normalized


def _optional_response_hash(value: object) -> str:
    """Return an optional canonical SHA-256 identity or reject it."""

    normalized = str(value or "").strip()
    return _require_response_hash(normalized) if normalized else ""


def _v20_receipt_schema_is_current(conn: sqlite3.Connection) -> bool:
    """Verify the current schema contract.

    The private name is retained for compatibility with downstream test seams
    introduced with schema v20; v21 additionally requires host-control CAS
    identity.
    """

    required_columns = {
        "delegation_activation_receipts": {
            "id",
            "token_hash",
            "session_id",
            "trace_id",
            "work_unit_id",
            "specialist_slug",
            "specialist_version",
            "specialist_prompt_hash",
            "worker_kind",
            "worker_id",
            "native_run_id",
            "created_at",
            "consumed_at",
            "delegation_event_id",
        },
        "delegation_events": {
            "executed_worker_kind",
            "executed_worker_id",
            "native_run_id",
            "retrieved_specialist_slug",
            "retrieved_specialist_version",
            "retrieved_specialist_prompt_hash",
            "activation_receipt_id",
        },
        "specialists_loaded": {"activation_receipt_id"},
        "finalization_events": {"policy_response_hash"},
        "host_controls": {"generation"},
    }
    for table, expected in required_columns.items():
        table_row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        if table_row is None:
            return False
        observed = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}
        if not expected.issubset(observed):
            return False

    expected_indexes = {
        "idx_activation_receipts_trace": (
            "delegation_activation_receipts",
            ("trace_id", "created_at"),
        ),
        "idx_activation_receipts_work_unit": (
            "delegation_activation_receipts",
            ("trace_id", "work_unit_id", "consumed_at"),
        ),
        "idx_finalization_trace_policy_response": (
            "finalization_events",
            ("trace_id", "action", "policy_response_hash"),
        ),
    }
    for name, (table, columns) in expected_indexes.items():
        index_row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ? AND tbl_name = ?",
            (name, table),
        ).fetchone()
        if index_row is None:
            return False
        observed = tuple(
            str(row["name"])
            for row in conn.execute(f"PRAGMA index_info({name})")  # nosec B608
        )
        if observed != columns:
            return False

    unique_column_sets = {
        tuple(
            str(column["name"])
            for column in conn.execute(
                f"PRAGMA index_info({row['name']})"  # nosec B608
            )
        )
        for row in conn.execute("PRAGMA index_list(delegation_activation_receipts)")
        if int(row["unique"] or 0) == 1
    }
    if not {
        ("token_hash",),
        (
            "trace_id",
            "work_unit_id",
            "specialist_slug",
            "specialist_version",
            "specialist_prompt_hash",
        ),
    }.issubset(unique_column_sets):
        return False

    foreign_keys = {
        (str(row["from"]), str(row["table"]), str(row["to"]))
        for row in conn.execute("PRAGMA foreign_key_list(delegation_activation_receipts)")
    }
    if not {
        ("trace_id", "runs", "trace_id"),
        ("delegation_event_id", "delegation_events", "id"),
    }.issubset(foreign_keys):
        return False

    expected_triggers = {
        "agency_delegation_activation_receipts_insert_activity",
        "agency_delegation_activation_receipts_update_activity",
    }
    trigger_rows = conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'trigger' "
        "AND tbl_name = 'delegation_activation_receipts'"
    ).fetchall()
    triggers = {str(row["name"]): str(row["sql"] or "").casefold() for row in trigger_rows}
    for name in expected_triggers:
        sql = triggers.get(name, "")
        if not sql or "update runs set last_activity_at" not in sql or "new.trace_id" not in sql:
            return False
    return True


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


def _default_db_path(config_path: str | Path | None = None) -> Path:
    return default_db_path(config_path)


def _default_runtime_directory() -> Path:
    return default_runtime_directory()


def _is_link_or_reparse_point(path: Path) -> bool:
    return is_link_or_reparse_point(path)


def _metadata_is_link_or_reparse_point(metadata: os.stat_result) -> bool:
    return metadata_is_link_or_reparse_point(metadata)


def _sqlite_storage_paths(db_path: Path) -> tuple[Path, ...]:
    return sqlite_storage_paths(db_path)


def _assert_storage_parent_chain(path: Path, *, allow_missing: bool) -> None:
    assert_storage_parent_chain(path, allow_missing=allow_missing)


def _storage_parent_is_trusted(path: Path) -> bool:
    return storage_parent_is_trusted(path, is_windows=_IS_WINDOWS)


def _storage_creation_boundary_is_trusted(boundary: Path, intended_parent: Path) -> bool:
    return storage_creation_boundary_is_trusted(
        boundary,
        intended_parent,
        is_windows=_IS_WINDOWS,
    )


def _create_private_storage_parent(
    boundary: Path,
    intended_parent: Path,
    *,
    created_paths: list[CreatedStoragePath] | None = None,
) -> bool:
    return create_private_storage_parent(
        boundary,
        intended_parent,
        is_windows=_IS_WINDOWS,
        created_paths=created_paths,
    )


def _storage_file_is_trusted(path: Path) -> bool:
    return storage_file_is_trusted(path, is_windows=_IS_WINDOWS)


def _require_storage_target_trusted(
    path: Path,
    *,
    directory: bool,
    message: str,
) -> None:
    trusted = _storage_parent_is_trusted(path) if directory else _storage_file_is_trusted(path)
    if not trusted:
        raise PermissionError(message)


def _nearest_existing_storage_parent(path: Path) -> Path:
    return nearest_existing_storage_parent(path)


_SCHEMA_VERSION = SCHEMA_VERSION


_SCHEMA_V1 = SCHEMA_V1


def _validate_roster_generation_counter(conn: sqlite3.Connection) -> None:
    counter = conn.execute(
        "SELECT value, typeof(value) AS value_type FROM store_counters "
        "WHERE name = 'roster-generation'"
    ).fetchone()
    if counter is None or counter["value_type"] != "integer" or int(counter["value"]) < 0:
        raise RuntimeError("roster generation counter integrity is invalid")


def _validate_turn_sequence_counter(conn: sqlite3.Connection) -> None:
    counter = conn.execute(
        "SELECT value, typeof(value) AS value_type FROM store_counters WHERE name = 'turn-sequence'"
    ).fetchone()
    maximum = conn.execute(
        "SELECT MAX(sequence) AS sequence FROM ("
        "SELECT MAX(turn_sequence) AS sequence FROM runs UNION ALL "
        "SELECT MAX(turn_sequence) AS sequence FROM trace_tombstones)"
    ).fetchone()
    if (
        counter is None
        or counter["value_type"] != "integer"
        or int(counter["value"]) < 0
        or int(counter["value"]) < int(maximum["sequence"] or 0)
    ):
        raise RuntimeError("turn sequence counter integrity is invalid")


_ALL_TABLES = ALL_TABLES
_RUNTIME_TABLE_TIMESTAMPS = RUNTIME_TABLE_TIMESTAMPS
_RUNTIME_DELETE_ORDER = RUNTIME_DELETE_ORDER


class Store(
    ChildRoutingStoreMixin,
    DelegationActivationStoreMixin,
    NativeChildStoreMixin,
    EvidenceStoreMixin,
    MaintenanceStoreMixin,
    RosterStoreMixin,
):
    """SQLite-backed canonical store for Agency Runtime."""

    def _capture_content_enabled(self) -> bool:
        """Resolve the patchable content-capture compatibility seam."""

        from agency_runtime.core.config_binding import (
            StoreConfigBindingError,
            assert_store_config_binding,
        )

        try:
            assert_store_config_binding(self)
        except StoreConfigBindingError:
            raise
        except Exception:
            # Invalid live configuration is not an effective retarget. Preserve
            # the established fail-private capture behavior while the frozen
            # database identity remains intact.
            pass
        return _capture_content_enabled(getattr(self, "config_path", None))

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        config_path: str | Path | None = None,
    ):
        # Freeze and validate one configuration identity before creating a
        # directory, database, journal, or schema. Live settings may reload
        # from this same path, but a later file or environment change to the
        # configured Store target fails closed until callers recreate Store.
        self.config_path = resolve_config_path(config_path)
        validated_config = load_config(self.config_path, reload=True)
        self._configured_config_path = self.config_path
        self._configured_store_path = Path(os.path.abspath(validated_config.store.resolved_path()))
        self._store_path_config_derived = db_path is None
        initial_capture_content = bool(validated_config.observability.capture_content)
        selected_db_path = (
            Path(os.path.expanduser(str(db_path))) if db_path else self._configured_store_path
        )
        # Freeze a lexical absolute identity without following a link. SQLite
        # never gets a later-CWD-dependent or newly resolved path.
        self.db_path = Path(os.path.abspath(selected_db_path))
        self._frozen_db_path = self.db_path
        self._permission_fingerprints: dict[Path, tuple[int, int]] = {}
        self._prepare_storage_parent()
        with storage_initialization_lock(self.db_path):
            created_paths: list[CreatedStoragePath] = []
            try:
                self._initialize_storage(
                    initial_capture_content=initial_capture_content,
                    created_paths=created_paths,
                )
            except BaseException as error:
                # Rollback is part of the same path-scoped critical section as
                # creation and schema initialization. No second constructor can
                # adopt this inode before its creator either commits or removes it.
                self._rollback_new_storage(created_paths, error=error)
                raise

    def _prepare_storage_parent(self) -> None:
        """Create and harden the parent before opening its persistent path lock."""

        _assert_storage_parent_chain(self.db_path.parent, allow_missing=True)
        creation_boundary = _nearest_existing_storage_parent(self.db_path.parent)
        if not _storage_creation_boundary_is_trusted(
            creation_boundary,
            self.db_path.parent,
        ):
            raise PermissionError(
                "Agency Runtime storage ancestor permits cross-account path substitution"
            )
        created_parent = _create_private_storage_parent(
            creation_boundary,
            self.db_path.parent,
        )
        default_parent = Path(os.path.abspath(_default_runtime_directory()))
        self._harden_storage_parent = bool(
            created_parent
            or (
                not self.db_path.parent.is_symlink()
                and os.path.abspath(self.db_path.parent) == os.path.abspath(default_parent)
            )
        )
        _assert_storage_parent_chain(self.db_path.parent, allow_missing=False)
        if not _storage_parent_is_trusted(self.db_path.parent):
            raise PermissionError(
                "Agency Runtime storage parent permits cross-account path substitution"
            )
        if self._harden_storage_parent:
            with _STORAGE_PERMISSION_REPAIR_LOCK:
                _restrict_path_permissions(self.db_path.parent, directory=True)
        if not _storage_parent_is_trusted(self.db_path.parent):
            raise PermissionError(
                "Agency Runtime storage parent permits cross-account path substitution"
            )

    def _initialize_storage(
        self,
        *,
        initial_capture_content: bool,
        created_paths: list[CreatedStoragePath],
    ) -> None:
        """Initialize one locked Store while retaining exact rollback receipts."""

        self._ensure_private_storage_file(created_paths=created_paths)
        self._foreign_keys_ready = False
        schema_current, journal_ready = self._current_schema_state()
        self._journal_ready = journal_ready
        if not schema_current:
            self._init_schema(capture_content=initial_capture_content)
        self._foreign_keys_ready = True
        self._repair_storage_permissions()

    def _rollback_new_storage(
        self,
        created_paths: list[CreatedStoragePath],
        *,
        error: BaseException,
    ) -> None:
        """Remove only unchanged storage created by this failed constructor."""

        created_database = any(
            not identity.directory and identity.path == self.db_path for identity in created_paths
        )
        if created_database:
            for path in _sqlite_storage_paths(self.db_path):
                if path == self.db_path or any(identity.path == path for identity in created_paths):
                    continue
                try:
                    identity = capture_created_storage_path(path, directory=False)
                except FileNotFoundError:
                    continue
                except (OSError, PermissionError) as sidecar_error:
                    add_exception_note(
                        error,
                        f"Agency Runtime could not identify a new sidecar for rollback: {sidecar_error}",
                    )
                    continue
                if not _storage_file_is_trusted(path):
                    add_exception_note(
                        error,
                        f"Agency Runtime left an untrusted new sidecar for inspection: {path}",
                    )
                    continue
                created_paths.append(identity)
        try:
            cleanup_created_storage_paths(created_paths, is_windows=_IS_WINDOWS)
        except Exception as cleanup_error:
            add_exception_note(
                error,
                f"Agency Runtime storage rollback failed: {cleanup_error}",
            )

    def _ensure_private_storage_file(
        self,
        *,
        created_paths: list[CreatedStoragePath] | None = None,
    ) -> None:
        """Securely create the DB without taking ownership of arbitrary parents."""
        self._assert_storage_paths_safe()
        for path in _sqlite_storage_paths(self.db_path):
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                continue
            del metadata
            self._require_stable_trusted_storage_file(
                path,
                optional_sidecar=path != self.db_path,
            )
        try:
            self.db_path.lstat()
        except FileNotFoundError:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | int(getattr(os, "O_CLOEXEC", 0))
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
                try:
                    opened = os.fstat(fd)
                    identity = capture_created_storage_path(self.db_path, directory=False)
                    current = os.lstat(self.db_path)
                    if not os.path.samestat(opened, current):
                        raise PermissionError(
                            "Agency Runtime database changed during exclusive creation"
                        )
                    if created_paths is not None:
                        created_paths.append(identity)
                finally:
                    os.close(fd)
        if _is_link_or_reparse_point(self.db_path):
            raise PermissionError("refusing Agency Runtime database symlink or reparse point")
        if not _storage_file_is_trusted(self.db_path):
            raise PermissionError("Agency Runtime storage file is not a trusted single-link file")
        with _STORAGE_PERMISSION_REPAIR_LOCK:
            _restrict_path_permissions(self.db_path, directory=False)
        if not _storage_file_is_trusted(self.db_path):
            raise PermissionError("Agency Runtime storage file is unsafe after permission repair")

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

    def _assert_storage_files_trusted(self) -> None:
        """Reject unsafe database or sidecar identities before every SQLite open."""

        for path in _sqlite_storage_paths(self.db_path):
            self._require_stable_trusted_storage_file(
                path,
                optional_sidecar=path != self.db_path,
            )

    def _require_stable_trusted_storage_file(
        self,
        path: Path,
        *,
        optional_sidecar: bool,
    ) -> None:
        """Accept absent/churning sidecars but require one stable trusted identity."""

        for _attempt in range(2):
            before = self._storage_metadata(path, optional=optional_sidecar)
            if before is None:
                return
            trusted = _storage_file_is_trusted(path)
            after = self._storage_metadata(path, optional=optional_sidecar)
            if after is None:
                return
            if os.path.samestat(before, after):
                if trusted:
                    return
                raise PermissionError(
                    "Agency Runtime database or sidecar is not a trusted single-link file"
                )
        raise PermissionError(
            "Agency Runtime database or sidecar changed repeatedly during trust inspection"
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

    def _optional_sidecar_identity_changed(
        self,
        path: Path,
        fingerprint: tuple[int, int],
    ) -> bool:
        """Distinguish transient sidecar churn from a stable unsafe object."""

        observed = self._storage_metadata(path, optional=True)
        if observed is None:
            return True
        if _metadata_is_link_or_reparse_point(observed):
            raise PermissionError(
                "refusing Agency Runtime database or sidecar symlink or reparse point"
            )
        return (int(observed.st_dev), int(observed.st_ino)) != fingerprint

    def _validate_repaired_storage_target(
        self,
        path: Path,
        *,
        directory: bool,
        optional_sidecar: bool,
        fingerprint: tuple[int, int],
    ) -> tuple[bool, tuple[int, int] | None]:
        """Validate the post-repair identity and return churn plus fingerprint."""

        repaired = self._storage_metadata(path, optional=optional_sidecar)
        if repaired is None:
            return True, None
        if _metadata_is_link_or_reparse_point(repaired):
            raise PermissionError(
                "refusing Agency Runtime database or sidecar symlink or reparse point"
            )
        repaired_fingerprint = (int(repaired.st_dev), int(repaired.st_ino))
        if repaired_fingerprint != fingerprint:
            return True, None
        try:
            _require_storage_target_trusted(
                path,
                directory=directory,
                message="Agency Runtime storage identity is unsafe after permission repair",
            )
        except PermissionError:
            if not optional_sidecar:
                raise
            if self._optional_sidecar_identity_changed(path, fingerprint):
                return True, None
            # A Windows sidecar can briefly deny security-descriptor reads
            # while another connection closes it. One stable recheck keeps
            # that churn distinct from an actually broad ACL.
            _require_storage_target_trusted(
                path,
                directory=False,
                message="Agency Runtime storage identity is unsafe after permission repair",
            )
        return False, repaired_fingerprint

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
        try:
            _require_storage_target_trusted(
                path,
                directory=directory,
                message=("refusing Agency Runtime storage permission repair on an unsafe identity"),
            )
        except PermissionError:
            if not optional_sidecar:
                raise
            if self._optional_sidecar_identity_changed(path, fingerprint):
                return True
            # Windows can briefly deny a sidecar security-descriptor read while
            # another connection opens or closes the same stable identity. A
            # single stable recheck tolerates that race without accepting a
            # persistently broad ACL.
            _require_storage_target_trusted(
                path,
                directory=False,
                message=("refusing Agency Runtime storage permission repair on an unsafe identity"),
            )
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
            if self._optional_sidecar_identity_changed(path, fingerprint):
                return True
            # A stable object that still rejects owner-only permissions is a
            # real hardening failure, not benign SQLite sidecar churn.
            raise
        changed, repaired_fingerprint = self._validate_repaired_storage_target(
            path,
            directory=directory,
            optional_sidecar=optional_sidecar,
            fingerprint=fingerprint,
        )
        if changed:
            return True
        if repaired_fingerprint is None:
            raise RuntimeError("stable storage repair omitted its identity fingerprint")
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
        self._assert_storage_files_trusted()
        expected_identity = self._database_identity()
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        try:
            self._require_database_identity(expected_identity)
            _enable_recursive_triggers(conn)
            secret_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'store_secrets'"
            ).fetchone()
            authority_key = b""
            if secret_table is not None:
                key_row = conn.execute(
                    "SELECT secret, typeof(secret) FROM store_secrets WHERE name = ?",
                    (REMEDIATION_AUTHORITY_KEY_NAME,),
                ).fetchone()
                if key_row is not None:
                    if (
                        str(key_row[1]) != "blob"
                        or not isinstance(key_row[0], bytes)
                        or len(key_row[0]) != 32
                    ):
                        raise RuntimeError("remediation resolution authority key is invalid")
                    authority_key = key_row[0]
            conn.create_function(
                "agency_verify_remediation_authority",
                10,
                lambda *values: verify_remediation_authority(
                    authority_key,
                    *values,
                ),
                deterministic=True,
            )
            conn.create_function(
                "agency_remediation_receipt_has_dependency",
                4,
                remediation_receipt_has_dependency,
                deterministic=True,
            )
            conn.create_function(
                "agency_remediation_scan_id",
                1,
                remediation_scan_id,
                deterministic=True,
            )
            conn.execute("PRAGMA busy_timeout=5000")
            secure_delete = conn.execute("PRAGMA secure_delete=ON").fetchone()
            if secure_delete is None or int(secure_delete[0]) != 1:
                raise RuntimeError("SQLite secure deletion is unavailable")
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
        self._assert_storage_files_trusted()
        try:
            metadata = self.db_path.lstat()
        except FileNotFoundError:
            return False, False
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size == 0:
            return False, False
        expected_identity = (int(metadata.st_dev), int(metadata.st_ino))
        try:
            conn = sqlite3.connect(
                self.db_path.as_uri() + "?mode=ro",
                uri=True,
                timeout=5.0,
            )
            try:
                self._require_database_identity(expected_identity)
                _enable_recursive_triggers(conn)
                conn.execute("PRAGMA busy_timeout=5000")
                conn.row_factory = sqlite3.Row
                journal_row = conn.execute("PRAGMA journal_mode").fetchone()
                journal_ready = bool(journal_row and str(journal_row[0]).casefold() == "wal")
                # Every integrity predicate must observe one SQLite snapshot.
                # Without an explicit read transaction, a concurrent writer can
                # commit between the counter and MAX(sequence) queries and make
                # healthy state look corrupt during another Store's startup.
                conn.execute("BEGIN")
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
                if observed_version == _SCHEMA_VERSION:
                    if (
                        not _v20_receipt_schema_is_current(conn)
                        or not remediation_indexes_are_current(conn)
                        or not remediation_authority_schema_is_current(conn)
                        or not agent_import_event_sequence_schema_is_current(conn)
                    ):
                        return False, journal_ready
                    ensure_correlation_key_integrity(
                        conn,
                        allow_initialize=False,
                    )
                    ensure_remediation_authority_key_integrity(
                        conn,
                        allow_initialize=False,
                    )
                    invalid_sequence = conn.execute(
                        "SELECT 1 FROM runs WHERE typeof(turn_sequence) <> 'integer' "
                        "OR turn_sequence <= 0 UNION ALL SELECT 1 FROM trace_tombstones "
                        "WHERE typeof(turn_sequence) <> 'integer' OR turn_sequence <= 0 "
                        "LIMIT 1"
                    ).fetchone()
                    if invalid_sequence is not None:
                        raise RuntimeError("turn sequence integrity is invalid")
                    invalid_revision = conn.execute(
                        "SELECT 1 FROM runs WHERE typeof(evidence_revision) <> 'integer' "
                        "OR evidence_revision <= 0 LIMIT 1"
                    ).fetchone()
                    if invalid_revision is not None:
                        raise RuntimeError("evidence revision integrity is invalid")
                    barrier_error = retired_barrier_integrity_error(conn)
                    if barrier_error is not None:
                        raise RuntimeError(barrier_error)
                    if not trace_tombstone_turn_sequence_is_unique(conn):
                        raise RuntimeError("retired-trace sequence index integrity is invalid")
                    _validate_turn_sequence_counter(conn)
                    _validate_roster_generation_counter(conn)
                    validate_stored_source_identities(conn)
                    if source_redaction_purge_pending(conn):
                        return False, journal_ready
                return observed_version == _SCHEMA_VERSION, journal_ready
            finally:
                if getattr(conn, "in_transaction", False):
                    try:
                        conn.rollback()
                    finally:
                        conn.close()
                else:
                    conn.close()
        except PermissionError:
            raise
        except (OSError, sqlite3.Error):
            return False, False

    def _database_identity(self) -> tuple[int, int]:
        """Return the stable regular-file identity SQLite is about to open."""

        try:
            metadata = self.db_path.lstat()
        except FileNotFoundError as exc:
            raise PermissionError("Agency Runtime database disappeared before open") from exc
        if _metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
            raise PermissionError("Agency Runtime database must be one regular non-link file")
        if int(getattr(metadata, "st_nlink", 0) or 0) != 1:
            raise PermissionError("Agency Runtime database must have exactly one hard link")
        identity = int(metadata.st_dev), int(metadata.st_ino)
        if identity[1] <= 0:
            raise PermissionError("Agency Runtime database identity is unavailable")
        if not _storage_file_is_trusted(self.db_path):
            raise PermissionError("Agency Runtime database is not a trusted current-user file")
        return identity

    def _require_database_identity(self, expected: tuple[int, int]) -> None:
        """Fail if SQLite's path target changed across its pathname open."""

        if self._database_identity() != expected:
            raise PermissionError("Agency Runtime database changed during SQLite open")

    def _init_schema(self, *, capture_content: bool | None = None) -> None:
        conn = self._connect()
        try:
            capture_policy = (
                self._capture_content_enabled
                if capture_content is None
                else lambda: capture_content
            )
            purge_required = migrate_schema(
                conn,
                now=self._now,
                capture_content=capture_policy,
            )
            conn.commit()
            if purge_required:
                self._purge_redacted_storage(conn)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _purge_redacted_storage(self, conn: sqlite3.Connection) -> None:
        """Physically purge sensitive legacy bytes before clearing recovery state."""

        expected_identity = self._database_identity()
        conn.execute("VACUUM")
        checkpoint = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if (
            checkpoint is None
            or len(checkpoint) < 3
            or any(
                isinstance(value, bool) or not isinstance(value, int) for value in checkpoint[:3]
            )
            or int(checkpoint[0]) != 0
            or int(checkpoint[1]) != 0
            or int(checkpoint[2]) != 0
        ):
            raise RuntimeError("SQLite source redaction purge did not complete")
        self._require_database_identity(expected_identity)
        self._assert_storage_paths_safe()
        self._assert_storage_files_trusted()
        cleared = conn.execute(
            "UPDATE store_counters SET value = 0 WHERE name = 'source-redaction-purge-pending'"
        )
        if cleared.rowcount != 1:
            raise RuntimeError("source redaction purge state could not be completed")
        conn.commit()
        self._require_database_identity(expected_identity)
        self._repair_storage_permissions()

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
            capture_content=self._capture_content_enabled(),
        )

    def _ensure_run(
        self,
        conn: sqlite3.Connection,
        *,
        trace_id: str,
        session_id: str | None = "",
        host: str = "unknown",
    ) -> None:
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        if session_id is not None:
            session_id = validate_correlation_id(
                session_id,
                field="session_id",
                required=False,
            )
        existing = conn.execute(
            "SELECT session_id, status FROM runs WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
        if existing is not None:
            existing_session = str(existing["session_id"] or "")
            if session_id is not None and existing_session != str(session_id or ""):
                raise ValueError("trace_id already belongs to a different session")
            if str(existing["status"]) not in {"active", "evidence_only"}:
                raise ValueError("trace_id belongs to a terminal turn")
            conn.execute(
                f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE trace_id = ?",
                (trace_id,),
            )
            return
        self._assert_trace_not_retired(conn, trace_id)
        created_at = self._now()
        conn.execute(
            "INSERT INTO runs "
            "(id, trace_id, session_id, host, started_at, last_activity_at, "
            "status, user_message, metadata) "
            f"VALUES (?, ?, ?, ?, ?, {STORE_CLOCK_SQL}, "  # nosec B608
            "'evidence_only', '', ?)",
            (
                self._uuid(),
                trace_id,
                str(session_id or ""),
                host or "unknown",
                created_at,
                json.dumps({"implicit": True}),
            ),
        )

    def _require_open_run(
        self,
        conn: sqlite3.Connection,
        *,
        trace_id: str,
        session_id: str | None = None,
        touch: bool = True,
    ) -> sqlite3.Row:
        """Require one existing open parent without compatibility creation."""

        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_session = (
            validate_correlation_id(session_id, field="session_id")
            if session_id is not None
            else None
        )
        run = conn.execute(
            "SELECT * FROM runs WHERE trace_id = ?",
            (normalized_trace,),
        ).fetchone()
        if run is None:
            raise ValueError("correlated run does not exist")
        if normalized_session is not None and str(run["session_id"] or "") != normalized_session:
            raise ValueError("trace_id already belongs to a different session")
        if str(run["status"] or "") not in {"active", "evidence_only"}:
            raise ValueError("trace_id belongs to a terminal turn")
        if touch:
            conn.execute(
                f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE id = ?",
                (run["id"],),
            )
        return run

    @staticmethod
    def _assert_trace_not_retired(conn: sqlite3.Connection, trace_id: str) -> None:
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        digest = correlation_digest(conn, trace_id, domain="trace")
        row = conn.execute(
            "SELECT 1 FROM trace_tombstones WHERE trace_digest = ? LIMIT 1",
            (digest,),
        ).fetchone()
        if row is not None:
            raise ValueError("trace_id was permanently retired by retention")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4())

    # ── Finalization ───────────────────────────────────────────────

    def record_finalization(
        self,
        *,
        trace_id: str,
        host: str,
        action: str,
        missing: list[str] | None = None,
        response_hash: str = "",
    ) -> str:
        event_id = self._uuid()
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._require_open_run(
                conn,
                trace_id=trace_id,
                session_id=None,
            )
            conn.execute(
                "INSERT INTO finalization_events "
                "(id, trace_id, host, action, missing, response_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    trace_id,
                    host,
                    action,
                    json.dumps(missing) if missing else None,
                    str(response_hash or "").strip() or None,
                    self._now(),
                ),
            )
            conn.commit()
            return event_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def validate_pending_retry_receipt(
        self,
        session_id: str,
        receipt_id: str,
        *,
        trace_id: str = "",
    ) -> str | None:
        """Resolve one authenticated retry receipt for the unique open turn."""
        normalized_session = (
            validate_correlation_id(session_id, field="session_id") if session_id else ""
        )
        normalized_receipt = str(receipt_id or "").strip()
        normalized_trace = validate_correlation_id(
            trace_id,
            field="trace_id",
            required=False,
        )
        if not normalized_session or not normalized_receipt:
            return None
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT run.trace_id FROM finalization_events AS event "
                "JOIN runs AS run ON run.trace_id = event.trace_id "
                "WHERE event.id = ? AND event.action = 'continue' "
                "AND event.terminal_status IS NULL AND run.session_id = ? "
                "AND run.status IN ('active', 'evidence_only') "
                "AND run.ended_at IS NULL AND (? = '' OR run.trace_id = ?) "
                "AND NOT EXISTS (SELECT 1 FROM runs AS other "
                "WHERE other.session_id = run.session_id "
                "AND other.status IN ('active', 'evidence_only') "
                "AND other.ended_at IS NULL AND other.trace_id <> run.trace_id) "
                "LIMIT 1",
                (
                    normalized_receipt,
                    normalized_session,
                    normalized_trace,
                    normalized_trace,
                ),
            ).fetchone()
            return str(row["trace_id"]) if row is not None else None
        finally:
            conn.close()

    def resolve_pending_internal_retry(
        self,
        session_id: str,
        trace_id: str,
    ) -> str | None:
        """Resolve an internal retry from exact durable lifecycle correlation.

        Unlike the compatibility receipt validator, this authority decision
        does not inspect assistant feedback or user-message content.
        """

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT run.trace_id FROM runs AS run "
                "WHERE run.session_id = ? AND run.trace_id = ? "
                "AND run.status IN ('active', 'evidence_only') "
                "AND run.ended_at IS NULL "
                "AND EXISTS (SELECT 1 FROM finalization_events AS event "
                "WHERE event.trace_id = run.trace_id AND event.action = 'continue' "
                "AND event.terminal_status IS NULL) "
                "AND NOT EXISTS (SELECT 1 FROM runs AS other "
                "WHERE other.session_id = run.session_id "
                "AND other.status IN ('active', 'evidence_only') "
                "AND other.ended_at IS NULL AND other.trace_id <> run.trace_id) "
                "LIMIT 1",
                (normalized_session, normalized_trace),
            ).fetchone()
            return str(row["trace_id"]) if row is not None else None
        finally:
            conn.close()

    def has_finalization_action(
        self,
        trace_id: str,
        action: str,
        *,
        response_hash: str = "",
    ) -> bool:
        """Return whether one exact turn has durably recorded an action."""
        normalized_trace = validate_correlation_id(trace_id, field="trace_id") if trace_id else ""
        normalized_action = str(action or "").strip()
        if not normalized_trace or not normalized_action:
            return False
        conn = self._connect()
        try:
            normalized_hash = str(response_hash or "").strip()
            if normalized_hash:
                row = conn.execute(
                    "SELECT 1 FROM finalization_events "
                    "WHERE trace_id = ? AND action = ? AND response_hash = ? LIMIT 1",
                    (normalized_trace, normalized_action, normalized_hash),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT 1 FROM finalization_events WHERE trace_id = ? AND action = ? LIMIT 1",
                    (normalized_trace, normalized_action),
                ).fetchone()
            return row is not None
        finally:
            conn.close()

    def claim_continuation(
        self,
        *,
        session_id: str,
        trace_id: str,
        host: str,
        response_hash: str,
        retry_active: bool = False,
        missing: list[str] | None = None,
    ) -> dict[str, str]:
        """Atomically claim or classify one host continuation response."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_host = str(host or "unknown").strip()[:64] or "unknown"
        normalized_hash = _require_response_hash(response_hash)
        if not isinstance(retry_active, bool):
            raise ValueError("retry_active must be a boolean")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._require_open_run(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
            )
            existing = conn.execute(
                "SELECT id, response_hash FROM finalization_events "
                "WHERE trace_id = ? AND action = 'continue' "
                "AND terminal_status IS NULL AND length(response_hash) = 64 "
                "AND response_hash NOT GLOB '*[^0-9a-f]*' "
                "ORDER BY created_at, rowid LIMIT 1",
                (normalized_trace,),
            ).fetchone()
            if retry_active:
                outcome = "exhausted"
                receipt_id = str(existing["id"] or "") if existing is not None else ""
            elif existing is not None:
                receipt_id = str(existing["id"] or "")
                outcome = (
                    "replay"
                    if str(existing["response_hash"] or "") == normalized_hash
                    else "exhausted"
                )
            else:
                receipt_id = self._uuid()
                conn.execute(
                    "INSERT INTO finalization_events "
                    "(id, trace_id, host, action, missing, response_hash, created_at) "
                    "VALUES (?, ?, ?, 'continue', ?, ?, ?)",
                    (
                        receipt_id,
                        normalized_trace,
                        normalized_host,
                        json.dumps(missing) if missing else None,
                        normalized_hash,
                        self._now(),
                    ),
                )
                outcome = "claimed"
            conn.commit()
            return {
                "outcome": outcome,
                "receipt_id": receipt_id,
                "response_hash": normalized_hash,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_completion_evidence_snapshot(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """Read one internally consistent, content-free completion snapshot."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT trace_id, session_id, host, status, ended_at, "
                "terminal_finalization_id, evidence_revision, "
                "preflight_state, preflight_result, "
                "COALESCE(NULLIF(preflight_request_kind, ''), CASE "
                "WHEN json_valid(metadata) THEN json_extract(metadata, '$.request_kind') "
                "ELSE '' END, '') AS request_kind "
                "FROM runs WHERE trace_id = ?",
                (normalized_trace,),
            ).fetchone()
            if run is None:
                raise ValueError("trace_id does not identify a recorded Agency turn")
            if str(run["session_id"] or "") != normalized_session:
                raise ValueError("trace_id does not belong to session_id")
            if str(run["status"] or "") in {"active", "evidence_only"} and (
                bool(run["ended_at"]) or bool(run["terminal_finalization_id"])
            ):
                raise RuntimeError("open Agency turn has inconsistent terminal state")
            receipt = conn.execute(
                "SELECT id, trace_id, session_id, host, requested_model, model_group, "
                "resolved_provider, resolved_model, attempted_fallbacks, model_id, "
                "source, recorded_at, started_at, ended_at, status "
                "FROM model_receipts WHERE trace_id = ? AND session_id = ? "
                f"ORDER BY {MODEL_RECEIPT_AUTHORITY_ORDER_SQL} LIMIT 1",  # nosec B608
                (normalized_trace, normalized_session),
            ).fetchone()
            skills = [
                str(row["skill_name"])
                for row in conn.execute(
                    "SELECT skill_name FROM skills_loaded "
                    "WHERE session_id = ? AND trace_id = ? "
                    "ORDER BY loaded_at, rowid",
                    (normalized_session, normalized_trace),
                ).fetchall()
            ]
            specialists = [
                str(row["agent_slug"])
                for row in conn.execute(
                    "SELECT agent_slug FROM specialists_loaded "
                    "WHERE session_id = ? AND trace_id = ? "
                    "ORDER BY loaded_at, rowid",
                    (normalized_session, normalized_trace),
                ).fetchall()
            ]
            ready_preflight = str(run["preflight_state"] or "") == "ready"
            recipe = (
                _decode_preflight_recipe(
                    run["preflight_result"],
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                )
                if ready_preflight
                else None
            )
            if ready_preflight and recipe is None:
                raise RuntimeError("ready preflight recipe failed integrity validation")
            if recipe is not None:
                for reference in recipe["specialist_refs"]:
                    self._reject_disabled_specialist(
                        conn,
                        session_id=normalized_session,
                        trace_id=normalized_trace,
                        specialist_slug=str(reference["slug"]),
                    )
            selected_specialists = (
                [dict(reference) for reference in recipe["specialist_refs"]]
                if recipe is not None
                else []
            )
            specialist_activations = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, session_id, trace_id, work_unit_id, specialist_slug, "
                    "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
                    "native_run_id, created_at, consumed_at, delegation_event_id "
                    "FROM delegation_activation_receipts WHERE session_id = ? "
                    "AND trace_id = ? AND consumed_at IS NOT NULL "
                    "ORDER BY consumed_at, rowid",
                    (normalized_session, normalized_trace),
                ).fetchall()
            ]
            if recipe is not None and recipe["delivery_mode"] == "isolated":
                specialists = list(
                    dict.fromkeys(str(row["specialist_slug"]) for row in specialist_activations)
                )
            delegations = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, trace_id, session_id, host, work_unit_id, "
                    "recommended_agent, status, backend, executed_worker_kind, "
                    "executed_worker_id, native_run_id, retrieved_specialist_slug, "
                    "retrieved_specialist_version, retrieved_specialist_prompt_hash, "
                    "activation_receipt_id, skip_reason, error, "
                    "started_at, completed_at FROM delegation_events "
                    "WHERE trace_id = ? AND session_id = ? "
                    "ORDER BY started_at, rowid",
                    (normalized_trace, normalized_session),
                ).fetchall()
            ]
            unit_agent_plan = (
                [dict(row) for row in recipe.get("unit_agent_plan", [])]
                if recipe is not None
                else []
            )
            raw_classification = recipe.get("turn_classification") if recipe is not None else None
            if isinstance(raw_classification, dict):
                turn_classification = dict(raw_classification)
            else:
                selection_required = str(run["request_kind"] or "") == "nontrivial"
                turn_classification = {
                    "turn_kind": ("new_intent" if selection_required else "acknowledgement"),
                    "selection_required": selection_required,
                    "reroute_required": selection_required,
                    "execution_decision_required": selection_required,
                    "continuation_of": "",
                    "confidence": 1.0,
                    "reason_codes": ["legacy_request_kind_projection"],
                    "state_revision": "",
                    "classifier_version": 0,
                }
            raw_resident_binding = (
                recipe.get("resident_manager_binding") if recipe is not None else None
            )
            resident_manager_binding = (
                dict(raw_resident_binding) if isinstance(raw_resident_binding, dict) else None
            )
            raw_resident_kernel = (
                resident_manager_binding.get("kernel")
                if resident_manager_binding is not None
                else (recipe.get("resident_manager_kernel") if recipe is not None else None)
            )
            resident_manager_kernel = (
                dict(raw_resident_kernel) if isinstance(raw_resident_kernel, dict) else None
            )
            resident_managers = (
                list(resident_manager_kernel.get("slugs", []))
                if resident_manager_kernel is not None
                else []
            )
            run_projection = dict(run)
            run_projection.pop("preflight_result", None)
            run_projection.update(turn_classification)
            snapshot = {
                "session_id": normalized_session,
                "trace_id": normalized_trace,
                "status": str(run["status"] or ""),
                "request_kind": str(run["request_kind"] or ""),
                **turn_classification,
                "evidence_revision": int(run["evidence_revision"]),
                "run": run_projection,
                "model_receipt": dict(receipt) if receipt is not None else None,
                "skills": skills,
                "specialists": specialists,
                "resident_managers": resident_managers,
                "resident_manager_kernel": resident_manager_kernel,
                "resident_manager_binding": resident_manager_binding,
                "preflight_recipe_version": (
                    int(recipe["recipe_version"]) if recipe is not None else 0
                ),
                "delivery_mode": str(recipe["delivery_mode"]) if recipe is not None else "",
                "selected_specialists": selected_specialists,
                "specialist_activations": specialist_activations,
                "delegations": delegations,
                "unit_agent_plan": unit_agent_plan,
            }
            conn.commit()
            return snapshot
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _terminal_finalization_result(
        *,
        outcome: str,
        authoritative: bool,
        session_id: str,
        trace_id: str,
        action: str,
        response_hash: str,
        status: str,
        policy_response_hash: str = "",
        event_id: str = "",
    ) -> dict[str, Any]:
        return {
            "outcome": outcome,
            "authoritative": authoritative,
            "event_id": event_id,
            "session_id": session_id,
            "trace_id": trace_id,
            "action": action,
            "response_hash": response_hash,
            "policy_response_hash": policy_response_hash,
            "status": status,
        }

    def commit_terminal_finalization(
        self,
        *,
        session_id: str,
        trace_id: str,
        host: str,
        action: str,
        response_hash: str,
        status: str,
        expected_evidence_revision: int,
        policy_response_hash: str = "",
        missing: list[str] | None = None,
        pending_interaction_kind: str = "",
        pending_interaction_fingerprint: str = "",
    ) -> dict[str, Any]:
        """Bind a terminal response only if its validated evidence is unchanged."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_host = str(host or "unknown").strip()[:64] or "unknown"
        normalized_action = str(action or "").strip()[:64]
        normalized_hash = _require_response_hash(response_hash)
        normalized_policy_hash = _optional_response_hash(policy_response_hash)
        normalized_status = str(status or "").strip()[:64]
        normalized_pending = str(pending_interaction_kind or "").strip()
        normalized_pending_fingerprint = str(pending_interaction_fingerprint or "").strip()
        if not normalized_action:
            raise ValueError("action is required for terminal finalization")
        if not normalized_status or normalized_status in {"active", "evidence_only"}:
            raise ValueError("terminal finalization requires a terminal status")
        if normalized_pending not in {"", "question", "authorization"}:
            raise ValueError("pending_interaction_kind is invalid")
        if bool(normalized_pending) != bool(normalized_pending_fingerprint):
            raise ValueError("pending interaction kind and fingerprint must be paired")
        if normalized_pending_fingerprint:
            _require_response_hash(normalized_pending_fingerprint)
        if (
            isinstance(expected_evidence_revision, bool)
            or not isinstance(expected_evidence_revision, int)
            or expected_evidence_revision <= 0
        ):
            raise ValueError("expected_evidence_revision must be a positive integer")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT id, session_id, status, ended_at, terminal_finalization_id, "
                "evidence_revision, metadata "
                "FROM runs WHERE trace_id = ?",
                (normalized_trace,),
            ).fetchone()
            if run is None or str(run["session_id"] or "") != normalized_session:
                conn.commit()
                return self._terminal_finalization_result(
                    outcome="not_active",
                    authoritative=False,
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                    action=normalized_action,
                    response_hash=normalized_hash,
                    policy_response_hash=normalized_policy_hash,
                    status=normalized_status,
                )

            binding = str(run["terminal_finalization_id"] or "")
            if binding:
                terminal_metadata = _bounded_run_metadata(run["metadata"])
                event = conn.execute(
                    "SELECT id, trace_id, action, response_hash, policy_response_hash, "
                    "terminal_status "
                    "FROM finalization_events WHERE id = ?",
                    (binding,),
                ).fetchone()
                exact_replay = bool(
                    event is not None
                    and str(event["trace_id"] or "") == normalized_trace
                    and str(event["action"] or "") == normalized_action
                    and str(event["response_hash"] or "") == normalized_hash
                    and str(event["policy_response_hash"] or "") == normalized_policy_hash
                    and str(event["terminal_status"] or "") == normalized_status
                    and str(run["status"] or "") == normalized_status
                    and bool(run["ended_at"])
                    and str(terminal_metadata.get("pending_interaction") or "")
                    == normalized_pending
                    and str(terminal_metadata.get("pending_interaction_fingerprint") or "")
                    == normalized_pending_fingerprint
                )
                conn.commit()
                return self._terminal_finalization_result(
                    outcome="replay" if exact_replay else "conflict",
                    authoritative=exact_replay,
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                    action=normalized_action,
                    response_hash=normalized_hash,
                    policy_response_hash=normalized_policy_hash,
                    status=normalized_status,
                    event_id=binding,
                )

            if str(run["status"] or "") not in {"active", "evidence_only"}:
                conn.commit()
                return self._terminal_finalization_result(
                    outcome="not_active",
                    authoritative=False,
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                    action=normalized_action,
                    response_hash=normalized_hash,
                    policy_response_hash=normalized_policy_hash,
                    status=normalized_status,
                )

            if bool(run["ended_at"]):
                conn.commit()
                return self._terminal_finalization_result(
                    outcome="lifecycle_conflict",
                    authoritative=False,
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                    action=normalized_action,
                    response_hash=normalized_hash,
                    policy_response_hash=normalized_policy_hash,
                    status=normalized_status,
                )

            if int(run["evidence_revision"]) != expected_evidence_revision:
                conn.commit()
                return self._terminal_finalization_result(
                    outcome="stale_evidence",
                    authoritative=False,
                    session_id=normalized_session,
                    trace_id=normalized_trace,
                    action=normalized_action,
                    response_hash=normalized_hash,
                    policy_response_hash=normalized_policy_hash,
                    status=normalized_status,
                )

            event_id = self._uuid()
            closed_at = self._now()
            terminal_metadata = _merge_projected_run_metadata(
                run["metadata"],
                {
                    "pending_interaction": normalized_pending,
                    "pending_interaction_fingerprint": normalized_pending_fingerprint,
                },
            )
            conn.execute(
                "INSERT INTO finalization_events "
                "(id, trace_id, host, action, missing, response_hash, "
                "policy_response_hash, terminal_status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    normalized_trace,
                    normalized_host,
                    normalized_action,
                    json.dumps(missing) if missing else None,
                    normalized_hash,
                    normalized_policy_hash or None,
                    normalized_status,
                    closed_at,
                ),
            )
            closed = conn.execute(
                "UPDATE runs SET ended_at = COALESCE(ended_at, ?), status = ?, "
                "terminal_finalization_id = ?, metadata = ?, "
                f"last_activity_at = {STORE_CLOCK_SQL} WHERE id = ? "  # nosec B608
                "AND terminal_finalization_id IS NULL "
                "AND status IN ('active', 'evidence_only')",
                (closed_at, normalized_status, event_id, terminal_metadata, run["id"]),
            )
            if closed.rowcount != 1:
                raise RuntimeError("terminal finalization compare-and-swap failed")
            conn.execute(
                "UPDATE specialists_loaded SET expired_at = ? "
                "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                (closed_at, normalized_session, normalized_trace),
            )
            conn.commit()
            return self._terminal_finalization_result(
                outcome="committed",
                authoritative=True,
                session_id=normalized_session,
                trace_id=normalized_trace,
                action=normalized_action,
                response_hash=normalized_hash,
                policy_response_hash=normalized_policy_hash,
                status=normalized_status,
                event_id=event_id,
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_authoritative_finalization(
        self,
        session_id: str,
        trace_id: str,
        *,
        action: str = "",
        response_hash: str = "",
        policy_response_hash: str = "",
    ) -> dict[str, Any] | None:
        """Read only the terminal event explicitly bound to one exact run."""

        normalized_session = (
            validate_correlation_id(session_id, field="session_id") if session_id else ""
        )
        normalized_trace = validate_correlation_id(trace_id, field="trace_id") if trace_id else ""
        normalized_action = str(action or "").strip()
        normalized_hash = str(response_hash or "").strip()
        normalized_policy_hash = str(policy_response_hash or "").strip()
        if not normalized_session or not normalized_trace:
            return None
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT event.id, event.trace_id, event.host, event.action, "
                "event.missing, event.response_hash, event.policy_response_hash, "
                "event.terminal_status, "
                "event.created_at, run.session_id, run.status, run.ended_at "
                "FROM runs AS run JOIN finalization_events AS event "
                "ON event.id = run.terminal_finalization_id "
                "WHERE run.session_id = ? AND run.trace_id = ? "
                "AND event.trace_id = run.trace_id "
                "AND event.terminal_status = run.status AND run.ended_at IS NOT NULL "
                "AND (? = '' OR event.action = ?) "
                "AND (? = '' OR event.response_hash = ?) "
                "AND (? = '' OR event.policy_response_hash = ?)",
                (
                    normalized_session,
                    normalized_trace,
                    normalized_action,
                    normalized_action,
                    normalized_hash,
                    normalized_hash,
                    normalized_policy_hash,
                    normalized_policy_hash,
                ),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["authoritative"] = True
            return result
        finally:
            conn.close()

    def find_authoritative_trace(
        self,
        session_id: str,
        *,
        action: str = "accept",
        response_hash: str,
    ) -> str | None:
        """Return one unambiguous bound trace for an exact session response."""

        return self._find_authoritative_trace_by_hash(
            session_id,
            action=action,
            response_hash=response_hash,
            use_policy_hash=False,
        )

    def find_authoritative_trace_by_policy_hash(
        self,
        session_id: str,
        *,
        action: str = "accept",
        policy_response_hash: str,
    ) -> str | None:
        """Return the unambiguous latest trace bound to exact policy text."""

        return self._find_authoritative_trace_by_hash(
            session_id,
            action=action,
            response_hash=policy_response_hash,
            use_policy_hash=True,
        )

    def _find_authoritative_trace_by_hash(
        self,
        session_id: str,
        *,
        action: str,
        response_hash: str,
        use_policy_hash: bool,
    ) -> str | None:
        """Resolve one exact terminal hash only when it names the latest turn."""

        normalized_session = (
            validate_correlation_id(session_id, field="session_id") if session_id else ""
        )
        normalized_action = str(action or "").strip()
        normalized_hash = str(response_hash or "").strip()
        if not normalized_session or not normalized_action or not normalized_hash:
            return None
        hash_query = (
            "SELECT run.trace_id, run.turn_sequence FROM runs AS run "
            "JOIN finalization_events AS event "
            "ON event.id = run.terminal_finalization_id "
            "WHERE run.session_id = ? "
            "AND event.trace_id = run.trace_id AND event.action = ? "
            "AND event.policy_response_hash = ? "
            "AND event.terminal_status = run.status "
            "AND run.ended_at IS NOT NULL "
            "ORDER BY run.turn_sequence DESC LIMIT 1"
            if use_policy_hash
            else "SELECT run.trace_id, run.turn_sequence FROM runs AS run "
            "JOIN finalization_events AS event "
            "ON event.id = run.terminal_finalization_id "
            "WHERE run.session_id = ? "
            "AND event.trace_id = run.trace_id AND event.action = ? "
            "AND event.response_hash = ? AND event.terminal_status = run.status "
            "AND run.ended_at IS NOT NULL "
            "ORDER BY run.turn_sequence DESC LIMIT 1"
        )
        conn = self._connect()
        try:
            latest = conn.execute(
                "SELECT trace_id, turn_sequence FROM runs WHERE session_id = ? "
                "ORDER BY turn_sequence DESC LIMIT 1",
                (normalized_session,),
            ).fetchone()
            if latest is None:
                return None
            session_digest = correlation_digest(
                conn,
                normalized_session,
                domain="session",
            )
            barrier = conn.execute(
                "SELECT MAX(turn_sequence) AS turn_sequence FROM trace_tombstones "
                "WHERE session_digest = ?",
                (session_digest,),
            ).fetchone()
            if barrier is not None and int(barrier["turn_sequence"] or 0) >= int(
                latest["turn_sequence"] or 0
            ):
                return None
            rows = conn.execute(
                hash_query,
                (
                    normalized_session,
                    normalized_action,
                    normalized_hash,
                ),
            ).fetchall()
            if len(rows) != 1:
                return None
            row = rows[0]
            if str(row["trace_id"]) != str(latest["trace_id"]) or int(
                row["turn_sequence"] or 0
            ) != int(latest["turn_sequence"] or 0):
                return None
            return str(row["trace_id"])
        finally:
            conn.close()
