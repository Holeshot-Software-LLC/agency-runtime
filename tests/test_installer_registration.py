"""Pure command-plan regression tests for native host registration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.installer_contracts import NativeCommandResult
from agency_runtime.core.installer_registration import native_registration_steps


def _result(*, stdout: str = "", returncode: int = 0) -> dict[str, Any]:
    return {"returncode": returncode, "stdout": stdout}


def _json_result(value: Any, *, returncode: int = 0) -> dict[str, Any]:
    return _result(stdout=json.dumps(value), returncode=returncode)


class _SequenceRunner:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.commands: list[list[str]] = []

    @property
    def exhausted(self) -> bool:
        return not self._responses

    def __call__(self, command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if not self._responses:
            raise AssertionError(f"unexpected native command: {command!r}")
        self.commands.append(command)
        return self._responses.pop(0)


@dataclass(frozen=True)
class _SuccessCase:
    host: str
    responses: list[dict[str, Any]]
    commands: list[list[str]]
    steps: list[str]


@dataclass(frozen=True)
class _FailureCase:
    host: str
    responses: list[dict[str, Any]]
    steps: list[str]
    failed_step: str
    force_refresh: bool = False


_TARGET = Path("managed-marketplace")
_SELECTOR = "agency-preflight@agency-runtime"


@pytest.mark.parametrize(
    "case",
    [
        _SuccessCase(
            host="hermes",
            responses=[
                _result(),
                _result(stdout="agency-preflight enabled"),
            ],
            commands=[
                ["hermes", "plugins", "enable", "agency-preflight"],
                ["hermes", "plugins", "list"],
            ],
            steps=["enable", "inventory"],
        ),
        _SuccessCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                _result(returncode=1),
                _result(),
                _result(),
                _result(),
                _json_result({"id": "agency-preflight", "loaded": True}),
            ],
            commands=[
                [
                    "openclaw",
                    "gateway",
                    "status",
                    "--deep",
                    "--require-rpc",
                    "--json",
                ],
                [
                    "openclaw",
                    "plugins",
                    "inspect",
                    "agency-preflight",
                    "--json",
                ],
                [
                    "openclaw",
                    "plugins",
                    "install",
                    str(_TARGET),
                ],
                ["openclaw", "plugins", "enable", "agency-preflight"],
                [
                    "openclaw",
                    "config",
                    "set",
                    "plugins.entries.agency-preflight.hooks.allowConversationAccess",
                    "true",
                ],
                [
                    "openclaw",
                    "plugins",
                    "inspect",
                    "agency-preflight",
                    "--runtime",
                    "--json",
                ],
            ],
            steps=[
                "gateway_status",
                "inspect_existing",
                "install",
                "enable",
                "conversation_access",
                "runtime_inspect",
            ],
        ),
        _SuccessCase(
            host="codex",
            responses=[
                _json_result([]),
                _json_result([]),
                _result(),
                _result(),
                _json_result([{"pluginId": "agency-preflight", "enabled": True}]),
            ],
            commands=[
                ["codex", "plugin", "list", "--json"],
                ["codex", "plugin", "marketplace", "list", "--json"],
                [
                    "codex",
                    "plugin",
                    "marketplace",
                    "add",
                    str(_TARGET),
                    "--json",
                ],
                ["codex", "plugin", "add", _SELECTOR, "--json"],
                ["codex", "plugin", "list", "--json"],
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "marketplace_add",
                "plugin_add",
                "inventory_after",
            ],
        ),
        _SuccessCase(
            host="claude",
            responses=[
                _json_result([]),
                _json_result([]),
                _result(),
                _result(),
                _result(),
                _json_result([{"name": "agency-preflight", "enabled": True}]),
            ],
            commands=[
                ["claude", "plugin", "list", "--json"],
                ["claude", "plugin", "marketplace", "list", "--json"],
                [
                    "claude",
                    "plugin",
                    "marketplace",
                    "add",
                    str(_TARGET),
                    "--scope",
                    "user",
                ],
                [
                    "claude",
                    "plugin",
                    "install",
                    _SELECTOR,
                    "--scope",
                    "user",
                ],
                [
                    "claude",
                    "plugin",
                    "enable",
                    _SELECTOR,
                    "--scope",
                    "user",
                ],
                ["claude", "plugin", "list", "--json"],
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "marketplace_add",
                "plugin_install",
                "enable",
                "inventory_after",
            ],
        ),
    ],
    ids=lambda case: case.host,
)
def test_registration_success_preserves_exact_commands_and_step_order(
    case: _SuccessCase,
) -> None:
    runner = _SequenceRunner(case.responses)

    steps, proven, failed_step = native_registration_steps(
        case.host,
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
    )

    assert proven is True
    assert failed_step is None
    assert runner.commands == case.commands
    assert [step["name"] for step in steps] == case.steps
    assert [step["command"] for step in steps] == case.commands
    assert runner.exhausted


@pytest.mark.parametrize(
    "inventory_record",
    [
        {"pluginId": "agency-preflight"},
        {"pluginId": "agency-preflight", "enabled": False},
    ],
    ids=("missing-enabled", "explicitly-disabled"),
)
def test_codex_registration_requires_explicit_enabled_inventory_proof(
    inventory_record: dict[str, Any],
) -> None:
    runner = _SequenceRunner(
        [
            _json_result([]),
            _json_result([{"name": "agency-runtime"}]),
            _result(),
            _json_result([inventory_record]),
        ]
    )

    steps, proven, failed_step = native_registration_steps(
        "codex",
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
    )

    assert proven is False
    assert failed_step == "inventory_after_unproven"
    assert [step["name"] for step in steps] == [
        "inventory_before",
        "marketplace_inventory",
        "plugin_add",
        "inventory_after",
    ]
    assert runner.exhausted


@pytest.mark.parametrize(
    ("host", "remove_command", "install_name", "install_command"),
    [
        (
            "codex",
            ["codex", "plugin", "remove", _SELECTOR, "--json"],
            "plugin_add",
            ["codex", "plugin", "add", _SELECTOR, "--json"],
        ),
        (
            "claude",
            [
                "claude",
                "plugin",
                "uninstall",
                _SELECTOR,
                "--scope",
                "user",
            ],
            "plugin_install",
            [
                "claude",
                "plugin",
                "install",
                _SELECTOR,
                "--scope",
                "user",
            ],
        ),
    ],
)
def test_marketplace_force_refresh_preserves_remove_then_install_order(
    host: str,
    remove_command: list[str],
    install_name: str,
    install_command: list[str],
) -> None:
    identity = "pluginId" if host == "codex" else "name"
    responses = [
        _json_result([{identity: "agency-preflight", "enabled": True}]),
        _json_result([{"name": "agency-runtime"}]),
        _result(),
        _result(),
    ]
    if host == "claude":
        responses.append(_result())
    responses.append(_json_result([{identity: "agency-preflight", "enabled": True}]))
    runner = _SequenceRunner(responses)

    steps, proven, failed_step = native_registration_steps(
        host,
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
        force_refresh=True,
    )

    assert proven is True
    assert failed_step is None
    names = [step["name"] for step in steps]
    assert names[:2] == ["inventory_before", "marketplace_inventory"]
    assert names[2:4] == ["plugin_remove_for_refresh", install_name]
    assert runner.commands[2:4] == [remove_command, install_command]
    assert "marketplace_add" not in names
    assert runner.exhausted


@pytest.mark.parametrize(
    ("force_refresh", "expected_install"),
    [
        (False, None),
        (
            True,
            [
                "openclaw",
                "plugins",
                "install",
                str(_TARGET),
                "--force",
            ],
        ),
    ],
)
def test_openclaw_existing_plugin_install_condition_is_exact(
    force_refresh: bool,
    expected_install: list[str] | None,
) -> None:
    responses = [
        _json_result({"running": False}),
        _json_result({"id": "agency-preflight", "enabled": True}),
    ]
    if force_refresh:
        responses.append(_result())
    responses.extend(
        [
            _result(),
            _result(),
            _json_result({"id": "agency-preflight", "loaded": True}),
        ]
    )
    runner = _SequenceRunner(responses)

    steps, proven, failed_step = native_registration_steps(
        "openclaw",
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
        force_refresh=force_refresh,
    )

    assert proven is True
    assert failed_step is None
    install_steps = [step for step in steps if step["name"] == "install"]
    assert [step["command"] for step in install_steps] == (
        [] if expected_install is None else [expected_install]
    )
    assert runner.exhausted


@pytest.mark.parametrize(
    ("gateway_response", "state", "failed_step"),
    [
        (_result(returncode=7), "unknown", "gateway_status_unproven"),
        (
            _json_result({"running": True}),
            "live",
            "host_restart_consent_required",
        ),
    ],
)
def test_openclaw_gateway_gate_stops_before_any_mutating_command(
    gateway_response: dict[str, Any],
    state: str,
    failed_step: str,
) -> None:
    runner = _SequenceRunner([gateway_response])

    steps, proven, actual_failed_step = native_registration_steps(
        "openclaw",
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
    )

    assert proven is False
    assert actual_failed_step == failed_step
    assert [step["name"] for step in steps] == ["gateway_status"]
    assert steps[0]["gateway_state"] == state
    assert len(runner.commands) == 1
    assert runner.exhausted


@pytest.mark.parametrize(
    "case",
    [
        _FailureCase(
            host="hermes",
            responses=[
                _result(returncode=1),
                _result(stdout="agency-preflight enabled"),
            ],
            steps=["enable", "inventory"],
            failed_step="enable",
        ),
        _FailureCase(
            host="hermes",
            responses=[_result(), _result(returncode=1)],
            steps=["enable", "inventory"],
            failed_step="inventory_unproven",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                _result(returncode=1),
                _result(returncode=1),
            ],
            steps=["gateway_status", "inspect_existing", "install"],
            failed_step="install",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                _json_result({"id": "agency-preflight"}),
                _result(returncode=1),
            ],
            steps=["gateway_status", "inspect_existing", "enable"],
            failed_step="enable",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                _json_result({"id": "agency-preflight"}),
                _result(),
                _result(returncode=1),
            ],
            steps=[
                "gateway_status",
                "inspect_existing",
                "enable",
                "conversation_access",
            ],
            failed_step="conversation_access",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                _json_result({"id": "agency-preflight"}),
                _result(),
                _result(),
                _json_result({"id": "agency-preflight"}),
            ],
            steps=[
                "gateway_status",
                "inspect_existing",
                "enable",
                "conversation_access",
                "runtime_inspect",
            ],
            failed_step="runtime_inspect_unproven",
        ),
        _FailureCase(
            host="codex",
            responses=[
                _json_result([]),
                _json_result([]),
                _result(returncode=1),
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "marketplace_add",
            ],
            failed_step="marketplace_add",
        ),
        _FailureCase(
            host="codex",
            responses=[
                _json_result([{"pluginId": "agency-preflight"}]),
                _json_result([{"name": "agency-runtime"}]),
                _result(returncode=1),
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "plugin_remove_for_refresh",
            ],
            failed_step="plugin_remove_for_refresh",
            force_refresh=True,
        ),
        _FailureCase(
            host="codex",
            responses=[
                _json_result([]),
                _json_result([{"name": "agency-runtime"}]),
                _result(returncode=1),
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "plugin_add",
            ],
            failed_step="plugin_add",
        ),
        _FailureCase(
            host="codex",
            responses=[
                _json_result([{"pluginId": "agency-preflight"}]),
                _json_result([{"name": "agency-runtime"}]),
                _json_result([]),
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "inventory_after",
            ],
            failed_step="inventory_after_unproven",
        ),
        _FailureCase(
            host="claude",
            responses=[
                _json_result([]),
                _json_result([{"name": "agency-runtime"}]),
                _result(returncode=1),
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "plugin_install",
            ],
            failed_step="plugin_install",
        ),
        _FailureCase(
            host="claude",
            responses=[
                _json_result([{"name": "agency-preflight", "enabled": True}]),
                _json_result([{"name": "agency-runtime"}]),
                _result(returncode=1),
            ],
            steps=["inventory_before", "marketplace_inventory", "enable"],
            failed_step="enable",
        ),
        _FailureCase(
            host="claude",
            responses=[
                _json_result([{"name": "agency-preflight", "enabled": True}]),
                _json_result([{"name": "agency-runtime"}]),
                _result(),
                _json_result([{"name": "agency-preflight", "enabled": False}]),
            ],
            steps=[
                "inventory_before",
                "marketplace_inventory",
                "enable",
                "inventory_after",
            ],
            failed_step="inventory_after_unproven",
        ),
    ],
    ids=lambda case: f"{case.host}-{case.failed_step}",
)
def test_registration_failure_matrix_preserves_stop_point(
    case: _FailureCase,
) -> None:
    runner = _SequenceRunner(case.responses)

    steps, proven, failed_step = native_registration_steps(
        case.host,
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
        force_refresh=case.force_refresh,
    )

    assert proven is False
    assert failed_step == case.failed_step
    assert [step["name"] for step in steps] == case.steps
    assert runner.exhausted


def test_registration_resolves_native_runner_through_facade_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import installer

    calls: list[tuple[list[str], dict[str, Any]]] = []

    def fake_run(
        command: list[str],
        **kwargs: Any,
    ) -> NativeCommandResult:
        calls.append((list(command), kwargs))
        stdout = "agency-preflight enabled" if command[-2:] == ["plugins", "list"] else ""
        return NativeCommandResult(tuple(command), 0, stdout=stdout)

    monkeypatch.setattr(installer, "_run_native", fake_run)

    steps, proven, failed_step = native_registration_steps(
        "hermes",
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=None,
    )

    assert proven is True
    assert failed_step is None
    assert [step["name"] for step in steps] == ["enable", "inventory"]
    assert [command for command, _kwargs in calls] == [
        ["hermes", "plugins", "enable", "agency-preflight"],
        ["hermes", "plugins", "list"],
    ]
    assert all(kwargs["host"] == "hermes" for _command, kwargs in calls)
    assert all(kwargs["timeout"] == 30 for _command, kwargs in calls)
