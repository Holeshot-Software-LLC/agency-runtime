from __future__ import annotations

import sqlite3
from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace

import pytest

from agency_runtime.core.config import AgencyConfig, DelegationConfig, ProviderEntry
from agency_runtime.core.preflight import (
    _assignment_recipe,
    _child_route_timeout,
    _normalize_parent_correlation,
    _resolve_preflight_routing,
)
from agency_runtime.core.preflight_recipe import _content_free_routing_recipe
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.judge import _scored_selection, _token_only_fallback
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
                "work_units": detect_work_units(message),
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


def test_child_store_rejects_invalid_keys_limits_and_documents(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    valid = _key("valid")
    common = {
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "cache_key": valid,
        "budget": 1,
        "concurrency": 1,
    }
    for invalid in ("short", "g" * 64):
        with pytest.raises(ValueError, match="SHA-256"):
            store.reserve_child_routing(**{**common, "cache_key": invalid})
    for budget in (True, -1, 257):
        with pytest.raises(ValueError, match="budget"):
            store.reserve_child_routing(**{**common, "budget": budget})
    for concurrency in (True, 0, 33):
        with pytest.raises(ValueError, match="concurrency"):
            store.reserve_child_routing(**{**common, "concurrency": concurrency})

    owner = store.reserve_child_routing(**common)
    with pytest.raises(ValueError, match="cache limit"):
        store.complete_child_routing(
            cache_key=valid,
            owner_token=owner["owner_token"],
            decision={"large": "x" * 300_000},
            ttl_seconds=1,
        )
    assert not store.complete_child_routing(
        cache_key=valid,
        owner_token="wrong-token",
        decision={},
        ttl_seconds=1,
    )
    assert store.complete_child_routing(
        cache_key=valid,
        owner_token=owner["owner_token"],
        decision={},
        ttl_seconds=0,
    )
    assert store.read_child_routing_cache(valid) == {}


def test_zero_ttl_still_shares_the_completed_singleflight_result(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    key = _key("zero-ttl-coalescing")
    owner = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=key,
        budget=1,
        concurrency=1,
    )

    decision = {"selected_ids": ["code-reviewer"]}
    assert store.complete_child_routing(
        cache_key=key,
        owner_token=owner["owner_token"],
        decision=decision,
        ttl_seconds=0,
    )
    assert store.read_child_routing_cache(key) == decision


@pytest.mark.parametrize("document", ["not-json", "[]"])
def test_child_store_recovers_from_unusable_cached_documents(tmp_path, document) -> None:
    store = Store(tmp_path / "agency.db")
    key = _key(document)
    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        connection.execute(
            "INSERT INTO child_routing_cache (cache_key, decision, expires_at, created_at) "
            "VALUES (?, ?, ?, '2026-07-21T00:00:00Z')",
            (key, document, 4_102_444_800.0),
        )
        connection.commit()
    assert store.read_child_routing_cache(key) is None
    reserved = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=key,
        budget=1,
        concurrency=1,
    )
    assert reserved["status"] == "owner"


def test_child_store_updates_existing_cache_and_bounds_long_ttl(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    key = _key("upsert")
    owner = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=key,
        budget=2,
        concurrency=1,
    )
    assert store.complete_child_routing(
        cache_key=key,
        owner_token=owner["owner_token"],
        decision={"version": 1},
        ttl_seconds=90_000,
    )
    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        connection.execute(
            "INSERT INTO child_routing_leases "
            "(cache_key, parent_trace_id, owner_token, expires_at, created_at) "
            "VALUES (?, 'parent-trace', 'replacement-token', ?, '2026-07-21T00:00:00Z')",
            (key, 4_102_444_800.0),
        )
        connection.commit()
    assert store.complete_child_routing(
        cache_key=key,
        owner_token="replacement-token",
        decision={"version": 2},
        ttl_seconds=60,
    )
    assert store.read_child_routing_cache(key) == {"version": 2}


def test_parent_correlation_timeout_and_score_boundaries() -> None:
    assert _normalize_parent_correlation("", "") == ("", "")
    assert _normalize_parent_correlation("parent-session", "parent-trace") == (
        "parent-session",
        "parent-trace",
    )
    with pytest.raises(ValueError, match="supplied together"):
        _normalize_parent_correlation("parent-session", "")

    config = AgencyConfig(
        providers=(ProviderEntry(name="slow", timeout=90),),
    )
    assert _child_route_timeout(config) == 60.0
    assert _scored_selection([], [], 2) == []
    fallback = _token_only_fallback(
        [{"slug": "semantic"}, {"slug": "weak-lexical"}],
        [9.0, 1.0],
        2,
        9.0,
        2,
        lexical_ids=("weak-lexical",),
    )
    assert fallback["selected_ids"] == []
    assert fallback["status"] == "abstained"


