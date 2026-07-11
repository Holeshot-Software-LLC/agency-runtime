"""SQLite canonical store for Agency Runtime.

All runtime state — runs, model receipts, skills, specialists, delegations,
roster — lives here. No loose JSON files.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit


_RUN_CONTENT_LIMIT = 2_000
_DELEGATION_DETAIL_LIMIT = 2_000
_DIAGNOSTIC_REASON_LIMIT = 160
_API_BASE_LIMIT = 512
_SAFE_RUN_METADATA_FIELDS = frozenset(
    {
        "callback",
        "content_capture",
        "event_type",
        "reason_code",
        "request_kind",
        "source",
        "transport",
    }
)
_SAFE_METADATA_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
_REASON_CODE = re.compile(r"[a-z][a-z0-9_.-]{0,95}\Z")
_URL_IN_TEXT = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s<>\"']+")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|authorization|password|passwd|secret|token)"
    r"\b\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_BEARER_TOKEN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")


def _capture_content_enabled() -> bool:
    """Read the explicit content-capture opt-in, failing closed."""
    try:
        from agency_runtime.core.config import load_config

        return bool(load_config().observability.capture_content)
    except Exception:
        return False


def _bounded(value: object, limit: int) -> str:
    """Return bounded text without NULs that can confuse operator surfaces."""
    return str(value or "").replace("\x00", "")[:limit]


def _sanitize_api_base(value: object) -> str:
    """Keep an endpoint useful for diagnostics without credentials or queries."""
    raw = _bounded(value, _API_BASE_LIMIT * 2).strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        if parts.scheme and parts.netloc:
            hostname = parts.hostname or ""
            if ":" in hostname and not hostname.startswith("["):
                hostname = f"[{hostname}]"
            try:
                port = parts.port
            except ValueError:
                port = None
            netloc = hostname + (f":{port}" if port is not None else "")
            return _bounded(
                urlunsplit(SplitResult(parts.scheme, netloc, parts.path, "", "")),
                _API_BASE_LIMIT,
            )
    except (TypeError, ValueError):
        pass

    # Be conservative with malformed or scheme-less values: remove the query,
    # fragment, and any apparent user-info rather than storing the original.
    endpoint = raw.split("#", 1)[0].split("?", 1)[0]
    if "@" in endpoint:
        prefix, endpoint = endpoint.rsplit("@", 1)
        if "://" in prefix:
            endpoint = prefix.split("://", 1)[0] + "://" + endpoint
    endpoint = _BEARER_TOKEN.sub("Bearer [REDACTED]", endpoint)
    endpoint = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", endpoint)
    return _bounded(endpoint, _API_BASE_LIMIT)


def _redact_sensitive_text(value: object, limit: int) -> str:
    """Bound opt-in diagnostic content and redact common credential forms."""
    text = _bounded(value, limit * 2)
    text = _BEARER_TOKEN.sub("Bearer [REDACTED]", text)
    text = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", text)

    def sanitize_url(match: re.Match[str]) -> str:
        token = match.group(0)
        suffix = ""
        while token and token[-1] in ".,;)]}":
            suffix = token[-1] + suffix
            token = token[:-1]
        return _sanitize_api_base(token) + suffix

    return _URL_IN_TEXT.sub(sanitize_url, text)[:limit]


_SAFE_DIAGNOSTIC_MESSAGES = {
    "agency_agents_delegate unavailable",
    "backend command failed",
    "delegate depth limit reached",
    "delegate_task requires a parent agent context.",
    "delegate_task unavailable",
    "delegation not requested",
    "host delegate backend is unavailable",
    "no backend available",
    "no command configured",
    "worker crashed",
}


def _project_delegation_detail(
    value: object,
    *,
    field: str,
    capture_content: bool | None = None,
) -> str:
    """Store raw detail only with opt-in; otherwise emit a safe reason code."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if capture_content is None:
        capture_content = _capture_content_enabled()
    if capture_content:
        return _redact_sensitive_text(raw, _DELEGATION_DETAIL_LIMIT)

    normalized = " ".join(raw.split()).lower()
    if normalized in _SAFE_DIAGNOSTIC_MESSAGES:
        return normalized
    if _REASON_CODE.fullmatch(normalized):
        return normalized

    timeout = re.fullmatch(
        r"backend command timed out after ([0-9]+(?:\.[0-9]+)?)s", normalized
    )
    if timeout:
        return f"backend command timed out after {timeout.group(1)}s"[
            :_DIAGNOSTIC_REASON_LIMIT
        ]
    exit_code = re.search(r"\bexited with (-?[0-9]+)\b", normalized)
    if exit_code:
        return f"backend exited with {exit_code.group(1)}"[:_DIAGNOSTIC_REASON_LIMIT]
    dependency = re.fullmatch(
        r"dependency did not complete successfully:\s*([a-z0-9_.-]{1,64})",
        normalized,
    )
    if dependency:
        return f"dependency did not complete successfully: {dependency.group(1)}"

    classifications = (
        (("timed out", "timeout"), "backend_timeout"),
        (("permission", "denied"), "permission_denied"),
        (("not found", "disappeared", "executable"), "executable_unavailable"),
        (("unavailable",), "backend_unavailable"),
        (("not configured", "no command"), "backend_not_configured"),
        (("dependency", "predecessor"), "dependency_failed"),
        (("merge",), "merge_failed"),
        (("confidence", "threshold"), "below_confidence_threshold"),
        (("policy",), "policy_denied"),
        (("cancel",), "cancelled"),
        (("invalid",), "invalid_request"),
    )
    for needles, reason_code in classifications:
        if any(needle in normalized for needle in needles):
            return reason_code
    return "unspecified_skip" if field == "skip_reason" else "execution_failed"


