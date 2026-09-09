"""Keep exact Hermes cards and truthful load evidence across native spilling."""

from __future__ import annotations

import json

import pytest

from agency_runtime.adapters.hermes.bridge import handle
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.core.header.contract import fill_header_fields
from tests.test_claude_context_delivery import _turn
from tests.test_hermes_turn_trace_payload import _generated_plugin


def test_full_cards_survive_default_hook_and_tool_spill_floors(tmp_path, monkeypatch):
    store, trace, bodies, context = _turn(tmp_path, monkeypatch, host="hermes")
    assert sum(map(len, bodies.values())) > 10_000
    assert len(context) <= 10_000
    assert "AGENCY RESPONSE CONTRACT" in context
    assert "AGENCY HERMES DELIVERY RULES" in context
    assert "agency_load_specialist" in context
    assert store.get_specialists_for_trace("context-session", trace) == []
    assert (
        fill_header_fields({}, "context-session", store, trace_id=trace)["agencies_loaded"]
        == "agency-steward"
    )
    module = _generated_plugin()
    module._remember_turn("context-session", trace)
    adapter = HermesAdapter(store)
    module._invoke = lambda action, payload: handle({"action": action, **payload}, adapter=adapter)
    for slug, body in bodies.items():
        text = module._agency_load_specialist({"slug": slug}, session_id="context-session")
        assert len(text) <= 7_000
        result = json.loads(text)
        assert result["prompt"] == body
        assert result["prompt_truncated"] is False
        assert result["trace_id"] == trace
    assert set(store.get_specialists_for_trace("context-session", trace)) == set(bodies)


@pytest.mark.parametrize(
    "fault",
    ["unselected", "other_session", "missing_trace", "terminal", "oversized", "new_version"],
)
def test_native_tool_cannot_invent_loads_or_change_selected_version(tmp_path, monkeypatch, fault):
    store, trace, bodies, _context = _turn(tmp_path, monkeypatch, host="hermes")
    slug = next(iter(bodies))
    payload = {
        "action": "load_specialist",
        "slug": slug,
        "session_id": "context-session",
        "trace_id": trace,
    }
    if fault == "unselected":
        payload["slug"] = "code-reviewer"
    elif fault == "other_session":
        payload["session_id"] = "another-session"
    elif fault == "missing_trace":
        payload["trace_id"] = ""
    elif fault == "terminal":
        store.close_turn_evidence("context-session", trace, status="response_invalid")
    elif fault == "oversized":
        original = store.get_versioned_specialist_prompt

        def oversized(*args, **kwargs):
            return {**original(*args, **kwargs), "prompt_body": "🙂" * 2_000}

        monkeypatch.setattr(store, "get_versioned_specialist_prompt", oversized)
    else:
        store._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": slug,
                "description": "New card",
                "prompt_body": "Changed body",
                "version": "2.0.0",
            }
        )
    result = handle(payload, adapter=HermesAdapter(store))
    if fault == "new_version":
        assert result["prompt"] == bodies[slug]
    else:
        assert "error" in result
        assert store.get_specialists_for_trace("context-session", trace) == []
