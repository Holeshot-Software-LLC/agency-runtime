"""Atomic full-roster installation and compatibility fallback tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.cli import install_commands
from agency_runtime.core import installer
from agency_runtime.core.store import roster as roster_module
from agency_runtime.core.store.sqlite import Store


def _agent(slug: str, *, content: str | None = None) -> dict[str, object]:
    return {
        "slug": slug,
        "name": f"{slug} name",
        "division": "engineering",
        "description": f"{slug} description",
        "version": "1.0.0",
        "prompt_body": content or f"You are {slug}.",
        "categories": ["engineering", "testing"],
        "capabilities": ["testing"],
        "tool_affinity": ["tests"],
    }


def _generation(store: Store) -> int:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT value FROM store_counters WHERE name = 'roster-generation'"
        ).fetchone()
        assert row is not None
        return int(row["value"])
    finally:
        conn.close()


def _version_count(store: Store, slug: str) -> int:
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS count FROM agent_versions WHERE agent_slug = ?",
            (slug,),
        ).fetchone()
        assert row is not None
        return int(row["count"])
    finally:
        conn.close()


def test_bulk_activation_is_atomic_idempotent_and_generation_exact(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    agents = [_agent("alpha"), _agent("beta"), _agent("gamma")]

    assert store._activate_prevalidated_agents_if_missing(agents) == 3
    assert [row["agent_slug"] for row in store.get_active_roster()] == [
        "alpha",
        "beta",
        "gamma",
    ]
    assert _generation(store) == 3

    assert store._activate_prevalidated_agents_if_missing([dict(agent) for agent in agents]) == 0
    assert _generation(store) == 3


def test_bulk_activation_preserves_operator_entries_and_reuses_versions(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    operator = _agent("operator-owned-specialist", content="Operator-owned prompt.")
    store._activate_prevalidated_agent(operator)

    assert (
        store._activate_prevalidated_agents_if_missing([_agent("operator-owned-specialist")]) == 0
    )
    prompt = store.get_specialist_prompt("operator-owned-specialist")
    assert prompt is not None
    assert prompt["prompt_body"] == "Operator-owned prompt."

    store.deactivate_agent("operator-owned-specialist")
    assert store._activate_prevalidated_agents_if_missing([dict(operator)]) == 1
    assert _version_count(store, "operator-owned-specialist") == 1


def test_bulk_immutable_conflict_rolls_back_every_entry(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    original = _agent("beta", content="Original immutable content.")
    store._activate_prevalidated_agent(original)
    store.deactivate_agent("beta")
    generation = _generation(store)

    with pytest.raises(ValueError, match=r"immutable agent version conflict for beta@1\.0\.0"):
        store._activate_prevalidated_agents_if_missing(
            [
                _agent("alpha"),
                _agent("beta", content="Changed content under the same version."),
            ]
        )

    assert store.get_active_roster() == []
    assert _version_count(store, "alpha") == 0
    assert _version_count(store, "beta") == 1
    assert _generation(store) == generation


def test_bulk_inputs_are_bounded_and_prevalidated_before_connect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    def unexpected_connect() -> Any:
        raise AssertionError("invalid batch opened the database")

    monkeypatch.setattr(store, "_connect", unexpected_connect)
    assert store._activate_prevalidated_agents_if_missing([]) == 0
    with pytest.raises(TypeError, match="sequence of mappings"):
        store._activate_prevalidated_agents_if_missing({})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="every roster entry"):
        store._activate_prevalidated_agents_if_missing([object()])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="duplicate roster slug"):
        store._activate_prevalidated_agents_if_missing([_agent("duplicate"), _agent("duplicate")])
    with pytest.raises(ValueError, match="at most 1 entries"):
        monkeypatch.setattr(roster_module, "_MAX_ACTIVE_ROSTER_LIMIT", 1)
        store._activate_prevalidated_agents_if_missing([_agent("one"), _agent("two")])


def test_bulk_activation_rejects_total_roster_overflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("existing"))
    monkeypatch.setattr(roster_module, "_MAX_ACTIVE_ROSTER_LIMIT", 1)

    with pytest.raises(ValueError, match="active roster cannot exceed 1 entries"):
        store._activate_prevalidated_agents_if_missing([_agent("new")])

    assert [row["agent_slug"] for row in store.get_active_roster()] == ["existing"]


def test_install_seed_uses_atomic_bulk_api_when_available() -> None:
    class BulkStore:
        def __init__(self) -> None:
            self.received: object = None

        def activate_agents_if_missing(self, agents: object) -> int:
            self.received = agents
            return 7

    store = BulkStore()
    assert installer.seed_starter_roster(store) == 7  # type: ignore[arg-type]
    assert store.received is installer.STARTER_ROSTER


def test_cli_seed_uses_atomic_bulk_api_and_records_event() -> None:
    class BulkStore:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def activate_agents_if_missing(self, agents: object) -> int:
            assert agents is install_commands.STARTER_ROSTER
            return 5

        def record_import_event(self, event: str, source: str, detail: str) -> None:
            self.events.append((event, source, detail))

    store = BulkStore()
    assert install_commands._seed_starter_roster(store) == 5  # type: ignore[arg-type]
    assert store.events == [("starter_roster_installed", "", "count=5")]
