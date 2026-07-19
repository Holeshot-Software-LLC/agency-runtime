from __future__ import annotations

import re
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import pytest
import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised by the Python 3.10 matrix
    import tomli as tomllib

from scripts.read_release_version import read_release_version
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
        r'^__version__ = "((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)'
        r'(?:(?:a|b|rc)(?:0|[1-9]\d*))?)"$',
        package_init,
        re.MULTILINE,
    )
    assert version_match, "package must expose one normalized __version__ value"
    for classifier in (
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.14",
    ):
        assert classifier in pyproject


def test_release_build_tool_pin_is_non_yanked_and_matches_ci() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        pyproject = tomllib.load(stream)
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    install = next(
        step
        for step in workflow["jobs"]["artifacts"]["steps"]
        if step["name"] == "Install release tools"
    )

    assert pyproject["project"]["optional-dependencies"]["release"] == [
        "build==1.5.0",
        "twine==6.2.0",
    ]
    assert install["run"] == 'python -m pip install "build==1.5.0" "twine==6.2.0"'


def test_release_version_reader_is_literal_canonical_and_non_importing(tmp_path: Path) -> None:
    assert read_release_version(ROOT / "agency_runtime" / "__init__.py") == "0.1.0"

    invalid = tmp_path / "__init__.py"
    for value in ("make_version()", '"01.2.3"', '"1.2.3preview4"', '"1.2.3rc01"'):
        invalid.write_text(f"__version__ = {value}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="one canonical literal"):
            read_release_version(invalid)


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
    artifact_steps = workflow["jobs"]["artifacts"]["steps"]
    capture = next(
        step for step in artifact_steps if step["name"] == "Capture immutable reviewed commit"
    )
    verify = next(
        step for step in artifact_steps if step["name"] == "Verify metadata and artifact contents"
    )
    assert 'AGENCY_RELEASE_COMMIT="$(git rev-parse --verify HEAD^{commit})"' in capture["run"]
    assert '"${AGENCY_RELEASE_COMMIT}" != "${GITHUB_SHA}"' in capture["run"]
    assert '--expected-commit "${AGENCY_RELEASE_COMMIT}"' in verify["run"]

    job = workflow["jobs"]["artifact-smoke"]
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-24.04", "windows-2022"}

    steps = job["steps"]
    node_step = next(step for step in steps if step["name"].startswith("Set up Node.js"))
    assert node_step["with"]["node-version"] == "24"
    smoke_step = next(step for step in steps if "source distribution" in step["name"])
    assert smoke_step["working-directory"] == "${{ runner.temp }}"
    script = smoke_step["run"]
    for required in (
        'EXPECTED_VERSION="$(python "${GITHUB_WORKSPACE}/scripts/read_release_version.py"',
        "python -m venv wheel-smoke",
        "python -m venv sdist-smoke",
        "agency-dist/*.whl",
        "agency-dist/*.tar.gz",
        "--no-cache-dir --only-binary=:all:",
        '"${python}" -I "${GITHUB_WORKSPACE}/scripts/smoke_installed_distribution.py" --expected-version "${EXPECTED_VERSION}"',
        'subprocess.run([sys.argv[1], "--version"], capture_output=True, text=True, check=False)',
        '(result.returncode, result.stdout, result.stderr) == (0, expected, "")',
        '"${agency}" smoke --all --json',
        '"${agency}" config show',
        '"${python}" -m pip check',
        'smoke_distribution wheel "${WHEEL_PYTHON}"',
        'smoke_distribution sdist "${SDIST_PYTHON}"',
    ):
        assert required in script


def test_history_derived_ledgers_use_the_complete_durable_head() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    steps = workflow["jobs"]["test"]["steps"]

    checkout = next(
        step for step in steps if step["name"] == "Check out canonical documentation history"
    )
    ledger = next(step for step in steps if step["name"] == "Verify documentation ledgers")
    condition = "matrix.os == 'ubuntu-24.04' && matrix.python == '3.14'"

    assert checkout["if"] == ledger["if"] == condition
    assert checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
        "ref": "${{ github.event.pull_request.head.sha || github.sha }}",
    }
    assert ledger["env"]["EXPECTED_HISTORY_HEAD"] == checkout["with"]["ref"]
    assert 'test "$(git rev-parse --is-shallow-repository)" = "false"' in ledger["run"]
    assert 'test "$(git rev-parse HEAD)" = "${EXPECTED_HISTORY_HEAD}"' in ledger["run"]
    assert steps.index(checkout) > steps.index(
        next(step for step in steps if step["name"] == "Check patch whitespace")
    )


