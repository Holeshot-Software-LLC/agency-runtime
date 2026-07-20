"""Durable master-switch security, atomicity, and cache behavior."""

from __future__ import annotations

import json
import os
import stat
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import runtime_control as control


@pytest.fixture(autouse=True)
def _clear_control_cache() -> None:
    control.clear_runtime_control_cache()
    yield
    control.clear_runtime_control_cache()


def _control_path(home: Path) -> Path:
    return home / ".agency-runtime" / "run" / "control.json"


def _write_document(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)
    control.clear_runtime_control_cache()


def _valid_document(**changes: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": control.RUNTIME_CONTROL_SCHEMA_VERSION,
        "enabled": False,
        "generation": 1,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": "test",
    }
    document.update(changes)
    return document


def test_canonical_path_and_absent_state_default_to_enabled(tmp_path: Path) -> None:
    expected = _control_path(tmp_path)

    assert control.runtime_control_path(home_dir=tmp_path) == expected
    assert control.read_runtime_control(home_dir=tmp_path) == {
        "schema_version": 1,
        "enabled": True,
        "generation": 0,
        "updated_at": "1970-01-01T00:00:00Z",
        "source": "default",
    }
    assert control.master_enabled(home_dir=tmp_path) is True
    assert not expected.exists()


def test_canary_control_path_override_is_narrow_and_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    override = _control_path(tmp_path)
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_CONTROL_PATH", str(override))

    assert control._target_path(path=None, home_dir=None) == override
    explicit_home = tmp_path / "explicit"
    assert control._target_path(path=None, home_dir=explicit_home) == _control_path(explicit_home)
    explicit_path = tmp_path / "explicit-control.json"
    assert control._target_path(path=explicit_path, home_dir=None) == explicit_path


def test_canary_control_path_override_rejects_noncanonical_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    monkeypatch.setenv("AGENCY_CANARY_CONTROL_PATH", str(tmp_path / "control.json"))

    with pytest.raises(control.RuntimeControlValidationError, match="not canonical"):
        control._target_path(path=None, home_dir=None)

    monkeypatch.setenv(
        "AGENCY_CANARY_CONTROL_PATH",
        str(Path(".agency-runtime") / "run" / "control.json"),
    )
    with pytest.raises(control.RuntimeControlValidationError, match="must be absolute"):
        control._target_path(path=None, home_dir=None)


def test_canary_control_path_override_is_ignored_outside_canary_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_CANARY_MODE", "0")
    monkeypatch.setenv("AGENCY_CANARY_CONTROL_PATH", str(_control_path(tmp_path)))

    assert control._target_path(path=None, home_dir=None) == control.runtime_control_path()


def test_control_snapshot_distinguishes_absent_default_from_materialized_state(
    tmp_path: Path,
) -> None:
    absent = control.read_runtime_control_snapshot(home_dir=tmp_path)

    assert absent.materialized is False
    assert absent.enabled is True
    assert absent.generation == 0
    assert absent.as_document() == control.read_runtime_control(home_dir=tmp_path)

    control.set_master_enabled(False, home_dir=tmp_path)
    materialized = control.read_effective_runtime_control_snapshot(home_dir=tmp_path)

    assert materialized.materialized is True
    assert materialized.enabled is False
    assert materialized.generation == 1
    assert materialized.as_document() == control.read_effective_runtime_control(home_dir=tmp_path)


def test_round_trip_cas_noop_and_generation_semantics(tmp_path: Path) -> None:
    first_time = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    second_time = datetime(2026, 7, 16, 12, 1, tzinfo=timezone.utc)

    disabled = control.set_master_enabled(
        False,
        expected_generation=0,
        source="cli",
        home_dir=tmp_path,
        now=first_time,
    )
    assert disabled == _valid_document(source="cli")
    assert control.master_enabled(home_dir=tmp_path) is False

    unchanged = control.set_master_enabled(
        False,
        expected_generation=1,
        source="dashboard",
        home_dir=tmp_path,
        now=second_time,
    )
    assert unchanged == disabled

    enabled = control.set_master_enabled(
        True,
        expected_generation=1,
        source="dashboard",
        home_dir=tmp_path,
        now=second_time,
    )
    assert enabled == {
        "schema_version": 1,
        "enabled": True,
        "generation": 2,
        "updated_at": "2026-07-16T12:01:00Z",
        "source": "dashboard",
    }
    assert control.read_runtime_control(home_dir=tmp_path) == enabled
    assert control.master_enabled(home_dir=tmp_path) is True

    target = _control_path(tmp_path)
    assert json.loads(target.read_text(encoding="utf-8")) == enabled
    assert target.stat().st_size <= control.MAX_RUNTIME_CONTROL_BYTES
    if os.name != "nt":
        assert stat.S_IMODE(target.stat().st_mode) == 0o600
        assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_noop_default_does_not_create_a_control_document(tmp_path: Path) -> None:
    state = control.set_master_enabled(
        True,
        expected_generation=0,
        source="cli",
        home_dir=tmp_path,
    )

    assert state["enabled"] is True
    assert state["generation"] == 0
    assert not _control_path(tmp_path).exists()


def test_materialization_is_idempotent_and_never_overwrites_existing_state(
    tmp_path: Path,
) -> None:
    materialized = control.ensure_runtime_control_materialized(
        home_dir=tmp_path,
        source="installer",
        now=datetime(2026, 7, 17, 1, 2, tzinfo=timezone.utc),
    )
    repeated = control.ensure_runtime_control_materialized(
        home_dir=tmp_path,
        source="different-source",
    )

    assert materialized == repeated
    assert materialized == {
        "schema_version": 1,
        "enabled": True,
        "generation": 0,
        "updated_at": "2026-07-17T01:02:00Z",
        "source": "installer",
    }
    assert control.read_runtime_control_snapshot(home_dir=tmp_path).materialized is True

    disabled = control.set_master_enabled(False, home_dir=tmp_path)
    assert control.ensure_runtime_control_materialized(home_dir=tmp_path) == disabled


