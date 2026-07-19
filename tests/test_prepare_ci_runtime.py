"""Hosted-CI private runtime preparation contracts."""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from agency_runtime.core.process_argv import snapshot_persistent_artifact
from scripts import prepare_ci_runtime
from tests import runtime_support


def test_prepare_ci_runtime_is_private_real_and_idempotent(tmp_path: Path) -> None:
    first = prepare_ci_runtime.prepare_ci_runtime("py3.10-linux", home_dir=tmp_path)
    second = prepare_ci_runtime.prepare_ci_runtime("py3.10-linux", home_dir=tmp_path)

    assert first == second
    root = Path(first["AGENCY_CI_ROOT"])
    python = Path(first["AGENCY_CI_PYTHON"])
    assert root.is_dir() and not root.is_symlink()
    assert python.is_file() and not python.is_symlink()
    assert python.resolve(strict=True).is_relative_to(root)
    assert snapshot_persistent_artifact(python, require_executable=True).resolved_path == str(
        python.resolve(strict=True)
    )
    if os.name != "nt":
        assert stat.S_IMODE(root.stat().st_mode) == 0o700
        assert not stat.S_IMODE(python.stat().st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
    completed = subprocess.run(
        [str(python), "-I", "-c", "import json; print(json.dumps({'ok': True}))"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {"ok": True}
    assert completed.stderr == ""


@pytest.mark.parametrize("label", ["", "../escape", "space here", "x" * 81])
def test_prepare_ci_runtime_rejects_unsafe_labels(tmp_path: Path, label: str) -> None:
    with pytest.raises(ValueError, match="filesystem-safe"):
        prepare_ci_runtime.prepare_ci_runtime(label, home_dir=tmp_path)


def test_prepare_ci_runtime_rejects_tampered_interpreter_without_following_link(
    tmp_path: Path,
) -> None:
    values = prepare_ci_runtime.prepare_ci_runtime("tamper-test", home_dir=tmp_path)
    python = Path(values["AGENCY_CI_PYTHON"])
    outside = tmp_path / "outside-python"
    sentinel = b"do-not-overwrite"
    outside.write_bytes(sentinel)
    python.unlink()
    try:
        python.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="incomplete or unsafe"):
        prepare_ci_runtime.prepare_ci_runtime("tamper-test", home_dir=tmp_path)
    assert outside.read_bytes() == sentinel


def test_trusted_test_interpreter_prefers_private_ci_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = tmp_path / "runtime with spaces" / "python"
    monkeypatch.setenv("AGENCY_CI_PYTHON", str(configured))

    assert runtime_support.trusted_test_interpreter() == configured.resolve()


def test_github_environment_writer_is_append_only_and_rejects_injection(
    tmp_path: Path,
) -> None:
    target = tmp_path / "github.env"
    target.write_text("EXISTING=value\n", encoding="utf-8")
    prepare_ci_runtime._write_github_environment(
        target,
        {"AGENCY_CI_ROOT": tmp_path.as_posix()},
    )
    assert target.read_text(encoding="utf-8") == (
        f"EXISTING=value\nAGENCY_CI_ROOT={tmp_path.as_posix()}\n"
    )

    with pytest.raises(RuntimeError, match="line breaks"):
        prepare_ci_runtime._write_github_environment(target, {"BAD": "line\nbreak"})

    link = tmp_path / "link.env"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlinks are unavailable: {exc}")
    with pytest.raises(RuntimeError, match="symlink"):
        prepare_ci_runtime._write_github_environment(link, {"BAD": "value"})
