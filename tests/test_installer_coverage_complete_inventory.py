from __future__ import annotations

import json
import os
import platform
import sqlite3
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import installer as installer_facade
from agency_runtime.core import installer_inventory as inventory
from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
    INSTALL_MANIFEST,
    PLUGIN_ID,
    PLUGIN_VERSION,
    NativeCommandResult,
)


def _manifest(**overrides: Any) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "install_id": "install-identity",
        "owned_files": ["payload.txt"],
    }
    manifest.update(overrides)
    return manifest


def _write_bundle(target: Path, *, manifest: Any | None = None) -> dict[str, str]:
    target.mkdir(parents=True, exist_ok=True)
    files = {"payload.txt": "managed payload\n"}
    (target / "payload.txt").write_text(
        files["payload.txt"],
        encoding="utf-8",
        newline="\n",
    )
    payload = _manifest() if manifest is None else manifest
    (target / INSTALL_MANIFEST).write_text(json.dumps(payload), encoding="utf-8")
    return files


def test_reconstructed_stat_result_without_windows_attributes_is_regular() -> None:
    metadata = os.stat_result((stat.S_IFREG | 0o600, 0, 0, 1, 0, 0, 0, 0, 0, 0))

    assert inventory._is_link_or_reparse(metadata) is False


def test_canary_read_and_invalidation_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "agency.db"
    database.write_bytes(b"not-a-database")
    monkeypatch.setattr(installer_facade, "_default_db_path", lambda: database)

    def fail_connect(*_args: Any, **_kwargs: Any) -> None:
        raise sqlite3.OperationalError("injected read failure")

    monkeypatch.setattr(inventory.sqlite3, "connect", fail_connect)
    assert inventory._read_canary_attestation("codex") is None

    class BrokenStore:
        def __init__(self, _path: Path) -> None:
            pass

        def clear_host_canary_attestation(self, _host: str) -> bool:
            raise RuntimeError("injected invalidation failure")

    monkeypatch.setattr(installer_facade, "Store", BrokenStore)
    assert inventory._invalidate_canary_attestation("codex", home_dir=None) is False


def test_canary_read_handles_missing_database_and_missing_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "agency.db"
    monkeypatch.setattr(installer_facade, "_default_db_path", lambda: database)
    assert inventory._read_canary_attestation("codex") is None

    connection = sqlite3.connect(database)
    connection.close()
    assert inventory._read_canary_attestation("codex") is None


def test_parent_and_file_fingerprints_detect_tampering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_bytes(b"a")

    real_lstat = inventory.os.lstat
    monkeypatch.setattr(
        inventory.os,
        "lstat",
        lambda path: (
            SimpleNamespace(st_mode=stat.S_IFREG) if Path(path) == root else real_lstat(path)
        ),
    )
    with pytest.raises(OSError, match="unsafe managed bundle directory"):
        inventory._checked_parent_directories(root, payload)

    monkeypatch.setattr(inventory.os, "lstat", real_lstat)
    metadata = real_lstat(root)
    fingerprint = list(inventory._stat_fingerprint(metadata))
    fingerprint[2] += 1
    with pytest.raises(OSError, match="directory changed while reading"):
        inventory._verify_parent_directories([(root, tuple(fingerprint))])

    with pytest.raises(OSError, match="byte limit exceeded"):
        inventory._read_regular_file_bounded(payload, root=root, limit=-1)

    def mutate_during_read(_path: Path, *, limit: int) -> bytes:
        assert limit == 1
        payload.write_bytes(b"bb")
        return b"a"

    monkeypatch.setattr(inventory, "read_bounded_regular_file", mutate_during_read)
    with pytest.raises(OSError, match="file changed while reading"):
        inventory._read_regular_file_bounded(payload, root=root, limit=1)

    payload.write_bytes(b"a")
    monkeypatch.setattr(
        inventory,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: b"too long",
    )
    with pytest.raises(OSError, match="file exceeds byte limit"):
        inventory._read_regular_file_bounded(payload, root=root, limit=1)


@pytest.mark.parametrize(
    "manifest",
    [
        [],
        _manifest(owner="other"),
        _manifest(host="claude"),
        _manifest(plugin_id="other-plugin"),
        _manifest(plugin_version=None),
        _manifest(plugin_version=""),
        _manifest(plugin_version="x" * 129),
        _manifest(plugin_version="bad\nversion"),
        _manifest(install_id=None),
        _manifest(install_id=""),
        _manifest(install_id="x" * 129),
        _manifest(install_id="bad\nid"),
        _manifest(owned_files=None),
    ],
)
def test_managed_bundle_identity_rejects_malformed_identity_fields(
    manifest: Any,
    tmp_path: Path,
) -> None:
    target = tmp_path / "bundle"
    _write_bundle(target, manifest=manifest)

    assert inventory._managed_bundle_identity(target, "codex") == (None, None, None)