def test_stale_compare_and_swap_does_not_change_state(tmp_path: Path) -> None:
    original = control.set_master_enabled(False, home_dir=tmp_path)

    with pytest.raises(control.RuntimeControlConflictError, match="expected 0, found 1"):
        control.set_master_enabled(
            True,
            expected_generation=0,
            source="cli",
            home_dir=tmp_path,
        )

    assert control.read_runtime_control(home_dir=tmp_path) == original


def test_concurrent_cas_allows_exactly_one_state_change(tmp_path: Path) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    successes: list[dict[str, Any]] = []
    conflicts: list[control.RuntimeControlConflictError] = []
    barrier = threading.Barrier(3)

    def update(source: str) -> None:
        barrier.wait()
        try:
            result = control.set_master_enabled(
                True,
                expected_generation=1,
                source=source,
                home_dir=tmp_path,
            )
        except control.RuntimeControlConflictError as exc:
            conflicts.append(exc)
        else:
            successes.append(result)

    workers = [threading.Thread(target=update, args=(f"worker-{index}",)) for index in range(2)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=10)

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert successes[0]["generation"] == 2
    assert control.read_runtime_control(home_dir=tmp_path)["generation"] == 2


@pytest.mark.parametrize(
    "document, message",
    [
        ({}, "invalid schema"),
        (_valid_document(extra=True), "invalid schema"),
        (_valid_document(schema_version=2), "version is unsupported"),
        (_valid_document(schema_version=True), "version is unsupported"),
        (_valid_document(schema_version=1.0), "version is unsupported"),
        (_valid_document(enabled=1), "must be boolean"),
        (_valid_document(generation=True), "generation is invalid"),
        (_valid_document(generation=-1), "generation is invalid"),
        (_valid_document(generation=1 << 63), "generation is invalid"),
        (_valid_document(updated_at="yesterday"), "timestamp is invalid"),
        (_valid_document(updated_at="2026-07-16T12:00:00"), "timestamp is invalid"),
        (_valid_document(source=""), "source is invalid"),
        (_valid_document(source="bad\nsource"), "source is invalid"),
    ],
)
def test_diagnostic_reader_rejects_every_noncanonical_document(
    tmp_path: Path,
    document: object,
    message: str,
) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    _write_document(_control_path(tmp_path), document)

    with pytest.raises(control.RuntimeControlValidationError, match=message):
        control.read_runtime_control(home_dir=tmp_path)
    assert control.master_enabled(home_dir=tmp_path) is True


@pytest.mark.parametrize("raw", [b"{", b"[]", b"\xff"])
def test_corrupt_control_fails_diagnostics_but_enforcement_stays_enabled(
    tmp_path: Path,
    raw: bytes,
) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    target = _control_path(tmp_path)
    target.write_bytes(raw)
    if os.name != "nt":
        target.chmod(0o600)
    control.clear_runtime_control_cache()

    with pytest.raises(control.RuntimeControlValidationError):
        control.read_runtime_control(home_dir=tmp_path)
    assert control.master_enabled(home_dir=tmp_path) is True


def test_oversized_control_is_rejected_and_fails_enabled(tmp_path: Path) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    target = _control_path(tmp_path)
    target.write_bytes(b"x" * (control.MAX_RUNTIME_CONTROL_BYTES + 1))
    if os.name != "nt":
        target.chmod(0o600)
    control.clear_runtime_control_cache()

    with pytest.raises(control.RuntimeControlValidationError, match="4 KiB"):
        control.read_runtime_control(home_dir=tmp_path)
    assert control.master_enabled(home_dir=tmp_path) is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode contract")
@pytest.mark.parametrize("mode", [0o640, 0o660, 0o666])
def test_nonprivate_posix_control_is_rejected(tmp_path: Path, mode: int) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    target = _control_path(tmp_path)
    target.chmod(mode)
    control.clear_runtime_control_cache()

    with pytest.raises(control.RuntimeControlSecurityError, match="owner-private"):
        control.read_runtime_control(home_dir=tmp_path)
    assert control.master_enabled(home_dir=tmp_path) is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX hard-link behavior")
def test_hardlinked_control_is_rejected(tmp_path: Path) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    target = _control_path(tmp_path)
    alias = target.with_name("alias.json")
    os.link(target, alias)

    with pytest.raises(control.RuntimeControlSecurityError, match="single-link"):
        control.read_runtime_control(home_dir=tmp_path)


def test_final_symlink_is_rejected_without_touching_target(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlinks unavailable")
    control.set_master_enabled(False, home_dir=tmp_path)
    target = _control_path(tmp_path)
    victim = tmp_path / "victim.json"
    victim.write_text("unchanged", encoding="utf-8")
    target.unlink()
    try:
        target.symlink_to(victim)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(control.RuntimeControlSecurityError, match="owner-private"):
        control.read_runtime_control(home_dir=tmp_path)
    assert control.master_enabled(home_dir=tmp_path) is True
    assert victim.read_text(encoding="utf-8") == "unchanged"


def test_parent_symlink_is_rejected_without_creating_state(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlinks unavailable")
    real = tmp_path / "real"
    real.mkdir()
    linked_home = tmp_path / "linked-home"
    try:
        linked_home.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(control.RuntimeControlSecurityError, match="unsafe"):
        control.read_runtime_control(home_dir=linked_home)
    assert control.master_enabled(home_dir=linked_home) is True
    assert not (real / ".agency-runtime").exists()


def test_stat_cache_detects_atomic_replacement(tmp_path: Path) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    target = _control_path(tmp_path)
    assert control.read_runtime_control(home_dir=tmp_path)["enabled"] is False

    replacement = target.with_name("replacement.json")
    replacement.write_text(
        json.dumps(_valid_document(enabled=True, generation=2, source="external")) + "\n",
        encoding="utf-8",
    )
    if os.name != "nt":
        replacement.chmod(0o600)
    else:
        assert control.restrict_windows_acl(replacement, is_windows=True)
    os.replace(replacement, target)

    observed = control.read_runtime_control(home_dir=tmp_path)
    assert observed["enabled"] is True
    assert observed["generation"] == 2


def test_cache_hit_avoids_a_second_bounded_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    control.clear_runtime_control_cache()
    calls = 0
    original = control.read_bounded_regular_file

    def observe(*args: Any, **kwargs: Any) -> bytes:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(control, "read_bounded_regular_file", observe)

    assert control.read_runtime_control(home_dir=tmp_path)["enabled"] is False
    assert control.read_runtime_control(home_dir=tmp_path)["enabled"] is False
    assert calls == 1


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"enabled": 1}, "must be boolean"),
        ({"enabled": False, "expected_generation": True}, "generation is invalid"),
        ({"enabled": False, "expected_generation": -1}, "generation is invalid"),
        ({"enabled": False, "source": ""}, "source is invalid"),
        ({"enabled": False, "source": "x" * 65}, "source is invalid"),
        ({"enabled": False, "timeout": float("nan")}, "lock timeout"),
        ({"enabled": False, "timeout": 301}, "lock timeout"),
        (
            {"enabled": False, "now": datetime(2026, 7, 16, 12, 0)},
            "timezone-aware",
        ),
    ],
)
def test_update_api_rejects_invalid_inputs(
    tmp_path: Path,
    kwargs: dict[str, Any],
    message: str,
) -> None:
    enabled = kwargs.pop("enabled")
    with pytest.raises(control.RuntimeControlValidationError, match=message):
        control.set_master_enabled(enabled, home_dir=tmp_path, **kwargs)


