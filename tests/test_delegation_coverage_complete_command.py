"""Command-backend validation, protocol, and launch-failure contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.delegation import backend_command
from agency_runtime.core.delegation.backend_command import CommandBackend


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"name": ""}, ValueError, "backend name"),
        ({"output_format": "xml"}, ValueError, "output_format"),
        ({"max_output_chars": 0}, ValueError, "max_output_chars"),
        ({"extra_env": {"KEY": 7}}, TypeError, "extra_env"),
        ({"extra_env": {"BAD=KEY": "value"}}, ValueError, "extra_env"),
        ({"command": [""]}, ValueError, "argv item"),
        ({"command": ["bad\x00command"]}, ValueError, "NUL"),
    ],
)
def test_command_backend_rejects_invalid_configuration(
    kwargs: dict[str, Any],
    error: type[Exception],
    message: str,
) -> None:
    parameters: dict[str, Any] = {"command": ["tool"]}
    parameters.update(kwargs)
    with pytest.raises(error, match=message):
        CommandBackend(**parameters)


def test_executable_discovery_handles_empty_path_override_and_resolver_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert CommandBackend([]).executable_path() is None

    observed: list[tuple[str, str | None]] = []

    def resolve(executable: str, path: str | None = None) -> str | None:
        observed.append((executable, path))
        return "/safe/tool"

    monkeypatch.setattr(backend_command.shutil, "which", resolve)
    backend = CommandBackend(["tool"], extra_env={"Path": "/safe/bin"})
    assert backend.executable_path() == "/safe/tool"
    assert observed == [("tool", "/safe/bin")]

    monkeypatch.setattr(
        backend_command.shutil,
        "which",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("resolver failed")),
    )
    assert backend.executable_path() is None


def test_availability_rejects_executable_that_cannot_be_safely_launched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = CommandBackend(["tool"])
    monkeypatch.setattr(CommandBackend, "executable_path", lambda _self: "/safe/tool")
    monkeypatch.setattr(
        backend_command,
        "prepare_process_argv",
        lambda _argv: ["missing-launcher"],
    )
    monkeypatch.setattr(backend_command.shutil, "which", lambda _executable: None)

    record = backend.availability()

    assert record["available"] is False
    assert record["executable"] is None
    assert "cannot be launched safely" in record["reason"]


def test_structured_parsers_reject_oversized_invalid_and_empty_payloads() -> None:
    json_backend = CommandBackend(["tool"], output_format="json", max_output_chars=4)
    with pytest.raises(ValueError, match="configured limit"):
        json_backend.parse_stdout("12345")
    with pytest.raises(ValueError, match="invalid bounded JSON"):
        json_backend.parse_stdout("nope")

    jsonl_backend = CommandBackend(["tool"], output_format="jsonl")
    with pytest.raises(ValueError, match="no events"):
        jsonl_backend.parse_stdout("\n  \n")


@pytest.mark.parametrize(
    ("task", "error", "message"),
    [
        (7, TypeError, "must be a string"),
        (" ", ValueError, "must not be empty"),
        ("bad\x00task", ValueError, "must not contain NUL"),
    ],
)
def test_task_validation_rejects_ambiguous_input(
    task: Any,
    error: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error, match=message):
        CommandBackend(["tool"]).execute(task=task)


def test_workdir_validation_rejects_regular_file(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        CommandBackend(["tool"]).execute(task="work", workdir=str(path))


class _EmptyCommandBackend(CommandBackend):
    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        del task, recommended_agent
        return []


class _InvalidCommandBackend(CommandBackend):
    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        del task, recommended_agent
        return [""]


class _InvalidInputBackend(CommandBackend):
    invalid_input: Any = None

    def build_input(self, task: str, recommended_agent: str | None = None) -> Any:
        del task, recommended_agent
        return self.invalid_input


def test_execute_rejects_invalid_built_command_and_input() -> None:
    with pytest.raises(Exception, match="no command configured"):
        _EmptyCommandBackend(["tool"]).execute(task="work")
    with pytest.raises(ValueError, match="invalid argv"):
        _InvalidCommandBackend(["tool"]).execute(task="work")

    backend = _InvalidInputBackend(["tool"])
    backend.invalid_input = b"bytes"
    with pytest.raises(ValueError, match="built input"):
        backend.execute(task="work")
    backend.invalid_input = "bad\x00input"
    with pytest.raises(ValueError, match="built input"):
        backend.execute(task="work")


def test_execute_returns_unavailable_record_when_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = CommandBackend(["missing"])
    monkeypatch.setattr(CommandBackend, "executable_path", lambda _self: None)

    result = backend.execute(task="work", check=False)

    assert result["status"] == "unavailable"
    assert result["exit_code"] == 127


@pytest.mark.parametrize(
    ("raised", "status", "exit_code", "message"),
    [
        (FileNotFoundError(), "unavailable", 127, "disappeared"),
        (PermissionError("denied"), "failed", 126, "permission denied"),
    ],
)
def test_execute_normalizes_launch_races_and_permissions(
    monkeypatch: pytest.MonkeyPatch,
    raised: Exception,
    status: str,
    exit_code: int,
    message: str,
) -> None:
    backend = CommandBackend(["tool"])
    monkeypatch.setattr(CommandBackend, "executable_path", lambda _self: "/safe/tool")
    monkeypatch.setattr(
        backend_command,
        "_run_owned_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(raised),
    )

    result = backend.execute(task="work", check=False)

    assert result["status"] == status
    assert result["exit_code"] == exit_code
    assert message in result["error"]


def test_execute_rejects_oversized_structured_success_before_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = CommandBackend(["tool"], output_format="json", max_output_chars=3)
    monkeypatch.setattr(CommandBackend, "executable_path", lambda _self: "/safe/tool")
    monkeypatch.setattr(
        backend_command,
        "_run_owned_process",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["tool"], 0, stdout="1234", stderr=""
        ),
    )

    result = backend.execute(task="work", check=False)

    assert result["status"] == "failed"
    assert result["process_exit_code"] == 0
    assert "structured output exceeded" in result["error"]
