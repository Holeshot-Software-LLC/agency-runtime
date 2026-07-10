"""Tests for explainable selector receipts across CLI and core surfaces."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.cli.main import main
from agency_runtime.core.config import AgencyConfig, JudgeConfig, reset_config_cache
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.store.sqlite import Store


def _catalog() -> list[dict[str, object]]:
    return [
        {"slug": "code-reviewer", "name": "Code Reviewer", "description": "Reviews code"},
        {"slug": "technical-writer", "name": "Technical Writer", "description": "Writes docs"},
    ]


def _seed_store(db: Path) -> None:
    store = Store(db)
    for agent in _catalog():
        store.activate_agent(agent)


def test_explain_route_returns_selection_receipt() -> None:
    clear_cache()
    clear_session_routing()
    config = AgencyConfig(judge=JudgeConfig(confidence_bypass_threshold=1.0))

    receipt = explain_route("s1", "review code", _catalog(), config=config, limit=2)

    assert receipt["schema_version"] == "agency.selection_explain.v1"
    assert receipt["selected"][0]["slug"] == "code-reviewer"
    assert receipt["signals"]["selection"]["status"] == "confidence_bypass"
    assert receipt["signals"]["cache"]["key"]
    assert receipt["considered_candidates"][0]["selected"] is True
    assert receipt["rejected_candidates"][0]["slug"] == "technical-writer"
    assert "reason" in receipt["rejected_candidates"][0]


def test_cli_explain_json(monkeypatch, tmp_path: Path, capsys) -> None:
    clear_cache()
    clear_session_routing()
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    monkeypatch.setenv("AGENCY_BYPASS_THRESHOLD", "1")
    reset_config_cache()
    _seed_store(db)

    assert main(["explain", "review code", "--session-id", "s1", "--limit", "2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "agency.selection_explain.v1"
    assert payload["selected"][0]["slug"] == "code-reviewer"
    assert payload["signals"]["selection"]["roster_size"] == 2
