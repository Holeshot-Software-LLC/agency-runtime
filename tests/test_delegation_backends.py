"""Deterministic delegation backend contract tests (no host/network required)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.generic.wrapper import GenericAdapter
from agency_runtime.core.delegation.backends import (
    BackendExecutionError,
    BackendProtocolError,
    BackendRegistry,
    BackendTimeoutError,
    BackendUnavailableError,
    ClaudeExecBackend,
    CodexExecBackend,
    CommandBackend,
    GenericCLIBackend,
    HermesDelegateBackend,
    OpenClawSessionsBackend,
)
from agency_runtime.core.store.sqlite import Store


def _fake_cli(tmp_path: Path) -> Path:
    script = tmp_path / "fake_agent.py"
    script.write_text(
        """
import json
import os
import sys
import time

mode = os.environ.get("FAKE_AGENT_MODE", "echo")
if mode == "echo":
    sys.stdout.write(sys.argv[-1])
elif mode == "argv":
    print(json.dumps(sys.argv[1:]))
elif mode == "codex":
    print(json.dumps({"type": "thread.started", "thread_id": "thread-1"}))
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}))
elif mode == "claude":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "done"}))
elif mode == "claude_error":
    print(json.dumps({"type": "result", "subtype": "error", "is_error": True, "result": "bad"}))
elif mode == "openclaw":
    print(json.dumps({"payloads": [{"text": "done"}], "meta": {"transport": "embedded"}}))
elif mode == "in_flight":
    print(json.dumps({"status": "in_flight", "payloads": []}))
elif mode == "invalid":
    print("not-json")
elif mode == "large":
    print("x" * 1000, end="")
elif mode == "fail":
    print("backend rejected task", file=sys.stderr)
    raise SystemExit(7)
elif mode == "sleep":
    time.sleep(5)
