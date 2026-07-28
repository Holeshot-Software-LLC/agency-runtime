"""Focused live Windows test for handle-bound directory retirement."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agency_runtime.core.windows_handle_rename import rename_directory_handle_bound


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-bound rename contract")
def test_handle_bound_directory_rename_moves_the_opened_identity(tmp_path: Path) -> None:
    source = tmp_path / "owned-source"
    destination = tmp_path / "retained-destination"
    source.mkdir()
    (source / "payload.txt").write_text("owned payload\n", encoding="utf-8")
    before = os.lstat(source)
    destination_parent = os.lstat(destination.parent)
    inode = int(getattr(before, "st_ino", 0) or 0)
    if inode <= 0:
        pytest.skip("this Windows filesystem does not expose a stable directory file ID")
    validated: list[int] = []

    def validate() -> None:
        current = os.lstat(source)
        validated.append(int(getattr(current, "st_ino", 0) or 0))
        assert (source / "payload.txt").read_text(encoding="utf-8") == "owned payload\n"

    rename_directory_handle_bound(
        source,
        destination,
        expected_device=int(before.st_dev),
        expected_inode=inode,
        expected_destination_device=int(destination_parent.st_dev),
        expected_destination_inode=int(getattr(destination_parent, "st_ino", 0) or 0),
        validate=validate,
    )

    assert validated == [inode]
    assert source.exists() is False
    assert destination.is_dir()
    assert int(getattr(os.lstat(destination), "st_ino", 0) or 0) == inode
    assert (destination / "payload.txt").read_text(encoding="utf-8") == "owned payload\n"


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-bound rename contract")
def test_handle_bound_directory_rename_rejects_wrong_destination_parent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "owned-source"
    destination = tmp_path / "retained-destination"
    source.mkdir()
    before = os.lstat(source)
    parent = os.lstat(destination.parent)

    with pytest.raises(OSError, match="destination parent identity changed"):
        rename_directory_handle_bound(
            source,
            destination,
            expected_device=int(before.st_dev),
            expected_inode=int(getattr(before, "st_ino", 0) or 0),
            expected_destination_device=int(parent.st_dev),
            expected_destination_inode=int(getattr(parent, "st_ino", 0) or 0) + 1,
            validate=lambda: None,
        )

    assert source.is_dir()
    assert destination.exists() is False
