"""Select a deterministic, size-balanced pytest file shard for CI."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path


def discover_test_files(root: Path) -> tuple[Path, ...]:
    """Return the canonical lexical pytest-file inventory below *root*."""

    files = tuple(sorted(root.rglob("test_*.py"), key=lambda path: path.as_posix()))
    if not files:
        raise ValueError(f"no pytest files found under {root}")
    return files


def partition_test_files(
    files: Sequence[Path],
    *,
    shard_count: int,
    weights: Mapping[Path, int] | None = None,
) -> tuple[tuple[Path, ...], ...]:
    """Return deterministic longest-processing-time file partitions."""

    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    if not files:
        raise ValueError("pytest file inventory must not be empty")
    unique = set(files)
    if len(unique) != len(files):
        raise ValueError("pytest file inventory contains duplicates")
    if shard_count > len(files):
        raise ValueError("shard_count cannot exceed the pytest file count")
    if weights is None:
        normalized_weights = {path: max(1, path.stat().st_size) for path in files}
    else:
        if set(weights) != unique:
            raise ValueError("pytest file weights must match the exact file inventory")
        normalized_weights = {}
        for path in files:
            weight = weights[path]
            if isinstance(weight, bool) or not isinstance(weight, int) or weight < 1:
                raise ValueError("pytest file weights must be positive integers")
            normalized_weights[path] = weight
    ordered = sorted(
        files,
        key=lambda path: (-normalized_weights[path], path.as_posix()),
    )
    shards: list[list[Path]] = [[] for _ in range(shard_count)]
    loads = [0] * shard_count
    for path in ordered:
        target = min(range(shard_count), key=lambda index: (loads[index], index))
        shards[target].append(path)
        loads[target] += normalized_weights[path]
    return tuple(tuple(sorted(shard, key=lambda path: path.as_posix())) for shard in shards)


def select_test_files(root: Path, *, shard_index: int, shard_count: int) -> tuple[Path, ...]:
    """Return one stable source-byte-weighted pytest file shard."""

    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be within shard_count")
    return partition_test_files(
        discover_test_files(root),
        shard_count=shard_count,
    )[shard_index]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("tests"))
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args(argv)
    for path in select_test_files(args.root, shard_index=args.index, shard_count=args.count):
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