def test_generation_exhaustion_is_fail_safe(tmp_path: Path) -> None:
    control.set_master_enabled(False, home_dir=tmp_path)
    _write_document(
        _control_path(tmp_path),
        _valid_document(generation=(1 << 63) - 1),
    )

    with pytest.raises(control.RuntimeControlValidationError, match="exhausted"):
        control.set_master_enabled(True, home_dir=tmp_path)
    assert control.read_runtime_control(home_dir=tmp_path)["enabled"] is False


def test_atomic_publish_fsyncs_file_and_parent_and_leaves_no_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fsync_calls: list[int] = []
    replacements: list[tuple[Path, Path]] = []
    original_fsync = control.os.fsync
    original_replace = control.os.replace

    def fsync(descriptor: int) -> None:
        fsync_calls.append(descriptor)
        original_fsync(descriptor)

    def replace(source: Path, target: Path) -> None:
        replacements.append((Path(source), Path(target)))
        original_replace(source, target)

    monkeypatch.setattr(control.os, "fsync", fsync)
    monkeypatch.setattr(control.os, "replace", replace)

    control.set_master_enabled(False, home_dir=tmp_path)

    target = _control_path(tmp_path)
    assert replacements and replacements[-1][1] == target
    assert len(fsync_calls) >= (2 if os.name == "nt" else 3)
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_publish_failure_preserves_previous_document_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = control.set_master_enabled(False, home_dir=tmp_path)

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(control, "_replace_atomically", fail_replace)
    with pytest.raises(control.RuntimeControlSecurityError, match="published durably"):
        control.set_master_enabled(True, home_dir=tmp_path)

    target = _control_path(tmp_path)
    assert json.loads(target.read_text(encoding="utf-8")) == original
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_windows_privacy_probe_is_part_of_file_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    target = tmp_path / "control.json"
    target.write_text("{}", encoding="utf-8")
    observed: list[tuple[Path, bool]] = []
    monkeypatch.setattr(control, "os", os_facade(control.os, name="nt"))
    monkeypatch.setattr(
        control,
        "windows_directory_prevents_untrusted_writes",
        lambda path, **kwargs: observed.append((path, kwargs["private_access"])) or True,
    )

    assert control._owner_private_metadata(target, target.stat(), directory=False)
    assert observed == [(target, True)]


class _BytesPath:
    def __fspath__(self) -> bytes:
        return b"bytes-are-not-a-control-path"


@pytest.mark.parametrize(
    "value, message",
    [
        (object(), "must be text"),
        (_BytesPath(), "must be text"),
        ("\ud800", "path is invalid"),
        ("", "path is invalid"),
        ("x" * 4097, "path is invalid"),
        ("bad\npath", "path is invalid"),
    ],
)
def test_control_path_validation_is_bounded_and_text_only(
    value: object,
    message: str,
) -> None:
    with pytest.raises(control.RuntimeControlValidationError, match=message):
        control.read_runtime_control(path=value)  # type: ignore[arg-type]


def test_posix_owner_private_metadata_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    target = tmp_path / "control.json"
    target.write_text("{}", encoding="utf-8")
    metadata = target.stat()
    real_os = control.os
    monkeypatch.setattr(
        control,
        "os",
        os_facade(real_os, name="posix", geteuid=lambda: 7),
    )
    assert control._current_uid() == 7
    monkeypatch.setattr(
        control,
        "os",
        os_facade(real_os, name="posix", missing=frozenset({"geteuid"})),
    )
    assert control._current_uid() is None
    monkeypatch.setattr(control, "_current_uid", lambda: 7)

    private_file = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o600,
        st_ino=metadata.st_ino,
        st_nlink=1,
        st_uid=7,
    )
    public_file = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o640,
        st_ino=metadata.st_ino,
        st_nlink=1,
        st_uid=7,
    )
    private_directory = SimpleNamespace(
        st_mode=stat.S_IFDIR | 0o700,
        st_ino=metadata.st_ino,
        st_nlink=1,
        st_uid=7,
    )
    assert control._owner_private_metadata(target, private_file, directory=False)
    assert not control._owner_private_metadata(target, public_file, directory=False)
    assert control._owner_private_metadata(tmp_path, private_directory, directory=True)
    monkeypatch.setattr(control, "_current_uid", lambda: None)
    assert not control._owner_private_metadata(tmp_path, private_directory, directory=True)


def test_owner_private_metadata_rejects_wrong_kinds_and_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "control.json"
    target.write_text("{}", encoding="utf-8")
    metadata = target.stat()
    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _value: True)
    assert not control._owner_private_metadata(target, metadata, directory=False)
    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _value: False)
    assert not control._owner_private_metadata(target, tmp_path.stat(), directory=False)
    zero_inode = SimpleNamespace(
        st_mode=metadata.st_mode,
        st_ino=0,
        st_nlink=1,
    )
    assert not control._owner_private_metadata(target, zero_inode, directory=False)
    linked = SimpleNamespace(
        st_mode=metadata.st_mode,
        st_ino=metadata.st_ino,
        st_nlink=2,
    )
    assert not control._owner_private_metadata(target, linked, directory=False)


