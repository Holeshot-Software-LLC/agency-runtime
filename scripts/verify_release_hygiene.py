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
    "agency.yaml",
    "build",
    "dist",
}
FORBIDDEN_SUFFIXES = {".db", ".egg-link", ".pyc", ".pyo", ".sqlite", ".sqlite3"}
SECRET_PATTERNS = {
    "Anthropic API key": re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "Google API key": re.compile(rb"\bAIza[0-9A-Za-z_-]{35}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "npm token": re.compile(rb"\bnpm_[A-Za-z0-9]{36}\b"),
    "private key": re.compile(rb"-----BEGIN (?:DSA |EC |OPENSSH |PGP |RSA )?PRIVATE KEY-----"),
    "provider API key": re.compile(rb"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "Slack token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Stripe live key": re.compile(rb"\bsk_live_[A-Za-z0-9]{20,}\b"),
}
ACTION_REFERENCE = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)
PINNED_ACTION = re.compile(r"^[^@]+@[0-9a-f]{40}$")
PROJECT_VERSION_STAGING = re.compile(
    r"^agency(?:[-_.]+)runtime-\d+\.\d+\.\d+(?:[a-z]+\d+)?$",
    re.IGNORECASE,
)


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
    if relative.parts and PROJECT_VERSION_STAGING.fullmatch(relative.parts[0]):
        return "generated project-version staging directory"
    if any(part in FORBIDDEN_NAMES or part.endswith(".egg-info") for part in relative.parts):
        return "generated directory or file"
    if any(part.startswith(".env.") and part != ".env.example" for part in relative.parts):
        return "environment secret file"
    if relative.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "generated/runtime suffix"
    if relative.name.endswith((".db-shm", ".db-wal", ".sqlite-shm", ".sqlite-wal")):
        return "generated/runtime sidecar"
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
        failures.extend(
            f"{path.relative_to(root).as_posix()}: possible {label}"
            for label, pattern in SECRET_PATTERNS.items()
            if pattern.search(payload)
        )
        relative = path.relative_to(root).as_posix()
        if relative.startswith(".github/workflows/") and path.suffix in {".yaml", ".yml"}:
            text = payload.decode("utf-8", errors="replace")
            if re.search(r"^\s*pull_request_target\s*:", text, re.MULTILINE):
                failures.append(f"{relative}: pull_request_target is not allowed")
            failures.extend(
                f"{relative}: action is not pinned to a full commit SHA ({reference})"
                for reference in ACTION_REFERENCE.findall(text)
                if not reference.startswith("./") and not PINNED_ACTION.fullmatch(reference)
            )
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
