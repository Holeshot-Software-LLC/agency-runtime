from __future__ import annotations

import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier

import pytest

from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.configuration import apply_config_operations, read_config_state
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.header.contract import (
    _delegation_line,
    validate_completion_policy,
)
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.preflight import PreflightResult, run_preflight
from agency_runtime.core.store import schema as store_schema
from agency_runtime.core.store.schema import (
    SCHEMA_VERSION,
    migrate_delegation_activation_unit_identity,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import handle_tool_call
from tests.runtime_support import (
    harden_private_test_file,
    stub_inference_invoker,
    write_provider_config,
)

_DRAFT = """Agency/Agencies loaded: code-reviewer
Agency/Agencies delegated: generic-worker via spawn_agent
Skills loaded: none
Actual Model selected: unknown -> unavailable - no model receipt recorded
Why: Specialist review was required.
How it shaped outcome: The review was applied in an isolated worker.

Done.
"""
_REQUEST = "Review and refactor this Python code for security and correctness"
_MULTI_REQUEST = (
    "Review and refactor this Python code for security and correctness, "
    "then document the deployment workflow."
)


@pytest.fixture()
def agent_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    try:
        yield config_path
    finally:
        reset_config_cache()


def _disable_agent(config_path: Path, slug: str) -> None:
    config_path.write_text(f"agents:\n  disabled: [{slug}]\n", encoding="utf-8")
    reset_config_cache()


def _optional_selected(selected: tuple[str, ...]) -> str:
    return next(slug for slug in selected if slug not in PROTECTED_AGENT_SLUGS)


def _capability(host: str, session_id: str, trace_id: str):
    return native_adapter_capability_receipt(
        host,
        platform="windows" if os.name == "nt" else "linux",
        session_id=session_id,
        trace_id=trace_id,
    )


def _isolated_preflight(
    path: Path,
    *,
    host: str = "codex",
    user_message: str = _REQUEST,
    minimum_selected: int = 1,
) -> tuple[Store, PreflightResult]:
    # ADR-0087: selection runs inference only when a provider is configured.
    # Configure one and stub the invoker so preflight exercises the inference
    # path instead of declining offline.
    config_path = path.parent / "agency.yaml"
    write_provider_config(config_path)
    os.environ["AGENCY_CONFIG_PATH"] = str(config_path)
    reset_config_cache()
    store = Store(path)
    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    try:
        result = run_preflight(
            store,
            session_id="session",
            trace_id="trace",
            user_message=user_message,
            host=host,
            capability_receipt=_capability(host, "session", "trace"),
        )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
        os.environ.pop("AGENCY_CONFIG_PATH", None)
        reset_config_cache()
    assert len(result.selected_specialists) >= minimum_selected
    return store, result


def _isolated_turn(
    path: Path,
    *,
    host: str = "codex",
    user_message: str = _REQUEST,
    minimum_selected: int = 1,
) -> tuple[Store, tuple[str, ...]]:
    store, result = _isolated_preflight(
        path,
        host=host,
        user_message=user_message,
        minimum_selected=minimum_selected,
    )
    return store, result.selected_specialists


def _active_version(store: Store, slug: str) -> str:
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT version FROM agent_active WHERE agent_slug = ?",
            (slug,),
        ).fetchone()
    finally:
        connection.close()
    assert row is not None
    return str(row["version"])


def _activation_work_unit(store: Store, slug: str) -> str:
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    planned = next(
        (row for row in snapshot["unit_agent_plan"] if row["recommended_agent"] == slug),
        None,
    )
    return str(planned["work_unit_id"]) if planned is not None else f"specialist:{slug}"


def _activation_work_unit_for(store: Store, slug: str, session_id: str, trace_id: str) -> str:
    snapshot = store.get_completion_evidence_snapshot(session_id, trace_id)
    planned = next(
        (row for row in snapshot["unit_agent_plan"] if row["recommended_agent"] == slug),
        None,
    )
    return str(planned["work_unit_id"]) if planned is not None else f"specialist:{slug}"


def _planned_goal(context: str, work_unit_id: str) -> str:
    prefix = f"- unit={work_unit_id};"
    line = next(item for item in context.splitlines() if item.startswith(prefix))
    return str(json.loads(line.split("; goal=", 1)[1]))


@pytest.mark.parametrize(
    ("host", "native_tool"),
    [
        ("codex", "`spawn_agent`"),
        ("claude", "`Agent`"),
        ("openclaw", "`sessions_spawn`"),
        ("hermes", "`delegate_task`"),
    ],
)
def test_every_persistent_host_parent_receives_an_exact_specialist_plan(
    tmp_path: Path,
    host: str,
    native_tool: str,
) -> None:
    store, result = _isolated_preflight(
        tmp_path / f"{host}-parent-plan.db",
        host=host,
    )
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    plan = snapshot["unit_agent_plan"]

    assert result.selected_specialists
    assert plan
    assert set(result.selected_specialists) == {
        slug for row in plan for slug in row["recommended_agents"]
    }
    assert result.loaded_specialists == ()
    assert "[AGENCY DELEGATION PLAN]" in result.context
    assert native_tool in result.context
    assert all(row["goal_hash"] and row["resource_hashes"] for row in plan)


