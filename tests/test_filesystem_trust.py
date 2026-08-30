"""Contract tests for canonical filesystem trust primitives."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

from agency_runtime.core import (
    bounded_io,
    configuration_identity,
    configuration_persistence,
    dashboard_broker_runtime,
    dashboard_runtime,
    installer_inventory,
    launcher_bootstrap,
    path_authority,
    private_paths,
    runtime_control,
)
from agency_runtime.core.filesystem_trust import (
    absolute_path,
    metadata_is_link_or_reparse_point,
    same_file_identity,
)
from agency_runtime.core.roster import ingress
from agency_runtime.core.selector import policy


def _metadata(
    *,
    device: int = 7,
    inode: int = 11,
    mode: int = stat.S_IFREG | 0o600,
    attributes: int | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        st_dev=device,
        st_ino=inode,
        st_mode=mode,
        st_file_attributes=attributes,
    )


def test_absolute_path_normalizes_lexically_without_requiring_target(tmp_path: Path) -> None:
    requested = tmp_path / "missing" / ".." / "target"

    assert absolute_path(requested) == Path(os.path.abspath(requested.expanduser()))
    assert absolute_path(requested).is_absolute()


def test_link_classifier_handles_posix_and_windows_metadata() -> None:
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))

    assert not metadata_is_link_or_reparse_point(_metadata(attributes=None))
    assert metadata_is_link_or_reparse_point(_metadata(mode=stat.S_IFLNK | 0o777, attributes=0))
    assert metadata_is_link_or_reparse_point(_metadata(attributes=reparse))


def test_same_file_identity_requires_nonzero_matching_device_and_inode() -> None:
    first = _metadata(device=3, inode=5, mode=stat.S_IFREG | 0o600)

    assert same_file_identity(first, _metadata(device=3, inode=5, mode=stat.S_IFDIR))
    assert not same_file_identity(first, _metadata(device=4, inode=5))
    assert not same_file_identity(first, _metadata(device=3, inode=6))
    assert not same_file_identity(first, _metadata(device=3, inode=0))
    assert same_file_identity(
        _metadata(device=3, inode=0),
        _metadata(device=3, inode=0),
        require_nonzero_inode=False,
    )


def test_metadata_call_sites_keep_canonical_monkeypatch_seams() -> None:
    aliases = (
        bounded_io._is_link_or_reparse,
        configuration_identity._is_link_or_reparse,
        dashboard_broker_runtime._link_like,
        dashboard_runtime._link_like,
        installer_inventory._is_link_or_reparse,
        launcher_bootstrap._is_link_or_reparse,
        ingress._metadata_is_link_or_reparse,
        policy._metadata_is_link_or_reparse,
    )

    assert all(alias is metadata_is_link_or_reparse_point for alias in aliases)


def test_identity_and_absolute_call_sites_keep_canonical_monkeypatch_seams() -> None:
    assert bounded_io._same_identity is same_file_identity
    assert dashboard_runtime._same_file is same_file_identity
    assert runtime_control._same_file is same_file_identity
    assert path_authority._absolute is absolute_path
    assert private_paths._absolute is absolute_path


def test_path_classifier_wrapper_delegates_through_patchable_alias(
    monkeypatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "regular"
    target.write_text("value", encoding="utf-8")
    observed: list[os.stat_result] = []

    monkeypatch.setattr(
        configuration_persistence,
        "_metadata_is_link_or_reparse",
        lambda metadata: observed.append(metadata) or True,
    )

    assert configuration_persistence.is_link_or_reparse_point(target)
    assert len(observed) == 1
