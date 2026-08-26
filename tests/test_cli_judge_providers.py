"""CLI-authenticated provider contracts and ordered judge fallback."""

from __future__ import annotations

import json
import os
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
from agency_runtime.core.process_argv import PreparedProcessArgv
from agency_runtime.core.selector import judge
from tests.runtime_support import trusted_test_interpreter

_TRUSTED_CLI = str(trusted_test_interpreter())
_TRUSTED_CLI_DIRECTORY = str(Path(_TRUSTED_CLI).parent)

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
        resolver=lambda _name: _TRUSTED_CLI,
        runner=runner,
        environ={"PATH": _TRUSTED_CLI_DIRECTORY, "SECRET_TOKEN": "do-not-forward"},
    )

    assert status == CLIProviderStatus(
        transport="codex",
        installed=True,
        authenticated=True,
        usable=True,
        executable=_TRUSTED_CLI,
    )
    assert calls == [
        [_TRUSTED_CLI, "login", "status"],
        [_TRUSTED_CLI, "exec", "--help"],
    ]


def test_cli_status_reuses_one_frozen_executable_identity() -> None:
    resolver_calls: list[str] = []
    frozen_identities: list[tuple[object, ...]] = []

    def resolver(name: str, **_kwargs: object) -> str:
        resolver_calls.append(name)
        return _TRUSTED_CLI

    def runner(argv: list[str], **_kwargs: Any) -> BoundedProcessResult:
        assert isinstance(argv, PreparedProcessArgv)
        frozen_identities.append(argv.executable_identities)
        if argv[1:3] == ["login", "status"]:
            return _result("Logged in")
        return _result(
            "--json --output-schema --ephemeral --ignore-user-config "
            "--ignore-rules --sandbox --strict-config"
        )

    status = inspect_cli_transport(
        "codex",
        resolver=resolver,
        runner=runner,
        environ={"PATH": _TRUSTED_CLI_DIRECTORY},
    )

    assert status.usable is True
    assert resolver_calls == ["codex"]
    assert len(frozen_identities) == 2
    assert frozen_identities[0] is frozen_identities[1]


