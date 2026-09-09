"""AR-427: preflight must not silently remove a verified team's fifth worker."""

from copy import deepcopy

import pytest

from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.selector import pipeline
from agency_runtime.core.store.sqlite import Store
from tests.test_preflight_bounds import _test_specialist_routing


def _fixture(tmp_path, monkeypatch, *, large=False):
    store = Store(tmp_path / "agency.db")
    slugs = [f"team-worker-{i}" for i in range(5)]
    bodies = {}
    for slug in slugs:
        body = f"Exact instructions for {slug}.\n" * (90 if large else 1)
        bodies[slug] = body
        store._activate_prevalidated_agent(
            {
                "slug": slug,
                "name": slug,
                "description": "Bounded review.",
                "prompt_body": body,
                "version": "1.0.0",
            }
        )

    def route(_session, message, *_args, **kwargs):
        rows = [
            _test_specialist_routing(f"{message} Part {i}.", kwargs["trace_id"], slug)
            for i, slug in enumerate(slugs)
        ]
        value = deepcopy(rows[0])
        value["selected_ids"] = slugs
        value["workforce_unit_bindings"] = [row["workforce_unit_bindings"][0] for row in rows]
        value["workforce_unit_descriptors"] = [
            {**row["workforce_unit_descriptors"][0], "ordinal": i + 1} for i, row in enumerate(rows)
        ]
        value["unit_assignment_agents"] = [row["unit_assignment_agents"][0] for row in rows]
        value["work_units"]["units"] = [row["work_units"]["units"][0] for row in rows]
        value["work_units"]["count"] = len(rows)
        return value

    monkeypatch.setattr(pipeline, "route", route)
    return store, bodies


@pytest.mark.parametrize("host", ["codex", "claude", "openclaw", "hermes", "zcode"])
def test_every_host_preserves_the_fifth_selected_worker(tmp_path, monkeypatch, host):
    store, bodies = _fixture(tmp_path, monkeypatch)
    result = run_preflight(
        store,
        session_id="team-session",
        trace_id="team-turn",
        user_message="Review the supplied implementation for correctness.",
        host=host,
    )
    assert list(result.selected_specialists) == list(bodies)
    assert store.get_specialists_for_trace("team-session", "team-turn") == list(bodies)
    assert all(body in result.context for body in bodies.values())


@pytest.mark.parametrize("host", ["claude", "hermes"])
def test_native_retrieval_preserves_five_exact_selected_references(tmp_path, monkeypatch, host):
    store, bodies = _fixture(tmp_path, monkeypatch, large=True)
    if host == "claude":
        from agency_runtime.adapters.hooks import HookBridge

        HookBridge(host, store=store).handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "team-session",
                "prompt": "Review the supplied implementation for correctness.",
            }
        )
    else:
        from agency_runtime.adapters.hermes.bridge import handle
        from agency_runtime.adapters.hermes.plugin import HermesAdapter

        handle(
            {
                "action": "pre_llm_call",
                "session_id": "team-session",
                "trace_id": "team-turn",
                "user_message": "Review the supplied implementation for correctness.",
            },
            adapter=HermesAdapter(store),
        )
    [trace] = store.get_open_traces_for_session("team-session")
    snapshot = store.get_completion_evidence_snapshot("team-session", trace)
    assert {row["slug"] for row in snapshot["selected_specialists"]} == set(bodies)
    assert store.get_specialists_for_trace("team-session", trace) == []


@pytest.mark.parametrize("fault", ["missing", "reference_limit", "context_limit"])
def test_incomplete_team_fails_before_any_load_is_recorded(tmp_path, fault):
    from agency_runtime.core.specialist_context import hydrate_selected_specialist_context

    store = Store(tmp_path / "agency.db")
    count = 17 if fault == "reference_limit" else 5
    catalog = []
    for i in range(count):
        slug = f"bounded-worker-{i}"
        card = {
            "slug": slug,
            "name": slug,
            "description": "Bounded review.",
            "prompt_body": "Exact bounded instructions.\n",
            "version": "1.0.0",
        }
        store._activate_prevalidated_agent(card)
        catalog.append(card)
    selected = [card["slug"] for card in catalog]
    if fault == "missing":
        selected.append("missing-worker")
    with pytest.raises(RuntimeError, match="team cannot be delivered completely"):
        hydrate_selected_specialist_context(
            store,
            catalog,
            {"selected_ids": selected},
            session_id="bounded-session",
            trace_id="bounded-turn",
            require_complete=True,
            maximum_chars=1 if fault == "context_limit" else 24_000,
        )
    assert store.get_specialists_for_trace("bounded-session", "bounded-turn") == []
