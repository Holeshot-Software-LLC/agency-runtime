"""Branch-focused regressions for low-complexity runtime orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.base import _tool_failure_reason
from agency_runtime.core.canary import (
    _backend,
    _claude_canary_record,
    _codex_canary_record,
    _codex_output,
    _process_succeeded,
)
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    ObservabilityConfig,
    _apply_env_overrides,
)
from agency_runtime.core.delegation.backend_command import _raise_or_result
from agency_runtime.core.delegation.backend_contracts import BackendExecutionError
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.roster.ingress import (
    RosterSyncError,
    _validate_source_spec,
)
from agency_runtime.core.selector.policy import (
    _policy_routes,
    detect_actions,
    detect_fallback_companions,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        (True, ""),
        (False, "tool call returned false"),
        (42, ""),
        ([], ""),
        ([{"error": "first failure"}], "first failure"),
        (
            ({"ok": True}, {"status": "failed", "reason": "second failure"}),
            "second failure",
        ),
        ("  ", ""),
        ("ordinary output", ""),
        (" error: explicit failure ", "error: explicit failure"),
        ('{"ok":false,"message":"JSON failure"}', "JSON failure"),
        ('{"broken"', "tool call returned invalid structured output"),
        ({"error": {"message": "nested error"}}, "nested error"),
        (
            {"result": {"status": "timeout", "detail": "nested timeout"}},
            "nested timeout",
        ),
        ({"content": [{"text": "ordinary content"}]}, ""),
    ],
)
def test_tool_failure_reason_branch_table(value: Any, expected: str) -> None:
    assert _tool_failure_reason(value) == expected


@pytest.mark.parametrize("key", ["success", "ok", "delegated", "loaded"])
def test_tool_failure_reason_false_flags(key: str) -> None:
    assert _tool_failure_reason({key: False, "message": key}) == key


@pytest.mark.parametrize("key", ["isError", "is_error", "cancelled", "canceled", "timed_out"])
def test_tool_failure_reason_true_flags(key: str) -> None:
    assert _tool_failure_reason({key: True, "message": key}) == key


@pytest.mark.parametrize("key", ["returncode", "return_code", "exit_code", "exitCode"])
def test_tool_failure_reason_exit_codes(key: str) -> None:
    assert _tool_failure_reason({key: 7}) == "tool call exited with 7"


def test_tool_failure_reason_depth_guard() -> None:
    nested: dict[str, Any] = {"error": "too deep"}
    for _ in range(7):
        nested = {"result": nested}
    assert _tool_failure_reason(nested) == ""


def _read_attribute(value: Any, dotted_path: str) -> Any:
    for segment in dotted_path.split("."):
        value = getattr(value, segment)
    return value


@pytest.mark.parametrize(
    ("environment", "path", "expected"),
    [
        ({"AGENCY_JUDGE_MODEL": "env-model"}, "judge.model", "env-model"),
        (
            {"AGENCY_JUDGE_BASE_URL": "https://judge.invalid/v1"},
            "judge.ollama_mode",
            False,
        ),
        ({"AGENCY_JUDGE_API_KEY": "direct"}, "judge.api_key", "direct"),
        ({"LITELLM_API_KEY": "fallback"}, "judge.api_key", "fallback"),
        ({"AGENCY_JUDGE_TIMEOUT": "30.5"}, "judge.timeout", 30.5),
        ({"AGENCY_MAX_SELECTED": "7"}, "judge.max_selected", 7),
        ({"AGENCY_BYPASS_THRESHOLD": "9.5"}, "judge.confidence_bypass_threshold", 9.5),
        (
            {"OLLAMA_BASE_URL": "http://127.0.0.1:11500"},
            "ollama.base_url",
            "http://127.0.0.1:11500",
        ),
        (
            {"AGENCY_OLLAMA_FALLBACK_MODEL": "local-model"},
            "ollama.model",
            "local-model",
        ),
        (
            {"AGENCY_DB_PATH": "/runtime/agency.db"},
            "store.db_path",
            "/runtime/agency.db",
        ),
        ({"AGENCY_CAPTURE_CONTENT": "yes"}, "observability.capture_content", True),
        ({"AGENCY_CAPTURE_CONTENT": "off"}, "observability.capture_content", False),
        ({"AGENCY_RETENTION_DAYS": "5"}, "observability.retention_days", 5),
        ({"AGENCY_DASHBOARD_PORT": "7900"}, "dashboard.port", 7900),
        ({"AGENCY_PROFILE": "  power  "}, "profile", "power"),
    ],
)
def test_environment_override_branch_table(
    environment: dict[str, str],
    path: str,
    expected: Any,
) -> None:
    config = AgencyConfig(
        judge=JudgeConfig(
            base_url="http://127.0.0.1:11434",
            ollama_mode=True,
        ),
        observability=ObservabilityConfig(capture_content=True),
    )

    updated = _apply_env_overrides(config, environ=environment)

    assert _read_attribute(updated, path) == expected


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AGENCY_JUDGE_TIMEOUT", "invalid"),
        ("AGENCY_MAX_SELECTED", "0"),
        ("AGENCY_BYPASS_THRESHOLD", "nan"),
        ("AGENCY_RETENTION_DAYS", "-1"),
        ("AGENCY_DASHBOARD_PORT", "70000"),
    ],
)
def test_invalid_numeric_environment_values_fail_closed(name: str, value: str) -> None:
    config = AgencyConfig()

    with pytest.raises(ValueError, match=rf"{name}: environment override is invalid"):
        _apply_env_overrides(config, environ={name: value})


@pytest.mark.parametrize(
    ("judge", "environment", "expected"),
    [
        (
            JudgeConfig(api_key="configured"),
            {"LITELLM_API_KEY": "fallback"},
            "configured",
        ),
        (
            JudgeConfig(api_key_env="EXISTING_KEY"),
            {"EXISTING_KEY": "configured", "LITELLM_API_KEY": "fallback"},
            "",
        ),
        (
            JudgeConfig(api_key="configured"),
            {"AGENCY_JUDGE_API_KEY": "direct", "LITELLM_API_KEY": "fallback"},
            "direct",
        ),
    ],
)
def test_judge_key_override_precedence(
    judge: JudgeConfig,
    environment: dict[str, str],
    expected: str,
) -> None:
    assert (
        _apply_env_overrides(AgencyConfig(judge=judge), environ=environment).judge.api_key
        == expected
    )


@pytest.mark.parametrize(
    "result",
    [
        BoundedProcessResult(1, "", ""),
        BoundedProcessResult(0, "", "", timed_out=True),
        BoundedProcessResult(0, "", "", stdout_truncated=True),
        BoundedProcessResult(0, "", "", stderr_truncated=True),
    ],
)
def test_process_success_rejects_every_failure_signal(
    result: BoundedProcessResult,
) -> None:
    assert _process_succeeded(result) is False


def test_process_success_accepts_clean_zero_exit() -> None:
    assert _process_succeeded(BoundedProcessResult(0, "", "")) is True


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("", None),
        ("not-json", None),
        (json.dumps({"type": "turn.completed"}), None),
        (
            "\n".join(
                (
                    "null",
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": "done"},
                        }
                    ),
                    json.dumps({"type": "turn.completed"}),
                )
            ),
            "done",
        ),
    ],
)
def test_codex_output_branch_table(stdout: str, expected: str | None) -> None:
    assert _codex_output(stdout) == expected


@pytest.mark.parametrize(
    ("factory", "stdout"),
    [
        (_codex_canary_record, "not-json"),
        (_claude_canary_record, "not-json"),
        (_claude_canary_record, "{}"),
    ],
)
def test_canary_records_fail_closed_on_protocol_errors(
    factory: Any,
    stdout: str,
) -> None:
    record = factory(BoundedProcessResult(0, stdout, ""))
    assert record["status"] == "failed"
    assert record["exit_code"] == 1


def test_canary_records_preserve_success_output() -> None:
    codex_stdout = "\n".join(
        (
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "codex-result"},
                }
            ),
            json.dumps({"type": "turn.completed"}),
        )
    )
    assert (
        _codex_canary_record(BoundedProcessResult(0, codex_stdout, ""))["output"] == "codex-result"
    )
    assert (
        _claude_canary_record(BoundedProcessResult(0, json.dumps({"result": "claude-result"}), ""))[
            "output"
        ]
        == "claude-result"
    )


@pytest.mark.parametrize(
    ("host", "timeout", "resolver", "message"),
    [
        ("hermes", 10, lambda _host: "hermes", "no proven safe"),
        ("codex", 0, lambda _host: "codex", "timeout must"),
        ("codex", 10, lambda _host: None, "executable is unavailable"),
    ],
)
def test_canary_backend_validation_table(
    host: str,
    timeout: float,
    resolver: Any,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _backend(
            host,
            db_path=Path("agency.db"),
            timeout=timeout,
            resolver=resolver,
        )


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_canary_backend_never_uses_cwd_as_an_implicit_managed_target(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".agents" / "plugins").mkdir(parents=True)
    (tmp_path / ".agents" / "plugins" / "marketplace.json").write_text("{}")
    claude_manifest = tmp_path / "plugins" / "agency-preflight" / ".claude-plugin" / "plugin.json"
    claude_manifest.parent.mkdir(parents=True)
    claude_manifest.write_text("{}")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match=f"managed {host.title()}"):
        _backend(
            host,
            db_path=tmp_path / "agency.db",
            timeout=10,
            native=None,
            resolver=lambda _host: host,
        )


def test_backend_error_check_seam_returns_or_raises_exact_result() -> None:
    result = {"status": "failed", "exit_code": 7}
    error = BackendExecutionError("failed", result=result)

    assert _raise_or_result(error, check=False) is error.result
    with pytest.raises(BackendExecutionError) as raised:
        _raise_or_result(error, check=True)
    assert raised.value is error


@pytest.mark.parametrize(
    ("source", "kind", "rendered"),
    [
        ("https://example.invalid/agents.json?version=1", "http", None),
        ("C:\\agents\\roster.json", "path", "C:\\agents\\roster.json"),
        ("relative/agents.json", "path", str(Path("relative/agents.json"))),
        ("file:///tmp/agents.json", "path", None),
    ],
)
def test_roster_source_valid_branch_table(
    source: str,
    kind: str,
    rendered: str | None,
) -> None:
    actual_kind, target = _validate_source_spec(source)

    assert actual_kind == kind
    if rendered is not None:
        assert str(target) == rendered


@pytest.mark.parametrize("source", ["file:", "file://localhost"])
def test_empty_file_url_never_resolves_to_cwd(source: str) -> None:
    with pytest.raises(RosterSyncError, match="must include a path"):
        _validate_source_spec(source)


@pytest.mark.parametrize(
    ("policy", "expected_errors"),
    [
        (
            {"actions": [], "division_anchors": []},
            {"actions must be a mapping", "division_anchors must be a mapping"},
        ),
        (
            {"actions": {"BUILD": "invalid"}},
            {"actions.BUILD must be a mapping"},
        ),
        (
            {"actions": {"BUILD": {"always_include": "invalid"}}},
            {"actions.BUILD.always_include must be a list"},
        ),
        (
            {
                "actions": {
                    "BUILD": {
                        "always_include": [None, {"slug": ""}, {"slug": "builder"}],
                        "conditional": [{"slug": "reviewer", "when": ""}],
                    }
                },
                "division_anchors": {
                    "engineering": {
                        "anchor": "architect",
                        "conditional": [
                            {"slug": "security", "when": "auth"},
                            ["release", "deploy"],
                            ["missing-condition"],
                        ],
                    }
                },
            },
            {
                "actions.BUILD.always_include[0] must be a mapping",
                "actions.BUILD.always_include[1].slug must be a non-empty string",
                "actions.BUILD.conditional[0].when must be a non-empty string",
                "division_anchors.engineering.conditional[2] must contain a slug and condition",
            },
        ),
    ],
)
def test_policy_route_validation_branch_table(
    policy: dict[str, Any],
    expected_errors: set[str],
) -> None:
    routes, errors = _policy_routes(policy)

    assert expected_errors <= set(errors)
    if "BUILD" in policy.get("actions", {}):
        assert all(route["slug"] for route in routes)


def _detection_policy() -> dict[str, Any]:
    return {
        "actions": {
            "DEFAULT": {
                "triggers": ["_fallback_"],
                "always_include": [{"slug": "base"}],
            },
            "BUILD": {
                "triggers": ["build"],
                "always_include": [{"slug": "builder"}, {"slug": "base"}],
                "conditional": [{"slug": "security", "when": "authentication"}],
            },
            "NO_TRIGGERS": {
                "triggers": [],
                "always_include": [{"slug": "never"}],
            },
        },
        "division_anchors": {
            "engineering": {
                "keywords": ["api"],
                "anchor": "architect",
                "conditional": [
                    {"slug": "security", "when": "authentication"},
                    ["release", "deploy"],
                    ["invalid"],
                ],
            }
        },
    }


@pytest.mark.parametrize(
    ("message", "availability", "expected_actions", "expected_companions"),
    [
        (
            "build authentication api deploy",
            None,
            ["BUILD"],
            ["builder", "security", "architect", "release"],
        ),
        ("unrelated", None, [], []),
        (
            "build authentication api deploy",
            {"enabled": ["base", "builder", "architect"]},
            ["BUILD"],
            ["builder", "architect"],
        ),
    ],
)
def test_action_detection_branch_table(
    message: str,
    availability: dict[str, Any] | None,
    expected_actions: list[str],
    expected_companions: list[str],
) -> None:
    policy = _detection_policy()
    if availability is not None:
        policy["specialist_availability"] = availability

    assert detect_actions(message, policy) == (
        expected_actions,
        expected_companions,
    )


def test_default_companion_detection_is_separate_and_bounded() -> None:
    policy = _detection_policy()
    policy["actions"]["DEFAULT"]["always_include"].extend([{"slug": "second"}, {"slug": "ignored"}])

    assert detect_fallback_companions(policy) == ["base", "second"]


@pytest.mark.parametrize("policy", [{}, {"actions": {}}])
def test_action_detection_empty_policy_is_empty(policy: dict[str, Any]) -> None:
    assert detect_actions("build", policy) == ([], [])
