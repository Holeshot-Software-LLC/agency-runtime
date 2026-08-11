"""Specialist launch-model reporting in the response header."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agency_runtime.core.header.contract import (
    _scoped_model_line,
    _specialist_launch_models,
)
from agency_runtime.core.store.schema import (
    DELEGATION_ACTIVATION_RECEIPT_MIGRATED_COLUMNS,
    migrate_delegation_activation_unit_identity,
)
from agency_runtime.core.store.sqlite import Store, _v20_receipt_schema_is_current

_LEGACY_RECEIPTS_DDL = """
CREATE TABLE delegation_activation_receipts (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    work_unit_id TEXT NOT NULL,
    specialist_slug TEXT NOT NULL,
    specialist_version TEXT NOT NULL,
    specialist_prompt_hash TEXT NOT NULL,
    worker_kind TEXT NOT NULL,
    worker_id TEXT NOT NULL DEFAULT '',
    native_run_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    consumed_at TEXT,
    delegation_event_id TEXT
)
"""


def test_legacy_database_gains_launch_model_without_losing_rows() -> None:
    """The rebuild branch restates the DDL, so it must carry the column too.

    ``ensure_column`` alone is not enough: a database whose unique index does
    not match drops through to a full table rebuild from a second, duplicated
    CREATE TABLE. A column added only to the first one silently disappears
    exactly on the databases that need migrating.
    """

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE runs (trace_id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE delegation_events (id TEXT PRIMARY KEY)")
    conn.execute(_LEGACY_RECEIPTS_DDL)
    conn.execute(
        "INSERT INTO delegation_activation_receipts VALUES "
        "('i','t','s','tr','u','sl','v','h','k','w','n','now',NULL,NULL)"
    )

    migrate_delegation_activation_unit_identity(conn)

    columns = [row[1] for row in conn.execute("PRAGMA table_info(delegation_activation_receipts)")]
    assert "launch_model" in columns
    preserved = conn.execute(
        "SELECT id, launch_model FROM delegation_activation_receipts"
    ).fetchone()
    assert preserved["id"] == "i"
    assert preserved["launch_model"] == ""
    conn.close()


@pytest.mark.parametrize(
    "column", [name for name, _definition in DELEGATION_ACTIVATION_RECEIPT_MIGRATED_COLUMNS]
)
def test_startup_predicate_reports_stale_when_a_migrated_column_is_missing(
    tmp_path: Path, column: str
) -> None:
    """Adding a column to the migration is useless if startup never runs it.

    A database already stamped at the current schema version migrates only when
    the startup predicate calls it stale. That predicate used to restate the
    receipt columns by hand, so ``launch_model`` landed in the migration, never
    reached an existing database, and failed every turn with ``no such column``
    -- while fresh test databases, built from the full DDL, stayed green.

    Baselining on a fully migrated store is what makes this real: the missing
    column is then the only thing the predicate can be reacting to.
    """

    store = Store(db_path=tmp_path / "agency.db")
    close = getattr(store, "close", None)
    if callable(close):
        close()

    conn = sqlite3.connect(tmp_path / "agency.db")
    conn.row_factory = sqlite3.Row
    assert _v20_receipt_schema_is_current(conn) is True

    try:
        conn.execute(f"ALTER TABLE delegation_activation_receipts DROP COLUMN {column}")
    except sqlite3.OperationalError as exc:
        # A trigger or index names the column, so the schema already pins it and
        # SQLite will not let it go missing. Tearing those down to force the drop
        # is what made an earlier version of this test pass on their absence
        # rather than on the column's, so leave them standing and skip instead.
        conn.close()
        pytest.skip(f"{column} is structurally pinned: {exc}")

    assert _v20_receipt_schema_is_current(conn) is False
    conn.close()


def test_no_specialist_reports_not_launched() -> None:
    line = _scoped_model_line(None, "", None, specialist_loaded=False)

    assert "specialist: not launched" in line


def test_absent_launch_model_names_the_host_default_without_claiming_it() -> None:
    """The old wording read as a failure; the new one must not overclaim either."""

    line = _scoped_model_line(None, "", None, specialist_loaded=True)

    assert "specialist: no model requested at launch; host default applies" in line
    assert "not evidenced" not in line
    # The host may resolve from the agent definition instead of the session
    # model, so the header must not assert inheritance it cannot observe.
    assert "inherits" not in line


def test_explicit_launch_model_is_reported() -> None:
    line = _scoped_model_line(
        None,
        "",
        None,
        specialist_loaded=True,
        launch_models=["haiku"],
    )

    assert "specialist: haiku (requested at launch)" in line


def test_multiple_distinct_launch_models_are_all_reported() -> None:
    line = _scoped_model_line(
        None,
        "",
        None,
        specialist_loaded=True,
        launch_models=["haiku", "sonnet"],
    )

    assert "specialist: haiku, sonnet (requested at launch)" in line


def test_launch_models_are_collected_and_deduped_from_activations() -> None:
    activations = [
        {"launch_model": "haiku"},
        {"launch_model": "haiku"},
        {"launch_model": ""},
        {"launch_model": "sonnet"},
        {"no_model_key": "ignored"},
    ]

    assert _specialist_launch_models(activations) == ["haiku", "sonnet"]


@pytest.mark.parametrize("activations", [None, "", 7, {}])
def test_non_sequence_activations_yield_no_models(activations: object) -> None:
    assert _specialist_launch_models(activations) == []
