"""Exact branch closure for adapter and public diagnostic boundaries."""

from __future__ import annotations

import importlib
import io
import json
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime import AgencyRuntime
from agency_runtime.adapters import base as base_adapter
from agency_runtime.adapters import hooks
from agency_runtime.adapters.base import BaseAdapter, _native_delegation_batch
from agency_runtime.adapters.hermes import bridge as hermes_bridge
from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.server import mcp_tools


class _EnabledStore:
    def get_host_control(self, _host: str) -> dict[str, bool]:
        return {"enabled": True}


class _Adapter(BaseAdapter):
    host_name = "test"

    def is_available(self) -> bool:
        return True

    def get_delegate_backend(self) -> str | None:
        return None


def test_native_delegation_batch_projects_bounded_official_shapes() -> None:
    assert _native_delegation_batch("spawn_agent", {}, None) is None
    assert _native_delegation_batch("delegate_task", {"tasks": "invalid"}, None) is None
    assert _native_delegation_batch("delegate_task", {"tasks": []}, None) == []

    projected = _native_delegation_batch(
        "delegate_task",
        {
            "role": "orchestrator",
            "tasks": [
                None,
                {"goal": "one"},
                {"goal": "two", "role": "leaf"},
                {"goal": "three"},
            ],
        },
        json.dumps(
            {
                "results": [
                    "opaque",
                    {"task_index": True, "status": "completed"},
                    {"task_index": "two", "status": "completed"},
                    {"task_index": 99, "status": "completed"},
                    {"task_index": 99, "status": "completed"},
                ]
            }
        ),
    )
    assert projected is not None
    assert [task for task, _result in projected] == [
        {"goal": "one"},
        {"goal": "two"},
        {"goal": "three"},
    ]
    assert _native_delegation_batch("delegate_task", {"tasks": []}, "not-json") == []

    failed = _native_delegation_batch(
        "delegate_task",
        {"tasks": [{"goal": "audit"}]},
        {"status": "failed", "error": "worker unavailable"},
    )
    assert failed == [
        (
            {"goal": "audit"},
            {"status": "failed", "error": "worker unavailable"},
        )
    ]
    limited = _native_delegation_batch(
        "delegate_task",
        {"tasks": [{"goal": str(index)} for index in range(20)]},
        None,
    )
    assert limited is not None and len(limited) == 16


def test_public_facade_rejects_invalid_diagnostic_and_delegation_inputs(tmp_path) -> None:
    runtime = AgencyRuntime(str(tmp_path / "public-owned.db"))
    with pytest.raises(ValueError, match="session_id is required"):
        runtime.route("", "review code")

    runtime.preflight("session", "Review this change.", trace_id="turn")
    cases = (
        ({"work_unit_id": "", "recommended_agent": "reviewer"}, "work_unit_id"),
        ({"work_unit_id": "unit", "recommended_agent": ""}, "recommended_agent"),
        (
            {"work_unit_id": "unit", "recommended_agent": "reviewer", "status": "invalid"},
            "unsupported delegation status",
        ),
        (
            {"work_unit_id": "unit", "recommended_agent": "reviewer", "status": "completed"},
            "backend is required",
        ),
    )
    for values, message in cases:
        with pytest.raises(ValueError, match=message):
            runtime.record_delegation(
                trace_id="turn",
                session_id="session",
                **values,
            )


