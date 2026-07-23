"""Select a deterministic, size-balanced pytest file shard for CI."""

from __future__ import annotations

import argparse
from pathlib import Path


def select_test_files(root: Path, *, shard_index: int, shard_count: int) -> tuple[Path, ...]:
    """Return one stable greedy shard of the repository's pytest files."""

    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be within shard_count")
    files = sorted(
        root.rglob("test_*.py"), key=lambda path: (-path.stat().st_size, path.as_posix())
    )
    if not files:
        raise ValueError(f"no pytest files found under {root}")
    shards: list[list[Path]] = [[] for _ in range(shard_count)]
    weights = [0] * shard_count
    for path in files:
        target = min(range(shard_count), key=lambda index: (weights[index], index))
        shards[target].append(path)
        weights[target] += path.stat().st_size
    return tuple(sorted(shards[shard_index], key=lambda path: path.as_posix()))


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
