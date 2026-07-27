"""Setuptools commands for host-derived platform-honest wheels."""

from __future__ import annotations

import os

from setuptools.command.bdist_wheel import bdist_wheel
from setuptools.command.build_py import build_py

try:  # The sdist and repository both expose the top-level scripts namespace.
    from scripts.release_contract import (
        NATIVE_OPERATOR_PRESENCE_EXECUTABLE,
        WheelProfile,
        host_wheel_profile,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - direct setup.py compatibility
    if exc.name != "scripts":
        raise
    from release_contract import (  # type: ignore[no-redef]
        NATIVE_OPERATOR_PRESENCE_EXECUTABLE,
        WheelProfile,
        host_wheel_profile,
    )


def _normalized_absolute_path(value: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(value)))


def _executable_path_for_package(package: str, src_dir: str) -> str | None:
    package_prefix = f"{package.replace('.', '/')}/"
    if not NATIVE_OPERATOR_PRESENCE_EXECUTABLE.startswith(package_prefix):
        return None
    relative = NATIVE_OPERATOR_PRESENCE_EXECUTABLE.removeprefix(package_prefix)
    return _normalized_absolute_path(os.path.join(src_dir, *relative.split("/")))


def current_wheel_profile() -> WheelProfile:
    """Return the immutable profile selected from the actual build host."""

    return host_wheel_profile()


class PlatformBuildPy(build_py):
    """Exclude the Windows PE from every portable wheel build."""

    def find_data_files(self, package: str, src_dir: str) -> list[str]:
        files = list(super().find_data_files(package, src_dir))
        if current_wheel_profile().includes_native_executable:
            return files
        executable = _executable_path_for_package(package, src_dir)
        if executable is None:
            return files
        return [name for name in files if _normalized_absolute_path(name) != executable]


class PlatformBdistWheel(bdist_wheel):
    """Emit an exact py3/none wheel tag with honest purelib placement."""

    _agency_profile: WheelProfile

    def finalize_options(self) -> None:
        super().finalize_options()
        self._agency_profile = current_wheel_profile()
        self.root_is_pure = self._agency_profile.root_is_purelib
        self.plat_name = "any" if self.root_is_pure else self._agency_profile.tag.rsplit("-", 1)[1]
        self.plat_name_supplied = False

    def get_tag(self) -> tuple[str, str, str]:
        profile = getattr(self, "_agency_profile", current_wheel_profile())
        return "py3", "none", profile.tag.removeprefix("py3-none-")

    def run(self) -> None:
        profile = getattr(self, "_agency_profile", current_wheel_profile())
        if profile.root_is_purelib:
            super().run()
            return
        original = self.distribution.has_ext_modules
        self.distribution.has_ext_modules = lambda: True
        try:
            super().run()
        finally:
            self.distribution.has_ext_modules = original


COMMAND_CLASSES = {
    "bdist_wheel": PlatformBdistWheel,
    "build_py": PlatformBuildPy,
}
