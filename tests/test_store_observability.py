from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path

import pytest

from agency_runtime.core.observability import RuntimeBoundary
from agency_runtime.core.store.observed_sqlite import ObservedSQLiteConnection
from agency_runtime.core.store.sqlite import Store


def _observations(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in caplog.records
        if record.getMessage().startswith("agency_observation ")
    ]


def test_store_uses_observed_connections(tmp_path: Path) -> None:
    store = Store(tmp_path / "observed.db")
    conn = store._connect()
    try:
        assert isinstance(conn, ObservedSQLiteConnection)
        assert conn.execute("SELECT 1").fetchone()[0] == 1
        assert conn.cursor().__class__.__name__ == "ObservedSQLiteCursor"
    finally:
        conn.close()


def test_slow_sqlite_observation_never_contains_sql_values_or_paths(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    secret = "Bearer-never-log-this"
    private_path = r"C:\\Users\\private\\agency.db"
    conn = sqlite3.connect(":memory:", factory=ObservedSQLiteConnection)
    conn.create_function("agency_slow", 0, lambda: time.sleep(0.06) or secret)
    try:
        with RuntimeBoundary(surface="http", operation="status") as boundary:
            assert conn.execute("SELECT agency_slow(), ?", (private_path,)).fetchone()[0] == secret
    finally:
        conn.close()

    store_event = next(
        item
        for item in _observations(caplog)
        if item.get("surface") == "store"
        and item.get("request_id") == boundary.request_id
        and item.get("operation") == "sqlite.select"
        and item.get("reason_code") == "slow_query"
    )
    serialized = json.dumps(store_event)
    assert store_event["request_id"] == boundary.request_id
    assert store_event["operation"] == "sqlite.select"
    assert store_event["outcome"] == "degraded"
    assert store_event["reason_code"] == "slow_query"
    assert secret not in serialized
    assert private_path not in serialized


def test_sqlite_busy_observation_is_bounded_and_value_free(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="agency_runtime.observation")
    database = tmp_path / "private-busy.db"
    owner = sqlite3.connect(database, timeout=0.01, factory=ObservedSQLiteConnection)
    contender = sqlite3.connect(database, timeout=0.01, factory=ObservedSQLiteConnection)
    owner.execute("CREATE TABLE values_table (value TEXT NOT NULL)")
    owner.commit()
    owner.execute("BEGIN EXCLUSIVE")
    owner.execute("INSERT INTO values_table(value) VALUES ('owner-secret')")
    contender.execute("PRAGMA busy_timeout=1")
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            contender.execute(
                "INSERT INTO values_table(value) VALUES (?)",
                ("contender-secret",),
            )
    finally:
        owner.rollback()
        owner.close()
        contender.close()

    event = next(
        item
        for item in reversed(_observations(caplog))
        if item.get("surface") == "store"
        and item.get("operation") == "sqlite.insert"
        and item.get("outcome") == "error"
        and item.get("reason_code") == "sqlite_busy"
    )
    serialized = json.dumps(event)
    assert event["operation"] == "sqlite.insert"
    assert event["outcome"] == "error"
    assert "owner-secret" not in serialized
    assert "contender-secret" not in serialized
    assert str(database) not in serialized
