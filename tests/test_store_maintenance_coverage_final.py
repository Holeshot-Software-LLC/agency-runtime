"""Exact reachable branch coverage for Store maintenance invariants."""

from __future__ import annotations

import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.store.sqlite import Store

_DIGEST = "a" * 64


def test_routing_decision_rejects_invalid_digests_and_non_mapping(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(ValueError, match="query_hash"):
        store.record_routing_decision(
            trace_id="turn",
            session_id="session",
            query_hash="bad",
            context_fingerprint=_DIGEST,
            decision={},
        )
    with pytest.raises(ValueError, match="routing decision must be a mapping"):
        store.record_routing_decision(
            trace_id="turn",
            session_id="session",
            query_hash=_DIGEST,
            context_fingerprint=_DIGEST,
            decision=[],  # type: ignore[arg-type]
        )


class _Result:
    def __init__(
        self,
        row: Any = None,
        *,
        rows: list[Any] | None = None,
        rowcount: int = 1,
    ) -> None:
        self._row = row
        self._rows = [] if rows is None else rows
        self.rowcount = rowcount

    def fetchone(self) -> Any:
        return self._row

    def fetchall(self) -> list[Any]:
        return self._rows


class _FailingConnection:
    def __init__(self) -> None:
        self.rolled_back = False
        self.closed = False

    def execute(self, *_args: Any, **_kwargs: Any) -> _Result:
        raise RuntimeError("synthetic routing write failure")

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _CloseTrackingConnection:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


def test_routing_decision_rolls_back_and_closes_on_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _FailingConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)
    with pytest.raises(RuntimeError, match="synthetic routing write failure"):
        store.record_routing_decision(
            trace_id="turn",
            session_id="session",
            query_hash=_DIGEST,
            context_fingerprint=_DIGEST,
            decision={},
        )
    assert connection.rolled_back is True
    assert connection.closed is True


def test_recent_activity_closes_connection_when_permission_repair_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    connection = _CloseTrackingConnection()
    monkeypatch.setattr(store, "_connect", lambda: connection)

    def fail_repair() -> None:
        raise PermissionError("synthetic permission repair failure")

    monkeypatch.setattr(store, "_repair_storage_permissions", fail_repair)

    with pytest.raises(PermissionError, match="synthetic permission repair failure"):
        store._recent_activity({}, limit=1)

    assert connection.close_count == 1


def test_database_sizes_treats_disappearing_wal_as_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    wal_path = Path(f"{store.db_path}-wal")
    original_metadata = store._storage_metadata

    def metadata_with_disappearing_wal(path: Path, *, optional: bool):
        if path == wal_path:
            return None
        return original_metadata(path, optional=optional)

    monkeypatch.setattr(store, "_storage_metadata", metadata_with_disappearing_wal)

    sizes = store.database_sizes()

    assert sizes["db_size_bytes"] > 0
    assert sizes["wal_size_bytes"] == 0


@pytest.mark.parametrize(
    ("replacement_mode", "expected_error"),
    [
        (stat.S_IFLNK, "symlink or reparse point"),
        (stat.S_IFDIR, "non-regular file"),
    ],
)
def test_database_sizes_rejects_unsafe_sidecar_replacement_after_initial_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_mode: int,
    expected_error: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    wal_path = Path(f"{store.db_path}-wal")
    original_metadata = store._storage_metadata

    def metadata_with_replaced_wal(path: Path, *, optional: bool):
        if path == wal_path:
            return SimpleNamespace(
                st_mode=replacement_mode,
                st_file_attributes=0,
                st_size=1024,
            )
        return original_metadata(path, optional=optional)

    monkeypatch.setattr(store, "_storage_metadata", metadata_with_replaced_wal)

    with pytest.raises(PermissionError, match=expected_error):
        store.database_sizes()


class _PairCasConnection:
    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
        if "SELECT COUNT(*) FROM agency_terminal_pair_candidates" in sql:
            return _Result([1])
        if "SELECT trace_id, session_id, turn_sequence" in sql:
            return _Result(rows=[{"trace_id": "turn"}])
        if "DELETE FROM runs WHERE id IN" in sql:
            return _Result(rowcount=0)
        if "DELETE FROM finalization_events WHERE id IN" in sql:
            return _Result(rowcount=1)
        return _Result()


def test_terminal_pair_deletion_detects_atomicity_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    monkeypatch.setattr(store, "_record_trace_tombstones", lambda *_args, **_kwargs: 1)
    with pytest.raises(RuntimeError, match="pair delete lost atomicity"):
        store._delete_eligible_terminal_pairs(
            _PairCasConnection(),
            cutoff=None,
            keep_last=1,
            retired_at="now",
        )


class _StaleRunCasConnection:
    def execute(self, sql: str, *_args: Any, **_kwargs: Any) -> _Result:
        if "SELECT COUNT(*) FROM agency_stale_open_candidates" in sql:
            return _Result([1])
        if "UPDATE runs SET status = 'retention_expired'" in sql:
            return _Result(rowcount=0)
        return _Result()


def test_stale_open_run_retirement_detects_compare_and_swap_loss(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(RuntimeError, match="lost compare-and-swap"):
        store._retire_stale_open_runs(
            _StaleRunCasConnection(),
            cutoff="cutoff",
            inactivity_cutoff="inactive",
        )
