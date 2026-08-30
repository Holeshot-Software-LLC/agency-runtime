from __future__ import annotations

import os
from pathlib import Path

import pytest

from agency_runtime.core.bounded_io import atomic_write_text, read_bounded_regular_file


def test_bounded_file_reads_regular_content(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(b"payload")

    assert read_bounded_regular_file(target, limit=7, label="state") == b"payload"


def test_bounded_file_rejects_oversized_and_non_regular_inputs(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized"
    oversized.write_bytes(b"1234")

    with pytest.raises(OSError, match="size limit"):
        read_bounded_regular_file(oversized, limit=3, label="state")
    with pytest.raises(OSError, match="regular non-link"):
        read_bounded_regular_file(tmp_path, limit=3, label="state")


def test_bounded_file_rejects_symbolic_links_when_supported(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"private")
    link = tmp_path / "link"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic links are unavailable")

    with pytest.raises(OSError, match="regular non-link"):
        read_bounded_regular_file(link, limit=32, label="state")


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_bounded_file_rejects_invalid_limits(limit: object, tmp_path: Path) -> None:
    target = tmp_path / "state"
    target.write_bytes(b"x")

    with pytest.raises(ValueError, match="positive integer"):
        read_bounded_regular_file(target, limit=limit)  # type: ignore[arg-type]


def test_bounded_file_closes_descriptor_when_identity_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "state"
    target.write_bytes(b"x")
    original_fstat = os.fstat

    def changed_identity(descriptor: int):
        metadata = original_fstat(descriptor)
        values = list(metadata)
        values[1] = int(metadata.st_ino) + 1
        return os.stat_result(values)

    monkeypatch.setattr(os, "fstat", changed_identity)

    with pytest.raises(OSError, match="changed during open"):
        read_bounded_regular_file(target, limit=1, label="state")


def test_atomic_text_output_replaces_complete_artifact(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("old", encoding="utf-8")

    atomic_write_text(target, "new\n")

    assert target.read_text(encoding="utf-8") == "new\n"
    assert list(tmp_path.glob(".report.json.*.tmp")) == []


def test_atomic_text_output_preserves_old_artifact_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "report.json"
    target.write_text("old", encoding="utf-8")

    monkeypatch.setattr(os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("busy")))
    with pytest.raises(OSError, match="busy"):
        atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "old"
    assert list(tmp_path.glob(".report.json.*.tmp")) == []
