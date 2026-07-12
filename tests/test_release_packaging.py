from __future__ import annotations

import re
import subprocess
import sys
from importlib.resources import files
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_resources_are_addressable() -> None:
    package = files("agency_runtime")
    required = (
        "core/companion_policy.yaml",
        "core/config_defaults.yaml",
        "core/configuration.py",
        "core/canary.py",
        "core/dashboard_runtime.py",
        "core/dashboard_service.py",
        "core/evals/data/routing_v1.py",
        "dashboard/app.css",
        "dashboard/app.js",
        "dashboard/charts.js",
        "dashboard/index.html",
    )
    for relative in required:
        assert package.joinpath(*relative.split("/")).is_file(), relative

    dashboard_bytes = sum(
        len(package.joinpath("dashboard", name).read_bytes())
        for name in ("index.html", "app.css", "charts.js", "app.js")
    )
    assert dashboard_bytes < 256 * 1024, "dashboard assets exceeded the 256 KiB budget"


def test_release_metadata_is_single_source_and_cross_platform() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    package_init = (ROOT / "agency_runtime" / "__init__.py").read_text(encoding="utf-8")

    assert 'dynamic = ["version"]' in pyproject
    assert 'version = {attr = "agency_runtime.__version__"}' in pyproject
    version_match = re.search(
        r'^__version__ = "(\d+\.\d+\.\d+(?:[a-z]+\d+)?)"$', package_init, re.MULTILINE
    )
    assert version_match, "package must expose one normalized __version__ value"
    for classifier in (
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.14",
    ):
        assert classifier in pyproject


def test_tracked_release_inputs_pass_hygiene_check() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/verify_release_hygiene.py", str(ROOT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
