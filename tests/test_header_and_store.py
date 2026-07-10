"""Tests for header contract, model receipts, and store."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency_runtime.core.header.contract import (
    parse_header,
    format_header,
    validate_header,
    finalize_header,
)
from agency_runtime.core.receipts.normalize import (
    normalize_litellm_receipt,
    build_unavailable_receipt,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.policy.profiles import LOCAL_ONLY, STANDARD, POWER, YOLO
from agency_runtime.core.policy.defaults import STARTER_ROSTER


# ─── Header contract ────────────────────────────────────────────────


SAMPLE_HEADER = """Agency/Agencies loaded: code-reviewer
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: task-general -> openai/gpt-5.5
Why: Code review requested
How it shaped outcome: Loaded code review specialist

This is the body of the response.
"""


def test_parse_header():
    fields = parse_header(SAMPLE_HEADER)
    assert fields["agencies_loaded"] == "code-reviewer"
    assert fields["skills_loaded"] == "none"
    assert "gpt-5.5" in fields["actual_model_selected"]


def test_validate_header_valid():
    valid, missing = validate_header(SAMPLE_HEADER)
    assert valid is True
    assert missing == []


def test_validate_header_missing_fields():
    bad = "Agency/Agencies loaded: code-reviewer\n\nBody text."
    valid, missing = validate_header(bad)
    assert valid is False
    assert len(missing) > 0


def test_format_header():
    fields = {
        "agencies_loaded": "code-reviewer",
        "agencies_delegated": "none",
        "skills_loaded": "none",
        "actual_model_selected": "task-general -> openai/gpt-5.5",
        "why": "test",
        "how_it_shaped_outcome": "test",
    }
    text = format_header(fields)
    assert "code-reviewer" in text
    assert "Actual Model selected:" in text


# ─── Model receipts ─────────────────────────────────────────────────


def test_normalize_litellm_receipt():
    headers = {
        "x-litellm-model-group": "task-general",
        "x-litellm-model-api-base": "https://api.openai.com/v1",
        "x-litellm-model-id": "gpt-5.5",
        "x-litellm-attempted-fallbacks": "0",
    }
    receipt = normalize_litellm_receipt(headers, "task-general")
    assert receipt["model_group"] == "task-general"
    assert receipt["resolved_model"] == "gpt-5.5"
    assert receipt["source"] == "litellm"


def test_build_unavailable_receipt():
    receipt = build_unavailable_receipt("task-general", "no gateway")
    assert receipt["resolved_model"] == "unavailable"
    assert receipt["source"] == "unknown"
    assert receipt["status"] in ("unavailable", "error")


# ─── Store ──────────────────────────────────────────────────────────


def test_store_create():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        assert store.db_path.exists()


def test_store_skill_recording():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_skill_loaded("session-1", "code-review")
        store.record_skill_loaded("session-1", "testing")
        skills = store.get_skills_for_session("session-1")
        assert "code-review" in skills
        assert "testing" in skills


def test_store_model_receipt():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        receipt_id = store.record_model_receipt(
            trace_id="trace-1",
            session_id="session-1",
            host="hermes",
            requested_model="task-general",
            resolved_provider="openai",
            resolved_model="gpt-5.5",
            source="litellm",
            status="success",
        )
        receipt = store.get_model_receipt("trace-1")
        assert receipt is not None
        assert receipt["resolved_model"] == "gpt-5.5"


def test_hermes_adapter_post_api_request_captures_dynamic_model():
    """The adapter must capture the resolved model from the response body,
    not from SpendLogs or static fallback chains."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        from agency_runtime.adapters.hermes.plugin import HermesAdapter
        adapter = HermesAdapter(store=store)

        # Simulate a response where LiteLLM complexity-routed to gpt-5.5-pro-extended
        adapter.post_api_request_handler(
            response={"model": "chatgpt/gpt-5.5-pro-extended", "usage": {}},
            model="task-chunk-planner",
            session_id="test-session",
            started_at="2026-07-08T20:00:00Z",
            ended_at="2026-07-08T20:00:05Z",
        )

        # Verify receipt was recorded with the ACTUAL model, not the alias
        receipt = store.get_model_receipt_for_session("test-session")
        assert receipt is not None
        assert receipt["resolved_model"] == "gpt-5.5-pro-extended"
        assert receipt["resolved_provider"] == "chatgpt"
        assert receipt["requested_model"] == "task-chunk-planner"
        assert receipt["source"] == "host"


def test_hermes_adapter_post_api_request_no_response_model():
    """When host telemetry lacks model truth, record an honest unavailable receipt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        from agency_runtime.adapters.hermes.plugin import HermesAdapter
        adapter = HermesAdapter(store=store)

        adapter.post_api_request_handler(
            response={"choices": []},
            model="task-general",
            session_id="test-session",
        )
        receipt = store.get_model_receipt_for_session("test-session")
        assert receipt is not None
        assert receipt["resolved_model"] == "unavailable"
        assert receipt["status"] == "unavailable"
        assert receipt["source"] == "unknown"


def test_hermes_adapter_post_tool_call_records_specialist_load():
    """Loading a specialist via agency_agents_load should record it in specialists_loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        from agency_runtime.adapters.hermes.plugin import HermesAdapter
        adapter = HermesAdapter(store=store)

        adapter.post_tool_call_handler(
            tool_name="agency_agents_load",
            args={"agent": "codebase-onboarding-engineer"},
            session_id="test-session",
        )

        specialists = store.get_specialists_for_session("test-session")
        assert len(specialists) == 1
        assert specialists[0] == "codebase-onboarding-engineer"