def test_mcp_missing_correlation_and_preflight_error_paths(monkeypatch) -> None:
    store = SimpleNamespace()
    assert mcp_tools._preflight({"session_id": "", "user_message": "x"}, store)["error"]

    def reject_preflight(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("bad preflight")

    monkeypatch.setattr("agency_runtime.core.preflight.run_preflight", reject_preflight)
    assert mcp_tools._preflight(
        {"session_id": "session", "host": "codex", "user_message": "x"}, store
    ) == {"error": "bad preflight"}
    assert "required" in mcp_tools._load_specialist({"slug": "x"}, store)["error"]
    assert "required" in mcp_tools._record_skill_loaded({"skill_name": "x"}, store)["error"]
    missing = mcp_tools._finalize({"draft_text": "draft", "session_id": ""}, store)
    assert missing == {
        "action": "continue",
        "text": "draft",
        "missing": ["session_id", "trace_id"],
    }


def test_http_preflight_value_error_and_invalid_delegation_status(monkeypatch) -> None:
    from agency_runtime.server.http import AgencyHTTPHandler

    observed: list[tuple[Any, Any]] = []
    handler = SimpleNamespace(
        store=object(),
        server=SimpleNamespace(allow_context_writes=True),
        _json_error=lambda status, message: observed.append((status, message)),
        _json_ok=lambda payload: observed.append(("ok", payload)),
    )

    def reject_preflight(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("invalid preflight")

    monkeypatch.setattr("agency_runtime.server.http.run_preflight", reject_preflight)
    AgencyHTTPHandler._handle_preflight(
        handler,
        {"session_id": "session", "user_message": "review"},
    )
    assert observed[-1][1] == "invalid preflight"

    AgencyHTTPHandler._handle_finalize(
        handler,
        {
            "draft_text": "draft",
            "session_id": "session",
            "trace_id": "trace",
            "delegations": [
                {
                    "agent": "reviewer",
                    "work_unit_id": "unit",
                    "backend": "spawn",
                    "status": "running",
                }
            ],
        },
    )
    assert observed[-1][1] == (
        "delegations[0].status must be delegated, completed, skipped, or failed"
    )


def test_base_adapter_defensive_store_and_delegation_paths(monkeypatch) -> None:
    adapter = _Adapter(store=_EnabledStore())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="cannot verify turn request kind"):
        adapter._was_nontrivial_turn("session", "trace")

    class TraceStore(_EnabledStore):
        def get_open_traces_for_session(self, _session_id: str) -> list[str]:
            raise OSError("offline")

    adapter.store = TraceStore()  # type: ignore[assignment]
    assert adapter.resolve_turn_trace("session") == ""

    monkeypatch.setattr(
        "agency_runtime.core.delegation.events.suggested_delegations",
        lambda store, session_id, *, trace_id: [
            {"store": store, "session": session_id, "trace": trace_id}
        ],
    )
    assert adapter._suggested_delegations("session", "trace")[0]["trace"] == "trace"

    adapter.store = _EnabledStore()  # type: ignore[assignment]
    adapter.record_tool_call(tool_name="spawn_agent", args={})

    adapter.post_api_request_handler(session_id="session", trace_id="trace")

    class RaisingRunStore(_EnabledStore):
        def get_run(self, _trace_id: str) -> dict[str, str]:
            raise OSError("offline")

    adapter.store = RaisingRunStore()  # type: ignore[assignment]
    adapter.post_api_request_handler(session_id="session", trace_id="trace")

    class WrongRunStore(_EnabledStore):
        def get_run(self, _trace_id: str) -> dict[str, str]:
            return {"session_id": "other", "status": "active"}

    adapter.store = WrongRunStore()  # type: ignore[assignment]
    adapter.post_api_request_handler(session_id="session", trace_id="trace")


def test_hermes_suggestion_override_executes(monkeypatch) -> None:
    from agency_runtime.adapters.hermes.plugin import HermesAdapter

    marker = object()
    monkeypatch.setattr(
        "agency_runtime.core.delegation.events.suggested_delegations",
        lambda store, session_id, *, trace_id: [marker, store, session_id, trace_id],
    )
    adapter = object.__new__(HermesAdapter)
    adapter.store = "store"  # type: ignore[assignment]
    assert adapter._suggested_delegations("session", "trace") == [
        marker,
        "store",
        "session",
        "trace",
    ]


def test_litellm_fail_open_before_event_claim_and_hostile_mapping(monkeypatch) -> None:
    from collections.abc import Mapping

    from agency_runtime.adapters.litellm.callback import AgencyLiteLLMCallback
    from agency_runtime.adapters.litellm.evidence import response_value

    callback = AgencyLiteLLMCallback()
    monkeypatch.setattr(
        callback,
        "_event_key",
        lambda *_args: (_ for _ in ()).throw(OSError("identity unavailable")),
    )
    callback._record_receipt({}, {}, None, None, status="success")

    class HostileMapping(Mapping):
        def __getitem__(self, key: object) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 0

        def get(self, key: object, default: object = None) -> Any:
            raise RuntimeError("hostile get")

    assert response_value(HostileMapping(), "model") is None


def _bridge(store: Any | None = None, adapter: Any | None = None) -> hooks.HookBridge:
    return hooks.HookBridge(
        "codex",
        store=store or SimpleNamespace(),
        adapter=adapter or SimpleNamespace(),
    )


def test_hook_trace_recovery_retry_and_reservation_fail_closed(monkeypatch) -> None:
    assert hooks._bounded_completion_reason("x" * hooks.MAX_CONTEXT_CHARS) != "x" * (
        hooks.MAX_CONTEXT_CHARS
    )

    bridge = _bridge(
        SimpleNamespace(
            get_open_traces_for_session=lambda _session: (_ for _ in ()).throw(OSError())
        )
    )
    assert bridge._unambiguous_open_trace("session") == ""

    activity = {
        "runs": [
            {"session_id": "session", "trace_id": "open", "status": "active"},
            {"session_id": "other", "trace_id": "ignored", "status": "active"},
        ]
    }
    bridge.store = SimpleNamespace(
        get_open_traces_for_session=lambda _session: [],
        recent_runtime_activity=lambda **_kwargs: activity,
    )
    assert bridge._unambiguous_open_trace("session") == "open"

    bridge.store = SimpleNamespace(
        get_open_traces_for_session=lambda _session: [],
        recent_runtime_activity=lambda **_kwargs: {
            "runs": [],
            "finalizations": [
                {"trace_id": "terminal", "action": "accept"},
            ],
            "routing": [
                {"session_id": "session", "trace_id": "terminal"},
                {"session_id": "session", "trace_id": "open"},
            ],
        },
    )
    assert bridge._unambiguous_open_trace("session") == "open"

    bridge.store = SimpleNamespace()
    assert (
        bridge._user_prompt_origin(hooks.HookCorrelation("s", "t", "", "", "")).origin
        != "internal_retry"
    )
    bridge.store = SimpleNamespace(
        resolve_pending_internal_retry=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError())
    )
    assert (
        bridge._user_prompt_origin(hooks.HookCorrelation("s", "t", "", "", "")).origin
        != "internal_retry"
    )

    bridge.store = SimpleNamespace()
    with pytest.raises(RuntimeError, match="cannot reserve"):
        bridge._reserve_user_turn("session", "trace")
    bridge.store = SimpleNamespace(reserve_session_turn=lambda **_kwargs: {})
    with pytest.raises(RuntimeError, match="could not be verified"):
        bridge._reserve_user_turn("session", "trace")
    bridge.store = SimpleNamespace(
        reserve_session_turn=lambda **_kwargs: {"trace_id": "trace", "reservation_token": "bad"}
    )
    with pytest.raises(RuntimeError, match="identity is invalid"):
        bridge._reserve_user_turn("session", "trace")
    bridge.store = SimpleNamespace(
        reserve_session_turn=lambda **_kwargs: {"trace_id": "trace", "created": True}
    )
    with pytest.raises(RuntimeError, match="was not persisted"):
        bridge._reserve_user_turn("session", "trace")
    with pytest.raises(RuntimeError, match="cannot abandon"):
        bridge._close_unused_reservation(
            "session",
            "trace",
            {"reservation_token": "receipt"},
        )


def test_hook_cleanup_and_terminal_helper_failures(monkeypatch) -> None:
    class RaisingAdapter:
        def pre_llm_call_handler(self, **_kwargs: Any) -> None:
            raise ValueError("preflight failed")

    bridge = _bridge(adapter=RaisingAdapter())
    monkeypatch.setattr(
        bridge,
        "_reserve_user_turn",
        lambda *_args: {"reservation_token": "receipt"},
    )
    monkeypatch.setattr(
        bridge,
        "_close_unused_reservation",
        lambda *_args: (_ for _ in ()).throw(OSError("cleanup failed")),
    )
    with pytest.raises(ValueError, match="preflight failed") as caught:
        bridge.handle(
            {"hook_event_name": "UserPromptSubmit", "session_id": "session", "prompt": "work"}
        )
    assert isinstance(caught.value.__cause__, OSError)

    bridge = _bridge()
    assert not bridge._commit_terminal_finalization(
        session_id="s",
        trace_id="t",
        action="accept",
        status="completed",
        response_text="draft",
        expected_evidence_revision=0,
    )
    bridge.store = SimpleNamespace(commit_terminal_finalization=lambda **_kwargs: {})
    assert not bridge._commit_terminal_finalization(
        session_id="s",
        trace_id="t",
        action="accept",
        status="completed",
        response_text="draft",
        expected_evidence_revision=0,
    )
    bridge.store = SimpleNamespace()
    with pytest.raises(RuntimeError, match="cannot recover"):
        bridge._authoritative_trace_for_response("s", "draft")
    bridge.store = SimpleNamespace(find_authoritative_trace=lambda *_args, **_kwargs: object())
    with pytest.raises(RuntimeError, match="could not be verified"):
        bridge._authoritative_trace_for_response("s", "draft")
    with pytest.raises(RuntimeError, match="lifecycle could not be verified"):
        bridge._is_terminal_turn("s", "t")
    bridge.store = SimpleNamespace(get_run=lambda _trace: {"session_id": "other"})
    with pytest.raises(RuntimeError, match="correlation could not be verified"):
        bridge._is_terminal_turn("s", "t")

    finalize_module = importlib.import_module("agency_runtime.core.header.finalize")
    monkeypatch.setattr(
        finalize_module,
        "terminal_response_run",
        lambda *_args, **_kwargs: {
            "authoritative": True,
            "action": "accept",
            "terminal_status": "retry_exhausted",
            "status": "retry_exhausted",
        },
    )
    with pytest.raises(RuntimeError, match="inconsistent Agency turn"):
        bridge._exact_terminal_finalization("s", "t", "draft")

    bridge.adapter = SimpleNamespace(evaluate_completion_policy=lambda *_args, **_kwargs: "bad")
    invalid = bridge._verify_final_response(
        "draft",
        correlation=hooks.HookCorrelation("s", "t", "", "", ""),
        trace_id="t",
        retry=False,
    )
    assert invalid["action"] == "continue"


