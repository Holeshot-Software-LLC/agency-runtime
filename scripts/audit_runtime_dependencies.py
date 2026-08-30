"""Audit exact installed runtime dependencies without resolving the local project."""

from __future__ import annotations

import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, requires, version

from agency_runtime.core.private_paths import private_temporary_directory

_DISTRIBUTION = "agency-runtime"
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def installed_runtime_requirements() -> list[str]:
    """Return exact versions for installed non-extra dependencies."""

    exact: set[str] = set()
    for requirement in requires(_DISTRIBUTION) or ():
        declaration, _, marker = requirement.partition(";")
        if "extra" in marker.casefold():
            continue
        match = _REQUIREMENT_NAME.match(declaration)
        if match is None:
            raise RuntimeError(f"could not parse installed requirement: {requirement!r}")
        name = match.group(1)
        try:
            installed = version(name)
        except PackageNotFoundError:
            if marker:
                continue
            raise RuntimeError(f"required runtime dependency is not installed: {name}") from None
        exact.add(f"{name}=={installed}")
    if not exact:
        raise RuntimeError("installed distribution exposes no runtime dependencies to audit")
    return sorted(exact, key=str.casefold)


def main() -> int:
    requirements = installed_runtime_requirements()
    with private_temporary_directory(prefix="dependency-audit") as temporary:
        requirement_file = temporary / "runtime-requirements.txt"
        requirement_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--strict",
                "--no-deps",
                "--disable-pip",
                "--requirement",
                str(requirement_file),
            ],
            check=False,
        )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
