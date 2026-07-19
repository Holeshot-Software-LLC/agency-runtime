"""Prompt contracts keep specialist context scoped to one current turn."""

from pathlib import Path

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_KERNEL
from agency_runtime.core.runtime_control import RuntimeControlSnapshot
from agency_runtime.core.selector.pipeline import HEADER_INSTRUCTION
from agency_runtime.core.specialist_context import _format_loaded_context
from agency_runtime.core.store import resident_binding as resident_binding_store
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _stable_materialized_master_control(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        resident_binding_store,
        "read_effective_runtime_control_snapshot",
        lambda **_kwargs: RuntimeControlSnapshot(
            schema_version=1,
            enabled=True,
            generation=0,
            updated_at="2026-07-17T00:00:00Z",
            source="test",
            materialized=True,
        ),
    )


def test_loaded_context_declares_complete_current_turn_capsule() -> None:
    context = _format_loaded_context(
        [
            {
                "agent_slug": "code-reviewer",
                "description": "Reviews code.",
                "prompt_body": "Inspect correctness.",
            }
        ]
    )

    assert "[AGENCY LOADED] Complete current-turn specialist instruction capsule:" in context
    assert (
        "Earlier Agency specialist capsules are expired and are not applied "
        "unless the specialist is repeated below."
    ) in context
    assert "code-reviewer" in context


def test_header_instruction_reuses_current_capsule_before_loading_more() -> None:
    assert (
        "Treat the current [AGENCY LOADED] capsule as the authoritative "
        "specialist context for this turn."
    ) in HEADER_INSTRUCTION
    assert (
        "Only use the host's installed Agency specialist tools "
        "(`agency.search_agents` and `agency.load_specialist` on MCP surfaces) when "
        "the current capsule is absent or additional expertise is materially needed."
    ) in HEADER_INSTRUCTION
    assert "agency_agents_search" not in HEADER_INSTRUCTION


def test_persistent_host_turns_never_inject_specialist_bodies_into_parent_history(
    tmp_path: Path,
) -> None:
    host = "claude"
    store = Store(tmp_path / f"{host}.db")
    store.set_host_control(
        host,
        enabled=False,
        expected_generation=0,
        source="test-materialize",
    )
    store.set_host_control(
        host,
        enabled=True,
        expected_generation=1,
        source="test-materialize",
    )
    bridge = HookBridge(host, store=store)
    session_id = f"{host}-long-session"

    first = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": "turn-one",
            "prompt": "Review the authentication and security implementation.",
        }
    )
    first_context = first["hookSpecificOutput"]["additionalContext"]
    connection = store._connect()
    try:
        prompt_bodies = [
            str(row["content"])
            for row in connection.execute(
                "SELECT content FROM agent_versions ORDER BY agent_slug, version"
            ).fetchall()
            if str(row["content"] or "").strip()
        ]
    finally:
        connection.close()
    assert store.acknowledge_resident_manager_binding(
        session_id=session_id,
        host=host,
        trace_id="turn-one",
        binding=store.get_completion_evidence_snapshot(session_id, "turn-one")[
            "resident_manager_binding"
        ],
    )

    second = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": session_id,
            "turn_id": "turn-two",
            "prompt": "Document the operator workflow and release checks.",
        }
    )
    second_context = second["hookSpecificOutput"]["additionalContext"]

    assert first_context.startswith(RESIDENT_MANAGER_KERNEL)
    assert "delivery=injected" in first_context
    assert "[AGENCY PREFLIGHT] Current isolated turn turn-one" in first_context
    assert second_context.startswith("[Agency resident managers active")
    assert "delivery=reused" in second_context
    assert RESIDENT_MANAGER_KERNEL not in second_context
    assert "[AGENCY PREFLIGHT] Current isolated turn turn-two" in second_context
    assert len(first_context) <= 4_096
    assert len(second_context) <= 4_096
    assert all(body not in first_context for body in prompt_bodies)
    assert all(body not in second_context for body in prompt_bodies)
    assert store.get_specialists_for_trace(session_id, "turn-one") == []
    assert store.get_specialists_for_trace(session_id, "turn-two") == []


@pytest.mark.parametrize("host", ["codex"])
def test_request_scoped_hosts_receive_a_fresh_bounded_manager_kernel(
    host: str,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / f"{host}.db")
    bridge = HookBridge(host, store=store)
    session_id = f"{host}-request-session"

    contexts = [
        bridge.handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "turn_id": f"turn-{number}",
                "prompt": "Review the authentication architecture.",
            }
        )["hookSpecificOutput"]["additionalContext"]
        for number in (1, 2)
    ]

    assert all(context.startswith(RESIDENT_MANAGER_KERNEL) for context in contexts)
    assert all("delivery=request" in context for context in contexts)
    connection = store._connect()
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM resident_manager_bindings").fetchone()[0] == 0
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    ("adapter_type", "method_name"),
    [
        (OpenClawAdapter, "on_message_received"),
        (HermesAdapter, "pre_llm_call_handler"),
    ],
)
def test_real_request_scoped_adapter_entrypoints_remain_row_free(
    adapter_type: type[OpenClawAdapter] | type[HermesAdapter],
    method_name: str,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / f"{adapter_type.host_name}.db")
    adapter = adapter_type(store=store)
    method = getattr(adapter, method_name)

    contexts = [
        method(
            f"{adapter_type.host_name}-session",
            "Review the authentication architecture.",
            trace_id=f"turn-{number}",
        )["context"]
        for number in (1, 2)
    ]

    assert all(context.startswith(RESIDENT_MANAGER_KERNEL) for context in contexts)
    assert all("delivery=request" in context for context in contexts)
    connection = store._connect()
    try:
        assert (
            connection.execute("SELECT COUNT(*) FROM resident_manager_bindings").fetchone()[0] == 0
        )
    finally:
        connection.close()
