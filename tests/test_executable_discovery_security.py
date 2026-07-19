"""Adversarial coverage for delegated executable discovery and launch identity."""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import process_argv
from agency_runtime.core.delegation import backends, lifecycle_git
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.process_argv import (
    freeze_process_argv,
    prepare_process_argv,
    revalidate_process_argv,
    sanitized_executable_search_path,
)


def _tool_name(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _write_tool(path: Path, payload: bytes = b"tool") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    if os.name != "nt":
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _replace_tool(path: Path) -> None:
    replacement = path.with_name(f"{path.name}.replacement")
    _write_tool(replacement, b"replacement executable payload")
    os.replace(replacement, path)


def test_path_discovery_ignores_empty_relative_dot_and_current_directory_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    working = tmp_path / "working"
    safe_bin = tmp_path / "safe-bin"
    working.mkdir()
    executable_name = _tool_name("codex")
    _write_tool(working / executable_name, b"cwd poison")
    trusted = _write_tool(safe_bin / executable_name, b"trusted")
    separator = os.pathsep
    poisoned_path = separator.join(("", ".", "relative-bin", str(working), str(safe_bin)))
    monkeypatch.chdir(working)
    monkeypatch.setenv("PATH", poisoned_path)

    sanitized = sanitized_executable_search_path()
    prepared = prepare_process_argv([executable_name, "--version"])

    assert sanitized == str(safe_bin)
    assert Path(prepared[0]).resolve() == trusted.resolve()


def test_sanitized_path_excludes_nested_workspace_entries_across_windows_drives() -> None:
    sanitized = sanitized_executable_search_path(
        r"C:\repo\.venv\Scripts;D:\Trusted\bin;D:\Trusted\bin",
        platform_name="nt",
        current_directory=r"C:\repo\src",
        forbidden_roots=(r"C:\repo",),
    )

    assert sanitized == r"D:\Trusted\bin"


@pytest.mark.parametrize(
    "value",
    [".", "..", "./codex", "bin/codex", r".\codex", r"bin\codex", r"C:codex.exe"],
)
def test_explicit_relative_executable_paths_are_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="must be absolute"):
        prepare_process_argv([value])


def test_frozen_executable_rejects_replacement_before_spawn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / _tool_name("codex"))
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    prepared = freeze_process_argv(prepare_process_argv([str(executable)]))
    _replace_tool(executable)
    monkeypatch.setattr(
        backends.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("replacement must be rejected before Popen"),
    )

    with pytest.raises(OSError, match="changed before launch"):
        backends._spawn_owned_process(
            prepared,
            cwd=None,
            env={"PATH": str(tmp_path)},
            input_text=None,
        )


def test_spawn_rejects_argv_without_frozen_identity() -> None:
    with pytest.raises(TypeError, match="frozen executable identity"):
        backends._spawn_owned_process(
            [str(Path.cwd() / _tool_name("codex"))],
            cwd=None,
            env={},
            input_text=None,
        )


def test_frozen_executable_identity_revalidates_unchanged_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / _tool_name("codex"))
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    prepared = freeze_process_argv(prepare_process_argv([str(executable)]))

    revalidate_process_argv(prepared)

    assert prepared.executable_identities[0].path == str(executable.resolve())
    assert prepared.executable_identities[0].inode > 0


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink contract")
def test_posix_executable_symlink_is_canonicalized_before_freezing(tmp_path: Path) -> None:
    target = _write_tool(tmp_path / "codex-real")
    link = tmp_path / "codex"
    link.symlink_to(target)

    prepared = freeze_process_argv(prepare_process_argv([str(link)]))

    assert prepared[0] == str(target.resolve())
    assert prepared.executable_identities[0].path == str(target.resolve())


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell companion contract")
def test_windows_approved_powershell_companion_identity_is_frozen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shim = _write_tool(tmp_path / "codex.cmd")
    script = tmp_path / "codex.ps1"
    script.write_text("exit 0", encoding="utf-8")
    powershell = _write_tool(tmp_path / "powershell.exe")
    prepared = prepare_process_argv(
        [str(shim)],
        platform_name="nt",
        system_resolver=lambda _name: str(powershell),
    )
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    freeze_process_argv(prepared)
    _replace_tool(script)

    with pytest.raises(OSError, match="changed before launch"):
        revalidate_process_argv(prepared)


