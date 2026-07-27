"""Security and transaction coverage for dashboard ownership manifests."""

from __future__ import annotations

import json
import os
import stat
from types import SimpleNamespace

import pytest

from agency_runtime.core import dashboard_service_core as core
from agency_runtime.core import dashboard_service_manifest as subject


def context(tmp_path, platform="linux"):
    result = core._context(
        home_dir=tmp_path,
        platform_name=platform,
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert result is not None
    return result


def test_runtime_fingerprint_manifest_and_current_contract(tmp_path):
    ctx = context(tmp_path)
    value = subject._manifest_value(ctx)
    assert value["runtime_fingerprint"] == subject._runtime_fingerprint(ctx)
    assert subject._manifest_owned(ctx, value)
    assert subject._manifest_current(ctx, value)
    for key, invalid in (
        ("schema_version", True),
        ("schema_version", 3),
        ("owner", "other"),
        ("service", "other"),
        ("platform", "windows"),
        ("manager", "other"),
        ("registration", "other"),
    ):
        changed = {**value, key: invalid}
        assert not subject._manifest_owned(ctx, changed)
    legacy = {**value, "schema_version": 1}
    assert subject._manifest_owned(ctx, legacy)
    assert not subject._manifest_current(ctx, legacy)
    for key, invalid in (
        ("worker_argv", []),
        ("config_path", "other"),
        ("package_version", "0"),
        ("runtime_fingerprint", "sha256:bad"),
    ):
        assert not subject._manifest_current(ctx, {**value, key: invalid})
    assert not subject._manifest_owned(ctx, None)
    assert not subject._manifest_current(ctx, None)


def test_path_presence_missing_error_and_present(tmp_path, monkeypatch):
    path = tmp_path / "state"
    assert not subject._path_present(path)
    path.write_text("value", encoding="utf-8")
    assert subject._path_present(path)
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(OSError("indeterminate")),
    )
    assert subject._path_present(path)


def test_link_like_accepts_reconstructed_none_attributes_and_detects_reparse():
    regular = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=None)
    assert subject._link_like(regular) is False
    reparse = SimpleNamespace(
        st_mode=stat.S_IFREG,
        st_file_attributes=int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)),
    )
    assert subject._link_like(reparse) is True
    symbolic = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
    assert subject._link_like(symbolic) is True


def test_same_file_compares_identity_and_mode():
    first = SimpleNamespace(st_dev=1, st_ino=2, st_mode=3)
    assert subject._same_file(first, SimpleNamespace(st_dev=1, st_ino=2, st_mode=3))
    assert not subject._same_file(first, SimpleNamespace(st_dev=1, st_ino=9, st_mode=3))
    assert not subject._same_file(first, SimpleNamespace(st_dev=1, st_ino=2, st_mode=4))
    assert subject._same_file(
        SimpleNamespace(st_dev=1, st_ino=0, st_mode=3),
        SimpleNamespace(st_dev=1, st_ino=0, st_mode=3),
    )


def test_bounded_file_normal_oversize_special_and_changed(tmp_path, monkeypatch):
    path = tmp_path / "value"
    path.write_bytes(b"abc")
    assert subject._read_bounded_file(path, limit=3, label="value") == b"abc"
    with pytest.raises(OSError, match="size limit"):
        subject._read_bounded_file(path, limit=2, label="value")

    actual_lstat = subject.os.lstat
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_size=0,
            st_dev=1,
            st_ino=1,
            st_file_attributes=0,
        ),
    )
    with pytest.raises(OSError, match="regular file"):
        subject._read_bounded_file(path, limit=3, label="value")
    monkeypatch.setattr(subject.os, "lstat", actual_lstat)
    monkeypatch.setattr(subject, "_same_file", lambda *_args: False)
    with pytest.raises(OSError, match="changed while it was opened"):
        subject._read_bounded_file(path, limit=3, label="value")


