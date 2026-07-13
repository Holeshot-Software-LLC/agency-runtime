"""Regression coverage for trusted Windows system executable resolution."""

from __future__ import annotations

import ctypes
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import process_argv, windows_system
from agency_runtime.core.process_argv import prepare_process_argv
from agency_runtime.core.windows_system import (
    trusted_windows_system_executable,
    windows_system_command,
)


class _FakeGetSystemDirectory:
    def __init__(self, value: str = "C:\\Windows\\System32", *, result: int | None = None):
        self.value = value
        self.result = len(value) if result is None else result
        self.argtypes = None
        self.restype = None
        self.buffer_size = 0

    def __call__(self, buffer, buffer_size: int) -> int:
        self.buffer_size = buffer_size
        if self.value:
            buffer.value = self.value
        return self.result


class _FakeKernel32:
    def __init__(self, function: _FakeGetSystemDirectory):
        self.GetSystemDirectoryW = function


@pytest.mark.parametrize(
    "name",
    [None, "", "cmd.exe", "C:\\Windows\\schtasks.exe", "../schtasks.exe", "bad\x00.exe"],
)
def test_system_executable_allowlist_rejects_names_and_paths(name: object) -> None:
    with pytest.raises(ValueError, match=r"invalid|not allowlisted"):
        trusted_windows_system_executable(name, platform_name="posix")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=r"invalid|not allowlisted"):
        windows_system_command(name, command_runner=object())  # type: ignore[arg-type]


def test_posix_and_injected_commands_preserve_portable_bare_names() -> None:
    assert trusted_windows_system_executable("PowerShell.EXE", platform_name="posix") == (
        "powershell.exe"
    )
    assert windows_system_command(
        "SCHTASKS.EXE",
        "/Query",
        command_runner=object(),
        platform_name="nt",
    ) == ["schtasks.exe", "/Query"]
    assert windows_system_command("schtasks.exe", "/Query", platform_name="posix") == [
        "schtasks.exe",
        "/Query",
    ]


def test_windows_resolution_ignores_cwd_and_path_shadowing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_directory = tmp_path / "Windows" / "System32"
    trusted = system_directory / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    trusted.parent.mkdir(parents=True)
    trusted.write_bytes(b"trusted")
    attacker_directory = tmp_path / "attacker"
    attacker_directory.mkdir()
    (attacker_directory / "powershell.exe").write_bytes(b"shadow")
    monkeypatch.chdir(attacker_directory)
    monkeypatch.setenv("PATH", str(attacker_directory))
    monkeypatch.delenv("PROCESSOR_ARCHITEW6432", raising=False)

    resolved = trusted_windows_system_executable(
        "powershell.exe",
        platform_name="nt",
        system_directory=system_directory,
    )

    assert resolved == str(trusted)
    assert Path(resolved).is_absolute()


def test_sysnative_is_preferred_and_system32_is_the_safe_fallback(tmp_path: Path) -> None:
    system_directory = tmp_path / "Windows" / "System32"
    system_directory.mkdir(parents=True)
    sysnative = system_directory.parent / "Sysnative" / "schtasks.exe"
    sysnative.parent.mkdir()
    sysnative.write_bytes(b"native")
    (system_directory / "schtasks.exe").write_bytes(b"system")
    environment = {"PROCESSOR_ARCHITEW6432": "AMD64", "PATH": str(tmp_path)}

    assert trusted_windows_system_executable(
        "schtasks.exe",
        platform_name="nt",
        system_directory=system_directory,
        environ=environment,
    ) == str(sysnative)

    fallback_directory = tmp_path / "FallbackWindows" / "System32"
    fallback_directory.mkdir(parents=True)
    fallback = fallback_directory / "schtasks.exe"
    fallback.write_bytes(b"system")
    assert trusted_windows_system_executable(
        "schtasks.exe",
        platform_name="nt",
        system_directory=fallback_directory,
        environ=environment,
    ) == str(fallback)


def test_windows_resolution_rejects_relative_missing_and_unsafe_files(tmp_path: Path) -> None:
    with pytest.raises(OSError, match="must be absolute"):
        trusted_windows_system_executable(
            "schtasks.exe",
            platform_name="nt",
            system_directory="relative",
        )

    system_directory = tmp_path / "Windows" / "System32"
    with pytest.raises(FileNotFoundError, match="not found"):
        trusted_windows_system_executable(
            "schtasks.exe",
            platform_name="nt",
            system_directory=system_directory,
            environ={},
            lstat=lambda _path: (_ for _ in ()).throw(FileNotFoundError()),
        )

    for metadata in (
        SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0),
        SimpleNamespace(
            st_mode=stat.S_IFREG,
            st_file_attributes=windows_system._FILE_ATTRIBUTE_REPARSE_POINT,
        ),
    ):
        with pytest.raises(OSError, match="unsafe"):
            trusted_windows_system_executable(
                "schtasks.exe",
                platform_name="nt",
                system_directory=system_directory,
                environ={},
                lstat=lambda _path, value=metadata: value,
            )

    def denied(_path):
        raise PermissionError("denied")

    with pytest.raises(OSError, match="unavailable") as raised:
        trusted_windows_system_executable(
            "schtasks.exe",
            platform_name="nt",
            system_directory=system_directory,
            environ={},
            lstat=denied,
        )
    assert isinstance(raised.value.__cause__, PermissionError)


