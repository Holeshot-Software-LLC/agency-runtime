from __future__ import annotations

import re
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import yaml

from scripts.verify_release_hygiene import SECRET_PATTERNS, generated_path_reason

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
        "dashboard/dashboard-actions.js",
        "dashboard/dashboard-config.js",
        "dashboard/dashboard-core.js",
        "dashboard/dashboard-live.js",
        "dashboard/dashboard-render.js",
        "dashboard/index.html",
        "dashboard/package.json",
    )
    for relative in required:
        assert package.joinpath(*relative.split("/")).is_file(), relative

    dashboard_bytes = sum(
        len(package.joinpath("dashboard", name).read_bytes())
        for name in (
            "index.html",
            "app.css",
            "charts.js",
            "app.js",
            "dashboard-actions.js",
            "dashboard-config.js",
            "dashboard-core.js",
            "dashboard-live.js",
            "dashboard-render.js",
            "package.json",
        )
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


def test_release_hygiene_rejects_runtime_and_environment_state(tmp_path: Path) -> None:
    forbidden = (
        ".env.production",
        "agency.yaml",
        "runtime.sqlite3",
        "runtime.db-wal",
        "runtime.sqlite-shm",
    )
    for name in forbidden:
        assert generated_path_reason(tmp_path / name, tmp_path) is not None

    assert generated_path_reason(tmp_path / ".env.example", tmp_path) is None


def test_release_hygiene_rejects_only_top_level_project_version_staging(
    tmp_path: Path,
) -> None:
    for name in (
        "agency_runtime-0.1.0",
        "agency-runtime-12.3.4rc1",
        "Agency.Runtime-2.0.1",
    ):
        assert generated_path_reason(tmp_path / name / "PKG-INFO", tmp_path) == (
            "generated project-version staging directory"
        )

    assert (
        generated_path_reason(
            tmp_path / "fixtures" / "agency_runtime-0.1.0" / "PKG-INFO",
            tmp_path,
        )
        is None
    )
    assert generated_path_reason(tmp_path / "agency_runtime-latest", tmp_path) is None
    assert generated_path_reason(tmp_path / "other_project-0.1.0", tmp_path) is None


def test_ci_smokes_wheel_and_sdist_in_separate_clean_environments() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    job = workflow["jobs"]["artifact-smoke"]
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-24.04", "windows-2022"}

    steps = job["steps"]
    node_step = next(step for step in steps if step["name"].startswith("Set up Node.js"))
    assert node_step["with"]["node-version"] == "24"
    smoke_step = next(step for step in steps if "source distribution" in step["name"])
    assert smoke_step["working-directory"] == "${{ runner.temp }}"
    script = smoke_step["run"]
    for required in (
        "python -m venv wheel-smoke",
        "python -m venv sdist-smoke",
        "agency-dist/*.whl",
        "agency-dist/*.tar.gz",
        "--no-cache-dir --only-binary=:all:",
        '"${python}" -I "${GITHUB_WORKSPACE}/scripts/smoke_installed_distribution.py"',
        '"${agency}" smoke --all --json',
        '"${agency}" config show',
        '"${python}" -m pip check',
        'smoke_distribution wheel "${WHEEL_PYTHON}"',
        'smoke_distribution sdist "${SDIST_PYTHON}"',
    ):
        assert required in script


def test_release_hygiene_recognizes_common_secret_families() -> None:
    examples = {
        "Anthropic API key": b"sk-ant-" + (b"a" * 24),
        "AWS access key": b"AKIA" + (b"A" * 16),
        "Google API key": b"AIza" + (b"a" * 35),
        "GitHub token": b"ghp_" + (b"a" * 30),
        "npm token": b"npm_" + (b"a" * 36),
        "Slack token": b"xoxb-" + (b"a" * 24),
        "Stripe live key": b"sk_live_" + (b"a" * 24),
    }

    for label, payload in examples.items():
        assert SECRET_PATTERNS[label].search(payload), label
