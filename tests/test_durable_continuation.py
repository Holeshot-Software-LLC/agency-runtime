"""Restart-safe, content-free continuation replay and invalidation contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, OllamaConfig
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.preflight_versions import PREFLIGHT_REPLAY_RECIPE_VERSION
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_origin import native_adapter_turn_origin


def _recipe(store: Store, trace_id: str) -> dict[str, Any]:
    connection = store._connect()
    try:
        raw = connection.execute(
            "SELECT preflight_result FROM runs WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()["preflight_result"]
    finally:
        connection.close()
    return json.loads(str(raw))


def _deterministic_config() -> AgencyConfig:
    """Keep persistence tests independent from machine-local inference services."""

    return AgencyConfig(ollama=OllamaConfig(enabled=False, model=""))


def _first_turn(
    path: Path,
    *,
    message: str = "Review the authentication security patch.",
    config: AgencyConfig | None = None,
):
    store = Store(path)
    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="adapter_preflight",
        session_id="durable-session",
        trace_id="turn-one",
    )
    result = run_preflight(
        store,
        session_id="durable-session",
        user_message=message,
        host="codex",
        trace_id="turn-one",
        config=config or _deterministic_config(),
        origin_receipt=origin_receipt,
    )
    assert result.selected_specialists
    return store, result


def _forbid_selector(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise AssertionError("durable continuation must not invoke semantic routing")


def _continue(
    store: Store,
    *,
    trace_id: str = "turn-two",
    host: str = "codex",
    config: AgencyConfig | None = None,
):
    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host=host,
        event="adapter_preflight",
        session_id="durable-session",
        trace_id=trace_id,
    )
    return run_preflight(
        store,
        session_id="durable-session",
        user_message="continue",
        host=host,
        trace_id=trace_id,
        config=config or _deterministic_config(),
        origin_receipt=origin_receipt,
    )


def _assert_fresh_reroute(store: Store, result: Any, trace_id: str = "turn-two") -> None:
    recipe = _recipe(store, trace_id)
    assert result.turn_kind == "continuation"
    assert result.reroute_required is True
    assert recipe["routing"]["status"] != "continuation_abstained"
    assert recipe["routing"]["continuation_reused"] is False
    assert recipe["routing"]["continuation_resolution_required"] is False
    assert "continuation_guard" not in recipe
    assert any(
        reason
        in {
            "continuation_guard_invalid",
            "continuation_guard_changed_before_commit",
            "continuation_recipe_invalid",
        }
        for reason in recipe["turn_classification"]["reason_codes"]
    )


def test_continuation_replays_after_restart_without_cache_or_judge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    first_store, first = _first_turn(path)
    first_recipe = _recipe(first_store, "turn-one")
    del first_store
    clear_cache()
    clear_session_routing()
    monkeypatch.setattr(pipeline, "route", _forbid_selector)

    restarted = Store(path)
    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host="codex",
        event="adapter_preflight",
        session_id="durable-session",
        trace_id="turn-two",
    )
    second = run_preflight(
        restarted,
        session_id="durable-session",
        user_message="continue",
        host="codex",
        trace_id="turn-two",
        config=_deterministic_config(),
        origin_receipt=origin_receipt,
    )
    second_recipe = _recipe(restarted, "turn-two")

    assert second.turn_kind == "continuation"
    assert second.continuation_of == "turn-one"
    assert second.selected_specialists == first.selected_specialists
    assert second_recipe["recipe_version"] == PREFLIGHT_REPLAY_RECIPE_VERSION
    assert second_recipe["routing"]["continuation_reused"] is True
    assert second_recipe["routing"]["routing_receipt"]["inference"] == {
        "configured": False,
        "required": False,
        "attempted": False,
        "mode": "durable_reuse",
        "provider_attempts": [],
    }
    assert len(second_recipe["routing"]["routing_receipt"]["origin_receipt_digest"]) == 64
    assert second_recipe["routing"]["origin_trace_id"] == "turn-one"
    assert second_recipe["routing"]["origin_query_hash"] == first_recipe["routing"]["query_hash"]
    assert second_recipe["routing"]["query_hash"] == hashlib.sha256(b"continue").hexdigest()
    assert second_recipe["selection_refs"] == first_recipe["selection_refs"]
    assert second_recipe["unit_agent_plan"] == first_recipe["unit_agent_plan"]
    assert "authentication security patch" not in second.context.casefold()
    connection = restarted._connect()
    try:
        persisted = "\n".join(
            str(row[0] or "")
            for row in connection.execute(
                "SELECT preflight_result FROM runs UNION ALL SELECT decision FROM routing_decisions"
            ).fetchall()
        )
        prompt_bodies = [
            str(row[0])
            for row in connection.execute("SELECT content FROM agent_versions").fetchall()
            if str(row[0] or "")
        ]
    finally:
        connection.close()
    assert "Review the authentication security patch." not in persisted
    assert all(prompt not in second.context for prompt in prompt_bodies)


@pytest.mark.parametrize("config_change", ["selector_threshold", "disabled_specialist"])
def test_roster_or_config_change_forces_fresh_routing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_change: str,
) -> None:
    path = tmp_path / "agency.db"
    store, _first = _first_turn(path)
    original = _deterministic_config()
    if config_change == "selector_threshold":
        changed = replace(
            original,
            selector=replace(
                original.selector,
                min_confidence=original.selector.min_confidence + 0.01,
            ),
        )
    else:
        selected_slug = _recipe(store, "turn-one")["selection_refs"][0]["slug"]
        changed = replace(
            original,
            agents=replace(original.agents, disabled=(selected_slug,)),
        )
    second = _continue(store, config=changed)

    _assert_fresh_reroute(store, second)


def test_ready_time_source_race_reroutes_instead_of_committing_stale_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    store, _first = _first_turn(path)
    original_mark_ready = store.mark_preflight_ready
    raced = False

    def race_source(**kwargs: Any) -> dict[str, str]:
        nonlocal raced
        if kwargs["trace_id"] == "turn-two" and not raced:
            raced = True
            connection = store._connect()
            try:
                connection.execute(
                    "UPDATE runs SET metadata = metadata WHERE trace_id = 'turn-one'"
                )
                connection.commit()
            finally:
                connection.close()
        return original_mark_ready(**kwargs)

    monkeypatch.setattr(store, "mark_preflight_ready", race_source)
    second = _continue(store)

    assert raced
    _assert_fresh_reroute(store, second)
    assert store.get_delegations("turn-two") == []


@pytest.mark.parametrize("invalidator", ["legacy_v9", "roster_generation", "wrong_host"])
def test_invalid_source_components_use_bounded_fresh_routing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalidator: str,
) -> None:
    store, _first = _first_turn(tmp_path / "agency.db")
    host = "codex"
    if invalidator == "legacy_v9":
        recipe = _recipe(store, "turn-one")
        recipe["recipe_version"] = 9
        connection = store._connect()
        try:
            connection.execute(
                "UPDATE runs SET preflight_result = ? WHERE trace_id = 'turn-one'",
                (json.dumps(recipe, sort_keys=True, separators=(",", ":")),),
            )
            connection.commit()
        finally:
            connection.close()
    elif invalidator == "roster_generation":
        connection = store._connect()
        try:
            connection.execute(
                "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
            )
            connection.commit()
        finally:
            connection.close()
    else:
        host = "hermes"
    result = _continue(store, host=host)

    _assert_fresh_reroute(store, result)


@pytest.mark.parametrize("progress", ["skipped", "activation_grant"])
def test_progressed_delegation_cannot_be_duplicated_by_continuation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    progress: str,
) -> None:
    store, _first = _first_turn(
        tmp_path / "agency.db",
        message=(
            "Perform these independent tasks:\n"
            "- Review authentication security.\n"
            "- Document release workflow."
        ),
    )
    delegations = store.get_delegations("turn-one")
    assert len(delegations) == 2
    if progress == "skipped":
        store.update_delegation(
            delegations[0]["id"],
            status="skipped",
            skip_reason="source work was already handled",
        )
    else:
        store.prepare_delegation_activation(
            session_id="durable-session",
            trace_id="turn-one",
            specialist_slug=str(delegations[0]["recommended_agent"]),
            work_unit_id=str(delegations[0]["work_unit_id"]),
        )
    second = _continue(store)

    _assert_fresh_reroute(store, second)
    assert store.get_delegations("turn-two") == []


def test_unstarted_unit_plan_is_reissued_with_ids_but_without_task_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_message = (
        "Perform these independent tasks:\n"
        "- Review authentication security.\n"
        "- Document release workflow."
    )
    store, _first = _first_turn(tmp_path / "agency.db", message=original_message)
    source_rows = store.get_delegations("turn-one")
    assert len(source_rows) == 2
    monkeypatch.setattr(pipeline, "route", _forbid_selector)

    second = _continue(store)
    target_rows = store.get_delegations("turn-two")

    assert len(target_rows) == 2
    assert {(row["work_unit_id"], row["recommended_agent"]) for row in target_rows} == {
        (row["work_unit_id"], row["recommended_agent"]) for row in source_rows
    }
    assert {row["status"] for row in target_rows} == {"suggested"}
    assert second.selected_specialists
    assert "Review authentication security." not in second.context
    assert "Document release workflow." not in second.context
    assert all(str(row["work_unit_id"]) in second.context for row in target_rows)


def test_active_revision_mismatch_is_detected_even_with_tampered_snapshot_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _first = _first_turn(tmp_path / "agency.db")
    source_recipe = _recipe(store, "turn-one")
    slug = source_recipe["selection_refs"][0]["slug"]
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE agent_active SET hash = ? WHERE agent_slug = ?",
            ("a" * 64, slug),
        )
        connection.commit()
    finally:
        connection.close()
    monkeypatch.setattr(
        pipeline,
        "routing_context_fingerprint",
        lambda *_args, **_kwargs: source_recipe["routing"]["context_fingerprint"],
    )
    result = _continue(store)

    _assert_fresh_reroute(store, result)


def test_continuation_chain_always_references_the_immediate_validated_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, first = _first_turn(tmp_path / "agency.db")
    monkeypatch.setattr(pipeline, "route", _forbid_selector)

    second = _continue(store)
    third = _continue(store, trace_id="turn-three")
    third_recipe = _recipe(store, "turn-three")

    assert second.selected_specialists == first.selected_specialists
    assert third.selected_specialists == first.selected_specialists
    assert third.continuation_of == "turn-two"
    assert third_recipe["routing"]["origin_trace_id"] == "turn-two"
    assert third_recipe["continuation_guard"]["source_trace_id"] == "turn-two"


def test_selector_refuses_bare_continuation_without_trusted_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["code-reviewer"],
            "confidence": 0.8,
            "latency_ms": 0,
            "status": "token_fallback",
        },
    )

    routing = pipeline.route(
        "session",
        "continue",
        [
            {
                "slug": "code-reviewer",
                "name": "Code Reviewer",
                "description": "Reviews code.",
                "division": "engineering",
                "categories": ["review"],
                "capabilities": ["code review"],
            }
        ],
        config=AgencyConfig(),
    )

    assert routing["turn_kind"] == "new_intent"
    assert routing["selected_ids"] == ["code-reviewer"]
    assert routing["status"] == "token_fallback"
    assert routing.get("continuation_reused") is not True
    assert routing.get("continuation_resolution_required") is not True
