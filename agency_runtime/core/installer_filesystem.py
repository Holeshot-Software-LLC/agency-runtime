"""Transactional and ownership-aware installer filesystem operations."""

from __future__ import annotations

import json
import os
import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.installer_contracts import (
    INSTALL_MANIFEST,
    PLUGIN_ID,
    PLUGIN_VERSION,
)
from agency_runtime.core.private_paths import (
    allocate_private_directory,
    ensure_private_directory,
    remove_private_directory,
)
from agency_runtime.core.process_argv import PersistentArtifactIdentity

_MAX_INSTALL_MANIFEST_BYTES = 64 * 1024


def _facade():
    """Resolve facade dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import installer

    return installer


def _safe_relative(*args: Any, **kwargs: Any) -> Path:
    return _facade()._safe_relative(*args, **kwargs)


def _bundle_digest(*args: Any, **kwargs: Any) -> str:
    return _facade()._bundle_digest(*args, **kwargs)


def _managed_bundle_matches(*args: Any, **kwargs: Any) -> bool:
    return _facade()._managed_bundle_matches(*args, **kwargs)


def _runtime_home(*args: Any, **kwargs: Any) -> Path:
    return _facade()._runtime_home(*args, **kwargs)


def _utc_stamp(*args: Any, **kwargs: Any) -> str:
    return _facade()._utc_stamp(*args, **kwargs)


def safe_relative(path: str) -> Path:
    candidate = Path(path)
    if candidate.anchor or ".." in candidate.parts:
        raise ValueError(f"unsafe generated file path: {path}")
    return candidate


def atomic_install_tree(
    target: Path,
    files: Mapping[str, str],
    *,
    host: str,
    dry_run: bool,
    home_dir: str | Path | None,
    launcher_artifacts: Sequence[PersistentArtifactIdentity] = (),
) -> dict[str, Any]:
    owned_files = sorted(files)
    backup_path: Path | None = None
    unchanged = target.exists() and _managed_bundle_matches(target, host, files)
    plan = {
        "target": str(target),
        "owned_files": [*owned_files, INSTALL_MANIFEST],
        "bundle_digest": _bundle_digest(files),
        "unchanged": unchanged,
        "would_backup": target.exists() and not unchanged,
    }
    if dry_run or unchanged:
        return plan

    install_parent = ensure_private_directory(target.parent, product_owned=False)
    stage_identity = allocate_private_directory(
        install_parent,
        prefix=f".{target.name}.staging",
    )
    stage = stage_identity.path
    stamp = _utc_stamp()
    try:
        for relative, content in files.items():
            destination = stage / _safe_relative(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")

        if target.exists():
            backup_path = _runtime_home(home_dir=home_dir) / "backups" / host / stamp
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup_path)

        manifest = {
            "schema_version": 2,
            "owner": "agency-runtime",
            "host": host,
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "install_id": str(uuid.uuid4()),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "target": str(target),
            "owned_files": owned_files,
            "backup_path": str(backup_path) if backup_path else None,
            "launcher_artifacts": [item.manifest() for item in launcher_artifacts],
        }
        (stage / INSTALL_MANIFEST).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(stage, target)
    except Exception:
        if backup_path is not None and backup_path.exists() and not target.exists():
            os.replace(backup_path, target)
        if stage.exists():
            remove_private_directory(stage_identity)
        raise

    return {**plan, "backup_path": str(backup_path) if backup_path else None}


def validate_owned_backup(
    path: Path,
    *,
    host: str,
    target: Path,
) -> tuple[bool, str | None, str | None]:
    """Validate that ``path`` is an Agency Runtime bundle for this target."""
    if not path.is_dir():
        return False, "Backup source is not a directory", None
    manifest_path = path / INSTALL_MANIFEST
    try:
        manifest = safe_load_bounded_json(
            read_bounded_regular_file(
                manifest_path,
                limit=_MAX_INSTALL_MANIFEST_BYTES,
                label="backup ownership manifest",
            )
        )
    except FileNotFoundError:
        return (
            False,
            "Backup does not contain an Agency Runtime ownership manifest",
            None,
        )
    except (BoundedJSONError, OSError, UnicodeError, json.JSONDecodeError):
        return False, "Backup ownership manifest is unreadable or invalid", None
    if not isinstance(manifest, dict):
        return False, "Backup ownership manifest must be a JSON object", None

    expected = {
        "owner": "agency-runtime",
        "host": host,
        "plugin_id": PLUGIN_ID,
    }
    if manifest.get("schema_version") not in {1, 2}:
        return False, "Backup ownership manifest has an unexpected schema_version", None
    for field, value in expected.items():
        if manifest.get(field) != value:
            return False, f"Backup ownership manifest has an unexpected {field}", None

    plugin_version = manifest.get("plugin_version")
    if not isinstance(plugin_version, str) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?",
        plugin_version,
    ):
        return False, "Backup ownership manifest has an invalid plugin_version", None

    manifest_target = manifest.get("target")
    if not isinstance(manifest_target, str) or not manifest_target.strip():
        return False, "Backup ownership manifest has no target", None
    try:
        recorded_target = Path(manifest_target).expanduser().resolve()
    except (OSError, RuntimeError):
        return False, "Backup ownership manifest target is invalid", None
    if recorded_target != target.resolve():
        return False, "Backup ownership manifest target does not match this host", None

    owned_files = manifest.get("owned_files")
    if not isinstance(owned_files, list) or not all(isinstance(item, str) for item in owned_files):
        return False, "Backup ownership manifest has an invalid owned_files list", None
    return True, None, plugin_version