""".lstrip(),
        encoding="utf-8",
    )
    return script


def _command(script: Path) -> tuple[str, str]:
    return sys.executable, str(script)


def test_command_backend_uses_argv_without_shell_interpretation(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    task = '$(touch injected); "quoted"\nsecond line'
    backend = CommandBackend(command=_command(script), timeout=5)

    result = backend.delegate(task=task, workdir=str(tmp_path))

    assert result["status"] == "completed"
    assert result["output"] == task
    assert result["command"][-1] == task
    assert not (tmp_path / "injected").exists()


def test_command_backend_preserves_environment_and_resolved_workdir(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = CommandBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "argv"},
        output_format="json",
    )

    result = backend.delegate(task="inspect argv", workdir=str(tmp_path))

    assert result["output"][-1] == "inspect argv"
    assert result["workdir"] == str(tmp_path.resolve())
    assert Path(result["executable"]).resolve() == Path(sys.executable).resolve()


def test_command_backend_reports_nonzero_exit_with_result(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = CommandBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "fail"},
    )

    with pytest.raises(BackendExecutionError, match="exited with 7") as caught:
        backend.delegate(task="fail")

    assert caught.value.result["status"] == "failed"
    assert caught.value.result["exit_code"] == 7
    assert "backend rejected task" in caught.value.result["stderr"]


def test_command_backend_timeout_is_not_success(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = CommandBackend(
        command=_command(script),
        timeout=0.05,
        extra_env={"FAKE_AGENT_MODE": "sleep"},
    )

    with pytest.raises(BackendTimeoutError, match="timed out") as caught:
        backend.delegate(task="wait")

    assert caught.value.result["status"] == "timed_out"
    assert caught.value.result["exit_code"] == 124


def test_command_backend_timeout_terminates_descendant_processes(tmp_path: Path) -> None:
    marker = tmp_path / "descendant-survived.txt"
    child = tmp_path / "child.py"
    child.write_text(
        "import pathlib, sys, time\n"
        "time.sleep(2.0)\n"
        "pathlib.Path(sys.argv[1]).write_text('survived', encoding='utf-8')\n",
        encoding="utf-8",
    )
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
        "time.sleep(5)\n",
        encoding="utf-8",
    )
    backend = CommandBackend(command=(sys.executable, str(parent), str(child), str(marker)), timeout=0.1)

    with pytest.raises(BackendTimeoutError):
        backend.delegate(task="ignored")

    # taskkill may take close to a second to enumerate a Windows process tree.
    # The marker delay intentionally leaves ample room for that bounded cleanup.
    time.sleep(2.2)
    assert not marker.exists()


def test_command_backend_bounds_text_output(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = CommandBackend(
        command=_command(script),
        max_output_chars=80,
        extra_env={"FAKE_AGENT_MODE": "large"},
    )

    result = backend.delegate(task="large")

    assert result["stdout_truncated"] is True
    assert result["output"] == result["stdout"]
    assert len(result["stdout"]) <= 80


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_command_backend_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout"):
        CommandBackend(command=(sys.executable,), timeout=timeout)


def test_command_backend_rejects_shell_command_strings() -> None:
    with pytest.raises(TypeError, match="argv sequence"):
        CommandBackend(command="agent --unsafe")  # type: ignore[arg-type]


def test_command_backend_rejects_missing_workdir(tmp_path: Path) -> None:
    backend = CommandBackend(command=(sys.executable,))
    with pytest.raises(ValueError, match="workdir does not exist"):
        backend.delegate(task="task", workdir=str(tmp_path / "missing"))


def test_unconfigured_generic_backend_is_truthfully_unavailable() -> None:
    backend = GenericCLIBackend()
    assert backend.availability() == {
        "backend": "generic",
        "available": False,
        "executable": None,
        "reason": "no command configured",
    }
    with pytest.raises(BackendUnavailableError, match="no command configured"):
        backend.delegate(task="task")


def test_registry_error_includes_unavailability_reason() -> None:
    registry = BackendRegistry([GenericCLIBackend()])
    with pytest.raises(BackendUnavailableError, match="generic: no command configured"):
        registry.select_backend(preferred="generic")


def test_codex_backend_validates_jsonl_and_extracts_final_message(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = CodexExecBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "codex"},
    )

    result = backend.delegate(task="fix it", recommended_agent="code-reviewer")

    assert result["output"] == "done"
    assert result["events"][-1]["type"] == "turn.completed"
    assert result["command"][-4:-1] == ["--json", "--color", "never"]
    assert "code-reviewer" in result["command"][-1]


def test_codex_backend_rejects_incomplete_jsonl_success(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = CodexExecBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "invalid"},
    )
    with pytest.raises(BackendProtocolError, match="invalid success response"):
        backend.delegate(task="fix it")


def test_claude_backend_validates_json_result(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = ClaudeExecBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "claude"},
    )

    result = backend.delegate(task="fix it")

    assert result["output"] == "done"
    assert result["response"]["is_error"] is False


def test_claude_backend_does_not_promote_is_error_response(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = ClaudeExecBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "claude_error"},
    )
    with pytest.raises(BackendProtocolError, match="is_error=true"):
        backend.delegate(task="fix it")


def test_hermes_backend_uses_documented_scripted_one_shot(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = HermesDelegateBackend(command=_command(script))

    result = backend.delegate(task="fix it", recommended_agent="python-pro")

    assert result["status"] == "completed"
    assert "python-pro" in result["output"]
    assert "fix it" in result["output"]


def test_openclaw_backend_uses_agent_cli_not_fake_sessions_spawn(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = OpenClawSessionsBackend(
        command=_command(script),
        agent_id="main",
        extra_env={"FAKE_AGENT_MODE": "openclaw"},
    )

    result = backend.delegate(task="fix it", recommended_agent="code-reviewer")

    argv = result["command"]
    assert "sessions_spawn" not in argv
    assert argv[2:4] == ["--agent", "main"]
    assert argv[-1] == "--json"
    assert "code-reviewer" in argv[-2]
    assert result["output"] == "done"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "pending"},
        {"error": "permission denied"},
        {"status": "success", "payloads": []},
    ],
)
def test_openclaw_rejects_nonterminal_or_empty_success(
    payload: dict[str, Any],
) -> None:
    backend = OpenClawSessionsBackend()
    with pytest.raises(ValueError):
        backend.parse_stdout(json.dumps(payload))


@pytest.mark.parametrize("payload", [{"error": "rate limit"}, {}, {"subtype": "success"}])
def test_claude_rejects_error_or_empty_success(payload: dict[str, Any]) -> None:
    backend = ClaudeExecBackend()
    with pytest.raises(ValueError):
        backend.parse_stdout(json.dumps(payload))


def test_openclaw_in_flight_response_is_not_completed(tmp_path: Path) -> None:
    script = _fake_cli(tmp_path)
    backend = OpenClawSessionsBackend(
        command=_command(script),
        extra_env={"FAKE_AGENT_MODE": "in_flight"},
    )
    with pytest.raises(BackendProtocolError, match="in_flight"):
        backend.delegate(task="fix it")


def test_adapter_wrappers_use_hardened_process_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")

    def available(_name: str) -> str:
        return sys.executable

    calls: list[list[str]] = []

    def completed(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        if "--json" in argv and "--color" in argv:
            stdout = "\n".join(
                [
                    json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}}),
                    json.dumps({"type": "turn.completed"}),
                ]
            )
        elif "--output-format" in argv:
            stdout = json.dumps({"is_error": False, "result": "ok"})
        else:
            stdout = "ok"
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

    monkeypatch.setattr("agency_runtime.core.delegation.backends.shutil.which", available)
    monkeypatch.setattr("agency_runtime.core.delegation.backends._run_owned_process", completed)

    codex = CodexAdapter(store=store).exec("task", workdir=str(tmp_path))
    claude = ClaudeAdapter(store=store).exec("task", workdir=str(tmp_path))
    generic = GenericAdapter(store=store, cli_cmd="custom-agent").exec("task", workdir=str(tmp_path))

    assert (codex["status"], codex["output"]) == ("completed", "ok")
    assert (claude["status"], claude["output"]) == ("completed", "ok")
    assert (generic["status"], generic["output"]) == ("completed", "ok")
    assert all(isinstance(argv, list) for argv in calls)


def test_generic_adapter_without_command_returns_unavailable(tmp_path: Path) -> None:
    result = GenericAdapter(store=Store(tmp_path / "agency.db")).exec("task", workdir=str(tmp_path))
    assert result["status"] == "unavailable"
    assert result["exit_code"] == 127
    assert result["error"] == "no command configured"