def test_hook_terminal_rejection_stop_and_closure_edge_paths(monkeypatch) -> None:
    bridge = _bridge()
    correlation = hooks.HookCorrelation("session", "trace", "", "", "")
    monkeypatch.setattr(bridge, "_verification_failed", lambda *_args: {"failed": True})
    monkeypatch.setattr(bridge, "_commit_terminal_finalization", lambda **_kwargs: False)
    assert bridge._handle_terminal_rejection(
        correlation=correlation,
        trace_id="trace",
        final_response="draft",
        verification={"action": "continue", "evidence_revision": 1},
    ) == {"failed": True}

    monkeypatch.setattr(bridge, "_commit_terminal_finalization", lambda **_kwargs: True)
    monkeypatch.setattr(
        bridge,
        "_terminal_completion_result",
        lambda action: {"terminal": action},
    )
    assert bridge._handle_terminal_rejection(
        correlation=correlation,
        trace_id="trace",
        final_response="draft",
        verification={"action": "continue", "evidence_revision": 1},
    ) == {"terminal": "response_invalid"}
    assert bridge._handle_terminal_rejection(
        correlation=correlation,
        trace_id="trace",
        final_response="draft",
        verification={
            "action": "continue",
            "delegation_strength": "strongly_preferred",
            "evidence_revision": 1,
        },
    ) == {"terminal": "delegation_declined"}

    monkeypatch.setattr(bridge, "_correlation", lambda _payload: correlation)
    monkeypatch.setattr(bridge, "_acknowledge_resident_manager_delivery", lambda **_kwargs: None)
    monkeypatch.setattr(bridge, "_exact_terminal_finalization", lambda *_args: None)
    monkeypatch.setattr(bridge, "_is_terminal_turn", lambda *_args: False)
    monkeypatch.setattr(
        bridge,
        "_verify_final_response",
        lambda *_args, **_kwargs: {"action": "accept", "runtime_disabled": True},
    )
    assert bridge._handle_stop({}) == {}

    bridge.store = SimpleNamespace()
    assert not bridge._close_turn("session", "trace", "closed")
    bridge.store = SimpleNamespace(
        close_turn_evidence=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
        get_run=lambda _trace: {},
    )
    assert not bridge._close_turn("session", "trace", "closed")
    bridge.store = SimpleNamespace()
    bridge._close_session_turns("session", "closed")
    bridge.store = SimpleNamespace(
        get_open_traces_for_session=lambda _session: (_ for _ in ()).throw(OSError())
    )
    bridge._close_session_turns("session", "closed")


def test_hook_stdio_rejects_mismatched_registered_event() -> None:
    output = io.BytesIO()
    errors = io.StringIO()
    status = hooks.run_hook_stdio(
        "codex",
        expected_event="Stop",
        input_stream=io.BytesIO(b'{"hook_event_name":"SessionStart","session_id":"session"}'),
        output_stream=output,
        error_stream=errors,
    )
    assert status == 0
    assert errors.getvalue() == (
        "agency hook codex: HookInputError; response publication blocked\n"
    )
    assert json.loads(output.getvalue())["continue"] is False


def test_openclaw_private_fail_closed_helpers() -> None:
    assert not node_bridge._is_authenticated_retry(
        SimpleNamespace(store=SimpleNamespace()),
        session_id="s",
        trace_id="t",
        message="retry",
    )
    raising_validator = SimpleNamespace(
        store=SimpleNamespace(
            resolve_pending_internal_retry=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OSError()
            )
        )
    )
    assert not node_bridge._is_authenticated_retry(
        raising_validator,
        session_id="s",
        trace_id="t",
        message="retry",
    )

    with pytest.raises(RuntimeError, match="cannot be verified"):
        node_bridge._recover_exact_terminal_trace(
            SimpleNamespace(store=SimpleNamespace()), "s", "x"
        )
    adapter = SimpleNamespace(
        store=SimpleNamespace(
            get_open_traces_for_session=lambda _session: ["open"],
            find_authoritative_trace=lambda *_args, **_kwargs: "ignored",
            find_authoritative_trace_by_policy_hash=lambda *_args, **_kwargs: "ignored",
        )
    )
    assert node_bridge._recover_exact_terminal_trace(adapter, "s", "x") == ""
    adapter.store.get_open_traces_for_session = lambda _session: []
    adapter.store.find_authoritative_trace_by_policy_hash = lambda *_args, **_kwargs: None
    assert node_bridge._recover_exact_terminal_trace(adapter, "s", "x") == ""
    adapter.store.find_authoritative_trace_by_policy_hash = lambda *_args, **_kwargs: object()
    with pytest.raises(RuntimeError, match="correlation is invalid"):
        node_bridge._recover_exact_terminal_trace(adapter, "s", "x")

    adapter = SimpleNamespace(
        store=SimpleNamespace(
            commit_terminal_finalization=lambda **_kwargs: (_ for _ in ()).throw(OSError())
        )
    )
    assert not node_bridge._commit_terminal_outcome(
        adapter,
        session_id="s",
        trace_id="t",
        final_response="draft",
        action="accept",
        status="completed",
        evidence_revision=1,
    )
    adapter.store = SimpleNamespace()
    assert (
        node_bridge._header_snapshot_context(
            adapter,
            session_id="s",
            trace_id="t",
            model="m",
        )
        == ""
    )
    unchanged = {"context": "existing"}
    assert (
        node_bridge._append_header_snapshot(
            unchanged,
            adapter,
            session_id="s",
            trace_id="t",
            model="m",
        )
        == unchanged
    )