@pytest.mark.parametrize("host", ["openclaw", "hermes"])
def test_direct_native_child_preflight_consumes_the_exact_parent_activation(
    tmp_path: Path,
    host: str,
) -> None:
    store, parent = _isolated_preflight(
        tmp_path / "openclaw-direct-child.db",
        host=host,
    )
    parent_snapshot = store.get_completion_evidence_snapshot("session", "trace")
    plan = parent_snapshot["unit_agent_plan"][0]
    unit = str(plan["work_unit_id"])
    slug = str(plan["recommended_agent"])
    goal = _planned_goal(parent.context, unit)
    backend = "sessions_spawn" if host == "openclaw" else "delegate_task"
    worker_id = f"{host}-child-session"
    native_run_id = f"{host}-subagent:{worker_id}"
    assert (
        mark_delegation_executed(
            store,
            session_id="session",
            trace_id="trace",
            host=host,
            backend=backend,
            agent=slug,
            goal=goal,
            work_unit_id=unit,
            executed_worker_kind="generic-worker",
            executed_worker_id=worker_id,
            native_run_id=native_run_id,
        )
        == 1
    )
    store.record_native_child_started(
        host=host,
        backend=backend,
        session_id="session",
        trace_id="trace",
        work_unit_id=unit,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )

    child = run_preflight(
        store,
        session_id="child-session",
        trace_id="child-trace",
        user_message=goal,
        host=host,
        capability_receipt=_capability(host, "child-session", "child-trace"),
        parent_session_id="session",
        parent_trace_id="trace",
        native_worker_id=worker_id,
        native_run_id=native_run_id,
    )

    assert child.routing["source"] == "parent_unit_reuse"
    assert child.routing["status"] == "parent_unit_reused"
    assert child.loaded_specialists == (slug,)
    assert child.selected_specialists == (slug,)
    reference = next(
        item for item in parent_snapshot["selected_specialists"] if item["slug"] == slug
    )
    prompt = store.get_versioned_specialist_prompt(
        slug,
        reference["version"],
        reference["hash"],
    )
    assert prompt["prompt_body"] in child.context
    completed_parent = store.get_completion_evidence_snapshot("session", "trace")
    activation = next(
        item for item in completed_parent["specialist_activations"] if item["work_unit_id"] == unit
    )
    assert activation["specialist_slug"] == slug
    assert activation["worker_id"] == worker_id
    assert activation["native_run_id"] == native_run_id
    delegation = next(
        item for item in completed_parent["delegations"] if item["work_unit_id"] == unit
    )
    assert delegation["activation_receipt_id"] == activation["id"]


def _activate(
    store: Store,
    slug: str,
    *,
    worker_id: str | None = None,
    native_run_id: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    work_unit_id = _activation_work_unit(store, slug)
    worker = worker_id or f"worker-{slug}"
    native = native_run_id or f"run-{slug}"
    prepared = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": work_unit_id,
        },
        store,
    )
    assert "error" not in prepared
    loaded = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": work_unit_id,
            "activation_token": prepared["activation_token"],
            "worker_id": worker,
            "native_run_id": native,
        },
        store,
    )
    assert "error" not in loaded
    return prepared, loaded


def test_flattened_codex_activation_requires_a_native_child_start(
    tmp_path: Path,
) -> None:
    store, selected = _isolated_turn(tmp_path / "v2-lifecycle.db")
    slug = selected[0]
    work_unit_id = _activation_work_unit(store, slug)
    prepared = store.prepare_delegation_activation(
        session_id="session",
        trace_id="trace",
        specialist_slug=slug,
        work_unit_id=work_unit_id,
        grant_origin="native_hook",
        tool_use_id="v2-spawn",
    )
    consume = {
        "activation_token": str(prepared["activation_token"]),
        "session_id": "session",
        "trace_id": "trace",
        "specialist_slug": slug,
        "work_unit_id": work_unit_id,
        "worker_id": f"task:{codex_task_name_for_work_unit(work_unit_id)}",
        "native_run_id": f"codex-task:{codex_task_name_for_work_unit(work_unit_id)}",
        "require_native_child_started": True,
    }

    with pytest.raises(ValueError, match="native-child lifecycle receipt"):
        store.consume_delegation_activation(**consume)

    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        work_unit_id=work_unit_id,
        worker_id="agent-v2",
        native_run_id="codex-agent:agent-v2",
    )

    with pytest.raises(ValueError, match="native-child lifecycle receipt"):
        store.consume_delegation_activation(
            **consume,
            match_native_child_identity=True,
        )

    consumed = store.consume_delegation_activation(**consume)
    assert consumed["slug"] == slug
    assert consumed["worker_id"] == "agent-v2"
    assert consumed["native_run_id"] == "codex-agent:agent-v2"
    assert store.get_consumed_delegation_lineage(
        session_id="session",
        trace_id="trace",
        specialist_slug=slug,
        work_unit_id=work_unit_id,
        activation_token=str(prepared["activation_token"]),
        tool_use_id="v2-spawn",
    ) == {
        "worker_kind": "generic-worker",
        "worker_id": "agent-v2",
        "native_run_id": "codex-agent:agent-v2",
    }
    assert (
        store.get_consumed_delegation_lineage(
            session_id="session",
            trace_id="trace",
            specialist_slug=slug,
            work_unit_id=work_unit_id,
            activation_token="y" * 43,
            tool_use_id="v2-spawn",
        )
        is None
    )


def test_isolated_activation_is_rejected_without_receipt_and_token_is_one_use(
    tmp_path: Path,
) -> None:
    store, selected = _isolated_turn(
        tmp_path / "partial.db",
        user_message=_MULTI_REQUEST,
    )

    without_grant = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": selected[0],
        },
        store,
    )
    assert "one-use activation_token" in without_grant["error"]

    mismatched_binding = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": selected[0],
            "work_unit_id": "unit-wrong",
        },
        store,
    )
    assert "do not match the persisted unit-agent plan" in mismatched_binding["error"]

    work_unit_id = _activation_work_unit(store, selected[0])
    prepared = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": selected[0],
            "work_unit_id": work_unit_id,
        },
        store,
    )
    missing_unit = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": selected[0],
            "activation_token": prepared["activation_token"],
        },
        store,
    )
    assert "work_unit_id is required" in missing_unit["error"]
    loaded = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": selected[0],
            "work_unit_id": work_unit_id,
            "activation_token": prepared["activation_token"],
            "worker_id": "worker-partial",
            "native_run_id": "run-partial",
        },
        store,
    )
    assert "error" not in loaded
    replay = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": selected[0],
            "work_unit_id": work_unit_id,
            "activation_token": prepared["activation_token"],
            "worker_id": "worker-partial",
            "native_run_id": "run-partial",
        },
        store,
    )
    assert "already consumed" in replay["error"]
    assert loaded["version"] == prepared["version"]
    assert loaded["prompt_hash"] == prepared["prompt_hash"]
    assert loaded["activation_receipt_id"] == prepared["receipt_id"]
    assert loaded["legacy_activation_receipt_id"] == prepared["receipt_id"]
    assert loaded["activation_grant"] == prepared["activation_grant"]
    assert loaded["consumption_receipt_id"] == loaded["activation_receipt"]["receipt_id"]
    assert loaded["activation_receipt"]["grant_id"] == prepared["grant_id"]
    assert loaded["activation_receipt"]["child_run"] == {
        "worker_kind": "generic-worker",
        "worker_id": "worker-partial",
        "native_run_id": "run-partial",
    }
    assert loaded["worker_kind"] == "generic-worker"
    assert loaded["worker_id"] == "worker-partial"
    assert loaded["native_run_id"] == "run-partial"
    assert prepared["activation_token"] not in repr(loaded)

    violation = validate_completion_policy(
        _DRAFT,
        session_id="session",
        trace_id="trace",
        store=store,
    )
    assert violation is not None
    assert violation["missing"] == ["specialist_activation"]

    for slug in selected[1:]:
        _activate(store, slug)
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    expected = {
        (row["slug"], row["version"], row["hash"]) for row in snapshot["selected_specialists"]
    }
    actual = {
        (
            row["specialist_slug"],
            row["specialist_version"],
            row["specialist_prompt_hash"],
        )
        for row in snapshot["specialist_activations"]
    }
    assert actual == expected


