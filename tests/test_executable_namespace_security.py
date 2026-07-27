"""Cross-account executable namespace and service-manager launch regressions."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import dashboard_service_core, executable_namespace, process_argv
from agency_runtime.core.delegation import backends


def _directory(*, owner: int, permissions: int = 0o755, attributes: int = 0) -> Any:
    return SimpleNamespace(
        st_mode=stat.S_IFDIR | permissions,
        st_uid=owner,
        st_file_attributes=attributes,
    )


def _file(*, owner: int, permissions: int = 0o755) -> Any:
    return SimpleNamespace(st_mode=stat.S_IFREG | permissions, st_uid=owner)


def _install_chain(
    monkeypatch: pytest.MonkeyPatch,
    final: Path,
    metadata: tuple[Any, ...],
) -> tuple[Path, ...]:
    normalized = executable_namespace._absolute_path(final)
    candidates = tuple(Path(f"namespace-component-{index}") for index in range(len(metadata) - 1))
    candidates = (*candidates, normalized)
    observed = dict(zip(candidates, metadata, strict=True))
    monkeypatch.setattr(executable_namespace, "_directory_chain", lambda _path: candidates)
    monkeypatch.setattr(executable_namespace.os, "lstat", lambda path: observed[path])
    return candidates


def _write_tool(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"trusted executable")
    if os.name != "nt":
        path.chmod(0o700)
    return path


def test_posix_tmp_agency_bin_style_writable_final_parent_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "tmp" / "agency-bin"
    _install_chain(
        monkeypatch,
        parent,
        (
            _directory(owner=0),
            _directory(owner=0, permissions=0o1777),
            _directory(owner=1000, permissions=0o777),
        ),
    )

    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: False,
    )


@pytest.mark.parametrize(
    ("label", "metadata"),
    [
        (
            "root-owned /usr/bin",
            (_directory(owner=0), _directory(owner=0), _directory(owner=0)),
        ),
        (
            "current-user private bin",
            (
                _directory(owner=0),
                _directory(owner=0),
                _directory(owner=1000),
                _directory(owner=1000, permissions=0o700),
            ),
        ),
        (
            "sticky shared ancestor",
            (
                _directory(owner=0),
                _directory(owner=0, permissions=0o1777),
                _directory(owner=1000, permissions=0o700),
            ),
        ),
    ],
)
def test_posix_trusted_system_user_and_sticky_paths_are_accepted(
    label: str,
    metadata: tuple[Any, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del label
    parent = tmp_path / "trusted-bin"
    _install_chain(monkeypatch, parent, metadata)

    assert executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: False,
    )


@pytest.mark.parametrize(
    "metadata",
    [
        (_directory(owner=0), _directory(owner=2000)),
        (_directory(owner=0, permissions=0o777), _directory(owner=1000, permissions=0o700)),
        (_directory(owner=0), SimpleNamespace(st_mode=stat.S_IFREG | 0o700, st_uid=1000)),
        (
            _directory(owner=0),
            _directory(owner=1000, attributes=0x400),
        ),
        (
            _directory(owner=0),
            SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_uid=1000, st_file_attributes=0),
        ),
    ],
)
def test_posix_rejects_foreign_writable_nondirectory_link_and_reparse_chains(
    metadata: tuple[Any, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "unsafe-bin"
    _install_chain(monkeypatch, parent, metadata)

    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: False,
    )


def test_posix_default_acl_and_unknown_identity_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "bin"
    _install_chain(monkeypatch, parent, (_directory(owner=0), _directory(owner=1000)))
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: True,
    )
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: (_ for _ in ()).throw(OSError("ACL probe failed")),
    )
    monkeypatch.setattr(executable_namespace.os, "geteuid", None, raising=False)
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        default_acl_probe=lambda _path: False,
    )


def test_posix_default_acl_probe_classifies_supported_absent_and_unknown_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(executable_namespace.os, "getxattr", None, raising=False)
    assert not executable_namespace.posix_directory_has_default_acl(tmp_path)
    monkeypatch.setattr(
        executable_namespace.os,
        "getxattr",
        lambda *_args, **_kwargs: b"default-acl",
        raising=False,
    )
    assert executable_namespace.posix_directory_has_default_acl(tmp_path)

    def absent(*_args: Any, **_kwargs: Any) -> bytes:
        raise OSError(errno.ENODATA, "absent")

    monkeypatch.setattr(executable_namespace.os, "getxattr", absent, raising=False)
    assert not executable_namespace.posix_directory_has_default_acl(tmp_path)

    def unknown(*_args: Any, **_kwargs: Any) -> bytes:
        raise OSError(errno.EACCES, "denied")

    monkeypatch.setattr(executable_namespace.os, "getxattr", unknown, raising=False)
    assert executable_namespace.posix_directory_has_default_acl(tmp_path)


def test_namespace_missing_empty_and_invalid_chains_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        executable_namespace.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(OSError("missing")),
    )
    assert not executable_namespace.executable_namespace_is_trusted(
        tmp_path,
        is_windows=False,
        effective_uid=1000,
    )
    monkeypatch.setattr(executable_namespace, "_directory_chain", lambda _path: ())
    assert not executable_namespace.executable_namespace_is_trusted(
        tmp_path,
        is_windows=False,
        effective_uid=1000,
    )


def test_windows_probe_checks_every_component_and_treats_final_as_write_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "Windows" / "System32"
    candidates = _install_chain(
        monkeypatch,
        parent,
        (_directory(owner=0), _directory(owner=0), _directory(owner=0)),
    )
    calls: list[tuple[Path, bool]] = []

    def probe(path: Path, final_parent: bool) -> bool:
        calls.append((path, final_parent))
        return True

    assert executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=True,
        windows_acl_probe=probe,
    )
    assert calls == [
        (candidates[0], False),
        (candidates[1], False),
        (candidates[2], True),
    ]


def test_windows_default_dacl_primitive_uses_prospective_final_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "trusted"
    candidates = _install_chain(
        monkeypatch,
        parent,
        (_directory(owner=0), _directory(owner=0)),
    )
    calls: list[tuple[Path, dict[str, Any]]] = []

    def probe(path: Path, **kwargs: Any) -> bool:
        calls.append((path, kwargs))
        return True

    monkeypatch.setattr(
        executable_namespace,
        "windows_directory_prevents_untrusted_writes",
        probe,
    )
    assert executable_namespace.executable_namespace_is_trusted(parent, is_windows=True)
    assert [path for path, _kwargs in calls] == list(candidates)
    assert calls[0][1]["prospective_child"] is False
    assert calls[-1][1]["prospective_child"] is True
    assert calls[-1][1]["allow_inheritable_read"] is True
    assert all(kwargs["final_parent"] is False for _path, kwargs in calls)


def test_windows_probe_rejection_and_failure_are_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "bin"
    _install_chain(monkeypatch, parent, (_directory(owner=0), _directory(owner=0)))
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=True,
        windows_acl_probe=lambda _path, final: not final,
    )
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=True,
        windows_acl_probe=lambda *_args: (_ for _ in ()).throw(OSError("DACL failed")),
    )


def test_posix_permission_change_invalidates_a_previously_trusted_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "bin"
    candidates = _install_chain(
        monkeypatch,
        parent,
        (_directory(owner=0), _directory(owner=1000, permissions=0o700)),
    )
    assert executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: False,
    )
    metadata = {
        candidates[0]: _directory(owner=0),
        candidates[1]: _directory(owner=1000, permissions=0o770),
    }
    monkeypatch.setattr(executable_namespace.os, "lstat", lambda path: metadata[path])
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=False,
        effective_uid=1000,
        default_acl_probe=lambda _path: False,
    )


def test_windows_acl_change_invalidates_a_previously_trusted_namespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "bin"
    _install_chain(monkeypatch, parent, (_directory(owner=0), _directory(owner=0)))
    state = {"trusted": True}

    def probe(_path: Path, _final: bool) -> bool:
        return state["trusted"]

    assert executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=True,
        windows_acl_probe=probe,
    )
    state["trusted"] = False
    assert not executable_namespace.executable_namespace_is_trusted(
        parent,
        is_windows=True,
        windows_acl_probe=probe,
    )


def test_executable_namespace_assertion_accepts_trusted_and_rejects_unsafe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "bin" / "agent"
    outcomes = iter((True, False))
    monkeypatch.setattr(
        executable_namespace,
        "executable_namespace_is_trusted",
        lambda *_args, **_kwargs: next(outcomes),
    )
    executable_namespace.assert_executable_namespace(executable, is_windows=False)
    with pytest.raises(PermissionError, match="cross-account substitution"):
        executable_namespace.assert_executable_namespace(executable, is_windows=False)


def test_permission_and_acl_changes_between_freeze_and_revalidation_are_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / ("agent.exe" if os.name == "nt" else "agent"))
    prepared = process_argv.prepare_process_argv([str(executable)])
    validations: list[tuple[str, bool]] = []

    def validate(path: str | Path, *, is_windows: bool) -> None:
        validations.append((str(path), is_windows))
        if len(validations) > 1:
            raise PermissionError("executable parent namespace permits cross-account substitution")

    monkeypatch.setattr(process_argv, "assert_executable_namespace", validate)
    process_argv.freeze_process_argv(prepared)
    with pytest.raises(PermissionError, match="cross-account substitution"):
        process_argv.revalidate_process_argv(prepared)
    assert len(validations) == 2


def test_posix_executable_artifact_rejects_shared_writes_and_access_acl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_argv.os, "geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr(process_argv, "_posix_file_has_access_acl", lambda _path: False)
    with pytest.raises(PermissionError, match="group or other writes"):
        process_argv._assert_executable_artifact_trusted(
            "/trusted/tool",
            _file(owner=1000, permissions=0o770),
            platform_name="posix",
        )

    monkeypatch.setattr(process_argv, "_posix_file_has_access_acl", lambda _path: True)
    with pytest.raises(PermissionError, match="access ACL"):
        process_argv._assert_executable_artifact_trusted(
            "/trusted/tool",
            _file(owner=1000, permissions=0o700),
            platform_name="posix",
        )


def test_windows_executable_artifact_requires_a_trusted_file_dacl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        process_argv,
        "windows_file_prevents_untrusted_mutation",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(PermissionError, match="cross-account mutation"):
        process_argv._assert_executable_artifact_trusted(
            r"C:\trusted\tool.exe",
            _file(owner=0),
            platform_name="nt",
        )


def test_persistent_artifact_manifest_round_trip_and_content_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / ("python.exe" if os.name == "nt" else "python"))
    bootstrap = tmp_path / "_bootstrap.py"
    bootstrap.write_text("print('first')\n", encoding="utf-8")
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_a, **_kw: None,
    )
    identities = process_argv.snapshot_persistent_artifacts(
        (executable, bootstrap),
        platform_name=os.name,
    )

    decoded = process_argv.persistent_artifacts_from_manifest(
        [identity.manifest() for identity in identities]
    )
    assert decoded == identities
    process_argv.revalidate_persistent_artifacts(decoded, platform_name=os.name)

    bootstrap.write_text("print('second')\n", encoding="utf-8")
    with pytest.raises(OSError, match="drifted"):
        process_argv.revalidate_persistent_artifacts(decoded, platform_name=os.name)


@pytest.mark.skipif(os.name == "nt", reason="POSIX lexical symlink contract")
def test_persistent_posix_launcher_preserves_symlink_spelling_and_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _write_tool(tmp_path / "python-real")
    second = _write_tool(tmp_path / "python-other")
    link = tmp_path / "python"
    link.symlink_to(first.name)
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_a, **_kw: None,
    )

    frozen = process_argv.snapshot_persistent_artifact(
        link,
        platform_name="posix",
        require_executable=True,
    )

    assert frozen.lexical_path == str(link.absolute())
    assert frozen.link_target == first.name
    assert frozen.resolved_path == str(first.resolve())
    link.unlink()
    link.symlink_to(second.name)
    with pytest.raises(OSError, match="drifted"):
        process_argv.revalidate_persistent_artifacts((frozen,), platform_name="posix")


def test_freeze_validates_every_artifact_namespace_and_records_platform(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _write_tool(tmp_path / ("node.exe" if os.name == "nt" else "node"))
    second = _write_tool(tmp_path / "tool.js")
    prepared = process_argv.PreparedProcessArgv(
        [str(first), str(second)],
        artifact_paths=(str(first), str(second)),
    )
    calls: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        process_argv,
        "assert_executable_namespace",
        lambda path, *, is_windows: calls.append((str(path), is_windows)),
    )

    process_argv.freeze_process_argv(prepared, platform_name=os.name)

    assert [path for path, _windows in calls] == list(prepared.artifact_paths)
    assert prepared.frozen_platform == os.name


def test_revalidation_requires_frozen_platform_when_identity_was_injected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / ("agent.exe" if os.name == "nt" else "agent"))
    prepared = process_argv.prepare_process_argv([str(executable)])
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    process_argv.freeze_process_argv(prepared)
    prepared.frozen_platform = None
    with pytest.raises(OSError, match="no frozen executable platform"):
        process_argv.revalidate_process_argv(prepared)


def test_namespace_revalidation_failure_never_launches_owned_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / ("agent.exe" if os.name == "nt" else "agent"))
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    prepared = process_argv.freeze_process_argv(
        process_argv.prepare_process_argv([str(executable)])
    )
    monkeypatch.setattr(
        process_argv,
        "assert_executable_namespace",
        lambda *_a, **_kw: (_ for _ in ()).throw(PermissionError("namespace changed")),
    )
    monkeypatch.setattr(
        backends.subprocess,
        "Popen",
        lambda *_a, **_kw: pytest.fail("untrusted namespace must not launch a child"),
    )

    with pytest.raises(PermissionError, match="namespace changed"):
        backends._spawn_owned_process(prepared, cwd=None, env={}, input_text=None)


def test_bare_systemctl_from_unsafe_path_namespace_never_launches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = "systemctl.exe" if os.name == "nt" else "systemctl"
    executable = _write_tool(tmp_path / "agency-bin" / name)
    monkeypatch.setenv("PATH", str(executable.parent))
    if os.name == "nt":
        monkeypatch.setenv("PATHEXT", ".EXE")
    monkeypatch.setattr(
        process_argv,
        "assert_executable_namespace",
        lambda path, **_kwargs: (_ for _ in ()).throw(
            PermissionError(f"unsafe executable namespace: {path}")
        ),
    )
    monkeypatch.setattr(
        dashboard_service_core.subprocess,
        "run",
        lambda *_a, **_kw: pytest.fail("unsafe PATH manager must not launch"),
    )

    result = dashboard_service_core._run(
        ["systemctl", "--user", "show-environment"],
        command_runner=None,
    )

    assert result.returncode == 127
    assert "PermissionError" in result.stderr


def test_default_service_runner_revalidates_immediately_before_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    prepared = ["resolved-manager"]
    monkeypatch.setattr(
        dashboard_service_core,
        "prepare_process_argv",
        lambda _argv, **_kwargs: events.append("prepare") or prepared,
    )
    monkeypatch.setattr(
        dashboard_service_core,
        "freeze_process_argv",
        lambda argv, **_kwargs: events.append("freeze") or argv,
    )
    monkeypatch.setattr(
        dashboard_service_core,
        "revalidate_process_argv",
        lambda argv: events.append("revalidate") if argv is prepared else None,
    )

    def run(argv: list[str], *, stdout: Any, stderr: Any, **_kwargs: Any) -> Any:
        assert argv is prepared
        assert events == ["prepare", "freeze", "revalidate"]
        stdout.write(b"ready")
        stderr.write(b"")
        events.append("spawn")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(dashboard_service_core.subprocess, "run", run)
    result = dashboard_service_core._run(["manager", "probe"], command_runner=None)
    assert result.ok
    assert result.stdout == "ready"
    assert events == ["prepare", "freeze", "revalidate", "spawn"]


def test_default_service_runner_revalidation_failure_never_starts_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = ["resolved-manager"]
    monkeypatch.setattr(
        dashboard_service_core,
        "prepare_process_argv",
        lambda _argv, **_kwargs: prepared,
    )
    monkeypatch.setattr(
        dashboard_service_core,
        "freeze_process_argv",
        lambda argv, **_kwargs: argv,
    )
    monkeypatch.setattr(
        dashboard_service_core,
        "revalidate_process_argv",
        lambda _argv: (_ for _ in ()).throw(PermissionError("manager namespace changed")),
    )
    monkeypatch.setattr(
        dashboard_service_core.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("failed revalidation must not start a child"),
    )

    result = dashboard_service_core._run(["manager", "probe"], command_runner=None)

    assert result.returncode == 127
    assert "manager namespace changed" in result.stderr


def test_injected_service_runner_preserves_argv_and_skips_local_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dashboard_service_core,
        "prepare_process_argv",
        lambda _argv: pytest.fail("injected runners own their execution boundary"),
    )
    seen: list[list[str]] = []

    result = dashboard_service_core._run(
        ["systemctl", "--user", "is-active"],
        command_runner=lambda argv, **_kwargs: seen.append(argv) or {"returncode": 0},
    )

    assert result.ok
    assert seen == [["systemctl", "--user", "is-active"]]
