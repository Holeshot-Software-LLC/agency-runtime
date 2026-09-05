from __future__ import annotations

import json
import os
import re
import shlex
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
from scripts.release_contract import DISTRIBUTION_LICENSE_FILES
from scripts.run_local_gates import PRODUCTION_SPINE, gates
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
QUALITY_GATE_NEEDS = (
    "quality-contracts",
    "coverage-complete",
    "performance",
    "test",
    "windows-portability-contract",
    "artifact-parity",
    "security",
)


def _quality_gate_script() -> str:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    run = workflow["jobs"]["quality"]["steps"][0]["run"]
    prefix = "python - <<'PY'\n"
    suffix = "\nPY\n"
    assert run.startswith(prefix)
    assert run.endswith(suffix)
    return run.removeprefix(prefix).removesuffix(suffix)


def _quality_gate_results(
    test_result: str | None,
    *,
    coverage_result: str | None = "success",
) -> dict[str, object]:
    return {
        name: {
            "result": (
                test_result
                if name == "test"
                else coverage_result
                if name == "coverage-complete"
                else "success"
            )
        }
        for name in QUALITY_GATE_NEEDS
    }


def _run_quality_gate(
    event_name: str,
    needs: dict[str, object],
    *,
    code_required: str = "true",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        CODE_REQUIRED=code_required,
        EVENT_NAME=event_name,
        NEEDS_JSON=json.dumps(needs),
    )
    return subprocess.run(
        [sys.executable, "-c", _quality_gate_script()],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _load_codeql_workflow() -> dict[object, object]:
    return yaml.safe_load((ROOT / ".github" / "workflows" / "codeql.yml").read_text("utf-8"))


def _embedded_python_script(run: str) -> str:
    prefix = "python - <<'PY'\n"
    suffix = "\nPY\n"
    assert run.startswith(prefix)
    assert run.endswith(suffix)
    return run.removeprefix(prefix).removesuffix(suffix)


def _run_codeql_result(
    capability_result: str,
    availability: str,
    analyze_result: str,
) -> subprocess.CompletedProcess[str]:
    workflow = _load_codeql_workflow()
    step = workflow["jobs"]["codeql"]["steps"][0]
    env = os.environ.copy()
    env.update(
        ANALYZE_RESULT=analyze_result,
        CAPABILITY_AVAILABLE=availability,
        CAPABILITY_RESULT=capability_result,
    )
    return subprocess.run(
        [sys.executable, "-c", _embedded_python_script(step["run"])],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _load_dependency_review_workflow() -> dict[object, object]:
    return yaml.safe_load(
        (ROOT / ".github" / "workflows" / "dependency-review.yml").read_text("utf-8")
    )


def _dependency_review_step(name: str) -> dict[str, object]:
    workflow = _load_dependency_review_workflow()
    return next(
        step for step in workflow["jobs"]["dependency-review"]["steps"] if step["name"] == name
    )


def _repository_identity_payload(
    *,
    full_name: str = "example/agency-runtime",
    visibility: str = "private",
    fork: bool = False,
    pull: bool = True,
) -> dict[str, object]:
    return {
        "fork": fork,
        "full_name": full_name,
        "permissions": {"pull": pull},
        "private": visibility != "public",
        "visibility": visibility,
    }


DEPENDENCY_REVIEW_UNAVAILABLE = {
    "documentation_url": "https://docs.github.com/rest/dependency-graph/dependency-review#get-a-diff-of-the-dependencies-between-commits",
    "message": "Forbidden",
    "status": "403",
}


def _run_dependency_capability_classifier(
    tmp_path: Path,
    *,
    repository_status: str = "200",
    repository_payload: object | None = None,
    repository_text: str | None = None,
    comparison_status: str = "200",
    comparison_payload: object | None = None,
    comparison_text: str | None = None,
    expected_visibility: str = "private",
    expected_fork: str = "false",
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    repository_response = tmp_path / "repository.json"
    comparison_response = tmp_path / "comparison.json"
    output = tmp_path / "github-output"
    repository_response.write_text(
        (
            json.dumps(
                _repository_identity_payload() if repository_payload is None else repository_payload
            )
            if repository_text is None
            else repository_text
        ),
        encoding="utf-8",
    )
    comparison_response.write_text(
        (
            json.dumps([] if comparison_payload is None else comparison_payload)
            if comparison_text is None
            else comparison_text
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        COMPARISON_HTTP_STATUS=comparison_status,
        COMPARISON_RESPONSE=str(comparison_response),
        EXPECTED_FORK=expected_fork,
        EXPECTED_REPOSITORY="example/agency-runtime",
        EXPECTED_VISIBILITY=expected_visibility,
        GITHUB_OUTPUT=str(output),
        REPOSITORY_HTTP_STATUS=repository_status,
        REPOSITORY_RESPONSE=str(repository_response),
    )
    classifier = _dependency_review_step("Classify dependency review capability")
    completed = subprocess.run(
        [sys.executable, "-c", _embedded_python_script(classifier["run"])],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = {}
    if output.is_file():
        outputs = dict(
            line.split("=", 1)
            for line in output.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
    return completed, outputs


def _run_dependency_review_result(
    availability: str,
    *,
    checkout: str = "success",
    probe: str = "success",
    capability: str = "success",
    native: str | None = None,
    fallback_python: str | None = None,
    fallback_install: str | None = None,
    fallback_audit: str | None = None,
) -> subprocess.CompletedProcess[str]:
    native = ("success" if availability == "true" else "skipped") if native is None else native
    fallback_default = "skipped" if availability == "true" else "success"
    env = os.environ.copy()
    env.update(
        CAPABILITY_AVAILABLE=availability,
        CAPABILITY_OUTCOME=capability,
        CHECKOUT_OUTCOME=checkout,
        FALLBACK_AUDIT_OUTCOME=(fallback_default if fallback_audit is None else fallback_audit),
        FALLBACK_INSTALL_OUTCOME=(
            fallback_default if fallback_install is None else fallback_install
        ),
        FALLBACK_PYTHON_OUTCOME=(fallback_default if fallback_python is None else fallback_python),
        NATIVE_REVIEW_OUTCOME=native,
        PROBE_OUTCOME=probe,
    )
    aggregate = _dependency_review_step("Require a coherent dependency review outcome")
    return subprocess.run(
        [sys.executable, "-c", _embedded_python_script(aggregate["run"])],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
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
    # PR #129 added substantial workforce/dashboard lifecycle UI (dashboard-render
    # grew ~25%). The original 256 KiB budget no longer accommodates the full
    # unmodified JS (required for 100% V8 branch coverage) plus minified CSS/HTML.
    # AR-188 adds the authenticated update projection and attended-command banner;
    # the later README-reality work adds traceable product proof projections. AR-236
    # adds source-separated selection, latency, child-delivery, Rule-8, and wiring
    # evidence. AR-290 adds the four-stage guided setup journey, and AR-296 adds
    # the bounded effective-profile/route authority projection. AR-297 adds explicit
    # managed-policy authority and AR-298 adds complete governed prompt visibility.
    # Keep that production behavior readable and branch-testable while retaining a
    # narrow ceiling above the audited 386,366-byte payload.
    assert dashboard_bytes < 378 * 1024, "dashboard assets exceeded the 378 KiB budget"


@pytest.mark.parametrize("gate_source", ("local", "hosted"))
def test_dashboard_coverage_gates_measure_all_production_javascript(gate_source: str) -> None:
    expected = (
        "node",
        "--test",
        "--experimental-test-coverage",
        "--test-coverage-include=agency_runtime/dashboard/**/*.js",
        "--test-coverage-lines=95",
        "--test-coverage-branches=86",
        "--test-coverage-functions=93",
        "tests/dashboard_ui.test.mjs",
    )
    if gate_source == "local":
        command = next(gate.command for gate in gates() if gate.name == "dashboard UI")
    else:
        workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
        step = next(
            item
            for item in workflow["jobs"]["quality-contracts"]["steps"]
            if item["name"] == "Run dashboard UI tests with coverage"
        )
        command = tuple(shlex.split(step["run"]))
    # The recursive product-wide selector admits future dashboard modules too.
    # Exact argv parity rejects narrower file lists, exclusions, and lower floors.
    assert command == expected


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

    parsed = tomllib.loads(pyproject)
    assert parsed["project"]["license-files"] == list(DISTRIBUTION_LICENSE_FILES)
    for relative in DISTRIBUTION_LICENSE_FILES:
        assert ROOT.joinpath(*relative.split("/")).is_file(), relative


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
    assert artifact_job["env"]["AGENCY_ARTIFACT_SET"] == "${{ matrix.artifact_set }}"
    assert artifact_job["runs-on"] == "${{ matrix.os }}"
    assert artifact_job["timeout-minutes"] == 35
    assert artifact_job["strategy"]["matrix"]["include"] == [
        {"os": "ubuntu-24.04", "artifact_set": "portable"},
        {"os": "windows-2022", "artifact_set": "windows-x64"},
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
    assert '--artifact-set "${AGENCY_ARTIFACT_SET}"' in verify["run"]
    assert verify["shell"] == "bash"
    release_smoke = next(
        step
        for step in artifact_steps
        if step["name"] == "Smoke release modules without installing the project"
    )
    assert "python -m scripts.build_distributions --help" in release_smoke["run"]
    assert "python -m scripts.verify_distribution --help" in release_smoke["run"]
    assert artifact_steps.index(autocrlf) < artifact_steps.index(build)
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
    assert artifact_uploads[0]["with"]["name"] == (
        "python-distributions-unsigned-review-${{ matrix.os }}"
    )
    smoke_python = next(
        step
        for step in artifact_steps
        if step["name"] == "Set up minimum supported Python for installed smoke"
    )
    assert smoke_python["id"] == "smoke-python"
    assert smoke_python["with"]["python-version"] == "3.10"
    node_step = next(step for step in artifact_steps if step["name"].startswith("Set up Node.js"))
    assert node_step["with"]["node-version"] == "24"
    installed_smoke = next(
        step
        for step in artifact_steps
        if step["name"] == "Install and smoke-test the platform wheel and source distribution"
    )
    assert installed_smoke["working-directory"] == "${{ runner.temp }}"
    assert installed_smoke["env"] == {
        "AGENCY_CI_SMOKE_PYTHON": "${{ steps.smoke-python.outputs.python-path }}"
    }
    smoke_script = installed_smoke["run"]
    for required in (
        '"${AGENCY_CI_SMOKE_PYTHON}" -m venv --copies',
        'export HOME="${AGENCY_CI_HOME}/${label}"',
        '"${AGENCY_CI_TEMP}"/dist/*.whl',
        '"${AGENCY_CI_TEMP}"/dist/*.tar.gz',
        "--no-cache-dir --only-binary=:all:",
        '--artifact-set "${AGENCY_ARTIFACT_SET}"',
        'subprocess.run([sys.argv[1], "--version"]',
        '"${agency}" smoke --all --json',
        '"${agency}" config show',
        '"${python}" -m pip check',
        'smoke_distribution wheel "${WHEEL_PYTHON}"',
        'smoke_distribution sdist "${SDIST_PYTHON}"',
    ):
        assert required in smoke_script
    assert artifact_steps.index(verify) < artifact_steps.index(installed_smoke)
    assert artifact_steps.index(installed_smoke) < artifact_steps.index(artifact_uploads[0])

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
        "name": "python-distributions-unsigned-review-ubuntu-24.04",
        "path": "${{ runner.temp }}/agency-dist-linux",
    }
    assert windows_download["with"] == {
        "name": "python-distributions-unsigned-review-windows-2022",
        "path": "${{ runner.temp }}/agency-dist-windows",
    }
    compare_index = next(
        index
        for index, step in enumerate(parity_steps)
        if step["name"] == "Require one byte-identical sdist and assemble the unsigned review set"
    )
    publish_index = next(
        index
        for index, step in enumerate(parity_steps)
        if step["name"] == "Upload verified canonical unsigned review distributions"
    )
    assert publish_index > compare_index
    compare = parity_steps[compare_index]
    assert compare["shell"] == "bash"
    assert "if" not in compare
    assert "continue-on-error" not in compare
    for required in (
        'test "$(find "${RUNNER_TEMP}/agency-dist-linux" -maxdepth 1 -type f | wc -l)" -eq 2',
        'test "$(find "${RUNNER_TEMP}/agency-dist-windows" -maxdepth 1 -type f | wc -l)" -eq 2',
        "*-py3-none-any.whl",
        "*-py3-none-win_amd64.whl",
        "sha256sum",
        "cmp --silent",
        "cp --no-clobber",
        'test "$(find "${RUNNER_TEMP}/agency-dist-release" -maxdepth 1 -type f | wc -l)" -eq 3',
    ):
        assert required in compare["run"]
    combined_verify = next(
        step
        for step in parity_steps
        if step["name"] == "Verify the combined three-artifact unsigned review contract"
    )
    assert "--artifact-set release" in combined_verify["run"]
    assert '--expected-commit "${AGENCY_RELEASE_COMMIT}"' in combined_verify["run"]
    assert parity_steps.index(combined_verify) > compare_index
    assert parity_steps.index(combined_verify) < publish_index
    publish = parity_steps[publish_index]
    assert publish["uses"] == ("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a")
    assert "if" not in publish
    assert "continue-on-error" not in publish
    assert publish["with"] == {
        "name": "python-distributions-unsigned-review",
        "path": "${{ runner.temp }}/agency-dist-release/*",
        "if-no-files-found": "error",
        "retention-days": 7,
    }
    canonical_uploads = [
        step
        for candidate_job in workflow["jobs"].values()
        for step in candidate_job.get("steps", ())
        if "upload-artifact@" in step.get("uses", "")
        and step.get("with", {}).get("name") == "python-distributions-unsigned-review"
    ]
    assert canonical_uploads == [publish]
    assert "artifact-smoke" not in workflow["jobs"]


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
    assert "scripts/build_windows_operator_presence.py" not in REQUIRED_SDIST_FILES
    assert "scripts/platform_wheel.py" in REQUIRED_SDIST_FILES
    assert "scripts/prove_autocrlf_checkout.py" in REQUIRED_SDIST_FILES
    assert "scripts/release_contract.py" in REQUIRED_SDIST_FILES
    assert "scripts/release_git.py" in REQUIRED_SDIST_FILES
    assert "setup.py" in REQUIRED_SDIST_FILES


def test_coverage_and_matrix_jobs_use_private_runtime_state_boundaries() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    assert workflow["jobs"]["coverage"]["timeout-minutes"] == 35
    assert workflow["jobs"]["test"]["timeout-minutes"] == 70
    coverage = next(
        step
        for step in workflow["jobs"]["coverage"]["steps"]
        if step["name"] == "Run paired coverage sessions"
    )
    assert coverage["shell"] == "bash"
    assert "scripts.run_ci_session_pair coverage" in coverage["run"]
    assert coverage["env"] == {
        "AGENCY_CI_PAIR": "${{ matrix.pair }}",
        "AGENCY_CI_PYTHON": "${{ steps.coverage-python.outputs.python-path }}",
        "AGENCY_CI_RUN_LABEL": (
            "${{ github.run_id }}-${{ github.run_attempt }}-p${{ matrix.pair }}"
        ),
        "AGENCY_CI_SHARD_A": "${{ matrix.shard_a }}",
        "AGENCY_CI_SHARD_B": "${{ matrix.shard_b }}",
    }

    compatibility = next(
        step
        for step in workflow["jobs"]["test"]["steps"]
        if step["name"] == "Run paired compatibility sessions"
    )
    assert compatibility["shell"] == "bash"
    assert "scripts.run_ci_session_pair compatibility" in compatibility["run"]
    assert compatibility["env"]["AGENCY_CI_PYTHON_A"] == (
        "${{ steps.python-a.outputs.python-path }}"
    )
    assert compatibility["env"]["AGENCY_CI_PYTHON_B"] == (
        "${{ steps.python-b.outputs.python-path }}"
    )

    runner = (ROOT / "scripts" / "run_ci_session_pair.py").read_text(encoding="utf-8")
    for boundary in (
        '"COVERAGE_FILE": str(coverage_file)',
        '"HOME": home',
        '"TEMP": temporary',
        '"TMPDIR": temporary',
        '"USERPROFILE": home',
        "run_bounded_binary_process",
        "ThreadPoolExecutor(max_workers=2",
    ):
        assert boundary in runner
    for module in RELEASE_COVERAGE_MODULES:
        assert f'"scripts.{module}"' in runner


def test_quality_first_gates_expensive_fanout_and_preserves_production_surfaces() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    jobs = workflow["jobs"]
    assert "needs" not in jobs["quality-contracts"]
    for job_name in (
        "performance",
        "windows-portability-contract",
        "security",
    ):
        assert jobs[job_name]["needs"] == "quality-contracts"
        assert jobs[job_name]["if"] == (
            "needs.quality-contracts.result == 'success' && "
            "needs.quality-contracts.outputs.code_required == 'true'"
        )
    manual_integration_condition = (
        "github.event_name == 'workflow_dispatch' && "
        "needs.quality-contracts.result == 'success' && "
        "needs.quality-contracts.outputs.code_required == 'true'"
    )
    assert jobs["coverage"]["if"] == manual_integration_condition
    assert jobs["test"]["if"] == manual_integration_condition
    assert jobs["coverage"]["name"].startswith("integration coverage / ")
    assert jobs["coverage-complete"]["name"] == "integration coverage / combined"
    assert jobs["test"]["name"].startswith("integration / full compatibility / ")
    assert jobs["quality"]["name"] == "automatic gates; integration suites are manual"
    assert jobs["artifacts"]["needs"] == "quality-contracts"
    assert "if" not in jobs["artifacts"]
    assert jobs["coverage"]["strategy"]["matrix"]["include"] == [
        {"pair": 0, "label": 1, "shard_a": 0, "shard_b": 1},
        {"pair": 1, "label": 2, "shard_a": 2, "shard_b": 3},
    ]
    coverage_run = next(
        step for step in jobs["coverage"]["steps"] if step["name"] == "Run paired coverage sessions"
    )["run"]
    assert "scripts.run_ci_session_pair coverage" in coverage_run
    assert '--shard-a "${AGENCY_CI_SHARD_A}"' in coverage_run
    assert '--shard-b "${AGENCY_CI_SHARD_B}"' in coverage_run
    assert jobs["coverage-complete"]["needs"] == "coverage"
    combined_run = jobs["coverage-complete"]["steps"][-1]["run"]
    assert "coverage combine" in combined_run
    assert "coverage report --fail-under=97" in combined_run
    performance_run = jobs["performance"]["steps"][-1]["run"]
    assert "-m performance" in performance_run
    assert "tests/test_candidate_narrow_scaling.py" in performance_run
    assert "tests/test_routing_eval_suite.py" in performance_run
    assert "pytest tests " not in performance_run
    quality_steps = {step["name"]: step for step in jobs["quality-contracts"]["steps"]}
    assert {
        "Classify the complete event delta",
        "Check dependency consistency",
        "Check patch whitespace",
        "Check tracked release inputs",
        "Check out canonical documentation history",
        "Install documentation dependencies",
        "Prepare private quality runtime",
        "Run fast Python production spine",
        "Run AR-119 matrix evidence",
        "Verify fast workflow contracts",
        "Run dashboard UI tests with coverage",
        "Verify documentation ledgers",
    } <= set(quality_steps)
    assert jobs["quality-contracts"]["outputs"] == {
        "code_required": "${{ steps.change-scope.outputs.code_required }}",
        "scope_reason": "${{ steps.change-scope.outputs.scope_reason }}",
    }
    dashboard_coverage = quality_steps["Run dashboard UI tests with coverage"]["run"]
    assert "--test-coverage-lines=95" in dashboard_coverage
    assert "--test-coverage-branches=86" in dashboard_coverage
    assert "--test-coverage-functions=93" in dashboard_coverage
    classifier = quality_steps["Classify the complete event delta"]
    assert classifier["id"] == "change-scope"
    assert classifier["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "EVENT_NAME": "${{ github.event_name }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha || github.sha }}",
    }
    assert "scripts/classify_ci_change.py" in classifier["run"]
    assert classifier["shell"] == "bash"
    for required in (
        'git ls-tree "${BASE_SHA}" -- "${classifier_path}"',
        'mktemp "${RUNNER_TEMP}/agency-ci-scope.',
        'git cat-file blob "${classifier_object}" > "${trusted_classifier}"',
        'python -I "${trusted_classifier}"',
        '--root "${GITHUB_WORKSPACE}"',
        "scope_reason=trusted_classifier_unavailable",
    ):
        assert required in classifier["run"]
    assert "python scripts/classify_ci_change.py" not in classifier["run"]
    assert quality_steps["Install development dependencies"]["if"].endswith(
        "code_required == 'true'"
    )
    assert quality_steps["Install documentation dependencies"] == {
        "name": "Install documentation dependencies",
        "if": "steps.change-scope.outputs.code_required == 'false'",
        "run": "python -m pip install .",
    }
    assert "if" not in quality_steps["Check patch whitespace"]
    assert "if" not in quality_steps["Check tracked release inputs"]
    assert "if" not in quality_steps["Verify documentation ledgers"]
    whitespace = quality_steps["Check patch whitespace"]
    assert whitespace["shell"] == "bash"
    assert whitespace["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "BEFORE_SHA": "${{ github.event.before }}",
        "EVENT_NAME": "${{ github.event_name }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha || github.sha }}",
    }
    for required in (
        'git ls-tree "${trusted_ref}" -- "${whitespace_path}"',
        'mktemp "${RUNNER_TEMP}/agency-ci-whitespace.',
        'git cat-file blob "${whitespace_object}" > "${trusted_whitespace}"',
        'python -I "${trusted_whitespace}"',
        '--base-sha "${BASE_SHA}"',
        '--before-sha "${BEFORE_SHA}"',
        'git diff --check "${comparison}" --',
    ):
        assert required in whitespace["run"]
    assert 'git diff --check "${comparison}" -- >/dev/null 2>&1' in whitespace["run"]
    assert 'echo "::error::Committed whitespace check failed."' in whitespace["run"]
    assert "python scripts/check_ci_whitespace.py" not in whitespace["run"]
    assert quality_steps["Check dependency consistency"]["run"] == "python -m pip check"
    private_quality = quality_steps["Prepare private quality runtime"]
    assert private_quality["if"] == "steps.change-scope.outputs.code_required == 'true'"
    assert "python -m scripts.prepare_ci_runtime" in private_quality["run"]
    assert (
        '--label "quality-${AGENCY_CI_RUN_ID}-${AGENCY_CI_RUN_ATTEMPT}"' in private_quality["run"]
    )
    quality_step_order = [step["name"] for step in jobs["quality-contracts"]["steps"]]
    assert quality_step_order.index("Install development dependencies") < quality_step_order.index(
        "Check dependency consistency"
    )
    quality_checkout = jobs["quality-contracts"]["steps"][0]
    assert quality_checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    quality_contracts = next(
        step
        for step in jobs["quality-contracts"]["steps"]
        if step["name"] == "Verify fast workflow contracts"
    )["run"]
    assert "tests/test_ci_change_scope.py tests/test_ci_sharding.py" in quality_contracts
    assert "tests/test_ci_session_pair.py tests/test_release_packaging.py" in quality_contracts
    assert '"${AGENCY_CI_PYTHON}" -m pytest' in quality_contracts
    assert 'export TMPDIR="${AGENCY_CI_TEMP}"' in quality_contracts
    assert '--basetemp "${AGENCY_CI_TEMP}/pytest-workflow"' in quality_contracts
    production_spine = quality_steps["Run fast Python production spine"]
    assert production_spine["if"] == "steps.change-scope.outputs.code_required == 'true'"
    assert 'export TMPDIR="${AGENCY_CI_TEMP}"' in production_spine["run"]
    assert '"${AGENCY_CI_PYTHON}" -m pytest' in production_spine["run"]
    assert '--basetemp "${AGENCY_CI_TEMP}/pytest-production-spine"' in production_spine["run"]
    # Derive the expectation from run_local_gates rather than pinning a third
    # copy of the list, the same way the matrix-evidence assertion below derives
    # its own. Four hand-kept copies existed and had already drifted: AGENTS.md
    # was missing test_storage_file_trust and test_upstream_selection_eval, so
    # the documented spine and the enforced one were different suites.
    assert re.findall(r"tests/test_[a-z0-9_]+\.py", production_spine["run"]) == list(
        PRODUCTION_SPINE
    )
    agents_text = Path("AGENTS.md").read_text(encoding="utf-8")
    documented = re.search(r"python -m pytest \\\n(.*?)\n  -q -W error", agents_text, re.DOTALL)
    assert documented, "the AGENTS.md production-spine block moved"
    assert re.findall(r"tests/test_[a-z0-9_]+\.py", documented.group(1)) == list(PRODUCTION_SPINE)
    matrix_evidence = quality_steps["Run AR-119 matrix evidence"]
    assert matrix_evidence["if"] == "steps.change-scope.outputs.code_required == 'true'"
    assert 'export TMPDIR="${AGENCY_CI_TEMP}"' in matrix_evidence["run"]
    assert '"${AGENCY_CI_PYTHON}" -m pytest' in matrix_evidence["run"]
    assert '--basetemp "${AGENCY_CI_TEMP}/pytest-matrix-evidence"' in matrix_evidence["run"]
    # Derive the expectation from the matrix rather than pinning a second copy
    # of the list.  A citation added to the matrix and not to CI fails here,
    # which is the drift that let R4 claude stay red behind a green pipeline.
    matrix_text = Path("docs/roadmap/AR-119-rule-host-evidence-matrix.md").read_text(
        encoding="utf-8"
    )
    cited = sorted(set(re.findall(r"`(tests/test_[a-z0-9_]+\.py)(?::\d+-\d+)?`", matrix_text)))
    assert cited, "the matrix cites no test files; the citation pattern moved"
    assert sorted(re.findall(r"tests/test_[a-z0-9_]+\.py", matrix_evidence["run"])) == cited

    assert jobs["test"]["strategy"]["matrix"]["include"] == [
        {
            "os": "ubuntu-24.04",
            "platform": "linux",
            "label": "ubuntu-310-311",
            "python_a": "3.10",
            "python_b": "3.11",
        },
        {
            "os": "ubuntu-24.04",
            "platform": "linux",
            "label": "ubuntu-312-314",
            "python_a": "3.12",
            "python_b": "3.14",
        },
        {
            "os": "windows-2022",
            "platform": "windows",
            "label": "windows-310-314",
            "python_a": "3.10",
            "python_b": "3.14",
        },
    ]
    assert jobs["quality"]["if"] == "always()"
    assert set(jobs["quality"]["needs"]) == set(QUALITY_GATE_NEEDS)
    aggregate_step = jobs["quality"]["steps"][0]
    assert aggregate_step["name"] == "Require every applicable production gate"
    assert aggregate_step["env"] == {
        "CODE_REQUIRED": "${{ needs.quality-contracts.outputs.code_required }}",
        "EVENT_NAME": "${{ github.event_name }}",
        "NEEDS_JSON": "${{ toJSON(needs) }}",
    }


def test_code_checks_keep_default_merge_revision_before_exact_head_ledgers() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    jobs = workflow["jobs"]
    steps = jobs["quality-contracts"]["steps"]
    source_checkout = steps[0]
    history_checkout = next(
        step for step in steps if step["name"] == "Check out canonical documentation history"
    )
    history_index = steps.index(history_checkout)

    assert source_checkout["name"] == "Check out source"
    assert source_checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert history_checkout["with"]["ref"] == (
        "${{ github.event.pull_request.head.sha || github.sha }}"
    )
    for name in (
        "Classify the complete event delta",
        "Check Python code quality",
        "Check patch whitespace",
        "Check tracked release inputs",
        "Verify fast workflow contracts",
        "Run dashboard UI tests with coverage",
    ):
        assert steps.index(next(step for step in steps if step["name"] == name)) < history_index

    for job_name in (
        "coverage",
        "performance",
        "windows-portability-contract",
        "artifacts",
        "security",
    ):
        checkout = next(
            step for step in jobs[job_name]["steps"] if step["name"] == "Check out source"
        )
        assert checkout["with"] == {"persist-credentials": False}


def test_docs_only_lane_keeps_same_revision_sdist_producers() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    jobs = workflow["jobs"]
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "recursive-include docs *.md" in manifest
    assert jobs["artifacts"]["needs"] == "quality-contracts"
    assert "if" not in jobs["artifacts"]
    assert jobs["artifact-parity"]["needs"] == "artifacts"
    artifact_checkout = next(
        step for step in jobs["artifacts"]["steps"] if step["name"] == "Check out source"
    )
    assert artifact_checkout["with"] == {"persist-credentials": False}


@pytest.mark.parametrize(
    ("event_name", "test_result", "coverage_result"),
    [
        ("pull_request", "skipped", "skipped"),
        ("push", "skipped", "skipped"),
        ("workflow_dispatch", "success", "success"),
    ],
)
def test_quality_aggregate_accepts_only_event_appropriate_integration_results(
    event_name: str,
    test_result: str,
    coverage_result: str,
) -> None:
    completed = _run_quality_gate(
        event_name,
        _quality_gate_results(test_result, coverage_result=coverage_result),
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    ("event_name", "job_name", "result"),
    [
        ("pull_request", "coverage-complete", "success"),
        ("pull_request", "test", "success"),
        ("push", "coverage-complete", "success"),
        ("push", "test", "success"),
        ("workflow_dispatch", "coverage-complete", "skipped"),
        ("workflow_dispatch", "coverage-complete", "failure"),
        ("workflow_dispatch", "coverage-complete", "cancelled"),
        ("workflow_dispatch", "test", "skipped"),
        ("workflow_dispatch", "test", "failure"),
        ("workflow_dispatch", "test", "cancelled"),
    ],
)
def test_quality_aggregate_rejects_wrong_integration_results(
    event_name: str,
    job_name: str,
    result: str,
) -> None:
    manual = event_name == "workflow_dispatch"
    needs = _quality_gate_results(
        "success" if manual else "skipped",
        coverage_result="success" if manual else "skipped",
    )
    needs[job_name] = {"result": result}

    completed = _run_quality_gate(event_name, needs)

    assert completed.returncode != 0
    assert f'"{job_name}"' in completed.stderr


@pytest.mark.parametrize(
    "job_name",
    [name for name in QUALITY_GATE_NEEDS if name not in {"coverage-complete", "test"}],
)
@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", None])
def test_quality_aggregate_requires_every_other_gate_to_succeed(
    job_name: str, result: str | None
) -> None:
    needs = _quality_gate_results("skipped", coverage_result="skipped")
    needs[job_name] = {"result": result}

    completed = _run_quality_gate("pull_request", needs)

    assert completed.returncode != 0
    assert f'"{job_name}"' in completed.stderr


@pytest.mark.parametrize("missing_job", QUALITY_GATE_NEEDS)
def test_quality_aggregate_rejects_missing_gate_results(missing_job: str) -> None:
    needs = _quality_gate_results("skipped", coverage_result="skipped")
    del needs[missing_job]

    completed = _run_quality_gate("pull_request", needs)

    assert completed.returncode != 0
    assert f'"{missing_job}"' in completed.stderr


def test_quality_aggregate_rejects_unknown_events_and_unexpected_jobs() -> None:
    unknown_event = _run_quality_gate(
        "schedule",
        _quality_gate_results("skipped", coverage_result="skipped"),
    )
    assert unknown_event.returncode != 0
    assert "unsupported workflow event" in unknown_event.stderr

    needs = _quality_gate_results("skipped", coverage_result="skipped")
    needs["unexpected"] = {"result": "success"}
    unexpected_job = _run_quality_gate("pull_request", needs)
    assert unexpected_job.returncode != 0
    assert '"unexpected_jobs"' in unexpected_job.stderr


def test_quality_aggregate_accepts_only_coherent_docs_only_pull_request_results() -> None:
    needs = _quality_gate_results("skipped")
    for name in QUALITY_GATE_NEEDS:
        if name != "quality-contracts":
            needs[name] = {"result": "skipped"}
    needs["artifact-parity"] = {"result": "success"}

    completed = _run_quality_gate(
        "pull_request",
        needs,
        code_required="false",
    )
    assert completed.returncode == 0, completed.stderr

    wrong_event = _run_quality_gate("push", needs, code_required="false")
    assert wrong_event.returncode != 0
    assert "only pull requests" in wrong_event.stderr

    needs["security"] = {"result": "success"}
    incoherent = _run_quality_gate(
        "pull_request",
        needs,
        code_required="false",
    )
    assert incoherent.returncode != 0
    assert '"security"' in incoherent.stderr


@pytest.mark.parametrize("code_required", ["", "unknown", "TRUE"])
def test_quality_aggregate_rejects_invalid_change_scope(code_required: str) -> None:
    completed = _run_quality_gate(
        "pull_request",
        _quality_gate_results("skipped"),
        code_required=code_required,
    )
    assert completed.returncode != 0
    assert "governed boolean" in completed.stderr


def test_history_derived_ledgers_use_the_complete_durable_head() -> None:
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    steps = workflow["jobs"]["quality-contracts"]["steps"]

    source_checkout = next(step for step in steps if step["name"] == "Check out source")
    checkout = next(
        step for step in steps if step["name"] == "Check out canonical documentation history"
    )
    ledger = next(step for step in steps if step["name"] == "Verify documentation ledgers")
    assert checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
        "ref": "${{ github.event.pull_request.head.sha || github.sha }}",
    }
    assert ledger["env"]["EXPECTED_HISTORY_HEAD"] == checkout["with"]["ref"]
    assert 'test "$(git rev-parse --is-shallow-repository)" = "false"' in ledger["run"]
    assert 'test "$(git rev-parse HEAD)" = "${EXPECTED_HISTORY_HEAD}"' in ledger["run"]
    assert "update_worklog.py --check" in ledger["run"]
    assert "python scripts/verify_docs.py" in ledger["run"]
    assert "--require-tracker" not in ledger["run"]
    assert source_checkout["with"] == {
        "fetch-depth": 0,
        "persist-credentials": False,
    }
    assert "ref" not in source_checkout["with"]
    assert steps.index(checkout) > steps.index(
        next(step for step in steps if step["name"] == "Run dashboard UI tests with coverage")
    )


def test_dependency_review_preserves_one_stable_least_privilege_gate() -> None:
    workflow = _load_dependency_review_workflow()
    assert workflow[True] == {"pull_request": None}
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "dependency-review-${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": True,
    }
    assert set(workflow["jobs"]) == {"dependency-review"}
    job = workflow["jobs"]["dependency-review"]
    assert job["name"] == "dependency review"
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] == 20

    checkout = _dependency_review_step("Check out source")
    assert checkout["id"] == "checkout"
    assert checkout["uses"] == ("actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0")
    assert checkout["with"] == {"persist-credentials": False}


def test_dependency_review_probe_is_authenticated_bounded_and_fail_closed() -> None:
    probe = _dependency_review_step("Probe repository identity and dependency review capability")
    assert probe["id"] == "dependency-review-probe"
    assert probe["env"] == {
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
        "GH_TOKEN": "${{ github.token }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
    }
    run = probe["run"]
    assert "set -euo pipefail" in run
    assert run.count("mktemp ") == 2
    assert run.count("--connect-timeout 10") == 2
    assert run.count("--max-time 30") == 2
    assert run.count("--max-filesize 1048576") == 2
    assert run.count("--write-out '%{http_code}'") == 2
    assert run.count("Authorization: Bearer ${GH_TOKEN}") == 2
    assert '"${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}"' in run
    assert "dependency-graph/compare/${BASE_SHA}...${HEAD_SHA}" in run
    assert run.count("if ! ") == 2
    assert run.count("exit 1") == 2
    assert "403|404" not in run
    assert "set -x" not in run
    assert "printf 'gh_token=" not in run.casefold()
    assert [line.strip() for line in run.splitlines() if line.strip().startswith("printf")] == [
        "printf 'repository_response=%s\\n' \"${repository_response}\"",
        "printf 'repository_http_status=%s\\n' \"${repository_status}\"",
        "printf 'comparison_response=%s\\n' \"${comparison_response}\"",
        "printf 'comparison_http_status=%s\\n' \"${comparison_status}\"",
    ]


def test_dependency_review_paths_are_exactly_gated_and_aggregated() -> None:
    classifier = _dependency_review_step("Classify dependency review capability")
    assert classifier["id"] == "dependency-review-capability"
    assert classifier["env"] == {
        "COMPARISON_HTTP_STATUS": (
            "${{ steps.dependency-review-probe.outputs.comparison_http_status }}"
        ),
        "COMPARISON_RESPONSE": ("${{ steps.dependency-review-probe.outputs.comparison_response }}"),
        "EXPECTED_FORK": "${{ github.event.repository.fork }}",
        "EXPECTED_REPOSITORY": "${{ github.repository }}",
        "EXPECTED_VISIBILITY": "${{ github.event.repository.visibility }}",
        "REPOSITORY_HTTP_STATUS": (
            "${{ steps.dependency-review-probe.outputs.repository_http_status }}"
        ),
        "REPOSITORY_RESPONSE": ("${{ steps.dependency-review-probe.outputs.repository_response }}"),
    }
    classifier_run = classifier["run"]
    for required in (
        're.fullmatch(r"[1-5][0-9]{2}", value)',
        "path.lstat()",
        "path.is_symlink()",
        "metadata.st_size <= maximum_bytes",
        "repository_status != 200",
        'repository.get("full_name") != expected_repository',
        'repository.get("private") is not (expected_visibility != "public")',
        "comparison_status == 403",
        '"message": "Forbidden"',
        '"status": "403"',
        "comparison == expected_forbidden",
        "dependency review capability response was ambiguous; refusing fallback",
    ):
        assert required in classifier_run
    assert '"vulnerability audit is compensating evidence, not equivalent "' in classifier_run
    assert '"dependency-change review."' in classifier_run
    assert "403|404" not in classifier_run

    native = _dependency_review_step("Reject vulnerable dependency changes")
    assert native["id"] == "native-review"
    assert native["if"].endswith("available == 'true'")
    assert native["uses"] == (
        "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294"
    )
    assert native["with"] == {
        "fail-on-severity": "moderate",
        "retry-on-snapshot-warnings": True,
    }

    setup = _dependency_review_step("Set up fallback Python")
    install = _dependency_review_step("Install runtime and pinned fallback audit tool")
    fallback = _dependency_review_step(
        "Audit installed runtime dependencies as non-equivalent compensating evidence"
    )
    for step in (setup, install, fallback):
        assert step["if"].endswith("available == 'false'")
    assert setup["id"] == "fallback-python"
    assert install["id"] == "fallback-install"
    assert fallback["id"] == "installed-runtime-audit"
    assert "pip install ." in install["run"]
    assert "pip install --no-deps ." not in install["run"]
    assert 'pip install "pip-audit==2.10.1"' in install["run"]
    assert ".[security]" not in install["run"]
    assert fallback["run"] == "python scripts/audit_runtime_dependencies.py"

    aggregate = _dependency_review_step("Require a coherent dependency review outcome")
    assert aggregate["id"] == "dependency-review-result"
    assert aggregate["if"] == "always()"
    assert aggregate["env"] == {
        "CAPABILITY_AVAILABLE": ("${{ steps.dependency-review-capability.outputs.available }}"),
        "CAPABILITY_OUTCOME": "${{ steps.dependency-review-capability.outcome }}",
        "CHECKOUT_OUTCOME": "${{ steps.checkout.outcome }}",
        "FALLBACK_AUDIT_OUTCOME": "${{ steps.installed-runtime-audit.outcome }}",
        "FALLBACK_INSTALL_OUTCOME": "${{ steps.fallback-install.outcome }}",
        "FALLBACK_PYTHON_OUTCOME": "${{ steps.fallback-python.outcome }}",
        "NATIVE_REVIEW_OUTCOME": "${{ steps.native-review.outcome }}",
        "PROBE_OUTCOME": "${{ steps.dependency-review-probe.outcome }}",
    }


@pytest.mark.parametrize(
    ("comparison_status", "comparison_payload", "available", "reason"),
    [
        ("200", [], "true", "repository_dependency_review_available"),
        (
            "403",
            DEPENDENCY_REVIEW_UNAVAILABLE,
            "false",
            "private_or_internal_repository_dependency_review_unavailable",
        ),
    ],
)
def test_dependency_review_classifier_accepts_only_proven_paths(
    tmp_path: Path,
    comparison_status: str,
    comparison_payload: object,
    available: str,
    reason: str,
) -> None:
    completed, outputs = _run_dependency_capability_classifier(
        tmp_path,
        comparison_status=comparison_status,
        comparison_payload=comparison_payload,
    )
    assert completed.returncode == 0, completed.stderr
    assert outputs == {
        "available": available,
        "http_status": comparison_status,
        "reason": reason,
    }
    if available == "false":
        assert "not equivalent dependency-change review" in completed.stdout


@pytest.mark.parametrize(
    ("comparison_status", "comparison_payload"),
    [
        (
            "403",
            {**DEPENDENCY_REVIEW_UNAVAILABLE, "unexpected": "field"},
        ),
        (
            "403",
            {**DEPENDENCY_REVIEW_UNAVAILABLE, "documentation_url": "https://example.invalid"},
        ),
        ("403", {"message": "API rate limit exceeded", "status": "403"}),
        ("404", {"message": "Not Found", "status": "404"}),
        ("401", {"message": "Bad credentials", "status": "401"}),
        ("500", {"message": "Server Error", "status": "500"}),
    ],
)
def test_dependency_review_classifier_rejects_ambiguous_api_responses(
    tmp_path: Path,
    comparison_status: str,
    comparison_payload: object,
) -> None:
    completed, outputs = _run_dependency_capability_classifier(
        tmp_path,
        comparison_status=comparison_status,
        comparison_payload=comparison_payload,
    )
    assert completed.returncode != 0
    assert outputs == {}
    assert "ambiguous; refusing fallback" in completed.stderr


@pytest.mark.parametrize(
    ("repository_status", "repository_payload", "expected_visibility", "expected_fork"),
    [
        ("401", {"message": "Bad credentials"}, "private", "false"),
        ("403", {"message": "Forbidden"}, "private", "false"),
        ("404", {"message": "Not Found"}, "private", "false"),
        ("200", _repository_identity_payload(full_name="other/repository"), "private", "false"),
        ("200", _repository_identity_payload(visibility="public"), "private", "false"),
        ("200", _repository_identity_payload(fork=True), "private", "false"),
        ("200", _repository_identity_payload(visibility="public"), "public", "false"),
        ("200", _repository_identity_payload(fork=True), "private", "true"),
    ],
)
def test_dependency_review_classifier_rejects_unproven_repository_identity_or_scope(
    tmp_path: Path,
    repository_status: str,
    repository_payload: object,
    expected_visibility: str,
    expected_fork: str,
) -> None:
    completed, outputs = _run_dependency_capability_classifier(
        tmp_path,
        repository_status=repository_status,
        repository_payload=repository_payload,
        comparison_status="403",
        comparison_payload=DEPENDENCY_REVIEW_UNAVAILABLE,
        expected_visibility=expected_visibility,
        expected_fork=expected_fork,
    )
    assert completed.returncode != 0
    assert outputs == {}


def test_dependency_review_classifier_accepts_exact_identity_without_permissions_projection(
    tmp_path: Path,
) -> None:
    repository = _repository_identity_payload()
    repository.pop("permissions")

    completed, outputs = _run_dependency_capability_classifier(
        tmp_path,
        repository_payload=repository,
        comparison_status="403",
        comparison_payload=DEPENDENCY_REVIEW_UNAVAILABLE,
    )

    assert completed.returncode == 0, completed.stderr
    assert outputs["available"] == "false"


@pytest.mark.parametrize(
    ("comparison_status", "comparison_text"),
    [
        ("403\nx", json.dumps(DEPENDENCY_REVIEW_UNAVAILABLE)),
        ("200", ""),
        ("200", "not-json"),
        ("200", "oversized"),
    ],
)
def test_dependency_review_classifier_rejects_malformed_or_unbounded_input(
    tmp_path: Path,
    comparison_status: str,
    comparison_text: str,
) -> None:
    if comparison_text == "oversized":
        comparison_text = "x" * (1024 * 1024 + 1)
    completed, outputs = _run_dependency_capability_classifier(
        tmp_path,
        comparison_status=comparison_status,
        comparison_text=comparison_text,
    )
    assert completed.returncode != 0
    assert outputs == {}


@pytest.mark.parametrize(
    ("availability", "expected"),
    [
        ("true", "Native dependency-diff review completed successfully."),
        (
            "false",
            "exact installed-runtime vulnerability evidence passed but is not equivalent",
        ),
    ],
)
def test_dependency_review_aggregate_accepts_only_coherent_outcomes(
    availability: str,
    expected: str,
) -> None:
    completed = _run_dependency_review_result(availability)
    assert completed.returncode == 0, completed.stderr
    assert expected in completed.stdout


@pytest.mark.parametrize(
    ("availability", "overrides"),
    [
        ("", {}),
        ("unknown", {}),
        ("true", {"checkout": "failure"}),
        ("true", {"probe": "cancelled"}),
        ("true", {"capability": "skipped"}),
        ("true", {"native": "failure"}),
        ("true", {"fallback_audit": "success"}),
        ("false", {"fallback_python": "failure"}),
        ("false", {"fallback_install": "cancelled"}),
        ("false", {"fallback_audit": "skipped"}),
        ("false", {"native": "success"}),
    ],
)
def test_dependency_review_aggregate_rejects_failed_missing_or_incoherent_outcomes(
    availability: str,
    overrides: dict[str, str],
) -> None:
    completed = _run_dependency_review_result(availability, **overrides)
    assert completed.returncode != 0
    assert "dependency review" in completed.stderr.casefold()


def test_codeql_preserves_events_and_exposes_one_stable_result() -> None:
    workflow = _load_codeql_workflow()
    assert workflow[True] == {
        "push": {"branches": ["main"]},
        "pull_request": {"branches": ["main"]},
        "schedule": [{"cron": "23 7 * * 1"}],
        "workflow_dispatch": None,
    }
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "codeql-${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": True,
    }
    assert set(workflow["jobs"]) == {"capability", "analyze", "codeql"}

    aggregate = workflow["jobs"]["codeql"]
    assert aggregate["name"] == "CodeQL result"
    assert aggregate["if"] == "always()"
    assert aggregate["needs"] == ["capability", "analyze"]
    assert aggregate["permissions"] == {"contents": "read"}


def test_codeql_runs_one_fail_closed_least_privilege_capability_probe() -> None:
    workflow = _load_codeql_workflow()
    capability = workflow["jobs"]["capability"]
    assert capability["permissions"] == {"contents": "read", "security-events": "read"}
    assert capability["outputs"] == {
        "available": "${{ steps.code-scanning-capability.outputs.available }}",
        "http_status": "${{ steps.code-scanning-capability.outputs.http_status }}",
        "reason": "${{ steps.code-scanning-capability.outputs.reason }}",
        "repository_visibility": (
            "${{ steps.code-scanning-capability.outputs.repository_visibility }}"
        ),
    }
    all_steps = [step for job in workflow["jobs"].values() for step in job["steps"]]
    probes = [step for step in all_steps if step["name"] == "Detect native CodeQL capability"]
    assert len(probes) == 1
    assert all(
        not step.get("uses", "").startswith("actions/checkout@") for step in capability["steps"]
    )

    probe = probes[0]
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


def test_codeql_available_path_preserves_exact_language_analyses() -> None:
    workflow = _load_codeql_workflow()
    job = workflow["jobs"]["analyze"]
    assert job["needs"] == "capability"
    assert job["if"] == "needs.capability.outputs.available == 'true'"
    assert job["strategy"] == {
        "fail-fast": False,
        "matrix": {"language": ["python", "javascript-typescript"]},
    }
    assert job["permissions"] == {
        "contents": "read",
        "packages": "read",
        "security-events": "write",
    }
    steps = job["steps"]
    checkout = next(step for step in steps if step["name"] == "Check out source")
    initialize = next(step for step in steps if step["name"] == "Initialize CodeQL")
    analyze = next(step for step in steps if step["name"] == "Analyze source")
    assert checkout["uses"] == ("actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0")
    assert checkout["with"] == {"persist-credentials": False}
    assert initialize["uses"] == (
        "github/codeql-action/init@99df26d4f13ea111d4ec1a7dddef6063f76b97e9"
    )
    assert initialize["with"] == {
        "languages": "${{ matrix.language }}",
        "queries": "security-extended",
    }
    assert analyze["uses"] == (
        "github/codeql-action/analyze@99df26d4f13ea111d4ec1a7dddef6063f76b97e9"
    )
    assert analyze["with"]["category"] == "/language:${{ matrix.language }}"
    assert analyze["with"]["upload"] == "always"
    assert analyze["with"]["output"] == "${{ runner.temp }}/codeql-results"
    assert all("if" not in step for step in steps)


def test_codeql_unavailable_path_records_both_languages_without_analysis(
    tmp_path: Path,
) -> None:
    workflow = _load_codeql_workflow()
    steps = workflow["jobs"]["capability"]["steps"]

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
        'for language in ("python", "javascript-typescript")',
    ):
        assert required in evidence["run"]

    env = os.environ.copy()
    env.update(
        CAPABILITY_HTTP_STATUS="403",
        CAPABILITY_REASON="private_or_internal_repository_code_security_not_enabled",
        GITHUB_EVENT_NAME="pull_request",
        GITHUB_REF="refs/pull/1/merge",
        GITHUB_REPOSITORY="example/agency-runtime",
        GITHUB_SHA="a" * 40,
        REPOSITORY_VISIBILITY="private",
        RUNNER_TEMP=str(tmp_path),
    )
    completed = subprocess.run(
        [sys.executable, "-c", _embedded_python_script(evidence["run"])],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    evidence_dir = tmp_path / "codeql-capability"
    assert sorted(path.name for path in evidence_dir.iterdir()) == [
        "javascript-typescript.json",
        "python.json",
    ]
    for language in ("python", "javascript-typescript"):
        payload = json.loads((evidence_dir / f"{language}.json").read_text("utf-8"))
        assert payload["language"] == language
        assert payload["available"] is False
        assert payload["analysis_performed"] is False
        assert payload["probe_http_status"] == 403

    retained = next(step for step in steps if step["name"] == "Retain CodeQL capability evidence")
    assert retained["if"].endswith("available == 'false'")
    assert retained["with"]["name"] == "codeql-capability"
    assert retained["with"]["path"] == "${{ runner.temp }}/codeql-capability/*.json"
    assert retained["with"]["if-no-files-found"] == "error"
    assert retained["with"]["retention-days"] == 7


@pytest.mark.parametrize(
    ("availability", "analyze_result", "expected"),
    [
        ("true", "success", "analysis completed successfully"),
        ("false", "skipped", "analysis was not performed"),
    ],
)
def test_codeql_aggregate_accepts_only_coherent_outcomes(
    availability: str,
    analyze_result: str,
    expected: str,
) -> None:
    completed = _run_codeql_result("success", availability, analyze_result)
    assert completed.returncode == 0, completed.stderr
    assert expected in completed.stdout
    if availability == "false":
        assert "analysis completed" not in completed.stdout.casefold()


@pytest.mark.parametrize(
    ("capability_result", "availability", "analyze_result"),
    [
        ("failure", "false", "skipped"),
        ("cancelled", "false", "skipped"),
        ("skipped", "false", "skipped"),
        ("", "false", "skipped"),
        ("success", "", "skipped"),
        ("success", "unknown", "skipped"),
        ("success", "true", "skipped"),
        ("success", "true", "failure"),
        ("success", "true", "cancelled"),
        ("success", "true", ""),
        ("success", "false", "success"),
        ("success", "false", "failure"),
        ("success", "false", "cancelled"),
        ("success", "false", ""),
    ],
)
def test_codeql_aggregate_rejects_missing_failed_or_inconsistent_results(
    capability_result: str,
    availability: str,
    analyze_result: str,
) -> None:
    completed = _run_codeql_result(capability_result, availability, analyze_result)
    assert completed.returncode != 0
    assert "CodeQL" in completed.stderr


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
