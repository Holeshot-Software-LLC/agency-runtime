"""Atomic exact-turn evidence persistence regressions."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agency_runtime.core.store.queries import RECENT_ACTIVITY_QUERIES
from agency_runtime.core.store.schema import SCHEMA_VERSION
from agency_runtime.core.store.sqlite import Store


def _row_count(store: Store, table: str, where: str, parameters: tuple[str, ...]) -> int:
    connection = store._connect()
    try:
        return int(
            connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {where}",  # nosec B608
                parameters,
            ).fetchone()[0]
        )
    finally:
        connection.close()


def test_turn_close_is_compare_and_swap_and_preserves_first_terminal_outcome(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")

    assert store.close_turn_evidence("session", "trace", status="failed") == 1
    first_run = store.get_run("trace")
    [first_load] = store.get_specialist_load_history("session")

    assert store.close_turn_evidence("session", "trace", status="completed") == 0
    assert store.close_turn_evidence("other-session", "trace", status="completed") == 0
    assert store.get_run("trace") == first_run
    assert store.get_specialist_load_history("session") == [first_load]
    with pytest.raises(ValueError, match="terminal status"):
        store.close_turn_evidence("session", "trace", status="active")


def test_turn_close_rolls_back_when_terminal_transition_fails(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    connection = store._connect()
    try:
        connection.execute(
            "CREATE TRIGGER reject_close BEFORE UPDATE OF status ON runs "
            "WHEN NEW.trace_id = 'trace' BEGIN SELECT RAISE(ABORT, 'reject close'); END"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="reject close"):
        store.close_turn_evidence("session", "trace")

    assert store.get_run("trace")["status"] == "active"
    assert store.get_active_specialists_for_trace("session", "trace") == ["reviewer"]


def test_turn_close_reports_run_cas_without_specialist_rows(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")

    assert store.close_turn_evidence("session", "trace") == 1
    assert store.close_turn_evidence("session", "trace") == 0
    assert store.get_run("trace")["status"] == "completed"


def test_failed_model_receipt_write_rolls_back_implicit_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    receipt_id = store.record_model_receipt(trace_id="seed", session_id="session")
    generated = iter((receipt_id, "new-model-parent"))
    monkeypatch.setattr(store, "_uuid", lambda: next(generated))

    with pytest.raises(sqlite3.IntegrityError):
        store.record_model_receipt(trace_id="rolled-back", session_id="session")

    assert store.get_run("rolled-back") is None


def test_failed_skill_write_rolls_back_implicit_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_skill_loaded("session", "seed", trace_id="seed")
    connection = store._connect()
    try:
        skill_id = str(
            connection.execute("SELECT id FROM skills_loaded WHERE trace_id = 'seed'").fetchone()[0]
        )
    finally:
        connection.close()
    generated = iter(("new-skill-parent", skill_id))
    monkeypatch.setattr(store, "_uuid", lambda: next(generated))

    with pytest.raises(sqlite3.IntegrityError):
        store.record_skill_loaded("session", "rolled-back", trace_id="rolled-back")

    assert store.get_run("rolled-back") is None


def test_failed_specialist_write_rolls_back_implicit_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session", "seed", trace_id="seed")
    [seed] = store.get_specialist_load_history("session")
    generated = iter(("new-specialist-parent", seed["id"]))
    monkeypatch.setattr(store, "_uuid", lambda: next(generated))

    with pytest.raises(sqlite3.IntegrityError):
        store.record_specialist_loaded(
            "session",
            "rolled-back",
            trace_id="rolled-back",
        )

    assert store.get_run("rolled-back") is None


def test_concurrent_specialist_load_is_one_conflict_safe_identity(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(
            executor.map(
                lambda _: store.record_specialist_loaded(
                    "session",
                    "reviewer",
                    trace_id="trace",
                ),
                range(32),
            )
        )

    assert store.get_specialists_for_trace("session", "trace") == ["reviewer"]
    assert (
        _row_count(
            store,
            "specialists_loaded",
            "session_id = ? AND trace_id = ? AND agent_slug = ?",
            ("session", "trace", "reviewer"),
        )
        == 1
    )


def test_current_migration_collapses_duplicate_specialist_identity(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    store.create_run(trace_id="trace", session_id="session")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    connection = store._connect()
    try:
        connection.execute("DROP INDEX idx_specialists_turn_agent_unique")
        connection.execute(
            "INSERT INTO specialists_loaded "
            "(id, session_id, trace_id, agent_slug, loaded_at, expired_at) "
            "VALUES ('duplicate', 'session', 'trace', 'reviewer', "
            "'2026-07-01T00:00:00+00:00', NULL)"
        )
        connection.execute(
            "INSERT INTO specialists_loaded "
            "(id, session_id, trace_id, agent_slug, loaded_at, expired_at) VALUES "
            "('expired-a', 'session', 'trace', 'archived', "
            "'2026-06-01T00:00:00+00:00', '2026-06-02T00:00:00+00:00'), "
            "('expired-b', 'session', 'trace', 'archived', "
            "'2026-06-03T00:00:00+00:00', '2026-06-04T00:00:00+00:00')"
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (12)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    assert migrated.get_specialists_for_trace("session", "trace") == [
        "archived",
        "reviewer",
    ]
    history = {row["agent_slug"]: row for row in migrated.get_specialist_load_history("session")}
    assert history["archived"]["loaded_at"] == "2026-06-01T00:00:00+00:00"
    assert history["archived"]["expired_at"] == "2026-06-04T00:00:00+00:00"
    connection = migrated._connect()
    try:
        assert (
            connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            == SCHEMA_VERSION
        )
        indexes = {
            str(row["name"]): bool(row["unique"])
            for row in connection.execute("PRAGMA index_list(specialists_loaded)")
        }
    finally:
        connection.close()
    assert indexes["idx_specialists_turn_agent_unique"] is True


def test_finalization_action_lookup_is_exact_and_indexed(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    assert store.has_finalization_action("trace", "continue") is False
    store.create_run(trace_id="trace", session_id="session")
    store.record_finalization(
        trace_id="trace",
        host="codex",
        action="continue",
        missing=[],
    )

    assert store.has_finalization_action("trace", "continue") is True
    assert store.has_finalization_action("trace", "accept") is False
    assert store.has_finalization_action("other", "continue") is False
    connection = store._connect()
    try:
        indexes = {
            str(row["name"]) for row in connection.execute("PRAGMA index_list(finalization_events)")
        }
    finally:
        connection.close()
    assert "idx_finalization_trace_action" in indexes


def test_exact_trace_request_kind_is_durable_and_tri_state(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="nontrivial",
        session_id="session",
        metadata={"request_kind": "nontrivial"},
    )
    store.create_run(
        trace_id="trivial",
        session_id="session",
        metadata={"request_kind": "trivial"},
    )

    assert store.get_turn_request_kind("session", "nontrivial") == "nontrivial"
    assert store.is_nontrivial_turn("session", "nontrivial") is True
    assert store.is_nontrivial_trace("session", "nontrivial") is True
    assert store.is_nontrivial_turn("session", "trivial") is False
    assert store.is_nontrivial_turn("other-session", "nontrivial") is None
    assert store.is_nontrivial_turn("session", "missing") is None
    assert store.get_turn_request_kind("", "nontrivial") is None
    assert store.get_turn_request_kind("session", "") is None

    store.close_turn_evidence("session", "nontrivial")
    assert store.is_nontrivial_turn("session", "nontrivial") is True

    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET metadata = '{not-json' WHERE trace_id = 'trivial'")
        connection.commit()
    finally:
        connection.close()
    assert store.is_nontrivial_turn("session", "trivial") is None


def test_recent_specialist_projection_uses_loaded_at_index(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    connection = store._connect()
    try:
        plan = " ".join(
            str(row["detail"])
            for row in connection.execute(
                "EXPLAIN QUERY PLAN " + RECENT_ACTIVITY_QUERIES["specialists"],
                (50,),
            )
        )
    finally:
        connection.close()

    assert "idx_specialists_recent" in plan
    assert "USE TEMP B-TREE" not in plan


def test_latest_model_receipt_uses_terminal_chronology_and_insertion_tiebreak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    ids = iter(("z-first", "run", "a-second"))
    monkeypatch.setattr(store, "_uuid", lambda: next(ids))
    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        resolved_model="first",
        started_at="2026-07-14T00:00:00+00:00",
        ended_at="2026-07-14T00:00:01+00:00",
    )
    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        resolved_model="second",
        started_at="2026-07-14T00:00:00+00:00",
        ended_at="2026-07-14T00:00:01+00:00",
    )

    assert store.get_model_receipt("trace")["resolved_model"] == "second"


def test_suggested_delegation_batch_is_atomic_bounded_and_idempotent(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    suggestions = [
        {"work_unit_id": f"unit-{index}", "recommended_agent": "reviewer"} for index in range(20)
    ]

    assert (
        store.record_suggested_delegations_batch(
            trace_id="trace",
            session_id="session",
            host="test",
            suggestions=suggestions,
        )
        == 16
    )
    assert (
        store.record_suggested_delegations_batch(
            trace_id="trace",
            session_id="session",
            host="test",
            suggestions=suggestions,
        )
        == 0
    )
    assert len(store.get_delegations("trace")) == 16
    assert (
        store.record_suggested_delegations_batch(
            trace_id="trace",
            session_id="session",
            suggestions=[
                {"work_unit_id": "", "recommended_agent": "reviewer"},
                {"work_unit_id": "", "recommended_agent": "reviewer"},
            ],
        )
        == 0
    )
    with pytest.raises(ValueError, match="trace_id and session_id"):
        store.record_suggested_delegations_batch(
            trace_id="",
            session_id="session",
            suggestions=[],
        )
    store.close_turn_evidence("session", "trace")
    with pytest.raises(ValueError, match="terminal"):
        store.record_suggested_delegations_batch(
            trace_id="trace",
            session_id="session",
            suggestions=[{"work_unit_id": "late", "recommended_agent": "reviewer"}],
        )


def test_suggested_delegation_batch_rolls_back_as_one_unit(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace", session_id="session")
    connection = store._connect()
    try:
        connection.execute(
            "CREATE TRIGGER reject_batch BEFORE INSERT ON delegation_events "
            "WHEN NEW.work_unit_id = 'boom' "
            "BEGIN SELECT RAISE(ABORT, 'reject batch'); END"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(sqlite3.IntegrityError, match="reject batch"):
        store.record_suggested_delegations_batch(
            trace_id="trace",
            session_id="session",
            suggestions=[
                {"work_unit_id": "first", "recommended_agent": "reviewer"},
                {"work_unit_id": "boom", "recommended_agent": "reviewer"},
            ],
        )

    assert store.get_delegations("trace") == []


def test_schema_version_constant_tracks_specialist_identity_migration() -> None:
    assert SCHEMA_VERSION >= 13
