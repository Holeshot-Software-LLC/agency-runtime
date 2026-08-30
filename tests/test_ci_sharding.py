from __future__ import annotations

from pathlib import Path

import pytest

from scripts.select_test_shard import (
    discover_test_files,
    main,
    partition_test_files,
    select_test_files,
)


def test_test_file_shards_are_deterministic_complete_and_disjoint(tmp_path: Path) -> None:
    root = tmp_path / "tests"
    root.mkdir()
    for index, size in enumerate((100, 80, 60, 40, 20)):
        (root / f"test_{index}.py").write_text("x" * size, encoding="utf-8")
    first = select_test_files(root, shard_index=0, shard_count=3)
    shards = [set(select_test_files(root, shard_index=index, shard_count=3)) for index in range(3)]
    assert first == select_test_files(root, shard_index=0, shard_count=3)
    assert set().union(*shards) == set(root.glob("test_*.py"))
    assert not (shards[0] & shards[1] or shards[0] & shards[2] or shards[1] & shards[2])


@pytest.mark.parametrize(
    ("index", "count", "message"),
    [(0, 0, "positive"), (-1, 2, "within"), (2, 2, "within")],
)
def test_test_file_shards_reject_invalid_coordinates(tmp_path, index, count, message) -> None:
    with pytest.raises(ValueError, match=message):
        select_test_files(tmp_path, shard_index=index, shard_count=count)


def test_test_file_shards_reject_empty_roots_and_print_cli_paths(tmp_path, capsys) -> None:
    with pytest.raises(ValueError, match="no pytest files"):
        select_test_files(tmp_path, shard_index=0, shard_count=1)
    root = tmp_path / "tests"
    root.mkdir()
    target = root / "test_one.py"
    target.write_text("pass\n", encoding="utf-8")
    assert main(["--root", str(root), "--index", "0", "--count", "1"]) == 0
    assert capsys.readouterr().out.strip().replace("\\", "/") == target.as_posix()


def test_lpt_partitions_resolve_ties_and_cover_every_supported_shard_count(
    tmp_path: Path,
) -> None:
    root = tmp_path / "tests"
    root.mkdir()
    for name in ("a", "b", "c", "d"):
        (root / f"test_{name}.py").write_text("pass\n", encoding="utf-8")
    files = discover_test_files(root)
    weights = dict.fromkeys(files, 10)

    assert partition_test_files(files, shard_count=2, weights=weights) == (
        (files[0], files[2]),
        (files[1], files[3]),
    )
    for shard_count in range(1, len(files) + 1):
        shards = partition_test_files(files, shard_count=shard_count, weights=weights)
        flattened = tuple(path for shard in shards for path in shard)
        assert len(flattened) == len(set(flattened))
        assert set(flattened) == set(files)


def test_repository_shard_union_is_exact_and_disjoint() -> None:
    root = Path(__file__).resolve().parent
    shards = [select_test_files(root, shard_index=index, shard_count=4) for index in range(4)]
    flattened = [path for shard in shards for path in shard]

    assert len(flattened) == len(set(flattened))
    assert set(flattened) == set(root.rglob("test_*.py"))