def test_parent_snapshot_reports_each_security_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control, "_directory_candidates", lambda _path: (tmp_path,))
    original_lstat = control.os.lstat
    monkeypatch.setattr(control.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("gone")))
    with pytest.raises(control.RuntimeControlSecurityError, match="could not be inspected"):
        control._snapshot_private_parent(tmp_path)

    monkeypatch.setattr(control.os, "lstat", original_lstat)
    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _value: True)
    with pytest.raises(control.RuntimeControlSecurityError, match="real directories"):
        control._snapshot_private_parent(tmp_path)

    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _value: False)
    monkeypatch.setattr(control, "storage_parent_is_trusted", lambda *_args, **_kwargs: False)
    with pytest.raises(control.RuntimeControlSecurityError, match="cross-account"):
        control._snapshot_private_parent(tmp_path)

    monkeypatch.setattr(control, "storage_parent_is_trusted", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(control, "_owner_private_metadata", lambda *_args, **_kwargs: False)
    with pytest.raises(control.RuntimeControlSecurityError, match="owner-private"):
        control._snapshot_private_parent(tmp_path)


def test_directory_snapshot_detects_disappearance_and_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = ((tmp_path, tmp_path.stat()),)
    monkeypatch.setattr(control.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("gone")))
    with pytest.raises(control.RuntimeControlSecurityError, match="changed"):
        control._validate_directory_snapshot(snapshot)

    metadata = snapshot[0][1]
    replacement = SimpleNamespace(
        st_mode=stat.S_IFREG | 0o600,
        st_ino=metadata.st_ino,
        st_dev=metadata.st_dev,
    )
    monkeypatch.setattr(control.os, "lstat", lambda _path: replacement)
    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _value: False)
    with pytest.raises(control.RuntimeControlSecurityError, match="changed"):
        control._validate_directory_snapshot(snapshot)


def test_parent_preparation_normalizes_boundary_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "private" / "control.json"
    monkeypatch.setattr(control, "assert_storage_parent_chain", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(control, "nearest_existing_storage_parent", lambda _path: tmp_path)
    monkeypatch.setattr(
        control,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="untrusted creation"):
        control._prepare_parent(target)

    monkeypatch.setattr(
        control,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        control,
        "create_private_storage_parent",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("blocked")),
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="created securely"):
        control._prepare_parent(target)


def test_absent_parent_handles_existing_private_parent_and_unsafe_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "missing.json"
    observed: list[Path] = []
    monkeypatch.setattr(control, "assert_storage_parent_chain", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(control, "nearest_existing_storage_parent", lambda _path: tmp_path)
    monkeypatch.setattr(
        control,
        "_snapshot_private_parent",
        lambda path: observed.append(path) or (),
    )
    control._validate_absent_parent(target)
    assert observed == [tmp_path]

    monkeypatch.setattr(
        control,
        "nearest_existing_storage_parent",
        lambda _path: tmp_path.parent,
    )
    monkeypatch.setattr(
        control,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="untrusted creation"):
        control._validate_absent_parent(target)


@pytest.mark.parametrize(
    "operation, message",
    [
        (lambda: control._validate_source(3), "must be text"),
        (lambda: control._validate_source("\ud800"), "source is invalid"),
        (lambda: control._validate_timestamp(3), "must be text"),
    ],
)
def test_scalar_diagnostic_validation_error_paths(operation: Any, message: str) -> None:
    with pytest.raises(control.RuntimeControlValidationError, match=message):
        operation()


def test_cache_is_bounded_and_evicts_oldest_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")
    snapshot = ((tmp_path, tmp_path.stat()),)
    monkeypatch.setattr(control, "_CACHE_LIMIT", 1)

    control._cache_put(first, first.stat(), snapshot, _valid_document())
    control._cache_put(second, second.stat(), snapshot, _valid_document(generation=2))

    assert list(control._state_cache) == [control._cache_key(second)]


def test_read_existing_normalizes_read_and_identity_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "control.json"
    target.write_text("{}", encoding="utf-8")
    metadata = target.stat()
    monkeypatch.setattr(control, "_snapshot_private_parent", lambda _path: ())
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unreadable")),
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="read safely"):
        control._read_existing(target, use_cache=False)

    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: json.dumps(_valid_document()).encode(),
    )
    calls = iter([metadata, OSError("vanished")])

    def lstat_after_read(_path: Path) -> os.stat_result:
        value = next(calls)
        if isinstance(value, OSError):
            raise value
        return value

    monkeypatch.setattr(control.os, "lstat", lstat_after_read)
    with pytest.raises(control.RuntimeControlSecurityError, match="changed during read"):
        control._read_existing(target, use_cache=False)


def test_cached_read_falls_through_when_identity_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "control.json"
    target.write_text("{}", encoding="utf-8")
    before = target.stat()
    changed = SimpleNamespace(
        **{name: getattr(before, name) for name in dir(before) if name.startswith("st_")}
    )
    changed.st_size = before.st_size + 1
    calls = iter([before, changed, before])
    monkeypatch.setattr(control, "_snapshot_private_parent", lambda _path: ())
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(control, "_cache_get", lambda *_args: _valid_document())
    monkeypatch.setattr(control.os, "lstat", lambda _path: next(calls))
    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: json.dumps(_valid_document()).encode(),
    )
    monkeypatch.setattr(control, "_cache_put", lambda *_args: None)

    assert control._read_existing(target, use_cache=True) == _valid_document()

    changed = SimpleNamespace(
        **{name: getattr(before, name) for name in dir(before) if name.startswith("st_")}
    )
    changed.st_size = before.st_size + 1
    calls = iter([before, changed])
    monkeypatch.setattr(control.os, "lstat", lambda _path: next(calls))
    with pytest.raises(control.RuntimeControlSecurityError, match="changed during read"):
        control._read_existing(target, use_cache=False)


