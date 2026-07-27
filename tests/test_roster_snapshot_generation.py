"""Roster-generation and lightweight snapshot contract tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.store.sqlite import Store


def _agent(slug: str) -> dict[str, object]:
    return {
        "slug": slug,
        "name": f"{slug} name",
        "division": "engineering",
        "description": f"{slug} exact routing description",
        "version": "1.0.0",
        "content": f"You are {slug}.",
        "categories": ["engineering", "review"],
        "capabilities": ["review", "testing"],
    }


def _roster_generation(store: Store) -> int:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT value, typeof(value) AS value_type FROM store_counters "
            "WHERE name = 'roster-generation'"
        ).fetchone()
        assert row is not None
        assert row["value_type"] == "integer"
        return int(row["value"])
    finally:
        conn.close()


def test_roster_generation_tracks_only_effective_membership_changes(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    agent = _agent("alpha-reviewer")

    assert _roster_generation(store) == 0
    assert store.get_roster_generation() == 0
    store._activate_prevalidated_agent(agent)
    assert _roster_generation(store) == 1
    assert store.get_roster_generation() == 1

    assert store._activate_prevalidated_agent_if_missing(agent) is False
    assert _roster_generation(store) == 1

    store.deactivate_agent("missing-reviewer")
    assert _roster_generation(store) == 1
    store.deactivate_agent("alpha-reviewer")
    assert _roster_generation(store) == 2
    assert store.get_roster_generation() == 2


def test_active_roster_slug_lookup_is_bounded_and_uses_complete_definitions(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("alpha-reviewer"))

    assert store.get_active_roster_slugs(()) == frozenset()
    assert store.get_active_roster_slugs({"missing-reviewer", "alpha-reviewer"}) == frozenset(
        {"alpha-reviewer"}
    )
    with pytest.raises(TypeError, match="collection of strings"):
        store.get_active_roster_slugs("alpha-reviewer")
    with pytest.raises(ValueError, match="at most 16"):
        store.get_active_roster_slugs(tuple(f"reviewer-{index}" for index in range(17)))


def test_roster_snapshots_share_generation_counts_and_projection_boundaries(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("alpha-reviewer"))
    store._activate_prevalidated_agent(_agent("beta-reviewer"))
    disabled = frozenset({"beta-reviewer"})

    selector = store.get_active_roster_page_snapshot(
        limit=1,
        disabled_agents=disabled,
    )
    ui = store.get_active_roster_ui_page_snapshot(
        limit=1,
        disabled_agents=disabled,
    )
    entry = store.get_active_roster_entry_snapshot(
        "alpha-reviewer",
        disabled_agents=disabled,
    )

    for snapshot in (selector, ui, entry):
        assert snapshot["generation"] == 2
        assert snapshot["total_count"] == 2
        assert snapshot["enabled_count"] == 1
    assert selector["rows"][0]["description"] == "alpha-reviewer exact routing description"
    assert set(ui["rows"][0]) == {
        "agent_slug",
        "name",
        "division",
        "capabilities",
    }
    assert ui["rows"][0]["capabilities"] == ["review", "testing"]
    assert entry["rows"][0]["agent_slug"] == "alpha-reviewer"


def test_enabled_roster_snapshot_filters_and_limits_inside_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    for slug in ("alpha-reviewer", "beta-reviewer", "delta-reviewer", "gamma-reviewer"):
        store._activate_prevalidated_agent(_agent(slug))

    statements: list[tuple[str, tuple[Any, ...]]] = []
    original_connect = store._connect

    class RecordingConnection:
        def __init__(self, connection: Any) -> None:
            self._connection = connection

        def execute(self, statement: str, parameters: Any = ()) -> Any:
            statements.append((statement, tuple(parameters)))
            return self._connection.execute(statement, parameters)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._connection, name)

    monkeypatch.setattr(store, "_connect", lambda: RecordingConnection(original_connect()))

    snapshot = store.get_enabled_roster_page_snapshot(
        limit=1,
        after="alpha-reviewer",
        disabled_agents=frozenset({"beta-reviewer"}),
    )

    assert snapshot["generation"] == 4
    assert snapshot["total_count"] == 3
    assert [row["agent_slug"] for row in snapshot["rows"]] == [
        "delta-reviewer",
        "gamma-reviewer",
    ]
    page_statement, page_parameters = next(
        item
        for item in statements
        if "workforce_recruitment_contract" in item[0] and "ORDER BY a.agent_slug" in item[0]
    )
    assert "json_each(?)" in page_statement
    assert "LIMIT ?" in page_statement
    assert page_parameters[-1] == 2


def test_enabled_roster_snapshot_is_generation_consistent_during_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "agency.db"
    reader = Store(db_path)
    writer = Store(db_path)
    reader._activate_prevalidated_agent(_agent("alpha-reviewer"))
    reader._activate_prevalidated_agent(_agent("beta-reviewer"))
    original_connect = reader._connect
    activation_fired = False

    class InterleavingConnection:
        def __init__(self, connection: Any) -> None:
            self._connection = connection

        def execute(self, statement: str, parameters: Any = ()) -> Any:
            nonlocal activation_fired
            cursor = self._connection.execute(statement, parameters)
            if (
                "store_counters WHERE name = 'roster-generation'" in statement
                and not activation_fired
            ):
                activation_fired = True
                writer._activate_prevalidated_agent(_agent("gamma-reviewer"))
            return cursor

        def __getattr__(self, name: str) -> Any:
            return getattr(self._connection, name)

    monkeypatch.setattr(reader, "_connect", lambda: InterleavingConnection(original_connect()))

    snapshot = reader.get_enabled_roster_page_snapshot(limit=2)

    assert activation_fired is True
    assert snapshot["generation"] == 2
    assert snapshot["total_count"] == 2
    assert [row["agent_slug"] for row in snapshot["rows"]] == [
        "alpha-reviewer",
        "beta-reviewer",
    ]
    assert writer.get_roster_generation() == 3


def test_ui_snapshot_bounds_max_capabilities_and_tolerates_legacy_json(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("alpha-reviewer"))
    maximum = [f"{index:03d}-" + ("x" * 508) for index in range(256)]
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_active SET capabilities = ? WHERE agent_slug = ?",
            (json.dumps(maximum), "alpha-reviewer"),
        )
        conn.commit()
    finally:
        conn.close()

    page = store.get_active_roster_ui_page_snapshot(limit=1)
    assert page["rows"][0]["capabilities"] == maximum[:4]
    assert all(len(value.encode("utf-8")) == 512 for value in page["rows"][0]["capabilities"])

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_active SET capabilities = ? WHERE agent_slug = ?",
            ("not-json", "alpha-reviewer"),
        )
        conn.commit()
    finally:
        conn.close()
    assert store.get_active_roster_ui_page_snapshot(limit=1)["rows"][0]["capabilities"] == []