def test_dependency_review_has_an_enforced_private_repository_fallback() -> None:
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text("utf-8")
    )
    steps = workflow["jobs"]["dependency-review"]["steps"]

    probe = next(step for step in steps if step["name"] == "Detect dependency review capability")
    assert "dependency-graph/compare/${BASE_SHA}...${HEAD_SHA}" in probe["run"]
    assert "403|404" in probe["run"]
    assert "exit 1" in probe["run"]

    native = next(step for step in steps if step["name"] == "Reject vulnerable dependency changes")
    assert native["if"].endswith("available == 'true'")
    assert native["with"]["fail-on-severity"] == "moderate"

    fallback = next(
        step for step in steps if step["name"] == "Audit the exact installed runtime dependency"
    )
    assert fallback["if"].endswith("available == 'false'")
    assert fallback["run"] == "python scripts/audit_runtime_dependencies.py"


def test_codeql_gates_native_actions_and_records_unavailable_capability() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "codeql.yml").read_text("utf-8"))
    steps = workflow["jobs"]["analyze"]["steps"]

    probe = next(step for step in steps if step["name"] == "Detect native CodeQL capability")
    assert "code-scanning/alerts?per_page=1" in probe["run"]
    assert probe["env"]["REPOSITORY_VISIBILITY"] == "${{ github.event.repository.visibility }}"
    probe_script = probe["run"]
    for required in (
        '--output "${response}"',
        "403)",
        "404)",
        "\"${REPOSITORY_VISIBILITY}\" != 'private'",
        "\"${REPOSITORY_VISIBILITY}\" != 'internal'",
        "code security must be enabled for this repository to use code scanning",
        "github code security or github advanced security must be enabled",
        "ambiguous HTTP 403",
        "private_or_internal_repository_code_security_not_enabled",
        "exit 1",
    ):
        assert required in probe_script
    assert "403|404" not in probe_script

    initialize = next(step for step in steps if step["name"] == "Initialize CodeQL")
    analyze = next(step for step in steps if step["name"] == "Analyze source")
    assert initialize["if"].endswith("available == 'true'")
    assert analyze["if"].endswith("available == 'true'")
    assert analyze["with"]["upload"] == "always"
    assert analyze["with"]["output"] == "${{ runner.temp }}/codeql-results"

    evidence = next(
        step for step in steps if step["name"] == "Record unavailable CodeQL capability"
    )
    assert evidence["if"].endswith("available == 'false'")
    for required in (
        '"evidence_type": "codeql-capability"',
        '"available": False',
        '"analysis_performed": False',
        '"repository_visibility": os.environ["REPOSITORY_VISIBILITY"]',
        '"probe_http_status": int(os.environ["CAPABILITY_HTTP_STATUS"])',
        '"bandit-source-analysis"',
        '"exact-installed-runtime-vulnerability-audit"',
        '"offline-workflow-security-audit"',
    ):
        assert required in evidence["run"]

    retained = next(step for step in steps if step["name"] == "Retain CodeQL capability evidence")
    assert retained["if"].endswith("available == 'false'")
    assert retained["with"]["path"].endswith("${{ matrix.language }}.json")
    assert retained["with"]["if-no-files-found"] == "error"
    assert retained["with"]["retention-days"] == 7


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