def test_openclaw_policy_projection_failure_matrix(monkeypatch) -> None:
    def evaluated(value: Any) -> Any:
        adapter = SimpleNamespace(evaluate_completion_policy=lambda *_args, **_kwargs: value)
        return node_bridge._evaluate_pre_verify_policy(
            adapter,
            final_response="draft",
            session_id="s",
            model="m",
            attempt=0,
            trace_id="t",
        )

    assert evaluated("bad") is None
    assert evaluated({"action": "continue", "runtime_disabled": True}) is None
    assert (
        node_bridge._evaluate_pre_verify_policy(
            SimpleNamespace(),
            final_response="draft",
            session_id="s",
            model="m",
            attempt=0,
            trace_id="t",
        )
        is None
    )
    assert node_bridge._evaluate_pre_verify_policy(
        SimpleNamespace(pre_verify_handler=lambda **_kwargs: None),
        final_response="draft",
        session_id="s",
        model="m",
        attempt=0,
        trace_id="t",
    ) == {"action": "accept"}
    assert (
        node_bridge._evaluate_pre_verify_policy(
            SimpleNamespace(pre_verify_handler=lambda **_kwargs: {"action": "accept"}),
            final_response="draft",
            session_id="s",
            model="m",
            attempt=0,
            trace_id="t",
        )
        is None
    )

    terminal = node_bridge._revision("x" * (node_bridge.MAX_VISIBLE_MESSAGE_JSON_BYTES + 1))
    assert terminal["action"] == "terminal"
    assert terminal["terminalStatus"] == "verification_failed"
    assert "revisionId" not in terminal

    with pytest.raises(RuntimeError, match="terminal response evidence is inconsistent"):
        node_bridge._accept_exact_finalized_response(
            SimpleNamespace(
                store=SimpleNamespace(
                    get_authoritative_finalization=lambda *_args, **_kwargs: {
                        "authoritative": True,
                        "status": "retry_exhausted",
                    }
                )
            ),
            "s",
            "t",
            "draft",
        )

    monkeypatch.setattr(
        node_bridge,
        "_evaluate_pre_verify_policy",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
    )
    assert (
        node_bridge._safe_policy_decision(
            object(),
            final_response="draft",
            session_id="s",
            model="m",
            attempt=0,
            trace_id="t",
        )
        is None
    )


def test_openclaw_persistence_and_preverify_edge_matrix(monkeypatch) -> None:
    adapter = SimpleNamespace()
    common = {
        "adapter": adapter,
        "policy_response": "draft",
        "response_binding": "draft",
        "session_id": "s",
        "trace_id": "t",
    }
    assert (
        node_bridge._finish_policy_rejection(
            **common, decision={"action": "continue", "evidence_revision": 0}
        )["terminalStatus"]
        == "verification_failed"
    )
    assert (
        node_bridge._finish_policy_rejection(
            **common, decision={"action": "continue", "runtime_disabled": True}
        )
        == {}
    )
    assert (
        node_bridge._finish_policy_rejection(
            **common, decision={"action": "accept", "evidence_revision": 1}
        )["terminalStatus"]
        == "verification_failed"
    )
    monkeypatch.setattr(
        node_bridge,
        "_commit_terminal_outcome",
        lambda *_args, **_kwargs: True,
    )
    rejected = node_bridge._finish_policy_rejection(
        **common, decision={"action": "continue", "evidence_revision": 1}
    )
    assert rejected["terminalRejected"] is True
    assert rejected["terminalStatus"] == "response_invalid"
    assert len(rejected["responseHash"]) == 64
    active = SimpleNamespace(
        runtime_enabled=lambda: True,
        store=SimpleNamespace(get_run=lambda _trace: {"session_id": "s", "status": "active"}),
    )
    monkeypatch.setattr(
        node_bridge,
        "_effective_pre_verify_trace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
    )
    assert (
        node_bridge._handle_pre_verify(
            active,
            {"finalResponse": "draft"},
            session_id="s",
            trace_id="t",
            model="m",
        )["terminalStatus"]
        == "verification_failed"
    )
    monkeypatch.setattr(node_bridge, "_effective_pre_verify_trace", lambda *_args, **_kwargs: "t")
    monkeypatch.setattr(
        node_bridge,
        "_exact_policy_terminal_state",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
    )
    assert (
        node_bridge._handle_pre_verify(
            active,
            {"finalResponse": "draft"},
            session_id="s",
            trace_id="t",
            model="m",
        )["terminalStatus"]
        == "verification_failed"
    )
    monkeypatch.setattr(node_bridge, "_exact_policy_terminal_state", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        node_bridge,
        "_safe_policy_decision",
        lambda *_args, **_kwargs: {"action": "accept", "runtime_disabled": True},
    )
    assert node_bridge._handle_pre_verify(
        active,
        {"finalResponse": "draft"},
        session_id="s",
        trace_id="t",
        model="m",
    ) == {"runtimeDisabled": True}


@pytest.mark.parametrize(
    ("payload", "policy_text", "expected"),
    [
        ({"text": "same", "spokenText": "same"}, "same", True),
        ({"spokenText": "audio only"}, "audio only", True),
        ({"ttsSupplement": {"spokenText": "audio only"}}, "audio only", True),
        ({"text": "visible", "spokenText": "different"}, "visible", False),
        (
            {"text": "visible", "ttsSupplement": {"spokenText": "different"}},
            "visible",
            False,
        ),
        ({"mediaUrl": "report.png"}, "visible", False),
    ],
)
def test_openclaw_outbound_payload_binds_every_text_surface(
    payload: dict[str, object],
    policy_text: str,
    expected: bool,
) -> None:
    assert (
        node_bridge._outbound_binding_matches_policy_text(
            json.dumps(payload, separators=(",", ":"), sort_keys=True),
            policy_text,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("session_id", "trace_id", "final_response"),
    (("", "t", "draft"), ("s", "", "draft"), ("s", "t", "")),
)
def test_openclaw_outbound_gate_requires_exact_correlation(
    session_id: str,
    trace_id: str,
    final_response: str,
) -> None:
    adapter = SimpleNamespace(store=object())
    result = node_bridge._handle_outbound_gate(
        adapter,
        session_id=session_id,
        trace_id=trace_id,
        final_response=final_response,
    )
    assert result["action"] == "replace"
    assert len(result["responseHash"]) == 64


def test_openclaw_outbound_gate_fails_closed_without_authoritative_evidence() -> None:
    adapter = SimpleNamespace(store=object())
    common = {
        "adapter": adapter,
        "session_id": "s",
        "trace_id": "t",
        "final_response": "draft",
    }
    assert node_bridge._handle_outbound_gate(**common)["action"] == "replace"

    adapter.store = SimpleNamespace(
        get_authoritative_finalization=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("store unavailable")
        )
    )
    assert node_bridge._handle_outbound_gate(**common)["action"] == "replace"
    adapter.store = SimpleNamespace(get_authoritative_finalization=lambda *_args, **_kwargs: None)
    assert node_bridge._handle_outbound_gate(**common)["action"] == "replace"
    adapter.store = SimpleNamespace(get_authoritative_finalization=lambda *_args, **_kwargs: {})
    assert node_bridge._handle_outbound_gate(**common)["action"] == "replace"

    adapter = SimpleNamespace(
        store=object(),
        runtime_enabled=lambda: False,
        evaluate_completion_policy=lambda *_args, **_kwargs: {
            "action": "accept",
            "runtime_disabled": True,
        },
    )
    disabled = node_bridge._handle_outbound_gate(**{**common, "adapter": adapter})
    assert disabled["action"] == "allow"
    assert disabled["runtimeDisabled"] is True


