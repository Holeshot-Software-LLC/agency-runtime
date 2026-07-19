"""Regression coverage for durable schema-v16 to schema-v17 upgrades."""

from __future__ import annotations

import hmac
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from agency_runtime.core.store.schema import SCHEMA_V1, SCHEMA_VERSION
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.trace_identity import correlation_digest
from tests.runtime_support import harden_private_test_file

_LEGACY_KEY = b"k" * 32


def _legacy_digest(value: str, *, domain: str) -> str:
    normalized = value or ("<uncorrelated-session>" if domain == "session" else "")
    payload = f"agency-runtime:{domain}:v1\0{normalized}".encode()
    return hmac.new(_LEGACY_KEY, payload, sha256).hexdigest()


def _create_v16_store(
    path: Path,
    *,
    runs: list[tuple[str, str, str, str]],
    tombstones: list[tuple[str, str]],
    include_key: bool = True,
    counter_value: str | int = 0,
    raw_digests: bool = False,
) -> None:
    """Create the exact legacy tombstone shape around an otherwise valid store."""

    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_V1)
        conn.execute("DROP TABLE trace_tombstones")
        conn.execute(
            "CREATE TABLE trace_tombstones ("
            "trace_digest TEXT PRIMARY KEY, retired_at TEXT NOT NULL)"
        )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (16)")
        conn.execute(
            "UPDATE store_counters SET value = ? WHERE name = 'turn-sequence'",
            (counter_value,),
        )
        if include_key:
            conn.execute(
                "INSERT INTO store_secrets (name, secret, created_at) VALUES (?, ?, ?)",
                ("retired-trace-hmac-v1", _LEGACY_KEY, "2026-01-01T00:00:00+00:00"),
            )
        conn.executemany(
            "INSERT INTO runs (id, trace_id, session_id, host, started_at) "
            "VALUES (?, ?, ?, 'codex', ?)",
            runs,
        )
        conn.executemany(
            "INSERT INTO trace_tombstones (trace_digest, retired_at) VALUES (?, ?)",
            [
                (trace_id if raw_digests else _legacy_digest(trace_id, domain="trace"), retired_at)
                for trace_id, retired_at in tombstones
            ],
        )
        conn.commit()
    finally:
        conn.close()
        harden_private_test_file(path)


def _open_rows(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def test_empty_v16_tombstone_table_upgrades_before_index_creation(tmp_path: Path) -> None:
    path = tmp_path / "empty-v16.db"
    _create_v16_store(path, runs=[], tombstones=[], include_key=False)

    store = Store(path)

    conn = _open_rows(path)
    try:
        assert (
            conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == SCHEMA_VERSION
        )
        assert {row["name"] for row in conn.execute("PRAGMA table_info(trace_tombstones)")} == {
            "trace_digest",
            "session_digest",
            "turn_sequence",
            "retired_at",
        }
        assert (
            conn.execute(
                "SELECT value FROM store_counters WHERE name = 'turn-sequence'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_trace_tombstones_session_sequence'"
            ).fetchone()[0]
            == 1
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_trace_tombstones_turn_sequence_unique'"
            ).fetchone()[0]
            == 1
        )
    finally:
        conn.close()
    assert store._current_schema_state() == (True, True)


def test_populated_v16_tombstones_are_preserved_and_sequenced(tmp_path: Path) -> None:
    path = tmp_path / "populated-v16.db"
    trace_a = "retired-a"
    trace_b = "retired-b"
    _create_v16_store(
        path,
        runs=[
            ("run-b", "trace-b", "session-b", "2026-01-02T00:00:00+00:00"),
            ("run-a", "trace-a", "session-a", "2026-01-01T00:00:00+00:00"),
        ],
        tombstones=[
            (trace_b, "2026-01-04T00:00:00+00:00"),
            (trace_a, "2026-01-03T00:00:00+00:00"),
        ],
        counter_value=10,
    )

    store = Store(path)

    conn = _open_rows(path)
    try:
        uncorrelated = correlation_digest(conn, "", domain="session")
        runs = conn.execute("SELECT id, turn_sequence FROM runs ORDER BY turn_sequence").fetchall()
        tombstones = conn.execute(
            "SELECT trace_digest, session_digest, turn_sequence, retired_at "
            "FROM trace_tombstones ORDER BY turn_sequence"
        ).fetchall()
        assert [(row["id"], row["turn_sequence"]) for row in runs] == [
            ("run-a", 1),
            ("run-b", 2),
        ]
        assert [row["trace_digest"] for row in tombstones] == [
            _legacy_digest(trace_a, domain="trace"),
            _legacy_digest(trace_b, domain="trace"),
        ]
        assert [row["retired_at"] for row in tombstones] == [
            "2026-01-03T00:00:00+00:00",
            "2026-01-04T00:00:00+00:00",
        ]
        assert {row["session_digest"] for row in tombstones} == {uncorrelated}
        assert [row["turn_sequence"] for row in tombstones] == [11, 12]
        assert (
            conn.execute(
                "SELECT value FROM store_counters WHERE name = 'turn-sequence'"
            ).fetchone()[0]
            == 12
        )
        assert (
            len(
                {
                    row[0]
                    for row in conn.execute(
                        "SELECT turn_sequence FROM runs UNION ALL "
                        "SELECT turn_sequence FROM trace_tombstones"
                    )
                }
            )
            == 4
        )
    finally:
        conn.close()
    with pytest.raises(ValueError, match="permanently retired"):
        store.create_run(trace_id=trace_a, session_id="session-a")