def test_git_ignores_fake_executable_in_target_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_git = shutil.which("git")
    if real_git is None:
        pytest.skip("Git is unavailable")
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_git = _write_tool(repo / Path(real_git).name, b"repository poison")
    monkeypatch.setenv("PATH", os.pathsep.join((str(repo), str(Path(real_git).parent))))
    observed: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> BoundedProcessResult:
        observed["argv"] = argv
        observed.update(kwargs)
        return BoundedProcessResult(0, "", "")

    monkeypatch.setattr(lifecycle_git, "run_bounded_process", run)

    result = lifecycle_git.run_git(repo, ["status", "--porcelain"])

    assert result.returncode == 0
    assert Path(observed["argv"][0]).resolve() == Path(real_git).resolve()
    assert Path(observed["argv"][0]).resolve() != fake_git.resolve()


def test_git_refuses_executable_resolved_inside_target_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_git = _write_tool(repo / _tool_name("git"))
    monkeypatch.setattr(
        lifecycle_git,
        "resolve_executable_path",
        lambda *_args, **_kwargs: str(fake_git),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "run_bounded_process",
        lambda *_args, **_kwargs: pytest.fail("repository-owned Git must never execute"),
    )

    result = lifecycle_git.run_git(repo, ["status", "--porcelain"])

    assert result.returncode == 126
    assert "inside the target repository" in result.stderr


def test_git_refuses_when_resolved_executable_identity_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(
        lifecycle_git,
        "resolve_executable_path",
        lambda *_args, **_kwargs: str(tmp_path / _tool_name("missing-git")),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "run_bounded_process",
        lambda *_args, **_kwargs: pytest.fail("unreadable Git must never execute"),
    )

    result = lifecycle_git.run_git(repo, ["status", "--porcelain"])

    assert result.returncode == 126
    assert "executable identity failed" in result.stderr


def test_git_fails_closed_when_path_contains_only_unsafe_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tool(repo / _tool_name("git"))
    monkeypatch.setenv("PATH", os.pathsep.join(("", ".", "relative", str(repo))))
    monkeypatch.setattr(
        lifecycle_git,
        "run_bounded_process",
        lambda *_args, **_kwargs: pytest.fail("unsafe PATH must never reach process launch"),
    )

    result = lifecycle_git.run_git(repo, ["status", "--porcelain"])

    assert result.returncode == 126
    assert "trusted executable is unavailable" in result.stderr


def test_path_validation_rejects_invalid_values_and_nonabsolute_resolver_results() -> None:
    with pytest.raises(ValueError, match="PATH must be text"):
        sanitized_executable_search_path("safe\x00unsafe")
    for value in (None, "", "bad\x00name", "bad\nname", "bad\x7fname"):
        with pytest.raises(ValueError, match="executable must be"):
            process_argv.resolve_executable_path(value)  # type: ignore[arg-type]
    with pytest.raises(OSError, match="non-absolute"):
        process_argv.resolve_executable_path(
            "codex",
            resolver=lambda _name: "relative-codex",
        )
    assert process_argv._is_absolute_path(
        str(Path.cwd()),
        platform_name="native",
    )


def test_posix_direct_search_requires_regular_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    executable = _write_tool(tmp_path / "codex")
    assert process_argv._search_absolute_path(
        "codex",
        search_path=".",
        platform_name="posix",
    ) == str(executable.absolute())
    monkeypatch.setattr(process_argv.os, "access", lambda *_args: False)
    assert (
        process_argv._search_absolute_path(
            "codex",
            search_path=".",
            platform_name="posix",
        )
        is None
    )


