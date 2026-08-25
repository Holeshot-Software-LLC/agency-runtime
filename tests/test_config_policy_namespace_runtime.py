"""Runtime config and policy namespace enforcement regressions."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from agency_runtime.core import config as config_module
from agency_runtime.core import configuration_persistence as persistence
from agency_runtime.core.configuration_contracts import ConfigurationError
from agency_runtime.core.selector import policy


def test_config_loader_checks_namespace_before_fresh_and_cached_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text("profile: standard\n", encoding="utf-8")
    config_module.load_config(config_path, reload=True)

    calls = 0

    def reject(_path: Path) -> None:
        nonlocal calls
        calls += 1
        raise ConfigurationError("configuration parent permits cross-account path substitution")

    monkeypatch.setattr(config_module, "assert_config_namespace", reject)

    with pytest.raises(ConfigurationError, match="cross-account"):
        config_module.load_config(config_path)
    assert calls == 1


def test_config_loader_rechecks_namespace_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text("profile: standard\n", encoding="utf-8")
    checks = 0

    def becomes_unsafe(_path: Path) -> None:
        nonlocal checks
        checks += 1
        if checks == 2:
            raise ConfigurationError("configuration parent permits cross-account path substitution")

    monkeypatch.setattr(config_module, "assert_config_namespace", becomes_unsafe)

    with pytest.raises(ConfigurationError, match="cross-account"):
        config_module.load_config(config_path, reload=True)
    assert checks == 2


def test_policy_loader_rejects_untrusted_namespace_before_cached_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("actions: {}\n", encoding="utf-8")
    policy_path.chmod(0o600)
    policy.load_policy(policy_path)

    monkeypatch.setattr(
        policy,
        "assert_config_namespace",
        lambda _path: (_ for _ in ()).throw(
            ConfigurationError("configuration parent permits cross-account path substitution")
        ),
    )

    with pytest.raises(policy.PolicyIdentityError, match="cross-account"):
        policy.load_policy(policy_path)


def test_missing_policy_uses_bundled_content_but_unsafe_appearance_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy_path = tmp_path / "policy.yaml"
    checks: list[Path] = []

    def reject(candidate: Path) -> None:
        checks.append(candidate)
        raise ConfigurationError("configuration parent permits cross-account path substitution")

    monkeypatch.setattr(policy, "assert_config_namespace", reject)
    monkeypatch.setattr(policy, "_BUNDLED_COMPANION_POLICY", {"actions": {}})

    assert policy.load_policy(policy_path) == {"actions": {}}
    assert checks == []

    policy_path.write_text("actions: {}\n", encoding="utf-8")
    policy_path.chmod(0o600)
    with pytest.raises(policy.PolicyIdentityError, match="cross-account"):
        policy.load_policy(policy_path)
    assert checks == [policy_path]


def test_config_parent_uses_private_host_capability_for_missing_descendant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "missing" / "nested" / "agency.yaml"
    checks = 0
    created: list[Path] = []

    def namespace_check(_path: Path, **_kwargs: object) -> None:
        nonlocal checks
        checks += 1
        if checks == 1:
            raise ConfigurationError("configuration parent permits cross-account path substitution")

    monkeypatch.setattr(persistence, "assert_config_namespace", namespace_check)
    monkeypatch.setattr(persistence, "private_path_authority_covers", lambda _path: False)
    monkeypatch.setattr(persistence, "is_link_or_reparse_point", lambda _path: False)
    monkeypatch.setattr(
        "agency_runtime.core.private_paths.ensure_private_directory",
        lambda path: created.append(path) or path.mkdir(parents=True) or path,
    )

    persistence.ensure_config_parent(
        target,
        path_check=lambda _path: False,
        is_windows=True,
    )

    assert created == [target.parent]
    assert checks == 3


def test_config_parent_creates_nested_components_privately_under_permissive_umask(
    tmp_path: Path,
) -> None:
    tmp_path.chmod(0o700)
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir(mode=0o700)
    target = (
        runtime_home
        / "openclaw"
        / "config-identities"
        / ("a" * 64)
        / "final-only-streaming-backup.yaml"
    )

    previous_umask = os.umask(0o002)
    try:
        persistence.ensure_config_parent(target, is_windows=False)
    finally:
        os.umask(previous_umask)

    for candidate in (
        runtime_home / "openclaw",
        runtime_home / "openclaw" / "config-identities",
        target.parent,
    ):
        assert stat.S_IMODE(os.lstat(candidate).st_mode) == 0o700


def test_config_parent_does_not_use_capability_fallback_on_posix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "missing" / "agency.yaml"
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ConfigurationError("configuration parent permits cross-account path substitution")
        ),
    )

    with pytest.raises(ConfigurationError, match="cross-account"):
        persistence.ensure_config_parent(
            target,
            path_check=lambda _path: False,
            is_windows=False,
        )


@pytest.mark.parametrize("failure", [FileNotFoundError(), OSError("identity denied")])
def test_config_parent_private_authority_fails_closed_on_creation_and_probe_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: OSError,
) -> None:
    target = tmp_path / "missing" / "agency.yaml"
    monkeypatch.setattr(persistence, "private_path_authority_covers", lambda _path: True)
    monkeypatch.setattr(
        persistence.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(failure),
    )
    monkeypatch.setattr(
        "agency_runtime.core.private_paths.ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("creation denied")),
    )

    message = "cross-account" if isinstance(failure, FileNotFoundError) else "identity"
    with pytest.raises(ConfigurationError, match=message):
        persistence.ensure_config_parent(
            target,
            path_check=lambda _path: False,
            is_windows=True,
        )


def test_config_parent_capability_fallback_wraps_private_creation_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "missing" / "agency.yaml"
    monkeypatch.setattr(persistence, "private_path_authority_covers", lambda _path: False)
    monkeypatch.setattr(
        persistence,
        "assert_config_namespace",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ConfigurationError("untrusted")),
    )
    monkeypatch.setattr(
        "agency_runtime.core.private_paths.ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(OSError("creation denied")),
    )

    with pytest.raises(ConfigurationError, match="cross-account"):
        persistence.ensure_config_parent(
            target,
            path_check=lambda _path: False,
            is_windows=True,
        )
