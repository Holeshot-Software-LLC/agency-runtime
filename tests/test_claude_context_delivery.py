"""Exercise the native hook ceiling and exact selected-card retrieval together."""

from __future__ import annotations

from copy import deepcopy

import pytest

from agency_runtime.adapters.hooks import HookBridge, HookInputError
from agency_runtime.core.claude_context_delivery import mcp_context_enabled, utf16_units
from agency_runtime.core.header.contract import fill_header_fields
from agency_runtime.core.selector import pipeline
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import handle_tool_call
from tests.test_preflight_bounds import _test_specialist_routing


def _turn(tmp_path, monkeypatch, *, count=4, host="claude"):
    store = Store(tmp_path / "agency.db")
    bodies = {}
    for i in range(count):
        slug = f"context-reviewer-{i}"
        body = f"  Exact specialist {i}.\n" + ("Review only the supplied function.\n" * 78) + "  \n"
        bodies[slug] = body
        store._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": slug,
                "description": "Reviews the supplied code.",
                "prompt_body": body,
                "version": "1.0.0",
            }
        )

    def route(_session, message, *_args, **kwargs):
        value = _test_specialist_routing(message, kwargs["trace_id"], next(iter(bodies)))
        value["selected_ids"] = list(bodies)
        value["workforce_unit_bindings"][0]["selected"] = list(bodies)
        template = value["unit_assignment_agents"][0]
        value["unit_assignment_agents"] = [
            {
                **deepcopy(template),
                "slug": slug,
                "name": slug,
                "primary_work_unit_ids": template["primary_work_unit_ids"] if i == 0 else [],
            }
            for i, slug in enumerate(bodies)
        ]
        return value

    monkeypatch.setattr(pipeline, "route", route)
    if host == "hermes":
        from agency_runtime.adapters.hermes.bridge import handle
        from agency_runtime.adapters.hermes.plugin import HermesAdapter

        result = handle(
            {
                "action": "pre_llm_call",
                "session_id": "context-session",
                "trace_id": "context-turn",
                "user_message": "Review the supplied Python average function for correctness.",
            },
            adapter=HermesAdapter(store),
        )
        return store, "context-turn", bodies, result["context"]
    bridge = HookBridge(host, store=store)
    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "context-session",
            "prompt": "Review the supplied Python average function for correctness.",
        }
    )
    [trace] = store.get_open_traces_for_session("context-session")
    return store, trace, bodies, result["hookSpecificOutput"]["additionalContext"]


def test_four_full_cards_cross_the_native_hook_boundary_without_file_reads(tmp_path, monkeypatch):
    store, trace, bodies, context = _turn(tmp_path, monkeypatch)

    assert sum(utf16_units(body) for body in bodies.values()) > 10_000
    assert utf16_units(context) <= 10_000
    assert "agency.load_specialist" in context
    assert "read files" in context
    assert store.get_specialists_for_trace("context-session", trace) == []
    before = fill_header_fields({}, "context-session", store, trace_id=trace)
    assert before["agencies_loaded"] == "agency-steward"
    selected = store.get_completion_evidence_snapshot("context-session", trace)[
        "selected_specialists"
    ]
    assert {row["slug"] for row in selected} == set(bodies)
    for slug, body in bodies.items():
        assert body not in context
        loaded = handle_tool_call(
            "agency.load_specialist",
            {"slug": slug, "session_id": "context-session", "trace_id": trace},
            store=store,
        )
        assert loaded["prompt"] == body
        assert loaded["prompt_truncated"] is False
    assert set(store.get_specialists_for_trace("context-session", trace)) == set(bodies)
    after = fill_header_fields({}, "context-session", store, trace_id=trace)
    assert all(slug in after["agencies_loaded"] for slug in bodies)


def test_retrieval_uses_the_selected_version_after_roster_refresh(tmp_path, monkeypatch):
    store, trace, bodies, _context = _turn(tmp_path, monkeypatch)
    slug = next(iter(bodies))
    reference = next(
        row
        for row in store.get_completion_evidence_snapshot("context-session", trace)[
            "selected_specialists"
        ]
        if row["slug"] == slug
    )
    store._activate_prevalidated_agent(
        {
            "slug": slug,
            "name": slug,
            "description": "New active revision.",
            "prompt_body": "Different current card.",
            "version": "2.0.0",
        }
    )
    loaded = handle_tool_call(
        "agency.load_specialist",
        {"slug": slug, "session_id": "context-session", "trace_id": trace},
        store=store,
    )
    assert loaded["prompt"] == bodies[slug]
    assert loaded["version"] == reference["version"]
    assert loaded["prompt_hash"] == reference["hash"]


@pytest.mark.parametrize("fault", ["unselected", "other_session", "missing_version", "terminal"])
def test_retrieval_does_not_invent_selection_or_reopen_a_turn(tmp_path, monkeypatch, fault):
    store, trace, bodies, _context = _turn(tmp_path, monkeypatch)
    args = {"slug": next(iter(bodies)), "session_id": "context-session", "trace_id": trace}
    if fault == "unselected":
        args["slug"] = "code-reviewer"
    elif fault == "other_session":
        args["session_id"] = "other-session"
    elif fault == "missing_version":
        with store._connect() as connection:
            connection.execute("DELETE FROM agent_versions WHERE agent_slug = ?", (args["slug"],))
    else:
        store.close_turn_evidence("context-session", trace, status="completed")
    result = handle_tool_call("agency.load_specialist", args, store=store)
    assert "error" in result
    assert store.get_specialists_for_trace("context-session", trace) == []


def test_other_hosts_keep_inline_delivery(tmp_path, monkeypatch):
    store, trace, bodies, context = _turn(tmp_path, monkeypatch, host="zcode")
    assert all(body in context for body in bodies.values())
    assert set(store.get_specialists_for_trace("context-session", trace)) == set(bodies)


@pytest.mark.parametrize("value", ["true", 1, None])
def test_malformed_delivery_flag_is_rejected(value):
    with pytest.raises(ValueError):
        mcp_context_enabled(
            {"host": "claude", "recipe_version": 16, "specialist_context_via_mcp": value}
        )


def test_native_limit_counts_astral_characters_twice():
    assert utf16_units("x" * 9_999 + "🙂") == 10_001


def test_oversized_native_envelope_fails_without_accepting_the_turn(tmp_path, monkeypatch):
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("claude", store=store)
    monkeypatch.setattr(
        bridge.adapter, "pre_llm_call_handler", lambda **_kwargs: {"context": "🙂" * 5_001}
    )
    with pytest.raises(HookInputError, match="native inline ceiling"):
        bridge.handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "oversized",
                "turn_id": "oversized-turn",
                "prompt": "Review the supplied code.",
            }
        )
    assert store.get_run("oversized-turn")["status"] == "failed"
    assert store.get_authoritative_finalization("oversized", "oversized-turn") is None
