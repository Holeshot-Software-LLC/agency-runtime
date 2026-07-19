"""Custom companion-policy ownership, identity, and race regressions."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.selector import policy


def _metadata(
    *,
    mode: int = stat.S_IFREG | 0o600,
    inode: int = 7,
    links: int = 1,
    uid: int = 41,
    attributes: int = 0,
    mtime_ns: int = 10,
    ctime_ns: int = 11,
) -> SimpleNamespace:
    return SimpleNamespace(
        st_dev=3,
        st_ino=inode,
        st_mode=mode,
        st_size=12,
        st_mtime_ns=mtime_ns,
        st_ctime_ns=ctime_ns,
        st_nlink=links,
        st_uid=uid,
        st_file_attributes=attributes,
    )


def _write_private_policy(path: Path, payload: str = "actions: {}\n") -> None:
    path.write_text(payload, encoding="utf-8")
    path.chmod(0o600)


@pytest.mark.parametrize("mode", [0o400, 0o600, 0o640, 0o644])
def test_posix_policy_metadata_accepts_non_writable_owner_read_modes(mode: int) -> None:
    policy._assert_trusted_policy_metadata(
        _metadata(mode=stat.S_IFREG | mode),
        is_windows=False,
        effective_uid=41,
    )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (_metadata(mode=stat.S_IFDIR | 0o700), "regular non-link"),
        (_metadata(attributes=0x400), "regular non-link"),
        (_metadata(inode=0), "identity is unavailable"),
        (_metadata(links=2), "exactly one hard link"),
        (_metadata(uid=42), "owned by the current user"),
        (_metadata(mode=stat.S_IFREG | 0o200), "owner-readable"),
        (_metadata(mode=stat.S_IFREG | 0o660), "owner-readable"),
        (_metadata(mode=stat.S_IFREG | 0o602), "owner-readable"),
    ],
)
def test_posix_policy_metadata_rejects_unsafe_shapes(
    metadata: SimpleNamespace,
    message: str,
) -> None:
    with pytest.raises(policy.PolicyIdentityError, match=message):
        policy._assert_trusted_policy_metadata(
            metadata,
            is_windows=False,
            effective_uid=41,
        )


def test_windows_metadata_uses_acl_for_ownership_and_permissions() -> None:
    metadata = _metadata(mode=stat.S_IFREG | 0o666, uid=999)
    policy._assert_trusted_policy_metadata(metadata, is_windows=True)
    assert policy._metadata_identity(metadata, is_windows=True)[5] == 0
    assert policy._metadata_identity(metadata, is_windows=False)[5] == metadata.st_ctime_ns


def test_windows_policy_owner_contract_accepts_only_exact_current_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = "S-1-5-21-1-2-3-1001"
    sddl = f"O:{current}D:P(A;;FA;;;{current})(A;;FR;;;BU)"
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(policy, "read_windows_sddl", lambda _path: sddl)
    monkeypatch.setattr(policy, "current_process_user_sid", lambda **_kwargs: current)

    def mutation_probe(_path: Path, **kwargs: Any) -> bool:
        calls.append(kwargs)
        assert kwargs["sddl_reader"](Path("same-snapshot")) == sddl
        assert kwargs["current_sid_reader"]() == current
        assert "trusted_sid_reader" not in kwargs
        return True

    monkeypatch.setattr(policy, "windows_file_prevents_untrusted_mutation", mutation_probe)

    assert policy._windows_policy_file_is_trusted(Path("policy.yaml"))
    assert calls and calls[0]["is_windows"] is True


@pytest.mark.parametrize("owner", ["SY", "BA", "S-1-5-80-956008885-1"])
def test_windows_policy_rejects_os_and_foreign_owners(
    owner: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = "S-1-5-21-1-2-3-1001"
    monkeypatch.setattr(
        policy,
        "read_windows_sddl",
        lambda _path: f"O:{owner}D:P(A;;FA;;;{owner})",
    )
    monkeypatch.setattr(policy, "current_process_user_sid", lambda **_kwargs: current)
    monkeypatch.setattr(
        policy,
        "windows_file_prevents_untrusted_mutation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("foreign owner must fail before mutation analysis")
        ),
    )

    assert not policy._windows_policy_file_is_trusted(Path("policy.yaml"))


def test_windows_policy_owner_or_dacl_probe_failure_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = "S-1-5-21-1-2-3-1001"
    monkeypatch.setattr(
        policy,
        "read_windows_sddl",
        lambda _path: (_ for _ in ()).throw(OSError("denied")),
    )
    assert not policy._windows_policy_file_is_trusted(Path("policy.yaml"))

    monkeypatch.setattr(policy, "read_windows_sddl", lambda _path: "D:P(A;;FR;;;BU)")
    monkeypatch.setattr(policy, "current_process_user_sid", lambda **_kwargs: current)
    monkeypatch.setattr(
        policy,
        "windows_file_prevents_untrusted_mutation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("missing owner must fail before mutation analysis")
        ),
    )
    assert not policy._windows_policy_file_is_trusted(Path("policy.yaml"))

    monkeypatch.setattr(
        policy,
        "read_windows_sddl",
        lambda _path: f"O:{current}D:P(A;;FA;;;{current})",
    )
    monkeypatch.setattr(policy, "current_process_user_sid", lambda **_kwargs: current)
    monkeypatch.setattr(
        policy,
        "windows_file_prevents_untrusted_mutation",
        lambda *_args, **_kwargs: False,
    )
    assert not policy._windows_policy_file_is_trusted(Path("policy.yaml"))


def test_policy_rejects_hard_link_before_read(tmp_path: Path) -> None:
    source = tmp_path / "policy.yaml"
    linked = tmp_path / "linked.yaml"
    _write_private_policy(source)
    try:
        os.link(source, linked)
    except OSError as exc:
        pytest.skip(f"hard-link creation unavailable: {exc}")

    with pytest.raises(policy.PolicyIdentityError, match="exactly one hard link"):
        policy.load_policy(source)


def test_windows_dacl_degradation_blocks_cached_policy_without_content_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    _write_private_policy(path)
    monkeypatch.setattr(policy, "_platform_is_windows", lambda: True)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    monkeypatch.setattr(policy, "assert_config_namespace", lambda _path: None)
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)

    loaded = policy.load_policy(path)
    unchanged_mtime = path.stat().st_mtime_ns
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: False)

    with pytest.raises(policy.PolicyIdentityError, match="DACL"):
        policy.load_policy(path)
    assert path.stat().st_mtime_ns == unchanged_mtime
    assert loaded == {"actions": {}}


@pytest.mark.skipif(os.name == "nt", reason="POSIX ownership and mode contract")
def test_posix_mode_degradation_blocks_cached_policy_without_mtime_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    _write_private_policy(path)
    monkeypatch.setattr(policy, "assert_config_namespace", lambda _path: None)
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    policy.load_policy(path)
    unchanged_mtime = path.stat().st_mtime_ns

    path.chmod(0o660)

    with pytest.raises(policy.PolicyIdentityError, match="owner-readable"):
        policy.load_policy(path)
    assert path.stat().st_mtime_ns == unchanged_mtime


def test_custom_policy_read_rejects_descriptor_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    _write_private_policy(path)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    original_fstat = policy.os.fstat
    calls = 0

    def changing_fstat(descriptor: int) -> Any:
        nonlocal calls
        calls += 1
        metadata = original_fstat(descriptor)
        if calls == 1:
            return metadata
        return SimpleNamespace(
            st_dev=metadata.st_dev,
            st_ino=metadata.st_ino,
            st_mode=metadata.st_mode,
            st_size=metadata.st_size,
            st_mtime_ns=metadata.st_mtime_ns + 1,
            st_ctime_ns=metadata.st_ctime_ns,
            st_nlink=metadata.st_nlink,
            st_uid=metadata.st_uid,
            st_file_attributes=getattr(metadata, "st_file_attributes", 0),
        )

    monkeypatch.setattr(policy.os, "fstat", changing_fstat)

    with pytest.raises(policy.PolicyIdentityError, match="changed during read"):
        policy._read_trusted_custom_policy(path, limit=1024)


def test_custom_policy_read_rejects_disappearance_and_open_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    _write_private_policy(path)
    monkeypatch.setattr(policy, "_policy_file_identity", lambda _path: None)
    with pytest.raises(policy.PolicyIdentityError, match="disappeared before read"):
        policy._read_trusted_custom_policy(path, limit=1024)

    monkeypatch.setattr(policy, "_policy_file_identity", lambda _path: (1,) * 8)
    monkeypatch.setattr(
        policy.os,
        "open",
        lambda *_args: (_ for _ in ()).throw(OSError("denied")),
    )
    with pytest.raises(policy.PolicyIdentityError, match="opened safely"):
        policy._read_trusted_custom_policy(path, limit=1024)


def test_custom_policy_read_rejects_path_swap_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    _write_private_policy(path)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    identity = policy._policy_file_identity(path)
    assert identity is not None
    changed = (*identity[:4], identity[4] + 1, *identity[5:])
    identities = iter((identity, changed))
    monkeypatch.setattr(policy, "_policy_file_identity", lambda _path: next(identities))

    with pytest.raises(policy.PolicyIdentityError, match="changed during open"):
        policy._read_trusted_custom_policy(path, limit=1024)


def test_custom_policy_read_rejects_growth_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    path.write_bytes(b"x")
    path.chmod(0o600)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    monkeypatch.setattr(policy.os, "read", lambda _descriptor, _size: b"xy")

    with pytest.raises(OSError, match="size limit"):
        policy._read_trusted_custom_policy(path, limit=1)


def test_custom_policy_read_rejects_path_swap_after_descriptor_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    _write_private_policy(path)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    identity = policy._policy_file_identity(path)
    assert identity is not None
    changed = (*identity[:4], identity[4] + 1, *identity[5:])
    identities = iter((identity, identity, changed))
    monkeypatch.setattr(policy, "_policy_file_identity", lambda _path: next(identities))

    with pytest.raises(policy.PolicyIdentityError, match="changed during read"):
        policy._read_trusted_custom_policy(path, limit=1024)


def test_policy_identity_rejects_failure_and_change_after_acl_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = _metadata(mode=stat.S_IFDIR | 0o700)
    target = _metadata()
    calls = iter((parent, target, OSError("replaced")))

    def failing_lstat(_path: Path) -> Any:
        result = next(calls)
        if isinstance(result, OSError):
            raise result
        return result

    monkeypatch.setattr(policy.os, "lstat", failing_lstat)
    monkeypatch.setattr(policy, "_platform_is_windows", lambda: False)
    monkeypatch.setattr(policy.os, "geteuid", lambda: 41, raising=False)
    with pytest.raises(policy.PolicyIdentityError, match="security validation"):
        policy._policy_file_identity(Path("policy.yaml"))

    changed = _metadata(mtime_ns=12)
    calls = iter((parent, target, changed))
    monkeypatch.setattr(policy.os, "lstat", lambda _path: next(calls))
    with pytest.raises(policy.PolicyIdentityError, match="security validation"):
        policy._policy_file_identity(Path("policy.yaml"))


def test_missing_policy_fast_path_never_probes_acl_or_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = tmp_path / "missing.yaml"
    monkeypatch.setattr(policy, "_platform_is_windows", lambda: True)
    monkeypatch.setattr(
        policy,
        "_windows_policy_file_is_trusted",
        lambda _path: (_ for _ in ()).throw(AssertionError("unexpected DACL probe")),
    )
    monkeypatch.setattr(
        policy,
        "assert_config_namespace",
        lambda _path: (_ for _ in ()).throw(AssertionError("unexpected namespace probe")),
    )
    monkeypatch.setattr(policy, "_BUNDLED_COMPANION_POLICY", {"actions": {}})

    assert policy.load_policy(missing) == {"actions": {}}
    assert policy.load_policy(missing) == {"actions": {}}


def test_implicit_missing_policy_creation_bypasses_freshness_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    monkeypatch.setattr(policy, "_resolve_policy_path", lambda: path)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    monkeypatch.setattr(policy, "assert_config_namespace", lambda _path: None)
    monkeypatch.setattr(policy, "_BUNDLED_COMPANION_POLICY", {"actions": {"BUNDLED": {}}})
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    monkeypatch.setattr(policy, "_POLICY_REQUEST_KEY", "")
    monkeypatch.setattr(policy, "_POLICY_CHECKED_AT", 0.0)

    assert set(policy.load_policy()["actions"]) == {"BUNDLED"}
    _write_private_policy(path, "actions:\n  CREATED: {}\n")

    assert set(policy.load_policy()["actions"]) == {"CREATED"}


def test_implicit_present_policy_replacement_reloads_within_freshness_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.yaml"
    replacement = tmp_path / "replacement.yaml"
    _write_private_policy(path, "actions:\n  FIRST: {}\n")
    monkeypatch.setattr(policy, "_resolve_policy_path", lambda: path)
    monkeypatch.setattr(policy, "_windows_policy_file_is_trusted", lambda _path: True)
    monkeypatch.setattr(policy, "assert_config_namespace", lambda _path: None)
    monkeypatch.setattr(policy, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy, "_POLICY_FILE_IDENTITY", None)
    monkeypatch.setattr(policy, "_POLICY_PATH", None)
    monkeypatch.setattr(policy, "_POLICY_REQUEST_KEY", "")
    monkeypatch.setattr(policy, "_POLICY_CHECKED_AT", 0.0)

    assert set(policy.load_policy()["actions"]) == {"FIRST"}
    _write_private_policy(replacement, "actions:\n  SECOND: {}\n")
    os.replace(replacement, path)

    second = policy.load_policy()
    assert set(second["actions"]) == {"SECOND"}
    assert policy.load_policy() is second
