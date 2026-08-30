"""SQLite classes that emit timings without retaining SQL or bound values."""

from __future__ import annotations

import re
import sqlite3
from contextlib import suppress
from time import monotonic_ns
from typing import Any

from agency_runtime.core.observability import (
    SLOW_SQLITE_MILLISECONDS,
    emit_store_observation,
)

_SQL_KIND = re.compile(
    r"\A\s*(?:(?:--[^\r\n]*(?:\r?\n|\Z))|(?:/\*.*?\*/\s*))*([A-Za-z]+)",
    re.DOTALL,
)
_KNOWN_SQL_KINDS = frozenset(
    {
        "alter",
        "begin",
        "commit",
        "create",
        "delete",
        "drop",
        "insert",
        "pragma",
        "release",
        "replace",
        "rollback",
        "savepoint",
        "select",
        "update",
        "vacuum",
        "with",
    }
)


def _operation(statement: object) -> str:
    """Classify at most the SQL verb; never return SQL or a literal."""

    match = _SQL_KIND.match(str(statement or "")[:4096])
    kind = match.group(1).casefold() if match is not None else "unknown"
    return f"sqlite.{kind if kind in _KNOWN_SQL_KINDS else 'unknown'}"


def _observe(
    operation: str,
    started_ns: int,
    *,
    error: sqlite3.Error | None = None,
) -> None:
    duration_ms = (monotonic_ns() - started_ns) / 1_000_000.0
    if error is None and duration_ms < SLOW_SQLITE_MILLISECONDS:
        return
    if error is None:
        outcome, reason = "degraded", "slow_query"
    else:
        normalized = str(error).casefold()
        outcome = "error"
        reason = "sqlite_busy" if "locked" in normalized or "busy" in normalized else "sqlite_error"
    # Observability must never alter the Store operation it measures.  The
    # envelope itself accepts no SQL, values, exception messages, or paths.
    with suppress(Exception):
        emit_store_observation(
            operation=operation,
            duration_ms=duration_ms,
            outcome=outcome,
            reason_code=reason,
        )


class ObservedSQLiteCursor(sqlite3.Cursor):
    """Cursor that measures slow and failed statements without logging them."""

    def execute(self, sql: str, parameters: Any = (), /) -> ObservedSQLiteCursor:
        operation = _operation(sql)
        started_ns = monotonic_ns()
        try:
            result = super().execute(sql, parameters)
        except sqlite3.Error as error:
            _observe(operation, started_ns, error=error)
            raise
        _observe(operation, started_ns)
        return result

    def executemany(self, sql: str, seq_of_parameters: Any, /) -> ObservedSQLiteCursor:
        operation = _operation(sql)
        started_ns = monotonic_ns()
        try:
            result = super().executemany(sql, seq_of_parameters)
        except sqlite3.Error as error:
            _observe(operation, started_ns, error=error)
            raise
        _observe(operation, started_ns)
        return result


class ObservedSQLiteConnection(sqlite3.Connection):
    """Connection that supplies observed cursors and covers shortcut calls."""

    def cursor(self, factory: Any = None) -> ObservedSQLiteCursor:
        return super().cursor(factory or ObservedSQLiteCursor)

    def execute(self, sql: str, parameters: Any = (), /) -> ObservedSQLiteCursor:
        operation = _operation(sql)
        started_ns = monotonic_ns()
        try:
            result = super().execute(sql, parameters)
        except sqlite3.Error as error:
            _observe(operation, started_ns, error=error)
            raise
        _observe(operation, started_ns)
        return result

    def executemany(self, sql: str, seq_of_parameters: Any, /) -> ObservedSQLiteCursor:
        operation = _operation(sql)
        started_ns = monotonic_ns()
        try:
            result = super().executemany(sql, seq_of_parameters)
        except sqlite3.Error as error:
            _observe(operation, started_ns, error=error)
            raise
        _observe(operation, started_ns)
        return result

    def executescript(self, sql_script: str, /) -> ObservedSQLiteCursor:
        operation = _operation(sql_script)
        started_ns = monotonic_ns()
        try:
            result = super().executescript(sql_script)
        except sqlite3.Error as error:
            _observe(operation, started_ns, error=error)
            raise
        _observe(operation, started_ns)
        return result

    def commit(self) -> None:
        started_ns = monotonic_ns()
        try:
            super().commit()
        except sqlite3.Error as error:
            _observe("sqlite.commit", started_ns, error=error)
            raise
        _observe("sqlite.commit", started_ns)

    def rollback(self) -> None:
        started_ns = monotonic_ns()
        try:
            super().rollback()
        except sqlite3.Error as error:
            _observe("sqlite.rollback", started_ns, error=error)
            raise
        _observe("sqlite.rollback", started_ns)


__all__ = ["ObservedSQLiteConnection", "ObservedSQLiteCursor"]
