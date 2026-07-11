"""Fail closed when release inputs contain generated files or likely secrets."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


FORBIDDEN_NAMES = {
    ".coverage",
    ".DS_Store",
    ".env",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
}
FORBIDDEN_SUFFIXES = {".db", ".egg-link", ".pyc", ".pyo"}
SECRET_PATTERNS = {
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "private key": re.compile(rb"-----BEGIN (?:DSA |EC |OPENSSH |PGP |RSA )?PRIVATE KEY-----"),
    "provider API key": re.compile(rb"\bsk-[A-Za-z0-9_-]{24,}\b"),
}
ACTION_REFERENCE = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
PINNED_ACTION = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def release_input_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [root / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def generated_path_reason(path: Path, root: Path) -> str | None:
    relative = PurePosixPath(path.relative_to(root).as_posix())
    if any(part in FORBIDDEN_NAMES or part.endswith(".egg-info") for part in relative.parts):
        return "generated directory or file"
    if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "generated/runtime suffix"
    return None


def scan(root: Path) -> list[str]:
    failures: list[str] = []
    for path in release_input_files(root):
        reason = generated_path_reason(path, root)
        if reason:
            failures.append(f"{path.relative_to(root).as_posix()}: {reason}")
            continue
        try:
            payload = path.read_bytes()
        except OSError as exc:
            failures.append(f"{path.relative_to(root).as_posix()}: unreadable ({exc})")
            continue
        if b"\0" in payload[:8192]:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(payload):
                failures.append(f"{path.relative_to(root).as_posix()}: possible {label}")
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".github/workflows/") and path.suffix in {".yaml", ".yml"}:
            text = payload.decode("utf-8", errors="replace")
            if re.search(r"^\s*pull_request_target\s*:", text, re.MULTILINE):
                failures.append(f"{relative}: pull_request_target is not allowed")
            for reference in ACTION_REFERENCE.findall(text):
                if not reference.startswith("./") and not PINNED_ACTION.fullmatch(reference):
                    failures.append(f"{relative}: action is not pinned to a full commit SHA ({reference})")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    failures = scan(root)
    if failures:
        print("Release hygiene check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Release hygiene check passed ({len(release_input_files(root))} release input files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
