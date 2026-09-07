from __future__ import annotations

import subprocess

import pytest

from scripts import run_local_gates as subject


@pytest.mark.parametrize("fast", (False, True))
@pytest.mark.parametrize("node_available", (False, True))
def test_local_gates_require_node_before_claiming_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fast: bool,
    node_available: bool,
) -> None:
    selected = (
        subject.Gate("earlier gate", ("earlier-test-command",)),
        subject.Gate("dashboard UI", ("node", "--test", "tests/dashboard_ui.test.mjs")),
        subject.Gate("later gate", ("unused-test-command",)),
    )
    calls: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subject, "gates", lambda: selected)
    monkeypatch.setattr(subject.sys, "argv", ["run_local_gates.py", *(["--fast"] if fast else [])])
    monkeypatch.setattr(
        subject.shutil, "which", lambda _name: "/available/node" if node_available else None
    )
    monkeypatch.setattr(subject.subprocess, "run", run)

    assert subject.main() == (0 if node_available else 1)
    output = capsys.readouterr().out
    if node_available:
        assert calls == [gate.command for gate in selected]
        assert "All 3 gates passed" in output
    else:
        assert calls == []
        assert "FAILED: dashboard UI" in output
        assert "node is not installed" in output
        assert "All 3 gates passed" not in output
        assert "No gates ran" in output
        assert "SKIPPED" not in output


def test_local_gate_listing_needs_no_executables(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(subject.sys, "argv", ["run_local_gates.py", "--list"])
    monkeypatch.setattr(
        subject, "gates", lambda: (subject.Gate("dashboard UI", ("node", "--test")),)
    )
    monkeypatch.setattr(
        subject.shutil, "which", lambda _name: pytest.fail("listing must not probe")
    )
    monkeypatch.setattr(
        subject.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("listing must not execute")
    )

    assert subject.main() == 0
    assert "dashboard UI" in capsys.readouterr().out


def test_local_gates_stop_after_an_ordinary_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    selected = (
        subject.Gate("first gate", ("first-test-command",)),
        subject.Gate("later gate", ("later-test-command",)),
    )
    calls: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 2)

    monkeypatch.setattr(subject.sys, "argv", ["run_local_gates.py"])
    monkeypatch.setattr(subject, "gates", lambda: selected)
    monkeypatch.setattr(subject.subprocess, "run", run)

    assert subject.main() == 1
    assert calls == [selected[0].command]
    assert "FAILED: first gate" in capsys.readouterr().out
