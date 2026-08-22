"""Pure command-plan regression tests for native host registration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import agency_runtime.core.installer_registration as registration
from agency_runtime.core.installer_contracts import (
    OPENCLAW_REQUIRED_HOOKS,
    NativeCommandResult,
)
from agency_runtime.core.installer_registration import native_registration_steps


def _result(
    *,
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> dict[str, Any]:
    return {"returncode": returncode, "stdout": stdout, "stderr": stderr}


def _json_result(value: Any, *, returncode: int = 0) -> dict[str, Any]:
    return _result(stdout=json.dumps(value), returncode=returncode)


def _openclaw_runtime_payload() -> dict[str, Any]:
    return {
        "plugin": {"id": "agency-preflight", "status": "loaded"},
        "typedHooks": [
            {
                "name": name,
                **(
                    {"priority": None}
                    if name in {"message_sending", "reply_payload_sending"}
                    else {}
                ),
            }
            for name in sorted(OPENCLAW_REQUIRED_HOOKS)
        ],
    }


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
_OPENCLAW_POLICY_RESPONSES = [
    _json_result({}),
    _json_result({}),
    _result(),
    _json_result({"blockStreamingDefault": "off"}),
    _json_result({}),
]
_OPENCLAW_POLICY_COMMANDS = [
    ["openclaw", "config", "get", "agents.defaults", "--json"],
    ["openclaw", "config", "get", "channels", "--json"],
    [
        "openclaw",
        "config",
        "set",
        "agents.defaults.blockStreamingDefault",
        '"off"',
        "--strict-json",
    ],
    ["openclaw", "config", "get", "agents.defaults", "--json"],
    ["openclaw", "config", "get", "channels", "--json"],
]
_OPENCLAW_POLICY_STEPS = [
    "streaming_config_before_agents",
    "streaming_config_before_channels",
    "streaming_config_set_1",
    "streaming_config_after_agents",
    "streaming_config_after_channels",
    "final_only_delivery_policy",
]
_OPENCLAW_POLICY_RESTORE_RESPONSES = [
    _json_result([]),
    _json_result({"blockStreamingDefault": "off"}),
    _json_result({}),
    _result(),
    _json_result({}),
    _json_result({}),
]
_OPENCLAW_POLICY_RESTORE_STEPS = [
    "policy_rollback_inventory_before",
    "streaming_config_restore_before_agents",
    "streaming_config_restore_before_channels",
    "streaming_config_restore_1",
    "streaming_config_restore_after_agents",
    "streaming_config_restore_after_channels",
    "final_only_delivery_restore",
]


def test_openclaw_policy_runner_redacts_native_selector_errors(tmp_path: Path) -> None:
    secret_path = str(tmp_path / "private-profile" / "openclaw.json")
    runner = _SequenceRunner([_result(returncode=1, stderr=f"permission denied: {secret_path}")])
    session = registration._RegistrationSession(
        "openclaw",
        _TARGET,
        home_dir=tmp_path,
        command_runner=runner,
    )

    result = registration._openclaw_policy_runner(session)(
        "streaming_config_before_agents",
        ["openclaw", "config", "get", "agents.defaults", "--json"],
    )

    assert secret_path in result.stderr
    assert secret_path not in json.dumps(session.steps)
    assert session.steps[-1]["error"] == (
        "OpenClaw streaming config command failed; native detail redacted"
    )


@pytest.mark.parametrize(
    ("responses", "expected", "step_names"),
    [
        (
            [_result(returncode=1)],
            (False, None),
            ["policy_rollback_inventory_before"],
        ),
        (
            [_json_result([])],
            (True, False),
            ["policy_rollback_inventory_before"],
        ),
        (
            [_json_result({"plugins": [{"id": "agency-preflight", "enabled": False}]})],
            (True, True),
            ["policy_rollback_inventory_before"],
        ),
        (
            [
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": True}]}),
                _result(returncode=1),
            ],
            (False, True),
            ["policy_rollback_inventory_before", "policy_rollback_disable"],
        ),
        (
            [
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": True}]}),
                _result(),
                _result(returncode=1),
            ],
            (False, None),
            [
                "policy_rollback_inventory_before",
                "policy_rollback_disable",
                "policy_rollback_inventory_after",
            ],
        ),
        (
            [
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": True}]}),
                _result(),
                _json_result([]),
            ],
            (True, False),
            [
                "policy_rollback_inventory_before",
                "policy_rollback_disable",
                "policy_rollback_inventory_after",
            ],
        ),
        (
            [
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": True}]}),
                _result(),
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": False}]}),
            ],
            (True, True),
            [
                "policy_rollback_inventory_before",
                "policy_rollback_disable",
                "policy_rollback_inventory_after",
            ],
        ),
        (
            [
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": True}]}),
                _result(),
                _json_result({"plugins": [{"id": "agency-preflight", "enabled": True}]}),
            ],
            (False, True),
            [
                "policy_rollback_inventory_before",
                "policy_rollback_disable",
                "policy_rollback_inventory_after",
            ],
        ),
    ],
)
def test_openclaw_policy_rollback_requires_proven_plugin_disablement(
    responses: list[dict[str, Any]],
    expected: tuple[bool, bool | None],
    step_names: list[str],
    tmp_path: Path,
) -> None:
    runner = _SequenceRunner(responses)
    session = registration._RegistrationSession(
        "openclaw",
        _TARGET,
        home_dir=tmp_path,
        command_runner=runner,
    )

    assert registration._openclaw_plugin_disabled_state(session) == expected
    assert [step["name"] for step in session.steps] == step_names
    assert runner.exhausted


def test_openclaw_policy_rollback_retains_final_only_when_disable_is_unproven(
    tmp_path: Path,
) -> None:
    runner = _SequenceRunner([_result(returncode=1)])
    session = registration._RegistrationSession(
        "openclaw",
        _TARGET,
        home_dir=tmp_path,
        command_runner=runner,
    )

    steps, proven, failed_step = registration._rollback_openclaw_policy(session, "enable")

    assert proven is False
    assert failed_step == "enable"
    assert [step["name"] for step in steps] == [
        "policy_rollback_inventory_before",
        "final_only_delivery_restore",
    ]
    restoration = steps[-1]
    assert restoration["plugin_disabled"] is False
    assert restoration["plugin_registered"] is None
    assert restoration["restored"] is False
    assert restoration["final_only_reapplied"] is True
    assert restoration["backup_retained"] is True
    assert runner.exhausted


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
                *_OPENCLAW_POLICY_RESPONSES,
                _result(returncode=1),
                _result(),
                _result(),
                _result(),
                _result(),
                _json_result(_openclaw_runtime_payload()),
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
                *_OPENCLAW_POLICY_COMMANDS,
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
                    "config",
                    "set",
                    "plugins.entries.agency-preflight.hooks.allowPromptInjection",
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
                *_OPENCLAW_POLICY_STEPS,
                "inspect_existing",
                "install",
                "enable",
                "conversation_access",
                "prompt_injection",
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
    tmp_path: Path,
) -> None:
    runner = _SequenceRunner(case.responses)

    steps, proven, failed_step = native_registration_steps(
        case.host,
        _TARGET,
        home_dir=tmp_path,
        command_runner=runner,
    )

    assert proven is True
    assert failed_step is None
    assert runner.commands == case.commands
    assert [step["name"] for step in steps] == case.steps
    assert [step["command"] for step in steps if "command" in step] == case.commands
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
    ("responses", "expected_steps", "failed_step"),
    [
        (
            [_result(returncode=1, stderr="inventory unavailable")],
            ["inventory_before"],
            "inventory_before",
        ),
        (
            [_result(stdout="{not-json")],
            ["inventory_before"],
            "inventory_before_unproven",
        ),
        (
            [_json_result("unexpected scalar")],
            ["inventory_before"],
            "inventory_before_unproven",
        ),
        (
            [_json_result([]), _result(returncode=1, stderr="marketplace unavailable")],
            ["inventory_before", "marketplace_inventory"],
            "marketplace_inventory",
        ),
        (
            [_json_result([]), _result(stdout="{not-json")],
            ["inventory_before", "marketplace_inventory"],
            "marketplace_inventory_unproven",
        ),
        (
            [_json_result([]), _json_result(None)],
            ["inventory_before", "marketplace_inventory"],
            "marketplace_inventory_unproven",
        ),
    ],
    ids=(
        "plugin-command-failure",
        "plugin-malformed-json",
        "plugin-scalar-json",
        "marketplace-command-failure",
        "marketplace-malformed-json",
        "marketplace-null-json",
    ),
)
def test_codex_preinstall_inventory_failure_stops_before_mutation(
    responses: list[dict[str, Any]],
    expected_steps: list[str],
    failed_step: str,
) -> None:
    runner = _SequenceRunner(responses)

    steps, proven, actual_failed_step = native_registration_steps(
        "codex",
        _TARGET,
        home_dir=Path("isolated-home"),
        command_runner=runner,
        force_refresh=True,
    )

    assert proven is False
    assert actual_failed_step == failed_step
    assert [step["name"] for step in steps] == expected_steps
    assert not any(
        command[:4] == ["codex", "plugin", "marketplace", "add"]
        or command[:3] == ["codex", "plugin", "remove"]
        or command[:3] == ["codex", "plugin", "add"]
        for command in runner.commands
    )
    assert runner.exhausted


@pytest.mark.parametrize(
    ("host", "responses", "failed_step"),
    [
        (
            "hermes",
            [_result(), _result(stdout="agency-preflight\n")],
            "inventory_unproven",
        ),
        (
            "claude",
            [
                _json_result([{"name": "agency-preflight", "enabled": True}]),
                _json_result([{"name": "agency-runtime"}]),
                _result(),
                _json_result([{"name": "agency-preflight"}]),
            ],
            "inventory_after_unproven",
        ),
    ],
)
def test_registration_rejects_unknown_enablement(
    host: str,
    responses: list[dict[str, Any]],
    failed_step: str,
    tmp_path: Path,
) -> None:
    runner = _SequenceRunner(responses)

    _steps, proven, actual_failed_step = native_registration_steps(
        host,
        _TARGET,
        home_dir=tmp_path,
        command_runner=runner,
    )

    assert proven is False
    assert actual_failed_step == failed_step
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
    tmp_path: Path,
) -> None:
    responses = [
        _json_result({"running": False}),
        *_OPENCLAW_POLICY_RESPONSES,
        _json_result({"id": "agency-preflight", "enabled": True}),
    ]
    if force_refresh:
        responses.append(_result())
    responses.extend(
        [
            _result(),
            _result(),
            _result(),
            _json_result(_openclaw_runtime_payload()),
        ]
    )
    runner = _SequenceRunner(responses)

    steps, proven, failed_step = native_registration_steps(
        "openclaw",
        _TARGET,
        home_dir=tmp_path,
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


def test_openclaw_gateway_gate_accepts_explicit_nested_stopped_status() -> None:
    runner = _SequenceRunner(
        [
            _json_result(
                {
                    "service": {
                        "runtime": {
                            "status": "stopped",
                            "state": "inactive",
                            "subState": "dead",
                        }
                    },
                    "rpc": {"ok": False},
                },
                returncode=1,
            )
        ]
    )

    live, probe = registration.openclaw_gateway_live(
        home_dir=Path("isolated-home"),
        command_runner=runner,
    )

    assert live is False
    assert probe.returncode == 1
    assert runner.commands == [
        ["openclaw", "gateway", "status", "--deep", "--require-rpc", "--json"]
    ]
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
                *_OPENCLAW_POLICY_RESPONSES,
                _result(returncode=1),
                _result(returncode=1),
                *_OPENCLAW_POLICY_RESTORE_RESPONSES,
            ],
            steps=[
                "gateway_status",
                *_OPENCLAW_POLICY_STEPS,
                "inspect_existing",
                "install",
                *_OPENCLAW_POLICY_RESTORE_STEPS,
            ],
            failed_step="install",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                *_OPENCLAW_POLICY_RESPONSES,
                _json_result({"id": "agency-preflight"}),
                _result(returncode=1),
                *_OPENCLAW_POLICY_RESTORE_RESPONSES,
            ],
            steps=[
                "gateway_status",
                *_OPENCLAW_POLICY_STEPS,
                "inspect_existing",
                "enable",
                *_OPENCLAW_POLICY_RESTORE_STEPS,
            ],
            failed_step="enable",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                *_OPENCLAW_POLICY_RESPONSES,
                _json_result({"id": "agency-preflight"}),
                _result(),
                _result(returncode=1),
                *_OPENCLAW_POLICY_RESTORE_RESPONSES,
            ],
            steps=[
                "gateway_status",
                *_OPENCLAW_POLICY_STEPS,
                "inspect_existing",
                "enable",
                "conversation_access",
                *_OPENCLAW_POLICY_RESTORE_STEPS,
            ],
            failed_step="conversation_access",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                *_OPENCLAW_POLICY_RESPONSES,
                _json_result({"id": "agency-preflight"}),
                _result(),
                _result(),
                _result(returncode=1),
                *_OPENCLAW_POLICY_RESTORE_RESPONSES,
            ],
            steps=[
                "gateway_status",
                *_OPENCLAW_POLICY_STEPS,
                "inspect_existing",
                "enable",
                "conversation_access",
                "prompt_injection",
                *_OPENCLAW_POLICY_RESTORE_STEPS,
            ],
            failed_step="prompt_injection",
        ),
        _FailureCase(
            host="openclaw",
            responses=[
                _json_result({"running": False}),
                *_OPENCLAW_POLICY_RESPONSES,
                _json_result({"id": "agency-preflight"}),
                _result(),
                _result(),
                _result(),
                _json_result({"id": "agency-preflight"}),
                *_OPENCLAW_POLICY_RESTORE_RESPONSES,
            ],
            steps=[
                "gateway_status",
                *_OPENCLAW_POLICY_STEPS,
                "inspect_existing",
                "enable",
                "conversation_access",
                "prompt_injection",
                "runtime_inspect",
                *_OPENCLAW_POLICY_RESTORE_STEPS,
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
    tmp_path: Path,
) -> None:
    runner = _SequenceRunner(case.responses)

    steps, proven, failed_step = native_registration_steps(
        case.host,
        _TARGET,
        home_dir=tmp_path,
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
