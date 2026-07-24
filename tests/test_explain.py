"""Tests for explainable selector receipts across CLI and core surfaces."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from agency_runtime.cli import roster_commands
from agency_runtime.cli.main import build_parser, main
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
    reset_config_cache,
)
from agency_runtime.core.host_capabilities import (
    diagnostic_installation_capability_receipt,
    host_capability_receipt_from_native_evidence,
)
from agency_runtime.core.selector import pipeline
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


def _stored_catalog() -> list[dict[str, object]]:
    agents = _catalog()
    agents[0].update(
        {
            "categories": ["software-engineering", "review"],
            "division": "engineering",
            "capabilities": ["review-diffs", "code-review"],
            "task_types": ["review"],
            "outcomes": ["Independently review code for defects and regressions"],
            "scope_qualifiers": ["review diffs"],
            "artifact_kinds": ["review-report"],
            "lifecycle_phases": ["review"],
            "domains": ["software-engineering"],
            "authority": "review",
            "context_mode": "isolated_only",
            "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "approved",
            "audit_revision": "fixture-v1",
            "routing_contract_valid": True,
            "version": "1.0.0",
        }
    )
    agents[1].update(
        {
            "categories": ["documentation"],
            "division": "documentation",
            "capabilities": ["technical-writing"],
            "task_types": ["documentation"],
            "outcomes": ["Produce accurate technical documentation"],
            "scope_qualifiers": ["technical writing"],
            "artifact_kinds": ["documentation"],
            "lifecycle_phases": ["implementation"],
            "domains": ["documentation"],
            "authority": "modify",
            "context_mode": "isolated_only",
            "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "approved",
            "audit_revision": "fixture-v1",
            "routing_contract_valid": True,
            "version": "1.0.0",
        }
    )
    for agent in agents:
        prompt = str(agent["prompt_body"])
        agent["hash"] = hashlib.sha256(prompt.encode()).hexdigest()
    return agents


def _seed_store(db: Path) -> None:
    store = Store(db)
    for agent in _stored_catalog():
        store._activate_prevalidated_agent(agent)


def _verified_diagnostic_context() -> dict[str, object]:
    inventory = host_capability_receipt_from_native_evidence(
        "codex",
        platform="windows",
        native_record={
            "host": "codex",
            "executable_discovered": True,
            "registered": True,
            "enabled": True,
            "managed_plugin_version": "fixture-v1",
            "launcher_artifacts_current": True,
        },
    )
    receipt = diagnostic_installation_capability_receipt(
        inventory,
        surface="codex",
        platform="windows",
    )
    assert receipt is not None
    return {"host": "codex", "platform": "windows", "capability_receipt": receipt}


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


@pytest.mark.parametrize("with_store", [False, True])
def test_explain_route_skips_inference_for_known_empty_social_turn(
    _isolated_selector_state,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    with_store: bool,
) -> None:
    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="configured",
                type="openai-compatible",
                model="configured-model",
                base_url="https://configured.invalid/v1",
                api_key="test-key",
                timeout=5.0,
            ),
        ),
        judge=JudgeConfig(confidence_bypass_threshold=0.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pure social diagnostic called inference")
        ),
    )
    store = Store(tmp_path / "agency.db") if with_store else None

    receipt = explain_route("social-session", "hello", _catalog(), config=config, store=store)

    routing = receipt["routing"]
    assert routing["turn_kind"] == "conversation"
    assert routing["selection_required"] is False
    assert routing["inference_required"] is False
    assert routing["inference_attempted"] is False
    assert routing["provider_attempts"] == []
    assert routing["selected_ids"] == []


def test_cli_explain_json(
    _isolated_selector_state,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    from tests.runtime_support import stub_inference_invoker, write_provider_config

    db = tmp_path / "agency.db"
    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path, db_path=db)
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("AGENCY_BYPASS_THRESHOLD", "1")
    reset_config_cache()
    monkeypatch.setattr(
        roster_commands,
        "_single_verified_route_host",
        lambda _store: _verified_diagnostic_context(),
    )
    _seed_store(db)

    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("fixture-code-reviewer",),
    )
    try:
        payload = {}
        for _attempt in range(2):
            assert main(["explain", "review code", "--session-id", "s1", "--limit", "2"]) == 0
            payload = json.loads(capsys.readouterr().out)
            assert payload["selected"], payload
    finally:
        _inference.invoke_structured_provider_result = original_invoker
        reset_config_cache()

    assert payload["schema_version"] == "agency.selection_explain.v1"
    assert payload["selected"][0]["slug"] == "fixture-code-reviewer"
    assert payload["signals"]["selection"]["roster_size"] >= 2
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


def test_cli_route_marks_fresh_social_diagnostic_trivial(
    _isolated_selector_state,
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    _seed_store(db)

    assert main(["route", "hello", "--json"]) == 0

    routing = json.loads(capsys.readouterr().out)["routing"]
    assert routing["turn_kind"] == "conversation"
    assert routing["selection_required"] is False
    assert routing["inference_attempted"] is False
    assert routing["provider_attempts"] == []
    assert set(routing["selected_ids"]) <= {"agents-orchestrator", "chief-of-staff"}


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