def test_native_system_directory_api_is_bounded_and_injectable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    successful = _FakeGetSystemDirectory()
    kernel = _FakeKernel32(successful)
    assert str(windows_system._native_system_directory(kernel32=kernel)) == (
        "C:\\Windows\\System32"
    )
    assert successful.argtypes == [ctypes.c_wchar_p, ctypes.c_uint]
    assert successful.restype is ctypes.c_uint
    assert successful.buffer_size == windows_system._MAX_WINDOWS_PATH_CHARS

    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, *, use_last_error: kernel,
        raising=False,
    )
    assert str(windows_system._native_system_directory()) == "C:\\Windows\\System32"

    failed = _FakeGetSystemDirectory("", result=0)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    with pytest.raises(OSError, match="GetSystemDirectoryW failed") as raised:
        windows_system._native_system_directory(kernel32=_FakeKernel32(failed))
    assert raised.value.errno == 5

    oversized = _FakeGetSystemDirectory(
        "C:\\Windows\\System32",
        result=windows_system._MAX_WINDOWS_PATH_CHARS,
    )
    with pytest.raises(OSError, match="path bound"):
        windows_system._native_system_directory(kernel32=_FakeKernel32(oversized))


def test_default_system_directory_and_command_resolution_are_delegated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_directory = tmp_path / "Windows" / "System32"
    executable = system_directory / "schtasks.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"trusted")
    monkeypatch.setattr(
        windows_system,
        "_native_system_directory",
        lambda: system_directory,
    )
    assert trusted_windows_system_executable(
        "schtasks.exe",
        platform_name="nt",
        environ={},
    ) == str(executable)

    calls: list[tuple[str, str | None]] = []

    def resolve(name: str, *, platform_name: str | None = None) -> str:
        calls.append((name, platform_name))
        return str(executable)

    monkeypatch.setattr(windows_system, "trusted_windows_system_executable", resolve)
    assert windows_system_command(
        "schtasks.exe",
        "/Run",
        platform_name="nt",
    ) == [str(executable), "/Run"]
    assert calls == [("schtasks.exe", "nt")]


def test_process_argv_system_resolver_is_fail_closed_and_optional(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = tmp_path / "agent.ps1"
    script.write_text("exit 0", encoding="utf-8")

    def resolver(_name: str) -> str:
        return str(script)

    with pytest.raises(FileNotFoundError, match="PowerShell"):
        prepare_process_argv(
            ["agent"],
            platform_name="nt",
            resolver=resolver,
            system_resolver=lambda _name: None,
        )

    trusted = tmp_path / "trusted-powershell.exe"
    monkeypatch.setattr(
        process_argv,
        "trusted_windows_system_executable",
        lambda name, *, platform_name: (
            str(trusted) if (name, platform_name) == ("powershell.exe", "nt") else None
        ),
    )
    prepared = prepare_process_argv(
        ["agent"],
        platform_name="nt",
        resolver=resolver,
    )
    assert prepared[0] == str(trusted)
    assert prepared[-1] == str(script)


def test_process_argv_prefers_native_executables_over_windows_shims(
    tmp_path: Path,
) -> None:
    shim = tmp_path / "agent.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    native = shim.with_suffix(".exe")
    native.write_bytes(b"native")

    assert prepare_process_argv(
        ["agent", "--version"],
        platform_name="nt",
        resolver=lambda _name: str(shim),
    ) == [str(native), "--version"]


def test_codex_npm_shim_prefers_packaged_native_executable(tmp_path: Path) -> None:
    shim = tmp_path / "codex.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    native = (
        tmp_path
        / "node_modules"
        / "@openai"
        / "codex"
        / "node_modules"
        / "@openai"
        / "codex-win32-x64"
        / "vendor"
        / "x86_64-pc-windows-msvc"
        / "bin"
        / "codex.exe"
    )
    native.parent.mkdir(parents=True)
    native.write_bytes(b"native")

    assert prepare_process_argv(
        ["codex", "exec", "-"],
        platform_name="nt",
        resolver=lambda _name: str(shim),
    ) == [str(native), "exec", "-"]
