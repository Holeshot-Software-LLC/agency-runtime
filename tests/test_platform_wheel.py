"""Platform wheel commands derive an exact, non-overridable host profile."""

from __future__ import annotations

from pathlib import Path

import pytest
from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py
from setuptools.dist import Distribution

from scripts import platform_wheel as subject
from scripts.release_contract import (
    PORTABLE_WHEEL_PROFILE,
    WINDOWS_X64_WHEEL_PROFILE,
    host_wheel_profile,
)


@pytest.mark.parametrize(
    ("platform_name", "pointer_size", "platform_tag", "expected"),
    [
        ("win32", 8, "win-amd64", WINDOWS_X64_WHEEL_PROFILE),
        ("win32", 8, "win_amd64", WINDOWS_X64_WHEEL_PROFILE),
        ("win32", 4, "win-amd64", PORTABLE_WHEEL_PROFILE),
        ("win32", 8, "win-arm64", PORTABLE_WHEEL_PROFILE),
        ("linux", 8, "linux-x86_64", PORTABLE_WHEEL_PROFILE),
        ("darwin", 8, "macosx-15-arm64", PORTABLE_WHEEL_PROFILE),
    ],
)
def test_host_profile_is_derived_from_the_actual_interpreter_platform(
    platform_name: str,
    pointer_size: int,
    platform_tag: str,
    expected: object,
) -> None:
    assert (
        host_wheel_profile(
            platform_name=platform_name,
            pointer_size=pointer_size,
            platform_tag=platform_tag,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("profile", "purelib", "platform_name", "tag"),
    [
        (PORTABLE_WHEEL_PROFILE, True, "any", ("py3", "none", "any")),
        (
            WINDOWS_X64_WHEEL_PROFILE,
            False,
            "win_amd64",
            ("py3", "none", "win_amd64"),
        ),
    ],
)
def test_bdist_wheel_forces_exact_profile_metadata(
    monkeypatch: pytest.MonkeyPatch,
    profile: object,
    purelib: bool,
    platform_name: str,
    tag: tuple[str, str, str],
) -> None:
    monkeypatch.setattr(subject, "current_wheel_profile", lambda: profile)
    command = subject.PlatformBdistWheel(Distribution({"name": "package", "version": "1"}))
    command.initialize_options()
    command.plat_name = "hostile_override"
    command.plat_name_supplied = True

    command.finalize_options()

    assert command.root_is_pure is purelib
    assert command.plat_name == platform_name
    assert command.plat_name_supplied is False
    assert command.get_tag() == tag


def test_portable_build_excludes_only_the_exact_reviewed_pe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "agency_runtime"
    executable = (
        source / "native" / "windows" / "operator_presence" / ("operator_presence_verifier.exe")
    )
    cpp = executable.with_suffix(".cpp")
    other_executable = source / "other.exe"
    files = [str(executable), str(cpp), str(other_executable)]
    monkeypatch.setattr(build_py, "find_data_files", lambda *_args: files)
    monkeypatch.setattr(subject, "current_wheel_profile", lambda: PORTABLE_WHEEL_PROFILE)
    command = subject.PlatformBuildPy(Distribution())

    assert command.find_data_files("agency_runtime", str(source)) == [
        str(cpp),
        str(other_executable),
    ]


def test_windows_build_retains_the_reviewed_pe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "agency_runtime"
    executable = (
        source / "native" / "windows" / "operator_presence" / ("operator_presence_verifier.exe")
    )
    files = [str(executable)]
    monkeypatch.setattr(build_py, "find_data_files", lambda *_args: files)
    monkeypatch.setattr(subject, "current_wheel_profile", lambda: WINDOWS_X64_WHEEL_PROFILE)
    command = subject.PlatformBuildPy(Distribution())

    assert command.find_data_files("agency_runtime", str(source)) == files


def test_windows_wheel_places_shared_python_payloads_at_the_platlib_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distribution = Distribution({"name": "package", "version": "1"})
    command = subject.PlatformBdistWheel(distribution)
    command._agency_profile = WINDOWS_X64_WHEEL_PROFILE
    observed: list[bool] = []
    monkeypatch.setattr(
        bdist_wheel,
        "run",
        lambda self: observed.append(self.distribution.has_ext_modules()),
    )

    command.run()

    assert observed == [True]
    assert distribution.has_ext_modules() is False


def test_setup_py_registers_commands_without_duplicating_project_metadata() -> None:
    setup_source = Path(__file__).resolve().parents[1].joinpath("setup.py").read_text("utf-8")

    assert "setup(cmdclass=COMMAND_CLASSES)" in setup_source
    assert "name=" not in setup_source
    assert "version=" not in setup_source