def test_isolated_turn_rejects_every_tokenless_slug_and_not_ready_load(tmp_path: Path) -> None:
    store, selected = _isolated_turn(tmp_path / "unselected.db")
    from agency_runtime.core.resident_managers import is_resident_manager_slug

    unselected = next(
        row["slug"]
        for row in store.get_active_roster_as_catalog()
        if row["slug"] not in selected and not is_resident_manager_slug(row["slug"])
    )
    rejected = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": unselected,
        },
        store,
    )
    assert "one-use activation_token" in rejected["error"]

    not_ready = Store(tmp_path / "not-ready.db")
    not_ready.create_run(
        trace_id="trace",
        session_id="session",
        host="codex",
    )
    rejected_not_ready = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": "code-reviewer",
        },
        not_ready,
    )
    assert rejected_not_ready["error"] == "trace_id has not completed preflight"


def test_activation_replays_immutable_version_after_roster_deactivation(tmp_path: Path) -> None:
    store, selected = _isolated_turn(tmp_path / "version.db")
    slug = selected[0]
    work_unit_id = _activation_work_unit(store, slug)
    prepared = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": work_unit_id,
        },
        store,
    )
    store.deactivate_agent(slug)

    loaded = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": work_unit_id,
            "activation_token": prepared["activation_token"],
            "worker_id": "worker-version",
            "native_run_id": "run-version",
        },
        store,
    )

    assert loaded["version"] == prepared["version"]
    assert loaded["prompt_hash"] == prepared["prompt_hash"]
    assert loaded["prompt"]


def test_recommendation_stays_immutable_and_header_separates_retrieval_from_execution(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "identity.db")
    store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="codex",
        work_unit_id="unit-a",
        recommended_agent="code-reviewer",
        status="suggested",
    )
    mark_delegation_executed(
        store,
        session_id="session",
        trace_id="trace",
        host="codex",
        backend="spawn_agent",
        agent="generic-worker",
        work_unit_id="unit-a",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-123",
        native_run_id="run-456",
    )
    row = store.get_delegations("trace")[0]
    assert row["recommended_agent"] == "code-reviewer"
    assert row["executed_worker_kind"] == "generic-worker"
    assert row["executed_worker_id"] == "worker-123"
    assert row["native_run_id"] == "run-456"
    assert _delegation_line([row]) == "none - executed worker has no validated Agency specialist"

    attested, selected = _isolated_turn(tmp_path / "attested.db")
    slug = selected[0]
    prepared, _loaded = _activate(
        attested,
        slug,
        worker_id="worker-789",
        native_run_id="spawn_agent:run-789",
    )
    mark_delegation_executed(
        attested,
        session_id="session",
        trace_id="trace",
        host="codex",
        backend="spawn_agent",
        work_unit_id=str(prepared["work_unit_id"]),
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-789",
        native_run_id="spawn_agent:run-789",
    )
    attested_row = attested.get_delegations("trace")[0]
    assert attested_row["activation_receipt_id"] == prepared["receipt_id"]
    assert attested_row["retrieved_specialist_slug"] == slug
    assert attested_row["retrieved_specialist_version"] == prepared["version"]
    assert attested_row["retrieved_specialist_prompt_hash"] == prepared["prompt_hash"]
    assert _delegation_line([attested_row]) == (f"{slug} via generic-worker/spawn_agent")


def test_native_adapter_separates_worker_and_run_ids_from_work_unit(tmp_path: Path) -> None:
    store = Store(tmp_path / "adapter.db")
    store.create_run(trace_id="trace", session_id="session", host="codex")
    adapter = CodexAdapter(store=store)

    adapter.record_tool_call(
        tool_name="spawn_agent",
        args={"goal": "review the security boundary"},
        result={"agent_id": "agent-123", "run_id": "run-456"},
        session_id="session",
        trace_id="trace",
    )

    row = store.get_delegations("trace")[0]
    assert row["work_unit_id"] != "agent-123"
    assert row["executed_worker_kind"] == "generic-worker"
    assert row["executed_worker_id"] == "agent-123"
    assert row["native_run_id"] == "run-456"