def test_hermes_adapter_post_tool_call_records_skill_load():
    """Loading a skill via skill_view should record it in skills_loaded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        from agency_runtime.adapters.hermes.plugin import HermesAdapter
        adapter = HermesAdapter(store=store)

        adapter.post_tool_call_handler(
            tool_name="skill_view",
            args={"name": "graphify"},
            session_id="test-session",
        )

        skills = store.get_skills_for_session("test-session")
        assert "graphify" in skills


def test_hermes_adapter_post_tool_call_ignores_unknown_tools():
    """Irrelevant tool calls should not crash or pollute the store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        from agency_runtime.adapters.hermes.plugin import HermesAdapter
        adapter = HermesAdapter(store=store)

        adapter.post_tool_call_handler(
            tool_name="terminal",
            args={"command": "ls"},
            session_id="test-session",
        )

        specialists = store.get_specialists_for_session("test-session")
        skills = store.get_skills_for_session("test-session")
        assert len(specialists) == 0
        assert len(skills) == 0


def test_header_reflects_loaded_specialist():
    """The header fill pipeline should report specialists from specialists_loaded, not default to 'none'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_specialist_loaded("s1", "code-reviewer")
        store.record_specialist_loaded("s1", "codebase-onboarding-engineer")

        from agency_runtime.core.header.contract import fill_header_fields
        filled = fill_header_fields({}, "s1", store, "task-chunk-planner")
        assert filled["agencies_loaded"] == "code-reviewer, codebase-onboarding-engineer"


def test_header_replaces_bare_none_when_store_has_agency_evidence():
    """Bare 'none' is only valid when the store has no loaded/delegated evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_specialist_loaded("s1", "code-reviewer")
        store.record_delegation(
            trace_id="trace-1",
            session_id="s1",
            recommended_agent="code-reviewer",
            status="delegated",
            backend="delegate_task",
        )

        from agency_runtime.core.header.contract import fill_header_fields
        filled = fill_header_fields(
            {"agencies_loaded": "none", "agencies_delegated": "none"},
            "s1",
            store,
            "task-chunk-planner",
        )
        assert filled["agencies_loaded"] == "code-reviewer"
        assert filled["agencies_delegated"] == "code-reviewer via delegate_task"


def test_header_replaces_noneish_loaded_reason_when_store_has_agency_evidence():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_specialist_loaded("s1", "senior-developer")

        from agency_runtime.core.header.contract import fill_header_fields
        filled = fill_header_fields(
            {"agencies_loaded": "none -- direct implementation"},
            "s1",
            store,
            "task-chunk-planner",
        )
        assert filled["agencies_loaded"] == "senior-developer"


def _activate_default_companions(store: Store) -> None:
    for slug in ("agents-orchestrator", "chief-of-staff"):
        store.activate_agent({
            "slug": slug,
            "name": slug.replace("-", " ").title(),
            "description": f"Default companion specialist {slug}",
            "division": "specialized",
            "source": "test",
        })


def test_trivial_preflight_loads_defaults_equally_for_hermes_and_openclaw():
    """Even ping should load DEFAULT companions consistently across hosts."""
    from agency_runtime.adapters.hermes.plugin import HermesAdapter
    from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        hermes_store = Store(Path(tmpdir) / "hermes.db")
        openclaw_store = Store(Path(tmpdir) / "openclaw.db")
        _activate_default_companions(hermes_store)
        _activate_default_companions(openclaw_store)

        hermes_result = HermesAdapter(store=hermes_store).build_preflight_context("s1", "ping")
        openclaw_result = OpenClawAdapter(store=openclaw_store).build_preflight_context("s1", "ping")

        assert hermes_result is not None
        assert openclaw_result is not None
        assert hermes_result["context"] == openclaw_result["context"]
        assert "agents-orchestrator, chief-of-staff" in hermes_result["context"]
        assert hermes_store.get_specialists_for_session("s1") == ["agents-orchestrator", "chief-of-staff"]
        assert openclaw_store.get_specialists_for_session("s1") == ["agents-orchestrator", "chief-of-staff"]


def test_store_delegation():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        event_id = store.record_delegation(
            trace_id="trace-1",
            recommended_agent="code-reviewer",
            status="suggested",
            backend="codex_exec",
        )
        delegations = store.get_delegations("trace-1")
        assert len(delegations) == 1
        assert delegations[0]["recommended_agent"] == "code-reviewer"


def test_store_roster_activation():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        agent = {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Reviews code for bugs and quality",
            "division": "engineering",
            "categories": ["software-development", "review"],
        }
        store.activate_agent(agent)
        roster = store.get_active_roster()
        assert len(roster) == 1
        assert roster[0]["agent_slug"] == "code-reviewer"

        catalog = store.get_active_roster_as_catalog()
        assert len(catalog) == 1
        assert catalog[0]["slug"] == "code-reviewer"


# ─── Policy profiles ────────────────────────────────────────────────


def test_local_only_profile():
    assert LOCAL_ONLY.network_enabled is False
    assert LOCAL_ONLY.auto_sync is False
    assert LOCAL_ONLY.auto_enable_new_agents is False


def test_standard_profile():
    assert STANDARD.auto_sync is False
    assert STANDARD.auto_enable_new_agents is False


def test_power_profile():
    assert POWER.network_enabled is True


def test_yolo_profile_enables_nightly_auto_sync():
    assert YOLO.network_enabled is True
    assert YOLO.auto_sync is True
    assert YOLO.auto_enable_new_agents is True
    assert YOLO.sync_schedule == "nightly"


def test_starter_roster():
    assert len(STARTER_ROSTER) >= 4
    slugs = [a["slug"] for a in STARTER_ROSTER]
    assert "code-reviewer" in slugs
    assert "senior-developer" in slugs
