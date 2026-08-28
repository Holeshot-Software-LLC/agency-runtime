"""Early local-suite trust diagnostics and private fixture creation."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from tests import conftest as suite
from tests import runtime_support


class _Config:
    pass


def test_offline_configuration_is_private_under_cooperative_umask(tmp_path: Path) -> None:
    config_path = tmp_path / "nested" / "offline-config" / "agency.yaml"
    previous = os.umask(0o002)
    try:
        suite._write_offline_configuration(config_path, config_path.parent)
    finally:
        os.umask(previous)

    assert stat.S_IMODE(config_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX umask contract")
def test_suite_umask_is_private_and_restores_the_exact_caller_value() -> None:
    config = _Config()
    initial = os.umask(0o002)
    try:
        suite.pytest_configure(config)  # type: ignore[arg-type]
        configured = os.umask(0o077)
        assert configured == 0o077
        suite.pytest_unconfigure(config)  # type: ignore[arg-type]
        restored = os.umask(initial)
        assert restored == 0o002
    finally:
        os.umask(initial)


def test_untrusted_test_interpreter_has_one_actionable_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "unsafe" / "python"
    monkeypatch.setattr(runtime_support, "trusted_test_interpreter", lambda: candidate)
    monkeypatch.setattr(
        "agency_runtime.core.launcher_bootstrap.persistent_python_executable",
        lambda _candidate: (_ for _ in ()).throw(OSError("unsafe namespace")),
    )

    with pytest.raises(RuntimeError) as captured:
        runtime_support.validate_trusted_test_interpreter()

    message = str(captured.value)
    assert "OS- or owner-protected Python" in message
    assert "AGENCY_CI_PYTHON" in message
    assert str(candidate) in message
    assert "unsafe namespace" not in message


def test_trusted_test_interpreter_returns_exact_validated_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate-python"
    trusted = tmp_path / "trusted-python"
    monkeypatch.setattr(runtime_support, "trusted_test_interpreter", lambda: candidate)
    monkeypatch.setattr(
        "agency_runtime.core.launcher_bootstrap.persistent_python_executable",
        lambda value: str(trusted) if value == candidate else "unexpected",
    )

    assert runtime_support.validate_trusted_test_interpreter() == trusted