@pytest.mark.parametrize(
    ("host", "tool_name", "tool_input", "tool_response", "expected_header"),
    [
        (
            "codex",
            "spawn_agent",
            {"task_name": "{unit}", "message": "apply the selected review"},
            {"agent_id": "agent-123", "status": "completed"},
            "{slug} via generic-worker/spawn_agent",
        ),
        (
            "claude",
            "Agent",
            {
                "description": "{unit}",
                "prompt": "apply the selected review",
                "subagent_type": "general-purpose",
            },
            {"agentId": "claude-worker", "status": "completed"},
            "{slug} via generic-worker/delegate_task",
        ),
    ],
)
def test_official_isolated_native_shapes_reciprocally_bind_receipt(
    tmp_path: Path,
    host: str,
    tool_name: str,
    tool_input: dict[str, str],
    tool_response: dict[str, str],
    expected_header: str,
) -> None:
    store, selected = _isolated_turn(tmp_path / f"{host}.db", host=host)
    slug = selected[0]
    prepared, _loaded = _activate(
        store,
        slug,
        worker_id="agent-123" if host == "codex" else "claude-worker",
        native_run_id=(
            "codex-agent:agent-123" if host == "codex" else "claude-agent:claude-worker"
        ),
    )
    unit = str(prepared["work_unit_id"])
    native_unit = codex_task_name_for_work_unit(unit) if host == "codex" else unit
    HookBridge(host, store=store).handle(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session",
            "turn_id": "trace",
            "tool_use_id": f"{host}-tool-use-1",
            "tool_name": tool_name,
            "tool_input": {
                key: value.format(unit=native_unit) for key, value in tool_input.items()
            },
            "tool_response": tool_response,
        }
    )

    event = store.get_delegations("trace")[0]
    activation = store.get_completion_evidence_snapshot("session", "trace")[
        "specialist_activations"
    ][0]
    assert event["work_unit_id"] == unit
    assert event["activation_receipt_id"] == prepared["receipt_id"]
    assert activation["delegation_event_id"] == event["id"]
    assert event["retrieved_specialist_slug"] == slug
    assert activation["native_run_id"] == (
        "codex-agent:agent-123" if host == "codex" else "claude-agent:claude-worker"
    )
    assert _delegation_line([event]) == expected_header.format(slug=slug)


@pytest.mark.parametrize(
    ("host", "tool_name", "label_field", "task_field", "worker_id", "native_run_id"),
    [
        (
            "codex",
            "spawn_agent",
            "task_name",
            "message",
            "agent-123",
            "codex-agent:agent-123",
        ),
        (
            "claude",
            "Agent",
            "description",
            "prompt",
            "claude-worker",
            "claude-agent:claude-worker",
        ),
    ],
)
def test_hook_owned_delivery_injects_and_reciprocally_activates_exact_prompt(
    tmp_path: Path,
    host: str,
    tool_name: str,
    label_field: str,
    task_field: str,
    worker_id: str,
    native_run_id: str,
) -> None:
    store, result = _isolated_preflight(tmp_path / f"hook-owned-{host}.db", host=host)
    selected = result.selected_specialists
    slug = selected[0]
    unit = _activation_work_unit(store, slug)
    goal = _planned_goal(result.context, unit)
    native_label = codex_task_name_for_work_unit(unit) if host == "codex" else unit
    bridge = HookBridge(host, store=store)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "session",
        "turn_id": "trace",
        "tool_use_id": f"{host}-tool-use-1",
        "tool_name": tool_name,
        "tool_input": {
            label_field: native_label,
            task_field: goal,
            **({"subagent_type": "general-purpose"} if host == "claude" else {}),
        },
    }

    pre_tool = bridge.handle(payload)
    output = pre_tool["hookSpecificOutput"]
    assert output["permissionDecision"] == "allow"
    rewritten = output["updatedInput"]
    assert "[AGENCY EXACT SPECIALIST ACTIVATION v1]" in rewritten[task_field]
    response_key = "agent_id" if host == "codex" else "agentId"
    if host == "codex":
        bridge.handle(
            {
                "hook_event_name": "SubagentStart",
                "session_id": "session",
                "turn_id": "child-turn",
                "agent_id": worker_id,
                "agent_type": "worker",
            }
        )
    bridge.handle(
        {
            **payload,
            "hook_event_name": "PostToolUse",
            "tool_input": rewritten,
            "tool_response": {response_key: worker_id, "status": "completed"},
        }
    )

    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    [activation] = snapshot["specialist_activations"]
    [event] = [item for item in snapshot["delegations"] if item["work_unit_id"] == unit]
    assert activation["specialist_slug"] == slug
    assert activation["worker_id"] == worker_id
    assert activation["native_run_id"] == native_run_id
    assert activation["delegation_event_id"] == event["id"]
    assert event["activation_receipt_id"] == activation["id"]
    assert event["retrieved_specialist_slug"] == slug


def _prepared_codex_hook_delivery(
    tmp_path: Path,
    *,
    tool_name: str,
) -> tuple[Store, HookBridge, dict[str, object], dict[str, object], str]:
    store, result = _isolated_preflight(tmp_path / f"hook-response-{tool_name}.db", host="codex")
    slug = result.selected_specialists[0]
    unit = _activation_work_unit(store, slug)
    goal = _planned_goal(result.context, unit)
    worker_id = "agent-lifecycle"
    bridge = HookBridge("codex", store=store)
    payload: dict[str, object] = {
        "hook_event_name": "PreToolUse",
        "session_id": "session",
        "turn_id": "trace",
        "tool_use_id": f"{tool_name}-tool-use",
        "tool_name": tool_name,
        "tool_input": {
            "task_name": codex_task_name_for_work_unit(unit),
            "message": goal,
        },
    }
    rewritten = bridge.handle(payload)["hookSpecificOutput"]["updatedInput"]
    bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "session",
            "turn_id": "child-turn",
            "agent_id": worker_id,
            "agent_type": "worker",
        }
    )
    return store, bridge, payload, rewritten, worker_id


def test_codex_json_identity_must_match_lifecycle_on_initial_use_and_replay(
    tmp_path: Path,
) -> None:
    store, bridge, payload, rewritten, worker_id = _prepared_codex_hook_delivery(
        tmp_path,
        tool_name="spawn_agent",
    )
    post_payload = {**payload, "hook_event_name": "PostToolUse"}

    initial_forgery = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload=post_payload,
        tool_input=rewritten,
        tool_response=json.dumps({"agent_id": "agent-forged"}),
        trace_id="trace",
    )
    assert initial_forgery[3] is False

    accepted = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload=post_payload,
        tool_input=rewritten,
        tool_response=json.dumps({"agent_id": worker_id}),
        trace_id="trace",
    )
    assert accepted[3] is True

    replay_forgery = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload=post_payload,
        tool_input=rewritten,
        tool_response=json.dumps({"agent_id": "agent-forged"}),
        trace_id="trace",
    )
    assert replay_forgery[3] is False
    [activation] = store.get_completion_evidence_snapshot("session", "trace")[
        "specialist_activations"
    ]
    assert activation["worker_id"] == worker_id


