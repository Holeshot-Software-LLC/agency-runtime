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
RELEASE_COVERAGE_MODULES = (
    "build_distributions",
    "canonicalize_distributions",
    "prove_autocrlf_checkout",
    "release_contract",
    "release_git",
    "verify_distribution",
)


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
    artifact_job = workflow["jobs"]["artifacts"]
    artifact_steps = artifact_job["steps"]
    build = next(
        step for step in artifact_steps if step["name"] == "Build wheel and source distribution"
    )
    autocrlf = next(
        step
        for step in artifact_steps
        if step["name"] == "Prove clean CRLF checkout uses canonical Git blobs"
    )
    verify = next(
        step for step in artifact_steps if step["name"] == "Verify metadata and artifact contents"
    )
    assert artifact_job["env"]["AGENCY_RELEASE_COMMIT"] == "${{ github.sha }}"
    assert artifact_job["runs-on"] == "${{ matrix.os }}"
    assert artifact_job["strategy"]["matrix"]["include"] == [
        {"os": "ubuntu-24.04"},
        {"os": "windows-2022"},
    ]
    assert artifact_steps.index(autocrlf) + 1 == artifact_steps.index(build)
    assert autocrlf == {
        "name": "Prove clean CRLF checkout uses canonical Git blobs",
        "shell": "bash",
        "run": (
            '"${AGENCY_CI_PYTHON}" -m scripts.prove_autocrlf_checkout '
            '--expected-commit "${AGENCY_RELEASE_COMMIT}"'
        ),
    }
    assert build["run"] == (
        '"${AGENCY_CI_PYTHON}" -m scripts.build_distributions "${AGENCY_CI_TEMP}/dist" '
        '--expected-commit "${AGENCY_RELEASE_COMMIT}"'
    )
    assert build["shell"] == "bash"
    assert "python -m build" not in build["run"]
    assert '--expected-commit "${AGENCY_RELEASE_COMMIT}"' in verify["run"]
    assert "-m scripts.verify_distribution" in verify["run"]
    assert '"${AGENCY_CI_TEMP}/dist"' in verify["run"]
    assert verify["shell"] == "bash"
    release_smoke = next(
        step
        for step in artifact_steps
        if step["name"] == "Smoke release modules without installing the project"
    )
    assert "python -m scripts.build_distributions --help" in release_smoke["run"]
    assert "python -m scripts.verify_distribution --help" in release_smoke["run"]
    private_release = next(
        step for step in artifact_steps if step["name"] == "Prepare private release runtime"
    )
    assert "python -m scripts.prepare_ci_runtime" in private_release["run"]
    assert private_release["shell"] == "bash"
    output = next(step for step in artifact_steps if step["name"] == "Bind private release output")
    assert output["id"] == "release-output"
    assert output["shell"] == "bash"
    assert output["run"] == ('printf \'path=%s\\n\' "${AGENCY_CI_TEMP}/dist" >> "${GITHUB_OUTPUT}"')
    artifact_uploads = [
        step for step in artifact_steps if "upload-artifact@" in step.get("uses", "")
    ]
    assert len(artifact_uploads) == 1
    assert artifact_uploads[0]["with"]["name"] == "python-distributions-${{ matrix.os }}"

    parity_job = workflow["jobs"]["artifact-parity"]
    assert parity_job["needs"] == "artifacts"
    parity_steps = parity_job["steps"]
    linux_download = next(
        step for step in parity_steps if step["name"] == "Download Linux distributions"
    )
    windows_download = next(
        step for step in parity_steps if step["name"] == "Download Windows distributions"
    )
    assert linux_download["with"] == {
        "name": "python-distributions-ubuntu-24.04",
        "path": "${{ runner.temp }}/agency-dist-linux",
    }
    assert windows_download["with"] == {
        "name": "python-distributions-windows-2022",
        "path": "${{ runner.temp }}/agency-dist-windows",
    }
    compare_index = next(
        index
        for index, step in enumerate(parity_steps)
        if step["name"] == "Require one byte-identical cross-platform artifact pair"
    )
    publish_index = next(
        index
        for index, step in enumerate(parity_steps)
        if step["name"] == "Publish verified canonical distributions"
    )
    assert publish_index > compare_index
    compare = parity_steps[compare_index]
    assert compare["shell"] == "bash"
    assert "if" not in compare
    assert "continue-on-error" not in compare
    for required in (
        'test "$(find "${RUNNER_TEMP}/agency-dist-linux" -maxdepth 1 -type f | wc -l)" -eq 2',
        'test "$(find "${RUNNER_TEMP}/agency-dist-windows" -maxdepth 1 -type f | wc -l)" -eq 2',
        "diff --brief --recursive",
        '"${RUNNER_TEMP}/agency-dist-linux"',
        '"${RUNNER_TEMP}/agency-dist-windows"',
    ):
        assert required in compare["run"]
    publish = parity_steps[publish_index]
    assert publish["uses"] == ("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a")
    assert "if" not in publish
    assert "continue-on-error" not in publish
    assert publish["with"] == {
        "name": "python-distributions",
        "path": "${{ runner.temp }}/agency-dist-linux/*",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    canonical_uploads = [
        step
        for candidate_job in workflow["jobs"].values()
        for step in candidate_job.get("steps", ())
        if "upload-artifact@" in step.get("uses", "")
        and step.get("with", {}).get("name") == "python-distributions"
    ]
    assert canonical_uploads == [publish]

    job = workflow["jobs"]["artifact-smoke"]
    assert set(job["needs"]) == {"artifacts", "artifact-parity"}
    assert set(job["strategy"]["matrix"]["os"]) == {"ubuntu-24.04", "windows-2022"}

    steps = job["steps"]
    canonical_download = next(step for step in steps if step["name"] == "Download distributions")
    assert canonical_download["with"] == {
        "name": "python-distributions",
        "path": "${{ runner.temp }}/agency-dist",
    }
    node_step = next(step for step in steps if step["name"].startswith("Set up Node.js"))
    assert node_step["with"]["node-version"] == "24"
    private_runtime_step = next(
        step for step in steps if step["name"] == "Prepare private artifact runtime"
    )
    assert "python -m scripts.prepare_ci_runtime" in private_runtime_step["run"]
    assert private_runtime_step["shell"] == "bash"
    assert private_runtime_step["env"] == {
        "AGENCY_CI_RUN_ATTEMPT": "${{ github.run_attempt }}",
        "AGENCY_CI_RUN_ID": "${{ github.run_id }}",
    }
    assert (
        '--label "artifact-smoke-${AGENCY_CI_RUN_ID}-${AGENCY_CI_RUN_ATTEMPT}"'
        in private_runtime_step["run"]
    )
    assert "${{" not in private_runtime_step["run"]
    smoke_step = next(step for step in steps if "source distribution" in step["name"])
    assert smoke_step["working-directory"] == "${{ runner.temp }}"
    script = smoke_step["run"]
    for required in (
        'EXPECTED_VERSION="$(python "${GITHUB_WORKSPACE}/scripts/read_release_version.py"',
        'python -m venv --copies "${AGENCY_CI_TEMP}/wheel-smoke"',
        'python -m venv --copies "${AGENCY_CI_TEMP}/sdist-smoke"',
        'export HOME="${AGENCY_CI_HOME}/${label}"',
        'export TMPDIR="${AGENCY_CI_TEMP}"',
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


def test_maintained_release_instructions_require_canonical_git_blob_builder() -> None:
    for relative in ("CONTRIBUTING.md", "docs/RELEASE_CHECKLIST.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert (
            'python -m scripts.build_distributions "${AGENCY_DIST_DIR}" --create-private-parent'
        ) in text
        assert "python -m scripts.verify_distribution" in text
        assert 'AGENCY_DIST_DIR="${HOME}/.agency-runtime/release-artifacts/' in text
        assert "python -m build --sdist --wheel" not in text

    from scripts.verify_distribution import REQUIRED_SDIST_FILES

    assert "scripts/build_distributions.py" in REQUIRED_SDIST_FILES
    assert "scripts/prove_autocrlf_checkout.py" in REQUIRED_SDIST_FILES
    assert "scripts/release_contract.py" in REQUIRED_SDIST_FILES
    assert "scripts/release_git.py" in REQUIRED_SDIST_FILES
    checklist = (ROOT / "docs/RELEASE_CHECKLIST.md").read_text(encoding="utf-8")
    for module in RELEASE_COVERAGE_MODULES:
        assert f"--cov=scripts.{module}" in checklist


def test_quality_and_matrix_jobs_use_private_runtime_state_boundaries() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    assert workflow["jobs"]["test"]["timeout-minutes"] == 45

    for job_name, preparation_name in (
        ("quality", "Prepare private test runtime"),
        ("test", "Prepare private test runtime"),
    ):
        steps = workflow["jobs"][job_name]["steps"]
        preparation = next(step for step in steps if step["name"] == preparation_name)
        execution = next(
            step
            for step in steps
            if step["name"]
            in {
                "Run warning-strict 100% line and branch coverage",
                "Run tests",
            }
        )
        assert "python -m scripts.prepare_ci_runtime" in preparation["run"]
        assert preparation["shell"] == "bash"
        assert preparation["env"]["AGENCY_CI_RUN_ID"] == "${{ github.run_id }}"
        assert preparation["env"]["AGENCY_CI_RUN_ATTEMPT"] == "${{ github.run_attempt }}"
        assert "${{" not in preparation["run"]
        if job_name == "test":
            assert preparation["env"]["AGENCY_CI_MATRIX_PYTHON"] == "${{ matrix.python }}"
            assert (
                "tests-py${AGENCY_CI_MATRIX_PYTHON}-${AGENCY_CI_RUN_ID}-${AGENCY_CI_RUN_ATTEMPT}"
            ) in preparation["run"]
        else:
            assert "quality-${AGENCY_CI_RUN_ID}-${AGENCY_CI_RUN_ATTEMPT}" in preparation["run"]
            for module in RELEASE_COVERAGE_MODULES:
                assert f"--cov=scripts.{module}" in execution["run"]
        for boundary in (
            'export HOME="${AGENCY_CI_HOME}"',
            'export USERPROFILE="${AGENCY_CI_HOME}"',
            'export TMPDIR="${AGENCY_CI_TEMP}"',
            "unset AGENCY_CONFIG_PATH AGENCY_DB_PATH",
            '"${AGENCY_CI_PYTHON}" -m pytest',
        ):
            assert boundary in execution["run"]


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
    assert workflow["jobs"]["dependency-review"]["timeout-minutes"] == 20

    probe = next(step for step in steps if step["name"] == "Detect dependency review capability")
    assert "dependency-graph/compare/${BASE_SHA}...${HEAD_SHA}" in probe["run"]
    assert "403|404" in probe["run"]
    assert "exit 1" in probe["run"]

    native = next(step for step in steps if step["name"] == "Reject vulnerable dependency changes")
    assert native["if"].endswith("available == 'true'")
    assert native["with"]["fail-on-severity"] == "moderate"

    install = next(
        step for step in steps if step["name"] == "Install runtime and pinned fallback audit tool"
    )
    assert install["if"].endswith("available == 'false'")
    assert "pip install ." in install["run"]
    assert "pip install --no-deps ." not in install["run"]
    assert 'pip install "pip-audit==2.10.1"' in install["run"]
    assert ".[security]" not in install["run"]

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