def test_read_runtime_control_normalizes_initial_inspection_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(control.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("denied")))
    with pytest.raises(control.RuntimeControlSecurityError, match="could not be inspected"):
        control.read_runtime_control(path=tmp_path / "control.json")


def test_secure_lock_open_error_paths_and_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock_path = tmp_path / ".control.json.lock"
    original_open = control.os.open
    original_lstat = control.os.lstat

    monkeypatch.setattr(
        control.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError()),
    )
    monkeypatch.setattr(control.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError("gone")))
    with pytest.raises(control.RuntimeControlSecurityError, match="could not be inspected"):
        control._secure_open_lock(lock_path, ())

    lock_path.write_bytes(b"\0")
    if os.name != "nt":
        lock_path.chmod(0o600)
    monkeypatch.setattr(control.os, "lstat", original_lstat)
    open_calls = 0

    def fail_second_open(*args: Any, **kwargs: Any) -> int:
        nonlocal open_calls
        open_calls += 1
        if open_calls == 1:
            raise FileExistsError
        raise OSError("open denied")

    monkeypatch.setattr(control.os, "open", fail_second_open)
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    with pytest.raises(control.RuntimeControlSecurityError, match="opened safely"):
        control._secure_open_lock(lock_path, ())

    monkeypatch.setattr(
        control.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("create denied")),
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="created safely"):
        control._secure_open_lock(tmp_path / "new.lock", ())
    monkeypatch.setattr(control.os, "open", original_open)


@pytest.mark.parametrize("acl_result", [False, control.WindowsACLSafetyError("unsafe")])
def test_new_windows_lock_requires_private_acl_and_cleans_up(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    acl_result: object,
    os_facade,
) -> None:
    lock_path = tmp_path / "control.lock"
    monkeypatch.setattr(control, "os", os_facade(control.os, name="nt"))

    def restrict(*_args: Any, **_kwargs: Any) -> bool:
        if isinstance(acl_result, Exception):
            raise acl_result
        return bool(acl_result)

    monkeypatch.setattr(control, "restrict_windows_acl", restrict)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    expected_error = (
        control.WindowsACLSafetyError
        if isinstance(acl_result, Exception)
        else control.RuntimeControlSecurityError
    )
    with pytest.raises(expected_error):
        control._secure_open_lock(lock_path, ())
    assert not lock_path.exists()


def test_new_windows_lock_accepts_a_stable_private_acl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    lock_path = tmp_path / "control.lock"
    monkeypatch.setattr(control, "os", os_facade(control.os, name="nt"))
    monkeypatch.setattr(control, "restrict_windows_acl", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(control, "_same_file", lambda *_args: True)
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)

    handle, created = control._secure_open_lock(lock_path, ())
    try:
        assert created is True
    finally:
        handle.close()


@pytest.mark.parametrize("existing", [False, True])
def test_secure_lock_detects_identity_change_before_and_after_hardening(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: bool,
) -> None:
    lock_path = tmp_path / "control.lock"
    if existing:
        lock_path.write_bytes(b"\0")
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(control, "restrict_windows_acl", lambda *_args, **_kwargs: True)
    outcomes = iter([True, False]) if not existing else iter([False])
    monkeypatch.setattr(control, "_same_file", lambda *_args: next(outcomes))

    with pytest.raises(control.RuntimeControlSecurityError, match="changed during open"):
        control._secure_open_lock(lock_path, ())
    if existing:
        assert lock_path.exists()
    else:
        assert not lock_path.exists()


def test_posix_lock_and_parent_fsync_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    target = tmp_path / "control.json"
    calls: list[int] = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda _fd, operation: calls.append(operation),
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.setattr(
        control,
        "os",
        os_facade(control.os, name="posix", fchmod=lambda *_args: None),
    )
    monkeypatch.setattr(control, "_prepare_parent", lambda _target: ())
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)

    with control._control_lock(target, timeout=1):
        pass
    assert calls == [3, 4]

    fsync_calls: list[int] = []
    original_open = control.os.open
    original_close = control.os.close
    probe = tmp_path / "fsync-probe"
    probe.write_bytes(b"")
    descriptor = original_open(probe, os.O_RDONLY)
    monkeypatch.setattr(control.os, "open", lambda *_args, **_kwargs: descriptor)
    monkeypatch.setattr(control.os, "fsync", lambda value: fsync_calls.append(value))
    monkeypatch.setattr(control.os, "close", lambda value: original_close(value))
    control._fsync_parent(tmp_path)
    assert fsync_calls == [descriptor]


