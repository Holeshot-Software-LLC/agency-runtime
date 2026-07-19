"""Read the canonical release version without importing checkout code."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path

VERSION_PATTERN = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:(?:a|b|rc)(?:0|[1-9]\d*))?"
)


def read_release_version(path: Path) -> str:
    """Return the one normalized literal version assignment."""

    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    values: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == "__version__"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            values.append(node.value.value)
    if len(values) != 1 or VERSION_PATTERN.fullmatch(values[0]) is None:
        raise ValueError("package must define one canonical literal __version__")
    return values[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_init", type=Path)
    args = parser.parse_args()
    print(read_release_version(args.package_init))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
