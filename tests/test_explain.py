"""Tests for explainable selector receipts across CLI and core surfaces."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from agency_runtime.cli.main import build_parser, main
from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig, reset_config_cache
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.store.sqlite import Store


def _catalog() -> list[dict[str, object]]:
    return [
        {
            "slug": "fixture-code-reviewer",
            "name": "Code Reviewer",
            "description": "Reviews code",
            "prompt_body": "Review code and report actionable correctness findings.",
        },
        {
            "slug": "fixture-technical-writer",
            "name": "Technical Writer",
            "description": "Writes docs",
            "prompt_body": "Write clear, accurate technical documentation.",
        },
    ]


def _seed_store(db: Path) -> None:
    store = Store(db)
    for agent in _catalog():
        store._activate_prevalidated_agent(agent)


@pytest.fixture
def _isolated_selector_state() -> Iterator[None]:
    """Reset process-local routing state even when an assertion fails."""
    reset_config_cache()
    clear_cache()
    clear_session_routing()
    yield
    clear_session_routing()
    clear_cache()
    reset_config_cache()


def test_explain_route_returns_selection_receipt(_isolated_selector_state) -> None:
    config = AgencyConfig(
        judge=JudgeConfig(confidence_bypass_threshold=1.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )

    receipt = explain_route("s1", "review code", _catalog(), config=config, limit=2)

    assert receipt["schema_version"] == "agency.selection_explain.v1"
    assert receipt["selected"][0]["slug"] == "fixture-code-reviewer"
    assert receipt["signals"]["selection"]["status"] == "confidence_bypass"
    assert receipt["signals"]["cache"]["key"]
    assert receipt["considered_candidates"][0]["selected"] is True
    assert receipt["rejected_candidates"][0]["slug"] == "fixture-technical-writer"
    assert "reason" in receipt["rejected_candidates"][0]


def test_cli_explain_json(
    _isolated_selector_state,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_BYPASS_THRESHOLD", "1")
    _seed_store(db)

    payload = {}
    for _attempt in range(2):
        assert main(["explain", "review code", "--session-id", "s1", "--limit", "2"]) == 0
        payload = json.loads(capsys.readouterr().out)

    assert payload["schema_version"] == "agency.selection_explain.v1"
    assert payload["selected"][0]["slug"] == "fixture-code-reviewer"
    assert payload["signals"]["selection"]["roster_size"] == 2
    assert "decision_id" not in payload["routing"]
    assert Store(db).get_open_traces_for_session("s1") == []


def test_cli_route_is_repeatably_diagnostic(
    _isolated_selector_state,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_BYPASS_THRESHOLD", "1")
    _seed_store(db)

    for _attempt in range(2):
        assert main(["route", "review code", "--json"]) == 0

    capsys.readouterr()
    store = Store(db)
    assert store.get_open_traces_for_session("cli") == []
    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM routing_decisions").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("command", ["search", "route", "explain"])
@pytest.mark.parametrize("limit", ["0", "-1"])
def test_selector_cli_rejects_nonpositive_limits(
    command: str,
    limit: str,
    capsys,
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args([command, "review code", "--limit", limit])

    assert exc_info.value.code == 2
    assert "positive integer" in capsys.readouterr().err
