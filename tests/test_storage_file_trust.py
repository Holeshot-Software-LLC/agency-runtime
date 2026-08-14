"""The integrity boundary Agency requires of files other programs wrote.

Every caller of ``storage_file_is_trusted`` reads a foreign artifact -- a Claude
sub-agent transcript, a Codex rollout, a host wiring file. Agency does not own
those writers and cannot choose their umask, so the boundary has to be
integrity: nobody but the owner could have substituted the bytes.

Requiring the group and other *read* bits to be clear as well demanded mode
0600 from files hosts write at 0644, which made the Rule 4 host-artifact proof
unobtainable on Linux while Windows accepted the same artifact.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from agency_runtime.core.store.security import storage_file_is_trusted

posix_only = pytest.mark.skipif(
    os.name == "nt",
    reason="the Windows branch checks ACLs, not mode bits",
)


def _artifact(tmp_path: Path, *, mode: int) -> Path:
    path = tmp_path / "agent-child.jsonl"
    path.write_text('{"type":"user"}\n', encoding="utf-8")
    os.chmod(path, mode)
    return path


@posix_only
def test_a_host_written_artifact_at_the_usual_umask_is_trusted(tmp_path: Path) -> None:
    """0644 is what a host writes; refusing it refuses every real artifact."""

    assert storage_file_is_trusted(_artifact(tmp_path, mode=0o644), is_windows=False) is True


@posix_only
@pytest.mark.parametrize("mode", [0o600, 0o640, 0o604, 0o444])
def test_every_owner_only_writable_mode_is_trusted(tmp_path: Path, mode: int) -> None:
    assert storage_file_is_trusted(_artifact(tmp_path, mode=mode), is_windows=False) is True


@posix_only
@pytest.mark.parametrize("mode", [0o664, 0o646, 0o666, 0o622])
def test_a_group_or_other_writable_artifact_is_refused(tmp_path: Path, mode: int) -> None:
    """Writability is the boundary: another account could substitute the bytes."""

    assert storage_file_is_trusted(_artifact(tmp_path, mode=mode), is_windows=False) is False


@posix_only
def test_a_symlink_is_refused_however_permissive_its_target(tmp_path: Path) -> None:
    target = _artifact(tmp_path, mode=0o600)
    link = tmp_path / "link.jsonl"
    link.symlink_to(target)

    assert storage_file_is_trusted(link, is_windows=False) is False


@posix_only
def test_a_second_hard_link_is_refused(tmp_path: Path) -> None:
    """A second link is a second name an attacker may already hold."""

    target = _artifact(tmp_path, mode=0o600)
    twin = tmp_path / "twin.jsonl"
    os.link(target, twin)

    assert storage_file_is_trusted(target, is_windows=False) is False
    assert storage_file_is_trusted(twin, is_windows=False) is False


@posix_only
def test_a_directory_is_refused(tmp_path: Path) -> None:
    assert storage_file_is_trusted(tmp_path, is_windows=False) is False


def test_a_missing_path_is_refused(tmp_path: Path) -> None:
    assert storage_file_is_trusted(tmp_path / "absent.jsonl", is_windows=os.name == "nt") is False


@posix_only
def test_a_file_owned_by_another_account_is_refused(tmp_path: Path, monkeypatch) -> None:
    """Ownership still has to be ours; only the read-bit demand was dropped."""

    artifact = _artifact(tmp_path, mode=0o644)
    monkeypatch.setattr(os, "geteuid", lambda: os.stat(artifact).st_uid + 1)

    assert storage_file_is_trusted(artifact, is_windows=False) is False


@posix_only
def test_the_setuid_and_sticky_bits_do_not_confuse_the_writability_check(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path, mode=0o644 | stat.S_ISUID | stat.S_ISVTX)

    assert storage_file_is_trusted(artifact, is_windows=False) is True
