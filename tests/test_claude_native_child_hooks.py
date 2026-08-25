"""Claude Code native-child hook correlation and isolation contracts."""

from __future__ import annotations

from hashlib import sha256
from threading import Lock
from typing import Any

from agency_runtime.adapters import hooks as hooks_module
from agency_runtime.adapters.hooks import MAX_CONTEXT_CHARS, MAX_HOOK_OUTPUT_BYTES, HookBridge
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.native_child_prompt_delivery import (
    render_codex_native_child_execution_message,
)
from agency_runtime.core.native_child_staffing import NativeChildStaffingResult
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
        self.execution_claims: dict[tuple[str, str], str] = {}
        self._lock = Lock()

    def get_open_traces_for_session(self, _session_id: str) -> list[str]:
        return list(self.open_traces)

    def get_completion_evidence_snapshot(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        self.snapshot_reads.append((session_id, trace_id))
        worker_runs = []
        for (work_unit_id, _slug), lineage in self._lineage.items():
            worker_id = str(lineage["worker_id"])
            execution_tool_use_id = self.execution_claims.get(
                (work_unit_id, worker_id),
                "",
            )
            worker_runs.append(
                {
                    "backend": "spawn_agent",
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "work_unit_id": work_unit_id,
                    "host": "codex",
                    "worker_id": worker_id,
                    "native_run_id": str(lineage["native_run_id"]),
                    "execution_tool_use_id": execution_tool_use_id,
                    "execution_dispatched_at": (
                        "2026-08-01T12:00:00Z" if execution_tool_use_id else None
                    ),
                    "ended_at": None,
                }
            )
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
            "worker_runs": worker_runs,
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

    def prepare_codex_opaque_native_child_activation(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.prepare_delegation_activation(
            session_id=kwargs["session_id"],
            trace_id=kwargs["trace_id"],
            specialist_slug=kwargs["specialist_slug"],
            work_unit_id=kwargs["work_unit_id"],
            worker_kind="generic-worker",
            grant_origin="native_hook",
            tool_use_id=kwargs["tool_use_id"],
            mutation_mode="read_only",
            mutation_path_prefixes=[],
            evidence_contract_id="agency-native-child-plan-v1",
            evidence_requirements=["delegation-execution", "specialist-load"],
        )

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

    def get_pending_native_hook_delivery(self, **_kwargs: Any) -> dict[str, str] | None:
        if not self.prepared:
            return None
        prepared = self.prepared[0]
        slug = str(prepared["specialist_slug"])
        return {
            "session_id": str(prepared["session_id"]),
            "trace_id": str(prepared["trace_id"]),
            "tool_use_id": str(prepared["tool_use_id"]),
            "work_unit_id": str(prepared["work_unit_id"]),
            "slug": slug,
            "version": "v1",
            "prompt_hash": self.hashes[slug],
            "prompt_body": self.prompts[slug],
        }

    def claim_codex_native_child_execution(self, **kwargs: Any) -> bool:
        key = (str(kwargs["work_unit_id"]), str(kwargs["worker_id"]))
        tool_use_id = str(kwargs["tool_use_id"])
        prior = self.execution_claims.get(key)
        if prior is not None:
            return prior == tool_use_id
        self.execution_claims[key] = tool_use_id
        return True

    def get_native_child_run(self, **kwargs: Any) -> dict[str, Any] | None:
        unit = str(kwargs["work_unit_id"])
        worker_id = str(kwargs["worker_id"])
        for (work_unit_id, _slug), lineage in self._lineage.items():
            if (
                work_unit_id != unit
                or lineage["worker_id"] != worker_id
                or lineage["native_run_id"] != kwargs["native_run_id"]
            ):
                continue
            tool_use_id = self.execution_claims.get((unit, worker_id), "")
            return {
                "backend": "spawn_agent",
                "session_id": str(kwargs["session_id"]),
                "trace_id": str(kwargs["trace_id"]),
                "work_unit_id": unit,
                "host": "codex",
                "worker_id": worker_id,
                "native_run_id": str(kwargs["native_run_id"]),
                "execution_tool_use_id": tool_use_id,
                "execution_dispatched_at": ("2026-08-01T12:00:00Z" if tool_use_id else None),
                "ended_at": None,
            }
        return None

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


def test_pre_tool_use_fails_closed_for_unplanned_or_ambiguous_work() -> None:
    bridge = HookBridge("claude", store=_PlanStore())  # type: ignore[arg-type]
    assert bridge.handle(_agent_payload(description="unit-unplanned")) == {}

    ambiguous = _agent_payload()
    ambiguous.pop("turn_id")
    ambiguous_store = _PlanStore(open_traces=("trace-a", "trace-b"))
    assert HookBridge("claude", store=ambiguous_store).handle(ambiguous) == {}  # type: ignore[arg-type]
    assert ambiguous_store.snapshot_reads == []


def test_plaintext_staffing_validates_the_exact_returned_hook_bytes_before_success(
    monkeypatch: Any,
) -> None:
    store = _PlanStore()
    observed: dict[str, Any] = {}

    def staff(*_args: Any, **kwargs: Any) -> NativeChildStaffingResult:
        rewritten = 'Review "exact" \\ escaping.\n[AGENCY INFERENCE TEAM v6]'
        validator = kwargs["delivery_validator"]
        observed["accepted"] = validator(rewritten)
        observed["prospective"] = hooks_module._encoded_hook_output(
            hooks_module._native_child_staffing_response(
                _agent_payload()["tool_input"],
                task_field="prompt",
                rewritten_task=rewritten,
            )
        )
        return NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task=rewritten,
        )

    monkeypatch.setattr(
        HookBridge,
        "_native_child_staffing_parent",
        lambda _self, _payload, _args: (
            hooks_module.HookCorrelation(
                "claude-session",
                "trace",
                "",
                "",
                "toolu-code",
            ),
            "trace",
        ),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_install_identity.current_runtime_managed_host_install_identity",
        lambda _host: object(),
    )
    monkeypatch.setattr("agency_runtime.core.native_child_staffing.staff_native_child", staff)

    response = HookBridge("claude", store=store).handle(_agent_payload())  # type: ignore[arg-type]
    returned = hooks_module._encoded_hook_output(response)

    assert observed["accepted"] is True
    assert returned == observed["prospective"]
    assert returned is not None and len(returned) <= MAX_HOOK_OUTPUT_BYTES


def test_zcode_agent_pre_tool_use_reaches_native_child_staffing(
    monkeypatch: Any,
) -> None:
    store = _PlanStore()
    observed: dict[str, Any] = {}

    def staff(*_args: Any, **kwargs: Any) -> NativeChildStaffingResult:
        observed.update(kwargs)
        rewritten = "Review the implementation.\n[AGENCY INFERENCE TEAM v6]"
        assert kwargs["delivery_validator"](rewritten) is True
        return NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task=rewritten,
        )

    monkeypatch.setattr(
        HookBridge,
        "_native_child_staffing_parent",
        lambda _self, _payload, _args: (
            hooks_module.HookCorrelation(
                "zcode-session",
                "trace",
                "",
                "",
                "toolu-code",
            ),
            "trace",
        ),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_install_identity.current_runtime_managed_host_install_identity",
        lambda host: {"host": host},
    )
    monkeypatch.setattr("agency_runtime.core.native_child_staffing.staff_native_child", staff)

    response = HookBridge("zcode", store=store).handle(  # type: ignore[arg-type]
        _zcode_agent_payload()
    )

    assert observed["host"] == "zcode"
    assert observed["parent_session_id"] == "zcode-session"
    assert observed["launch_id"] == "toolu-code"
    assert response["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert response["hookSpecificOutput"]["updatedInput"]["prompt"].endswith(
        "[AGENCY INFERENCE TEAM v6]"
    )


