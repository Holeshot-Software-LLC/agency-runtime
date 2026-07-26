"""Stable runtime identity and child-environment contracts for the local test loop."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import sysconfig
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.process_environment import least_privilege_subprocess_environment
from scripts.ci_private_node import resolved_node_source_manifest
from scripts.parallel_change_loop_storage import exact_private_file_is_valid

RUNTIME_CONTRACT_VERSION = 2
RUNTIME_RECEIPT_NAME = ".agency-local-change-loop-runtime-v2"
RUNTIME_RECEIPT_SCHEMA = "agency.local-change-loop-runtime.v2"
_RUNTIME_RECEIPT_MAX_BYTES = 16 * 1024
_CI_RUNTIME_CONTRACT_RECEIPT = ".agency-ci-runtime-contract-v1"
_CI_RUNTIME_OWNER_RECEIPT = ".agency-ci-runtime-owner-v1"
_CI_RUNTIME_OWNER_PAYLOAD = b"agency-ci-runtime-owner:v1\n"
_SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


@dataclass(frozen=True, slots=True)
class RuntimeContract:
    dependency_paths: tuple[Path, ...]
    key: str
    label: str
    node_resolver: Callable[[str], str | None]
    node_source: Mapping[str, int | str] | None

    def assert_node_unchanged(self) -> None:
        if resolved_node_source_manifest(resolver=self.node_resolver) != self.node_source:
            raise RuntimeError("CI Node source changed while the parallel plan was built")


def _real_directory(path: Path, *, label: str) -> Path:
    raw = path.expanduser()
    if raw.is_symlink():
        raise RuntimeError(f"{label} must not be a symlink")
    try:
        resolved = raw.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"{label} must exist") from exc
    if not resolved.is_dir() or os.pathsep in str(resolved):
        raise RuntimeError(f"{label} must be an unambiguous real directory")
    return resolved


def _same_path(left: Path, right: Path) -> bool:
    left_value = str(left.resolve(strict=True))
    right_value = str(right.resolve(strict=True))
    if os.name == "nt":
        return os.path.normcase(left_value) == os.path.normcase(right_value)
    return left_value == right_value


def _contains_real_pytest(root: Path) -> bool:
    package = root / "pytest"
    package_init = package / "__init__.py"
    return bool(
        package.is_dir()
        and not package.is_symlink()
        and package_init.is_file()
        and not package_init.is_symlink()
    )


def _managed_runtime_root(environment: Mapping[str, str]) -> Path | None:
    root_value = environment.get("AGENCY_CI_ROOT")
    python_value = environment.get("AGENCY_CI_PYTHON")
    if root_value is None and python_value is None:
        return None
    if not root_value or not python_value:
        raise RuntimeError("managed CI runtime identity is incomplete")
    root = _real_directory(Path(root_value), label="managed CI runtime root")
    python = Path(python_value).expanduser()
    if python.is_symlink():
        raise RuntimeError("managed CI runtime Python must not be a symlink")
    try:
        python = python.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("managed CI runtime Python must exist") from exc
    if (
        not python.is_file()
        or os.pathsep in str(python)
        or not _same_path(python, Path(sys.executable))
    ):
        raise RuntimeError("managed CI runtime Python does not match the current interpreter")
    try:
        python.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("managed CI runtime Python escaped its runtime root") from exc
    return root


def _managed_runtime_receipt(root: Path) -> dict[str, object]:
    try:
        raw = read_bounded_regular_file(
            root / RUNTIME_RECEIPT_NAME,
            limit=_RUNTIME_RECEIPT_MAX_BYTES,
            label="parallel runtime receipt",
        )
        payload = safe_load_bounded_json(
            raw,
            maximum_bytes=_RUNTIME_RECEIPT_MAX_BYTES,
            maximum_depth=4,
            maximum_nodes=32,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError("managed CI runtime receipt is unavailable or invalid") from exc
    if not exact_private_file_is_valid(root / RUNTIME_RECEIPT_NAME, raw):
        raise RuntimeError("managed CI runtime receipt is not owner-trusted")
    if not isinstance(payload, dict) or set(payload) != {
        "dependency_paths",
        "runtime_key",
        "schema",
    }:
        raise RuntimeError("managed CI runtime receipt has an invalid shape")
    return payload


def _managed_dependency_paths(environment: Mapping[str, str]) -> tuple[Path, ...]:
    root = _managed_runtime_root(environment)
    if root is None:
        return ()
    payload = _managed_runtime_receipt(root)
    runtime_key = payload.get("runtime_key")
    if (
        payload.get("schema") != RUNTIME_RECEIPT_SCHEMA
        or not isinstance(runtime_key, str)
        or not re.fullmatch(r"[a-f0-9]{64}", runtime_key)
    ):
        raise RuntimeError("managed CI runtime receipt identity is invalid")
    if not exact_private_file_is_valid(
        root / _CI_RUNTIME_OWNER_RECEIPT,
        _CI_RUNTIME_OWNER_PAYLOAD,
    ) or not exact_private_file_is_valid(
        root / _CI_RUNTIME_CONTRACT_RECEIPT,
        f"agency-ci-runtime-contract:v1:{runtime_key}\n".encode("ascii"),
    ):
        raise RuntimeError("managed CI runtime ownership receipts are invalid")
    dependency_values = payload.get("dependency_paths")
    if (
        not isinstance(dependency_values, list)
        or not 1 <= len(dependency_values) <= 8
        or any(not isinstance(value, str) or not value for value in dependency_values)
    ):
        raise RuntimeError("managed CI runtime dependency paths are invalid")
    dependencies: list[Path] = []
    for index, value in enumerate(dependency_values):
        dependency = _real_directory(
            Path(value),
            label=f"managed CI runtime dependency {index}",
        )
        if dependency not in dependencies:
            dependencies.append(dependency)
    if not any(_contains_real_pytest(root_path) for root_path in dependencies):
        raise RuntimeError("managed CI runtime receipt does not provide pytest")
    return tuple(dependencies)


def _dependency_paths(
    repo_root: Path,
    environment: Mapping[str, str] | None = None,
) -> tuple[Path, ...]:
    roots: list[Path] = [repo_root]
    for name in ("purelib", "platlib"):
        value = sysconfig.get_path(name)
        if value:
            candidate = _real_directory(Path(value), label=f"invoking Python {name}")
            if candidate not in roots:
                roots.append(candidate)
    if not any(_contains_real_pytest(root) for root in roots[1:]):
        # A change-loop child uses a private venv plus explicit dependency roots,
        # so sysconfig points at the intentionally empty private site-packages.
        # Pytest is already loaded by that child; recover only its verified package
        # root instead of trusting an ambient PYTHONPATH value.
        loaded_pytest = sys.modules.get("pytest")
        loaded_path = getattr(loaded_pytest, "__file__", None)
        if loaded_path:
            package_init = Path(loaded_path).expanduser()
            package_directory = package_init.parent
            if (
                package_init.name != "__init__.py"
                or package_init.is_symlink()
                or not package_init.is_file()
                or package_directory.name != "pytest"
                or package_directory.is_symlink()
            ):
                raise RuntimeError("the loaded pytest package path is not a real package")
            candidate = _real_directory(
                package_directory.parent,
                label="loaded pytest dependency root",
            )
            if candidate not in roots:
                roots.append(candidate)
    if not any(_contains_real_pytest(root) for root in roots[1:]):
        for candidate in _managed_dependency_paths(
            os.environ if environment is None else environment
        ):
            if candidate not in roots:
                roots.append(candidate)
    if not any(_contains_real_pytest(root) for root in roots[1:]):
        raise RuntimeError("the invoking Python environment does not provide a real pytest package")
    return tuple(roots)


def _fingerprint_path(path: Path) -> str:
    value = str(path.resolve(strict=True))
    return os.path.normcase(value) if os.name == "nt" else value


def build_runtime_contract(
    repo_root: Path,
    label: str,
    environment: Mapping[str, str],
) -> RuntimeContract:
    if not _SAFE_LABEL.fullmatch(label):
        raise ValueError("label must be a bounded filesystem-safe identifier")
    dependencies = _dependency_paths(repo_root, environment)
    search_path = environment.get("PATH", "")

    def node_resolver(name: str) -> str | None:
        return shutil.which(name, path=search_path)

    node_source = resolved_node_source_manifest(resolver=node_resolver)
    interpreter = Path(sys.executable).resolve(strict=True)
    metadata = interpreter.stat()
    payload = {
        "dependencies": [_fingerprint_path(path) for path in dependencies],
        "interpreter": {
            "device": int(metadata.st_dev),
            "inode": int(getattr(metadata, "st_ino", 0) or 0),
            "modified_ns": int(metadata.st_mtime_ns),
            "path": _fingerprint_path(interpreter),
            "size": int(metadata.st_size),
            "version": list(sys.version_info[:3]),
        },
        "label": label,
        "node_source": None if node_source is None else dict(node_source),
        "repo": _fingerprint_path(repo_root),
        "runtime_contract": {
            "plugin_autoload": False,
            "system_site_packages": False,
            "version": RUNTIME_CONTRACT_VERSION,
        },
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    key = hashlib.sha256(encoded.encode()).hexdigest()
    digest = hashlib.sha256(
        f"{_fingerprint_path(repo_root)}\0{label}\0{RUNTIME_CONTRACT_VERSION}".encode()
    ).hexdigest()[:16]
    suffix = f"-{digest}"
    return RuntimeContract(
        dependency_paths=dependencies,
        key=key,
        label=f"{label[: 80 - len(suffix)]}{suffix}",
        node_resolver=node_resolver,
        node_source=node_source,
    )


def runtime_receipt_payload(contract: RuntimeContract) -> bytes:
    return (
        json.dumps(
            {
                "dependency_paths": [str(path) for path in contract.dependency_paths],
                "runtime_key": contract.key,
                "schema": RUNTIME_RECEIPT_SCHEMA,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        + b"\n"
    )


def runtime_path(runtime: Mapping[str, str], name: str) -> Path:
    try:
        raw = Path(runtime[name]).expanduser()
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"CI runtime did not provide {name}") from exc
    if raw.is_symlink():
        raise RuntimeError(f"CI runtime {name} must not be a symlink")
    try:
        return raw.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"CI runtime {name} must exist") from exc


def private_child_environment(
    ambient: Mapping[str, str],
    runtime: Mapping[str, str],
    *,
    runtime_root: Path,
    python: Path,
    private_home: Path,
    private_temp: Path,
    dependency_paths: tuple[Path, ...],
    repo_root: Path,
) -> dict[str, str]:
    extras = {
        "AGENCY_CI_ROOT": str(runtime_root),
        "AGENCY_CI_PYTHON": str(python),
        "AGENCY_CI_HOME": str(private_home),
        "AGENCY_CI_TEMP": str(private_temp),
        "HOME": str(private_home),
        "USERPROFILE": str(private_home),
        "TMP": str(private_temp),
        "TEMP": str(private_temp),
        "TMPDIR": str(private_temp),
        "PYTHONPATH": os.pathsep.join(str(path) for path in dependency_paths),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "VIRTUAL_ENV": str(python.parent.parent),
    }
    node_value = runtime.get("AGENCY_CI_NODE")
    if node_value is not None:
        node = Path(node_value).expanduser()
        if node.is_symlink() or not node.is_file():
            raise RuntimeError("CI runtime AGENCY_CI_NODE must be a real file")
        extras["AGENCY_CI_NODE"] = str(node.resolve(strict=True))
    safe = least_privilege_subprocess_environment(
        "pytest",
        environ=ambient,
        home_dir=private_home,
        extra_env=extras,
        current_directory=repo_root,
        forbidden_roots=(repo_root,),
    )
    allowed = {
        "COMSPEC",
        "CURL_CA_BUNDLE",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "NODE_EXTRA_CA_CERTS",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "WINDIR",
    }
    return {name: value for name, value in safe.items() if name in allowed or name in extras}


__all__ = [
    "RUNTIME_CONTRACT_VERSION",
    "RUNTIME_RECEIPT_NAME",
    "RUNTIME_RECEIPT_SCHEMA",
    "RuntimeContract",
    "build_runtime_contract",
    "private_child_environment",
    "runtime_path",
    "runtime_receipt_payload",
]
