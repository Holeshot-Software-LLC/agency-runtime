"""Trusted, reboot-durable identity for the user configuration file."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import secrets
import stat
from datetime import datetime
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import BoundedFileError, read_bounded_regular_file
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.configuration_contracts import ConfigurationError
from agency_runtime.core.process_argv import (
    PersistentArtifactIdentity,
    agency_bootstrap_path,
    persistent_artifacts_from_manifest,
    revalidate_persistent_artifacts,
)

DASHBOARD_MANIFEST_SCHEMA_VERSION = 2
DASHBOARD_MANIFEST_OWNER = "agency-runtime"
DASHBOARD_MANIFEST_SERVICE = "dashboard"
DASHBOARD_MANIFEST_RELATIVE_PATH = Path(".agency-runtime/services/dashboard-service.json")

_MAX_MANIFEST_BYTES = 64 * 1024
_MAX_PATH_BYTES = 4096
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_MANIFEST_KEYS = frozenset(
    {
        "schema_version",
        "owner",
        "service",
        "platform",
        "manager",
        "registration",
        "worker_argv",
        "launcher_artifacts",
        "config_path",
        "package_version",
        "runtime_fingerprint",
        "installed_at",
    }
)
_SERVICE_IDENTITIES = {
    "linux": ("systemd-user", "agency-runtime-dashboard.service"),
    "windows": ("schtasks", "Agency Runtime Dashboard"),
}


def _platform_name(value: str | None) -> str:
    name = str(value or platform.system()).strip().casefold()
    if name in {"gnu/linux", "linux"}:
        return "linux"
    if name in {"nt", "win32", "windows"}:
        return "windows"
    return name


def _path(value: str | Path, *, label: str) -> Path:
    text = os.fspath(value)
    if not isinstance(text, str):
        raise ValueError(f"{label} must be text")
    encoded = text.encode("utf-8")
    if (
        not text
        or len(encoded) > _MAX_PATH_BYTES
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        raise ValueError(f"{label} is invalid")
    # ``Path.resolve()`` dereferences every existing component.  That is the
    # wrong primitive for a security identity: a caller-supplied symlink would
    # disappear before the bounded reader or atomic writer could reject it.
    # ``abspath`` gives us a stable, normalized absolute spelling without
    # following the final file or any parent directory.
    return Path(os.path.abspath(Path(text).expanduser()))


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse)


def _assert_config_identity_link_safe(path: Path) -> None:
    """Reject links in every existing component of one config identity.

    A missing suffix is valid because first-run configuration files and their
    private runtime directory may not exist yet.  Every component that does
    exist is inspected with ``lstat`` so neither a final file link nor a parent
    directory link/reparse point can be hidden by path canonicalization.
    """

    anchor = Path(path.anchor)
    current = anchor
    components = path.parts[1:]
    candidates = [anchor]
    candidates.extend(
        anchor.joinpath(*components[:index]) for index in range(1, len(components) + 1)
    )
    for index, candidate in enumerate(candidates):
        current = candidate
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise ConfigurationError("configuration path identity could not be validated") from exc
        if _is_link_or_reparse(metadata):
            raise ConfigurationError("refusing configuration path symlink or reparse point")
        if index < len(candidates) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise ConfigurationError("configuration path parent must be a directory")


def _config_identity_path(value: str | Path, *, label: str) -> Path:
    path = _path(value, label=label)
    _assert_config_identity_link_safe(path)
    return path


def _real_manifest_parent(home: Path, manifest_path: Path) -> bool:
    """Reject a service-state directory chain containing links or special files."""

    try:
        relative_parts = manifest_path.parent.relative_to(home).parts
    except ValueError:
        return False
    current = home
    for part in (None, *relative_parts):
        if part is not None:
            current /= part
        metadata = os.lstat(current)
        if _is_link_or_reparse(metadata):
            return False
        if not stat.S_ISDIR(metadata.st_mode):
            return False
    return True


def _manifest_document(home: Path) -> dict[str, Any] | None:
    manifest_path = home / DASHBOARD_MANIFEST_RELATIVE_PATH
    try:
        if not _real_manifest_parent(home, manifest_path):
            return None
        raw = read_bounded_regular_file(
            manifest_path,
            limit=_MAX_MANIFEST_BYTES,
            label="dashboard service ownership manifest",
        )
        value = safe_load_bounded_json(
            raw,
            maximum_bytes=_MAX_MANIFEST_BYTES,
            maximum_depth=8,
            maximum_nodes=128,
        )
    except (BoundedFileError, BoundedJSONError, FileNotFoundError, OSError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def _canonical_absolute_path(value: object) -> Path | None:
    if not isinstance(value, str):
        return None
    try:
        candidate = _config_identity_path(value, label="manifest config path")
    except (OSError, UnicodeError, ValueError):
        return None
    if not Path(value).is_absolute():
        return None
    if os.path.normcase(str(candidate)) != os.path.normcase(value):
        return None
    return candidate


def _valid_worker_binding(worker: object, config_path: str) -> bool:
    if not isinstance(worker, list) or len(worker) != 8:
        return False
    if any(not isinstance(item, str) for item in worker):
        return False
    if worker[1:7] != [
        "-I",
        agency_bootstrap_path(),
        "agency_runtime.cli",
        "dashboard",
        "--service-mode",
        "--config",
    ]:
        return False
    try:
        _path(worker[0], label="manifest worker executable")
    except (OSError, UnicodeError, ValueError):
        return False
    # Preserve virtualenv shims: service argv intentionally stores an absolute
    # launcher path without dereferencing its final symlink.
    return Path(worker[0]).is_absolute() and worker[7] == config_path


def _valid_manifest_integrity(value: dict[str, Any]) -> bool:
    package_version = value.get("package_version")
    fingerprint = value.get("runtime_fingerprint")
    installed_at = value.get("installed_at")
    if (
        not isinstance(package_version, str)
        or not package_version
        or len(package_version) > 128
        or not isinstance(fingerprint, str)
        or _SHA256.fullmatch(fingerprint) is None
        or not isinstance(installed_at, str)
        or len(installed_at) > 128
    ):
        return False
    try:
        installed = datetime.fromisoformat(installed_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if installed.tzinfo is None:
        return False
    payload = json.dumps(
        {
            "package_version": package_version,
            "python_executable": value["worker_argv"][0],
            "worker_argv": value["worker_argv"],
            "launcher_artifacts": value["launcher_artifacts"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected = f"sha256:{hashlib.sha256(payload).hexdigest()}"
    return secrets.compare_digest(fingerprint, expected)


def _valid_launcher_binding(value: object, worker: object) -> bool:
    """Validate the exact persistent interpreter/bootstrap identity pair."""

    if not isinstance(value, list) or not isinstance(worker, list) or len(worker) < 3:
        return False
    fields = set(PersistentArtifactIdentity.__dataclass_fields__)
    if any(not isinstance(item, dict) or set(item) != fields for item in value):
        return False
    try:
        artifacts = persistent_artifacts_from_manifest(value)
    except (TypeError, ValueError):
        return False
    if len(artifacts) != 2 or [item.lexical_path for item in artifacts] != [
        worker[0],
        worker[2],
    ]:
        return False
    try:
        # The manifest was content-hashed at installation. Recheck its exact
        # namespace, metadata, link target, and mutation authority before it is
        # allowed to redirect the process-wide configuration identity.
        revalidate_persistent_artifacts(artifacts)
    except (OSError, PermissionError, ValueError):
        return False
    return True


def trusted_dashboard_config_path(
    home_dir: str | Path,
    *,
    platform_name: str | None = None,
) -> Path | None:
    """Return the config path from one exact owned service manifest, if valid."""

    try:
        home = _path(home_dir, label="home directory")
    except (OSError, UnicodeError, ValueError):
        return None
    value = _manifest_document(home)
    if value is None or set(value) != _MANIFEST_KEYS:
        return None
    schema = value.get("schema_version")
    target_platform = _platform_name(platform_name)
    service_identity = _SERVICE_IDENTITIES.get(target_platform)
    if (
        type(schema) is not int
        or schema != DASHBOARD_MANIFEST_SCHEMA_VERSION
        or value.get("owner") != DASHBOARD_MANIFEST_OWNER
        or value.get("service") != DASHBOARD_MANIFEST_SERVICE
        or value.get("platform") != target_platform
        or service_identity is None
        or (value.get("manager"), value.get("registration")) != service_identity
    ):
        return None
    raw_config_path = value.get("config_path")
    config_path = _canonical_absolute_path(raw_config_path)
    if config_path is None or not _valid_worker_binding(
        value.get("worker_argv"), str(raw_config_path)
    ):
        return None
    if not _valid_launcher_binding(value.get("launcher_artifacts"), value.get("worker_argv")):
        return None
    if not _valid_manifest_integrity(value):
        return None
    return config_path


def resolve_config_identity_path(
    path: str | Path | None = None,
    *,
    home_dir: str | Path | None = None,
    use_environment: bool = True,
    platform_name: str | None = None,
) -> Path:
    """Resolve explicit, environment, installed, then conventional config identity."""

    if path is not None:
        return _config_identity_path(path, label="config path")
    if use_environment:
        configured = os.environ.get("AGENCY_CONFIG_PATH", "").strip()
        if configured:
            return _config_identity_path(configured, label="config path")
    home = _path(home_dir if home_dir is not None else Path.home(), label="home directory")
    installed = trusted_dashboard_config_path(home, platform_name=platform_name)
    if installed is not None:
        return installed
    return _config_identity_path(home / ".agency-runtime" / "agency.yaml", label="config path")


__all__ = [
    "DASHBOARD_MANIFEST_OWNER",
    "DASHBOARD_MANIFEST_RELATIVE_PATH",
    "DASHBOARD_MANIFEST_SCHEMA_VERSION",
    "DASHBOARD_MANIFEST_SERVICE",
    "resolve_config_identity_path",
    "trusted_dashboard_config_path",
]