@pytest.mark.parametrize("invalid_digest", ["A" * 64, "g" * 64])
def test_invalid_v16_tombstone_fails_atomically(
    tmp_path: Path,
    invalid_digest: str,
) -> None:
    path = tmp_path / "invalid-v16.db"
    _create_v16_store(
        path,
        runs=[],
        tombstones=[(invalid_digest, "2026-01-03T00:00:00+00:00")],
        raw_digests=True,
    )

    with pytest.raises(RuntimeError, match="legacy retired-trace barrier integrity"):
        Store(path)

    conn = _open_rows(path)
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 16
        assert [row["name"] for row in conn.execute("PRAGMA table_info(trace_tombstones)")] == [
            "trace_digest",
            "retired_at",
        ]
        assert conn.execute("SELECT COUNT(*) FROM trace_tombstones").fetchone()[0] == 1
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_trace_tombstones_session_sequence'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] < SCHEMA_VERSION
        )
    finally:
        conn.close()


def test_nonempty_v16_tombstones_refuse_a_missing_integrity_key(tmp_path: Path) -> None:
    path = tmp_path / "missing-key-v16.db"
    _create_v16_store(
        path,
        runs=[],
        tombstones=[("retired", "2026-01-03T00:00:00+00:00")],
        include_key=False,
    )

    with pytest.raises(RuntimeError, match="key is unavailable for legacy tombstones"):
        Store(path)

    conn = _open_rows(path)
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 16
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM store_secrets WHERE name = 'retired-trace-hmac-v1'"
            ).fetchone()[0]
            == 0
        )
        assert [row["name"] for row in conn.execute("PRAGMA table_info(trace_tombstones)")] == [
            "trace_digest",
            "retired_at",
        ]
    finally:
        conn.close()


def test_partially_upgraded_v16_rejects_duplicate_global_sequences(tmp_path: Path) -> None:
    path = tmp_path / "duplicate-sequence-v16.db"
    _create_v16_store(
        path,
        runs=[],
        tombstones=[
            ("retired-a", "2026-01-03T00:00:00+00:00"),
            ("retired-b", "2026-01-04T00:00:00+00:00"),
        ],
    )
    conn = sqlite3.connect(path)
    try:
        conn.execute("ALTER TABLE trace_tombstones ADD COLUMN session_digest TEXT DEFAULT ''")
        conn.execute("ALTER TABLE trace_tombstones ADD COLUMN turn_sequence INTEGER DEFAULT 0")
        conn.execute(
            "UPDATE trace_tombstones SET session_digest = ?, turn_sequence = 7",
            (_legacy_digest("", domain="session"),),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="turn sequence uniqueness"):
        Store(path)