@pytest.mark.parametrize(
    ("session_id", "trace_id", "final_response"),
    (("s", "t", "accepted"), ("s", "t", "rejected"), ("", "", "")),
)
def test_openclaw_outbound_gate_soft_off_precedes_all_correlation_paths(
    session_id: str,
    trace_id: str,
    final_response: str,
) -> None:
    result = node_bridge._handle_outbound_gate(
        SimpleNamespace(store=object(), runtime_enabled=lambda: False),
        session_id=session_id,
        trace_id=trace_id,
        final_response=final_response,
    )

    assert result["action"] == "allow"
    assert result["runtimeDisabled"] is True


def test_openclaw_constructor_error_and_oversized_main_fallback(monkeypatch) -> None:
    class BrokenAdapter:
        def __init__(self) -> None:
            raise OSError("offline")

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", BrokenAdapter)
    with pytest.raises(OSError, match="offline"):
        node_bridge.handle({"action": "preflight", "userMessage": "work"})

    monkeypatch.setattr(node_bridge, "_read_payload", lambda: {"action": "test"})
    monkeypatch.setattr(
        node_bridge,
        "handle",
        lambda _payload: {"message": "x" * node_bridge.MAX_BRIDGE_OUTPUT_BYTES},
    )
    stdout = io.StringIO()
    monkeypatch.setattr(node_bridge.sys, "stdout", stdout)
    assert node_bridge.main() == 0
    assert stdout.getvalue() == "{}\n"


def test_hook_claude_assignment_and_child_identity_fail_closed_matrix(monkeypatch) -> None:
    # The native-child preflight recipe budget was removed in PR #129; the
    # assignment type is now NativeChildAssignment.
    assert hooks._canonical_tool_call("codex", "Agent", {}, {})[0] == "spawn_agent"

    payload = {
        "tool_name": "Agent",
        "session_id": "session",
        "tool_use_id": "tool",
    }
    valid_snapshot = {
        "session_id": "session",
        "trace_id": "trace",
        "status": "active",
        "delivery_mode": "isolated",
        "selected_specialists": [{"slug": "reviewer", "version": "1.0.0", "hash": "a" * 64}],
        "unit_agent_plan": [
            {
                "work_unit_id": "specialist:reviewer",
                "recommended_agent": "reviewer",
                "goal_hash": "a" * 64,
                "mutation_scope": "",
                "resource_hashes": [],
                "required_evidence": [],
            }
        ],
    }
    bridge = hooks.HookBridge(
        "claude",
        store=SimpleNamespace(
            get_completion_evidence_snapshot=lambda *_args: dict(valid_snapshot),
        ),
        adapter=SimpleNamespace(),
    )
    assert (
        _bridge()._resolve_claude_child_assignment(
            payload=payload,
            tool_input={"description": "specialist:reviewer"},
            trace_id="trace",
        )
        is None
    )
    assert (
        bridge._resolve_claude_child_assignment(
            payload={**payload, "tool_use_id": ""},
            tool_input={"description": "specialist:reviewer"},
            trace_id="trace",
        )
        is None
    )

    bridge.store = SimpleNamespace(
        get_completion_evidence_snapshot=lambda *_args: (_ for _ in ()).throw(OSError())
    )
    assert (
        bridge._resolve_claude_child_assignment(
            payload=payload,
            tool_input={"description": "specialist:reviewer"},
            trace_id="trace",
        )
        is None
    )
    for mutation in (
        {"status": "completed"},
        {"selected_specialists": {}},
        {"unit_agent_plan": {}},
        {"unit_agent_plan": [], "selected_specialists": [{"slug": "other"}]},
    ):
        snapshot = {**valid_snapshot, **mutation}
        bridge.store = SimpleNamespace(
            get_completion_evidence_snapshot=lambda *_args, snapshot=snapshot: snapshot
        )
        assert (
            bridge._resolve_claude_child_assignment(
                payload=payload,
                tool_input={"description": "specialist:reviewer"},
                trace_id="trace",
            )
            is None
        )
    bridge.store = SimpleNamespace(
        get_completion_evidence_snapshot=lambda *_args: dict(valid_snapshot)
    )
    assert (
        bridge._resolve_claude_child_assignment(
            payload=payload,
            tool_input={"description": "unplanned"},
            trace_id="trace",
        )
        is None
    )
    resolved = bridge._resolve_claude_child_assignment(
        payload=payload,
        tool_input={"description": "specialist:reviewer"},
        trace_id="trace",
    )
    assert resolved is not None and resolved.specialist_slug == "reviewer"

    assert bridge._claude_post_tool_response({}, "opaque") == ("opaque", None)
    assert bridge._claude_post_tool_response({"agent_id": "bad id"}, {"agent_id": "bad id"}) == (
        {"agent_id": "bad id"},
        None,
    )
    assert (
        bridge._handle_native_child_pre_tool_use({"tool_name": "Other", "session_id": "session"})
        == {}
    )
    with pytest.raises(hooks.HookInputError, match="prompt"):
        bridge._handle_native_child_pre_tool_use(
            {
                "tool_name": "Agent",
                "session_id": "session",
                "tool_input": {},
            }
        )

    child_payload = {
        "session_id": "session",
        "agent_type": "worker",
        "agent_id": "bad id",
    }
    assert bridge._handle_claude_subagent_start(child_payload) == {}
    assert bridge._handle_claude_subagent_stop(child_payload) == {}
    codex = _bridge()
    assert codex._handle_codex_subagent_start(child_payload) == {}
    assert codex._handle_codex_subagent_stop(child_payload) == {}

    valid_child = {**child_payload, "agent_id": "child-1"}
    assert "hookSpecificOutput" in bridge._handle_claude_subagent_start(valid_child)
    assert bridge._handle_claude_subagent_stop(valid_child) == {}
    assert "hookSpecificOutput" in codex._handle_codex_subagent_start(valid_child)
    assert codex._handle_codex_subagent_stop(valid_child) == {}