@pytest.mark.skipif(os.name != "nt", reason="Windows byte-range lock behavior")
def test_control_lock_timeout_and_identity_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import msvcrt

    target = tmp_path / "control.json"
    lock_path = target.with_name(f".{target.name}.lock")
    lock_path.write_bytes(b"\0")
    handle = lock_path.open("r+b")
    monkeypatch.setattr(control, "_prepare_parent", lambda _target: ())
    monkeypatch.setattr(control, "_secure_open_lock", lambda *_args, **_kwargs: (handle, False))
    monkeypatch.setattr(msvcrt, "locking", lambda *_args: (_ for _ in ()).throw(OSError("busy")))
    with (
        pytest.raises(control.RuntimeControlBusyError, match="busy"),
        control._control_lock(target, timeout=0),
    ):
        pytest.fail("lock must not be acquired")

    handle = lock_path.open("r+b")
    monkeypatch.setattr(control, "_secure_open_lock", lambda *_args, **_kwargs: (handle, False))
    monkeypatch.setattr(msvcrt, "locking", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_same_file", lambda *_args: False)
    with (
        pytest.raises(control.RuntimeControlSecurityError, match="before acquisition"),
        control._control_lock(target, timeout=1),
    ):
        pytest.fail("identity loss must prevent acquisition")


def test_windows_control_lock_portable_acquire_timeout_and_identity_loss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    target = tmp_path / "control.json"
    lock_path = target.with_name(f".{target.name}.lock")
    lock_path.write_bytes(b"\0")
    operations: list[int] = []
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        LK_UNLCK=2,
        locking=lambda _fd, operation, _length: operations.append(operation),
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(control, "os", os_facade(control.os, name="nt"))
    monkeypatch.setattr(control, "_prepare_parent", lambda _target: ())
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(control, "_same_file", lambda *_args: True)

    handle = lock_path.open("r+b")
    monkeypatch.setattr(control, "_secure_open_lock", lambda *_args: (handle, False))
    with control._control_lock(target, timeout=1):
        pass
    assert operations == [fake_msvcrt.LK_NBLCK, fake_msvcrt.LK_UNLCK]

    def busy(_fd: int, _operation: int, _length: int) -> None:
        raise OSError("busy")

    fake_msvcrt.locking = busy
    handle = lock_path.open("r+b")
    monkeypatch.setattr(control, "_secure_open_lock", lambda *_args: (handle, False))
    with (
        pytest.raises(control.RuntimeControlBusyError, match="busy"),
        control._control_lock(target, timeout=0),
    ):
        pytest.fail("busy lock must not be acquired")

    fake_msvcrt.locking = lambda _fd, operation, _length: operations.append(operation)
    monkeypatch.setattr(control, "_same_file", lambda *_args: False)
    handle = lock_path.open("r+b")
    monkeypatch.setattr(control, "_secure_open_lock", lambda *_args: (handle, False))
    with (
        pytest.raises(control.RuntimeControlSecurityError, match="before acquisition"),
        control._control_lock(target, timeout=1),
    ):
        pytest.fail("identity loss must prevent acquisition")


def test_serialization_and_atomic_replace_platform_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    with pytest.raises(control.RuntimeControlValidationError, match="4 KiB"):
        control._serialize_document({"value": "x" * 5000})

    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("value", encoding="utf-8")
    real_os = control.os
    monkeypatch.setattr(control, "os", os_facade(real_os, name="posix"))
    control._replace_atomically(source, target)
    assert target.read_text(encoding="utf-8") == "value"

    monkeypatch.setattr(control, "os", os_facade(real_os, name="nt"))
    calls = 0

    def retry_replace(_source: Path, _target: Path) -> None:
        nonlocal calls
        calls += 1
        if calls <= len(control._WINDOWS_REPLACE_DELAYS):
            raise PermissionError("sharing violation")

    monkeypatch.setattr(control.os, "replace", retry_replace)
    monkeypatch.setattr(control.time, "sleep", lambda _delay: None)
    control._replace_atomically(source, target)
    assert calls == len(control._WINDOWS_REPLACE_DELAYS) + 1


@pytest.mark.parametrize(
    "failure",
    ["acl-error", "acl-false", "write-zero", "created-race", "write-race", "publish-race"],
)
def test_publish_document_fails_safely_for_security_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    os_facade,
) -> None:
    target = tmp_path / "control.json"
    snapshot = ((tmp_path, tmp_path.stat()),)
    monkeypatch.setattr(control, "os", os_facade(control.os, name="nt"))
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "restrict_windows_acl", lambda *_args, **_kwargs: True)
    if failure == "acl-error":
        monkeypatch.setattr(
            control,
            "restrict_windows_acl",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                control.WindowsACLSafetyError("unsafe token")
            ),
        )
    elif failure == "acl-false":
        monkeypatch.setattr(control, "restrict_windows_acl", lambda *_args, **_kwargs: False)
    elif failure == "write-zero":
        monkeypatch.setattr(control.os, "write", lambda *_args, **_kwargs: 0)
    elif failure == "created-race":
        monkeypatch.setattr(control, "_same_file", lambda *_args: False)
    elif failure == "write-race":
        outcomes = iter([True, False])
        monkeypatch.setattr(control, "_same_file", lambda *_args: next(outcomes))
    else:
        outcomes = iter([True, True, True, False])
        monkeypatch.setattr(control, "_same_file", lambda *_args: next(outcomes))

    with pytest.raises(control.RuntimeControlSecurityError):
        control._publish_document(target, _valid_document(), snapshot)
    assert not list(tmp_path.glob(".control.json.*.tmp"))


def test_publish_document_posix_hardening_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    target = tmp_path / "control.json"
    monkeypatch.setattr(
        control,
        "os",
        os_facade(control.os, name="posix", fchmod=lambda *_args: None),
    )
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(control, "_validate_regular_private_file", lambda *_args: None)
    monkeypatch.setattr(control, "_fsync_parent", lambda _path: None)

    control._publish_document(target, _valid_document(), ())

    assert json.loads(target.read_text(encoding="utf-8")) == _valid_document()


def test_setter_handles_missing_corrupt_and_failed_postcondition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "control.json"
    monkeypatch.setattr(control, "_control_lock", lambda *_args, **_kwargs: _NullLock())
    monkeypatch.setattr(
        control,
        "_read_existing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    monkeypatch.setattr(control, "_publish_document", lambda *_args, **_kwargs: None)
    with pytest.raises(FileNotFoundError):
        control.set_master_enabled(False, path=target)

    security_error = control.RuntimeControlSecurityError("corrupt")
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        control,
        "_read_existing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(security_error),
    )
    monkeypatch.setattr(control.os, "lstat", lambda _path: target.stat())
    with pytest.raises(control.RuntimeControlSecurityError, match="corrupt"):
        control.set_master_enabled(False, path=target)

    documents = iter([_valid_document(), _valid_document(enabled=False, generation=99)])
    monkeypatch.setattr(control, "_read_existing", lambda *_args, **_kwargs: next(documents))
    with pytest.raises(control.RuntimeControlSecurityError, match="postcondition"):
        control.set_master_enabled(True, path=target)


def test_materializer_handles_absent_corrupt_and_failed_postcondition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "control.json"
    document = _valid_document(enabled=True, generation=0)
    monkeypatch.setattr(control, "_control_lock", lambda *_args, **_kwargs: _NullLock())
    monkeypatch.setattr(control, "_publish_document", lambda *_args, **_kwargs: None)

    reads = iter([FileNotFoundError(), document])

    def _read_absent(*_args, **_kwargs):
        value = next(reads)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(control, "_read_existing", _read_absent)
    now = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    assert (
        control.ensure_runtime_control_materialized(
            path=target,
            source="test",
            now=now,
        )
        == document
    )

    security_error = control.RuntimeControlSecurityError("corrupt")
    monkeypatch.setattr(
        control,
        "_read_existing",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(security_error),
    )
    monkeypatch.setattr(control.os, "lstat", lambda _path: target.stat())
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(control.RuntimeControlSecurityError, match="corrupt"):
        control.ensure_runtime_control_materialized(path=target, source="test", now=now)

    reads = iter([FileNotFoundError(), _valid_document(enabled=False, generation=1)])
    monkeypatch.setattr(control, "_read_existing", _read_absent)
    with pytest.raises(control.RuntimeControlSecurityError, match="postcondition"):
        control.ensure_runtime_control_materialized(path=target, source="test", now=now)