def test_child_coalescing_waits_for_cache_and_uses_longest_timeout(monkeypatch) -> None:
    reads = iter(
        (
            None,
            {
                "selected_ids": ["code-reviewer"],
                "work_units": _content_free_routing_recipe(
                    {"work_units": detect_work_units("Review this patch")},
                    trace_id="owner-trace",
                )["work_units"],
            },
        )
    )
    reservation = {}

    class SharedStore:
        def reserve_child_routing(self, **kwargs):
            reservation.update(kwargs)
            return {"status": "coalescing"}

        def read_child_routing_cache(self, _key):
            return next(reads)

    class Pipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            raise AssertionError("coalesced route must not run inference")

    monkeypatch.setattr("agency_runtime.core.preflight.time.sleep", lambda _seconds: None)
    config = AgencyConfig(
        providers=(ProviderEntry(name="slow", type="cli", transport="codex", timeout=40),),
    )
    classification = classify_turn_intent(
        "Review this patch",
        TurnState(state_known=True, state_status="ready"),
    )
    routing, _, _ = _resolve_preflight_routing(
        SharedStore(),
        session_id="child",
        trace_id="child-trace",
        user_message="Review this patch",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
        catalog=[],
        config=config,
        classification=classification,
        routing_fingerprint="routing",
        policy_fingerprint="policy",
        roster_generation=1,
        pipeline=Pipeline,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
    )
    assert routing["status"] == "child_cache_reused"
    assert reservation["lease_seconds"] == 45.0


def test_cached_multi_unit_child_route_restores_units_from_the_same_message() -> None:
    message = "1. Review the implementation\n2. Audit the security controls"
    source = {
        "selected_ids": ["code-reviewer"],
        "semantic_ids": ["code-reviewer"],
        "companion_ids": [],
        "confidence": 0.9,
        "latency_ms": 5,
        "status": "selected",
        "source": "inference",
        "work_units": detect_work_units(message),
    }
    decision = _content_free_routing_recipe(source, trace_id="owner-trace")

    class SharedStore:
        @staticmethod
        def reserve_child_routing(**_kwargs):
            return {"status": "cached", "decision": decision}

    classification = classify_turn_intent(
        message,
        TurnState(state_known=True, state_status="ready"),
    )
    routing, _, _ = _resolve_preflight_routing(
        SharedStore(),
        session_id="child",
        trace_id="child-trace",
        user_message=message,
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
        catalog=[],
        config=AgencyConfig(
            providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
        ),
        classification=classification,
        routing_fingerprint="routing",
        policy_fingerprint="policy",
        roster_generation=1,
        pipeline=SimpleNamespace(),
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
    )

    assert routing["status"] == "child_cache_reused"
    assert routing["work_units"]["units"] == source["work_units"]["units"]


def test_child_coalescing_timeout_abstains_without_duplicate_inference(monkeypatch) -> None:
    class SharedStore:
        @staticmethod
        def reserve_child_routing(**_kwargs):
            return {"status": "coalescing"}

        @staticmethod
        def read_child_routing_cache(_key):
            return None

    class DeterministicPipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            return {"selected_ids": ["code-reviewer"]}

    clocks = iter((0.0, 0.0, 21.0))
    monkeypatch.setattr("agency_runtime.core.preflight.time.monotonic", lambda: next(clocks))
    monkeypatch.setattr("agency_runtime.core.preflight.time.sleep", lambda _seconds: None)
    classification = classify_turn_intent(
        "Review this patch",
        TurnState(state_known=True, state_status="ready"),
    )
    routing, _, _ = _resolve_preflight_routing(
        SharedStore(),
        session_id="child",
        trace_id="child-trace",
        user_message="Review this patch",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
        catalog=[],
        config=AgencyConfig(
            providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
        ),
        classification=classification,
        routing_fingerprint="routing",
        policy_fingerprint="policy",
        roster_generation=1,
        pipeline=DeterministicPipeline,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
    )
    assert routing["status"] == "child_budget_abstained"
    assert routing["child_routing_source"] == "coalescing"
    assert routing["selected_ids"] == []
    assert routing["deterministic_candidate_ids"] == ["code-reviewer"]


def test_child_owner_failure_aborts_and_unconfigured_child_is_deterministic() -> None:
    aborted = []

    class OwnerStore:
        def reserve_child_routing(self, **_kwargs):
            return {"status": "owner", "owner_token": "owner-token"}

        def abort_child_routing(self, **kwargs):
            aborted.append(kwargs)

    class FailingPipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            raise RuntimeError("provider failed")

    classification = classify_turn_intent(
        "Review this patch",
        TurnState(state_known=True, state_status="ready"),
    )
    configured = AgencyConfig(
        providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
    )
    with pytest.raises(RuntimeError, match="provider failed"):
        _resolve_preflight_routing(
            OwnerStore(),
            session_id="child",
            trace_id="child-trace",
            user_message="Review this patch",
            host="codex",
            platform="windows",
            available_tools=(),
            capability_receipt=SimpleNamespace(),
            catalog=[],
            config=configured,
            classification=classification,
            routing_fingerprint="routing",
            policy_fingerprint="policy",
            roster_generation=1,
            pipeline=FailingPipeline,
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
        )
    assert aborted and aborted[0]["owner_token"] == "owner-token"

    class DeterministicPipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            return {"selected_ids": ["code-reviewer"]}

    routing, _, _ = _resolve_preflight_routing(
        SimpleNamespace(),
        session_id="child",
        trace_id="child-trace",
        user_message="Review this patch",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
        catalog=[],
        config=AgencyConfig(providers=()),
        classification=classification,
        routing_fingerprint="routing",
        policy_fingerprint="policy",
        roster_generation=1,
        pipeline=DeterministicPipeline,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
    )
    assert routing["child_routing_source"] == "deterministic_unconfigured"


def test_budget_abstention_never_runs_exact_unit_routing() -> None:
    agents, plan = _assignment_recipe(
        [],
        {"status": "child_budget_abstained", "work_units": {"delegate": True}},
        None,
        AgencyConfig(),
        session_id="child",
        trace_id="child-trace",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
    )
    assert agents == []
    assert plan == []