def test_hook_post_tool_resident_and_terminal_defensive_matrix(monkeypatch) -> None:
    observed: list[dict[str, Any]] = []
    bridge = hooks.HookBridge(
        "codex",
        store=SimpleNamespace(),
        adapter=SimpleNamespace(post_tool_call_handler=lambda **kwargs: observed.append(kwargs)),
    )
    common = {
        "session_id": "session",
        "turn_id": "trace",
        "tool_name": "spawn_agent",
        "tool_input": {},
    }
    for response in ("opaque", {}, {"agent_id": "bad id"}):
        bridge._handle_post_tool_use(
            "PostToolUse",
            {**common, "tool_response": response},
        )
    assert len(observed) == 3

    with pytest.raises(RuntimeError, match="cannot retire"):
        bridge._handle_resident_lifecycle("SessionEnd", {"session_id": "session"})

    bridge.store = SimpleNamespace(
        get_completion_evidence_snapshot=lambda *_args: "invalid",
    )
    with pytest.raises(RuntimeError, match="unavailable"):
        bridge._acknowledge_resident_manager_delivery(session_id="session", trace_id="trace")
    bridge.store = SimpleNamespace(
        get_completion_evidence_snapshot=lambda *_args: {
            "resident_manager_binding": {"invalid": True}
        },
    )
    with pytest.raises(RuntimeError, match="invalid"):
        bridge._acknowledge_resident_manager_delivery(session_id="session", trace_id="trace")

    from agency_runtime.core.resident_manager_binding import build_resident_manager_binding

    request_scoped = build_resident_manager_binding(
        session_id="session",
        host="codex",
        delivery_mode="request",
    ).as_dict()
    claude = hooks.HookBridge(
        "claude",
        store=SimpleNamespace(
            get_completion_evidence_snapshot=lambda *_args: {
                "resident_manager_binding": request_scoped
            }
        ),
        adapter=SimpleNamespace(),
    )
    claude._acknowledge_resident_manager_delivery(session_id="session", trace_id="trace")

    persistent = build_resident_manager_binding(
        session_id="session",
        host="claude",
        delivery_mode="injected",
    ).as_dict()
    bridge.store = SimpleNamespace(
        get_completion_evidence_snapshot=lambda *_args: {"resident_manager_binding": persistent}
    )
    with pytest.raises(RuntimeError, match="host does not match"):
        bridge._acknowledge_resident_manager_delivery(session_id="session", trace_id="trace")

    bridge.store = SimpleNamespace()
    with pytest.raises(RuntimeError, match="cannot acknowledge"):
        bridge._acknowledge_resident_manager_delivery(session_id="session", trace_id="trace")

    closed: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        bridge,
        "_close_turn",
        lambda session, trace, status: closed.append((session, trace, status)) or True,
    )
    monkeypatch.setattr(
        bridge,
        "_verify_final_response",
        lambda *_args, **_kwargs: {"verification_unavailable": True},
    )
    correlation = hooks.HookCorrelation("session", "trace", "", "", "")
    monkeypatch.setattr(bridge, "_correlation", lambda _payload: correlation)
    monkeypatch.setattr(bridge, "_acknowledge_resident_manager_delivery", lambda **_kwargs: None)
    monkeypatch.setattr(bridge, "_exact_terminal_finalization", lambda *_args: None)
    monkeypatch.setattr(bridge, "_is_terminal_turn", lambda *_args: False)
    result = bridge._handle_stop({"last_assistant_message": "draft"})
    assert result["continue"] is False
    assert closed[-1] == ("session", "trace", "verification_failed")

    bridge.store = SimpleNamespace(
        find_authoritative_trace=lambda *_args, action, **_kwargs: (
            "one" if action == "accept" else "two"
        )
    )
    with pytest.raises(RuntimeError, match="could not be verified"):
        bridge._authoritative_trace_for_response("session", "draft")
    with pytest.raises(RuntimeError, match="action is invalid"):
        bridge._terminal_completion_result("invalid")

    helper_bridge = _bridge()
    finalize_module = importlib.import_module("agency_runtime.core.header.finalize")
    monkeypatch.setattr(finalize_module, "terminal_response_run", lambda *_args, **_kwargs: None)
    assert helper_bridge._exact_terminal_finalization("session", "trace", "draft") is None
    monkeypatch.setattr(
        finalize_module,
        "terminal_response_run",
        lambda *_args, **_kwargs: {
            "authoritative": True,
            "action": "accept",
            "terminal_status": "completed",
            "status": "completed",
        },
    )
    exact_run = helper_bridge._exact_terminal_finalization("session", "trace", "draft")
    assert exact_run is not None and str(exact_run.get("action") or "") == "accept"
    helper_bridge.store = SimpleNamespace(get_run=lambda _trace: None)
    assert not helper_bridge._is_terminal_turn("session", "trace")

    helper_bridge.adapter = SimpleNamespace(
        evaluate_completion_policy=lambda *_args, **_kwargs: {"action": "accept"}
    )
    verification = helper_bridge._verify_final_response(
        "draft",
        correlation=correlation,
        trace_id="trace",
        retry=False,
    )
    assert verification["verification_unavailable"] is True


def test_base_adapter_ignores_unavailable_native_child_recorders(monkeypatch) -> None:
    observations: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "agency_runtime.adapters.base._record_native_delegation_observation",
        lambda _store, **kwargs: observations.append(kwargs),
    )
    openclaw = _Adapter(store=_EnabledStore())  # type: ignore[arg-type]
    openclaw.host_name = "openclaw"
    openclaw.record_tool_call(
        tool_name="sessions_spawn",
        args={"goal": "work", "taskName": "unit"},
        result={"childSessionKey": "child", "native_run_id": "run"},
        session_id="session",
        trace_id="trace",
    )
    claude = _Adapter(store=_EnabledStore())  # type: ignore[arg-type]
    claude.host_name = "claude"
    claude.record_tool_call(
        tool_name="delegate_task",
        args={"goal": "work", "work_unit_id": "unit"},
        result={"agent_id": "child", "native_run_id": "run"},
        session_id="session",
        trace_id="trace",
    )
    assert len(observations) == 2