def test_codex_v2_json_task_path_must_be_rooted_before_lifecycle_binding(
    tmp_path: Path,
) -> None:
    _store, bridge, payload, rewritten, _worker_id = _prepared_codex_hook_delivery(
        tmp_path,
        tool_name="collaborationspawn_agent",
    )
    post_payload = {**payload, "hook_event_name": "PostToolUse"}
    task_name = str(rewritten["task_name"])

    unrooted = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload=post_payload,
        tool_input=rewritten,
        tool_response=json.dumps({"task_name": task_name}),
        trace_id="trace",
    )
    assert unrooted[3] is False

    rooted = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload=post_payload,
        tool_input=rewritten,
        tool_response=json.dumps({"task_name": f"/root/{task_name}"}),
        trace_id="trace",
    )
    assert rooted[3] is True


def test_codex_v2_native_mapping_task_path_binds_started_child(
    tmp_path: Path,
) -> None:
    _store, bridge, payload, rewritten, _worker_id = _prepared_codex_hook_delivery(
        tmp_path,
        tool_name="collaborationspawn_agent",
    )
    task_name = str(rewritten["task_name"])

    accepted = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload={**payload, "hook_event_name": "PostToolUse"},
        tool_input=rewritten,
        tool_response={"task_name": f"/root/{task_name}"},
        trace_id="trace",
    )

    assert accepted[3] is True


def test_codex_v2_spawn_nickname_is_discarded_before_lifecycle_binding(
    tmp_path: Path,
) -> None:
    _store, bridge, payload, rewritten, worker_id = _prepared_codex_hook_delivery(
        tmp_path,
        tool_name="collaborationspawn_agent",
    )
    task_name = str(rewritten["task_name"])

    accepted = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload={**payload, "hook_event_name": "PostToolUse"},
        tool_input=rewritten,
        tool_response=json.dumps({"task_name": f"/root/{task_name}", "nickname": "Curie"}),
        trace_id="trace",
    )

    assert accepted[1] == {
        "task_name": task_name,
        "agent_id": worker_id,
        "native_run_id": f"codex-agent:{worker_id}",
    }
    assert accepted[3] is True


def test_codex_v2_spawn_result_rejects_unreviewed_extra_fields(
    tmp_path: Path,
) -> None:
    _store, bridge, payload, rewritten, _worker_id = _prepared_codex_hook_delivery(
        tmp_path,
        tool_name="collaborationspawn_agent",
    )
    task_name = str(rewritten["task_name"])

    rejected = bridge._consume_native_child_prompt_delivery(
        event="PostToolUse",
        payload={**payload, "hook_event_name": "PostToolUse"},
        tool_input=rewritten,
        tool_response=json.dumps(
            {"task_name": f"/root/{task_name}", "nickname": None, "extra": True}
        ),
        trace_id="trace",
    )

    assert rejected[3] is False


def test_all_selected_receipts_require_reciprocal_native_execution(tmp_path: Path) -> None:
    store, selected = _isolated_turn(tmp_path / "reciprocal.db")
    bridge = HookBridge("codex", store=store)
    for index, slug in enumerate(selected):
        prepared, _loaded = _activate(
            store,
            slug,
            worker_id=f"agent-{index}",
            native_run_id=f"codex-agent:agent-{index}",
        )
        unit = str(prepared["work_unit_id"])
        bridge.handle(
            {
                "hook_event_name": "PostToolUse",
                "session_id": "session",
                "turn_id": "trace",
                "tool_use_id": f"tool-use-{index}",
                "tool_name": "spawn_agent",
                "tool_input": {
                    "task_name": codex_task_name_for_work_unit(unit),
                    "message": "apply specialist",
                },
                "tool_response": {"agent_id": f"agent-{index}", "status": "completed"},
            }
        )

    violation = validate_completion_policy(
        _DRAFT,
        session_id="session",
        trace_id="trace",
        store=store,
    )
    assert violation is not None
    assert violation["missing"] != ["specialist_activation"]
    activations = store.get_completion_evidence_snapshot("session", "trace")[
        "specialist_activations"
    ]
    assert len({row["delegation_event_id"] for row in activations}) == len(selected)
    assert all(row["delegation_event_id"] for row in activations)


def test_disabled_agent_kills_prepared_grant_and_versioned_read(
    tmp_path: Path,
    agent_config: Path,
) -> None:
    store, selected = _isolated_turn(tmp_path / "disabled-consume.db")
    slug = _optional_selected(selected)
    unit = _activation_work_unit(store, slug)
    prepared = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": unit,
        },
        store,
    )
    assert "error" not in prepared

    _disable_agent(agent_config, slug)
    assert (
        store.get_versioned_specialist_prompt(
            slug,
            str(prepared["version"]),
            str(prepared["prompt_hash"]),
        )
        is None
    )
    rejected = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": unit,
            "activation_token": prepared["activation_token"],
            "worker_id": "worker-disabled",
            "native_run_id": "run-disabled",
        },
        store,
    )
    assert "is disabled" in rejected["error"]
    assert store.get_run("trace")["status"] == "specialist_disabled"
    connection = store._connect()
    try:
        consumed_at = connection.execute(
            "SELECT consumed_at FROM delegation_activation_receipts WHERE id = ?",
            (prepared["receipt_id"],),
        ).fetchone()[0]
    finally:
        connection.close()
    assert consumed_at is None


