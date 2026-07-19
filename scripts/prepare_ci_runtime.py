"""Create a private, cross-platform Python and state boundary for hosted CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import venv
from collections.abc import Callable
from pathlib import Path

from agency_runtime.core.private_paths import (
    bootstrap_private_directory,
    ensure_private_directory,
)
from agency_runtime.core.store.security import storage_parent_is_trusted
from agency_runtime.core.windows_acl import current_process_user_sid
from scripts.ci_private_node import prepare_private_node

_SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_IS_WINDOWS = os.name == "nt"


def _private_directory(path: Path) -> Path:
    """Create or validate one real current-user CI directory."""

    try:
        return ensure_private_directory(path)
    except (OSError, PermissionError) as exc:
        raise RuntimeError(f"CI runtime path must be private: {path}") from exc


def _venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _validated_environment_python(root: Path, environment: Path) -> Path:
    """Return a complete reusable interpreter without mutating unknown contents."""

    configuration = environment / "pyvenv.cfg"
    python = _venv_python(environment)
    if (
        not configuration.is_file()
        or configuration.is_symlink()
        or not python.is_file()
        or python.is_symlink()
    ):
        raise RuntimeError("existing CI Python environment is incomplete or unsafe")
    resolved = python.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("CI Python interpreter escaped its private runtime") from exc
    if os.name != "nt":
        python.chmod(0o700)
    return python


def _ci_bootstrap_request(home: Path, *, is_windows: bool | None = None) -> Path:
    """Choose a CI root whose full path remains trustworthy to child processes."""

    windows = _IS_WINDOWS if is_windows is None else is_windows
    requested = home / ".agency-runtime-ci"
    if not windows:
        return requested
    parent = home
    while not storage_parent_is_trusted(parent, is_windows=True, final_parent=False):
        if parent == parent.parent:
            raise RuntimeError("CI runtime has no trusted Windows creation boundary")
        parent = parent.parent
    if parent == home:
        return requested
    sid = current_process_user_sid(is_windows=True)
    if not sid:
        raise RuntimeError("CI runtime cannot identify the current Windows user")
    digest = hashlib.sha256(
        f"{sid}\0{requested.as_posix().casefold()}".encode(
            "utf-8",
            errors="surrogatepass",
        )
    ).hexdigest()[:32]
    return parent / f".agency-runtime-ci-{digest}"


def prepare_ci_runtime(
    label: str,
    *,
    home_dir: Path | None = None,
    node_resolver: Callable[[str], str | None] | None = None,
) -> dict[str, str]:
    """Build an idempotent private test runtime in a durable user boundary."""

    if not _SAFE_LABEL.fullmatch(label):
        raise ValueError("CI runtime label must be a bounded filesystem-safe identifier")
    home = (home_dir or Path.home()).expanduser().resolve(strict=True)
    base = bootstrap_private_directory(_ci_bootstrap_request(home))
    root = _private_directory(base / label)
    isolated_home = _private_directory(root / "home")
    temporary = _private_directory(root / "tmp")
    environment_path = root / "venv"
    environment = _private_directory(environment_path)
    if any(environment.iterdir()):
        python = _validated_environment_python(root, environment)
    else:
        venv.EnvBuilder(
            clear=False,
            symlinks=False,
            system_site_packages=True,
            with_pip=False,
        ).create(environment)
        python = _venv_python(environment)
        if os.name != "nt" and python.is_symlink():
            python.unlink()
            shutil.copy2(Path(sys.executable).resolve(strict=True), python)
        python = _validated_environment_python(root, environment)
    values = {
        "AGENCY_CI_ROOT": root.as_posix(),
        "AGENCY_CI_PYTHON": python.as_posix(),
        "AGENCY_CI_HOME": isolated_home.as_posix(),
        "AGENCY_CI_TEMP": temporary.as_posix(),
    }
    node = prepare_private_node(root, resolver=node_resolver or shutil.which)
    if node is not None:
        values["AGENCY_CI_NODE"] = node.as_posix()
    return values


def _write_github_environment(path: Path, values: dict[str, str]) -> None:
    if path.is_symlink():
        raise RuntimeError("GitHub environment file must not be a symlink")
    if any("\n" in value or "\r" in value for value in values.values()):
        raise RuntimeError("CI runtime paths must not contain line breaks")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for name, value in values.items():
            handle.write(f"{name}={value}\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--github-env",
        type=Path,
        default=Path(os.environ["GITHUB_ENV"]) if os.environ.get("GITHUB_ENV") else None,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    values = prepare_ci_runtime(args.label)
    if args.github_env is not None:
        _write_github_environment(args.github_env, values)
    print(json.dumps(values, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
