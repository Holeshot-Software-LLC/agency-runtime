"""Focused managed-install identity contracts for native-child delivery."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import native_child_install_identity as subject
from agency_runtime.core.installer_contracts import INSTALL_MANIFEST, PLUGIN_ID, PLUGIN_VERSION
from agency_runtime.core.installer_native import plugin_target
from agency_runtime.core.process_argv import PersistentArtifactIdentity

_DIGEST = "a" * 64
_INSTALL_ID = "38111c8f-e807-4ff0-a851-4d0f7babe0fb"


def _artifact(path: str, *, digest: str) -> dict[str, int | str | None]:
    return PersistentArtifactIdentity(
        lexical_path=path,
        lexical_device=1,
        lexical_inode=2,
        lexical_mode=3,
        lexical_size=4,
        lexical_modified_ns=5,
        lexical_file_attributes=0,
        link_target=None,
        resolved_path=path,
        resolved_device=1,
        resolved_inode=2,
        resolved_mode=3,
        resolved_size=4,
        resolved_modified_ns=5,
        resolved_file_attributes=0,
        sha256=digest,
    ).manifest()


def _managed_target(home: Path, host: str = "codex") -> Path:
    target = plugin_target(host, home_dir=home)
    target.mkdir(parents=True)
    (target / "payload.txt").write_text("managed payload\n", encoding="utf-8")
    manifest: dict[str, Any] = {
        "schema_version": 2,
        "owner": "agency-runtime",
        "host": host,
        "plugin_id": PLUGIN_ID,
        "plugin_version": PLUGIN_VERSION,
        "install_id": _INSTALL_ID,
        "installed_at": "2026-08-12T00:00:00+00:00",
        "target": str(target),
        "owned_files": ["payload.txt"],
        "backup_path": None,
        "launcher_artifacts": [
            _artifact("trusted-python", digest="b" * 64),
            _artifact("trusted-bootstrap", digest="c" * 64),
        ],
    }
    (target / INSTALL_MANIFEST).write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def _trusted_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "snapshot_persistent_artifacts",
        lambda paths: subject.persistent_artifacts_from_manifest(
            [
                _artifact(paths[0], digest="b" * 64),
                _artifact(paths[1], digest="c" * 64),
            ]
        ),
    )
    monkeypatch.setattr(subject, "revalidate_persistent_artifacts", lambda _items: None)
    monkeypatch.setattr(subject, "runtime_digest_for_bootstrap", lambda _path: _DIGEST)
    monkeypatch.setattr(subject, "running_runtime_digest", lambda: _DIGEST)


def test_current_identity_binds_exact_bundle_install_and_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _managed_target(tmp_path)
    _trusted_runtime(monkeypatch)

    identity = subject.current_managed_host_install_identity(
        "codex",
        home_dir=tmp_path,
    )

    assert identity is not None
    assert identity.host == "codex"
    assert identity.plugin_version == PLUGIN_VERSION
    assert identity.install_id == _INSTALL_ID
    assert len(identity.bundle_digest) == 64
    assert identity.running_runtime_digest == identity.candidate_digest == _DIGEST
    with pytest.raises(FrozenInstanceError):
        identity.install_id = "changed"  # type: ignore[misc]


def test_runtime_identity_uses_owner_home_capability_inside_isolated_canary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_home = tmp_path / "owner"
    isolated_home = tmp_path / "isolated"
    _managed_target(owner_home, host="claude")
    isolated_home.mkdir()
    _trusted_runtime(monkeypatch)

    identity = subject.current_runtime_managed_host_install_identity(
        "claude",
        environ={
            "AGENCY_CANARY_MODE": "1",
            subject.CANARY_NATIVE_INSTALL_HOME_ENV: str(owner_home.resolve()),
            "HOME": str(isolated_home),
            "USERPROFILE": str(isolated_home),
            "CLAUDE_CONFIG_DIR": str(isolated_home / ".claude"),
        },
    )

    assert identity is not None
    assert identity.host == "claude"
    assert identity.install_id == _INSTALL_ID
    assert (
        subject.current_runtime_managed_host_install_identity(
            "claude",
            environ={
                "AGENCY_CANARY_MODE": "1",
                subject.CANARY_NATIVE_INSTALL_HOME_ENV: "relative-owner-home",
            },
        )
        is None
    )
    assert (
        subject.current_runtime_managed_host_install_identity(
            "claude",
            environ={"AGENCY_CANARY_MODE": "1", "HOME": str(isolated_home)},
        )
        is None
    )


@pytest.mark.parametrize(
    ("mutation", "patch_runtime"),
    [
        (lambda target: (target / "unexpected.txt").write_text("extra", encoding="utf-8"), None),
        (
            lambda target: json.loads((target / INSTALL_MANIFEST).read_text(encoding="utf-8")),
            "mismatch",
        ),
    ],
)
def test_current_identity_fails_closed_for_unowned_content_or_runtime_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
    patch_runtime: str | None,
) -> None:
    target = _managed_target(tmp_path)
    _trusted_runtime(monkeypatch)
    mutation(target)
    if patch_runtime:
        monkeypatch.setattr(subject, "running_runtime_digest", lambda: "d" * 64)

    assert subject.current_managed_host_install_identity("codex", home_dir=tmp_path) is None


def test_current_identity_rejects_manifest_drift_and_mid_read_bundle_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _managed_target(tmp_path)
    _trusted_runtime(monkeypatch)

    manifest_path = target / INSTALL_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["target"] = str(tmp_path / "other")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert subject.current_managed_host_install_identity("codex", home_dir=tmp_path) is None

    manifest["target"] = str(target)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    original = subject._managed_bundle_identity
    calls = 0

    def change_after_first_read(path: Path, host: str) -> tuple[str | None, str | None, str | None]:
        nonlocal calls
        identity = original(path, host)
        calls += 1
        if calls == 1:
            (path / "payload.txt").write_text("changed after first read\n", encoding="utf-8")
        return identity

    monkeypatch.setattr(subject, "_managed_bundle_identity", change_after_first_read)
    assert subject.current_managed_host_install_identity("codex", home_dir=tmp_path) is None


def test_current_identity_rejects_unknown_host_missing_runtime_and_launcher_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _managed_target(tmp_path)
    _trusted_runtime(monkeypatch)

    assert subject.current_managed_host_install_identity("unknown", home_dir=tmp_path) is None

    monkeypatch.setattr(subject, "running_runtime_digest", lambda: "")
    assert subject.current_managed_host_install_identity("codex", home_dir=tmp_path) is None

    _trusted_runtime(monkeypatch)
    monkeypatch.setattr(subject, "snapshot_persistent_artifacts", lambda _paths: ())
    assert subject.current_managed_host_install_identity("codex", home_dir=tmp_path) is None