def test_explicit_config_identity_governs_selection_replay_and_activation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global_config = tmp_path / "global.yaml"
    write_provider_config(global_config)
    # Global default disables code-reviewer; the custom config must override it.
    global_config.write_text(
        global_config.read_text(encoding="utf-8") + "agents:\n  disabled: [code-reviewer]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(global_config))
    reset_config_cache()

    custom_config = tmp_path / "custom.yaml"
    write_provider_config(custom_config)
    # Preserve the test's disabled-agent toggles while keeping the provider.
    custom_config.write_text(
        custom_config.read_text(encoding="utf-8") + "agents:\n  disabled: []\n",
        encoding="utf-8",
    )
    config = load_config(custom_config)
    store = Store(
        tmp_path / "custom-config.db",
        config_path=config.config_path,
    )
    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    try:
        first = run_preflight(
            store,
            session_id="custom-session",
            trace_id="custom-trace",
            user_message=_REQUEST,
            host="codex",
            config=config,
            capability_receipt=_capability("codex", "custom-session", "custom-trace"),
        )
        assert "code-reviewer" in first.selected_specialists

        replay = run_preflight(
            store,
            session_id="custom-session",
            trace_id="custom-trace",
            user_message=_REQUEST,
            host="codex",
            config=config,
            capability_receipt=_capability("codex", "custom-session", "custom-trace"),
        )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
    assert replay.selected_specialists == first.selected_specialists
    assert replay.context == first.context

    unit = _activation_work_unit_for(store, "code-reviewer", "custom-session", "custom-trace")
    prepared = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "custom-session",
            "trace_id": "custom-trace",
            "slug": "code-reviewer",
            "work_unit_id": unit,
        },
        store,
    )
    assert "error" not in prepared

    # Simulate a dashboard or CLI write after the grant was issued.  Explicit
    # config identities are uncached, so consume must see the external change
    # without a process-global cache reset.
    custom_config.write_text(
        "agents:\n  disabled: [code-reviewer]\n",
        encoding="utf-8",
    )
    rejected = handle_tool_call(
        "agency.load_specialist",
        {
            "session_id": "custom-session",
            "trace_id": "custom-trace",
            "slug": "code-reviewer",
            "work_unit_id": unit,
            "activation_token": prepared["activation_token"],
            "worker_id": "worker-config",
            "native_run_id": "run-config",
        },
        store,
    )
    assert "is disabled" in rejected["error"]
    assert store.get_run("custom-trace")["status"] == "specialist_disabled"


def test_disabled_agent_kills_prepare_and_ready_recipe_replay(
    tmp_path: Path,
    agent_config: Path,
) -> None:
    prepare_store, prepare_selected = _isolated_turn(tmp_path / "disabled-prepare.db")
    slug = _optional_selected(prepare_selected)
    # Resolve the persisted work unit before disabling the specialist; the
    # completion-evidence snapshot now rejects disabled specialists (PR #129).
    unit = _activation_work_unit(prepare_store, slug)
    _disable_agent(agent_config, slug)
    rejected = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": unit,
        },
        prepare_store,
    )
    assert "is disabled" in rejected["error"]
    assert prepare_store.get_run("trace")["status"] == "specialist_disabled"

    agent_config.write_text("agents:\n  disabled: []\n", encoding="utf-8")
    reset_config_cache()
    replay_store, replay_selected = _isolated_turn(tmp_path / "disabled-replay.db")
    replay_slug = _optional_selected(replay_selected)
    _disable_agent(agent_config, replay_slug)
    with pytest.raises(RuntimeError, match="is disabled; start a fresh Agency preflight"):
        run_preflight(
            replay_store,
            session_id="session",
            trace_id="trace",
            user_message=_REQUEST,
            host="codex",
            capability_receipt=_capability("codex", "session", "trace"),
        )
    assert replay_store.get_run("trace")["status"] == "specialist_disabled"


def test_disabled_agent_kills_completion_after_capability_retrieval(
    tmp_path: Path,
    agent_config: Path,
) -> None:
    store, selected = _isolated_turn(tmp_path / "disabled-completion.db")
    slug = _optional_selected(selected)
    _activate(store, slug)
    _disable_agent(agent_config, slug)

    with pytest.raises(ValueError, match="is disabled; start a fresh Agency preflight"):
        store.get_completion_evidence_snapshot("session", "trace")
    assert store.get_run("trace")["status"] == "specialist_disabled"


def test_disable_racing_activation_consume_has_one_linearized_outcome(
    tmp_path: Path,
    agent_config: Path,
) -> None:
    """A cross-file/SQLite race must never leave half-consumed evidence."""

    for iteration in range(8):
        agent_config.write_text("agents:\n  disabled: []\n", encoding="utf-8")
        reset_config_cache()
        store, selected = _isolated_turn(tmp_path / f"activation-race-{iteration}.db")
        slug = _optional_selected(selected)
        unit = _activation_work_unit(store, slug)
        prepared = handle_tool_call(
            "agency.prepare_delegation",
            {
                "session_id": "session",
                "trace_id": "trace",
                "slug": slug,
                "work_unit_id": unit,
            },
            store,
        )
        assert "error" not in prepared
        revision = read_config_state(agent_config).revision
        barrier = Barrier(2)

        def disable(
            *,
            sync: Barrier = barrier,
            agent_slug: str = slug,
            config_revision: str = revision,
        ) -> None:
            sync.wait()
            apply_config_operations(
                [{"op": "set", "path": "agents.disabled", "value": [agent_slug]}],
                expected_revision=config_revision,
                path=agent_config,
            )

        def consume(
            *,
            sync: Barrier = barrier,
            agent_slug: str = slug,
            work_unit: str = unit,
            grant: dict[str, object] = prepared,
            runtime_store: Store = store,
        ) -> dict[str, object]:
            sync.wait()
            return handle_tool_call(
                "agency.load_specialist",
                {
                    "session_id": "session",
                    "trace_id": "trace",
                    "slug": agent_slug,
                    "work_unit_id": work_unit,
                    "activation_token": grant["activation_token"],
                    "worker_id": "worker-race",
                    "native_run_id": "run-race",
                },
                runtime_store,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            disable_future = executor.submit(disable)
            consume_future = executor.submit(consume)
            disable_future.result(timeout=10)
            consumed = consume_future.result(timeout=10)

        connection = store._connect()
        try:
            receipt = connection.execute(
                "SELECT consumed_at FROM delegation_activation_receipts WHERE id = ?",
                (prepared["receipt_id"],),
            ).fetchone()
            evidence = connection.execute(
                "SELECT activation_receipt_id, expired_at FROM specialists_loaded "
                "WHERE session_id = 'session' AND trace_id = 'trace' AND agent_slug = ?",
                (slug,),
            ).fetchall()
        finally:
            connection.close()

        assert receipt is not None
        if "error" in consumed:
            assert "is disabled" in str(consumed["error"])
            assert receipt["consumed_at"] is None
            assert evidence == []
        else:
            assert receipt["consumed_at"] is not None
            assert len(evidence) == 1
            assert evidence[0]["activation_receipt_id"] == prepared["receipt_id"]
            assert evidence[0]["expired_at"] is None
            with pytest.raises(ValueError, match="is disabled; start a fresh Agency preflight"):
                store.get_completion_evidence_snapshot("session", "trace")
            connection = store._connect()
            try:
                expired_at = connection.execute(
                    "SELECT expired_at FROM specialists_loaded WHERE activation_receipt_id = ?",
                    (prepared["receipt_id"],),
                ).fetchone()["expired_at"]
            finally:
                connection.close()
            assert expired_at is not None
        assert store.get_run("trace")["status"] == "specialist_disabled"


@pytest.mark.skip(reason="ADR-0087: needs full inference nomination-delivery flow")
@pytest.mark.parametrize("host", ["codex", "hermes"])
def test_oversized_prompt_is_rejected_for_isolated_and_direct_delivery(
    tmp_path: Path,
    host: str,
) -> None:
    store = Store(tmp_path / f"oversized-{host}.db")
    store._activate_prevalidated_agent(
        dict(next(agent for agent in STARTER_ROSTER if agent["slug"] == "code-reviewer"))
    )
    content = "x" * 7_001
    content_hash = sha256(content.encode()).hexdigest()
    active_version = _active_version(store, "code-reviewer")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET content = ?, hash = ? "
            "WHERE agent_slug = 'code-reviewer' AND version = ?",
            (content, content_hash, active_version),
        )
        conn.execute(
            "UPDATE agent_active SET hash = ? WHERE agent_slug = 'code-reviewer'",
            (content_hash,),
        )
        conn.commit()
    finally:
        conn.close()

    # ADR-0087: configure a provider + stub the invoker so preflight exercises
    # the inference path (and reaches the oversized-content delivery check)
    # instead of declining offline.
    config_path = tmp_path / f"oversized-{host}-config.yaml"
    write_provider_config(config_path)
    os.environ["AGENCY_CONFIG_PATH"] = str(config_path)
    reset_config_cache()
    from agency_runtime.core.workforce import inference as _inference

    original_invoker = _inference.invoke_structured_provider_result
    _inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    try:
        with pytest.raises(RuntimeError, match="exact-delivery ceiling"):
            run_preflight(
                store,
                session_id="session",
                trace_id="trace",
                user_message="Review this code for security and correctness",
                host=host,
                capability_receipt=_capability(host, "session", "trace"),
            )
    finally:
        _inference.invoke_structured_provider_result = original_invoker
        os.environ.pop("AGENCY_CONFIG_PATH", None)
        reset_config_cache()


