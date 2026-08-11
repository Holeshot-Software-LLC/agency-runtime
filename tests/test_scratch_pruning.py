"""Bounded pytest scratch retention.

Nothing reclaimed this suite's Windows scratch tree, and by 2026-08-10 it held
113,849 directories dating back to 2026-07-16. That is not only waste: filesystem
identity assertions in ``test_build_distributions.py`` began failing at random,
and the failures moved between runs on a barely-changed tree, which cost real
diagnosis time before the cause was found (handoff §7.2, §6 entry 20).

These tests pin the retention rule directly so it cannot regress quietly back
into the same mess.
"""

from __future__ import annotations

from pathlib import Path

from tests.conftest import _RETAINED_NUMBERED_DIRS, _prune_pytest_scratch


def _numbered(user_root: Path, number: int) -> Path:
    path = user_root / f"pytest-{number}"
    path.mkdir(parents=True)
    (path / "artifact.txt").write_text("scratch", encoding="utf-8")
    return path


def test_only_the_newest_numbered_directories_survive(tmp_path: Path) -> None:
    user_root = tmp_path / "pytest-of-someone"
    created = [_numbered(user_root, number) for number in range(6)]

    _prune_pytest_scratch(tmp_path)

    surviving = sorted(
        int(path.name.rpartition("-")[2]) for path in user_root.glob("pytest-*") if path.is_dir()
    )
    assert surviving == [4, 5], "retention must keep the newest, not the first found"
    assert len(surviving) == _RETAINED_NUMBERED_DIRS
    assert not created[0].exists()


def test_orphaned_cleanup_directories_are_swept(tmp_path: Path) -> None:
    """pytest renames a numbered dir to `.cleanup-*` then deletes it.

    Any left behind lost that race on Windows and own nothing, so they are pure
    residue -- nine were present when this was written.
    """

    orphan = tmp_path / ".cleanup-abc123"
    (orphan / "nested").mkdir(parents=True)

    _prune_pytest_scratch(tmp_path)

    assert not orphan.exists()


def test_pruning_never_raises_on_a_missing_or_hostile_root(tmp_path: Path) -> None:
    """A scratch sweep must never be able to fail an otherwise green run."""

    _prune_pytest_scratch(tmp_path / "does-not-exist")

    a_file = tmp_path / "not-a-directory"
    a_file.write_text("", encoding="utf-8")
    _prune_pytest_scratch(a_file)

    # A user root containing unexpected shapes is ignored rather than fatal.
    odd = tmp_path / "pytest-of-someone"
    (odd / "pytest-not-a-number").mkdir(parents=True)
    (odd / "unrelated").mkdir()
    _prune_pytest_scratch(tmp_path)
    assert (odd / "pytest-not-a-number").exists(), "only numbered directories are managed"
    assert (odd / "unrelated").exists()
