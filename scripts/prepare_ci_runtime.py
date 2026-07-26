"""Create a private, cross-platform Python and state boundary for hosted CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import venv
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from agency_runtime.core.private_paths import (
    bootstrap_private_directory,
    ensure_private_directory,
    remove_private_directory,
)
from agency_runtime.core.store.security import (
    metadata_is_link_or_reparse_point,
    storage_parent_is_trusted,
)
from agency_runtime.core.windows_acl import current_process_user_sid
from scripts.ci_private_node import prepare_private_node
from scripts.parallel_change_loop_storage import (
    capture_private_directory_identity,
    create_exact_private_file,
    exact_private_file_is_valid,
    private_runtime_lock,
)

_SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_IS_WINDOWS = os.name == "nt"
_PREPARATION_LOCK_TIMEOUT_SECONDS = 300.0
_MAX_VENV_CONFIGURATION_BYTES = 16 * 1024
_RUNTIME_CONTRACT_RECEIPT = ".agency-ci-runtime-contract-v1"
_RUNTIME_OWNER_RECEIPT = ".agency-ci-runtime-owner-v1"
_RUNTIME_OWNER_PAYLOAD = b"agency-ci-runtime-owner:v1\n"


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


def _configuration_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(getattr(metadata, "st_ino", 0) or 0),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
    )


def _attested_system_site_packages(configuration: Path) -> bool:
    """Read the venv isolation mode through one bounded, no-follow file handle."""

    flags = os.O_RDONLY
    flags |= int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.lstat(configuration)
        descriptor = os.open(configuration, flags)
    except OSError as exc:
        raise RuntimeError("existing CI Python environment configuration is unsafe") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            metadata_is_link_or_reparse_point(before)
            or metadata_is_link_or_reparse_point(opened)
            or not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or int(getattr(before, "st_nlink", 0) or 0) != 1
            or int(getattr(opened, "st_nlink", 0) or 0) != 1
            or not 0 < int(opened.st_size) <= _MAX_VENV_CONFIGURATION_BYTES
            or _configuration_identity(before) != _configuration_identity(opened)
        ):
            raise RuntimeError("existing CI Python environment configuration is unsafe")
        payload = os.read(descriptor, _MAX_VENV_CONFIGURATION_BYTES + 1)
        after_handle = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = os.lstat(configuration)
    except OSError as exc:
        raise RuntimeError("existing CI Python environment configuration changed") from exc
    if (
        len(payload) != int(opened.st_size)
        or _configuration_identity(after_handle) != _configuration_identity(opened)
        or _configuration_identity(after_path) != _configuration_identity(opened)
    ):
        raise RuntimeError("existing CI Python environment configuration changed")
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise RuntimeError("existing CI Python environment configuration is invalid") from exc
    values = [
        value.strip().casefold()
        for line in lines
        if "=" in line
        for name, value in [line.split("=", 1)]
        if name.strip().casefold() == "include-system-site-packages"
    ]
    if len(values) != 1 or values[0] not in {"true", "false"}:
        raise RuntimeError("existing CI Python environment isolation mode is invalid")
    return values[0] == "true"


def _validated_environment_python(
    root: Path,
    environment: Path,
    *,
    system_site_packages: bool,
) -> Path:
    """Return a complete reusable interpreter without mutating unknown contents."""

    configuration = environment / "pyvenv.cfg"
    python = _venv_python(environment)
    if not python.is_file() or python.is_symlink():
        raise RuntimeError("existing CI Python environment is incomplete or unsafe")
    if _attested_system_site_packages(configuration) is not system_site_packages:
        raise RuntimeError("existing CI Python environment has the wrong isolation mode")
    resolved = python.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("CI Python interpreter escaped its private runtime") from exc
    if os.name != "nt":
        python.chmod(0o700)
    return python


@contextmanager
def _runtime_preparation_lock(base: Path, label: str) -> Iterator[None]:
    """Serialize one stable venv/Node publication across local processes."""

    entered = False
    try:
        with private_runtime_lock(
            base / f".{label}.prepare.lock",
            wait_seconds=_PREPARATION_LOCK_TIMEOUT_SECONDS,
            busy_message="CI runtime preparation is busy; retry the operation",
        ):
            entered = True
            yield
    except RuntimeError as exc:
        if entered:
            raise
        raise RuntimeError("CI runtime preparation lock failed") from exc


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


def ci_runtime_root_path(label: str, *, home_dir: Path | None = None) -> Path:
    """Project one stable CI runtime path without creating filesystem state."""

    if not _SAFE_LABEL.fullmatch(label):
        raise ValueError("CI runtime label must be a bounded filesystem-safe identifier")
    home = (home_dir or Path.home()).expanduser().resolve(strict=True)
    return _ci_bootstrap_request(home) / label


def prepare_ci_runtime(
    label: str,
    *,
    home_dir: Path | None = None,
    node_resolver: Callable[[str], str | None] | None = None,
    system_site_packages: bool = True,
    runtime_contract: str | None = None,
) -> dict[str, str]:
    """Build an idempotent private test runtime in a durable user boundary."""

    if not _SAFE_LABEL.fullmatch(label):
        raise ValueError("CI runtime label must be a bounded filesystem-safe identifier")
    if not isinstance(system_site_packages, bool):
        raise TypeError("system_site_packages must be a bool")
    if runtime_contract is not None and not re.fullmatch(r"[a-f0-9]{64}", runtime_contract):
        raise ValueError("runtime_contract must be a SHA-256 hex digest")
    root_path = ci_runtime_root_path(label, home_dir=home_dir)
    base = bootstrap_private_directory(root_path.parent)
    with _runtime_preparation_lock(base, label):
        root_path = base / root_path.name
        contract_payload = (
            None
            if runtime_contract is None
            else f"agency-ci-runtime-contract:v1:{runtime_contract}\n".encode("ascii")
        )
        root_created = False
        if contract_payload is not None:
            try:
                os.lstat(root_path)
            except FileNotFoundError:
                root_created = True
            else:
                identity = capture_private_directory_identity(root_path)
                if not exact_private_file_is_valid(
                    root_path / _RUNTIME_OWNER_RECEIPT,
                    _RUNTIME_OWNER_PAYLOAD,
                ):
                    raise RuntimeError("existing CI runtime is not Agency-owned")
                if not exact_private_file_is_valid(
                    root_path / _RUNTIME_CONTRACT_RECEIPT,
                    contract_payload,
                ):
                    remove_private_directory(identity)
                    root_created = True
        root = _private_directory(root_path)
        if contract_payload is not None and root_created:
            identity = capture_private_directory_identity(root)
            try:
                create_exact_private_file(
                    root / _RUNTIME_OWNER_RECEIPT,
                    _RUNTIME_OWNER_PAYLOAD,
                )
            except BaseException:
                remove_private_directory(identity)
                raise
        isolated_home = _private_directory(root / "home")
        temporary = _private_directory(root / "tmp")
        environment_path = root / "venv"
        environment = _private_directory(environment_path)
        if any(environment.iterdir()):
            python = _validated_environment_python(
                root,
                environment,
                system_site_packages=system_site_packages,
            )
        else:
            venv.EnvBuilder(
                clear=False,
                symlinks=False,
                system_site_packages=system_site_packages,
                with_pip=False,
            ).create(environment)
            python = _venv_python(environment)
            if os.name != "nt" and python.is_symlink():
                python.unlink()
                shutil.copy2(Path(sys.executable).resolve(strict=True), python)
            python = _validated_environment_python(
                root,
                environment,
                system_site_packages=system_site_packages,
            )
        values = {
            "AGENCY_CI_ROOT": root.as_posix(),
            "AGENCY_CI_PYTHON": python.as_posix(),
            "AGENCY_CI_HOME": isolated_home.as_posix(),
            "AGENCY_CI_TEMP": temporary.as_posix(),
        }
        node = prepare_private_node(root, resolver=node_resolver or shutil.which)
        if node is not None:
            values["AGENCY_CI_NODE"] = node.as_posix()
        if contract_payload is not None:
            create_exact_private_file(root / _RUNTIME_CONTRACT_RECEIPT, contract_payload)
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
