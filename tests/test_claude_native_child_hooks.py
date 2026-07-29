"""Claude Code native-child hook correlation and isolation contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Lock
from typing import Any

import pytest

import agency_runtime.adapters.hooks as hooks
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.native_child_prompt_delivery import (
    parse_native_child_prompt_delivery,
    render_native_child_prompt_delivery,
)
from agency_runtime.core.specialist_context import (
    SpecialistPromptReference,
    format_isolated_specialist_context,
)
from agency_runtime.core.unit_assignment import work_unit_goal_hash


class _PlanStore:
    def __init__(self, *, open_traces: tuple[str, ...] = ("trace",)) -> None:
        self.open_traces = open_traces
        self.snapshot_reads: list[tuple[str, str]] = []
        self.prompts = {
            "code-reviewer": "You are the exact code review specialist.",
            "security-reviewer": "You are the exact security review specialist.",
        }
        self.hashes = {
            slug: sha256(prompt.encode()).hexdigest() for slug, prompt in self.prompts.items()
        }
        self.goals = {
            "unit-code": "Review the implementation.",
            "unit-security": "Audit the implementation security.",
        }
        self.prepared: list[dict[str, Any]] = []
        self.consumed: list[dict[str, Any]] = []
        self.parent_scopes: list[dict[str, Any]] = []
        self._lineage: dict[tuple[str, str], dict[str, str]] = {}
        self._lock = Lock()

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
                {
                    "slug": "code-reviewer",
                    "version": "v1",
                    "hash": self.hashes["code-reviewer"],
                },
                {
                    "slug": "security-reviewer",
                    "version": "v1",
                    "hash": self.hashes["security-reviewer"],
                },
            ],
            "unit_agent_plan": [
                {
                    "work_unit_id": "unit-code",
                    "recommended_agent": "code-reviewer",
                    "goal_hash": work_unit_goal_hash(self.goals["unit-code"]),
                    "mutation_scope": "read_only",
                    "resource_hashes": [sha256(b"repository-workspace").hexdigest()],
                    "required_evidence": [],
                },
                {
                    "work_unit_id": "unit-security",
                    "recommended_agent": "security-reviewer",
                    "goal_hash": work_unit_goal_hash(self.goals["unit-security"]),
                    "mutation_scope": "read_only",
                    "resource_hashes": [sha256(b"repository-workspace").hexdigest()],
                    "required_evidence": [],
                },
            ],
        }

    def get_versioned_specialist_prompt(
        self,
        slug: str,
        version: str,
        content_hash: str,
        *,
        max_chars: int,
    ) -> dict[str, Any] | None:
        prompt = self.prompts.get(slug)
        if prompt is None or version != "v1" or self.hashes[slug] != content_hash:
            return None
        return {
            "slug": slug,
            "version": version,
            "hash": content_hash,
            "prompt_body": prompt[:max_chars],
            "prompt_truncated": len(prompt) > max_chars,
        }

    def prepare_delegation_activation(self, **kwargs: Any) -> dict[str, Any]:
        with self._lock:
            token = f"token-{len(self.prepared)}-{kwargs['specialist_slug']}"
            row = {**kwargs, "activation_token": token}
            self.prepared.append(row)
        slug = str(kwargs["specialist_slug"])
        return {
            "activation_token": token,
            "version": "v1",
            "prompt_hash": self.hashes[slug],
        }

    def verify_pending_delegation_activation(self, **kwargs: Any) -> bool:
        with self._lock:
            matches = [
                row
                for row in self.prepared
                if row["activation_token"] == kwargs["activation_token"]
                and row["session_id"] == kwargs["session_id"]
                and row["trace_id"] == kwargs["trace_id"]
                and row["work_unit_id"] == kwargs["work_unit_id"]
                and row["specialist_slug"] == kwargs["specialist_slug"]
                and row["grant_origin"] == kwargs["grant_origin"]
                and row["tool_use_id"] == kwargs["tool_use_id"]
                and not any(
                    consumed["activation_token"] == row["activation_token"]
                    for consumed in self.consumed
                )
            ]
        return (
            len(matches) == 1
            and kwargs["host"] in {"codex", "claude", "zcode"}
            and kwargs["specialist_version"] == "v1"
            and kwargs["specialist_prompt_hash"] == self.hashes[str(kwargs["specialist_slug"])]
        )

    def consume_delegation_activation(self, **kwargs: Any) -> dict[str, Any]:
        token = str(kwargs["activation_token"])
        native_hook_tool_use_id = str(kwargs.get("native_hook_tool_use_id") or "")
        with self._lock:
            if any(
                row["activation_token"] == token
                and str(row.get("native_hook_tool_use_id") or "") == native_hook_tool_use_id
                for row in self.consumed
            ):
                raise ValueError("already consumed")
            matches = [
                row
                for row in self.prepared
                if (
                    row["activation_token"] == token
                    if token
                    else row.get("grant_origin") == "native_hook"
                    and row.get("tool_use_id") == native_hook_tool_use_id
                )
            ]
            if len(matches) != 1:
                raise ValueError("activation grant is unavailable or ambiguous")
            prepared = matches[0]
            slug = str(prepared["specialist_slug"])
            row = {
                **kwargs,
                "activation_token": token,
                "slug": slug,
                "version": "v1",
                "prompt_hash": self.hashes[slug],
                "prompt_body": self.prompts[slug],
                "worker_kind": "generic-worker",
            }
            self.consumed.append(row)
            self._lineage[(str(kwargs["work_unit_id"]), slug)] = {
                "worker_kind": "generic-worker",
                "worker_id": str(kwargs["worker_id"]),
                "native_run_id": str(kwargs["native_run_id"]),
            }
            return row

    def get_consumed_delegation_lineage(self, **kwargs: Any) -> dict[str, str] | None:
        return self._lineage.get((str(kwargs["work_unit_id"]), str(kwargs["specialist_slug"])))

    def create_native_child_parent_scope(self, **kwargs: Any) -> dict[str, Any]:
        receipt = {
            **kwargs,
            "parent_scope_token": f"parent-scope-{len(self.parent_scopes)}",
        }
        self.parent_scopes.append(receipt)
        return receipt


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


def _zcode_agent_payload(
    *,
    event: str = "PreToolUse",
    prompt: str = "Review the implementation.",
) -> dict[str, Any]:
    """Return the documented ZCode 3.5 Agent hook envelope."""

    return {
        "hook_event_name": event,
        "session_id": "zcode-session",
        "turn_id": "trace",
        "tool_name": "Agent",
        "tool_use_id": "toolu-code",
        "tool_input": {
            "description": "unit-code",
            "prompt": prompt,
            "subagent_type": "general-purpose",
            "model": "sonnet",
        },
    }


def test_pre_tool_use_preserves_native_scheduling_and_injects_exact_prompt() -> None:
    store = _PlanStore()
    result = HookBridge("claude", store=store).handle(_agent_payload())  # type: ignore[arg-type]

    output = result["hookSpecificOutput"]
    updated = output["updatedInput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "allow"
    assert updated["description"] == "unit-code"
    assert updated["subagent_type"] == "general-purpose"
    assert updated["model"] == "sonnet"
    assert updated["prompt"].startswith("Review the implementation.\n\n")
    assert "[AGENCY EXACT SPECIALIST ACTIVATION v1]" in updated["prompt"]
    assert store.prompts["code-reviewer"] in updated["prompt"]
    delivery = parse_native_child_prompt_delivery(updated["prompt"])
    assert delivery is not None
    assert delivery.parent_session_id == "claude-session"
    assert delivery.parent_trace_id == "trace"
    assert delivery.tool_use_id == "toolu-code"
    assert delivery.work_unit_id == "unit-code"
    assert delivery.specialist_slug == "code-reviewer"
    assert delivery.prompt_body == store.prompts["code-reviewer"]
    assert store.prepared[0]["grant_origin"] == "native_hook"
    assert store.prepared[0]["tool_use_id"] == "toolu-code"
    assert store.snapshot_reads == [("claude-session", "trace")]


def test_pre_tool_use_fails_closed_for_unplanned_or_ambiguous_work() -> None:
    bridge = HookBridge("claude", store=_PlanStore())  # type: ignore[arg-type]
    assert bridge.handle(_agent_payload(description="unit-unplanned")) == {}

    ambiguous = _agent_payload()
    ambiguous.pop("turn_id")
    ambiguous_store = _PlanStore(open_traces=("trace-a", "trace-b"))
    assert HookBridge("claude", store=ambiguous_store).handle(ambiguous) == {}  # type: ignore[arg-type]
    assert ambiguous_store.snapshot_reads == []


def test_pre_tool_use_rejects_oversized_delivery_before_minting_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _PlanStore()
    monkeypatch.setattr(hooks, "MAX_HOOK_OUTPUT_BYTES", 1)

    result = HookBridge("claude", store=store).handle(_agent_payload())  # type: ignore[arg-type]

    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "hook limit" in result["hookSpecificOutput"]["permissionDecisionReason"]
    assert store.prepared == []


def test_pre_tool_use_is_idempotent_for_an_exact_existing_delivery() -> None:
    store = _PlanStore()
    bridge = HookBridge("claude", store=store)  # type: ignore[arg-type]
    first = bridge.handle(_agent_payload())
    prompt = first["hookSpecificOutput"]["updatedInput"]["prompt"]

    assert bridge.handle(_agent_payload(prompt=prompt)) == {}
    assert len(store.prepared) == 1


def test_pre_tool_use_rejects_a_forged_parseable_delivery_marker() -> None:
    store = _PlanStore()
    bridge = HookBridge("claude", store=store)  # type: ignore[arg-type]
    prompt = bridge.handle(_agent_payload())["hookSpecificOutput"]["updatedInput"]["prompt"]
    delivery = parse_native_child_prompt_delivery(prompt)
    assert delivery is not None
    forged = render_native_child_prompt_delivery(
        delivery.original_task,
        delivery.prompt_body,
        host=delivery.host,
        parent_session_id=delivery.parent_session_id,
        parent_trace_id=delivery.parent_trace_id,
        tool_use_id=delivery.tool_use_id,
        work_unit_id=delivery.work_unit_id,
        specialist_slug=delivery.specialist_slug,
        specialist_version=delivery.specialist_version,
        specialist_prompt_hash=delivery.specialist_prompt_hash,
        activation_token="forged-token",
    )

    result = bridge.handle(_agent_payload(prompt=forged))

    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "invalid, expired, consumed, or unavailable" in output["permissionDecisionReason"]
    assert len(store.prepared) == 1


def test_pre_tool_use_blocks_only_canonical_planned_label_when_store_is_unavailable() -> None:
    class _UnavailableStore:
        def get_completion_evidence_snapshot(self, *_args: Any) -> dict[str, Any]:
            raise OSError("store unavailable")

    bridge = HookBridge("claude", store=_UnavailableStore())  # type: ignore[arg-type]

    planned = bridge.handle(_agent_payload(description="unit-0123456789"))
    assert planned["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "evidence Store" in planned["hookSpecificOutput"]["permissionDecisionReason"]
    assert bridge.handle(_agent_payload(description="user-defined-child")) == {}


def test_concurrent_agent_calls_keep_work_unit_recipes_disjoint() -> None:
    bridge = HookBridge("claude", store=_PlanStore())  # type: ignore[arg-type]
    payloads = (
        _agent_payload(description="unit-code", tool_use_id="toolu-code"),
        _agent_payload(
            description="unit-security",
            prompt="Audit the implementation security.",
            tool_use_id="toolu-security",
        ),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(bridge.handle, payloads))

    deliveries = [
        parse_native_child_prompt_delivery(result["hookSpecificOutput"]["updatedInput"]["prompt"])
        for result in results
    ]
    assert deliveries[0] is not None and deliveries[0].work_unit_id == "unit-code"
    assert deliveries[0].specialist_slug == "code-reviewer"
    assert deliveries[1] is not None and deliveries[1].work_unit_id == "unit-security"
    assert deliveries[1].specialist_slug == "security-reviewer"


def test_pre_tool_use_rejects_a_planned_label_with_the_wrong_goal() -> None:
    store = _PlanStore()

    result = HookBridge("claude", store=store).handle(  # type: ignore[arg-type]
        _agent_payload(prompt="Audit an unrelated deployment.")
    )

    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "does not exactly match" in output["permissionDecisionReason"]
    assert store.prepared == []


def test_claude_post_tool_consumes_exact_delivery_with_host_child_identity() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("claude", store=store, adapter=adapter)  # type: ignore[arg-type]
    preflight = bridge.handle(_agent_payload())
    updated_input = preflight["hookSpecificOutput"]["updatedInput"]
    post = _agent_payload(event="PostToolUse")
    post["tool_input"] = updated_input
    post["tool_response"] = {
        "agentId": "agent-42",
        "resolvedModel": "claude-sonnet-5",
        "status": "completed",
    }

    assert bridge.handle(post) == {}
    [consumed] = store.consumed
    assert consumed["specialist_slug"] == "code-reviewer"
    assert consumed["work_unit_id"] == "unit-code"
    assert consumed["worker_id"] == "agent-42"
    assert consumed["native_run_id"] == "claude-agent:agent-42"
    [call] = adapter.calls
    assert call["args"]["agent"] == "code-reviewer"
    assert call["args"]["work_unit_id"] == "unit-code"
    assert call["args"]["goal"] == "Review the implementation."

    # A replay sees the same immutable lineage and does not create a second
    # activation consumption.
    assert bridge.handle(post) == {}
    assert len(store.consumed) == 1


def test_zcode_35_pre_and_post_hooks_consume_exact_planned_activation() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("zcode", store=store, adapter=adapter)  # type: ignore[arg-type]

    pre = bridge.handle(_zcode_agent_payload())
    output = pre["hookSpecificOutput"]
    updated_input = output["updatedInput"]
    delivery = parse_native_child_prompt_delivery(updated_input["prompt"])

    assert output["permissionDecision"] == "allow"
    assert delivery is not None
    assert delivery.host == "zcode"
    assert delivery.parent_session_id == "zcode-session"
    assert delivery.work_unit_id == "unit-code"
    assert "message" not in updated_input

    post = _zcode_agent_payload(event="PostToolUse")
    post["tool_input"] = updated_input
    post["tool_response"] = {
        "agentId": "agent-42",
        "resolvedModel": "zcode-sonnet",
        "status": "completed",
    }

    assert bridge.handle(post) == {}
    [consumed] = store.consumed
    assert consumed["specialist_slug"] == "code-reviewer"
    assert consumed["work_unit_id"] == "unit-code"
    assert consumed["worker_id"] == "agent-42"
    assert consumed["native_run_id"] == "zcode-agent:agent-42"
    [call] = adapter.calls
    assert call["tool_name"] == "delegate_task"
    assert call["args"]["agent"] == "code-reviewer"
    assert call["args"]["work_unit_id"] == "unit-code"
    assert call["args"]["goal"] == "Review the implementation."
    assert call["result"]["native_run_id"] == "zcode-agent:agent-42"


def test_zcode_35_failed_agent_hook_records_no_invented_child_lineage() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("zcode", store=store, adapter=adapter)  # type: ignore[arg-type]
    updated_input = bridge.handle(_zcode_agent_payload())["hookSpecificOutput"]["updatedInput"]
    failure = _zcode_agent_payload(event="PostToolUseFailure")
    failure["tool_input"] = updated_input
    failure["error"] = "native Agent launch failed"
    failure["is_interrupt"] = False

    assert bridge.handle(failure) == {}
    assert store.consumed == []
    [call] = adapter.calls
    assert call["tool_name"] == "delegate_task"
    assert call["args"]["agent"] == "code-reviewer"
    assert call["args"]["work_unit_id"] == "unit-code"
    assert call["result"] == {
        "status": "failed",
        "error": "native Agent launch failed",
        "is_interrupt": False,
    }
    assert "agent_id" not in call["result"]
    assert "native_run_id" not in call["result"]


def test_post_tool_rejects_a_delivery_rebound_to_a_different_goal() -> None:
    store = _PlanStore()
    bridge = HookBridge("claude", store=store, adapter=_RecordingAdapter())  # type: ignore[arg-type]
    payload = _agent_payload()
    updated_input = bridge.handle(payload)["hookSpecificOutput"]["updatedInput"]
    delivery = parse_native_child_prompt_delivery(updated_input["prompt"])
    assert delivery is not None
    updated_input["prompt"] = render_native_child_prompt_delivery(
        "Audit an unrelated deployment.",
        delivery.prompt_body,
        host=delivery.host,
        parent_session_id=delivery.parent_session_id,
        parent_trace_id=delivery.parent_trace_id,
        tool_use_id=delivery.tool_use_id,
        work_unit_id=delivery.work_unit_id,
        specialist_slug=delivery.specialist_slug,
        specialist_version=delivery.specialist_version,
        specialist_prompt_hash=delivery.specialist_prompt_hash,
        activation_token=delivery.activation_token,
    )

    bridge.handle(
        {
            **payload,
            "hook_event_name": "PostToolUse",
            "tool_input": updated_input,
            "tool_response": {"agentId": "agent-42", "status": "completed"},
        }
    )

    assert store.consumed == []


def test_codex_pre_and_post_hooks_deliver_exact_specialist_without_child_mcp_calls() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("codex", store=store, adapter=adapter)  # type: ignore[arg-type]
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "codex-session",
        "turn_id": "trace",
        "tool_name": "spawn_agent",
        "tool_use_id": "call-code",
        "tool_input": {
            "task_name": codex_task_name_for_work_unit("unit-code"),
            "message": "Review the implementation.",
            "agent_type": "worker",
        },
    }

    preflight = bridge.handle(payload)
    output = preflight["hookSpecificOutput"]
    assert output["permissionDecision"] == "allow"
    delivery = parse_native_child_prompt_delivery(output["updatedInput"]["message"])
    assert delivery is not None
    assert delivery.specialist_slug == "code-reviewer"
    assert delivery.prompt_body == store.prompts["code-reviewer"]

    post = {
        **payload,
        "hook_event_name": "PostToolUse",
        "tool_input": output["updatedInput"],
        "tool_response": {"agent_id": "agent-77", "status": "accepted"},
    }
    assert bridge.handle(post) == {}
    [consumed] = store.consumed
    assert consumed["worker_id"] == "agent-77"
    assert consumed["native_run_id"] == "codex-agent:agent-77"
    [call] = adapter.calls
    assert call["args"]["agent"] == "code-reviewer"
    assert call["args"]["work_unit_id"] == "unit-code"
    assert call["args"]["goal"] == "Review the implementation."


def test_codex_v2_task_path_is_authoritative_native_child_identity() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("codex", store=store, adapter=adapter)  # type: ignore[arg-type]
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "codex-session",
        "turn_id": "trace",
        "tool_name": "spawn_agent",
        "tool_use_id": "call-code",
        "tool_input": {
            "task_name": codex_task_name_for_work_unit("unit-code"),
            "message": "Review the implementation.",
        },
    }
    updated = bridge.handle(payload)["hookSpecificOutput"]["updatedInput"]
    post = {
        **payload,
        "hook_event_name": "PostToolUse",
        "tool_input": updated,
        "tool_response": {
            "task_name": f"/root/{payload['tool_input']['task_name']}",
            "status": "accepted",
        },
    }

    assert bridge.handle(post) == {}
    [consumed] = store.consumed
    expected_task = str(payload["tool_input"]["task_name"])
    assert consumed["worker_id"] == f"task:{expected_task}"
    assert consumed["native_run_id"] == f"codex-task:{expected_task}"


def test_codex_v1_spawn_resolves_unique_plan_row_from_exact_message_goal() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("codex", store=store, adapter=adapter)  # type: ignore[arg-type]
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "codex-session",
        "turn_id": "trace",
        "tool_name": "spawn_agent",
        "tool_use_id": "call-code-v1",
        "tool_input": {
            "message": "Review the implementation.",
            "agent_type": "worker",
        },
    }

    output = bridge.handle(payload)["hookSpecificOutput"]
    assert output["permissionDecision"] == "allow"
    delivery = parse_native_child_prompt_delivery(output["updatedInput"]["message"])
    assert delivery is not None
    assert delivery.work_unit_id == "unit-code"
    assert delivery.specialist_slug == "code-reviewer"

    assert (
        bridge.handle(
            {
                **payload,
                "hook_event_name": "PostToolUse",
                "tool_input": output["updatedInput"],
                "tool_response": {"agent_id": "agent-v1", "status": "accepted"},
            }
        )
        == {}
    )
    [consumed] = store.consumed
    assert consumed["work_unit_id"] == "unit-code"
    assert consumed["worker_id"] == "agent-v1"


def test_codex_v1_spawn_leaves_ambiguous_goal_hash_to_native_scheduler() -> None:
    store = _PlanStore()
    store.goals["unit-security"] = store.goals["unit-code"]
    result = HookBridge("codex", store=store).handle(  # type: ignore[arg-type]
        {
            "hook_event_name": "PreToolUse",
            "session_id": "codex-session",
            "turn_id": "trace",
            "tool_name": "spawn_agent",
            "tool_use_id": "call-ambiguous-v1",
            "tool_input": {"message": "Review the implementation."},
        }
    )

    assert result == {}
    assert store.prepared == []


def test_codex_v1_spawn_leaves_unmatched_goal_to_native_scheduler() -> None:
    store = _PlanStore()
    result = HookBridge("codex", store=store).handle(  # type: ignore[arg-type]
        {
            "hook_event_name": "PreToolUse",
            "session_id": "codex-session",
            "turn_id": "trace",
            "tool_name": "spawn_agent",
            "tool_use_id": "call-unmatched-v1",
            "tool_input": {"message": "Perform unrelated work."},
        }
    )

    assert result == {}
    assert store.prepared == []


def test_planned_child_is_blocked_when_exact_prompt_cannot_be_verified() -> None:
    store = _PlanStore()
    store.prompts.clear()

    result = HookBridge("claude", store=store).handle(_agent_payload())  # type: ignore[arg-type]

    output = result["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "exact selected prompt version" in output["permissionDecisionReason"]
    assert store.prepared == []


def test_subagent_start_injects_only_current_child_lineage() -> None:
    store = _PlanStore()
    result = HookBridge("claude", store=store).handle(  # type: ignore[arg-type]
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
    assert 'session_id="claude-child:agent-42"' in context
    assert 'parent_scope_token="parent-scope-0"' in context
    assert "parent_session_id or parent_trace_id" in context
    assert "parent budget, cache, and singleflight" in context
    assert store.parent_scopes[0]["parent_session_id"] == "claude-session"
    assert store.parent_scopes[0]["parent_trace_id"] == "trace"


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
        assert "parent-scope receipt is unavailable" in context
        assert "parent_session_id=" not in context
        assert "parent_trace_id=" not in context
        assert "parent_scope_token=" not in context


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
    assert 'parent_scope_token="parent-scope-0"' in context
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


def test_codex_opaque_canary_delivery_is_terminal_parseable_child_context() -> None:
    from agency_runtime.core.activation_canary_contract import (
        CODEX_ACTIVATION_CANARY_WORK_UNIT,
    )

    class OpaqueCanaryStore(_PlanStore):
        def __init__(self) -> None:
            super().__init__()
            self.goals["unit-code"] = CODEX_ACTIVATION_CANARY_WORK_UNIT

        def get_pending_native_hook_delivery(self, **_kwargs: Any) -> dict[str, str]:
            prepared = self.prepared[0]
            return {
                "session_id": str(prepared["session_id"]),
                "trace_id": str(prepared["trace_id"]),
                "tool_use_id": str(prepared["tool_use_id"]),
                "work_unit_id": str(prepared["work_unit_id"]),
                "slug": "code-reviewer",
                "version": "v1",
                "prompt_hash": self.hashes["code-reviewer"],
                "prompt_body": self.prompts["code-reviewer"],
            }

    store = OpaqueCanaryStore()
    bridge = HookBridge("codex", store=store)  # type: ignore[arg-type]
    pre = bridge.handle(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "codex-session",
            "turn_id": "trace",
            "tool_name": "collaborationspawn_agent",
            "tool_use_id": "call-canary",
            "tool_input": {
                "fork_turns": "none",
                "task_name": codex_task_name_for_work_unit("unit-code"),
                "message": "gAAAAA" + "opaque-canary-ciphertext" * 2,
            },
        }
    )
    assert "updatedInput" not in pre["hookSpecificOutput"]

    started = bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "codex-session",
            "agent_id": "agent-canary",
            "agent_type": "worker",
        }
    )
    context = started["hookSpecificOutput"]["additionalContext"]
    delivery = parse_native_child_prompt_delivery(context)

    assert delivery is not None
    assert delivery.original_task == CODEX_ACTIVATION_CANARY_WORK_UNIT
    assert delivery.specialist_slug == "code-reviewer"
    assert context.endswith(store.prompts["code-reviewer"])


def test_zcode_does_not_invent_undocumented_child_lifecycle_identity() -> None:
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
    payload = {
        "hook_event_name": "SubagentStart",
        "session_id": "zcode-session",
        "agent_id": "agent-42",
        "agent_type": "general-purpose",
    }

    assert HookBridge("zcode", store=store).handle(payload) == {}  # type: ignore[arg-type]
    assert store.parent_scopes == []
    assert (
        HookBridge("zcode", store=store).handle(  # type: ignore[arg-type]
            {**payload, "hook_event_name": "SubagentStop"}
        )
        == {}
    )
    assert store.started == []
    assert store.stopped == []


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


@pytest.mark.parametrize(
    ("host", "native_tool", "binding", "activation_marker", "forbidden_marker"),
    [
        ("codex", "`spawn_agent`", "`native_task_name`", "PreToolUse hook", "`Agent`"),
        ("claude", "`Agent`", "`description`", "PreToolUse hook", "`spawn_agent`"),
        (
            "hermes",
            "`delegate_task`",
            "unchanged `work_unit_id` and exact `goal`",
            "child pre-LLM hook",
            "PreToolUse hook",
        ),
        (
            "openclaw",
            "`sessions_spawn`",
            "unchanged `work_unit_id` and exact `goal`",
            "child pre-LLM hook",
            "PreToolUse hook",
        ),
    ],
)
def test_isolated_parent_guidance_uses_the_exact_host_activation_contract(
    host: str,
    native_tool: str,
    binding: str,
    activation_marker: str,
    forbidden_marker: str,
) -> None:
    reference = SpecialistPromptReference(
        slug="code-reviewer",
        version="v1",
        content_hash="a" * 64,
        description="Review code",
        capabilities=("review",),
    )

    context = format_isolated_specialist_context(
        [reference],
        host=host,
        session_id=f"{host}-session",
        trace_id="trace",
        nontrivial=True,
        unit_plan=[{"work_unit_id": "unit-review"}],
    )

    assert native_tool in context
    assert binding in context
    assert activation_marker in context
    assert forbidden_marker not in context
    assert "Do not call `agency.prepare_delegation`" in context
    assert "`agency.load_specialist`" in context
    assert "code-reviewer" in context


def test_isolated_parent_guidance_rejects_selected_specialist_without_exact_plan() -> None:
    reference = SpecialistPromptReference(
        slug="code-reviewer",
        version="v1",
        content_hash="a" * 64,
        description="Review code",
        capabilities=("review",),
    )

    with pytest.raises(RuntimeError, match="lacks an exact unit-agent plan"):
        format_isolated_specialist_context(
            [reference],
            host="codex",
            session_id="codex-session",
            trace_id="trace",
            nontrivial=True,
        )


def test_isolated_parent_guidance_does_not_dispatch_an_untyped_worker() -> None:
    context = format_isolated_specialist_context(
        [],
        host="openclaw",
        session_id="openclaw-session",
        trace_id="trace",
        nontrivial=False,
    )

    assert "No specialist assignment was accepted" in context
    assert "Do not dispatch an untyped native worker" in context