def test_base_adapter_delegation_failure_batch_and_provider_projection(monkeypatch) -> None:
    outcomes: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "agency_runtime.core.delegation.events.mark_delegation_skipped",
        lambda **kwargs: outcomes.append(("skipped", kwargs)),
    )
    monkeypatch.setattr(
        "agency_runtime.core.delegation.events.mark_delegation_executed",
        lambda **kwargs: outcomes.append(("executed", kwargs)),
    )
    common = {
        "store": object(),
        "session_id": "session",
        "host": "codex",
        "agent": "reviewer",
        "backend": "spawn_agent",
        "goal": "review",
        "work_unit_id": "unit",
        "trace_id": "trace",
        "executed_worker_kind": "generic-worker",
        "executed_worker_id": "worker",
        "native_run_id": "run",
    }
    base_adapter._record_native_delegation_observation(
        **common,
        failure_reason="worker failed",
    )
    assert outcomes[0][0] == "skipped"
    assert (
        base_adapter._tool_call_failure_reason(
            {"result": {"status": "failed", "error": "worker failed"}}
        )
        == "worker failed"
    )

    observations: list[dict[str, Any]] = []
    monkeypatch.setattr(
        base_adapter,
        "_record_native_delegation_observation",
        lambda _store, **kwargs: observations.append(kwargs),
    )
    adapter = _Adapter(store=_EnabledStore())  # type: ignore[arg-type]
    adapter.record_tool_call(
        tool_name="skill_view",
        args={"name": ""},
        session_id="session",
        trace_id="trace",
    )
    adapter.record_tool_call(
        tool_name="delegate_task",
        args={"tasks": [{"goal": "review", "work_unit_id": "unit"}]},
        result={"results": [{"task_index": 0, "agent_id": "worker", "native_run_id": "run"}]},
        session_id="session",
        trace_id="trace",
    )
    assert observations and observations[0]["goal"] == "review"

    receipts: list[dict[str, Any]] = []

    class ReceiptStore(_EnabledStore):
        def get_run(self, _trace: str) -> dict[str, str]:
            return {"session_id": "session", "status": "active"}

        def record_model_receipt(self, **kwargs: Any) -> None:
            receipts.append(kwargs)

    adapter.store = ReceiptStore()  # type: ignore[assignment]
    adapter.post_api_request_handler(
        session_id="session",
        trace_id="trace",
        requested_model="router",
        resolved_model="openai/concrete-model",
    )
    assert receipts[0]["resolved_provider"] == "openai"
    assert receipts[0]["resolved_model"] == "concrete-model"


def test_openclaw_terminal_correlation_and_state_matrix() -> None:
    digest = node_bridge.response_hash("draft")

    def legacy_store(*, ambiguous: bool = False) -> SimpleNamespace:
        def legacy_trace(_session: str, *, action: str, **_kwargs: Any) -> object:
            if ambiguous:
                return "first" if action == "accept" else "second"
            return object()

        return SimpleNamespace(
            get_open_traces_for_session=lambda _session: [],
            find_authoritative_trace_by_policy_hash=lambda *_args, **_kwargs: None,
            find_authoritative_trace=lambda *_args, **_kwargs: legacy_trace(
                _args[0],
                action=_kwargs["action"],
            ),
            get_authoritative_finalization=lambda *_args, **_kwargs: {"policy_response_hash": ""},
        )

    with pytest.raises(RuntimeError, match="correlation is invalid"):
        node_bridge._recover_exact_terminal_trace(
            SimpleNamespace(store=legacy_store()),
            "session",
            "draft",
        )

    def finder(_session: str, *, action: str, **_kwargs: Any) -> str:
        return "first" if action == "accept" else "second"

    store = legacy_store(ambiguous=True)
    store.find_authoritative_trace = finder
    store.get_authoritative_finalization = lambda *_args, **_kwargs: {
        "policy_response_hash": "",
    }
    with pytest.raises(RuntimeError, match="correlation is invalid"):
        node_bridge._recover_exact_terminal_trace(
            SimpleNamespace(store=store),
            "session",
            "draft",
        )

    adapter = SimpleNamespace(store=SimpleNamespace())
    assert (
        node_bridge._exact_policy_terminal_state(
            adapter,
            session_id="",
            trace_id="trace",
            final_response="draft",
        )
        == ""
    )

    def every_action(
        _session: str,
        _trace: str,
        *,
        action: str,
        policy_response_hash: str = "",
        response_hash: str = "",
    ) -> dict[str, Any]:
        status = node_bridge.TERMINAL_ACTION_STATUS[action]
        return {
            "authoritative": True,
            "action": action,
            "terminal_status": status,
            "status": status,
            "policy_response_hash": policy_response_hash or response_hash or digest,
        }

    adapter.store = SimpleNamespace(get_authoritative_finalization=every_action)
    with pytest.raises(RuntimeError, match="ambiguous"):
        node_bridge._exact_policy_terminal_state(
            adapter,
            session_id="session",
            trace_id="trace",
            final_response="draft",
        )
    with pytest.raises(RuntimeError, match="action is invalid"):
        node_bridge._terminal_pre_verify_result("invalid", "draft", "trace")

    assert node_bridge._terminal_turn_status(adapter, "", "trace") == ""
    adapter.store = SimpleNamespace()
    with pytest.raises(RuntimeError, match="could not be verified"):
        node_bridge._terminal_turn_status(adapter, "session", "trace")
    adapter.store = SimpleNamespace(get_run=lambda _trace: None)
    assert node_bridge._terminal_turn_status(adapter, "session", "trace") == ""
    adapter.store = SimpleNamespace(get_run=lambda _trace: {"session_id": "other"})
    with pytest.raises(RuntimeError, match="correlation is invalid"):
        node_bridge._terminal_turn_status(adapter, "session", "trace")

    failure = node_bridge._revision("verification unavailable")
    assert failure["action"] == "terminal"
    assert failure["terminalRejected"] is True
    assert failure["terminalStatus"] == "verification_failed"
    assert failure["turnId"] == ""