def test_prepare_rejects_legacy_ready_ref_whose_body_is_now_oversized(tmp_path: Path) -> None:
    store, selected = _isolated_turn(tmp_path / "oversized-ready.db")
    slug = selected[0]
    active_version = _active_version(store, slug)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET content = ? WHERE agent_slug = ? AND version = ?",
            ("x" * 7_001, slug, active_version),
        )
        conn.commit()
    finally:
        conn.close()

    result = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": slug,
            "work_unit_id": _activation_work_unit(store, slug),
        },
        store,
    )
    assert "exact-delivery ceiling" in result["error"]


def test_v18_store_migrates_receipts_and_legacy_execution_identity(tmp_path: Path) -> None:
    path = tmp_path / "legacy-v18.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version VALUES (18);
        CREATE TABLE runs (
            id TEXT PRIMARY KEY, trace_id TEXT NOT NULL UNIQUE, session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown', started_at TEXT NOT NULL,
            ended_at TEXT, status TEXT NOT NULL DEFAULT 'active',
            user_message TEXT, metadata TEXT
        );
        CREATE TABLE delegation_events (
            id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown', work_unit_id TEXT,
            recommended_agent TEXT, status TEXT NOT NULL DEFAULT 'suggested',
            backend TEXT, skip_reason TEXT, error TEXT, started_at TEXT,
            completed_at TEXT
        );
        INSERT INTO runs VALUES (
            'run', 'trace', 'session', 'codex', '2026-07-15T00:00:00+00:00',
            '2026-07-15T00:00:01+00:00', 'completed', '', '{}'
        );
        INSERT INTO delegation_events VALUES (
            'event', 'trace', 'session', 'codex', 'unit-a', 'code-reviewer',
            'delegated', 'spawn_agent', '', '', '2026-07-15T00:00:00+00:00', NULL
        );
        """
    )
    conn.commit()
    conn.close()
    harden_private_test_file(path)

    store = Store(path)
    conn = store._connect()
    try:
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        receipt_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'delegation_activation_receipts'"
        ).fetchone()
        row = conn.execute(
            "SELECT executed_worker_kind, retrieved_specialist_slug, "
            "activation_receipt_id FROM delegation_events WHERE id = 'event'"
        ).fetchone()
    finally:
        conn.close()

    assert version == SCHEMA_VERSION
    assert receipt_table is not None
    assert row["executed_worker_kind"] == "legacy-unverified-worker"
    assert row["retrieved_specialist_slug"] == ""
    assert row["activation_receipt_id"] is None


def test_v19_activation_receipts_migrate_to_unit_scoped_identity() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE runs (trace_id TEXT PRIMARY KEY);
        CREATE TABLE delegation_events (id TEXT PRIMARY KEY);
        CREATE TABLE delegation_activation_receipts (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            work_unit_id TEXT NOT NULL,
            specialist_slug TEXT NOT NULL,
            specialist_version TEXT NOT NULL,
            specialist_prompt_hash TEXT NOT NULL,
            worker_kind TEXT NOT NULL,
            worker_id TEXT NOT NULL DEFAULT '',
            native_run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            consumed_at TEXT,
            delegation_event_id TEXT,
            UNIQUE(trace_id, specialist_slug, specialist_version, specialist_prompt_hash),
            FOREIGN KEY (trace_id) REFERENCES runs(trace_id),
            FOREIGN KEY (delegation_event_id) REFERENCES delegation_events(id)
        );
        CREATE INDEX idx_activation_receipts_trace
        ON delegation_activation_receipts(trace_id, created_at);
        CREATE INDEX idx_activation_receipts_work_unit
        ON delegation_activation_receipts(trace_id, work_unit_id, consumed_at);
        INSERT INTO delegation_activation_receipts VALUES (
            'receipt', 'token', 'session', 'trace', 'unit-a', 'code-reviewer',
            'v1', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'generic-worker', '', '', '2026-07-16T00:00:00+00:00', NULL, NULL
        );
        """
    )

    migrate_delegation_activation_unit_identity(conn)

    row = conn.execute(
        "SELECT id, work_unit_id, specialist_slug FROM delegation_activation_receipts"
    ).fetchone()
    unique_column_sets = {
        tuple(str(column["name"]) for column in conn.execute(f"PRAGMA index_info({index['name']})"))
        for index in conn.execute("PRAGMA index_list(delegation_activation_receipts)")
        if int(index["unique"]) == 1
    }
    assert dict(row) == {
        "id": "receipt",
        "work_unit_id": "unit-a",
        "specialist_slug": "code-reviewer",
    }
    assert (
        "trace_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
    ) in unique_column_sets
    conn.close()


