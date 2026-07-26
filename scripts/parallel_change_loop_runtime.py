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

from agency_runtime.core.process_environment import least_privilege_subprocess_environment
from scripts.ci_private_node import resolved_node_source_manifest

RUNTIME_CONTRACT_VERSION = 1
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


def _dependency_paths(repo_root: Path) -> tuple[Path, ...]:
    roots: list[Path] = [repo_root]
    for name in ("purelib", "platlib"):
        value = sysconfig.get_path(name)
        if value:
            candidate = _real_directory(Path(value), label=f"invoking Python {name}")
            if candidate not in roots:
                roots.append(candidate)
    if not any(
        (root / "pytest" / "__init__.py").is_file() and not (root / "pytest").is_symlink()
        for root in roots[1:]
    ):
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
    dependencies = _dependency_paths(repo_root)
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
    "RuntimeContract",
    "build_runtime_contract",
    "private_child_environment",
    "runtime_path",
]
