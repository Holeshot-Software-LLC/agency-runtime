from __future__ import annotations

import sqlite3
from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace

from agency_runtime.core.config import AgencyConfig, DelegationConfig, ProviderEntry
from agency_runtime.core.preflight import _resolve_preflight_routing
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent


def _key(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def test_child_routing_singleflight_cache_and_content_boundary(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    key = _key("assignment text that must not be stored")
    owner = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=key,
        budget=4,
        concurrency=2,
    )
    assert owner["status"] == "owner"
    assert (
        store.reserve_child_routing(
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            cache_key=key,
            budget=4,
            concurrency=2,
        )["status"]
        == "coalescing"
    )
    decision = {"selected_ids": ["code-reviewer"], "confidence": 0.91}
    assert store.complete_child_routing(
        cache_key=key,
        owner_token=owner["owner_token"],
        decision=decision,
        ttl_seconds=900,
    )
    cached = store.reserve_child_routing(
        parent_session_id="another-session",
        parent_trace_id="another-trace",
        cache_key=key,
        budget=4,
        concurrency=2,
    )
    assert cached == {"status": "cached", "decision": decision}
    assert b"assignment text that must not be stored" not in (tmp_path / "agency.db").read_bytes()


def test_child_routing_parent_budget_and_concurrency_are_shared(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    first = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=_key("one"),
        budget=2,
        concurrency=1,
    )
    assert first["status"] == "owner"
    assert (
        store.reserve_child_routing(
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            cache_key=_key("two"),
            budget=2,
            concurrency=1,
        )["status"]
        == "concurrency_exhausted"
    )
    store.abort_child_routing(cache_key=_key("one"), owner_token=first["owner_token"])
    second = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=_key("two"),
        budget=2,
        concurrency=1,
    )
    assert second["status"] == "owner"
    store.abort_child_routing(cache_key=_key("two"), owner_token=second["owner_token"])
    assert (
        store.reserve_child_routing(
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            cache_key=_key("three"),
            budget=2,
            concurrency=1,
        )["status"]
        == "budget_exhausted"
    )
    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        assert (
            connection.execute(
                "SELECT inference_calls FROM child_routing_usage WHERE parent_trace_id = ?",
                ("parent-trace",),
            ).fetchone()[0]
            == 2
        )


def test_unplanned_child_reuses_inferred_route_and_abstains_when_budget_is_zero(
    tmp_path,
) -> None:
    store = Store(tmp_path / "agency.db")
    calls = []

    class Pipeline:
        @staticmethod
        def route(session_id, message, catalog, **kwargs):
            calls.append((session_id, message, catalog, kwargs["config"]))
            return {
                "selected_ids": ["code-reviewer"],
                "semantic_ids": ["code-reviewer"],
                "companion_ids": [],
                "confidence": 0.9,
                "latency_ms": 5,
                "status": "selected",
                "source": "inference",
                "work_units": [],
            }

    config = AgencyConfig(
        providers=(ProviderEntry(name="codex", type="cli", transport="codex", model="gpt-cheap"),),
        delegation=DelegationConfig(child_inference_budget=1),
    )
    classification = classify_turn_intent(
        "Review this patch",
        TurnState(state_known=True, state_status="ready"),
    )
    arguments = {
        "store": store,
        "session_id": "child-one",
        "trace_id": "child-trace-one",
        "user_message": "Review this patch",
        "host": "codex",
        "platform": "windows",
        "available_tools": (),
        "capability_receipt": SimpleNamespace(),
        "catalog": [],
        "config": config,
        "classification": classification,
        "routing_fingerprint": "routing-fingerprint",
        "policy_fingerprint": "policy-fingerprint",
        "roster_generation": 1,
        "pipeline": Pipeline,
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
    }
    first, _, _ = _resolve_preflight_routing(**arguments)
    assert first["selected_ids"] == ["code-reviewer"]
    arguments.update(session_id="child-two", trace_id="child-trace-two")
    cached, _, _ = _resolve_preflight_routing(**arguments)
    assert cached["selected_ids"] == ["code-reviewer"]
    assert cached["child_routing_source"] == "shared_cache"
    assert len(calls) == 1

    zero_config = AgencyConfig(
        providers=config.providers,
        delegation=DelegationConfig(child_inference_budget=0),
    )
    arguments.update(
        user_message="Audit a different change",
        trace_id="child-trace-three",
        config=zero_config,
    )
    abstained, _, _ = _resolve_preflight_routing(**arguments)
    assert abstained["selected_ids"] == []
    assert abstained["deterministic_candidate_ids"] == ["code-reviewer"]
    assert abstained["status"] == "child_budget_abstained"
