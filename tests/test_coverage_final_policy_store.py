"""Exact branch coverage for policy and private storage boundary invariants."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import private_paths
from agency_runtime.core.selector import policy
from agency_runtime.core.store import security, sqlite


def test_policy_skips_non_mapping_fallbacks_and_short_division_entries() -> None:
    companion_policy = {
        "actions": {"DEFAULT": {"always_include": ["invalid"]}},
    }

    assert policy.detect_fallback_companions(companion_policy) == []
    assert policy._division_companion_values(["incomplete"]) is None


def _private_identity(path: Path) -> private_paths.PrivateDirectoryIdentity:
    return private_paths.PrivateDirectoryIdentity(path=path, device=1, inode=1)


def test_host_descendant_can_skip_restriction_and_rejects_untrusted_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    authority = _private_identity(root)
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: True)
    monkeypatch.setattr(private_paths, "_host_descendant_is_private", lambda *_args: True)
    monkeypatch.setattr(
        private_paths,
        "_restrict_private_directory",
        lambda _path: pytest.fail("a host-owned child must not be permission-repaired"),
    )

    target = root / "host-owned"
    assert (
        private_paths._ensure_host_private_descendant(
            target,
            authority,
            product_owned=False,
        )
        == target
    )

    trust = iter((True, False))
    monkeypatch.setattr(
        private_paths,
        "_host_descendant_is_private",
        lambda *_args: next(trust),
    )
    with pytest.raises(PermissionError, match="descendant is not private"):
        private_paths._ensure_host_private_descendant(
            root / "untrusted",
            authority,
            product_owned=False,
        )


class _StaleGuard:
    def __init__(self) -> None:
        self.closed = False

    def is_current(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


def test_codex_parent_pinning_closes_a_stale_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visualizations = tmp_path / "visualizations"
    candidate = visualizations / "2026" / "07" / "16" / "019f4c7c-64ea-7650-a414-2680b0efabc6"
    candidate.mkdir(parents=True)
    guard = _StaleGuard()
    monkeypatch.setattr(private_paths, "validate_private_directory", lambda path: path)
    monkeypatch.setattr(
        private_paths,
        "windows_restricted_host_boundary_is_trusted",
        lambda _path: True,
    )
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: guard,
    )

    assert private_paths._pin_codex_host_private_parent(candidate, visualizations) is None
    assert guard.closed is True

    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: None,
    )
    assert private_paths._pin_codex_host_private_parent(candidate, visualizations) is None


def test_posix_creation_boundary_rejects_an_uninspectable_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary = tmp_path / "boundary"
    intended = boundary / "child"
    monkeypatch.setattr(security, "storage_parent_is_trusted", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        security.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(OSError("denied")),
    )

    assert not security.storage_creation_boundary_is_trusted(
        boundary,
        intended,
        is_windows=False,
    )


def test_discard_created_receipts_ignores_receipts_owned_elsewhere() -> None:
    retained = security.CreatedStoragePath(Path("retained"), 1, 2, True)
    unrelated = security.CreatedStoragePath(Path("unrelated"), 3, 4, True)
    receipts = [retained]

    security._discard_created_receipts(receipts, [unrelated])

    assert receipts == [retained]


def _bare_store(path: Path) -> sqlite.Store:
    store = sqlite.Store.__new__(sqlite.Store)
    store.db_path = path
    store._permission_fingerprints = {}
    return store


def test_storage_creation_rejects_an_initially_untrusted_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "agency.db"
    database.touch()
    store = _bare_store(database)
    monkeypatch.setattr(store, "_assert_storage_paths_safe", lambda: None)
    monkeypatch.setattr(
        store, "_require_stable_trusted_storage_file", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(sqlite, "_sqlite_storage_paths", lambda _path: (database,))
    monkeypatch.setattr(sqlite, "_is_link_or_reparse_point", lambda _path: False)
    monkeypatch.setattr(sqlite, "_storage_file_is_trusted", lambda _path: False)

    with pytest.raises(PermissionError, match="not a trusted single-link file"):
        store._ensure_private_storage_file()


@pytest.mark.parametrize(
    ("method_name", "expected_message"),
    [
        ("_validate_repaired_storage_target", "unsafe after permission repair"),
        ("_repair_storage_target_once", "unsafe identity"),
    ],
)
def test_non_optional_storage_targets_propagate_pretrust_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    expected_message: str,
) -> None:
    database = tmp_path / "agency.db"
    store = _bare_store(database)
    metadata = SimpleNamespace(st_dev=3, st_ino=7, st_mode=0o600)
    monkeypatch.setattr(store, "_storage_metadata", lambda *_args, **_kwargs: metadata)
    monkeypatch.setattr(sqlite, "_metadata_is_link_or_reparse_point", lambda _metadata: False)

    def reject(*_args: Any, message: str, **_kwargs: Any) -> None:
        raise PermissionError(message)

    monkeypatch.setattr(sqlite, "_require_storage_target_trusted", reject)

    method = getattr(store, method_name)
    with pytest.raises(PermissionError, match=expected_message):
        method(
            database,
            directory=False,
            optional_sidecar=False,
            **(
                {"fingerprint": (3, 7)}
                if method_name == "_validate_repaired_storage_target"
                else {}
            ),
        )
