"""Setuptools commands for host-derived platform-honest wheels."""

from __future__ import annotations

from setuptools.command.bdist_wheel import bdist_wheel

try:  # The sdist and repository both expose the top-level scripts namespace.
    from scripts.release_contract import (
        WheelProfile,
        host_wheel_profile,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - direct setup.py compatibility
    if exc.name != "scripts":
        raise
    from release_contract import (  # type: ignore[no-redef]
        WheelProfile,
        host_wheel_profile,
    )


def current_wheel_profile() -> WheelProfile:
    """Return the immutable profile selected from the actual build host."""

    return host_wheel_profile()


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
}