@pytest.mark.parametrize("transport", ["codex", "claude"])
def test_repo_local_cli_shadow_is_never_executed(
    transport: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / (f"{transport}.exe" if os.name == "nt" else transport)
    executable.write_bytes(b"not a trusted host CLI")
    if os.name != "nt":
        executable.chmod(0o700)
    monkeypatch.chdir(tmp_path)
    observed_search_paths: list[str] = []
    launched = False

    def resolver(_name: str, *, path: str) -> str:
        observed_search_paths.append(path)
        return str(executable)

    def runner(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        nonlocal launched
        launched = True
        return _result()

    status = inspect_cli_transport(
        transport,
        resolver=resolver,
        runner=runner,
        environ={"PATH": os.pathsep.join((str(tmp_path), _TRUSTED_CLI_DIRECTORY))},
    )

    # A shadow is refused, not missing. Reporting "not found" for a binary that
    # is right there sends the reader hunting through PATH; that exact confusion
    # cost a day when npm's ACLs started refusing both real host CLIs.
    assert status.reason.startswith("executable unusable")
    assert launched is False
    assert observed_search_paths
    assert str(tmp_path) not in observed_search_paths[0].split(os.pathsep)


@pytest.mark.parametrize("shadow_kind", ["native", "npm-shim"])
def test_nested_repo_cli_shadows_are_never_executed(
    shadow_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repo"
    (repository / ".git").mkdir(parents=True)
    nested_cwd = repository / "src" / "package"
    nested_cwd.mkdir(parents=True)
    if shadow_kind == "native":
        shadow_directory = repository / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        executable = shadow_directory / ("codex.exe" if os.name == "nt" else "codex")
    else:
        shadow_directory = repository / "node_modules" / ".bin"
        executable = shadow_directory / ("codex.cmd" if os.name == "nt" else "codex")
    shadow_directory.mkdir(parents=True)
    executable.write_bytes(b"repository-controlled host CLI")
    if os.name == "nt" and shadow_kind == "npm-shim":
        executable.with_suffix(".exe").write_bytes(b"repository-controlled npm companion")
    if os.name != "nt":
        executable.chmod(0o700)
    monkeypatch.chdir(nested_cwd)
    observed_search_paths: list[str] = []
    launched = False

    def resolver(_name: str, *, path: str) -> str:
        observed_search_paths.append(path)
        return str(executable)

    def runner(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        nonlocal launched
        launched = True
        return _result()

    status = inspect_cli_transport(
        "codex",
        resolver=resolver,
        runner=runner,
        environ={"PATH": os.pathsep.join((str(shadow_directory), _TRUSTED_CLI_DIRECTORY))},
    )

    assert status.reason.startswith("executable unusable")
    assert launched is False
    assert observed_search_paths
    assert str(shadow_directory) not in observed_search_paths[0].split(os.pathsep)
    assert _TRUSTED_CLI_DIRECTORY in observed_search_paths[0].split(os.pathsep)


def test_cli_status_reports_missing_auth_without_exposing_output() -> None:
    def runner(_argv: list[str], **_kwargs: Any) -> BoundedProcessResult:
        return _result("account@example.test token=secret", returncode=1)

    status = inspect_cli_transport(
        "codex",
        resolver=lambda _name: _TRUSTED_CLI,
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
        resolver=lambda _name: _TRUSTED_CLI,
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
        resolver=lambda _name: _TRUSTED_CLI,
        runner=runner,
    )

    assert status.authenticated is True
    assert status.usable is usable


def test_safe_cli_environment_drops_unrelated_credentials() -> None:
    safe = safe_cli_environment(
        {
            "PATH": _TRUSTED_CLI_DIRECTORY,
            "HOME": "/home/user",
            "CODEX_HOME": "/home/user/.codex",
            "NODE_EXTRA_CA_CERTS": "/trust/corporate-ca.pem",
            "REQUESTS_CA_BUNDLE": "/trust/python-ca.pem",
            "SSL_CERT_FILE": "/trust/openssl-ca.pem",
            "LITELLM_API_KEY": "configured-but-not-scoped",
            "OPENAI_API_KEY": "secret",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "UNRELATED_TOKEN": "secret",
        }
    )

    assert safe["PATH"] == _TRUSTED_CLI_DIRECTORY
    assert safe["CODEX_HOME"] == "/home/user/.codex"
    assert safe["NODE_EXTRA_CA_CERTS"] == "/trust/corporate-ca.pem"
    assert safe["REQUESTS_CA_BUNDLE"] == "/trust/python-ca.pem"
    assert safe["SSL_CERT_FILE"] == "/trust/openssl-ca.pem"
    assert "LITELLM_API_KEY" not in safe
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
        schema_path = Path(argv[argv.index("--output-schema") + 1])
        projected = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "uniqueItems" not in json.dumps(projected)
        return _result(stdout)

    parsed = invoke_cli_judge(
        ProviderEntry(
            name="codex",
            type="cli",
            transport="codex",
            model="openai/gpt-5-mini",
            reasoning_effort="low",
        ),
        prompt,
        timeout=4,
        resolver=lambda _name: _TRUSTED_CLI,
        runner=runner,
        environ={
            "PATH": _TRUSTED_CLI_DIRECTORY,
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
    assert 'model_reasoning_effort="low"' in observed["argv"]
    assert "--strict-config" in observed["argv"]
    assert "features.shell_tool=false" in observed["argv"]
    assert "features.unified_exec=false" in observed["argv"]
    assert 'web_search="disabled"' in observed["argv"]
    assert observed["env"]["CODEX_HOME"] == "C:\\Users\\person\\.codex"
    assert observed["env"]["USERPROFILE"].startswith(observed["cwd"])
    for name in ("TEMP", "TMP", "TMPDIR"):
        assert Path(observed["env"][name]).is_relative_to(Path(observed["cwd"]))
    assert "OPENAI_API_KEY" not in observed["env"]


def test_codex_structured_accepts_completed_schema_item_when_turn_hangs() -> None:
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started"}),
            json.dumps({"type": "turn.started"}),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": '{"selected_ids":[],"confidence":0}',
                    },
                }
            ),
        ]
    )

    parsed = invoke_cli_judge(
        ProviderEntry(name="codex", type="cli", transport="codex", model="gpt-test"),
        "route safely",
        timeout=3,
        resolver=lambda _name: _TRUSTED_CLI,
        runner=lambda *_args, **_kwargs: _result(
            stdout,
            timed_out=True,
            returncode=124,
        ),
    )

    assert parsed == {"selected_ids": [], "confidence": 0}


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
        resolver=lambda _name: _TRUSTED_CLI,
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
            resolver=lambda _name: _TRUSTED_CLI,
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
            resolver=lambda _name: _TRUSTED_CLI,
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


@pytest.mark.parametrize(
    "provider",
    [
        ProviderEntry(name="codex", type="cli", transport="codex", reasoning_effort="extreme"),
        ProviderEntry(name="claude", type="cli", transport="claude", reasoning_effort="low"),
    ],
)
def test_cli_judge_rejects_unallowlisted_reasoning_effort_before_launch(
    provider: ProviderEntry,
) -> None:
    called = False

    def runner(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        nonlocal called
        called = True
        return _result()

    assert (
        invoke_cli_judge(
            provider,
            "private prompt remains on stdin",
            timeout=1,
            resolver=lambda _name: _TRUSTED_CLI,
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


def test_failed_cli_falls_through_to_http_then_explicit_degradation(
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
    assert result["status"] == "inference_unavailable"
    assert result["selected_ids"] == []
    assert [entry["provider_name"] for entry in result["provider_attempts"]] == [
        "codex",
        "http",
    ]


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

    assert result["status"] == "inference_unavailable"
    assert result["selected_ids"] == []
    assert calls == []