def test_current_v18_health_rejects_nonhex_and_duplicate_barriers(tmp_path: Path) -> None:
    nonhex_path = tmp_path / "nonhex-v17.db"
    nonhex_store = Store(nonhex_path)
    nonhex_store.create_run(trace_id="run", session_id="session")
    conn = nonhex_store._connect()
    try:
        session_digest = correlation_digest(conn, "session", domain="session")
        conn.execute(
            "INSERT INTO trace_tombstones "
            "(trace_digest, session_digest, turn_sequence, retired_at) VALUES (?, ?, 2, ?)",
            ("A" * 64, session_digest, "2026-01-03T00:00:00+00:00"),
        )
        conn.execute("UPDATE store_counters SET value = 2 WHERE name = 'turn-sequence'")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="retired-trace barrier integrity"):
        Store(nonhex_path)

    duplicate_path = tmp_path / "duplicate-v17.db"
    duplicate_store = Store(duplicate_path)
    duplicate_store.create_run(trace_id="run", session_id="session")
    conn = duplicate_store._connect()
    try:
        session_digest = correlation_digest(conn, "session", domain="session")
        conn.execute(
            "INSERT INTO trace_tombstones "
            "(trace_digest, session_digest, turn_sequence, retired_at) VALUES (?, ?, 1, ?)",
            ("a" * 64, session_digest, "2026-01-03T00:00:00+00:00"),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="turn sequence uniqueness"):
        Store(duplicate_path)


def test_candidate_v17_store_upgrades_to_v18_unique_sequence_contract(tmp_path: Path) -> None:
    path = tmp_path / "candidate-v17.db"
    store = Store(path)
    store.create_run(trace_id="run", session_id="session")
    conn = store._connect()
    try:
        session_digest = correlation_digest(conn, "session", domain="session")
        trace_digest = correlation_digest(conn, "retired", domain="trace")
        conn.execute(
            "INSERT INTO trace_tombstones "
            "(trace_digest, session_digest, turn_sequence, retired_at) VALUES (?, ?, 2, ?)",
            (trace_digest, session_digest, "2026-01-03T00:00:00+00:00"),
        )
        conn.execute("UPDATE store_counters SET value = 1 WHERE name = 'turn-sequence'")
        conn.execute("DROP INDEX idx_trace_tombstones_turn_sequence_unique")
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (17)")
        conn.commit()
    finally:
        conn.close()

    upgraded = Store(path)

    conn = upgraded._connect()
    try:
        assert (
            conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == SCHEMA_VERSION
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_trace_tombstones_turn_sequence_unique'"
            ).fetchone()[0]
            == 1
        )
        assert (
            conn.execute(
                "SELECT value FROM store_counters WHERE name = 'turn-sequence'"
            ).fetchone()[0]
            == 2
        )
    finally:
        conn.close()
    with pytest.raises(ValueError, match="permanently retired"):
        upgraded.create_run(trace_id="retired", session_id="session")


def test_candidate_v17_counter_remains_the_next_allocation_floor(tmp_path: Path) -> None:
    path = tmp_path / "candidate-v17-high-counter.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.execute("DROP INDEX idx_trace_tombstones_turn_sequence_unique")
        conn.execute("UPDATE store_counters SET value = 50 WHERE name = 'turn-sequence'")
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (17)")
        conn.commit()
    finally:
        conn.close()

    upgraded = Store(path)
    upgraded.create_run(trace_id="next", session_id="session")

    assert upgraded.get_run("next")["turn_sequence"] == 51


def test_current_v18_health_requires_unique_tombstone_sequence_index(tmp_path: Path) -> None:
    path = tmp_path / "missing-sequence-index-v18.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.execute("DROP INDEX idx_trace_tombstones_turn_sequence_unique")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="sequence index integrity"):
        Store(path)


@pytest.mark.parametrize("counter_value", ["invalid", -1])
def test_current_v18_health_rejects_invalid_counter_types(
    tmp_path: Path,
    counter_value: str | int,
) -> None:
    path = tmp_path / f"counter-{counter_value}.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE store_counters SET value = ? WHERE name = 'turn-sequence'",
            (counter_value,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="turn sequence counter integrity"):
        Store(path)


def test_current_v18_health_rejects_counter_below_evidence(tmp_path: Path) -> None:
    path = tmp_path / "counter-below-evidence.db"
    store = Store(path)
    store.create_run(trace_id="run", session_id="session")
    conn = store._connect()
    try:
        conn.execute("UPDATE store_counters SET value = 0 WHERE name = 'turn-sequence'")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="turn sequence counter integrity"):
        Store(path)


@pytest.mark.parametrize("counter_value", ["invalid", -1])
def test_v16_migration_rejects_invalid_counter_types_atomically(
    tmp_path: Path,
    counter_value: str | int,
) -> None:
    path = tmp_path / f"legacy-counter-{counter_value}.db"
    _create_v16_store(
        path,
        runs=[],
        tombstones=[],
        counter_value=counter_value,
    )

    with pytest.raises(RuntimeError, match="legacy turn sequence counter integrity"):
        Store(path)

    conn = _open_rows(path)
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 16
    finally:
        conn.close()