def test_openclaw_outbound_rejection_preverify_and_native_child_matrix(monkeypatch) -> None:
    digest = node_bridge.response_hash("draft")
    declined = {
        "authoritative": True,
        "action": "delegation_declined",
        "terminal_status": "delegation_declined",
        "status": "delegation_declined",
        "response_hash": digest,
    }
    adapter = SimpleNamespace(
        store=SimpleNamespace(
            get_authoritative_finalization=lambda _session, _trace, *, action, **_kwargs: (
                declined if action == "delegation_declined" else None
            )
        )
    )
    assert (
        node_bridge._exact_outbound_terminal_state(
            adapter,
            session_id="session",
            trace_id="trace",
            digest=digest,
        )
        == "delegation_declined"
    )

    adapter = SimpleNamespace(
        runtime_enabled=lambda: True,
        store=SimpleNamespace(
            get_authoritative_finalization=lambda *_args, **_kwargs: None,
        ),
    )
    monkeypatch.setattr(
        node_bridge,
        "_safe_policy_decision",
        lambda *_args, **_kwargs: {
            "action": "continue",
            "evidence_revision": 1,
        },
    )
    monkeypatch.setattr(node_bridge, "_commit_terminal_outcome", lambda *_args, **_kwargs: True)
    rejected = node_bridge._handle_outbound_gate(
        adapter,
        session_id="session",
        trace_id="trace",
        final_response="draft",
    )
    assert rejected["action"] == "replace"

    active = SimpleNamespace(
        runtime_enabled=lambda: True,
        store=SimpleNamespace(get_run=lambda _trace: (_ for _ in ()).throw(OSError("unavailable"))),
    )
    monkeypatch.setattr(
        node_bridge, "_effective_pre_verify_trace", lambda *_args, **_kwargs: "trace"
    )
    monkeypatch.setattr(node_bridge, "_exact_policy_terminal_state", lambda *_args, **_kwargs: "")
    result = node_bridge._handle_pre_verify(
        active,
        {"finalResponse": "draft"},
        session_id="session",
        trace_id="trace",
        model="model",
    )
    assert result["action"] in {"continue", "terminal"}

    calls: list[tuple[str, dict[str, Any]]] = []

    class NativeStore:
        def record_native_child_started(self, **kwargs: Any) -> None:
            calls.append(("started", kwargs))

        def record_native_child_ended(self, **kwargs: Any) -> None:
            calls.append(("ended", kwargs))

    native_adapter = SimpleNamespace(store=NativeStore())
    assert (
        node_bridge._handle_observation_action(
            native_adapter,
            {"action": "native_child_started"},
            action="native_child_started",
            session_id="",
            trace_id="",
        )
        == {}
    )
    assert (
        node_bridge._handle_observation_action(
            native_adapter,
            {
                "action": "native_child_started",
                "workerId": "worker",
                "nativeRunId": "run",
            },
            action="native_child_started",
            session_id="session",
            trace_id="trace",
        )
        == {}
    )
    assert (
        node_bridge._handle_observation_action(
            native_adapter,
            {"action": "native_child_ended"},
            action="native_child_ended",
            session_id="",
            trace_id="",
        )
        == {}
    )
    assert (
        node_bridge._handle_observation_action(
            native_adapter,
            {
                "action": "native_child_ended",
                "workerId": "worker",
                "nativeRunId": "run",
                "outcome": "completed",
            },
            action="native_child_ended",
            session_id="session",
            trace_id="trace",
        )
        == {}
    )
    assert [name for name, _kwargs in calls] == ["started", "ended"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("failed", "error"),
        ("timeout", "timeout"),
        ("cancelled", "killed"),
        ("reset", "reset"),
        ("unexpected", "unknown"),
    ],
)
def test_hermes_native_child_outcome_matrix(value: str, expected: str) -> None:
    assert hermes_bridge._native_child_outcome(value) == expected


def test_hermes_retry_and_native_child_validation_matrix() -> None:
    class Store:
        def __init__(self) -> None:
            self.events: list[tuple[str, dict[str, Any]]] = []

        def resolve_pending_internal_retry(self, *_args: Any) -> str:
            raise OSError("unavailable")

        def record_native_child_started(self, **kwargs: Any) -> None:
            self.events.append(("started", kwargs))

        def record_native_child_ended(self, **kwargs: Any) -> None:
            self.events.append(("ended", kwargs))

    store = Store()
    adapter = SimpleNamespace(
        store=store,
        pre_llm_call_handler=lambda **kwargs: kwargs,
        post_tool_call_handler=lambda **kwargs: store.events.append(("tool", kwargs)),
    )
    result = hermes_bridge._pre_llm_call(
        adapter,
        {"user_message": "review", "model": "model"},
        session_id="session",
        trace_id="trace",
    )
    assert result["trace_id"] == "trace"
    adapter_without_retry_resolver = SimpleNamespace(
        store=SimpleNamespace(),
        pre_llm_call_handler=lambda **kwargs: kwargs,
    )
    assert (
        hermes_bridge._pre_llm_call(
            adapter_without_retry_resolver,
            {"user_message": "review", "model": "model"},
            session_id="session",
            trace_id="trace",
        )["trace_id"]
        == "trace"
    )

    store.resolve_pending_internal_retry = lambda _session, trace: trace  # type: ignore[method-assign]
    assert (
        hermes_bridge._pre_llm_call(
            adapter,
            {"user_message": "retry", "model": "model"},
            session_id="session",
            trace_id="trace",
        )
        is None
    )

    assert (
        hermes_bridge.handle(
            {"action": "native_child_started", "session_id": "session"},
            adapter=adapter,
        )
        is None
    )
    assert (
        hermes_bridge.handle(
            {
                "action": "native_child_started",
                "session_id": "session",
                "trace_id": "trace",
                "worker_id": "worker",
                "native_run_id": "run",
                "goal": "review",
            },
            adapter=adapter,
        )
        is None
    )
    assert (
        hermes_bridge.handle(
            {"action": "native_child_ended", "session_id": "session"},
            adapter=adapter,
        )
        is None
    )
    assert (
        hermes_bridge.handle(
            {
                "action": "native_child_ended",
                "session_id": "session",
                "trace_id": "trace",
                "worker_id": "worker",
                "native_run_id": "run",
                "outcome": "failed",
            },
            adapter=adapter,
        )
        is None
    )
    assert [name for name, _kwargs in store.events] == ["tool", "started", "ended"]


def test_mcp_preflight_rejects_a_nonexecution_host() -> None:
    # The decline_delegation half of this matrix went with `agency.decline_delegation`
    # in eab8c085.
    assert (
        "execution host"
        in mcp_tools._preflight(
            {"session_id": "session", "host": "browser", "user_message": "review"},
            SimpleNamespace(),
        )["error"]
    )


def test_mcp_search_missing_prompt_skill_success_and_unknown_dispatch(monkeypatch) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.selector.candidate_narrow.pre_narrow",
        lambda query, catalog, *, limit: ([{"slug": query, "catalog": catalog}], [1.0]),
    )
    search_store = SimpleNamespace(get_active_roster_as_catalog=lambda: [{"slug": "reviewer"}])
    assert (
        mcp_tools._search_agents({"query": "security"}, search_store)["agents"][0]["slug"]
        == "security"
    )

    class ActiveStore:
        def __init__(self) -> None:
            self.skills: list[tuple[str, str, str]] = []

        def get_run(self, _trace: str) -> dict[str, Any]:
            return {
                "session_id": "session",
                "status": "active",
                "ended_at": None,
                "preflight_state": "ready",
            }

        def requires_delegation_activation(self, **_kwargs: Any) -> bool:
            return False

        def get_specialist_prompt(self, _slug: str) -> None:
            return None

        def record_skill_loaded(
            self,
            session_id: str,
            skill_name: str,
            *,
            trace_id: str,
        ) -> None:
            self.skills.append((session_id, skill_name, trace_id))

    store = ActiveStore()
    correlation = {
        "session_id": "session",
        "trace_id": "trace",
    }
    assert (
        "not found"
        in mcp_tools._load_specialist(
            {**correlation, "slug": "missing"},
            store,
        )["error"]
    )
    assert mcp_tools._record_skill_loaded(
        {**correlation, "skill_name": "review"},
        store,
    ) == {"status": "recorded"}
    assert store.skills == [("session", "review", "trace")]
    assert mcp_tools.dispatch_tool_call("agency.unknown", {}, store) == {
        "error": "unknown tool: agency.unknown"
    }
