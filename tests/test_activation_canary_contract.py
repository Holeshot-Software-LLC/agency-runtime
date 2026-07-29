"""Deterministic, authority-bounded Codex activation-canary routing."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core import canary
from agency_runtime.core.activation_canary_contract import (
    CODEX_ACTIVATION_CANARY_PROMPT,
    CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
    CODEX_ACTIVATION_CANARY_WORK_UNIT,
    is_exact_codex_activation_canary_task,
)
from agency_runtime.core.config import AgencyConfig, reset_config_cache
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.native_child_prompt_delivery import parse_native_child_prompt_delivery
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import (
    MAX_WORK_UNIT_CHARS,
    build_unit_agent_plan,
    hydrate_unit_agent_plan,
)
from tests.runtime_support import write_provider_config

_CANARY_ENV = {
    "AGENCY_CANARY_MODE": "1",
    "AGENCY_CANARY_REQUIRE_EXISTING_STORE": "1",
}


def _task(nonce: str = "a" * 32) -> str:
    return f"{CODEX_ACTIVATION_CANARY_PROMPT}\n\nCanary nonce: {nonce}"


def _catalog(*, required_tools: list[str] | None = None) -> list[dict[str, Any]]:
    return [
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Reviews code for behavioral regressions and test gaps.",
            "categories": ["code", "review", "quality"],
            "capabilities": ["code review", "bug finding", "test assessment"],
            "supported_hosts": ["codex"],
            "supported_platforms": ["windows"],
            "authority": "review",
            "task_types": ["analysis", "review"],
            "context_mode": "direct_safe",
            "required_tools": required_tools or [],
            "evidence_requirements": [],
        }
    ]


def _route(
    monkeypatch: pytest.MonkeyPatch,
    *,
    catalog: list[dict[str, Any]] | None = None,
    set_canary_env: bool = True,
) -> dict[str, Any]:
    session_id = "activation-canary-contract"
    trace_id = "activation-canary-contract-trace"
    if set_canary_env:
        for name, value in _CANARY_ENV.items():
            monkeypatch.setenv(name, value)
    capability = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id=session_id,
        trace_id=trace_id,
        available_tools=("repository-read", "native-delegation"),
    )
    snapshot = SimpleNamespace(
        generation=7,
        worker_count=1,
        contract_fingerprint="sha256:" + "a" * 64,
    )
    return pipeline.route(
        session_id,
        _task(),
        _catalog() if catalog is None else catalog,
        config=AgencyConfig(),
        trace_id=trace_id,
        host="codex",
        platform="windows",
        capability_receipt=capability,
        workforce_snapshot=snapshot,
    )


@pytest.mark.parametrize(
    ("task", "host", "status", "environ"),
    [
        (_task(), "claude", "native-contract-verified", _CANARY_ENV),
        (_task(), "codex", "explicit", _CANARY_ENV),
        (_task(), "codex", "native-contract-verified", {"AGENCY_CANARY_MODE": "1"}),
        (
            _task(),
            "codex",
            "native-contract-verified",
            {"AGENCY_CANARY_REQUIRE_EXISTING_STORE": "1"},
        ),
        (_task("A" * 32), "codex", "native-contract-verified", _CANARY_ENV),
        (_task("a" * 31), "codex", "native-contract-verified", _CANARY_ENV),
        (_task("a" * 33), "codex", "native-contract-verified", _CANARY_ENV),
        (
            _task().replace("\n\n", "\r\n\r\n"),
            "codex",
            "native-contract-verified",
            _CANARY_ENV,
        ),
        (_task() + " ", "codex", "native-contract-verified", _CANARY_ENV),
        ("Canary nonce: " + "a" * 32, "codex", "native-contract-verified", _CANARY_ENV),
    ],
)
def test_activation_canary_task_recognition_is_closed_world(
    task: str,
    host: str,
    status: str,
    environ: dict[str, str],
) -> None:
    assert not is_exact_codex_activation_canary_task(
        task,
        host=host,
        capability_status=status,
        environ=environ,
    )


def test_activation_canary_task_recognizes_only_exact_native_probe() -> None:
    assert is_exact_codex_activation_canary_task(
        _task(),
        host="codex",
        capability_status="native-contract-verified",
        environ=_CANARY_ENV,
    )


def test_activation_canary_prompt_and_unit_fit_every_transport_bound() -> None:
    task = _task()
    assert len(task) <= pipeline.MAX_ROUTING_SIGNAL_CHARS
    assert len(CODEX_ACTIVATION_CANARY_WORK_UNIT) <= MAX_WORK_UNIT_CHARS
    assert CODEX_ACTIVATION_CANARY_WORK_UNIT != CODEX_ACTIVATION_CANARY_PROMPT
    assert " ".join(task.split()) != CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert "Canary nonce:" not in CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert canary.CANARY_PROMPT == CODEX_ACTIVATION_CANARY_PROMPT


def test_activation_canary_route_bypasses_planner_with_one_read_only_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    clear_cache()
    clear_session_routing()

    def forbidden_planner(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("activation canary crossed semantic workforce planning")

    monkeypatch.setattr(inference, "plan_and_staff_workforce", forbidden_planner)
    monkeypatch.setattr(
        pipeline,
        "_remember_routing",
        lambda *_args, **_kwargs: pytest.fail("diagnostic route must not enter routing caches"),
    )
    result = _route(monkeypatch)

    assert result["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert result["selected_ids"] == ["code-reviewer"]
    assert result["semantic_ids"] == ["code-reviewer"]
    assert result["inference_mode"] == "activation_canary_contract"
    assert result["inference_required"] is False
    assert result["inference_attempted"] is False
    assert result["provider_attempts"] == []
    assert result["work_units"] == {
        "count": 1,
        "confidence": "high",
        "source": "activation-canary-contract",
        "units": [CODEX_ACTIVATION_CANARY_WORK_UNIT],
        "delegate": True,
    }
    assert "workforce_unit_bindings" not in result
    assert "workforce_unit_descriptors" not in result
    assert len(result["unit_assignment_agents"]) == 1
    assert result["unit_assignment_agents"][0]["slug"] == "code-reviewer"
    assert result["unit_assignment_agents"][0].get("required_tools", []) == []

    plan = build_unit_agent_plan(result, AgencyConfig().delegation)
    assert len(plan) == 1
    assert plan[0]["recommended_agent"] == "code-reviewer"
    assert plan[0]["mutation_scope"] == "read_only"
    assert plan[0]["required_tools"] == []
    hydrated = hydrate_unit_agent_plan(result, plan)
    assert len(hydrated) == 1
    assert hydrated[0]["goal"] == CODEX_ACTIVATION_CANARY_WORK_UNIT


@pytest.mark.parametrize(
    "drift",
    [
        {"authority": "modify"},
        {"task_types": ["implementation"]},
        {"context_mode": "isolated"},
    ],
)
def test_activation_canary_route_abstains_on_specialist_authority_drift(
    monkeypatch: pytest.MonkeyPatch,
    drift: dict[str, Any],
) -> None:
    from agency_runtime.core.workforce import inference

    clear_cache()
    clear_session_routing()
    monkeypatch.setattr(
        inference,
        "plan_and_staff_workforce",
        lambda *_args, **_kwargs: pytest.fail("planner must remain unreachable"),
    )
    catalog = _catalog()
    catalog[0].update(drift)

    result = _route(monkeypatch, catalog=catalog)

    assert result["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert result["status"] == "abstained"
    assert result["selected_ids"] == []
    assert result["work_units"]["delegate"] is False


def test_activation_canary_route_never_fabricates_a_missing_specialist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    clear_cache()
    clear_session_routing()
    monkeypatch.setattr(
        inference,
        "plan_and_staff_workforce",
        lambda *_args, **_kwargs: pytest.fail("planner must remain unreachable"),
    )

    result = _route(monkeypatch, catalog=[])

    assert result["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert result["status"] == "abstained"
    assert result["selected_ids"] == []
    assert result["error"] == ("activation canary specialist is not eligible in the current roster")


def test_activation_canary_route_abstains_when_no_tool_contract_drifts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    clear_cache()
    clear_session_routing()
    monkeypatch.setattr(
        inference,
        "plan_and_staff_workforce",
        lambda *_args, **_kwargs: pytest.fail("planner must remain unreachable"),
    )

    result = _route(monkeypatch, catalog=_catalog(required_tools=["repository-read"]))

    assert result["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert result["status"] == "abstained"
    assert result["selected_ids"] == []
    assert result["unit_assignment_agents"] == []
    assert result["work_units"]["delegate"] is False
    assert result["error"] == (
        "activation canary specialist requires tools outside the no-tool contract"
    )


def test_ordinary_exact_text_without_restricted_environment_uses_workforce_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference, routing_projection

    clear_cache()
    clear_session_routing()
    monkeypatch.delenv("AGENCY_CANARY_MODE", raising=False)
    monkeypatch.delenv("AGENCY_CANARY_REQUIRE_EXISTING_STORE", raising=False)
    calls: list[str] = []

    def fake_planner(message: str, *_args: Any, **_kwargs: Any) -> SimpleNamespace:
        calls.append(message)
        return SimpleNamespace(attempts=())

    monkeypatch.setattr(inference, "plan_and_staff_workforce", fake_planner)
    monkeypatch.setattr(
        pipeline,
        "_run_gap_hiring",
        lambda outcome, request, config, store, snapshot, catalog, **_kwargs: (
            outcome,
            snapshot,
            catalog,
            [],
        ),
    )
    monkeypatch.setattr(
        routing_projection,
        "project_workforce_routing",
        lambda *_args, **_kwargs: {
            "selected_ids": [],
            "semantic_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "workforce_inference",
            "work_units": {"count": 0, "units": [], "delegate": False},
        },
    )

    result = _route(monkeypatch, set_canary_env=False)

    assert calls == [_task()]
    assert result["source"] == "workforce_inference"


def test_activation_canary_preflight_replays_one_exact_selected_only_unit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.workforce import inference

    config_path = tmp_path / "agency.yaml"
    write_provider_config(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    store = Store(tmp_path / "agency.db", config_path=config_path)
    seed_starter_roster(store)
    for name, value in _CANARY_ENV.items():
        monkeypatch.setenv(name, value)
    session_id = "activation-canary-preflight"
    trace_id = "activation-canary-preflight-trace"
    capability = native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id=session_id,
        trace_id=trace_id,
        available_tools=("repository-read", "native-delegation"),
    )
    monkeypatch.setattr(
        inference,
        "plan_and_staff_workforce",
        lambda *_args, **_kwargs: pytest.fail("planner must remain unreachable"),
    )
    try:
        result = run_preflight(
            store,
            session_id=session_id,
            trace_id=trace_id,
            user_message=_task(),
            host="codex",
            capability_receipt=capability,
        )
    finally:
        reset_config_cache()

    assert result.routing["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    assert result.selected_specialists == ("code-reviewer",)
    assert len(result.delegation_plan) == 1
    plan = result.delegation_plan[0]
    assert plan["recommended_agent"] == "code-reviewer"
    assert plan["mutation_scope"] == "read_only"
    assert plan["goal"] == CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert plan["goal"] != " ".join(_task().split())

    task_name = codex_task_name_for_work_unit(str(plan["work_unit_id"]))
    bridge = HookBridge("codex", store=store)
    hook_payload = {
        "hook_event_name": "PreToolUse",
        "session_id": session_id,
        "turn_id": trace_id,
        "tool_name": "collaborationspawn_agent",
        "tool_use_id": "canonical-child-goal",
        "tool_input": {
            "fork_turns": "none",
            "task_name": task_name,
            "message": CODEX_ACTIVATION_CANARY_WORK_UNIT,
        },
    }
    parent_as_child = bridge.handle(
        {
            **hook_payload,
            "tool_use_id": "parent-prompt-is-not-child-goal",
            "tool_input": {**hook_payload["tool_input"], "message": _task()},
        }
    )["hookSpecificOutput"]
    assert parent_as_child["permissionDecision"] == "deny"
    assert "does not exactly match" in parent_as_child["permissionDecisionReason"]

    hook_result = bridge.handle(
        {
            **hook_payload,
            "tool_input": {
                **hook_payload["tool_input"],
                "message": "gAAAAABopaque-parent-tool-ciphertext",
            },
        }
    )
    assert hook_result["hookSpecificOutput"] == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    }
    start = bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": session_id,
            "turn_id": "activation-canary-child-trace",
            "agent_id": "activation-canary-child",
            "agent_type": "worker",
        }
    )
    delivery = parse_native_child_prompt_delivery(start["hookSpecificOutput"]["additionalContext"])
    assert delivery is not None
    assert delivery.original_task == CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert hook_payload["tool_input"]["task_name"] == task_name

    snapshot = store.get_canary_activation_snapshot(
        host="codex",
        query_hash=result.routing["query_hash"],
    )
    assert snapshot["route"]["source"] == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
