"""A refused executable and a missing one are different problems.

Collapsing them into "executable not found" cost a day on 2026-08-10: both host
CLIs resolved fine and were then rejected because npm's directory permits
cross-account substitution, so `agency doctor` reported a missing binary that was
sitting right there on PATH.
"""

from __future__ import annotations

import pytest

from agency_runtime.core import cli_transport
from agency_runtime.core.cli_transport import _resolve_cli, _unusable_executable_reason


def test_a_refused_executable_says_refused_not_missing() -> None:
    reason = _unusable_executable_reason(
        PermissionError(
            "executable parent namespace permits cross-account substitution: "
            r"C:\Users\x\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
        )
    )

    assert reason.startswith("executable refused as untrusted")
    assert "not found" not in reason


def test_a_genuinely_missing_executable_still_says_not_found() -> None:
    assert _unusable_executable_reason(FileNotFoundError("claude")) == "executable not found"


def test_an_unexpected_failure_names_its_type_without_leaking_a_stack() -> None:
    reason = _unusable_executable_reason(RuntimeError("boom at 0xdeadbeef"))

    assert reason == "executable could not be prepared: RuntimeError"
    assert "0xdeadbeef" not in reason


def test_no_reason_ever_echoes_the_exception_text() -> None:
    """A status string is a public surface; a resolver message is not curated."""

    secret = "private-account@example.invalid"
    for error in (
        PermissionError(secret),
        OSError(secret),
        FileNotFoundError(secret),
        RuntimeError(secret),
    ):
        assert secret not in _unusable_executable_reason(error)


def test_the_reason_reaches_the_transport_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """The whole point: the reason has to survive the trip to the caller."""

    def _refuse(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("executable parent namespace permits cross-account substitution: x")

    monkeypatch.setattr(cli_transport, "resolve_executable_path", _refuse)

    resolved = _resolve_cli("claude", lambda _name: "claude", environ={"PATH": ""})

    assert resolved.executable is None
    assert "refused as untrusted" in resolved.reason


def test_a_usable_executable_carries_no_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = object()
    monkeypatch.setattr(cli_transport, "resolve_executable_path", lambda *a, **k: "claude")
    monkeypatch.setattr(cli_transport, "prepare_process_argv", lambda *a, **k: sentinel)
    monkeypatch.setattr(cli_transport, "freeze_process_argv", lambda prepared, **k: prepared)

    resolved = _resolve_cli("claude", lambda _name: "claude", environ={"PATH": ""})

    assert resolved.executable is sentinel
    assert resolved.reason == ""