def test_bounded_file_rejects_growth_after_open(tmp_path, monkeypatch):
    path = tmp_path / "value"
    path.write_bytes(b"abc")
    before = os.lstat(path)
    monkeypatch.setattr(subject.os, "lstat", lambda _path: before)
    real_fdopen = subject.os.fdopen

    class GrowingStream:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _limit):
            return b"abcd"

    monkeypatch.setattr(subject.os, "fdopen", lambda *_a, **_kw: GrowingStream())
    with pytest.raises(OSError, match="size limit"):
        subject._read_bounded_file(path, limit=3, label="value")
    monkeypatch.setattr(subject.os, "fdopen", real_fdopen)


def test_decode_file_match_and_manifest_reading(tmp_path, monkeypatch):
    assert subject._decode_service_file(b"one\r\ntwo\rthree") == "one\ntwo\nthree"
    path = tmp_path / "value"
    assert subject._file_matches(path, None)
    path.write_bytes(b"content")
    assert not subject._file_matches(path, None)
    assert subject._file_matches(path, b"content")
    assert not subject._file_matches(path, b"other")

    ctx = context(tmp_path)
    assert subject._read_manifest_bytes(ctx) is None
    ctx.manifest_path.parent.mkdir(parents=True)
    ctx.manifest_path.write_text("[]", encoding="utf-8")
    assert subject._read_manifest(ctx) is None
    ctx.manifest_path.write_text("not-json", encoding="utf-8")
    assert subject._read_manifest(ctx) is None
    value = subject._manifest_value(ctx)
    ctx.manifest_path.write_text(json.dumps(value), encoding="utf-8")
    assert subject._read_manifest(ctx) == value
    monkeypatch.setattr(
        subject,
        "_assert_real_directory_chain",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("unsafe")),
    )
    assert subject._read_manifest(ctx) is None


def test_replaceable_and_directory_chain_safety(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    subject._assert_replaceable(missing, label="value")
    path = tmp_path / "file"
    path.write_text("value", encoding="utf-8")
    subject._assert_replaceable(path, label="value")
    with pytest.raises(OSError, match="escaped"):
        subject._assert_real_directory_chain(tmp_path.parent, anchor=tmp_path)
    subject._assert_real_directory_chain(tmp_path / "future" / "child", anchor=tmp_path)
    real_lstat = subject.os.lstat
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0),
    )
    with pytest.raises(OSError, match="home must be a real directory"):
        subject._assert_real_directory_chain(tmp_path / "file", anchor=tmp_path)
    monkeypatch.setattr(subject.os, "lstat", real_lstat)


def test_prepare_parent_atomic_write_restore_and_unlink(tmp_path):
    path = tmp_path / "private" / "state"
    subject._prepare_private_parent(path, trusted_root=tmp_path)
    assert path.parent.is_dir()
    subject._atomic_write(path, "first", trusted_root=tmp_path)
    assert path.read_text(encoding="utf-8") == "first"
    subject._atomic_write(path, "second", trusted_root=tmp_path)
    assert path.read_text(encoding="utf-8") == "second"
    assert subject._safe_unlink(path)
    assert not subject._safe_unlink(path, missing_ok=True)
    with pytest.raises(FileNotFoundError):
        subject._safe_unlink(path)
    subject._restore_file(path, b"restored")
    assert path.read_bytes() == b"restored"
    subject._restore_file(path, None)
    assert not path.exists()


def test_safe_unlink_rejects_special_file(tmp_path, monkeypatch):
    path = tmp_path / "value"
    path.write_text("value", encoding="utf-8")
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0),
    )
    with pytest.raises(OSError, match="linked or special"):
        subject._safe_unlink(path)


@pytest.mark.parametrize("timeout", [True, -1, 301, float("nan"), "1"])
def test_service_lock_rejects_invalid_timeout(tmp_path, timeout):
    with (
        pytest.raises(ValueError, match="lock timeout"),
        subject._service_lock(context(tmp_path), timeout=timeout),
    ):
        pass


def test_service_lock_serializes_and_releases(tmp_path):
    ctx = context(tmp_path)
    with subject._service_lock(ctx, timeout=1):
        assert ctx.manifest_path.parent.joinpath(".dashboard-service.lock").exists()


def test_write_manifest_new_current_and_invalid_existing(tmp_path):
    ctx = context(tmp_path)
    assert subject._write_manifest(ctx)
    assert not subject._write_manifest(ctx)
    ctx.manifest_path.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid dashboard service ownership"):
        subject._write_manifest(ctx)
