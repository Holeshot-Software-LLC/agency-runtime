"""Truthful installation-backed host context for CLI routing diagnostics."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agency_runtime.cli import roster_commands
from agency_runtime.core import host_capabilities, host_control


def test_disabled_candidate_shadow_is_human_visible(capsys: pytest.CaptureFixture[str]) -> None:
    roster_commands._print_disabled_candidate_shadows(
        {
            "disabled_candidate_shadows": [
                None,
                {"agent_id": ""},
                {
                    "agent_id": "typescript-application-engineer",
                    "fallback_agent_id": "backend-service-engineer",
                },
            ]
        }
    )

    assert capsys.readouterr().out == (
        "left on the table: disabled typescript-application-engineer ranked higher; "
        "used backend-service-engineer\n"
    )


def _status(
    host: str = "codex",
    *,
    effective_enabled: object = True,
    capability_status: str = "native-installation-verified",
) -> dict[str, object]:
    return {
        "host": host,
        "effective_enabled": effective_enabled,
        "execution_capabilities": {
            "status": capability_status,
            "platform": "windows",
        },
    }


def test_route_host_context_requires_one_exact_diagnostic_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert roster_commands._route_host_context(None) == (
        {},
        {"host_proof": "no_verified_host", "verified_hosts": []},
    )

    def unavailable(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        raise PermissionError("blocked")

    monkeypatch.setattr(host_control, "inspect_all_host_statuses", unavailable)
    assert roster_commands._route_host_context(object())[0] == {}

    monkeypatch.setattr(
        host_control,
        "inspect_all_host_statuses",
        lambda *_args, **_kwargs: [
            _status(effective_enabled=False),
            {
                "host": "openclaw",
                "effective_enabled": True,
                "execution_capabilities": [],
            },
            _status("claude", capability_status="native-evidence-unproven"),
        ],
    )
    assert roster_commands._route_host_context(object()) == (
        {},
        {"host_proof": "no_verified_host", "verified_hosts": []},
    )

    monkeypatch.setattr(
        host_control,
        "inspect_all_host_statuses",
        lambda *_args, **_kwargs: [_status()],
    )
    monkeypatch.setattr(
        host_capabilities,
        "diagnostic_installation_capability_receipt",
        lambda *_args, **_kwargs: None,
    )
    assert roster_commands._route_host_context(object())[0] == {}

    receipt = SimpleNamespace(as_dict=lambda: {"status": "native-installation-verified"})
    monkeypatch.setattr(
        host_capabilities,
        "diagnostic_installation_capability_receipt",
        lambda *_args, **_kwargs: receipt,
    )
    context, proof = roster_commands._route_host_context(object())
    assert context == {"host": "codex", "platform": "windows", "capability_receipt": receipt}
    assert proof == {"host_proof": "single_verified", "verified_hosts": ["codex"]}


def test_several_verified_hosts_are_disambiguated_rather_than_discarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AR-374: an ordinary multi-host installation must not prove zero hosts.

    The previous rule proved a host only when exactly one was verified, so a box
    with codex, hermes and openclaw all installed rejected every candidate
    `execution_host_unproven` -- more installation meant less capability.
    """

    receipt = SimpleNamespace(as_dict=lambda: {"status": "native-installation-verified"})
    monkeypatch.setattr(
        host_control,
        "inspect_all_host_statuses",
        lambda *_args, **_kwargs: [_status("openclaw"), _status("codex"), _status("hermes")],
    )
    monkeypatch.setattr(
        host_capabilities,
        "diagnostic_installation_capability_receipt",
        lambda *_args, **_kwargs: receipt,
    )

    context, proof = roster_commands._route_host_context(object())
    assert context == {}
    assert proof == {
        "host_proof": "ambiguous_host",
        "verified_hosts": ["codex", "hermes", "openclaw"],
    }

    context, proof = roster_commands._route_host_context(object(), "hermes")
    assert context["host"] == "hermes"
    assert proof["host_proof"] == "requested"

    context, proof = roster_commands._route_host_context(object(), "  CODEX  ")
    assert context["host"] == "codex"

    context, proof = roster_commands._route_host_context(object(), "zcode")
    assert context == {}
    assert proof == {
        "host_proof": "requested_host_unverified",
        "requested_host": "zcode",
        "verified_hosts": ["codex", "hermes", "openclaw"],
    }


def test_unproven_host_is_stated_rather_than_implied(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A ranking nothing was eligible for must not read like a real ranking."""

    roster_commands._print_host_proof(
        {"host_proof": "ambiguous_host", "verified_hosts": ["codex", "hermes"]}
    )
    out = capsys.readouterr().out
    assert "host: not proven" in out
    assert "codex, hermes" in out
    assert "score order only" in out

    roster_commands._print_host_proof(
        {"host_proof": "single_verified", "verified_hosts": ["codex"]}
    )
    assert capsys.readouterr().out == ""


def test_route_and_explain_forward_the_verified_diagnostic_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core.selector import candidate_narrow, pipeline

    receipt = object()
    host_context = {
        "host": "codex",
        "platform": "windows",
        "capability_receipt": receipt,
    }
    operation = roster_commands._RoutingOperation(
        store=SimpleNamespace(get_turn_state_context=lambda _session_id: {"state_known": True}),
        snapshot=SimpleNamespace(catalog=[{"slug": "agent"}], config=object()),
        receipt=None,
    )
    monkeypatch.setattr(roster_commands, "_runtime_enabled", lambda: True)
    monkeypatch.setattr(roster_commands, "_routing_operation", lambda **_kwargs: operation)
    monkeypatch.setattr(
        roster_commands,
        "_route_host_context",
        lambda _store, _requested="": (
            host_context,
            {"host_proof": "single_verified", "verified_hosts": ["codex"]},
        ),
    )
    monkeypatch.setattr(
        candidate_narrow,
        "pre_narrow",
        lambda *_args, **_kwargs: ([{"slug": "agent"}], [1.0]),
    )
    route_kwargs: dict[str, object] = {}

    def fake_route(*_args: object, **kwargs: object) -> dict[str, object]:
        route_kwargs.update(kwargs)
        return {"selected_ids": ["agent"]}

    monkeypatch.setattr(pipeline, "route", fake_route)
    emitted: list[object] = []
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)

    assert (
        roster_commands.cmd_route(
            SimpleNamespace(task="review", limit=1, json=True),
        )
        == 0
    )
    assert route_kwargs["host"] == "codex"
    assert route_kwargs["platform"] == "windows"
    assert route_kwargs["capability_receipt"] is receipt
    assert route_kwargs["allow_installation_diagnostic"] is True
    assert emitted[-1]["routing"]["selected_ids"] == ["agent"]  # type: ignore[index]

    explain_kwargs: dict[str, object] = {}

    def fake_explain(*_args: object, **kwargs: object) -> dict[str, object]:
        explain_kwargs.update(kwargs)
        return {"routing": {"selected_ids": ["agent"]}}

    monkeypatch.setattr(roster_commands, "explain_route", fake_explain)
    assert (
        roster_commands.cmd_explain(
            SimpleNamespace(session_id="cli", task="review", limit=1),
        )
        == 0
    )
    assert explain_kwargs["host"] == "codex"
    assert explain_kwargs["platform"] == "windows"
    assert explain_kwargs["capability_receipt"] is receipt