def _prepare_v19_activation_store(path: Path) -> dict[str, object]:
    original = Store(path)
    original.create_run(
        session_id="session-v19",
        trace_id="trace-v19",
        host="codex",
    )
    legacy = {
        "id": "receipt-v19",
        "token_hash": sha256(b"legacy-token").hexdigest(),
        "session_id": "session-v19",
        "trace_id": "trace-v19",
        "work_unit_id": "unit-v19",
        "specialist_slug": "code-reviewer",
        "specialist_version": "v19",
        "specialist_prompt_hash": "a" * 64,
        "worker_kind": "generic-worker",
        "worker_id": "worker-v19",
        "native_run_id": "run-v19",
        "created_at": "2026-07-16T00:00:00+00:00",
        "consumed_at": None,
        "delegation_event_id": None,
    }
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        PRAGMA foreign_keys = OFF;
        DROP TABLE delegation_activation_consumptions;
        DROP TABLE delegation_activation_receipts;
        CREATE TABLE delegation_activation_receipts (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            session_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            work_unit_id TEXT NOT NULL,
            specialist_slug TEXT NOT NULL,
            specialist_version TEXT NOT NULL,
            specialist_prompt_hash TEXT NOT NULL,
            worker_kind TEXT NOT NULL,
            worker_id TEXT NOT NULL DEFAULT '',
            native_run_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            consumed_at TEXT,
            delegation_event_id TEXT,
            UNIQUE(trace_id, specialist_slug, specialist_version, specialist_prompt_hash)
        );
        DELETE FROM schema_version;
        INSERT INTO schema_version VALUES (19);
        """
    )
    conn.execute(
        "INSERT INTO delegation_activation_receipts "
        "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
        "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
        "native_run_id, created_at, consumed_at, delegation_event_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(legacy.values()),
    )
    conn.commit()
    conn.close()
    return legacy


def _read_activation_receipt(path: Path) -> dict[str, object]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, token_hash, grant_id, grant_payload, grant_issued_unix, "
            "grant_expires_unix, child_host, grant_origin, tool_use_id, session_id, "
            "trace_id, work_unit_id, "
            "specialist_slug, specialist_version, specialist_prompt_hash, worker_kind, "
            "worker_id, native_run_id, created_at, consumed_at, delegation_event_id "
            "FROM delegation_activation_receipts"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return dict(row)


def test_store_upgrade_defers_public_grant_index_until_legacy_columns_exist(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-v19-activation.db"
    legacy = _prepare_v19_activation_store(path)

    upgraded = Store(path)
    reopened = Store(path)
    conn = upgraded._connect()
    try:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(delegation_activation_receipts)")
        }
        indexes = {
            str(row["name"])
            for row in conn.execute("PRAGMA index_list(delegation_activation_receipts)")
        }
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        receipt_count = int(
            conn.execute("SELECT COUNT(*) FROM delegation_activation_receipts").fetchone()[0]
        )
    finally:
        conn.close()

    migrated = _read_activation_receipt(path)
    assert {
        "grant_id",
        "grant_payload",
        "grant_issued_unix",
        "grant_expires_unix",
        "grant_origin",
        "tool_use_id",
    } <= columns
    assert "idx_activation_grants_public_id" in indexes
    assert version == SCHEMA_VERSION
    assert receipt_count == 1
    assert migrated == {
        **legacy,
        "grant_id": "",
        "grant_payload": "",
        "grant_issued_unix": 0,
        "grant_expires_unix": 0,
        "child_host": "",
        "grant_origin": "manual_api",
        "tool_use_id": "",
    }
    assert upgraded._current_schema_state() == (True, True)
    assert reopened._current_schema_state() == (True, True)
    assert _read_activation_receipt(path) == migrated


def test_store_upgrade_rolls_back_v19_activation_rebuild_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "legacy-v19-activation-rollback.db"
    legacy = _prepare_v19_activation_store(path)

    monkeypatch.setattr(
        store_schema,
        "create_delegation_activation_consumption_schema",
        lambda _conn: (_ for _ in ()).throw(RuntimeError("injected migration failure")),
    )
    with pytest.raises(RuntimeError, match="injected migration failure"):
        Store(path)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(delegation_activation_receipts)")
        }
        row = conn.execute(
            "SELECT id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at, delegation_event_id "
            "FROM delegation_activation_receipts"
        ).fetchone()
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        consumption_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'delegation_activation_consumptions'"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert dict(row) == legacy
    assert "grant_id" not in columns
    assert version == 19
    assert consumption_table is None


@pytest.mark.parametrize(
    "mutation",
    [
        "ALTER TABLE delegation_activation_receipts "
        "RENAME COLUMN worker_kind TO missing_worker_kind",
        "DROP INDEX idx_activation_receipts_trace",
        "DROP TRIGGER agency_delegation_activation_receipts_insert_activity",
    ],
    ids=["required-column", "required-index", "required-trigger"],
)
def test_v20_readiness_rejects_incomplete_receipt_boundary(
    tmp_path: Path,
    mutation: str,
) -> None:
    store = Store(tmp_path / "incomplete-v20.db")
    assert store._current_schema_state() == (True, True)
    connection = store._connect()
    try:
        connection.execute(mutation)
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)
