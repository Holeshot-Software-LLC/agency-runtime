from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from agency_runtime.core.config import AgencyConfig, DelegationConfig, ProviderEntry
from agency_runtime.core.preflight import (
    _activate_direct_native_child,
    _assignment_recipe,
    _child_route_timeout,
    _normalize_parent_correlation,
    _prepare_preflight_evidence,
    _publish_child_routing_bundle,
    _resolve_preflight_routing,
)
from agency_runtime.core.preflight_recipe import (
    PreflightResult,
    _content_free_routing_recipe,
    preflight_delivery_policy,
)
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.judge import _scored_selection, _token_only_fallback
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent
from agency_runtime.core.unit_assignment import build_unit_agent_plan, work_unit_id_from_text
from agency_runtime.core.workforce.routing_projection import (
    workforce_work_units_from_descriptors,
)


def _key(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _ready_parent(
    store: Store,
    *,
    session_id: str = "parent-session",
    trace_id: str = "parent-trace",
    host: str = "codex",
) -> None:
    connection = store._connect()
    try:
        connection.execute(
            "INSERT INTO runs "
            "(id, trace_id, session_id, host, started_at, status, user_message, "
            "metadata, preflight_state, preflight_result) "
            "VALUES (?, ?, ?, ?, '2026-07-26T00:00:00Z', 'active', '', '{}', "
            "'ready', '{}')",
            (f"run:{trace_id}", trace_id, session_id, host),
        )
        connection.commit()
    finally:
        connection.close()


def test_native_child_parent_scope_survives_store_process_boundary_once(tmp_path) -> None:
    path = tmp_path / "scope.db"
    issuer = Store(path)
    _ready_parent(issuer)
    issued = issuer.create_native_child_parent_scope(
        host="codex",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        work_unit_id="unit-0123456789",
        worker_kind="generic-worker",
        worker_id="agent-42",
        native_run_id="codex-agent:agent-42",
        child_session_id="codex-child:agent-42",
    )
    assert str(issued["parent_scope_token"]).encode() not in path.read_bytes()
    connection = issuer._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable or consumed"):
            connection.execute("UPDATE native_child_parent_scopes SET worker_id = 'forged-worker'")
        connection.rollback()
    finally:
        connection.close()

    consumer = Store(path)
    with pytest.raises(ValueError, match="invalid, ambiguous, or already consumed"):
        consumer.consume_native_child_parent_scope(
            parent_scope_token=str(issued["parent_scope_token"]),
            host="claude",
            child_session_id="codex-child:agent-42",
            child_trace_id="child-trace",
        )
    with pytest.raises(ValueError, match="invalid, ambiguous, or already consumed"):
        consumer.consume_native_child_parent_scope(
            parent_scope_token=str(issued["parent_scope_token"]),
            host="codex",
            child_session_id="codex-child:another-agent",
            child_trace_id="child-trace",
        )

    consumed = consumer.consume_native_child_parent_scope(
        parent_scope_token=str(issued["parent_scope_token"]),
        host="codex",
        child_session_id="codex-child:agent-42",
        child_trace_id="child-trace",
    )
    assert consumed == {
        "host": "codex",
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "work_unit_id": "unit-0123456789",
        "worker_kind": "generic-worker",
        "worker_id": "agent-42",
        "native_run_id": "codex-agent:agent-42",
        "child_session_id": "codex-child:agent-42",
        "child_trace_id": "child-trace",
    }
    with pytest.raises(ValueError, match="invalid, ambiguous, or already consumed"):
        issuer.consume_native_child_parent_scope(
            parent_scope_token=str(issued["parent_scope_token"]),
            host="codex",
            child_session_id="codex-child:agent-42",
            child_trace_id="replay-trace",
        )


def test_failed_child_preflight_restores_scope_but_success_cannot_reopen_it(tmp_path) -> None:
    store = Store(tmp_path / "scope-retry.db")
    _ready_parent(store)
    issued = store.create_native_child_parent_scope(
        host="codex",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        work_unit_id="unit-0123456789",
        worker_kind="generic-worker",
        worker_id="agent-retry",
        native_run_id="codex-agent:agent-retry",
        child_session_id="codex-child:agent-retry",
    )
    token = str(issued["parent_scope_token"])
    store.consume_native_child_parent_scope(
        parent_scope_token=token,
        host="codex",
        child_session_id="codex-child:agent-retry",
        child_trace_id="failed-child-trace",
    )
    store.restore_native_child_parent_scope_after_failed_preflight(
        parent_scope_token=token,
        host="codex",
        child_session_id="codex-child:agent-retry",
        child_trace_id="failed-child-trace",
    )
    store.consume_native_child_parent_scope(
        parent_scope_token=token,
        host="codex",
        child_session_id="codex-child:agent-retry",
        child_trace_id="successful-child-trace",
    )
    _ready_parent(
        store,
        session_id="codex-child:agent-retry",
        trace_id="successful-child-trace",
    )

    with pytest.raises(ValueError, match=r"successful.*cannot be retried"):
        store.restore_native_child_parent_scope_after_failed_preflight(
            parent_scope_token=token,
            host="codex",
            child_session_id="codex-child:agent-retry",
            child_trace_id="successful-child-trace",
        )


def test_native_child_parent_scope_ambiguity_and_timeout_fail_closed(tmp_path) -> None:
    store = Store(tmp_path / "scope-guards.db")
    _ready_parent(store, trace_id="parent-trace-a")
    _ready_parent(store, trace_id="parent-trace-b")
    first = store.create_native_child_parent_scope(
        host="claude",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace-a",
        work_unit_id="",
        worker_kind="generic-worker",
        worker_id="agent-a",
        native_run_id="claude-agent:agent-a",
        child_session_id="claude-child:shared",
        ttl_seconds=1,
    )
    store.create_native_child_parent_scope(
        host="claude",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace-b",
        work_unit_id="",
        worker_kind="generic-worker",
        worker_id="agent-b",
        native_run_id="claude-agent:agent-b",
        child_session_id="claude-child:shared",
        ttl_seconds=1,
    )
    with pytest.raises(ValueError, match="ambiguous"):
        store.consume_native_child_parent_scope(
            parent_scope_token=str(first["parent_scope_token"]),
            host="claude",
            child_session_id="claude-child:shared",
            child_trace_id="child-trace",
        )

    time.sleep(2.0)
    _ready_parent(store, trace_id="parent-trace-c")
    current = store.create_native_child_parent_scope(
        host="claude",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace-c",
        work_unit_id="",
        worker_kind="generic-worker",
        worker_id="agent-c",
        native_run_id="claude-agent:agent-c",
        child_session_id="claude-child:shared",
    )
    assert (
        store.consume_native_child_parent_scope(
            parent_scope_token=str(current["parent_scope_token"]),
            host="claude",
            child_session_id="claude-child:shared",
            child_trace_id="current-child-trace",
        )["parent_trace_id"]
        == "parent-trace-c"
    )

    _ready_parent(store, trace_id="parent-trace-expiring")
    expiring = store.create_native_child_parent_scope(
        host="codex",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace-expiring",
        work_unit_id="",
        worker_kind="generic-worker",
        worker_id="agent-expiring",
        native_run_id="codex-agent:agent-expiring",
        child_session_id="codex-child:agent-expiring",
        ttl_seconds=1,
    )
    time.sleep(2.0)
    with pytest.raises(ValueError, match="expired"):
        store.consume_native_child_parent_scope(
            parent_scope_token=str(expiring["parent_scope_token"]),
            host="codex",
            child_session_id="codex-child:agent-expiring",
            child_trace_id="child-trace",
        )


def _planned_parent_unit_fixture() -> tuple[str, list[dict], dict]:
    request = "Review and refactor this Python code for security and correctness"
    goal = workforce_work_units_from_descriptors(
        request,
        [
            {
                "ordinal": 1,
                "artifact_kind": "implementation-change",
                "lifecycle_phase": "implementation",
                "authority": "modify",
            }
        ],
    )[0]
    work_unit_id = work_unit_id_from_text(goal)
    catalog = [
        {
            "slug": "python-application-engineer",
            "name": "Python Application Engineer",
            "description": "Implements secure Python application changes.",
            "capabilities": ["python-application-development"],
            "tags": ["python", "implementation"],
            "categories": ["engineering"],
            "required_tools": [],
            "evidence_requirements": ["targeted-tests"],
            "version": "revision-1",
            "hash": "a" * 64,
        }
    ]
    routing = {
        "selected_ids": ["python-application-engineer"],
        "work_units": {
            "delegate": True,
            "count": 1,
            "confidence": "high",
            "source": "test",
            "units": [goal],
        },
        "unit_assignment_agents": [
            {
                **catalog[0],
                "matched_work_unit_ids": [work_unit_id],
                "primary_work_unit_ids": [work_unit_id],
            }
        ],
    }
    plan = build_unit_agent_plan(routing)
    assert len(plan) == 1
    snapshot = {
        "session_id": "parent-session",
        "trace_id": "parent-trace",
        "status": "active",
        "delivery_mode": "isolated",
        "run": {"host": "codex"},
        "unit_agent_plan": plan,
        "selected_specialists": [
            {
                "slug": catalog[0]["slug"],
                "version": catalog[0]["version"],
                "hash": catalog[0]["hash"],
            }
        ],
    }
    return goal, catalog, snapshot


def test_persistent_native_parents_are_isolated_and_child_hooks_deliver_directly() -> None:
    for host in ("openclaw", "hermes"):
        assert preflight_delivery_policy(host)[0] == "isolated"
        assert preflight_delivery_policy(host, native_child=True)[0] == "direct"
    for host in ("codex", "claude"):
        assert preflight_delivery_policy(host, native_child=True)[0] == "isolated"


def test_direct_native_child_abstains_without_lineage_or_an_exact_parent_unit() -> None:
    base = PreflightResult(
        session_id="child-session",
        trace_id="child-trace",
        routing={"source": "parent_unit_reuse", "status": "parent_unit_reused"},
        context="context",
        loaded_specialists=("code-reviewer",),
        selected_specialists=("code-reviewer",),
        trivial=False,
        roster_size=1,
        delegation_plan=(
            {
                "work_unit_id": "unit-a",
                "goal_hash": _key("Review this patch"),
                "recommended_agent": "code-reviewer",
                "recommended_agents": ["code-reviewer"],
            },
        ),
    )
    with pytest.raises(RuntimeError, match="lacks host-issued child lineage"):
        _activate_direct_native_child(
            SimpleNamespace(),
            base,
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            user_message="Review this patch",
            host="openclaw",
            worker_id="",
            native_run_id="",
        )
    unplanned = replace(base, routing={"source": "inference", "status": "selected"})
    with pytest.raises(RuntimeError, match="requires one exact parent plan row"):
        _activate_direct_native_child(
            SimpleNamespace(),
            unplanned,
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            user_message="Review this patch",
            host="hermes",
            worker_id="worker",
            native_run_id="hermes-subagent:worker",
        )


def test_child_routing_singleflight_cache_and_content_boundary(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    assert store.read_child_routing_cache(_key("missing")) is None
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
        "capability_receipt": SimpleNamespace(as_dict=lambda: {}),
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
    _publish_child_routing_bundle(
        store,
        first,
        trace_id="child-trace-one",
        unit_assignment_agents=[],
        suggestions=[],
        ttl_seconds=config.delegation.child_cache_ttl_seconds,
    )
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


def test_exact_planned_parent_unit_reuses_assignment_without_child_inference() -> None:
    goal, catalog, snapshot = _planned_parent_unit_fixture()
    snapshot_reads: list[tuple[str, str]] = []

    class ParentStore:
        @staticmethod
        def get_completion_evidence_snapshot(session_id, trace_id):
            snapshot_reads.append((session_id, trace_id))
            return snapshot

        @staticmethod
        def reserve_child_routing(**_kwargs):
            raise AssertionError("an exact parent unit must not reserve child inference")

    class Pipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            raise AssertionError("an exact parent unit must not rerun selection")

    classification = classify_turn_intent(
        goal,
        TurnState(state_known=True, state_status="ready"),
    )
    routing, continuation, returned_classification = _resolve_preflight_routing(
        ParentStore(),
        session_id="child-session",
        trace_id="child-trace",
        user_message=goal,
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(as_dict=lambda: {"status": "verified"}),
        catalog=catalog,
        config=AgencyConfig(
            providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
        ),
        classification=classification,
        routing_fingerprint="routing-fingerprint",
        policy_fingerprint="policy-fingerprint",
        roster_generation=1,
        pipeline=Pipeline,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
    )

    assert snapshot_reads == [("parent-session", "parent-trace")]
    assert continuation is None
    assert returned_classification == classification
    assert routing["status"] == "parent_unit_reused"
    assert routing["source"] == "parent_unit_reuse"
    assert routing["parent_unit_reused"] is True
    assert routing["inference_attempted"] is False
    assert routing["selected_ids"] == ["python-application-engineer"]
    assert routing["_cached_unit_agent_plan"] == snapshot["unit_agent_plan"]
    assert routing["_cached_unit_assignment_agents"][0]["slug"] == ("python-application-engineer")


@pytest.mark.parametrize(
    "case",
    [
        "wrong_goal",
        "wrong_host",
        "stale_revision",
        "multi_specialist_unit",
        "malformed_run",
    ],
)
def test_parent_unit_reuse_rejects_unbound_or_ambiguous_assignments(case) -> None:
    goal, catalog, snapshot = _planned_parent_unit_fixture()
    child_goal = goal
    if case == "wrong_goal":
        child_goal = f"{goal} Also publish the release."
    elif case == "wrong_host":
        snapshot["run"]["host"] = "claude"
    elif case == "stale_revision":
        catalog[0]["hash"] = "b" * 64
    elif case == "multi_specialist_unit":
        snapshot["unit_agent_plan"][0]["recommended_agents"] = [
            "python-application-engineer",
            "code-reviewer",
        ]
    elif case == "malformed_run":
        snapshot["run"] = "codex"

    route_calls: list[str] = []

    class ParentStore:
        @staticmethod
        def get_completion_evidence_snapshot(_session_id, _trace_id):
            return snapshot

    class Pipeline:
        @staticmethod
        def route(_session_id, message, _catalog, **_kwargs):
            route_calls.append(message)
            return {"selected_ids": [], "status": "abstained"}

    classification = classify_turn_intent(
        child_goal,
        TurnState(state_known=True, state_status="ready"),
    )
    routing, _, _ = _resolve_preflight_routing(
        ParentStore(),
        session_id="child-session",
        trace_id="child-trace",
        user_message=child_goal,
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(as_dict=lambda: {}),
        catalog=catalog,
        config=AgencyConfig(providers=()),
        classification=classification,
        routing_fingerprint="routing-fingerprint",
        policy_fingerprint="policy-fingerprint",
        roster_generation=1,
        pipeline=Pipeline,
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
    )

    assert route_calls == [child_goal]
    assert routing["child_routing_source"] == "deterministic_unconfigured"
    assert routing.get("parent_unit_reused") is not True


def test_parent_unit_cache_identity_binds_parent_policy_roster_and_workforce() -> None:
    keys: list[str] = []

    class KeyStore:
        @staticmethod
        def reserve_child_routing(**kwargs):
            keys.append(kwargs["cache_key"])
            return {
                "status": "cached",
                "decision": {
                    "selected_ids": [],
                    "work_units": _content_free_routing_recipe(
                        {"work_units": detect_work_units("Review")},
                        trace_id="source-trace",
                    )["work_units"],
                },
            }

    config = AgencyConfig(
        providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
    )
    classification = classify_turn_intent(
        "Review",
        TurnState(state_known=True, state_status="ready"),
    )
    base = {
        "store": KeyStore(),
        "session_id": "child",
        "trace_id": "child-trace",
        "user_message": "Review",
        "host": "codex",
        "platform": "windows",
        "available_tools": ("repository-read",),
        "capability_receipt": SimpleNamespace(
            surface="codex",
            inference_surface="codex-subscription",
            status="verified",
            unknown_tools=(),
            as_dict=lambda: {},
        ),
        "catalog": [],
        "config": config,
        "classification": classification,
        "routing_fingerprint": "routing-v1",
        "policy_fingerprint": "policy-v1",
        "roster_generation": 1,
        "pipeline": SimpleNamespace(),
        "workforce_snapshot": SimpleNamespace(
            contract_fingerprint="contracts-v1",
            recruiter_fingerprint="recruiter-v1",
        ),
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
    }

    _resolve_preflight_routing(**base)
    _resolve_preflight_routing(**base)
    _resolve_preflight_routing(**{**base, "parent_trace_id": "other-parent"})
    _resolve_preflight_routing(**{**base, "policy_fingerprint": "policy-v2"})
    _resolve_preflight_routing(**{**base, "roster_generation": 2})
    _resolve_preflight_routing(
        **{
            **base,
            "workforce_snapshot": SimpleNamespace(
                contract_fingerprint="contracts-v2",
                recruiter_fingerprint="recruiter-v1",
            ),
        }
    )

    assert keys[0] == keys[1]
    assert len(set(keys)) == 5
    assert all(len(key) == 64 for key in keys)


def test_cached_child_reuses_complete_multi_unit_assignment_bundle(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "agency.db")
    message = "1. Review the implementation\n2. Audit the security controls"
    route_calls: list[str] = []
    assignment_calls: list[str] = []

    class Pipeline:
        @staticmethod
        def route(_session_id, routed_message, _catalog, **_kwargs):
            route_calls.append(routed_message)
            return {
                "selected_ids": ["code-reviewer"],
                "semantic_ids": ["code-reviewer"],
                "companion_ids": [],
                "confidence": 0.9,
                "latency_ms": 5,
                "status": "selected",
                "source": "inference",
                "work_units": detect_work_units(routed_message),
            }

    assignment_agents = [{"slug": "code-reviewer", "work_unit_ids": ["unit-a"]}]
    plan = [{"work_unit_id": "unit-a", "recommended_agent": "code-reviewer"}]

    def assign(*_args, **_kwargs):
        assignment_calls.append("inference")
        return assignment_agents

    monkeypatch.setattr("agency_runtime.core.preflight.assignment_agents_from_catalog", assign)
    monkeypatch.setattr("agency_runtime.core.preflight._suggestion_recipe", lambda *_args: plan)
    config = AgencyConfig(
        providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
        delegation=DelegationConfig(child_inference_budget=1),
    )
    classification = classify_turn_intent(
        message,
        TurnState(state_known=True, state_status="ready"),
    )
    arguments = {
        "store": store,
        "session_id": "child-one",
        "trace_id": "child-trace-one",
        "user_message": message,
        "host": "codex",
        "platform": "windows",
        "available_tools": (),
        "capability_receipt": SimpleNamespace(as_dict=lambda: {}),
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
    first_agents, first_plan = _assignment_recipe(
        [],
        first,
        None,
        config,
        session_id="child-one",
        trace_id="child-trace-one",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
    )
    _publish_child_routing_bundle(
        store,
        first,
        trace_id="child-trace-one",
        unit_assignment_agents=first_agents,
        suggestions=first_plan,
        ttl_seconds=config.delegation.child_cache_ttl_seconds,
    )

    arguments.update(session_id="child-two", trace_id="child-trace-two")
    cached, _, _ = _resolve_preflight_routing(**arguments)
    cached_agents, cached_plan = _assignment_recipe(
        [],
        cached,
        None,
        config,
        session_id="child-two",
        trace_id="child-trace-two",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=SimpleNamespace(),
    )

    assert route_calls == [message]
    assert assignment_calls == ["inference"]
    assert cached_agents == first_agents == assignment_agents
    assert cached_plan == first_plan == plan


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
    for invalid, message in (
        ({"score": float("nan")}, "invalid"),
        (
            {"nested": [[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[0]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]},
            "structural",
        ),
        ({"items": [0] * 50_001}, "structural"),
    ):
        with pytest.raises(ValueError, match=message):
            store.complete_child_routing(
                cache_key=valid,
                owner_token=owner["owner_token"],
                decision=invalid,
                ttl_seconds=1,
            )
        assert store.read_child_routing_cache(valid) is None
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
        capability_receipt=SimpleNamespace(as_dict=lambda: {}),
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
    current_receipt = {"session_id": "child", "trace_id": "child-trace"}

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
        capability_receipt=SimpleNamespace(as_dict=lambda: current_receipt),
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
    assert routing["execution_context"] == current_receipt


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

    clocks = iter((0.0, 0.0, 200.0))
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


def test_failed_preflight_validation_aborts_unpublished_child_bundle(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "agency.db")
    message = "Review this patch"

    class Pipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            return {
                "selected_ids": [],
                "semantic_ids": [],
                "companion_ids": [],
                "confidence": 0.0,
                "latency_ms": 1,
                "status": "abstained",
                "source": "inference",
                "work_units": detect_work_units(message),
            }

        @staticmethod
        def build_routing_context(*_args, **_kwargs):
            return ""

    monkeypatch.setattr(
        "agency_runtime.core.preflight._recipe_revision_refs",
        lambda *_args, **_kwargs: ([], []),
    )
    monkeypatch.setattr(
        "agency_runtime.core.preflight._result_from_recipe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("replay rejected")),
    )
    config = AgencyConfig(
        providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
        delegation=DelegationConfig(child_inference_budget=1),
    )
    classification = classify_turn_intent(
        message,
        TurnState(state_known=True, state_status="ready"),
    )

    with pytest.raises(RuntimeError, match="replay rejected"):
        _prepare_preflight_evidence(
            store,
            session_id="child-session",
            trace_id="child-trace",
            user_message=message,
            host="codex",
            platform="windows",
            runtime_capabilities=SimpleNamespace(capabilities=(), as_dict=lambda: {}),
            catalog=[],
            config=config,
            classification=classification,
            routing_fingerprint="routing-fingerprint",
            policy_fingerprint="policy-fingerprint",
            roster_generation=1,
            workforce_snapshot=None,
            delivery_mode="direct",
            context_limit=4_096,
            resident_binding=SimpleNamespace(as_dict=lambda: {}),
            resident_context="",
            pipeline=Pipeline,
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
        )

    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        assert connection.execute("SELECT COUNT(*) FROM child_routing_cache").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM child_routing_leases").fetchone()[0] == 0


def test_child_routing_lease_can_be_renewed_until_complete(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    key = _key("renewable")
    owner = store.reserve_child_routing(
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        cache_key=key,
        budget=1,
        concurrency=1,
        lease_seconds=1,
    )
    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        before = connection.execute(
            "SELECT expires_at FROM child_routing_leases WHERE cache_key = ?", (key,)
        ).fetchone()[0]
    assert store.renew_child_routing(
        cache_key=key,
        owner_token=owner["owner_token"],
        lease_seconds=60,
    )
    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        after = connection.execute(
            "SELECT expires_at FROM child_routing_leases WHERE cache_key = ?", (key,)
        ).fetchone()[0]
    assert after > before
    assert store.complete_child_routing(
        cache_key=key,
        owner_token=owner["owner_token"],
        decision={"routing": {"selected_ids": []}},
        ttl_seconds=60,
    )
    assert not store.renew_child_routing(
        cache_key=key,
        owner_token=owner["owner_token"],
        lease_seconds=60,
    )


def test_child_heartbeat_start_failure_aborts_owner_lease(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "agency.db")

    class Pipeline:
        @staticmethod
        def route(*_args, **_kwargs):
            return {"selected_ids": [], "work_units": detect_work_units("Review this patch")}

    monkeypatch.setattr(
        "agency_runtime.core.preflight._start_child_route_heartbeat",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("thread unavailable")),
    )
    classification = classify_turn_intent(
        "Review this patch",
        TurnState(state_known=True, state_status="ready"),
    )
    with pytest.raises(RuntimeError, match="thread unavailable"):
        _resolve_preflight_routing(
            store,
            session_id="child-session",
            trace_id="child-trace",
            user_message="Review this patch",
            host="codex",
            platform="windows",
            available_tools=(),
            capability_receipt=SimpleNamespace(as_dict=lambda: {}),
            catalog=[],
            config=AgencyConfig(
                providers=(ProviderEntry(name="codex", type="cli", transport="codex"),),
                delegation=DelegationConfig(child_inference_budget=1),
            ),
            classification=classification,
            routing_fingerprint="routing-fingerprint",
            policy_fingerprint="policy-fingerprint",
            roster_generation=1,
            pipeline=Pipeline,
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
        )

    with closing(sqlite3.connect(tmp_path / "agency.db")) as connection:
        assert connection.execute("SELECT COUNT(*) FROM child_routing_cache").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM child_routing_leases").fetchone()[0] == 0
