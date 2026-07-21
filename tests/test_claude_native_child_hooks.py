"""Claude Code native-child hook correlation and isolation contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.specialist_context import (
    SpecialistPromptReference,
    format_isolated_specialist_context,
)


class _PlanStore:
    def __init__(self, *, open_traces: tuple[str, ...] = ("trace",)) -> None:
        self.open_traces = open_traces
        self.snapshot_reads: list[tuple[str, str]] = []

    def get_open_traces_for_session(self, _session_id: str) -> list[str]:
        return list(self.open_traces)

    def get_completion_evidence_snapshot(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        self.snapshot_reads.append((session_id, trace_id))
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "status": "active",
            "delivery_mode": "isolated",
            "selected_specialists": [
                {"slug": "code-reviewer", "version": "v1", "hash": "a" * 64},
                {"slug": "security-reviewer", "version": "v1", "hash": "b" * 64},
            ],
            "unit_agent_plan": [
                {
                    "work_unit_id": "unit-code",
                    "recommended_agent": "code-reviewer",
                },
                {
                    "work_unit_id": "unit-security",
                    "recommended_agent": "security-reviewer",
                },
            ],
        }


class _RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _agent_payload(
    *,
    event: str = "PreToolUse",
    description: str = "unit-code",
    prompt: str = "Review the implementation.",
    tool_use_id: str = "toolu-code",
) -> dict[str, Any]:
    return {
        "hook_event_name": event,
        "session_id": "claude-session",
        "turn_id": "trace",
        "tool_name": "Agent",
        "tool_use_id": tool_use_id,
        "tool_input": {
            "description": description,
            "prompt": prompt,
            "subagent_type": "general-purpose",
            "model": "sonnet",
        },
    }


def test_pre_tool_use_preserves_native_agent_scheduling_and_appends_child_recipe() -> None:
    store = _PlanStore()
    result = HookBridge("claude", store=store).handle(_agent_payload())  # type: ignore[arg-type]

    output = result["hookSpecificOutput"]
    updated = output["updatedInput"]
    assert output["hookEventName"] == "PreToolUse"
    assert updated["description"] == "unit-code"
    assert updated["subagent_type"] == "general-purpose"
    assert updated["model"] == "sonnet"
    assert updated["prompt"].startswith("Review the implementation.\n\n")
    assert "[AGENCY CHILD PREFLIGHT v1]" in updated["prompt"]
    assert 'parent_session_id="claude-session"' in updated["prompt"]
    assert 'parent_trace_id="trace"' in updated["prompt"]
    assert 'parent_tool_use_id="toolu-code"' in updated["prompt"]
    assert 'work_unit_id="unit-code"' in updated["prompt"]
    assert 'specialist_slug="code-reviewer"' in updated["prompt"]
    assert "secret-specialist-prompt" not in updated["prompt"]
    assert "permissionDecision" not in output
    assert store.snapshot_reads == [("claude-session", "trace")]


def test_pre_tool_use_fails_closed_for_unplanned_or_ambiguous_work() -> None:
    bridge = HookBridge("claude", store=_PlanStore())  # type: ignore[arg-type]
    assert bridge.handle(_agent_payload(description="unit-unplanned")) == {}

    ambiguous = _agent_payload()
    ambiguous.pop("turn_id")
    ambiguous_store = _PlanStore(open_traces=("trace-a", "trace-b"))
    assert HookBridge("claude", store=ambiguous_store).handle(ambiguous) == {}  # type: ignore[arg-type]
    assert ambiguous_store.snapshot_reads == []


def test_pre_tool_use_is_idempotent_and_never_serializes_a_bearer() -> None:
    prompt = "Review.\n\n[AGENCY CHILD PREFLIGHT v1]\nalready attached"
    result = HookBridge("claude", store=_PlanStore()).handle(  # type: ignore[arg-type]
        _agent_payload(prompt=prompt)
    )

    assert result == {}


def test_concurrent_agent_calls_keep_work_unit_recipes_disjoint() -> None:
    bridge = HookBridge("claude", store=_PlanStore())  # type: ignore[arg-type]
    payloads = (
        _agent_payload(description="unit-code", tool_use_id="toolu-code"),
        _agent_payload(description="unit-security", tool_use_id="toolu-security"),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(bridge.handle, payloads))

    prompts = [result["hookSpecificOutput"]["updatedInput"]["prompt"] for result in results]
    assert 'work_unit_id="unit-code"' in prompts[0]
    assert 'specialist_slug="code-reviewer"' in prompts[0]
    assert "security-reviewer" not in prompts[0]
    assert 'work_unit_id="unit-security"' in prompts[1]
    assert 'specialist_slug="security-reviewer"' in prompts[1]
    assert "code-reviewer" not in prompts[1]


def test_subagent_start_injects_only_current_child_lineage() -> None:
    result = HookBridge("claude", store=_PlanStore()).handle(  # type: ignore[arg-type]
        {
            "hook_event_name": "SubagentStart",
            "session_id": "claude-session",
            "agent_id": "agent-42",
            "agent_type": "general-purpose",
        }
    )

    output = result["hookSpecificOutput"]
    context = output["additionalContext"]
    assert output["hookEventName"] == "SubagentStart"
    assert "[AGENCY NATIVE CHILD IDENTITY v1]" in context
    assert 'worker_kind="generic-worker"' in context
    assert 'worker_id="agent-42"' in context
    assert 'native_run_id="claude-agent:agent-42"' in context
    assert "code-reviewer" not in context
    assert "activation_token" not in context
    assert 'parent_session_id="claude-session"' in context
    assert 'parent_trace_id="trace"' in context
    assert "shared parent budget, cache, and singleflight" in context


def test_subagent_start_omits_both_parent_ids_when_trace_is_ambiguous() -> None:
    store = _PlanStore(open_traces=("trace-a", "trace-b"))
    payload = {
        "hook_event_name": "SubagentStart",
        "session_id": "session",
        "agent_id": "agent-42",
        "agent_type": "general-purpose",
    }

    for host in ("claude", "codex"):
        context = HookBridge(host, store=store).handle(payload)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "Parent correlation is unavailable" in context
        assert "parent_session_id=" not in context
        assert "parent_trace_id=" not in context


def test_subagent_stop_does_not_guess_parent_work_unit_correlation() -> None:
    store = _PlanStore()
    result = HookBridge("claude", store=store).handle(  # type: ignore[arg-type]
        {
            "hook_event_name": "SubagentStop",
            "session_id": "claude-session",
            "agent_id": "agent-42",
            "agent_type": "general-purpose",
        }
    )

    assert result == {}
    assert store.snapshot_reads == []


def test_codex_subagent_lifecycle_injects_exact_identity_and_child_owned_fallback() -> None:
    class LifecycleStore(_PlanStore):
        def __init__(self) -> None:
            super().__init__()
            self.started: list[dict[str, str]] = []
            self.stopped: list[dict[str, str]] = []

        def record_native_child_started(self, **kwargs: str) -> None:
            self.started.append(kwargs)

        def record_native_child_stopped(self, **kwargs: str) -> None:
            self.stopped.append(kwargs)

    store = LifecycleStore()
    bridge = HookBridge("codex", store=store)  # type: ignore[arg-type]
    start = bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "codex-session",
            "agent_id": "agent-42",
            "agent_type": "worker",
        }
    )

    context = start["hookSpecificOutput"]["additionalContext"]
    assert 'worker_id="agent-42"' in context
    assert 'native_run_id="codex-agent:agent-42"' in context
    assert "complete delegated assignment" in context
    assert 'session_id="codex-child:agent-42"' in context
    assert "does not load, select, or inherit" in context
    assert store.started == [
        {
            "host": "codex",
            "backend": "spawn_agent",
            "session_id": "codex-session",
            "trace_id": "trace",
            "work_unit_id": "",
            "worker_id": "agent-42",
            "native_run_id": "codex-agent:agent-42",
        }
    ]

    assert (
        bridge.handle(
            {
                "hook_event_name": "SubagentStop",
                "session_id": "codex-session",
                "agent_id": "agent-42",
                "agent_type": "worker",
            }
        )
        == {}
    )
    assert store.stopped == store.started


def test_post_tool_use_reconciles_exact_plan_lineage_and_host_model() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    payload = _agent_payload(event="PostToolUse")
    payload["tool_response"] = {
        "agentId": "agent-42",
        "resolvedModel": "claude-sonnet-5",
        "status": "completed",
    }

    result = HookBridge("claude", store=store, adapter=adapter).handle(payload)  # type: ignore[arg-type]

    assert result == {}
    [call] = adapter.calls
    assert call["tool_name"] == "delegate_task"
    assert call["trace_id"] == "trace"
    assert call["args"]["work_unit_id"] == "unit-code"
    assert call["args"]["agent"] == "code-reviewer"
    assert call["args"]["requested_model"] == "sonnet"
    assert call["args"]["resolved_model"] == "claude-sonnet-5"
    assert call["result"]["agent_id"] == "agent-42"
    assert call["result"]["native_run_id"] == "claude-agent:agent-42"


def test_post_tool_use_never_promotes_requested_model_or_unplanned_label() -> None:
    adapter = _RecordingAdapter()
    payload = _agent_payload(event="PostToolUse", description="unit-unplanned")
    payload["tool_response"] = {"agentId": "agent-9", "status": "completed"}

    HookBridge("claude", store=_PlanStore(), adapter=adapter).handle(payload)  # type: ignore[arg-type]

    [call] = adapter.calls
    assert call["args"]["work_unit_id"] == ""
    assert call["args"]["requested_model"] == "sonnet"
    assert call["args"]["resolved_model"] == "unavailable"
    assert call["result"]["native_run_id"] == "claude-agent:agent-9"


def test_post_tool_use_without_an_exact_open_turn_records_nothing() -> None:
    adapter = _RecordingAdapter()
    payload = _agent_payload(event="PostToolUse")
    payload.pop("turn_id")
    payload["tool_response"] = {"agentId": "agent-9", "status": "completed"}

    result = HookBridge(
        "claude",
        store=_PlanStore(open_traces=("trace-a", "trace-b")),
        adapter=adapter,
    ).handle(payload)  # type: ignore[arg-type]

    assert result == {}
    assert adapter.calls == []


def test_claude_parent_guidance_defers_prepare_and_load_to_the_native_child() -> None:
    reference = SpecialistPromptReference(
        slug="code-reviewer",
        version="v1",
        content_hash="a" * 64,
        description="Review code",
        capabilities=("review",),
    )

    context = format_isolated_specialist_context(
        [reference],
        host="claude",
        session_id="claude-session",
        trace_id="trace",
        nontrivial=True,
    )

    assert "Do not call `agency.prepare_delegation` in the parent" in context
    assert "do not place an activation token in the Agent prompt" in context
    assert "PreToolUse and SubagentStart hooks" in context
    assert "Inside the child only" in context
    assert "code-reviewer => work_unit_id=specialist:code-reviewer" in context


def test_codex_parent_guidance_keeps_parent_preparation_contract() -> None:
    reference = SpecialistPromptReference(
        slug="code-reviewer",
        version="v1",
        content_hash="a" * 64,
        description="Review code",
        capabilities=("review",),
    )

    context = format_isolated_specialist_context(
        [reference],
        host="codex",
        session_id="codex-session",
        trace_id="trace",
        nontrivial=True,
    )

    assert "In the parent, call `agency.prepare_delegation`" in context
    assert "returned `activation_token` only to its isolated child" in context
    assert "PreToolUse and SubagentStart hooks" not in context
