"""Focused adapter wiring for host-owned native-child staffing and launch joins."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.adapters import base as base_adapter
from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core import native_child_install_identity, native_child_staffing
from agency_runtime.core.native_child_install_identity import NativeChildInstallIdentity
from agency_runtime.core.native_child_staffing import NativeChildStaffingResult


class _Adapter(BaseAdapter):
    def __init__(self, host: str, store: Any) -> None:
        super().__init__(store=store)
        self.host_name = host

    def is_available(self) -> bool:
        return True

    def runtime_enabled(self) -> bool:
        return True


def _install(host: str) -> NativeChildInstallIdentity:
    return NativeChildInstallIdentity(
        host=host,
        plugin_version="test",
        install_id="install-one",
        bundle_digest="b" * 64,
        running_runtime_digest="c" * 64,
        candidate_digest="c" * 64,
    )


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
def test_native_child_pre_model_adapter_uses_exact_inference_service_and_child_binding(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
) -> None:
    calls: list[dict[str, Any]] = []

    def staff(_store: object, **kwargs: Any) -> NativeChildStaffingResult:
        calls.append(kwargs)
        return NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task=str(kwargs["task"]) + "\n\n[exact team]",
            context_segment="\n\n[exact team]",
            decision_id="decision-one",
            selected_ids=("code-reviewer", "software-architect"),
            native_child_delivery={"schema": "test"},
        )

    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)
    monkeypatch.setattr(
        native_child_install_identity,
        "current_managed_host_install_identity",
        lambda actual_host: _install(actual_host),
    )
    adapter = _Adapter(host, object())

    result = adapter.build_preflight_context(
        "child-session",
        "Review the exact child assignment.",
        parent_session_id="parent-session",
        parent_trace_id="parent-trace",
        native_worker_id="child-worker",
        native_run_id="native-run-one",
    )

    assert result == {
        "status": "applied",
        "semantic_status": "applied",
        "context": "\n\n[exact team]",
        "selected_ids": ["code-reviewer", "software-architect"],
        "semantic_ids": ["code-reviewer", "software-architect"],
        "native_child_delivery": {"schema": "test"},
        "native_child_decision_id": "decision-one",
        "native_child_reason": "staffed",
    }
    [call] = calls
    assert call["host"] == host
    assert call["task"] == "Review the exact child assignment."
    assert call["parent_session_id"] == "parent-session"
    assert call["parent_trace_id"] == "parent-trace"
    assert call["launch_id"] == "native-run-one"
    assert call["binding_kind"] == "child_id"
    assert call["binding_id"] == "child-worker"
    assert call["install_identity"] == _install(host)
    assert call["install_identity_reader"](host) == _install(host)


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
@pytest.mark.parametrize(
    "missing",
    ["parent_session_id", "parent_trace_id", "native_worker_id", "native_run_id"],
)
def test_native_child_pre_model_adapter_partial_correlation_fails_open_without_staffing(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
    missing: str,
) -> None:
    monkeypatch.setattr(
        native_child_staffing,
        "staff_native_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("staffing invoked")),
    )
    fields = {
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-trace",
        "native_worker_id": "child-worker",
        "native_run_id": "native-run-one",
    }
    fields[missing] = ""

    assert (
        _Adapter(host, object()).build_preflight_context(
            "child-session",
            "Review the exact child assignment.",
            **fields,
        )
        is None
    )


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
@pytest.mark.parametrize("mode", ["unstaffed", "exception"])
def test_native_child_pre_model_adapter_inference_failure_never_blocks_host(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
    mode: str,
) -> None:
    if mode == "exception":

        def replacement(*_args: Any, **_kwargs: Any) -> NativeChildStaffingResult:
            raise RuntimeError("offline")
    else:

        def replacement(*_args: Any, **_kwargs: Any) -> NativeChildStaffingResult:
            return NativeChildStaffingResult(
                staffed=False,
                reason_code="native_child_inference_unavailable",
                rewritten_task="Review the exact child assignment.",
            )

    monkeypatch.setattr(native_child_staffing, "staff_native_child", replacement)
    monkeypatch.setattr(
        native_child_install_identity,
        "current_managed_host_install_identity",
        lambda actual_host: _install(actual_host),
    )

    assert (
        _Adapter(host, object()).build_preflight_context(
            "child-session",
            "Review the exact child assignment.",
            parent_session_id="parent-session",
            parent_trace_id="parent-trace",
            native_worker_id="child-worker",
            native_run_id="native-run-one",
        )
        is None
    )


class _LaunchStore:
    def __init__(self) -> None:
        self.ended: list[dict[str, Any]] = []
        self.bindings: list[dict[str, Any]] = []

    def record_native_child_ended(self, **kwargs: Any) -> None:
        self.ended.append(kwargs)

    def bind_native_child_launch(self, **kwargs: Any) -> bool:
        self.bindings.append(kwargs)
        return True


@pytest.mark.parametrize("host", ["claude", "zcode"])
def test_post_tool_adapter_binds_host_child_to_exact_pretool_launch(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
) -> None:
    monkeypatch.setattr(
        base_adapter, "_record_native_delegation_observation", lambda *_a, **_k: None
    )
    store = _LaunchStore()
    adapter = _Adapter(host, store)

    adapter.record_tool_call(
        tool_name="delegate_task",
        args={"goal": "Review the exact child assignment."},
        result={"agent_id": "child-worker", "native_run_id": "native-run-one"},
        session_id="parent-session",
        trace_id="parent-trace",
        tool_use_id="launch-one",
    )

    assert len(store.ended) == 1
    assert store.ended[0]["worker_id"] == "child-worker"
    assert store.ended[0]["native_run_id"] == "native-run-one"
    assert store.bindings == [
        {
            "host": host,
            "session_id": "parent-session",
            "trace_id": "parent-trace",
            "worker_id": "child-worker",
            "native_run_id": "native-run-one",
            "launch_id": "launch-one",
        }
    ]


@pytest.mark.parametrize("host", ["claude", "zcode"])
def test_post_tool_adapter_never_invents_a_missing_launch_identity(
    monkeypatch: pytest.MonkeyPatch,
    host: str,
) -> None:
    monkeypatch.setattr(
        base_adapter, "_record_native_delegation_observation", lambda *_a, **_k: None
    )
    store = _LaunchStore()

    _Adapter(host, store).record_tool_call(
        tool_name="delegate_task",
        args={"goal": "Review the exact child assignment."},
        result={"agent_id": "child-worker", "native_run_id": "native-run-one"},
        session_id="parent-session",
        trace_id="parent-trace",
    )

    assert len(store.ended) == 1
    assert store.bindings == []
