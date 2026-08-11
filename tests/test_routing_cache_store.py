"""Routing reuse that survives the process it was computed in.

The in-memory routing cache cannot hit in production: every hook event runs as
its own short-lived process, so the module-level dict is built empty and thrown
away on the same turn. Zero of 200 recorded decisions on the first box checked
came from `cache` or `session`.

These tests pin the two properties that decide whether the store-backed cache
is safe to have at all: what it is allowed to persist, and that a reused entry
is revalidated rather than trusted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.core.store.queries import _ROUTING_DECISION_FIELDS
from agency_runtime.core.store.sqlite import Store


def _routing(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "selected_ids": ["python-cli-architecture-specialist"],
        "semantic_ids": ["python-cli-architecture-specialist"],
        "source_message_hash": "b" * 64,
        "context_fingerprint": "c" * 64,
        "confidence": 0.87,
        "status": "accepted",
        "source": "semantic",
    }
    value.update(overrides)
    return value


def test_only_persistable_fields_are_written(tmp_path: Path) -> None:
    """A cache is not a reason to widen what the store retains.

    The live routing dict carries work-unit text and unit descriptors that the
    decision projection deliberately drops. Persisting the payload verbatim
    would put exactly that content into the database through a side door.
    """

    store = Store(str(tmp_path / "agency.db"))
    assert store.put_cached_routing(
        "key-1",
        _routing(
            work_units={"text": "SENSITIVE USER MESSAGE TEXT"},
            workforce_unit_descriptors=["SENSITIVE DESCRIPTOR"],
            workforce_unit_bindings={"unit": "SENSITIVE BINDING"},
            compatibility={"contract_version": 3, "selected_ids": ["x"]},
        ),
        context_fingerprint="c" * 64,
    )

    restored = store.get_cached_routing("key-1")

    assert restored is not None
    assert set(restored) <= _ROUTING_DECISION_FIELDS
    for leaked in ("work_units", "workforce_unit_descriptors", "workforce_unit_bindings"):
        assert leaked not in restored
    assert "SENSITIVE" not in str(restored)


def test_the_compatibility_receipt_is_not_persisted(tmp_path: Path) -> None:
    """Its absence is what forces the entry back through revalidation.

    A persisted receipt would let a later process accept a selection without
    re-checking it against the live catalog, which is the one way this cache
    could change which specialists a turn gets.
    """

    store = Store(str(tmp_path / "agency.db"))
    store.put_cached_routing(
        "key-1",
        _routing(compatibility={"contract_version": 99, "selected_ids": ["stale"]}),
    )

    restored = store.get_cached_routing("key-1")

    assert restored is not None
    assert "compatibility" not in restored


def test_a_decision_that_selected_nothing_is_not_cached(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "agency.db"))

    assert store.put_cached_routing("key-1", _routing(selected_ids=[])) is False
    assert store.get_cached_routing("key-1") is None


def test_entries_expire(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "agency.db"))
    store.put_cached_routing("key-1", _routing())

    assert store.get_cached_routing("key-1", max_age_seconds=600) is not None
    # Freshness is enforced in the store so a caller cannot forget to check.
    assert store.get_cached_routing("key-1", max_age_seconds=0) is None


def test_a_rewritten_key_replaces_rather_than_duplicates(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "agency.db"))
    store.put_cached_routing("key-1", _routing(selected_ids=["first"]))
    store.put_cached_routing("key-1", _routing(selected_ids=["second"]))

    restored = store.get_cached_routing("key-1")

    assert restored is not None
    assert restored["selected_ids"] == ["second"]


def test_the_cache_is_bounded(tmp_path: Path) -> None:
    """An unbounded cache in the operator's store is a disk-growth bug."""

    store = Store(str(tmp_path / "agency.db"))
    for index in range(6):
        store.put_cached_routing(f"key-{index}", _routing(), max_entries=3)

    survivors = [
        index for index in range(6) if store.get_cached_routing(f"key-{index}") is not None
    ]

    assert len(survivors) <= 3
    assert 5 in survivors


def test_an_unknown_key_is_a_miss_not_an_error(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "agency.db"))

    assert store.get_cached_routing("never-written") is None
    assert store.get_cached_routing("") is None


@pytest.mark.parametrize("payload", [{"selected_ids": ["a"], "blob": "x" * 32_000}])
def test_an_oversized_payload_is_refused(tmp_path: Path, payload: dict[str, object]) -> None:
    """A routing payload is ids, hashes and flags; anything larger is wrong."""

    store = Store(str(tmp_path / "agency.db"))

    # 'blob' is not persistable anyway, so build the oversize from a real field.
    assert (
        store.put_cached_routing(
            "key-1",
            _routing(selected_ids=[f"slug-{index}" for index in range(4000)]),
        )
        is False
    )
    assert store.get_cached_routing("key-1") is None


def test_an_existing_database_gains_the_cache_table(tmp_path: Path) -> None:
    """A table absent entirely must make the startup predicate report stale."""

    import sqlite3

    from agency_runtime.core.store.sqlite import _v20_receipt_schema_is_current

    db = tmp_path / "agency.db"
    Store(str(db))

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("BEGIN;\nDROP TABLE routing_cache;\nCOMMIT;")
        assert not _v20_receipt_schema_is_current(conn), (
            "the staleness predicate does not require routing_cache, so no existing "
            "database would ever be migrated to create it"
        )
    finally:
        conn.close()

    Store(str(db))
    conn = sqlite3.connect(db)
    try:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()
    assert "routing_cache" in tables