def test_direct_search_skips_nonregular_candidates(tmp_path: Path) -> None:
    directory = tmp_path / _tool_name("codex")
    directory.mkdir()

    assert (
        process_argv._search_absolute_path(
            directory.name,
            search_path=str(tmp_path),
            platform_name=os.name,
        )
        is None
    )


def test_windows_direct_search_ignores_untrusted_pathext_suffixes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_tool(tmp_path / "codex.COM")
    trusted = _write_tool(tmp_path / "codex.EXE")
    monkeypatch.setenv("PATHEXT", ".COM;.EXE")

    resolved = process_argv._search_absolute_path(
        "codex",
        search_path=str(tmp_path),
        platform_name="nt",
    )

    assert Path(resolved or "").samefile(trusted)
    explicit = process_argv._search_absolute_path(
        "codex.EXE",
        search_path=str(tmp_path),
        platform_name="nt",
    )
    assert Path(explicit or "").samefile(trusted)

    trusted.unlink()
    with pytest.raises(FileNotFoundError, match="executable not found"):
        process_argv.resolve_executable_path(
            "codex",
            search_path=str(tmp_path),
            platform_name="nt",
        )


def test_windows_fallback_rejects_an_untrusted_com_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_argv, "_search_absolute_path", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        process_argv.shutil,
        "which",
        lambda _name, *, path: "C:\\tools\\codex.COM" if path else None,
    )

    with pytest.raises(FileNotFoundError, match="executable not found"):
        process_argv.resolve_executable_path(
            "codex",
            search_path="C:\\tools",
            platform_name="nt",
        )


def test_executable_artifact_requires_existing_real_regular_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="artifact is unavailable"):
        freeze_process_argv(
            process_argv.PreparedProcessArgv(
                [str(tmp_path / _tool_name("missing"))],
                artifact_paths=(str(tmp_path / _tool_name("missing")),),
            )
        )
    with pytest.raises(OSError, match="regular file"):
        process_argv._canonical_regular_file(str(tmp_path), platform_name=os.name)


def test_executable_artifact_rejects_reparse_and_nonexecutable_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / _tool_name("codex"))
    actual_lstat = process_argv.os.lstat
    reparse = SimpleNamespace(
        st_mode=stat.S_IFREG,
        st_file_attributes=process_argv._WINDOWS_REPARSE_POINT,
    )
    monkeypatch.setattr(process_argv.os, "lstat", lambda _path: reparse)
    with pytest.raises(OSError, match="link or reparse"):
        process_argv._canonical_regular_file(str(executable), platform_name="nt")
    monkeypatch.setattr(process_argv.os, "lstat", actual_lstat)
    monkeypatch.setattr(process_argv.os, "access", lambda *_args: False)
    with pytest.raises(PermissionError, match="not executable"):
        process_argv._canonical_regular_file(str(executable), platform_name="posix")


def test_executable_artifact_fails_when_canonicalization_or_final_type_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / _tool_name("codex"))
    monkeypatch.setattr(
        process_argv.Path,
        "resolve",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("resolution failed")),
    )
    with pytest.raises(FileNotFoundError, match="artifact is unavailable"):
        process_argv._canonical_regular_file(str(executable), platform_name=os.name)


def test_final_executable_type_is_revalidated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / _tool_name("codex"))
    regular = executable.stat()
    directory = tmp_path.stat()
    observed = iter((regular, directory))
    monkeypatch.setattr(process_argv.os, "lstat", lambda _path: next(observed))
    monkeypatch.setattr(process_argv.Path, "resolve", lambda self, **_kwargs: self)

    with pytest.raises(OSError, match="real regular file"):
        process_argv._canonical_regular_file(str(executable), platform_name=os.name)


