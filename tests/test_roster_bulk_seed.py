"""Atomic full-roster installation and compatibility fallback tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from agency_runtime.cli import install_commands
from agency_runtime.core import installer
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.store import roster as roster_module
from agency_runtime.core.store.roster import BundledRosterReconciliation
from agency_runtime.core.store.sqlite import Store

_LEGACY_CODE_REVIEWER: dict[str, Any] = {
    "name": "Code Reviewer",
    "division": "engineering",
    "description": (
        "Reviews diffs for correctness, maintainability, tests, security, and production risk."
    ),
    "categories": ["code", "review", "quality"],
    "capabilities": [
        "code review",
        "bug finding",
        "test assessment",
        "security review",
    ],
    "tool_affinity": ["git", "github", "tests"],
    "prompt_body": (
        "You are a senior code reviewer. Focus on concrete correctness issues, regressions, "
        "missing tests, security risks, and maintainability problems."
    ),
}
_LEGACY_IDENTITY_ALLOWLIST_DIGEST = (
    "1c7593d3dc84cb186c40280475e8ae374dc5e1ba26cac7838bf785712f5637ac"
)


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


def _insert_legacy_bundled_active(
    store: Store,
    *,
    slug: str,
    source: str = "bundled",
    metadata: str = "{}",
    content: str | None = None,
    name: str | None = None,
) -> str:
    assert slug == "code-reviewer"
    legacy_content = content or _LEGACY_CODE_REVIEWER["prompt_body"]
    legacy_hash = hashlib.sha256(legacy_content.encode("utf-8")).hexdigest()
    conn = store._connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO agent_versions "
            "(id, agent_slug, version, hash, content, metadata, created_at) "
            "VALUES (?, ?, '1.0.0', ?, ?, ?, ?)",
            (
                str(uuid4()),
                slug,
                legacy_hash,
                legacy_content,
                metadata,
                store._now(),
            ),
        )
        conn.execute(
            "INSERT INTO agent_active "
            "(id, agent_slug, name, division, description, source, version, hash, "
            "categories, capabilities, tool_affinity, prompt_path, activated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, '1.0.0', ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                slug,
                name or _LEGACY_CODE_REVIEWER["name"],
                _LEGACY_CODE_REVIEWER["division"],
                _LEGACY_CODE_REVIEWER["description"],
                source,
                legacy_hash,
                json.dumps(_LEGACY_CODE_REVIEWER["categories"]),
                json.dumps(_LEGACY_CODE_REVIEWER["capabilities"]),
                json.dumps(_LEGACY_CODE_REVIEWER["tool_affinity"]),
                f"bundled://{slug}",
                store._now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return legacy_hash


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


def test_bundled_reconciliation_inputs_are_bounded_before_connect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    def unexpected_connect() -> Any:
        raise AssertionError("invalid reconciliation opened the database")

    monkeypatch.setattr(store, "_connect", unexpected_connect)
    assert store.reconcile_bundled_agents([]) == BundledRosterReconciliation(
        added=0,
        upgraded=0,
    )
    with pytest.raises(TypeError, match="sequence of mappings"):
        store.reconcile_bundled_agents({})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="every roster entry"):
        store.reconcile_bundled_agents([object()])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="duplicate roster slug"):
        store.reconcile_bundled_agents([STARTER_ROSTER[0], STARTER_ROSTER[0]])
    monkeypatch.setattr(roster_module, "_MAX_ACTIVE_ROSTER_LIMIT", 1)
    with pytest.raises(ValueError, match="at most 1 entries"):
        store.reconcile_bundled_agents([STARTER_ROSTER[0], STARTER_ROSTER[1]])


def test_bundled_reconciliation_rejects_total_roster_overflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("operator-owned"))
    monkeypatch.setattr(roster_module, "_MAX_ACTIVE_ROSTER_LIMIT", 1)

    with pytest.raises(ValueError, match="active roster cannot exceed 1 entries"):
        store.reconcile_bundled_agents([STARTER_ROSTER[0]])

    assert [row["agent_slug"] for row in store.get_active_roster()] == ["operator-owned"]


def test_legacy_bundled_migration_authority_is_immutable_and_slug_bounded() -> None:
    serialized = json.dumps(
        roster_module._LEGACY_BUNDLED_IDENTITIES,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert hashlib.sha256(serialized).hexdigest() == _LEGACY_IDENTITY_ALLOWLIST_DIGEST
    assert set(roster_module._LEGACY_BUNDLED_IDENTITIES) == {
        "workflow-architect",
        "code-reviewer",
        "senior-developer",
        "technical-writer",
        "internationalization-engineer",
        "payments-billing-engineer",
        "test-automation-engineer",
    }
    assert roster_module._is_legacy_bundled_active({}, "unknown-specialist") is False


def test_bundled_reconciliation_upgrades_only_the_legacy_package_shape(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    canonical = next(agent for agent in STARTER_ROSTER if agent["slug"] == "code-reviewer")
    _insert_legacy_bundled_active(store, slug="code-reviewer")
    generation = _generation(store)

    assert store.reconcile_bundled_agents([canonical]) == BundledRosterReconciliation(
        added=0,
        upgraded=1,
    )
    assert store.reconcile_bundled_agents([canonical]) == BundledRosterReconciliation(
        added=0,
        upgraded=0,
    )
    assert _generation(store) == generation + 1
    active = store.get_roster_entry("code-reviewer")
    assert active is not None
    assert active["version"] == canonical["version"]
    assert active["hash"] == canonical["hash"]
    assert active["source_id"] == canonical["source_id"]
    assert _version_count(store, "code-reviewer") == 2
    catalog = store.get_active_roster_as_catalog()
    assert catalog[0]["routing_contract_valid"] is True


@pytest.mark.parametrize(
    ("source", "metadata"),
    [
        ("operator-owned", "{}"),
        ("bundled", '{"name":"near-miss"}'),
    ],
)
def test_bundled_reconciliation_preserves_legacy_near_misses(
    tmp_path: Path,
    source: str,
    metadata: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    canonical = next(agent for agent in STARTER_ROSTER if agent["slug"] == "code-reviewer")
    legacy_hash = _insert_legacy_bundled_active(
        store,
        slug="code-reviewer",
        source=source,
        metadata=metadata,
    )
    generation = _generation(store)

    assert store.reconcile_bundled_agents([canonical]) == BundledRosterReconciliation(
        added=0,
        upgraded=0,
    )
    assert _generation(store) == generation
    active = store.get_roster_entry("code-reviewer")
    assert active is not None
    assert active["version"] == "1.0.0"
    assert active["hash"] == legacy_hash
    assert active["source"] == source


@pytest.mark.parametrize(
    ("content", "name"),
    [
        ("Operator-authored prompt under a bundled-looking row.", None),
        (None, "Customized Code Reviewer"),
    ],
)
def test_bundled_reconciliation_requires_exact_historical_identity(
    tmp_path: Path,
    content: str | None,
    name: str | None,
) -> None:
    store = Store(tmp_path / "agency.db")
    canonical = next(agent for agent in STARTER_ROSTER if agent["slug"] == "code-reviewer")
    legacy_hash = _insert_legacy_bundled_active(
        store,
        slug="code-reviewer",
        content=content,
        name=name,
    )

    assert store.reconcile_bundled_agents([canonical]) == BundledRosterReconciliation(
        added=0,
        upgraded=0,
    )
    active = store.get_roster_entry("code-reviewer")
    assert active is not None
    assert active["hash"] == legacy_hash
    assert active["name"] == (name or _LEGACY_CODE_REVIEWER["name"])


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


def test_install_seed_supports_the_legacy_single_agent_store_contract() -> None:
    class SingleStore:
        def __init__(self) -> None:
            self.received: list[object] = []

        def activate_agent_if_missing(self, agent: object) -> bool:
            self.received.append(agent)
            return len(self.received) <= 2

    store = SingleStore()
    assert installer.seed_starter_roster(store) == 2  # type: ignore[arg-type]
    assert len(store.received) == len(installer.STARTER_ROSTER)


def test_install_seed_prefers_legacy_bundled_reconciliation() -> None:
    class ReconcileStore:
        def __init__(self) -> None:
            self.received: object = None

        def reconcile_bundled_agents(self, agents: object) -> int:
            self.received = agents
            return 3

        def activate_agents_if_missing(self, _agents: object) -> int:
            raise AssertionError("missing-only seed must not bypass reconciliation")

    store = ReconcileStore()
    assert installer.seed_starter_roster(store) == 3  # type: ignore[arg-type]
    assert store.received is installer.STARTER_ROSTER


def test_install_seed_reports_legacy_upgrades_separately_from_additions() -> None:
    class ReconcileStore:
        def reconcile_bundled_agents(self, _agents: object) -> BundledRosterReconciliation:
            return BundledRosterReconciliation(added=0, upgraded=3)

    store = ReconcileStore()
    result = installer.reconcile_starter_roster(store)  # type: ignore[arg-type]
    assert result == BundledRosterReconciliation(added=0, upgraded=3)
    seeded = installer.seed_starter_roster(store)  # type: ignore[arg-type]
    assert seeded == 0
    assert seeded.upgraded == 3  # type: ignore[attr-defined]


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


def test_cli_seed_records_legacy_upgrades_without_reporting_them_as_added() -> None:
    class ReconcileStore:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str]] = []

        def reconcile_bundled_agents(self, _agents: object) -> BundledRosterReconciliation:
            return BundledRosterReconciliation(added=0, upgraded=3)

        def record_import_event(self, event: str, source: str, detail: str) -> None:
            self.events.append((event, source, detail))

    store = ReconcileStore()
    assert install_commands._seed_starter_roster(store) == 0  # type: ignore[arg-type]
    assert store.events == [
        ("starter_roster_installed", "", "count=0"),
        ("starter_roster_upgraded", "", "count=3"),
    ]