def test_escaping_heavy_hook_response_is_rejected_before_staffing_can_persist(
    monkeypatch: Any,
) -> None:
    store = _PlanStore()
    observed: dict[str, Any] = {}

    def staff(*_args: Any, **kwargs: Any) -> NativeChildStaffingResult:
        rewritten = ('"\\\n' * 15_000) + "tail"
        observed["raw_chars"] = len(rewritten)
        observed["accepted"] = kwargs["delivery_validator"](rewritten)
        return NativeChildStaffingResult(
            staffed=bool(observed["accepted"]),
            reason_code=("staffed" if observed["accepted"] else "validation_failed"),
            rewritten_task=rewritten,
        )

    monkeypatch.setattr(
        HookBridge,
        "_native_child_staffing_parent",
        lambda _self, _payload, _args: (
            hooks_module.HookCorrelation(
                "claude-session",
                "trace",
                "",
                "",
                "toolu-code",
            ),
            "trace",
        ),
    )
    monkeypatch.setattr(
        "agency_runtime.core.native_child_install_identity.current_runtime_managed_host_install_identity",
        lambda _host: object(),
    )
    monkeypatch.setattr("agency_runtime.core.native_child_staffing.staff_native_child", staff)

    response = HookBridge("claude", store=store).handle(_agent_payload())  # type: ignore[arg-type]

    assert observed["raw_chars"] < MAX_CONTEXT_CHARS
    assert observed["accepted"] is False
    assert response == {}


