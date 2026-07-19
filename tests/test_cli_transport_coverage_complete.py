"""Complete allowlisted CLI transport parsing and failure coverage."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import cli_transport
from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.delegation.backends import BoundedProcessResult

_TRUSTED_CLI = str(Path(getattr(sys, "_base_executable", sys.executable)).resolve())


def _provider(transport: str, *, model: str = "model") -> ProviderEntry:
    return ProviderEntry(
        name=transport,
        type="cli",
        transport=transport,
        model=model,
    )


def test_repository_marker_probe_fails_closed_when_marker_is_unreadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repo"
    nested = repository / "src"
    nested.mkdir(parents=True)
    original_lstat = Path.lstat

    def guarded_lstat(path: Path):
        if path == repository / ".git":
            raise PermissionError("marker is unreadable")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", guarded_lstat)

    roots = cli_transport._repository_forbidden_roots(nested)

    assert nested.resolve() in roots
    assert repository.resolve() in roots


def test_timeout_and_version_parsers_fail_closed_on_invalid_values() -> None:
    class _NoFloat:
        def __float__(self) -> float:
            raise OverflowError

    assert cli_transport._valid_timeout(_NoFloat()) is False  # type: ignore[arg-type]
    assert cli_transport._version_tuple("Claude unknown") is None
    assert cli_transport._version_tuple("Claude 2.1.205") == (2, 1, 205)


def test_capability_inspection_handles_runner_exceptions() -> None:
    def fail(*_args: Any, **_kwargs: Any) -> BoundedProcessResult:
        raise OSError("unavailable")

    codex = cli_transport._inspect_codex_capability(
        "codex",
        timeout=1,
        runner=fail,
        environ={},
    )
    claude = cli_transport._inspect_claude_capability(
        "claude",
        timeout=1,
        runner=fail,
        environ={},
    )
    assert codex.usable is False
    assert claude.usable is False


@pytest.mark.parametrize(
    "payload",
    [
        "\n",
        '"scalar"',
        '{"type":"error"}',
        '{"type":"item.completed","item":{"type":"agent_message","text":"{}"}}',
        '{"type":"turn.completed"}',
    ],
)
def test_codex_parser_rejects_incomplete_or_ambiguous_event_streams(payload: str) -> None:
    assert cli_transport._parse_codex(payload) is None


def test_cli_parsers_reject_oversized_invalid_and_nested_string_payloads() -> None:
    assert cli_transport._parse_codex("x" * (cli_transport._MAX_CLI_OUTPUT_CHARS + 1)) is None
    invalid_message = "\n".join(
        [
            '{"type":"item.completed","item":{"type":"agent_message","text":"{invalid"}}',
            '{"type":"turn.completed"}',
        ]
    )
    assert cli_transport._parse_codex(invalid_message) is None
    assert cli_transport._parse_claude("{invalid") is None
    assert (
        cli_transport._parse_claude(
            json.dumps({"subtype": "completed", "structured_output": "{invalid"})
        )
        is None
    )
    assert cli_transport._parse_claude(
        json.dumps(
            {
                "subtype": "completed",
                "structured_output": '{"selected_ids":[],"confidence":0}',
            }
        )
    ) == {"selected_ids": [], "confidence": 0}


@pytest.mark.parametrize(
    "payload",
    [
        {"is_error": True, "result": {}},
        {"error": "failed", "result": {}},
        {"subtype": "streaming", "result": {}},
    ],
)
def test_claude_parser_rejects_error_and_nonterminal_payloads(payload: dict[str, Any]) -> None:
    assert cli_transport._parse_claude(json.dumps(payload)) is None


def test_cli_judge_handles_resolver_exception_and_invalid_prompt() -> None:
    def fail_resolver(_name: str) -> str:
        raise OSError("path unavailable")

    assert (
        cli_transport.invoke_cli_judge(
            _provider("codex"),
            "task",
            timeout=1,
            resolver=fail_resolver,
        )
        is None
    )
    assert (
        cli_transport.invoke_cli_structured(
            _provider("codex"),
            None,  # type: ignore[arg-type]
            {},
            timeout=1,
        )
        is None
    )
    assert (
        cli_transport.invoke_cli_judge(
            _provider("codex"),
            "\x00",
            timeout=1,
            resolver=lambda _name: "codex",
        )
        is None
    )


def test_claude_judge_passes_explicit_model_and_parses_structured_output(
    tmp_path: Path,
) -> None:
    del tmp_path
    captured: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        captured["argv"] = argv
        captured.update(kwargs)
        return BoundedProcessResult(
            0,
            json.dumps(
                {
                    "subtype": "completed",
                    "structured_output": {
                        "selected_ids": ["security"],
                        "confidence": 0.9,
                    },
                }
            ),
            "",
        )

    result = cli_transport.invoke_cli_judge(
        _provider("claude", model="claude-test"),
        "review security",
        timeout=1,
        resolver=lambda _name: _TRUSTED_CLI,
        runner=run,
        environ={"HOME": str(Path.home())},
    )
    assert result == {"selected_ids": ["security"], "confidence": 0.9}
    assert captured["argv"][-2:] == ["--model", "claude-test"]