def test_managed_bundle_matching_requires_an_exact_tamper_free_tree(tmp_path: Path) -> None:
    target = tmp_path / "bundle"
    files = _write_bundle(target)

    assert inventory._managed_bundle_matches(target, "codex", files) is True

    (target / "unexpected.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    assert inventory._managed_bundle_matches(target, "codex", files) is False


class _SyntheticEntry:
    def __init__(self, *, symlink: bool = False) -> None:
        self._symlink = symlink

    def is_symlink(self) -> bool:
        return self._symlink

    def is_file(self) -> bool:
        return False


class _SyntheticTree:
    def __init__(self, entries: list[_SyntheticEntry] | None = None) -> None:
        self._entries = entries

    def rglob(self, _pattern: str) -> list[_SyntheticEntry]:
        if self._entries is None:
            raise OSError("injected enumeration failure")
        return self._entries


@pytest.mark.parametrize(
    "tree",
    [
        _SyntheticTree([_SyntheticEntry(symlink=True)]),
        _SyntheticTree([_SyntheticEntry() for _ in range(513)]),
        _SyntheticTree(),
    ],
)
def test_managed_bundle_matching_rejects_links_huge_trees_and_io_failures(
    monkeypatch: pytest.MonkeyPatch,
    tree: _SyntheticTree,
) -> None:
    files = {"payload.txt": "payload"}
    monkeypatch.setattr(
        inventory,
        "_managed_bundle_identity",
        lambda *_args: (PLUGIN_VERSION, "install-id", inventory._bundle_digest(files)),
    )

    assert inventory._managed_bundle_matches(tree, "codex", files) is False


def test_native_version_and_host_version_validation_is_conservative() -> None:
    cachebuster = f"{PLUGIN_VERSION}+codex.{'a' * 12}"
    assert inventory._native_plugin_version_matches("codex", PLUGIN_VERSION) is True
    assert inventory._native_plugin_version_matches("claude", cachebuster) is False
    assert inventory._native_plugin_version_matches("codex", cachebuster) is True
    assert inventory._native_plugin_version_matches("codex", f"{cachebuster}x") is False
    assert inventory._sanitize_host_version(NativeCommandResult(("codex",), 1, "codex 1.0")) is None


def _attestation(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "proof_contract": CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        "proof_digest": "a" * 64,
        "profile_scope": "current-profile",
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "host_version": "codex 1.0",
        "plugin_version": PLUGIN_VERSION,
        "install_id": "install-id",
        "bundle_digest": "digest",
    }
    value.update(overrides)
    return value


def _canary_state(**overrides: Any) -> tuple[bool | None, str, list[str], dict[str, Any] | None]:
    values: dict[str, Any] = {
        "target": Path("managed"),
        "registered": True,
        "enabled": True,
        "native_record": {"pluginVersion": PLUGIN_VERSION},
        "host_version": "codex 1.0",
        "managed_version": PLUGIN_VERSION,
        "install_id": "install-id",
        "bundle_digest": "digest",
        "allow_read": True,
    }
    values.update(overrides)
    return inventory._canary_attestation_state("codex", **values)


def test_canary_attestation_checks_platform_native_version_and_native_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inventory, "_read_canary_attestation", lambda _host: _attestation())
    assert _canary_state()[:3] == (True, "verified", [])

    monkeypatch.setattr(
        inventory,
        "_read_canary_attestation",
        lambda _host: _attestation(platform_system="different"),
    )
    canary, status, reasons, _attested = _canary_state(
        registered=False,
        native_record={"version": "tampered-version"},
    )
    assert canary is None
    assert status == "stale"
    assert reasons == ["native_plugin_version", "native_state", "platform_system"]


def test_runtime_state_and_empty_inventory_are_explicit() -> None:
    assert inventory._runtime_state(False) == "not-loaded"
    assert inventory.inspect_host_installations(hosts=[]) == []


def test_marketplace_probe_failure_remains_unproven(tmp_path: Path) -> None:
    def runner(command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if command[1:] == ["--version"]:
            return {"returncode": 0, "stdout": "codex 1.0"}
        if "marketplace" in command:
            return {"returncode": 1, "stderr": "marketplace unavailable"}
        return {"returncode": 0, "stdout": '{"plugins": []}'}

    record = inventory.inspect_host_installation(
        "codex",
        home_dir=tmp_path,
        binary_resolver=lambda binary: binary,
        command_runner=runner,
    )

    assert record["marketplace_registered"] is None


def test_concurrent_inventory_contains_unexpected_worker_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(inventory, "_can_execute_native", lambda **_kwargs: False)

    def fail_worker(_host: str, **_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("injected worker failure")

    monkeypatch.setattr(inventory, "_safe_inspect_host", fail_worker)
    records = inventory.inspect_host_installations(hosts=("codex", "claude"))

    assert [record["host"] for record in records] == ["codex", "claude"]
    assert all(record["evidence"] == ["inspection:error:RuntimeError"] for record in records)
    assert all(
        record["inventory_error"] == "RuntimeError: injected worker failure" for record in records
    )