def test_unserializable_host_input_never_enters_staffing_or_persistence(
    monkeypatch: Any,
) -> None:
    store = _PlanStore()
    called = False

    def staff(*_args: Any, **_kwargs: Any) -> NativeChildStaffingResult:
        nonlocal called
        called = True
        raise AssertionError("staffing must not run")

    monkeypatch.setattr(
        HookBridge,
        "_native_child_staffing_parent",
        lambda _self, _payload, _args: (
            hooks_module.HookCorrelation(
                "claude-session",
                "trace",
                "",
                "",
                "toolu-code",
            ),
            "trace",
        ),
    )
    monkeypatch.setattr("agency_runtime.core.native_child_staffing.staff_native_child", staff)
    payload = _agent_payload()
    payload["tool_input"]["unserializable"] = float("nan")

    response = HookBridge("claude", store=store).handle(payload)  # type: ignore[arg-type]

    assert response == {}
    assert called is False


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
    assert "host-owned launch prompt" in context
    assert "does not ask the child to repair staffing" in context
    assert "agency.preflight" not in context
    assert "parent_scope_token" not in context
    assert store.parent_scopes == []


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
        assert "parent_session_id=" not in context
        assert "parent_trace_id=" not in context
        assert "parent_scope_token=" not in context
        assert "agency.preflight" not in context


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


def test_codex_subagent_lifecycle_reports_opaque_unstaffed_identity() -> None:
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
    assert "hook contract did not expose this child's decrypted" in context
    assert "proceed with its native child unstaffed" in context
    assert "agency.preflight" not in context
    assert "parent_scope_token" not in context
    assert "does not load, select, or inherit" in context
    assert store.parent_scopes == []
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


def _activate_codex_plan_child(
    bridge: HookBridge,
    *,
    worker_id: str = "019fa6a6-a197-7a83-b3fb-d2c20411f608",
) -> tuple[str, str]:
    task_name = codex_task_name_for_work_unit("unit-code")
    bridge.handle(
        {
            "hook_event_name": "PreToolUse",
            "session_id": "codex-session",
            "turn_id": "trace",
            "tool_name": "collaborationspawn_agent",
            "tool_use_id": "call-product",
            "tool_input": {
                "fork_turns": "none",
                "task_name": task_name,
                "message": "gAAAAA" + "opaque-product-ciphertext" * 2,
            },
        }
    )
    bridge.handle(
        {
            "hook_event_name": "SubagentStart",
            "session_id": "codex-session",
            "agent_id": worker_id,
            "agent_type": "worker",
        }
    )
    message = render_codex_native_child_execution_message(
        work_unit_id="unit-code",
        goal_hash=work_unit_goal_hash("Review the implementation."),
        goal="Review the implementation.",
    )
    return task_name, message


def test_codex_followup_post_tool_does_not_record_a_second_delegation() -> None:
    store = _PlanStore()
    adapter = _RecordingAdapter()
    bridge = HookBridge("codex", store=store, adapter=adapter)  # type: ignore[arg-type]
    task_name, message = _activate_codex_plan_child(bridge)

    bridge.handle(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "codex-session",
            "turn_id": "trace",
            "tool_name": "collaborationfollowup_task",
            "tool_use_id": "call-followup",
            "tool_input": {"target": f"/root/{task_name}", "message": message},
            "tool_response": "",
        }
    )

    assert adapter.calls == []


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
