"""Retained intent: the one place the store keeps content, and its guard rails.

Selection quality was unauditable. `routing_decisions` keeps
`source_message_hash` and `query_hash` and never what was asked, so the
2026-08-11 finding -- frontend-developer staffed on a turn that excluded
frontend work, skipped on a turn that was entirely frontend work -- only
existed because two people remembered the prompts.

This retains the planner's own work-unit text beside each decision. Because
that inverts the content-free posture every other routing table holds, the
first test here is the one that matters most: with the flag off, nothing is
written at all.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from agency_runtime.cli.evidence_commands import cmd_evidence_intent
from agency_runtime.core.config import AgencyConfig, config_to_yaml
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.configuration_schema import _validate_selector, validate_config_document
from agency_runtime.core.selector.pipeline import _finalize_decision
from agency_runtime.core.store.sqlite import Store


def _routing(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "selected_ids": ["python-cli-architecture-specialist", "code-reviewer"],
        "source": "computed",
        "work_units": {
            "count": 2,
            "confidence": "high",
            "source": "verified-workforce-plan",
            "units": ["fix the provider token parameter", "add a regression test"],
            "delegate": False,
        },
        "workforce_unit_descriptors": [
            {
                "ordinal": 1,
                "artifact_kind": "implementation-change",
                "lifecycle_phase": "implementation",
                "authority": "modify",
            }
        ],
    }
    value.update(overrides)
    return value


def _args(db: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {"db": str(db), "limit": 20, "specialist": None, "json": False}
    values.update(overrides)
    return argparse.Namespace(**values)


def test_nothing_is_retained_when_the_flag_is_off(tmp_path: Path) -> None:
    """The default must leave the store exactly as content-free as it was.

    This is the whole safety property. A retention feature that writes before
    an operator asks for it is a privacy regression shipped as a feature.
    """

    db = tmp_path / "agency.db"
    store = Store(str(db))

    _finalize_decision(
        _routing(),
        session_id="session-1",
        user_message="fix the provider token parameter",
        context_fingerprint="c" * 64,
        store=store,
        trace_id="trace-1",
    )

    assert store.get_routing_intents() == []


def test_the_flag_retains_units_beside_the_specialists(tmp_path: Path) -> None:
    """The comparison an audit needs: what it understood, next to who it staffed."""

    store = Store(str(tmp_path / "agency.db"))

    _finalize_decision(
        _routing(),
        session_id="session-1",
        user_message="fix the provider token parameter",
        context_fingerprint="c" * 64,
        store=store,
        trace_id="trace-1",
        record_intent=True,
    )

    retained = store.get_routing_intents()

    assert len(retained) == 1
    assert retained[0]["units"] == [
        "fix the provider token parameter",
        "add a regression test",
    ]
    assert retained[0]["selected_ids"] == [
        "python-cli-architecture-specialist",
        "code-reviewer",
    ]
    assert retained[0]["trace_id"] == "trace-1"


def test_retention_never_fails_the_turn(tmp_path: Path) -> None:
    """Auditing is observability; a turn must not die for it."""

    class BrokenStore(Store):
        def record_routing_intent(self, *args: object, **kwargs: object) -> bool:
            raise RuntimeError("disk is gone")

    store = BrokenStore(str(tmp_path / "agency.db"))
    routing = _finalize_decision(
        _routing(),
        session_id="session-1",
        user_message="anything",
        context_fingerprint="c" * 64,
        store=store,
        trace_id="trace-1",
        record_intent=True,
    )

    assert routing["selected_ids"]


def test_unit_text_is_bounded_per_unit_and_in_count(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "agency.db"))
    work_units = {"units": ["x" * 4_000, *[f"unit {index}" for index in range(40)]]}

    store.record_routing_intent(_routing(work_units=work_units), trace_id="trace-1")

    units = store.get_routing_intents()[0]["units"]
    assert len(units) <= 16
    assert all(len(unit) <= 512 for unit in units)


def test_control_characters_never_survive_retention(tmp_path: Path) -> None:
    """Retained text is printed back to a terminal by the audit command."""

    store = Store(str(tmp_path / "agency.db"))
    store.record_routing_intent(
        _routing(work_units={"units": ["hello\x1b[31mworld\x07", "second\r\nunit"]}),
        trace_id="trace-1",
    )

    units = store.get_routing_intents()[0]["units"]

    assert "\x1b" not in "".join(units)
    assert "\x07" not in "".join(units)
    assert units[1] == "second unit"


def test_a_decision_with_neither_units_nor_specialists_is_not_retained(tmp_path: Path) -> None:
    store = Store(str(tmp_path / "agency.db"))

    assert (
        store.record_routing_intent(
            {"selected_ids": [], "work_units": {"units": []}}, trace_id="trace-1"
        )
        is False
    )
    assert store.get_routing_intents() == []


def test_retention_is_bounded_in_total(tmp_path: Path) -> None:
    """An audit trail must not grow into a transcript of everything ever asked."""

    store = Store(str(tmp_path / "agency.db"))
    for index in range(8):
        store.record_routing_intent(
            _routing(work_units={"units": [f"unit {index}"]}),
            trace_id=f"trace-{index}",
            max_entries=3,
        )

    retained = store.get_routing_intents()

    assert len(retained) == 3
    assert retained[0]["units"] == ["unit 7"]


def test_an_existing_database_gains_the_table(tmp_path: Path) -> None:
    import sqlite3

    from agency_runtime.core.store.sqlite import _v20_receipt_schema_is_current

    db = tmp_path / "agency.db"
    Store(str(db))
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript("BEGIN;\nDROP TABLE routing_intent;\nCOMMIT;")
        assert not _v20_receipt_schema_is_current(conn)
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
    assert "routing_intent" in tables


def test_the_empty_surface_distinguishes_off_from_quiet(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """"Nothing here" has two causes and an operator needs to know which."""

    db = tmp_path / "agency.db"
    Store(str(db))

    cmd_evidence_intent(_args(db))

    out = capsys.readouterr().out
    assert "record_routing_intent" in out


def test_the_surface_prints_units_against_who_was_staffed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "agency.db"
    store = Store(str(db))
    store.record_routing_intent(_routing(), trace_id="trace-1")

    assert cmd_evidence_intent(_args(db)) == 0

    out = capsys.readouterr().out
    assert "fix the provider token parameter" in out
    assert "code-reviewer" in out


def test_the_surface_filters_by_specialist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "agency.db"
    store = Store(str(db))
    store.record_routing_intent(_routing(), trace_id="trace-1")
    store.record_routing_intent(
        _routing(selected_ids=["technical-writer"], work_units={"units": ["write the doc"]}),
        trace_id="trace-2",
    )

    cmd_evidence_intent(_args(db, specialist="technical-writer"))

    out = capsys.readouterr().out
    assert "write the doc" in out
    assert "fix the provider token parameter" not in out


def test_the_setting_round_trips_through_its_own_validator() -> None:
    """Renderer and schema are separate declarations; they must agree."""

    config = replace(
        AgencyConfig(), selector=replace(AgencyConfig().selector, record_routing_intent=True)
    )

    rendered = yaml.safe_load(config_to_yaml(config, redact=False))
    validated = validate_config_document(rendered)

    assert validated["selector"]["record_routing_intent"] is True


def test_the_validator_refuses_a_non_boolean_setting() -> None:
    with pytest.raises(ConfigValidationError, match="record_routing_intent"):
        _validate_selector({"record_routing_intent": "yes please"})