def test_effective_reader_prefers_restricted_canonical_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "control.json"
    target.write_text("{}", encoding="utf-8")
    expected = _valid_document()
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(control, "_read_restricted_windows_control", lambda _path: expected)
    monkeypatch.setattr(
        control,
        "read_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("strict reader touched")),
    )

    assert control.read_effective_runtime_control(path=target) == expected
    assert control.master_enabled(path=target) is False


def test_effective_restricted_reader_defaults_only_a_missing_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "missing.json"
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)

    assert control.read_effective_runtime_control(path=target)["enabled"] is True

    monkeypatch.setattr(
        control.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(PermissionError("denied")),
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="could not be inspected"):
        control.read_effective_runtime_control(path=target)
    assert control.master_enabled(path=target) is True


def test_authoritative_default_reader_brokers_a_validated_master_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _valid_document(enabled=False, generation=9, source="dashboard")
    calls: list[str] = []
    monkeypatch.setattr(
        control,
        "read_effective_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            control.RuntimeControlSecurityError("restricted reader cannot prove the ACL")
        ),
    )
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)

    def broker(path: str, *, timeout: float) -> dict[str, Any]:
        calls.append(f"{path}:{timeout}")
        return {"master": expected}

    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        broker,
    )

    assert control.read_authoritative_runtime_control() == (expected, "dashboard")
    assert control.master_enabled() is False
    assert calls == ["/api/runtime:0.25", "/api/runtime:0.25"]


def test_authoritative_reader_forwards_uncached_direct_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _valid_document()
    calls: list[dict[str, Any]] = []

    def direct(**kwargs: Any) -> dict[str, Any]:
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(control, "read_effective_runtime_control", direct)

    assert control.read_authoritative_runtime_control(use_cache=False) == (expected, "direct")
    assert calls == [{"use_cache": False}]


@pytest.mark.parametrize("identity", ["path", "home_dir"])
def test_authoritative_reader_never_brokers_an_explicit_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity: str,
) -> None:
    direct_error = control.RuntimeControlSecurityError("custom identity is unreadable")
    monkeypatch.setattr(
        control,
        "read_effective_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(direct_error),
    )
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("explicit runtime identity was brokered")
        ),
    )
    arguments = (
        {"path": tmp_path / "control.json"} if identity == "path" else {"home_dir": tmp_path}
    )

    with pytest.raises(control.RuntimeControlSecurityError, match="custom identity"):
        control.read_authoritative_runtime_control(**arguments)
    assert control.master_enabled(**arguments) is True


@pytest.mark.parametrize(
    "direct_error",
    [
        control.RuntimeControlValidationError("corrupt control document"),
        control.RuntimeControlBusyError("control lock is busy"),
        control.RuntimeControlSecurityError("ordinary process cannot prove the path"),
    ],
)
def test_authoritative_reader_does_not_broker_normal_or_unproven_failures(
    monkeypatch: pytest.MonkeyPatch,
    direct_error: control.RuntimeControlError,
) -> None:
    restricted_checks: list[Path] = []
    monkeypatch.setattr(
        control,
        "read_effective_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(direct_error),
    )
    monkeypatch.setattr(
        control,
        "_restricted_windows_control_target",
        lambda path: restricted_checks.append(path) or False,
    )
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("ordinary runtime-control failure was brokered")
        ),
    )

    with pytest.raises(type(direct_error), match=str(direct_error)):
        control.read_authoritative_runtime_control()
    assert control.master_enabled() is True
    expected_checks = 2 if isinstance(direct_error, control.RuntimeControlSecurityError) else 0
    assert len(restricted_checks) == expected_checks


@pytest.mark.parametrize(
    "broker_result",
    [
        {"master": _valid_document(), "extra": True},
        {"master": {**_valid_document(), "enabled": "false"}},
        OSError("dashboard unavailable"),
    ],
)
def test_authoritative_reader_rejects_unavailable_or_malformed_brokerage(
    monkeypatch: pytest.MonkeyPatch,
    broker_result: object,
) -> None:
    monkeypatch.setattr(
        control,
        "read_effective_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            control.RuntimeControlSecurityError("restricted reader unavailable")
        ),
    )
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)

    def broker(_path: str, *, timeout: float) -> dict[str, Any]:
        assert timeout == 0.25
        if isinstance(broker_result, BaseException):
            raise broker_result
        return broker_result  # type: ignore[return-value]

    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        broker,
    )

    with pytest.raises(
        control.RuntimeControlSecurityError,
        match="authenticated dashboard service could not broker",
    ):
        control.read_authoritative_runtime_control()
    assert control.master_enabled() is True


def test_bound_enforcement_reader_uses_exact_uncached_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _control_path(tmp_path).resolve()
    expected = _valid_document(enabled=False, generation=12)
    calls: list[dict[str, Any]] = []

    def direct(**kwargs: Any) -> tuple[dict[str, Any], str]:
        calls.append(kwargs)
        return expected, "direct"

    monkeypatch.setattr(control, "read_authoritative_runtime_control", direct)

    assert control.read_bound_enforcement_runtime_control(target) == (expected, "direct")
    assert calls == [{"path": target, "use_cache": False}]


@pytest.mark.parametrize(
    "invalid_path",
    [".agency-runtime/run/control.json", "C:/tmp/not-control.json"],
)
def test_bound_enforcement_reader_rejects_untrusted_identity(
    invalid_path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        control,
        "read_authoritative_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("invalid identity reached the authoritative reader")
        ),
    )

    document, transport = control.read_bound_enforcement_runtime_control(invalid_path)

    assert document["enabled"] is True
    assert document["source"] == "fail-enabled"
    assert transport == "fail-enabled"


