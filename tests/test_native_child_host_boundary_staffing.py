"""Rule 4 on Hermes and OpenClaw: a host-spawned child is dealt its own cards.

Claude and ZCode already prove this by driving their real hook boundary. Hermes
and OpenClaw had only a synthetic adapter subclass calling `build_preflight_context`
directly, which cannot speak for the shipped plugin classes or for the bridges
that actually receive a child launch -- the same substitution the ZCode Rule 7
work had to undo.

These cases drive the real `handle()` entry point of each bridge with the real
adapter class, using the payload shape the host really sends, and assert that
the exact inference-selected team -- plural, ordered, correlated to the host's
own parent and child identities -- reaches the child before the child model
runs. The staffing service is stubbed at the same boundary the Claude and ZCode
Rule 4 cases stub it, so the claim is like for like.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hermes import bridge as hermes_bridge
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw import node_bridge as openclaw_bridge
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core import native_child_install_identity, native_child_staffing
from agency_runtime.core.native_child_install_identity import NativeChildInstallIdentity
from agency_runtime.core.native_child_staffing import NativeChildStaffingResult
from agency_runtime.core.store.sqlite import Store

_TASK = "Review the exact child assignment for correctness and exposure."

# Plural, and ordered: rule 4 says children get cards, not a card.
_TEAM = ("code-reviewer", "software-architect")
_SEGMENT = "\n\n[exact inference team: code-reviewer, software-architect]"

_PARENT_SESSION = "parent-session"
_PARENT_TRACE = "parent-trace"
_CHILD_WORKER = "child-worker"
_NATIVE_RUN = "native-run-one"


def _install(host: str) -> NativeChildInstallIdentity:
    return NativeChildInstallIdentity(
        host=host,
        plugin_version="test",
        install_id="install-one",
        bundle_digest="b" * 64,
        running_runtime_digest="c" * 64,
        candidate_digest="c" * 64,
    )


def _bind_staffing(monkeypatch: pytest.MonkeyPatch, calls: list[dict[str, Any]]) -> None:
    def staff(_store: object, **kwargs: Any) -> NativeChildStaffingResult:
        calls.append(kwargs)
        return NativeChildStaffingResult(
            staffed=True,
            reason_code="staffed",
            rewritten_task=str(kwargs["task"]) + _SEGMENT,
            context_segment=_SEGMENT,
            decision_id="decision-one",
            selected_ids=_TEAM,
            native_child_delivery={"schema": "test"},
        )

    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)
    monkeypatch.setattr(
        native_child_install_identity,
        "current_managed_host_install_identity",
        lambda actual_host, **_kwargs: _install(actual_host),
    )


def _store(tmp_path: Path) -> Store:
    return Store(tmp_path / "agency.db")


def _call_host_bridge(host: str, store: Store) -> dict[str, Any]:
    """Send the child launch the way the host's own bridge receives it."""

    if host == "hermes":
        return dict(
            hermes_bridge.handle(
                {
                    "action": "pre_llm_call",
                    "session_id": "child-session",
                    "trace_id": "child-trace",
                    "user_message": _TASK,
                    "parent_session_id": _PARENT_SESSION,
                    "parent_trace_id": _PARENT_TRACE,
                    "native_worker_id": _CHILD_WORKER,
                    "native_run_id": _NATIVE_RUN,
                },
                adapter=HermesAdapter(store=store),
            )
            or {}
        )
    return dict(
        openclaw_bridge.handle(
            {
                "action": "preflight",
                "sessionId": "child-session",
                "traceId": "child-trace",
                "userMessage": _TASK,
                "parentSessionId": _PARENT_SESSION,
                "parentTraceId": _PARENT_TRACE,
                "workerId": _CHILD_WORKER,
                "nativeRunId": _NATIVE_RUN,
            },
            adapter=OpenClawAdapter(store=store),
        )
        or {}
    )


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
def test_a_host_spawned_child_receives_its_exact_team_at_the_real_bridge(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 4: the child gets the whole team, before the child model runs."""

    calls: list[dict[str, Any]] = []
    _bind_staffing(monkeypatch, calls)

    result = _call_host_bridge(host, _store(tmp_path))

    # The cards reach the child's own context, in the order inference chose.
    assert result["selected_ids"] == list(_TEAM)
    assert result["semantic_ids"] == list(_TEAM)
    assert _SEGMENT in str(result["context"])
    assert result["status"] == "applied"
    assert result["native_child_decision_id"] == "decision-one"
    assert result["native_child_reason"] == "staffed"


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
def test_the_child_team_is_bound_to_the_hosts_own_launch_identity(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The host started the child, so the host's identities are what correlate it."""

    calls: list[dict[str, Any]] = []
    _bind_staffing(monkeypatch, calls)

    _call_host_bridge(host, _store(tmp_path))

    [call] = calls
    assert call["host"] == host
    assert call["task"] == _TASK
    assert call["parent_session_id"] == _PARENT_SESSION
    assert call["parent_trace_id"] == _PARENT_TRACE
    assert call["launch_id"] == _NATIVE_RUN
    assert call["binding_kind"] == "child_id"
    assert call["binding_id"] == _CHILD_WORKER
    assert call["install_identity"] == _install(host)


@pytest.mark.parametrize("host", ["hermes", "openclaw"])
def test_a_child_without_full_host_correlation_is_left_unstaffed(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Partial correlation must not be guessed at: an unbindable child gets nothing.

    Without this the suite could pass on a path that staffs any child it is told
    about, which is the opposite of correlating one to its own parent.
    """

    calls: list[dict[str, Any]] = []
    _bind_staffing(monkeypatch, calls)
    store = _store(tmp_path)

    if host == "hermes":
        result = (
            hermes_bridge.handle(
                {
                    "action": "pre_llm_call",
                    "session_id": "child-session",
                    "trace_id": "child-trace",
                    "user_message": _TASK,
                    "parent_session_id": _PARENT_SESSION,
                    "parent_trace_id": _PARENT_TRACE,
                    "native_worker_id": "",
                    "native_run_id": "",
                },
                adapter=HermesAdapter(store=store),
            )
            or {}
        )
    else:
        result = (
            openclaw_bridge.handle(
                {
                    "action": "preflight",
                    "sessionId": "child-session",
                    "traceId": "child-trace",
                    "userMessage": _TASK,
                    "parentSessionId": _PARENT_SESSION,
                    "parentTraceId": _PARENT_TRACE,
                    "workerId": "",
                    "nativeRunId": "",
                },
                adapter=OpenClawAdapter(store=store),
            )
            or {}
        )

    assert calls == []
    assert _SEGMENT not in str(result.get("context") or "")
