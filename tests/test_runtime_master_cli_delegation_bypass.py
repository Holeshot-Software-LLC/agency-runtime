"""Work-free CLI and direct delegation behavior while Agency is globally off."""

from __future__ import annotations

from argparse import Namespace
from typing import Any

import pytest

import agency_runtime.cli.roster_commands as roster_commands
import agency_runtime.core.delegation.lifecycle as lifecycle
import agency_runtime.core.runtime_control as runtime_control
from agency_runtime.core.delegation import dispatch_work_units
from agency_runtime.core.delegation.lifecycle_types import DependencyGraph, WorkUnit


class _UnexpectedAccess(AssertionError):
    """Raised when a disabled boundary performs Agency work."""


def _unexpected(*_args: Any, **_kwargs: Any) -> Any:
    raise _UnexpectedAccess("global-off boundary performed Agency work")


def _disable_agency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_control, "master_enabled", lambda: False)


def test_cli_search_global_off_bypasses_before_store(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _disable_agency(monkeypatch)
    emitted: list[Any] = []
    monkeypatch.setattr(roster_commands, "_store", _unexpected)
    monkeypatch.setattr(roster_commands, "pre_narrow", _unexpected)
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)

    result = roster_commands.cmd_search(Namespace(query="review this", limit=10, json=True))

    assert result == 0
    assert emitted == [
        {
            "runtime_enabled": False,
            "bypassed": True,
            "query": "review this",
            "agents": [],
            "count": 0,
        }
    ]

    assert roster_commands.cmd_search(Namespace(query="review this", limit=10, json=False)) == 0
    assert capsys.readouterr().out.strip() == (
        "Agency Runtime is globally disabled; agent search was bypassed."
    )


def test_cli_route_global_off_bypasses_before_store_and_routing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _disable_agency(monkeypatch)
    emitted: list[Any] = []
    monkeypatch.setattr(roster_commands, "_store", _unexpected)
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)
    arguments = Namespace(task="route this", limit=10, json=True)

    assert roster_commands.cmd_route(arguments) == 0

    assert emitted == [
        {
            "task": "route this",
            "routing": {
                "runtime_enabled": False,
                "bypassed": True,
                "trace_id": "",
                "selected_ids": [],
                "semantic_ids": [],
                "confidence": 0.0,
                "latency_ms": 0,
                "status": "bypassed",
                "source": "master_control",
                "provider": "master_control",
                "work_units": {
                    "count": 0,
                    "confidence": "none",
                    "source": "master_control",
                    "units": [],
                    "delegate": False,
                },
            },
            "candidates": [],
        }
    ]

    arguments.json = False
    assert roster_commands.cmd_route(arguments) == 0
    assert capsys.readouterr().out.splitlines() == [
        "selected: none (status=bypassed)",
        "confidence=0.000 source=master_control trace=none",
    ]


def test_cli_explain_global_off_bypasses_before_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_agency(monkeypatch)
    emitted: list[Any] = []
    monkeypatch.setattr(roster_commands, "_store", _unexpected)
    monkeypatch.setattr(roster_commands, "explain_route", _unexpected)
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)

    result = roster_commands.cmd_explain(
        Namespace(session_id="session", task="explain this", limit=10)
    )

    assert result == 0
    assert emitted == [
        {
            "runtime_enabled": False,
            "bypassed": True,
            "session_id": "session",
            "task": "explain this",
            "routing": {
                "runtime_enabled": False,
                "bypassed": True,
                "trace_id": "",
                "selected_ids": [],
                "semantic_ids": [],
                "confidence": 0.0,
                "latency_ms": 0,
                "status": "bypassed",
                "source": "master_control",
                "provider": "master_control",
                "work_units": {
                    "count": 0,
                    "confidence": "none",
                    "source": "master_control",
                    "units": [],
                    "delegate": False,
                },
            },
            "selected": [],
            "considered_candidates": [],
            "rejected_candidates": [],
            "signals": {"source": "master_control"},
        }
    ]


def test_public_dispatch_global_off_never_invokes_delegate_or_dispatcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_agency(monkeypatch)
    monkeypatch.setattr(lifecycle._dispatch, "dispatch_work_units", _unexpected)
    unit = WorkUnit("unit", "perform delegated work")
    graph = DependencyGraph(edges={"unit": set()})

    result = dispatch_work_units(
        [unit],
        graph,
        {},
        delegate_func=_unexpected,
        max_workers=0,
    )

    assert result == ({}, [], [])