def test_bound_enforcement_reader_brokers_restricted_windows_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _control_path(tmp_path).resolve()
    expected = _valid_document(enabled=False, generation=13, source="dashboard")
    monkeypatch.setattr(
        control,
        "read_authoritative_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            control.RuntimeControlSecurityError("restricted token cannot inspect ACL")
        ),
    )
    monkeypatch.setattr(control.os, "name", "nt")
    monkeypatch.setattr(control, "current_process_token_is_restricted", lambda **_kwargs: True)
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        lambda path, *, timeout: (
            {"master": expected}
            if path == "/api/runtime" and timeout == 0.25
            else (_ for _ in ()).throw(AssertionError("unexpected broker request"))
        ),
    )

    assert control.read_bound_enforcement_runtime_control(target) == (expected, "dashboard")


@pytest.mark.parametrize("restricted", [False, True])
def test_bound_enforcement_reader_fails_enabled_without_valid_brokerage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    restricted: bool,
) -> None:
    target = _control_path(tmp_path).resolve()
    monkeypatch.setattr(
        control,
        "read_authoritative_runtime_control",
        lambda **_kwargs: (_ for _ in ()).throw(
            control.RuntimeControlSecurityError("direct read unavailable")
        ),
    )
    monkeypatch.setattr(control.os, "name", "nt")
    monkeypatch.setattr(
        control,
        "current_process_token_is_restricted",
        lambda **_kwargs: restricted,
    )
    monkeypatch.setattr(
        "agency_runtime.core.dashboard_runtime.dashboard_api_request",
        lambda *_args, **_kwargs: {"master": {**_valid_document(), "enabled": "false"}},
    )

    document, transport = control.read_bound_enforcement_runtime_control(target)

    assert document["enabled"] is True
    assert document["source"] == "fail-enabled"
    assert transport == "fail-enabled"


def test_restricted_windows_reader_proves_identity_and_non_forgeability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    target = _control_path(home)
    target.parent.mkdir(parents=True)
    _write_document(target, _valid_document())
    monkeypatch.setattr(control.Path, "home", lambda: home)
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(
        control,
        "current_process_has_control_forgery_access",
        lambda *_args, **_kwargs: False,
    )

    assert control._read_restricted_windows_control(target) == _valid_document()

    monkeypatch.setattr(
        control,
        "current_process_has_control_forgery_access",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="could not be proven"):
        control._read_restricted_windows_control(target)


def test_runtime_control_public_validator_and_restricted_target_probe(
    monkeypatch: pytest.MonkeyPatch,
    os_facade,
) -> None:
    assert control.validate_runtime_control_document(_valid_document()) == _valid_document()

    target = control.runtime_control_path()
    monkeypatch.setattr(control, "os", os_facade(control.os, name="nt"))
    monkeypatch.setattr(
        control,
        "current_process_token_is_restricted",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("probe failed")),
    )
    assert control._restricted_windows_control_target(target) is False


def test_restricted_windows_reader_rejects_unavailable_and_unstable_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    target = _control_path(home)
    target.parent.mkdir(parents=True)
    _write_document(target, _valid_document())
    monkeypatch.setattr(control.Path, "home", lambda: home)

    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: False)
    with pytest.raises(control.RuntimeControlSecurityError, match="reader is unavailable"):
        control._read_restricted_windows_control(target)

    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(
        control.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(PermissionError("denied")),
    )
    with pytest.raises(
        control.RuntimeControlSecurityError, match="identity could not be inspected"
    ):
        control._read_restricted_windows_control(target)

    monkeypatch.undo()
    monkeypatch.setattr(control.Path, "home", lambda: home)
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _metadata: True)
    with pytest.raises(control.RuntimeControlSecurityError, match="only real directories"):
        control._read_restricted_windows_control(target)

    monkeypatch.setattr(control, "metadata_is_link_or_reparse_point", lambda _metadata: False)
    target.unlink()
    target.mkdir()
    with pytest.raises(control.RuntimeControlSecurityError, match="one real regular file"):
        control._read_restricted_windows_control(target)


def test_restricted_windows_reader_covers_cache_io_and_identity_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    target = _control_path(home)
    target.parent.mkdir(parents=True)
    _write_document(target, _valid_document())
    monkeypatch.setattr(control.Path, "home", lambda: home)
    monkeypatch.setattr(control, "_restricted_windows_control_target", lambda _path: True)
    monkeypatch.setattr(
        control,
        "current_process_has_control_forgery_access",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(control, "_validate_directory_snapshot", lambda _snapshot: None)
    monkeypatch.setattr(control, "_cache_get", lambda *_args: _valid_document())
    assert control._read_restricted_windows_control(target) == _valid_document()

    identities = iter([(1,), (2,), (3,), (3,)])
    monkeypatch.setattr(control, "_metadata_identity", lambda _metadata: next(identities))
    monkeypatch.setattr(control, "_cache_put", lambda *_args: None)
    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: json.dumps(_valid_document()).encode(),
    )
    assert control._read_restricted_windows_control(target) == _valid_document()

    monkeypatch.setattr(control, "_cache_get", lambda *_args: None)
    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(control.FileSizeLimitError("too large")),
    )
    with pytest.raises(control.RuntimeControlValidationError, match="4 KiB"):
        control._read_restricted_windows_control(target)

    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(control.BoundedFileError("unreadable")),
    )
    with pytest.raises(control.RuntimeControlSecurityError, match="read safely"):
        control._read_restricted_windows_control(target)

    monkeypatch.setattr(
        control,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: json.dumps(_valid_document()).encode(),
    )
    identities = iter([(1,), (2,)])
    monkeypatch.setattr(control, "_metadata_identity", lambda _metadata: next(identities))
    with pytest.raises(control.RuntimeControlSecurityError, match="changed during read"):
        control._read_restricted_windows_control(target)


class _NullLock:
    def __enter__(self) -> tuple[tuple[Path, os.stat_result], ...]:
        return ()

    def __exit__(self, *_args: Any) -> None:
        return None
