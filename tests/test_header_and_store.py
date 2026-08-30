"""Tests for header contract, model receipts, and store."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency_runtime.core.header.contract import (
    fill_header_fields,
    format_header,
    parse_header,
    validate_header,
)
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.policy.profiles import LOCAL_ONLY, POWER, STANDARD, YOLO
from agency_runtime.core.receipts.normalize import (
    build_unavailable_receipt,
    normalize_litellm_receipt,
)
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_KERNEL
from agency_runtime.core.store.sqlite import Store

# ─── Header contract ────────────────────────────────────────────────


SAMPLE_HEADER = """Agency/Agencies loaded: code-reviewer
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: task-general -> openai/gpt-5.5
Recruited via: inference
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


def test_partial_header_never_discards_answer_lines(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="partial",
        session_id="partial",
        metadata={"request_kind": "trivial"},
    )
    draft = "\n".join(
        [
            "Agency/Agencies loaded: code-reviewer",
            "First answer line",
            "Second answer line",
            "Third answer line",
            "Fourth answer line",
            "Fifth answer line",
            "Sixth answer line",
        ]
    )

    result = finalize_response(
        draft,
        trace_metadata={"session_id": "partial", "trace_id": "partial"},
        store=store,
    )

    assert result["action"] == "accept"
    for line in draft.splitlines():
        assert line in result["text"]


def test_out_of_order_header_is_preserved_as_body(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="out-of-order",
        session_id="out-of-order",
        metadata={"request_kind": "trivial"},
    )
    draft = SAMPLE_HEADER.replace(
        "Agency/Agencies delegated: none\nSkills loaded: none",
        "Skills loaded: none\nAgency/Agencies delegated: none",
    )

    result = finalize_response(
        draft,
        trace_metadata={"session_id": "out-of-order", "trace_id": "out-of-order"},
        store=store,
    )

    assert result["action"] == "accept"
    assert draft.strip() in result["text"]


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
    assert receipt["model_id"] == "gpt-5.5"
    assert receipt["resolved_model"] == "unavailable"
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
        store.record_model_receipt(
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
        store.create_run(
            trace_id="hermes-turn",
            session_id="test-session",
            metadata={"request_kind": "nontrivial"},
        )

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
        store.create_run(
            trace_id="hermes-turn",
            session_id="test-session",
            metadata={"request_kind": "nontrivial"},
        )

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
        store.record_specialist_loaded("s1", "code-reviewer", trace_id="trace-1")
        store.record_specialist_loaded(
            "s1",
            "codebase-onboarding-engineer",
            trace_id="trace-1",
        )

        from agency_runtime.core.header.contract import fill_header_fields

        filled = fill_header_fields({}, "s1", store, "task-chunk-planner", "trace-1")
        assert filled["agencies_loaded"] == "code-reviewer, codebase-onboarding-engineer"


def test_header_replaces_loaded_none_but_rejects_unvalidated_native_worker():
    """A generic worker is not delegated Agency evidence without activation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_specialist_loaded("s1", "code-reviewer", trace_id="trace-1")
        store.record_delegation(
            trace_id="trace-1",
            session_id="s1",
            work_unit_id="unit-review",
            recommended_agent="code-reviewer",
            status="delegated",
            backend="delegate_task",
            executed_worker_kind="generic-worker",
            executed_worker_id="worker-1",
            native_run_id="native-run-1",
        )

        from agency_runtime.core.header.contract import fill_header_fields

        filled = fill_header_fields(
            {"agencies_loaded": "none", "agencies_delegated": "none"},
            "s1",
            store,
            "task-chunk-planner",
            "trace-1",
        )
        assert filled["agencies_loaded"] == "code-reviewer"
        assert (
            filled["agencies_delegated"]
            == "none - executed worker has no validated Agency specialist"
        )


def test_header_replaces_noneish_loaded_reason_when_store_has_agency_evidence():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_specialist_loaded("s1", "senior-developer", trace_id="trace-1")

        from agency_runtime.core.header.contract import fill_header_fields

        filled = fill_header_fields(
            {"agencies_loaded": "none -- direct implementation"},
            "s1",
            store,
            "task-chunk-planner",
            "trace-1",
        )
        assert filled["agencies_loaded"] == "senior-developer"


def test_control_preflight_binds_same_kernel_with_host_specific_receipts():
    """Exact control turns share a kernel without conflating host bindings."""
    from agency_runtime.adapters.hermes.plugin import HermesAdapter
    from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        hermes_store = Store(Path(tmpdir) / "hermes.db")
        openclaw_store = Store(Path(tmpdir) / "openclaw.db")

        hermes_result = HermesAdapter(store=hermes_store).build_preflight_context(
            "s1", "agency status"
        )
        openclaw_result = OpenClawAdapter(store=openclaw_store).build_preflight_context(
            "s1", "agency status"
        )

        assert hermes_result is not None
        assert openclaw_result is not None
        assert hermes_result["context"].startswith(RESIDENT_MANAGER_KERNEL)
        assert openclaw_result["context"].startswith(RESIDENT_MANAGER_KERNEL)
        assert (
            hermes_result["resident_manager_kernel_hash"]
            == openclaw_result["resident_manager_kernel_hash"]
        )
        assert hermes_result["resident_manager_binding"]["host"] == "hermes"
        assert openclaw_result["resident_manager_binding"]["host"] == "openclaw"
        assert (
            hermes_result["resident_manager_binding"]["binding_id"]
            != openclaw_result["resident_manager_binding"]["binding_id"]
        )
        assert hermes_store.get_specialists_for_session("s1") == []
        assert openclaw_store.get_specialists_for_session("s1") == []

        trace_id = hermes_result["trace_id"]
        snapshot = hermes_store.get_completion_evidence_snapshot("s1", trace_id)
        store_fields = fill_header_fields({}, "s1", hermes_store, trace_id=trace_id)
        snapshot_fields = fill_header_fields(
            {},
            "s1",
            hermes_store,
            trace_id=trace_id,
            evidence_snapshot=snapshot,
        )
        assert store_fields == snapshot_fields
        assert store_fields["agencies_loaded"] == "agency-steward"


def test_store_delegation():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "test.db")
        store.record_delegation(
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
            "slug": "custom-code-reviewer",
            "name": "Custom Code Reviewer",
            "description": "Reviews code for bugs and quality",
            "division": "engineering",
            "categories": ["software-development", "review"],
            "prompt_body": "Review code for bugs, security risks, and maintainability.",
        }
        store._activate_prevalidated_agent(agent)
        roster = store.get_active_roster()
        assert len(roster) == 1
        assert roster[0]["agent_slug"] == "custom-code-reviewer"

        catalog = store.get_active_roster_as_catalog()
        assert len(catalog) == 1
        assert catalog[0]["slug"] == "custom-code-reviewer"


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


def test_yolo_profile_does_not_claim_an_uninstalled_scheduler():
    assert YOLO.network_enabled is True
    assert YOLO.auto_sync is False
    assert YOLO.auto_enable_new_agents is True
    assert YOLO.sync_schedule is None


def test_starter_roster():
    assert len(STARTER_ROSTER) >= 4
    slugs = [a["slug"] for a in STARTER_ROSTER]
    assert "code-reviewer" in slugs
    assert "senior-developer" in slugs