def _project_run_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Return the fixed metadata projection used even when content is enabled."""
    if not isinstance(metadata, dict):
        return None
    projected: dict[str, bool | int | float | str] = {}
    for key in sorted(_SAFE_RUN_METADATA_FIELDS):
        if key not in metadata:
            continue
        value = metadata[key]
        if isinstance(value, bool):
            projected[key] = value
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            projected[key] = value
        elif isinstance(value, str) and _SAFE_METADATA_LABEL.fullmatch(value):
            projected[key] = value
    return (
        json.dumps(projected, sort_keys=True, separators=(",", ":"))
        if projected
        else None
    )


def _restrict_windows_acl(path: Path, *, directory: bool) -> bool:
    """Best-effort owner-only DACL through Win32 APIs, never a subprocess."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class TrusteeW(ctypes.Structure):
            _fields_ = [
                ("pMultipleTrustee", ctypes.c_void_p),
                ("MultipleTrusteeOperation", wintypes.DWORD),
                ("TrusteeForm", wintypes.DWORD),
                ("TrusteeType", wintypes.DWORD),
                ("ptstrName", wintypes.LPWSTR),
            ]

        class ExplicitAccessW(ctypes.Structure):
            _fields_ = [
                ("grfAccessPermissions", wintypes.DWORD),
                ("grfAccessMode", wintypes.DWORD),
                ("grfInheritance", wintypes.DWORD),
                ("Trustee", TrusteeW),
            ]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_security = advapi32.GetNamedSecurityInfoW
        get_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        get_security.restype = wintypes.DWORD
        set_entries = advapi32.SetEntriesInAclW
        set_entries.argtypes = [
            wintypes.ULONG,
            ctypes.POINTER(ExplicitAccessW),
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        set_entries.restype = wintypes.DWORD
        set_security = advapi32.SetNamedSecurityInfoW
        set_security.argtypes = [
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        set_security.restype = wintypes.DWORD
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        owner_sid = ctypes.c_void_p()
        security_descriptor = ctypes.c_void_p()
        acl = ctypes.c_void_p()
        try:
            code = get_security(
                str(path),
                1,  # SE_FILE_OBJECT
                0x00000001,  # OWNER_SECURITY_INFORMATION
                ctypes.byref(owner_sid),
                None,
                None,
                None,
                ctypes.byref(security_descriptor),
            )
            if code:
                return False
            trustee = TrusteeW(
                None,
                0,
                0,  # TRUSTEE_IS_SID
                1,  # TRUSTEE_IS_USER
                ctypes.cast(owner_sid, wintypes.LPWSTR),
            )
            inheritance = 0x3 if directory else 0
            access = ExplicitAccessW(0x001F01FF, 2, inheritance, trustee)
            code = set_entries(1, ctypes.byref(access), None, ctypes.byref(acl))
            if code:
                return False
            code = set_security(
                str(path),
                1,
                0x00000004 | 0x80000000,  # DACL + protected DACL
                None,
                None,
                acl,
                None,
            )
            return code == 0
        finally:
            if acl:
                kernel32.LocalFree(acl)
            if security_descriptor:
                kernel32.LocalFree(security_descriptor)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return False


def _restrict_path_permissions(path: Path, *, directory: bool) -> None:
    """Repair storage permissions; unsupported filesystems fail closed enough."""
    if not path.exists():
        return
    if os.name == "nt":
        try:
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
        except OSError:
            pass
        _restrict_windows_acl(path, directory=directory)
        return
    expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
    os.chmod(path, expected_mode)
    actual_mode = stat.S_IMODE(path.stat().st_mode)
    if actual_mode != expected_mode:
        raise PermissionError(
            f"could not enforce private permissions on Agency Runtime storage: {path}"
        )


def _default_db_path() -> Path:
    """Resolve DB path from config, honoring the environment per call."""
    if env_path := os.environ.get("AGENCY_DB_PATH"):
        return Path(os.path.expanduser(env_path))
    try:
        from agency_runtime.core.config import load_config

        return load_config().store.resolved_path()
    except Exception:
        return Path.home() / ".agency-runtime" / "agency.db"


_SCHEMA_V1 = """
-- Run tracking
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL UNIQUE,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    user_message TEXT,
    metadata TEXT
);

-- Model receipts (what actually ran)
CREATE TABLE IF NOT EXISTS model_receipts (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    requested_model TEXT,
    model_group TEXT,
    resolved_provider TEXT,
    resolved_model TEXT,
    api_base TEXT,
    attempted_fallbacks INTEGER DEFAULT 0,
    model_id TEXT,
    source TEXT NOT NULL DEFAULT 'unknown',
    started_at TEXT,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
);

-- Skills loaded per session
CREATE TABLE IF NOT EXISTS skills_loaded (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    loaded_at TEXT NOT NULL
);

-- Specialists loaded per session
CREATE TABLE IF NOT EXISTS specialists_loaded (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_slug TEXT NOT NULL,
    loaded_at TEXT NOT NULL
);

-- Delegation events
CREATE TABLE IF NOT EXISTS delegation_events (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    work_unit_id TEXT,
    recommended_agent TEXT,
    status TEXT NOT NULL DEFAULT 'suggested',
    backend TEXT,
    skip_reason TEXT,
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
);

-- Worker runs (delegation execution records)
CREATE TABLE IF NOT EXISTS worker_runs (
    id TEXT PRIMARY KEY,
    delegation_event_id TEXT,
    backend TEXT NOT NULL,
    workdir TEXT,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (delegation_event_id) REFERENCES delegation_events(id)
);

-- Finalization events
CREATE TABLE IF NOT EXISTS finalization_events (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    host TEXT NOT NULL,
    action TEXT NOT NULL,
    missing TEXT,
    created_at TEXT NOT NULL
);

-- Roster tables
CREATE TABLE IF NOT EXISTS agent_sources (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    added_at TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    trusted_for_auto_approve INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_downloads (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    slug TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    hash TEXT,
    content TEXT,
    status TEXT NOT NULL DEFAULT 'quarantined',
    FOREIGN KEY (source_id) REFERENCES agent_sources(id)
);

CREATE TABLE IF NOT EXISTS agent_candidates (
    id TEXT PRIMARY KEY,
    download_id TEXT,
    slug TEXT NOT NULL,
    name TEXT,
    division TEXT,
    categories TEXT,
    capabilities TEXT,
    tool_affinity TEXT,
    prompt_path TEXT,
    source TEXT,
    version TEXT,
    hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    quarantined_at TEXT NOT NULL,
    FOREIGN KEY (download_id) REFERENCES agent_downloads(id)
);

CREATE TABLE IF NOT EXISTS agent_versions (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL,
    version TEXT NOT NULL,
    hash TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(agent_slug, version)
);

CREATE TABLE IF NOT EXISTS agent_categories (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL,
    category TEXT NOT NULL,
    UNIQUE(agent_slug, category)
);

CREATE TABLE IF NOT EXISTS agent_embeddings (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL UNIQUE,
    embedding TEXT,
    model TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_snapshots (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    agent_count INTEGER,
    manifest TEXT,
    activated INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_active (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL UNIQUE,
    name TEXT,
    division TEXT,
    description TEXT,
    source TEXT,
    version TEXT,
    hash TEXT,
    categories TEXT,
    capabilities TEXT,
    tool_affinity TEXT,
    prompt_path TEXT,
    activated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_import_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    agent_slug TEXT,
    detail TEXT,
    created_at TEXT NOT NULL
);

-- Schema version
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Immutable routing decision projections. Raw prompt content is omitted by
-- default; query_hash supports correlation without content capture.
CREATE TABLE IF NOT EXISTS routing_decisions (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    session_id TEXT,
    query_hash TEXT NOT NULL,
    context_fingerprint TEXT,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    selected_ids TEXT,
    semantic_ids TEXT,
    companion_ids TEXT,
    confidence REAL,
    latency_ms INTEGER,
    provider TEXT,
    work_units TEXT,
    decision TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Read-path indexes used by hooks, the dashboard, and retention jobs.
CREATE INDEX IF NOT EXISTS idx_runs_trace_id ON runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_runs_session_started ON runs(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_recent ON runs(started_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_trace_id ON model_receipts(trace_id);
CREATE INDEX IF NOT EXISTS idx_receipts_session_ended ON model_receipts(session_id, ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_recent ON model_receipts(COALESCE(ended_at, started_at) DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_skills_session_loaded ON skills_loaded(session_id, loaded_at);
CREATE INDEX IF NOT EXISTS idx_specialists_session_loaded ON specialists_loaded(session_id, loaded_at);
CREATE INDEX IF NOT EXISTS idx_delegations_trace_id ON delegation_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_delegations_session_started ON delegation_events(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_delegations_recent ON delegation_events(COALESCE(completed_at, started_at) DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_worker_runs_event ON worker_runs(delegation_event_id);
CREATE INDEX IF NOT EXISTS idx_finalization_trace_created ON finalization_events(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_finalization_recent ON finalization_events(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_routing_trace_created ON routing_decisions(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_session_created ON routing_decisions(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_recent ON routing_decisions(created_at DESC, id DESC);
"""

_ALL_TABLES: tuple[str, ...] = (
    "runs",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "delegation_events",
    "worker_runs",
    "finalization_events",
    "routing_decisions",
    "agent_sources",
    "agent_downloads",
    "agent_candidates",
    "agent_versions",
    "agent_categories",
    "agent_embeddings",
    "agent_snapshots",
    "agent_active",
    "agent_import_events",
    "schema_version",
)

_RUNTIME_TABLE_TIMESTAMPS: dict[str, str] = {
    "runs": "COALESCE(ended_at, started_at)",
    "model_receipts": "COALESCE(ended_at, started_at)",
    "skills_loaded": "loaded_at",
    "specialists_loaded": "loaded_at",
    "delegation_events": "COALESCE(completed_at, started_at)",
    "worker_runs": "COALESCE(ended_at, started_at)",
    "finalization_events": "created_at",
    "routing_decisions": "created_at",
}

_RUNTIME_DELETE_ORDER: tuple[str, ...] = (
    "worker_runs",
    "delegation_events",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "finalization_events",
    "routing_decisions",
    "runs",
)


class Store:
    """SQLite-backed canonical store for Agency Runtime."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(os.path.expanduser(str(db_path)))
        else:
            self.db_path = _default_db_path()
        self._permission_fingerprints: dict[Path, tuple[int, int]] = {}
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._ensure_private_storage_file()
        self._foreign_keys_ready = False
        self._init_schema()
        self._foreign_keys_ready = True
        self._repair_storage_permissions()

    def _ensure_private_storage_file(self) -> None:
        """Securely create the DB and repair an existing parent/database."""
        _restrict_path_permissions(self.db_path.parent, directory=True)
        if not self.db_path.exists():
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_BINARY"):
                flags |= os.O_BINARY
            try:
                fd = os.open(self.db_path, flags, stat.S_IRUSR | stat.S_IWUSR)
            except FileExistsError:
                pass
            else:
                os.close(fd)
        _restrict_path_permissions(self.db_path, directory=False)

    def _repair_storage_permissions(self) -> None:
        """Keep the database directory and SQLite sidecars owner-only."""
        targets = (
            (self.db_path.parent, True),
            (self.db_path, False),
            (Path(f"{self.db_path}-wal"), False),
            (Path(f"{self.db_path}-shm"), False),
        )
        for path, directory in targets:
            try:
                current = path.stat()
            except OSError:
                continue
            fingerprint = (int(current.st_dev), int(current.st_ino))
            expected_mode = stat.S_IRWXU if directory else stat.S_IRUSR | stat.S_IWUSR
            if os.name != "nt" and stat.S_IMODE(current.st_mode) == expected_mode:
                continue
            if (
                os.name == "nt"
                and self._permission_fingerprints.get(path) == fingerprint
            ):
                continue
            try:
                _restrict_path_permissions(path, directory=directory)
            except FileNotFoundError:
                # SQLite removes WAL sidecars when the final connection closes.
                continue
            self._permission_fingerprints[path] = fingerprint

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        if self._foreign_keys_ready:
            conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        self._repair_storage_permissions()
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA_V1)
            self._ensure_column(
                conn,
                "agent_sources",
                "trusted_for_auto_approve",
                "INTEGER DEFAULT 0",
            )
            self._migrate_trace_integrity(conn)
            version_row = conn.execute(
                "SELECT MAX(version) AS version FROM schema_version"
            ).fetchone()
            current_version = int(version_row["version"] or 0)
            if current_version < 4:
                self._migrate_private_projections(conn)
            conn.execute("DELETE FROM schema_version")
            conn.execute("INSERT INTO schema_version (version) VALUES (4)")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        """Add a SQLite column when opening a database created by an older build."""
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _runs_trace_is_unique(conn: sqlite3.Connection) -> bool:
        for index in conn.execute("PRAGMA index_list(runs)").fetchall():
            if not bool(index["unique"]):
                continue
            columns = [
                row["name"]
                for row in conn.execute(
                    f"PRAGMA index_info({index['name']})"
                ).fetchall()
            ]
            if columns == ["trace_id"]:
                return True
        return False

    def _migrate_trace_integrity(self, conn: sqlite3.Connection) -> None:
        """Upgrade legacy stores so evidence foreign keys can be enforced."""
        if not self._runs_trace_is_unique(conn):
            conn.execute("DROP TABLE IF EXISTS runs_v2")
            conn.execute(
                "CREATE TABLE runs_v2 ("
                "id TEXT PRIMARY KEY, trace_id TEXT NOT NULL UNIQUE, session_id TEXT, "
                "host TEXT NOT NULL DEFAULT 'unknown', started_at TEXT NOT NULL, ended_at TEXT, "
                "status TEXT NOT NULL DEFAULT 'active', user_message TEXT, metadata TEXT)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO runs_v2 "
                "(id, trace_id, session_id, host, started_at, ended_at, status, user_message, metadata) "
                "SELECT id, trace_id, session_id, host, started_at, ended_at, status, user_message, metadata "
                "FROM runs ORDER BY started_at, rowid"
            )
            conn.execute("DROP TABLE runs")
            conn.execute("ALTER TABLE runs_v2 RENAME TO runs")

        # Older builds wrote child evidence without creating a run. Preserve
        # those records by creating metadata-only parent rows before enabling
        # foreign-key enforcement for normal operation.
        for source_table in ("model_receipts", "delegation_events"):
            conn.execute(
                "INSERT OR IGNORE INTO runs "
                "(id, trace_id, session_id, host, started_at, status, user_message, metadata) "
                f"SELECT lower(hex(randomblob(16))), trace_id, COALESCE(session_id, ''), "
                f"COALESCE(host, 'unknown'), COALESCE(MIN(started_at), ?), "
                "'evidence_only', '', '{\"migrated\":true}' "
                f"FROM {source_table} WHERE trace_id IS NOT NULL GROUP BY trace_id",
                (self._now(),),
            )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_trace_id ON runs(trace_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_runs_session_started "
            "ON runs(session_id, started_at DESC)"
        )

    def _migrate_private_projections(self, conn: sqlite3.Connection) -> None:
        """Sanitize legacy content once when upgrading to the private schema."""
        capture_content = _capture_content_enabled()
        for row in conn.execute(
            "SELECT id, user_message, metadata FROM runs"
        ).fetchall():
            try:
                metadata = json.loads(row["metadata"]) if row["metadata"] else None
            except (json.JSONDecodeError, TypeError):
                metadata = None
            message = (
                _redact_sensitive_text(row["user_message"], _RUN_CONTENT_LIMIT)
                if capture_content
                else ""
            )
            conn.execute(
                "UPDATE runs SET user_message = ?, metadata = ? WHERE id = ?",
                (message, _project_run_metadata(metadata), row["id"]),
            )

        for row in conn.execute("SELECT id, api_base FROM model_receipts").fetchall():
            conn.execute(
                "UPDATE model_receipts SET api_base = ? WHERE id = ?",
                (_sanitize_api_base(row["api_base"]), row["id"]),
            )

        for row in conn.execute(
            "SELECT id, skip_reason, error FROM delegation_events"
        ).fetchall():
            conn.execute(
                "UPDATE delegation_events SET skip_reason = ?, error = ? WHERE id = ?",
                (
                    _project_delegation_detail(
                        row["skip_reason"],
                        field="skip_reason",
                        capture_content=capture_content,
                    ),
                    _project_delegation_detail(
                        row["error"],
                        field="error",
                        capture_content=capture_content,
                    ),
                    row["id"],
                ),
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

    # ── Runs ───────────────────────────────────────────────────────

    def create_run(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        user_message: str = "",
        metadata: dict | None = None,
    ) -> str:
        capture_content = _capture_content_enabled()
        trace_id = trace_id or self._uuid()
        run_id = self._uuid()
        captured_message = (
            _redact_sensitive_text(user_message, _RUN_CONTENT_LIMIT)
            if capture_content
            else ""
        )
        safe_metadata = _project_run_metadata(metadata)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO runs (id, trace_id, session_id, host, started_at, status, user_message, metadata) "
                "VALUES (?, ?, ?, ?, ?, 'active', ?, ?) "
                "ON CONFLICT(trace_id) DO UPDATE SET "
                "session_id = excluded.session_id, host = excluded.host, "
                "started_at = excluded.started_at, ended_at = NULL, status = 'active', "
                "user_message = excluded.user_message, metadata = excluded.metadata",
                (
                    run_id,
                    trace_id,
                    session_id,
                    host,
                    self._now(),
                    captured_message,
                    safe_metadata,
                ),
            )
            row = conn.execute(
                "SELECT id FROM runs WHERE trace_id = ?", (trace_id,)
            ).fetchone()
            conn.commit()
            return str(row["id"])
        finally:
            conn.close()

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE runs SET ended_at = ?, status = ? WHERE id = ?",
                (self._now(), status, run_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Model receipts ─────────────────────────────────────────────

    def record_model_receipt(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        requested_model: str = "",
        model_group: str = "",
        resolved_provider: str = "",
        resolved_model: str = "",
        api_base: str = "",
        attempted_fallbacks: int = 0,
        model_id: str = "",
        source: str = "unknown",
        started_at: str = "",
        ended_at: str = "",
        status: str = "success",
    ) -> str:
        receipt_id = self._uuid()
        trace_id = trace_id or receipt_id
        safe_api_base = _sanitize_api_base(api_base)
        conn = self._connect()
        try:
            self._ensure_run(conn, trace_id=trace_id, session_id=session_id, host=host)
            conn.execute(
                "INSERT INTO model_receipts "
                "(id, trace_id, session_id, host, requested_model, model_group, "
                "resolved_provider, resolved_model, api_base, attempted_fallbacks, "
                "model_id, source, started_at, ended_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    receipt_id,
                    trace_id,
                    session_id,
                    host,
                    requested_model,
                    model_group,
                    resolved_provider,
                    resolved_model,
                    safe_api_base,
                    attempted_fallbacks,
                    model_id,
                    source,
                    started_at or self._now(),
                    ended_at or self._now(),
                    status,
                ),
            )
            conn.commit()
            return receipt_id
        finally:
            conn.close()

    def get_model_receipt(self, trace_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE trace_id = ? ORDER BY id DESC LIMIT 1",
                (trace_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_model_receipt_for_session(self, session_id: str) -> dict[str, Any] | None:
        """Get the most recent model receipt for a session."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE session_id = ? "
                "ORDER BY ended_at DESC, started_at DESC, id DESC LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Skills ─────────────────────────────────────────────────────

    def record_skill_loaded(self, session_id: str, skill_name: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO skills_loaded (id, session_id, skill_name, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (self._uuid(), session_id, skill_name, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_skills_for_session(self, session_id: str) -> list[str]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT skill_name FROM skills_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["skill_name"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Specialists ────────────────────────────────────────────────

    def record_specialist_loaded(self, session_id: str, agent_slug: str) -> None:
        if not session_id or not agent_slug:
            return
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT 1 FROM specialists_loaded WHERE session_id = ? AND agent_slug = ? LIMIT 1",
                (session_id, agent_slug),
            ).fetchone()
            if existing:
                return
            conn.execute(
                "INSERT INTO specialists_loaded (id, session_id, agent_slug, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (self._uuid(), session_id, agent_slug, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_specialists_for_session(self, session_id: str) -> list[str]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["agent_slug"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Delegation events ──────────────────────────────────────────

    def record_delegation(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        work_unit_id: str = "",
        recommended_agent: str = "",
        status: str = "suggested",
        backend: str = "",
        skip_reason: str = "",
        error: str = "",
    ) -> str:
        event_id = self._uuid()
        trace_id = trace_id or event_id
        safe_skip_reason = _project_delegation_detail(skip_reason, field="skip_reason")
        safe_error = _project_delegation_detail(error, field="error")
        conn = self._connect()
        try:
            self._ensure_run(conn, trace_id=trace_id, session_id=session_id, host=host)
            conn.execute(
                "INSERT INTO delegation_events "
                "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
                "status, backend, skip_reason, error, started_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    trace_id,
                    session_id,
                    host,
                    work_unit_id,
                    recommended_agent,
                    status,
                    backend,
                    safe_skip_reason,
                    safe_error,
                    self._now(),
                ),
            )
            conn.commit()
            return event_id
        finally:
            conn.close()

    def update_delegation(
        self,
        event_id: str,
        *,
        status: str,
        backend: str = "",
        error: str = "",
        recommended_agent: str = "",
        skip_reason: str = "",
        host: str = "",
    ) -> None:
        safe_skip_reason = _project_delegation_detail(skip_reason, field="skip_reason")
        safe_error = _project_delegation_detail(error, field="error")
        conn = self._connect()
        try:
            ended = (
                self._now() if status in ("completed", "failed", "skipped") else None
            )
            conn.execute(
                "UPDATE delegation_events "
                "SET status = ?, "
                "host = COALESCE(NULLIF(?, ''), host), "
                "backend = COALESCE(NULLIF(?, ''), backend), "
                "error = ?, "
                "recommended_agent = COALESCE(NULLIF(?, ''), recommended_agent), "
                "skip_reason = COALESCE(NULLIF(?, ''), skip_reason), "
                "completed_at = COALESCE(?, completed_at) "
                "WHERE id = ?",
                (
                    status,
                    host,
                    backend,
                    safe_error,
                    recommended_agent,
                    safe_skip_reason,
                    ended,
                    event_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM delegation_events WHERE trace_id = ? ORDER BY started_at",
                (trace_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_delegations_for_session(
        self, session_id: str, statuses: list[str] | tuple[str, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Return delegation events for a session, optionally filtered by status."""
        conn = self._connect()
        try:
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                cur = conn.execute(
                    f"SELECT * FROM delegation_events WHERE session_id = ? AND status IN ({placeholders}) ORDER BY started_at",
                    (session_id, *statuses),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM delegation_events WHERE session_id = ? ORDER BY started_at",
                    (session_id,),
                )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Maintenance ────────────────────────────────────────────────

    def runtime_table_counts(self) -> dict[str, int]:
        """Return row counts for every Agency Runtime SQLite table."""
        conn = self._connect()
        try:
            counts: dict[str, int] = {}
            for table in _ALL_TABLES:
                cur = conn.execute(f"SELECT COUNT(*) AS count FROM {table}")
                counts[table] = int(cur.fetchone()["count"])
            return counts
        finally:
            conn.close()

    def database_stats(self) -> dict[str, Any]:
        """Return database size and row-count stats for CLI maintenance."""

        return {
            **self.database_sizes(),
            "tables": self.runtime_table_counts(),
        }

    def database_sizes(self) -> dict[str, Any]:
        """Return cheap database and sidecar sizes without scanning tables."""

        wal_path = Path(f"{self.db_path}-wal")
        shm_path = Path(f"{self.db_path}-shm")
        return {
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size
            if self.db_path.exists()
            else 0,
            "wal_size_bytes": wal_path.stat().st_size if wal_path.exists() else 0,
            "shm_size_bytes": shm_path.stat().st_size if shm_path.exists() else 0,
        }

    def recent_runtime_activity(
        self, *, limit: int = 50
    ) -> dict[str, list[dict[str, Any]]]:
        """Return bounded metadata-only activity for operator surfaces.

        Raw prompts, worker stdout/stderr, API bases, and other potentially
        sensitive content are deliberately excluded. Content capture is an
        explicit opt-in concern, not a dashboard side effect.
        """
        bounded = max(1, min(int(limit), 200))
        conn = self._connect()
        try:
            queries = {
                "runs": (
                    "SELECT id, trace_id, session_id, host, started_at, ended_at, status "
                    "FROM runs ORDER BY started_at DESC, id DESC LIMIT ?"
                ),
                "receipts": (
                    "SELECT id, trace_id, session_id, host, requested_model, model_group, "
                    "resolved_provider, resolved_model, attempted_fallbacks, model_id, "
                    "source, started_at, ended_at, status "
                    "FROM model_receipts ORDER BY COALESCE(ended_at, started_at) DESC, id DESC LIMIT ?"
                ),
                "delegations": (
                    "SELECT id, trace_id, session_id, host, work_unit_id, recommended_agent, "
                    "status, backend, skip_reason, started_at, completed_at "
                    "FROM delegation_events ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT ?"
                ),
                "finalizations": (
                    "SELECT id, trace_id, host, action, missing, created_at "
                    "FROM finalization_events ORDER BY created_at DESC, id DESC LIMIT ?"
                ),
                "routing": (
                    "SELECT id, trace_id, session_id, query_hash, context_fingerprint, status, "
                    "source, selected_ids, semantic_ids, companion_ids, confidence, latency_ms, "
                    "provider, work_units, created_at FROM routing_decisions "
                    "ORDER BY created_at DESC, id DESC LIMIT ?"
                ),
            }
            activity: dict[str, list[dict[str, Any]]] = {}
            for name, sql in queries.items():
                rows = [dict(row) for row in conn.execute(sql, (bounded,)).fetchall()]
                if name == "finalizations":
                    for row in rows:
                        raw_missing = row.get("missing")
                        if isinstance(raw_missing, str) and raw_missing:
                            try:
                                row["missing"] = json.loads(raw_missing)
                            except json.JSONDecodeError:
                                row["missing"] = ["unparseable"]
                        elif not raw_missing:
                            row["missing"] = []
                elif name == "routing":
                    for row in rows:
                        for field in (
                            "selected_ids",
                            "semantic_ids",
                            "companion_ids",
                            "work_units",
                        ):
                            raw_value = row.get(field)
                            if not isinstance(raw_value, str) or not raw_value:
                                row[field] = [] if field != "work_units" else {}
                                continue
                            try:
                                row[field] = json.loads(raw_value)
                            except json.JSONDecodeError:
                                row[field] = [] if field != "work_units" else {}
                activity[name] = rows
            return activity
        finally:
            self._repair_storage_permissions()
            conn.close()

    def list_roster_snapshots(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Return bounded snapshot metadata without candidate prompt content."""
        bounded = max(1, min(int(limit), 200))
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT snapshot_id, created_at, agent_count, manifest, activated "
                "FROM agent_snapshots ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (bounded,),
            ).fetchall()
            snapshots: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                try:
                    manifest = json.loads(item.pop("manifest") or "{}")
                except json.JSONDecodeError:
                    manifest = {}
                item["approved"] = bool(manifest.get("approved"))
                item["activated"] = bool(item.get("activated"))
                item["added"] = len(manifest.get("added", []))
                item["changed"] = len(manifest.get("changed", []))
                item["removed"] = len(manifest.get("removed", []))
                snapshots.append(item)
            return snapshots
        finally:
            conn.close()

    def record_routing_decision(
        self,
        *,
        trace_id: str,
        session_id: str,
        query_hash: str,
        context_fingerprint: str,
        decision: dict[str, Any],
    ) -> str:
        """Persist one metadata-only authoritative routing projection."""
        allowed_fields = {
            "status",
            "selected_ids",
            "semantic_ids",
            "companion_actions",
            "companion_ids",
            "available_companion_ids",
            "unavailable_companion_ids",
            "confidence",
            "latency_ms",
            "provider",
            "candidate_count",
            "top_score",
            "cache_hit",
            "session_reused",
            "source_message_hash",
            "trace_id",
            "context_fingerprint",
            "query_hash",
        }
        safe_decision = {
            key: value for key, value in decision.items() if key in allowed_fields
        }
        raw_work_units = decision.get("work_units")
        safe_work_units: dict[str, Any] = {}
        if isinstance(raw_work_units, dict):
            safe_work_units = {
                key: raw_work_units[key]
                for key in ("delegate", "count", "confidence", "source")
                if key in raw_work_units
            }
        safe_decision["work_units"] = safe_work_units

        event_id = self._uuid()
        source = (
            "cache"
            if safe_decision.get("cache_hit")
            else ("session" if safe_decision.get("session_reused") else "computed")
        )
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO routing_decisions "
                "(id, trace_id, session_id, query_hash, context_fingerprint, status, source, "
                "selected_ids, semantic_ids, companion_ids, confidence, latency_ms, provider, "
                "work_units, decision, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    trace_id,
                    session_id,
                    query_hash,
                    context_fingerprint,
                    str(safe_decision.get("status") or "unknown"),
                    source,
                    json.dumps(safe_decision.get("selected_ids") or []),
                    json.dumps(safe_decision.get("semantic_ids") or []),
                    json.dumps(safe_decision.get("available_companion_ids") or []),
                    float(safe_decision.get("confidence") or 0.0),
                    int(safe_decision.get("latency_ms") or 0),
                    str(safe_decision.get("provider") or ""),
                    json.dumps(safe_work_units),
                    json.dumps(safe_decision, sort_keys=True, default=str),
                    self._now(),
                ),
            )
            conn.commit()
            return event_id
        finally:
            conn.close()

    def trim_runtime_tables(
        self,
        *,
        older_than_days: int | None = None,
        keep_last: int | None = None,
        dry_run: bool = False,
        vacuum: bool = True,
    ) -> dict[str, Any]:
        """Trim append-only runtime/audit tables without touching the roster.

        A retention policy is required. Use ``older_than_days`` for age-based
        cleanup, ``keep_last`` for bounded local smoke tests, or both.
        """
        if older_than_days is None and keep_last is None:
            raise ValueError("trim requires older_than_days, keep_last, or both")
        if older_than_days is not None and older_than_days < 0:
            raise ValueError("older_than_days must be >= 0")
        if keep_last is not None and keep_last < 0:
            raise ValueError("keep_last must be >= 0")

        cutoff = None
        if older_than_days is not None:
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=older_than_days)
            ).isoformat()

        before = self.database_stats()
        deleted: dict[str, dict[str, int]] = {}
        conn = self._connect()
        try:
            for table in _RUNTIME_DELETE_ORDER:
                timestamp_expr = _RUNTIME_TABLE_TIMESTAMPS[table]
                clauses: list[str] = []
                params: list[Any] = []
                if cutoff is not None:
                    clauses.append(f"{timestamp_expr} < ?")
                    params.append(cutoff)
                if keep_last is not None:
                    clauses.append(
                        "rowid NOT IN ("
                        f"SELECT rowid FROM {table} "
                        f"ORDER BY {timestamp_expr} DESC, rowid DESC LIMIT ?"
                        ")"
                    )
                    params.append(keep_last)
                if table == "delegation_events":
                    clauses.append(
                        "NOT EXISTS (SELECT 1 FROM worker_runs "
                        "WHERE worker_runs.delegation_event_id = delegation_events.id)"
                    )
                elif table == "runs":
                    clauses.extend(
                        [
                            "NOT EXISTS (SELECT 1 FROM model_receipts "
                            "WHERE model_receipts.trace_id = runs.trace_id)",
                            "NOT EXISTS (SELECT 1 FROM delegation_events "
                            "WHERE delegation_events.trace_id = runs.trace_id)",
                            "NOT EXISTS (SELECT 1 FROM finalization_events "
                            "WHERE finalization_events.trace_id = runs.trace_id)",
                            "NOT EXISTS (SELECT 1 FROM routing_decisions "
                            "WHERE routing_decisions.trace_id = runs.trace_id)",
                        ]
                    )
                where = " AND ".join(f"({clause})" for clause in clauses)
                count_sql = f"SELECT COUNT(*) AS count FROM {table} WHERE {where}"
                count = int(conn.execute(count_sql, params).fetchone()["count"])
                deleted[table] = {"deleted": count}
                if count:
                    conn.execute(f"DELETE FROM {table} WHERE {where}", params)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        finally:
            conn.close()

        if vacuum and not dry_run:
            conn = self._connect()
            try:
                conn.execute("VACUUM")
            finally:
                conn.close()

        after = self.database_stats()
        return {
            "db_path": str(self.db_path),
            "dry_run": dry_run,
            "older_than_days": older_than_days,
            "keep_last": keep_last,
            "vacuumed": bool(vacuum and not dry_run),
            "db_size_before_bytes": before["db_size_bytes"],
            "db_size_after_bytes": after["db_size_bytes"],
            "wal_size_before_bytes": before["wal_size_bytes"],
            "wal_size_after_bytes": after["wal_size_bytes"],
            "tables": deleted,
            "remaining_tables": after["tables"],
        }

    # ── Roster ─────────────────────────────────────────────────────

    def add_agent_source(
        self, url: str, name: str = "", *, trusted_for_auto_approve: bool = False
    ) -> str:
        source_id = self._uuid()
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT id FROM agent_sources WHERE url = ?", (url,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE agent_sources "
                    "SET name = COALESCE(NULLIF(?, ''), name), enabled = 1, "
                    "trusted_for_auto_approve = CASE WHEN ? THEN 1 ELSE trusted_for_auto_approve END "
                    "WHERE url = ?",
                    (name, 1 if trusted_for_auto_approve else 0, url),
                )
                source_id = existing["id"]
            else:
                conn.execute(
                    "INSERT INTO agent_sources (id, url, name, added_at, trusted_for_auto_approve) VALUES (?, ?, ?, ?, ?)",
                    (
                        source_id,
                        url,
                        name or url,
                        self._now(),
                        1 if trusted_for_auto_approve else 0,
                    ),
                )
            conn.commit()
            return source_id
        finally:
            conn.close()

    def list_agent_sources(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM agent_sources WHERE enabled = 1 ORDER BY added_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def activate_agent(self, agent: dict[str, Any]) -> None:
        content = str(
            agent.get("prompt_body") or agent.get("content") or agent.get("body") or ""
        )
        if not content.strip():
            identity = str(agent.get("name") or agent.get("slug") or "specialist")
            description = str(
                agent.get("description") or "Apply your named specialty to the task."
            )
            content = f"You are the {identity} specialist. {description}".strip()
        version = str(agent.get("version") or "1.0.0")
        content_hash = str(
            agent.get("hash") or hashlib.sha256(content.encode("utf-8")).hexdigest()
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing_version = conn.execute(
                "SELECT id, hash, content FROM agent_versions "
                "WHERE agent_slug = ? AND version = ?",
                (agent["slug"], version),
            ).fetchone()
            if existing_version is not None and (
                str(existing_version["hash"] or "") != content_hash
                or str(existing_version["content"] or "") != content
            ):
                raise ValueError(
                    f"immutable agent version conflict for {agent['slug']}@{version}"
                )
            if existing_version is None:
                conn.execute(
                    "INSERT INTO agent_versions "
                    "(id, agent_slug, version, hash, content, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        self._uuid(),
                        agent["slug"],
                        version,
                        content_hash,
                        content,
                        self._now(),
                    ),
                )
            conn.execute(
                "INSERT OR REPLACE INTO agent_active "
                "(id, agent_slug, name, division, description, source, version, hash, "
                "categories, capabilities, tool_affinity, prompt_path, activated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    agent["slug"],
                    agent.get("name", ""),
                    agent.get("division", ""),
                    agent.get("description", ""),
                    agent.get("source", ""),
                    version,
                    content_hash,
                    json.dumps(agent.get("categories", [])),
                    json.dumps(agent.get("capabilities", [])),
                    json.dumps(agent.get("tool_affinity", [])),
                    agent.get("prompt_path", ""),
                    self._now(),
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_active_roster(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT * FROM agent_active ORDER BY agent_slug")
            agents = []
            for row in cur.fetchall():
                d = dict(row)
                d["categories"] = json.loads(d.get("categories") or "[]")
                d["capabilities"] = json.loads(d.get("capabilities") or "[]")
                d["tool_affinity"] = json.loads(d.get("tool_affinity") or "[]")
                agents.append(d)
            return agents
        finally:
            conn.close()

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        """Return active roster in selector-compatible format."""
        agents = self.get_active_roster()
        catalog = []
        for a in agents:
            catalog.append(
                {
                    "slug": a["agent_slug"],
                    "name": a.get("name", ""),
                    "description": a.get("description", ""),
                    "division": a.get("division", ""),
                    "categories": a.get("categories", []),
                    "capabilities": a.get("capabilities", []),
                }
            )
        return catalog

    def get_specialist_prompt(
        self,
        slug: str,
        *,
        max_chars: int = 65_536,
    ) -> dict[str, Any] | None:
        """Return one active specialist with its versioned bounded prompt."""
        bounded = max(1, min(int(max_chars), 262_144))
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT a.*, v.content AS prompt_body, v.hash AS prompt_hash "
                "FROM agent_active AS a "
                "LEFT JOIN agent_versions AS v "
                "ON v.agent_slug = a.agent_slug AND v.version = a.version "
                "WHERE a.agent_slug = ? LIMIT 1",
                (slug,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            for field in ("categories", "capabilities", "tool_affinity"):
                try:
                    result[field] = json.loads(result.get(field) or "[]")
                except json.JSONDecodeError:
                    result[field] = []
            content = str(result.get("prompt_body") or "")
            result["prompt_body"] = content[:bounded]
            result["prompt_truncated"] = len(content) > bounded
            return result
        finally:
            conn.close()

    def deactivate_agent(self, slug: str) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM agent_active WHERE agent_slug = ?", (slug,))
            conn.commit()
        finally:
            conn.close()

    def create_snapshot(self, snapshot_id: str, manifest: dict[str, Any]) -> None:
        snapshot_agent_count = len(manifest.get("candidates", []))
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_snapshots (id, snapshot_id, created_at, agent_count, manifest, activated) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (
                    self._uuid(),
                    snapshot_id,
                    self._now(),
                    snapshot_agent_count,
                    json.dumps(manifest),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def record_import_event(
        self, event_type: str, agent_slug: str = "", detail: str = ""
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_import_events (id, event_type, agent_slug, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self._uuid(), event_type, agent_slug, detail, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

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