def test_forbidden_repository_suffix_and_inode_guards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_tool(tmp_path / _tool_name("codex"))
    assert process_argv._is_within(str(executable), tmp_path / "missing") is False
    prepared = prepare_process_argv([str(executable)])
    with pytest.raises(OSError, match="target repository"):
        freeze_process_argv(prepared, forbidden_roots=(tmp_path,))

    untrusted = _write_tool(tmp_path / "agent.cmd")
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_args, **_kwargs: None,
    )
    with pytest.raises(OSError, match="trusted native suffix"):
        process_argv._snapshot_executable(
            str(untrusted),
            platform_name="nt",
            forbidden_roots=(),
            require_native_suffix=True,
        )

    zero_inode = SimpleNamespace(
        st_ino=0,
        st_dev=1,
        st_mode=stat.S_IFREG,
        st_size=1,
        st_mtime_ns=1,
        st_file_attributes=0,
    )
    monkeypatch.setattr(
        process_argv,
        "_canonical_regular_file",
        lambda *_args, **_kwargs: (str(executable), zero_inode),
    )
    with pytest.raises(OSError, match="no stable filesystem identity"):
        process_argv._snapshot_executable(
            str(executable),
            platform_name=os.name,
            forbidden_roots=(),
            require_native_suffix=False,
        )


def test_revalidation_requires_a_frozen_identity() -> None:
    prepared = process_argv.PreparedProcessArgv(
        [str(Path.cwd() / _tool_name("codex"))],
        artifact_paths=(),
    )
    with pytest.raises(OSError, match="no frozen executable identity"):
        revalidate_process_argv(prepared)


def test_npm_companion_resolution_is_allowlisted_and_identity_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.name != "nt":
        monkeypatch.setattr(
            process_argv,
            "_is_absolute_path",
            lambda value, *, platform_name: Path(value).is_absolute(),
        )
        monkeypatch.setattr(process_argv, "ntpath", process_argv.posixpath)
    assert (
        process_argv._trusted_npm_companion(
            tmp_path / "other.cmd",
            lambda _name: None,
        )
        is None
    )
    claude = tmp_path / "claude.cmd"
    assert process_argv._trusted_npm_companion(claude, lambda _name: None) is None

    script = tmp_path / "node_modules" / "@anthropic-ai" / "claude-code" / "cli.js"
    script.parent.mkdir(parents=True)
    script.write_text("process.exit(0)", encoding="utf-8")
    sibling_node = _write_tool(tmp_path / "node.exe")
    assert process_argv._trusted_npm_companion(claude, lambda _name: None) == [
        str(sibling_node),
        str(script),
    ]
    sibling_node.unlink()
    external_node = _write_tool(tmp_path / "external" / "node.exe")
    assert process_argv._trusted_npm_companion(
        claude,
        lambda _name: str(external_node),
    ) == [str(external_node), str(script)]
    assert process_argv._trusted_npm_companion(claude, lambda _name: None) is None


def test_windows_launch_rules_reject_unsafe_fallbacks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(OSError, match="non-absolute"):
        process_argv._trusted_powershell(
            platform_name="nt",
            system_resolver=lambda _name: "powershell.exe",
        )
    if os.name != "nt":
        monkeypatch.setattr(
            process_argv,
            "_is_absolute_path",
            lambda value, *, platform_name: Path(value).is_absolute(),
        )
        monkeypatch.setattr(process_argv, "ntpath", process_argv.posixpath)
    trusted = _write_tool(tmp_path / "powershell.exe")
    monkeypatch.setattr(
        process_argv,
        "trusted_windows_system_executable",
        lambda *_args, **_kwargs: str(trusted),
    )
    assert process_argv._trusted_powershell(
        platform_name="nt",
        system_resolver=None,
    ) == str(trusted)

    cmd = _write_tool(tmp_path / "unsafe.cmd")
    with pytest.raises(OSError, match=r"unsafe cmd\.exe shim"):
        prepare_process_argv(
            [str(cmd)],
            platform_name="nt",
            resolver=lambda _name: str(cmd),
            system_resolver=lambda _name: str(trusted),
        )
    untrusted = _write_tool(tmp_path / "unsafe.vbs")
    with pytest.raises(OSError, match="untrusted suffix"):
        prepare_process_argv(
            [str(untrusted)],
            platform_name="nt",
            resolver=lambda _name: str(untrusted),
        )
