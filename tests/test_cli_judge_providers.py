"""CLI-authenticated provider contracts and ordered judge fallback."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.cli_transport import (
    CLIProviderStatus,
    inspect_cli_transport,
    invoke_cli_judge,
    safe_cli_environment,
)
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
)
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.selector import judge

CATALOG = [
    {
        "slug": "security-reviewer",
        "description": "Reviews authentication and application security.",
    }
]


def _result(
    stdout: str = "",
    *,
    returncode: int = 0,
    timed_out: bool = False,
    stdout_truncated: bool = False,
) -> BoundedProcessResult:
    return BoundedProcessResult(
        returncode=returncode,
        stdout=stdout,
        stderr="",
        timed_out=timed_out,
        stdout_truncated=stdout_truncated,
    )


def test_codex_status_distinguishes_installed_authenticated_and_usable() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], **_kwargs: Any) -> BoundedProcessResult:
        calls.append(argv)
        if argv[1:3] == ["login", "status"]:
            return _result("Logged in")
        return _result(
            "--json --output-schema --ephemeral --ignore-user-config "
            "--ignore-rules --sandbox --strict-config"
        )

    status = inspect_cli_transport(
        "codex",
        resolver=lambda _name: "/tools/codex",
        runner=runner,
        environ={"PATH": "/tools", "SECRET_TOKEN": "do-not-forward"},
    )

    assert status == CLIProviderStatus(
        transport="codex",
        installed=True,
        authenticated=True,
        usable=True,
        executable="/tools/codex",
    )
    assert calls == [
        ["/tools/codex", "login", "status"],
        ["/tools/codex", "exec", "--help"],
    ]


def test_cli_status_reports_missing_auth_without_exposing_output() -> None:
    def runner(_argv: list[str], **_kwargs: Any) -> BoundedProcessResult:
        return _result("account@example.test token=secret", returncode=1)

    status = inspect_cli_transport(
        "codex",
        resolver=lambda _name: "codex.cmd",
        runner=runner,
    )

    assert status.installed is True
    assert status.authenticated is False
    assert status.usable is False
    assert "account@example.test" not in status.reason
    assert "secret" not in status.reason


def test_cli_status_launch_failure_is_safe_and_unusable() -> None:
    status = inspect_cli_transport(
        "codex",
        resolver=lambda _name: "codex",
        runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("secret")),
    )

    assert status.installed is True
    assert status.authenticated is False
    assert status.usable is False
    assert "secret" not in status.reason


@pytest.mark.parametrize(
    ("version", "usable"),
    [("2.1.204", False), ("claude 2.1.205", True), ("3.0.0", True)],
)
def test_claude_status_version_gates_fail_closed_schema_support(
    version: str,
    usable: bool,
) -> None:
    def runner(argv: list[str], **_kwargs: Any) -> BoundedProcessResult:
        return _result("{}" if argv[1:3] == ["auth", "status"] else version)

    status = inspect_cli_transport(
        "claude",
        resolver=lambda _name: "/tools/claude",
        runner=runner,
    )

    assert status.authenticated is True
    assert status.usable is usable


def test_safe_cli_environment_drops_unrelated_credentials() -> None:
    safe = safe_cli_environment(
        {
            "PATH": "/tools",
            "HOME": "/home/user",
            "CODEX_HOME": "/home/user/.codex",
            "NODE_EXTRA_CA_CERTS": "/trust/corporate-ca.pem",
            "REQUESTS_CA_BUNDLE": "/trust/python-ca.pem",
            "SSL_CERT_FILE": "/trust/openssl-ca.pem",
            "OPENAI_API_KEY": "secret",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "UNRELATED_TOKEN": "secret",
        }
    )

    assert safe["PATH"] == "/tools"
    assert safe["CODEX_HOME"] == "/home/user/.codex"
    assert safe["NODE_EXTRA_CA_CERTS"] == "/trust/corporate-ca.pem"
    assert safe["REQUESTS_CA_BUNDLE"] == "/trust/python-ca.pem"
    assert safe["SSL_CERT_FILE"] == "/trust/openssl-ca.pem"
    assert "OPENAI_API_KEY" not in safe
    assert "AWS_SECRET_ACCESS_KEY" not in safe
    assert "UNRELATED_TOKEN" not in safe


def test_codex_judge_uses_stdin_strict_tool_gates_and_isolated_home() -> None:
    prompt = "route this private task"
    observed: dict[str, Any] = {}
    selection = json.dumps(
        {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.92,
        }
    )
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": selection},
                }
            ),
            json.dumps({"type": "turn.completed"}),
        ]
    )

    def runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        observed.update({"argv": argv, **kwargs})
        assert Path(kwargs["cwd"]).exists()
        return _result(stdout)

    parsed = invoke_cli_judge(
        ProviderEntry(
            name="codex",
            type="cli",
            transport="codex",
            model="openai/gpt-5-mini",
        ),
        prompt,
        timeout=4,
        resolver=lambda _name: "C:\\tools\\codex.CMD",
        runner=runner,
        environ={
            "PATH": "C:\\tools",
            "USERPROFILE": "C:\\Users\\person",
            "CODEX_HOME": "C:\\Users\\person\\.codex",
            "OPENAI_API_KEY": "must-not-leak",
        },
    )

    assert parsed == {
        "selected_ids": ["security-reviewer"],
        "confidence": 0.92,
    }
    assert prompt not in observed["argv"]
    assert observed["input_text"] == prompt
    assert observed["argv"][observed["argv"].index("--model") + 1] == ("openai/gpt-5-mini")
    assert "--strict-config" in observed["argv"]
    assert "features.shell_tool=false" in observed["argv"]
    assert "features.unified_exec=false" in observed["argv"]
    assert 'web_search="disabled"' in observed["argv"]
    assert observed["env"]["CODEX_HOME"] == "C:\\Users\\person\\.codex"
    assert observed["env"]["USERPROFILE"].startswith(observed["cwd"])
    for name in ("TEMP", "TMP", "TMPDIR"):
        assert Path(observed["env"][name]).is_relative_to(Path(observed["cwd"]))
    assert "OPENAI_API_KEY" not in observed["env"]


def test_claude_judge_disables_tools_customizations_and_persistence() -> None:
    observed: dict[str, Any] = {}
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "structured_output": {
                "selected_ids": ["security-reviewer"],
                "confidence": 0.81,
            },
        }
    )

    def runner(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        observed.update({"argv": argv, **kwargs})
        return _result(stdout)

    parsed = invoke_cli_judge(
        ProviderEntry(name="claude", type="cli", transport="claude"),
        "select safely",
        timeout=3,
        resolver=lambda _name: "/tools/claude",
        runner=runner,
    )

    assert parsed and parsed["selected_ids"] == ["security-reviewer"]
    assert "--safe-mode" in observed["argv"]
    assert "--no-session-persistence" in observed["argv"]
    assert observed["argv"][observed["argv"].index("--tools") + 1] == ""
    assert "--strict-mcp-config" in observed["argv"]


@pytest.mark.parametrize(
    "process_result",
    [
        _result(timed_out=True, returncode=124),
        _result("not json"),
        _result("{}", stdout_truncated=True),
    ],
)
def test_cli_judge_failures_are_not_promoted(
    process_result: BoundedProcessResult,
) -> None:
    assert (
        invoke_cli_judge(
            ProviderEntry(name="codex", type="cli", transport="codex"),
            "select",
            timeout=1,
            resolver=lambda _name: "/tools/codex",
            runner=lambda *_args, **_kwargs: process_result,
        )
        is None
    )


def test_cli_judge_launch_exception_is_not_promoted() -> None:
    assert (
        invoke_cli_judge(
            ProviderEntry(name="claude", type="cli", transport="claude"),
            "select",
            timeout=1,
            resolver=lambda _name: "/tools/claude",
            runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("private")),
        )
        is None
    )


def test_windows_cmd_shim_rejects_model_metacharacters_before_launch() -> None:
    called = False

    def runner(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        nonlocal called
        called = True
        return _result()

    assert (
        invoke_cli_judge(
            ProviderEntry(
                name="codex",
                type="cli",
                transport="codex",
                model="gpt-5&whoami",
            ),
            "private prompt remains on stdin",
            timeout=1,
            resolver=lambda _name: "C:\\tools\\codex.CMD",
            runner=runner,
        )
        is None
    )
    assert called is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows batch semantics")
@pytest.mark.parametrize("transport", ["codex", "claude"])
def test_cli_judge_rejects_batch_shim_without_safe_companion(
    transport: str,
    tmp_path: Path,
) -> None:
    marker = tmp_path / "invoked.txt"
    shim = tmp_path / f"{transport}.cmd"
    shim.write_text(f"@echo invoked>{marker}\r\n", encoding="utf-8")

    assert (
        invoke_cli_judge(
            ProviderEntry(name=transport, type="cli", transport=transport),
            "private prompt",
            timeout=2,
            resolver=lambda _name: str(shim),
        )
        is None
    )
    assert not marker.exists()


def test_cli_judge_success_requires_no_agency_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        judge,
        "invoke_cli_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.9,
        },
    )
    cfg = AgencyConfig(
        providers=(
            ProviderEntry(
                name="codex",
                type="cli",
                transport="codex",
                timeout=2,
            ),
        ),
        judge=JudgeConfig(model="", timeout=3, confidence_bypass_threshold=999),
        ollama=OllamaConfig(enabled=False, model=""),
    )

    result = judge.query_judge("review authentication", CATALOG, config=cfg)

    assert result["status"] == "applied"
    assert result["selected_ids"] == ["security-reviewer"]
    assert result["provider"] == "codex (cli:codex)"


def test_failed_cli_falls_through_to_http_then_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    monkeypatch.setattr(
        judge,
        "invoke_cli_judge",
        lambda *_args, **_kwargs: order.append("cli") or None,
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int = -1) -> bytes:
            order.append("http")
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "selected_ids": ["security-reviewer"],
                                        "confidence": 0.8,
                                    }
                                )
                            }
                        }
                    ],
                }
            ).encode()

    monkeypatch.setattr(judge, "open_no_redirect", lambda *_a, **_kw: Response())
    cfg = AgencyConfig(
        providers=(
            ProviderEntry(name="codex", type="cli", transport="codex"),
            ProviderEntry(
                name="http",
                type="openai-compatible",
                model="model",
                base_url="https://provider.invalid/v1",
                api_key="key",
            ),
        ),
        judge=JudgeConfig(model="", timeout=4, confidence_bypass_threshold=999),
        ollama=OllamaConfig(enabled=False, model=""),
    )

    result = judge.query_judge("review authentication", CATALOG, config=cfg)
    assert result["status"] == "applied"
    assert order == ["cli", "http"]

    monkeypatch.setattr(
        judge,
        "open_no_redirect",
        lambda *_a, **_kw: (_ for _ in ()).throw(TimeoutError()),
    )
    result = judge.query_judge("review authentication", CATALOG, config=cfg)
    assert result["status"] == "token_fallback"


def test_nonempty_cli_chain_never_calls_removed_legacy_or_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(judge, "invoke_cli_judge", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        judge,
        "open_no_redirect",
        lambda request, **_kwargs: calls.append(request.full_url),
    )
    cfg = AgencyConfig(
        providers=(
            ProviderEntry(
                name="codex",
                type="cli",
                transport="codex",
            ),
        ),
        judge=JudgeConfig(
            model="removed-paid-model",
            base_url="https://removed.invalid/v1",
            api_key="secret",
            timeout=3,
            confidence_bypass_threshold=999,
        ),
        ollama=OllamaConfig(
            enabled=True,
            model="removed-local-model",
            base_url="http://127.0.0.1:11434",
        ),
    )

    result = judge.query_judge("review authentication", CATALOG, config=cfg)

    assert result["status"] == "token_fallback"
    assert calls == []
