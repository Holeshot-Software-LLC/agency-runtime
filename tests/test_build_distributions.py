"""Canonical builds use authenticated Git bytes and fail closed on unsafe state."""

from __future__ import annotations

import errno
import hashlib
import os
import runpy
import shutil
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest

from scripts import build_distributions as subject
from scripts import canonicalize_distributions as canonicalizer
from scripts import release_git


@pytest.fixture(autouse=True)
def _stub_distribution_canonicalizer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "canonicalize_distributions", lambda *_args, **_kwargs: None)


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_bytes,
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    return completed.stdout


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.name", "Release Test")
    _git(repo, "config", "user.email", "release@example.invalid")
    _git(repo, "config", "core.autocrlf", "true")
    (repo / ".gitattributes").write_bytes(b"*.py text eol=crlf\n")
    (repo / ".gitignore").write_bytes(b"dist/\n.agency-release-*/\n*.egg-info/\nbuild/\n")
    (repo / "agency_runtime").mkdir()
    (repo / "agency_runtime" / "__init__.py").write_bytes(b'__version__ = "0.1.0"\n')
    (repo / "LICENSE").write_bytes(b"license\n")
    (repo / "pyproject.toml").write_bytes(b"[build-system]\nrequires=[]\nbuild-backend='example'\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    return repo, commit


def _fake_materializer(
    _root: Path,
    source: Path,
    _commit: str,
    *,
    git,
):
    assert git is not None
    source.mkdir()
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    return []


def _fake_successful_build(
    _root: Path,
    _source: Path,
    output: Path,
    _scratch: Path,
    *,
    timestamp: int,
) -> None:
    assert timestamp >= 0
    (output / "agency_runtime-0.1.0-py3-none-any.whl").write_bytes(b"wheel")
    (output / "agency_runtime-0.1.0.tar.gz").write_bytes(b"sdist")


def _blob_id(payload: bytes, algorithm: str = "sha1") -> str:
    digest = hashlib.new(algorithm)
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _entry(payload: bytes, algorithm: str = "sha1") -> subject.ReleaseEntry:
    return subject.ReleaseEntry(PurePosixPath("x.py"), _blob_id(payload, algorithm), len(payload))


def _batch(entry: subject.ReleaseEntry, payload: bytes) -> bytes:
    return f"{entry.object_id} blob {entry.size}\n".encode("ascii") + payload + b"\n"


def test_materialization_reads_authenticated_canonical_blobs_from_autocrlf_checkout(
    tmp_path: Path,
) -> None:
    repo, commit = _repository(tmp_path)
    worktree = repo / "agency_runtime" / "__init__.py"
    worktree.write_bytes(b'__version__ = "0.1.0"\r\n')
    _git(repo, "add", "agency_runtime/__init__.py")
    (repo / "agency_runtime.egg-info").mkdir()
    (repo / "agency_runtime.egg-info" / "poison.py").write_text("raise SystemExit\n")

    assert _git(repo, "status", "--porcelain=v1") == b""
    assert _git(repo, "hash-object", "--no-filters", "agency_runtime/__init__.py").strip() != (
        _git(repo, "rev-parse", "HEAD:agency_runtime/__init__.py").strip()
    )

    destination = tmp_path / "canonical"
    entries = subject.materialize_reviewed_sources(repo, destination, commit)

    assert destination.joinpath("agency_runtime", "__init__.py").read_bytes() == (
        b'__version__ = "0.1.0"\n'
    )
    assert not (destination / "agency_runtime.egg-info").exists()
    assert {entry.path.as_posix() for entry in entries} == {
        ".gitattributes",
        "LICENSE",
        "agency_runtime/__init__.py",
        "pyproject.toml",
    }


def test_release_tree_rejects_executable_and_linked_inputs_before_build(tmp_path: Path) -> None:
    repo, _commit = _repository(tmp_path)
    script = repo / "agency_runtime" / "tool.py"
    script.write_bytes(b"print('ok')\n")
    if os.name != "nt":
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
    _git(repo, "add", "agency_runtime/tool.py")
    _git(repo, "update-index", "--chmod=+x", "agency_runtime/tool.py")
    _git(repo, "commit", "-m", "executable")
    executable_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    with pytest.raises(RuntimeError, match="non-executable regular Git blob"):
        subject.materialize_reviewed_sources(repo, tmp_path / "executable", executable_commit)

    _git(repo, "rm", "agency_runtime/tool.py")
    object_id = _git(repo, "hash-object", "-w", "--stdin", input_bytes=b"target").decode().strip()
    _git(
        repo,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{object_id},agency_runtime/link",
    )
    _git(repo, "commit", "-m", "link")
    link_commit = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    with pytest.raises(RuntimeError, match="non-executable regular Git blob"):
        subject.materialize_reviewed_sources(repo, tmp_path / "linked", link_commit)


def test_portable_tree_rejects_case_component_and_prefix_aliases() -> None:
    def entry(name: str) -> subject.ReleaseEntry:
        return subject.ReleaseEntry(PurePosixPath(name), "a" * 40, 1)

    with pytest.raises(RuntimeError, match="case-aliasing paths"):
        subject._portable_component_aliases([entry("A.py"), entry("a.py")])
    with pytest.raises(RuntimeError, match="components"):
        subject._portable_component_aliases([entry("A/x.py"), entry("a/y.py")])
    with pytest.raises(RuntimeError, match="prefix collision"):
        subject._portable_component_aliases([entry("agency_runtime"), entry("agency_runtime/x.py")])


@pytest.mark.parametrize("algorithm", ["sha1", "sha256"])
def test_blob_batch_recomputes_object_identity_before_materialization(algorithm: str) -> None:
    payload = b"abc\x00\xff"
    entry = _entry(payload, algorithm)
    parsed = subject._parse_blob_batch([entry], _batch(entry, payload), algorithm=algorithm)
    assert bytes(parsed[0]) == payload

    tampered = bytearray(payload)
    tampered[-1] ^= 1
    with pytest.raises(RuntimeError, match="failed object verification"):
        subject._parse_blob_batch(
            [entry],
            _batch(entry, bytes(tampered)),
            algorithm=algorithm,
        )


@pytest.mark.parametrize(
    ("output", "message"),
    [
        (b"not-a-header\nabc\n", "header is malformed"),
        (f"{'a' * 40} blob +3\nabc\n".encode(), "header is malformed"),
        (f"{'a' * 40} blob 03\nabc\n".encode(), "header is malformed"),
        (b"\xff blob 3\nabc\n", "header is malformed"),
        (f"{'a' * 40} blob 3\nabc".encode(), "payload is truncated"),
    ],
)
def test_blob_batch_rejects_noncanonical_headers_and_truncation(
    output: bytes,
    message: str,
) -> None:
    entry = subject.ReleaseEntry(PurePosixPath("x.py"), "a" * 40, 3)
    with pytest.raises(RuntimeError, match=message):
        subject._parse_blob_batch([entry], output, algorithm="sha1")


def test_blob_batch_rejects_identity_and_trailing_content() -> None:
    payload = b"abc"
    entry = _entry(payload)
    wrong = f"{'b' * 40} blob 3\nabc\n".encode()
    with pytest.raises(RuntimeError, match="identity mismatch"):
        subject._parse_blob_batch([entry], wrong, algorithm="sha1")
    with pytest.raises(RuntimeError, match="trailing"):
        subject._parse_blob_batch([entry], _batch(entry, payload) + b"extra", algorithm="sha1")


def test_absent_ignored_in_repo_destination_is_accepted(tmp_path: Path) -> None:
    repo, _commit = _repository(tmp_path)
    git = release_git.ReleaseGit.discover(repo)

    assert subject._checked_destination(repo, repo / "dist", git) == repo / "dist"
    with pytest.raises(ValueError, match="must be Git-ignored"):
        subject._checked_destination(repo, repo / "release-output", git)


def test_destination_trust_is_bound_to_the_prospective_child(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _commit = _repository(tmp_path)
    destination = tmp_path / "published"
    observed: dict[str, object] = {}

    def trusted(boundary, intended_parent, *, is_windows):
        observed.update(
            boundary=boundary,
            intended_parent=intended_parent,
            is_windows=is_windows,
        )
        return True

    monkeypatch.setattr(subject, "storage_creation_boundary_is_trusted", trusted)

    assert (
        subject._checked_destination(
            repo,
            destination,
            release_git.ReleaseGit.discover(repo),
        )
        == destination
    )
    assert observed == {
        "boundary": tmp_path.resolve(),
        "intended_parent": destination,
        "is_windows": os.name == "nt",
    }


def test_builder_publishes_exact_pair_and_preserves_stage_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    destination = tmp_path / "published"
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)
    monkeypatch.setattr(subject, "_invoke_build", _fake_successful_build)

    wheel, sdist = subject.build_distributions(repo, destination, expected_commit=commit)

    assert wheel.parent == sdist.parent == destination
    assert sorted(path.name for path in destination.iterdir()) == sorted((wheel.name, sdist.name))


def test_builder_rehashes_materialized_sources_before_backend_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    destination = tmp_path / "published"
    events: list[str] = []
    entry = subject.ReleaseEntry(PurePosixPath("pyproject.toml"), "a" * 40, 0)

    def materialize(_root, source, _commit, *, git):
        assert git is not None
        source.mkdir()
        (source / "pyproject.toml").write_bytes(b"")
        events.append("materialize")
        return [entry]

    def verify(source, entries):
        assert source.joinpath("pyproject.toml").is_file()
        assert entries == [entry]
        events.append("verify")

    def build(root, source, output, scratch, *, timestamp):
        assert events == ["materialize", "verify"]
        events.append("build")
        _fake_successful_build(root, source, output, scratch, timestamp=timestamp)

    monkeypatch.setattr(subject, "materialize_reviewed_sources", materialize)
    monkeypatch.setattr(subject, "_verify_materialized_sources", verify)
    monkeypatch.setattr(subject, "_invoke_build", build)

    subject.build_distributions(repo, destination, expected_commit=commit)

    assert events == ["materialize", "verify", "build"]


def test_builder_failure_or_stage_replacement_never_publishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)

    def fail(_root, _source, output, _scratch, *, timestamp):
        (output / "partial.whl").write_bytes(str(timestamp).encode())
        raise RuntimeError("backend failed")

    monkeypatch.setattr(subject, "_invoke_build", fail)
    destination = tmp_path / "failed"
    with pytest.raises(RuntimeError, match="backend failed"):
        subject.build_distributions(repo, destination, expected_commit=commit)
    assert not destination.exists()

    def replace_stage(root, source, output, scratch, *, timestamp):
        displaced = scratch / "displaced"
        output.rename(displaced)
        output.mkdir()
        _fake_successful_build(root, source, output, scratch, timestamp=timestamp)

    monkeypatch.setattr(subject, "_invoke_build", replace_stage)
    destination = tmp_path / "replaced"
    with pytest.raises(RuntimeError, match="changed identity"):
        subject.build_distributions(repo, destination, expected_commit=commit)
    assert not destination.exists()


def test_second_canonical_artifact_replacement_failure_never_publishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    destination = tmp_path / "canonicalizer-failed"
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)
    monkeypatch.setattr(subject, "_invoke_build", _fake_successful_build)
    monkeypatch.setattr(
        canonicalizer,
        "canonicalize_wheel_bytes",
        lambda *_args, **_kwargs: b"canonical-wheel",
    )
    monkeypatch.setattr(
        canonicalizer,
        "canonicalize_sdist_bytes",
        lambda *_args, **_kwargs: b"canonical-sdist",
    )
    monkeypatch.setattr(
        subject, "canonicalize_distributions", canonicalizer.canonicalize_distributions
    )
    real_replace = canonicalizer.os.replace
    replacements = 0

    def fail_second_replace(source: Path, target: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("second canonical replacement failed")
        real_replace(source, target)

    monkeypatch.setattr(canonicalizer.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="second canonical replacement failed"):
        subject.build_distributions(repo, destination, expected_commit=commit)

    assert not destination.exists()
    assert not list(tmp_path.glob(".agency-release-source-*"))
    assert not list(tmp_path.glob(".agency-release-artifacts-*"))


def test_builder_rechecks_reviewed_checkout_after_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    destination = tmp_path / "published"
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)

    def mutate(root, source, output, scratch, *, timestamp):
        _fake_successful_build(root, source, output, scratch, timestamp=timestamp)
        (repo / "LICENSE").write_text("changed\n", encoding="utf-8")

    monkeypatch.setattr(subject, "_invoke_build", mutate)
    with pytest.raises(ValueError, match="clean Git checkout"):
        subject.build_distributions(repo, destination, expected_commit=commit)
    assert not destination.exists()


def test_builder_refuses_existing_and_concurrently_created_destinations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="must not already exist"):
        subject.build_distributions(repo, existing, expected_commit=commit)

    destination = tmp_path / "collision"
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)
    monkeypatch.setattr(subject, "_invoke_build", _fake_successful_build)

    def collide(_source: Path, output: Path, *, platform_name=None) -> None:
        destination.mkdir()
        (destination / "owned-by-other").write_text("keep", encoding="utf-8")
        raise FileExistsError("distribution destination appeared before publication")

    monkeypatch.setattr(subject, "_publish_no_replace", collide)
    with pytest.raises(FileExistsError, match="appeared"):
        subject.build_distributions(repo, destination, expected_commit=commit)
    assert (destination / "owned-by-other").read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("mutation", ["extra", "replace"])
def test_builder_rejects_artifact_changes_after_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    repo, commit = _repository(tmp_path)
    destination = tmp_path / "published"
    staged: dict[str, Path] = {}
    checks = 0
    real_reviewed_checkout = subject.reviewed_checkout
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)

    def build(root, source, output, scratch, *, timestamp):
        staged["path"] = output
        _fake_successful_build(root, source, output, scratch, timestamp=timestamp)

    def review(root, expected_commit, *, git):
        nonlocal checks
        checks += 1
        result = real_reviewed_checkout(root, expected_commit, git=git)
        if checks == 2:
            if mutation == "extra":
                (staged["path"] / "unexpected.txt").write_text("unexpected", encoding="utf-8")
            else:
                wheel = next(staged["path"].glob("*.whl"))
                wheel.write_bytes(b"other")
        return result

    monkeypatch.setattr(subject, "_invoke_build", build)
    monkeypatch.setattr(subject, "reviewed_checkout", review)

    with pytest.raises(RuntimeError, match=r"exactly one wheel|changed identity"):
        subject.build_distributions(repo, destination, expected_commit=commit)
    assert not destination.exists()


@pytest.mark.parametrize(
    "names",
    [
        ("only.whl",),
        ("one.whl", "one.tar.gz", "unexpected.txt"),
        ("one.whl", "two.whl"),
    ],
)
def test_artifact_contract_requires_one_wheel_and_one_sdist(
    tmp_path: Path,
    names: tuple[str, ...],
) -> None:
    identity = subject._directory_identity(tmp_path)
    for name in names:
        (tmp_path / name).write_bytes(b"artifact")
    with pytest.raises(RuntimeError, match="exactly one wheel"):
        subject._artifacts(tmp_path, expected_directory=identity)


def test_artifact_contract_rejects_hardlinks(tmp_path: Path) -> None:
    identity = subject._directory_identity(tmp_path)
    backing = tmp_path.parent / f"{tmp_path.name}-backing"
    backing.write_bytes(b"wheel")
    os.link(backing, tmp_path / "one.whl")
    (tmp_path / "one.tar.gz").write_bytes(b"sdist")
    try:
        with pytest.raises(RuntimeError, match="single-link regular"):
            subject._artifacts(tmp_path, expected_directory=identity)
    finally:
        backing.unlink()


def test_artifact_contract_bounds_individual_and_aggregate_sizes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = subject._directory_identity(tmp_path)
    wheel = tmp_path / "one.whl"
    sdist = tmp_path / "one.tar.gz"
    wheel.write_bytes(b"1234")
    sdist.write_bytes(b"5678")

    monkeypatch.setattr(subject, "MAX_ARTIFACT_FILE_BYTES", 3)
    with pytest.raises(RuntimeError, match="file-size budget"):
        subject._artifacts(tmp_path, expected_directory=identity)

    monkeypatch.setattr(subject, "MAX_ARTIFACT_FILE_BYTES", 8)
    monkeypatch.setattr(subject, "MAX_ARTIFACT_TOTAL_BYTES", 7)
    with pytest.raises(RuntimeError, match="aggregate byte budget"):
        subject._artifacts(tmp_path, expected_directory=identity)


def test_build_invocation_preserves_launcher_and_sanitizes_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def run(argv, **kwargs):
        captured.update(argv=list(argv), **kwargs)
        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
            timed_out=False,
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.setattr(subject, "run_bounded_process", run)
    frozen: dict[str, object] = {}

    def freeze(argv, **kwargs):
        frozen.update(kwargs)
        return argv

    monkeypatch.setattr(subject, "freeze_process_argv", freeze)
    monkeypatch.setattr(subject, "freeze_persistent_process_argv", freeze)
    for name in (
        "AWS_SECRET_ACCESS_KEY",
        "AZURE_CLIENT_SECRET",
        "CI_JOB_TOKEN",
        "CLOUDSDK_AUTH_ACCESS_TOKEN",
        "DYLD_INSERT_LIBRARIES",
        "GIT_ASKPASS",
        "GITHUB_TOKEN",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "NO_PROXY",
        "PYTHONHOME",
        "PYTHONPATH",
        "PIP_INDEX_URL",
        "SSH_AUTH_SOCK",
        "TWINE_PASSWORD",
    ):
        monkeypatch.setenv(name, "unsafe-secret")
    root = tmp_path / "root"
    source = tmp_path / "source"
    output = tmp_path / "output"
    scratch = tmp_path / "scratch"
    for directory in (root, source, output, scratch):
        directory.mkdir()

    subject._invoke_build(root, source, output, scratch, timestamp=123)

    argv = captured["argv"]
    assert argv[0] == subject.absolute_executable_path(sys.executable)
    assert argv[1:4] == ["-I", "-m", "build"]
    assert argv[-2:] == [str(output), str(source)]
    assert captured["cwd"] == str(source)
    environment = captured["env"]
    assert environment["SOURCE_DATE_EPOCH"] == "123"
    assert environment["PIP_CONFIG_FILE"] == os.devnull
    expected_names = {
        "HOME",
        "PATH",
        "PIP_CONFIG_FILE",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "PIP_NO_INPUT",
        "PYTHONIOENCODING",
        "PYTHONNOUSERSITE",
        "PYTHONUTF8",
        "SOURCE_DATE_EPOCH",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
    }
    if os.name == "nt":
        expected_names.update(
            name for name in ("SYSTEMROOT", "WINDIR", "PATHEXT") if os.environ.get(name)
        )
    assert set(environment) == expected_names
    for name in (
        "AWS_SECRET_ACCESS_KEY",
        "AZURE_CLIENT_SECRET",
        "CI_JOB_TOKEN",
        "CLOUDSDK_AUTH_ACCESS_TOKEN",
        "DYLD_INSERT_LIBRARIES",
        "GIT_ASKPASS",
        "GITHUB_TOKEN",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "LD_LIBRARY_PATH",
        "LD_PRELOAD",
        "NO_PROXY",
        "PYTHONHOME",
        "PYTHONPATH",
        "PIP_INDEX_URL",
        "SSH_AUTH_SOCK",
        "TWINE_PASSWORD",
    ):
        assert name not in environment
    assert frozen["forbidden_roots"] == (root, source)


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (
            SimpleNamespace(
                returncode=124,
                stdout="",
                stderr="",
                timed_out=True,
                stdout_truncated=False,
                stderr_truncated=False,
            ),
            "time limit",
        ),
        (
            SimpleNamespace(
                returncode=0,
                stdout="",
                stderr="",
                timed_out=False,
                stdout_truncated=True,
                stderr_truncated=False,
            ),
            "output limit",
        ),
        (
            SimpleNamespace(
                returncode=2,
                stdout="",
                stderr="failed",
                timed_out=False,
                stdout_truncated=False,
                stderr_truncated=False,
            ),
            "exited 2: failed",
        ),
    ],
)
def test_build_invocation_fails_closed_on_incomplete_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result,
    message: str,
) -> None:
    monkeypatch.setattr(subject, "run_bounded_process", lambda *_args, **_kwargs: result)
    monkeypatch.setattr(subject, "freeze_process_argv", lambda argv, **_kwargs: argv)
    monkeypatch.setattr(
        subject,
        "freeze_persistent_process_argv",
        lambda argv, **_kwargs: argv,
    )
    directories = [tmp_path / name for name in ("root", "source", "output", "scratch")]
    for directory in directories:
        directory.mkdir()
    with pytest.raises(RuntimeError, match=message):
        subject._invoke_build(*directories, timestamp=1)


def test_atomic_publish_rejects_unsupported_platform_and_non_siblings(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(RuntimeError, match="sibling"):
        subject._publish_no_replace(source, tmp_path / "other" / "dest")
    with pytest.raises(RuntimeError, match="unsupported"):
        subject._publish_no_replace(source, tmp_path / "dest", platform_name="unsupported")


def test_atomic_publish_never_replaces_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (destination / "keep").write_text("owned", encoding="utf-8")

    with pytest.raises((FileExistsError, RuntimeError)):
        subject._publish_no_replace(source, destination)
    assert source.is_dir()
    assert (destination / "keep").read_text(encoding="utf-8") == "owned"


def test_builder_rejects_noncanonical_commit_dirty_checkout_and_bad_output_parent(
    tmp_path: Path,
) -> None:
    repo, commit = _repository(tmp_path)
    with pytest.raises(ValueError, match="full lowercase commit"):
        subject.build_distributions(repo, tmp_path / "one", expected_commit=commit[:12])

    (repo / "untracked.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ValueError, match="clean Git checkout"):
        subject.build_distributions(repo, tmp_path / "two", expected_commit=commit)

    (repo / "untracked.txt").unlink()
    with pytest.raises((PermissionError, ValueError), match="parent"):
        subject.build_distributions(repo, tmp_path / "missing" / "three", expected_commit=commit)


def test_builder_can_explicitly_prepare_an_external_private_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, commit = _repository(tmp_path)
    destination = tmp_path / "private" / "published"
    observed: list[Path] = []

    def bootstrap(path: Path) -> Path:
        observed.append(path)
        path.mkdir()
        return path

    monkeypatch.setattr(subject, "bootstrap_private_directory", bootstrap)
    monkeypatch.setattr(subject, "materialize_reviewed_sources", _fake_materializer)
    monkeypatch.setattr(subject, "_invoke_build", _fake_successful_build)

    subject.build_distributions(
        repo,
        destination,
        expected_commit=commit,
        create_private_parent=True,
    )

    assert observed == [destination.parent]
    assert destination.is_dir()


def test_release_git_ignores_repository_path_shadowing(tmp_path: Path, monkeypatch) -> None:
    repo, _commit = _repository(tmp_path)
    marker = repo / "shadow-ran"
    if os.name == "nt":
        shadow = repo / "git.exe"
        shadow.write_bytes(b"not an executable")
    else:
        shadow = repo / "git"
        shadow.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
        shadow.chmod(0o755)
    monkeypatch.setenv("PATH", f"{repo}{os.pathsep}{os.environ.get('PATH', '')}")

    session = release_git.ReleaseGit.discover(repo)

    assert Path(session.launcher[0]).resolve() != shadow.resolve()
    assert not marker.exists()


def test_release_git_rejects_executable_local_configuration(tmp_path: Path) -> None:
    repo, _commit = _repository(tmp_path)
    _git(repo, "config", "filter.evil.clean", "attacker")

    with pytest.raises(release_git.ReleaseGitError, match="executable filter"):
        release_git.ReleaseGit.discover(repo)


def test_release_git_strips_ambient_git_state_and_bounds_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _commit = _repository(tmp_path)
    captured: list[dict[str, object]] = []

    def run(argv, **kwargs):
        captured.append({"argv": list(argv), **kwargs})
        output = b""
        if "rev-parse" in argv:
            git_directory = (repo / ".git").resolve()
            output = f"{repo.resolve()}\n{git_directory}\n{git_directory}\n".encode()
        return SimpleNamespace(
            returncode=0,
            stdout=output,
            stderr=b"",
            timed_out=False,
            stdout_truncated=False,
            stderr_truncated=False,
        )

    monkeypatch.setattr(release_git, "run_bounded_binary_process", run)
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", "attacker")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "99")
    session = release_git.ReleaseGit.discover(repo)
    session.run_bytes(["status", "--porcelain=v1"], max_stdout_bytes=123, max_stderr_bytes=45)

    invocation = captured[-1]
    environment = invocation["env"]
    assert "GIT_OBJECT_DIRECTORY" not in environment
    assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert environment["GIT_NO_LAZY_FETCH"] == "1"
    assert invocation["max_stdout_bytes"] == 123
    assert invocation["max_stderr_bytes"] == 45
    assert "--no-replace-objects" in invocation["argv"]
    assert "core.fsmonitor=false" in invocation["argv"]


def test_release_builder_module_help_is_importable() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.build_distributions", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "expected-commit" in completed.stdout
    assert "create-private-parent" in completed.stdout


@pytest.mark.parametrize(
    "module",
    ("scripts.build_distributions", "scripts.release_git"),
)
def test_release_module_import_and_help_do_not_load_delegation_or_yaml(module: str) -> None:
    root = Path(__file__).resolve().parents[1]
    probe = "\n".join(
        (
            "import runpy",
            "import sys",
            f"sys.path.insert(0, {str(root)!r})",
            f"sys.argv = [{module!r}, '--help']",
            "try:",
            f"    runpy.run_module({module!r}, run_name='__main__')",
            "except SystemExit as exc:",
            "    if exc.code != 0:",
            "        raise",
            "for name in sys.modules:",
            "    assert not name.startswith('agency_runtime.core.delegation'), name",
            "    assert name != 'yaml', name",
        )
    )

    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_git_fixture_uses_a_real_git_executable() -> None:
    assert Path(shutil.which("git") or "").is_absolute()


def _tree_item(
    name: bytes,
    *,
    mode: bytes = b"100644",
    object_type: bytes = b"blob",
    object_id: bytes = b"a" * 40,
    size: int = 1,
) -> bytes:
    return (
        mode
        + b" "
        + object_type
        + b" "
        + object_id
        + b" "
        + str(size).encode("ascii")
        + b"\t"
        + name
        + b"\0"
    )


def _required_tree(*, package_object_id: bytes = b"a" * 40) -> bytes:
    return b"".join(
        (
            _tree_item(
                b"agency_runtime/__init__.py",
                object_id=package_object_id,
            ),
            _tree_item(b"pyproject.toml"),
            _tree_item(b"LICENSE"),
        )
    )


def _manifest_git(payload: bytes):
    return SimpleNamespace(run_bytes=lambda *_args, **_kwargs: payload)


def test_directory_and_staging_identity_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="directory is unavailable"):
        subject._directory_identity(tmp_path / "missing")

    regular = tmp_path / "regular"
    regular.write_text("file", encoding="utf-8")
    with pytest.raises(RuntimeError, match="real directory"):
        subject._directory_identity(regular)

    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o700,
            st_file_attributes=0,
            st_ino=0,
            st_dev=1,
        ),
    )
    with pytest.raises(RuntimeError, match="stable identity"):
        subject._directory_identity(tmp_path)


def test_private_staging_directory_must_remain_trusted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "restrict_path_permissions", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(subject, "storage_parent_is_trusted", lambda *_args, **_kwargs: False)

    with pytest.raises(PermissionError, match="not private"):
        subject._secure_private_directory(tmp_path)


@pytest.mark.parametrize(
    "payload",
    (
        b"\xff\n",
        b"-1\n",
        b"01\n",
        b"missing\n",
    ),
)
def test_commit_timestamp_must_be_canonical_ascii(payload: bytes) -> None:
    git = SimpleNamespace(run_bytes=lambda *_args, **_kwargs: payload)

    with pytest.raises(RuntimeError, match="timestamp is invalid"):
        subject._commit_timestamp(git, "a" * 40)


def test_release_manifest_skips_non_release_inputs_and_returns_sorted_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = subject.is_release_source
    monkeypatch.setattr(
        subject,
        "is_release_source",
        lambda name: False if name == "ignored.tmp" else original(name),
    )
    payload = _tree_item(b"ignored.tmp") + _required_tree()

    entries, algorithm = subject._release_entries(_manifest_git(payload), "a" * 40)

    assert [entry.path.as_posix() for entry in entries] == [
        "LICENSE",
        "agency_runtime/__init__.py",
        "pyproject.toml",
    ]
    assert algorithm == "sha1"


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        (b"malformed\tLICENSE\0", "manifest is malformed"),
        (_tree_item(b"\xff"), "manifest is malformed"),
        (_tree_item(b"../outside"), "manifest is malformed"),
        (_tree_item(b"agency_runtime/__init__.py"), "tree is incomplete"),
        (
            _required_tree(package_object_id=b"a" * 64),
            "mixes Git object hash algorithms",
        ),
    ),
)
def test_release_manifest_rejects_malformed_incomplete_and_mixed_inputs(
    payload: bytes,
    message: str,
) -> None:
    with pytest.raises(RuntimeError, match=message):
        subject._release_entries(_manifest_git(payload), "a" * 40)


@pytest.mark.parametrize(
    "name",
    ("com¹", "CoM².txt", "COM³", "lpt¹", "LpT².md", "LPT³"),
)
def test_release_manifest_rejects_superscript_windows_device_names(name: str) -> None:
    payload = _tree_item(f"agency_runtime/{name}".encode()) + _required_tree()

    with pytest.raises(RuntimeError, match="manifest is malformed"):
        subject._release_entries(_manifest_git(payload), "a" * 40)


def test_release_manifest_enforces_file_total_duplicate_and_entry_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _tree_item(b"agency_runtime/__init__.py", size=2)

    monkeypatch.setattr(subject, "MAX_RELEASE_FILE_BYTES", 1)
    with pytest.raises(RuntimeError, match="file-size budget"):
        subject._release_entries(_manifest_git(package), "a" * 40)

    monkeypatch.setattr(subject, "MAX_RELEASE_FILE_BYTES", 16)
    monkeypatch.setattr(subject, "MAX_RELEASE_TOTAL_BYTES", 1)
    with pytest.raises(RuntimeError, match="aggregate byte budget"):
        subject._release_entries(_manifest_git(package), "a" * 40)

    monkeypatch.setattr(subject, "MAX_RELEASE_TOTAL_BYTES", 128)
    duplicate = package + package
    with pytest.raises(RuntimeError, match="duplicates a release source"):
        subject._release_entries(_manifest_git(duplicate), "a" * 40)

    monkeypatch.setattr(subject, "MAX_RELEASE_ENTRIES", 0)
    with pytest.raises(RuntimeError, match="entry budget"):
        subject._release_entries(_manifest_git(package), "a" * 40)


def test_blob_batch_rejects_missing_or_overlong_header() -> None:
    entry = subject.ReleaseEntry(PurePosixPath("x.py"), "a" * 40, 1)

    with pytest.raises(RuntimeError, match="header is missing or overlong"):
        subject._parse_blob_batch(
            [entry],
            b"x" * subject.MAX_GIT_BATCH_OVERHEAD_BYTES,
            algorithm="sha1",
        )


def test_timestamp_rejects_links_and_supports_posix_no_follow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"x")
    real_lstat = subject.os.lstat
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: SimpleNamespace(
            st_mode=stat.S_IFLNK | 0o777,
            st_file_attributes=0,
        ),
    )
    with pytest.raises(RuntimeError, match="link or reparse"):
        subject._set_timestamp(target, 1)

    monkeypatch.setattr(subject.os, "lstat", real_lstat)
    observed: dict[str, object] = {}
    monkeypatch.setattr(subject.os, "name", "posix")
    monkeypatch.setattr(
        subject.os,
        "utime",
        lambda path, times, *, follow_symlinks: observed.update(
            path=path,
            times=times,
            follow_symlinks=follow_symlinks,
        ),
    )
    subject._set_timestamp(target, 7)
    assert observed == {
        "path": target,
        "times": (7, 7),
        "follow_symlinks": False,
    }

    observed.clear()
    monkeypatch.setattr(subject.os, "name", "nt")
    monkeypatch.setattr(
        subject.os,
        "utime",
        lambda path, times: observed.update(path=path, times=times),
    )
    subject._set_timestamp(target, 8)
    assert observed == {
        "path": target,
        "times": (8, 8),
    }


def test_canonical_tree_rejects_file_identity_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "source"
    payload = b"content"
    entry = subject.ReleaseEntry(PurePosixPath("x.py"), _blob_id(payload), len(payload))
    real_lstat = subject.os.lstat
    target_checks = 0

    def lstat(path):
        nonlocal target_checks
        metadata = real_lstat(path)
        if Path(path).name == "x.py":
            target_checks += 1
            if target_checks == 2:
                return SimpleNamespace(
                    st_mode=metadata.st_mode,
                    st_file_attributes=0,
                    st_nlink=2,
                )
        return metadata

    monkeypatch.setattr(subject.os, "lstat", lstat)

    with pytest.raises(RuntimeError, match="single-link regular file"):
        subject._write_canonical_tree(
            destination,
            [entry],
            (memoryview(payload),),
            timestamp=1,
        )


def test_materialized_source_readback_rehashes_exact_git_object(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = b"reviewed\nbytes\x00"
    entry = _entry(payload)
    target = source / entry.path
    target.write_bytes(payload)
    target.chmod(0o644)

    subject._verify_materialized_sources(source, [entry])

    target.write_bytes(payload[:-1] + b"!")
    with pytest.raises(RuntimeError, match="failed object verification"):
        subject._verify_materialized_sources(source, [entry])


def test_materialized_source_readback_rejects_path_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = b"reviewed"
    entry = _entry(payload)
    target = source / entry.path
    target.write_bytes(payload)
    target.chmod(0o644)
    replacement = source / "replacement"
    replacement.write_bytes(b"tampered")
    replacement.chmod(0o644)
    real_open = subject.os.open
    swapped = False

    def swap_then_open(path, flags):
        nonlocal swapped
        if Path(path) == target and not swapped:
            swapped = True
            target.unlink()
            replacement.replace(target)
        return real_open(path, flags)

    monkeypatch.setattr(subject.os, "open", swap_then_open)

    with pytest.raises(RuntimeError, match="changed before hashing"):
        subject._verify_materialized_sources(source, [entry])


def test_materialized_source_readback_rejects_mutation_during_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = b"x" * (subject.COPY_CHUNK_BYTES + 1)
    entry = _entry(payload)
    target = source / entry.path
    target.write_bytes(payload)
    target.chmod(0o644)
    real_fstat = subject.os.fstat
    calls = 0

    def fstat(descriptor):
        nonlocal calls
        calls += 1
        metadata = real_fstat(descriptor)
        if calls == 2:
            return _artifact_metadata(
                metadata,
                st_mtime_ns=metadata.st_mtime_ns + 1,
            )
        return metadata

    monkeypatch.setattr(subject.os, "fstat", fstat)

    with pytest.raises(RuntimeError, match="changed while hashing"):
        subject._verify_materialized_sources(source, [entry])


def test_materialized_entry_contract_rejects_duplicates_and_invalid_budgets() -> None:
    entry = subject.ReleaseEntry(PurePosixPath("x.py"), "a" * 40, 1)
    names = {"x.py"}
    with pytest.raises(RuntimeError, match="invalid or duplicate"):
        subject._validate_materialized_entry_contract(
            entry,
            names=names,
            accumulated_size=0,
        )

    for size in (-1, subject.MAX_RELEASE_FILE_BYTES + 1):
        with pytest.raises(RuntimeError, match="file-size budget"):
            subject._validate_materialized_entry_contract(
                subject.ReleaseEntry(PurePosixPath("x.py"), "a" * 40, size),
                names=set(),
                accumulated_size=0,
            )

    with pytest.raises(RuntimeError, match="aggregate byte budget"):
        subject._validate_materialized_entry_contract(
            entry,
            names=set(),
            accumulated_size=subject.MAX_RELEASE_TOTAL_BYTES,
        )
    with pytest.raises(RuntimeError, match="invalid object ID"):
        subject._validate_materialized_entry_contract(
            subject.ReleaseEntry(PurePosixPath("x.py"), "not-an-object", 1),
            names=set(),
            accumulated_size=0,
        )


def test_materialized_source_readback_rejects_unsafe_file_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = b"x"
    entry = _entry(payload)
    target = source / entry.path

    with pytest.raises(RuntimeError, match="unavailable"):
        subject._verify_materialized_entry(source, entry)

    target.write_bytes(payload)
    target.chmod(0o644)
    metadata = subject.os.lstat(target)
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: _artifact_metadata(metadata, st_nlink=2),
    )
    with pytest.raises(RuntimeError, match="single-link regular"):
        subject._verify_materialized_entry(source, entry)

    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: _artifact_metadata(
            metadata,
            st_mode=(metadata.st_mode & ~0o777) | 0o755,
        ),
    )
    with pytest.raises(RuntimeError, match="noncanonical mode"):
        subject._verify_materialized_entry(source, entry)

    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: _artifact_metadata(metadata, st_ino=0),
    )
    with pytest.raises(RuntimeError, match="no stable identity"):
        subject._verify_materialized_entry(source, entry)

    monkeypatch.setattr(subject.os, "lstat", lambda _path: metadata)
    with pytest.raises(RuntimeError, match="unexpected size"):
        subject._verify_materialized_entry(
            source,
            subject.ReleaseEntry(entry.path, entry.object_id, entry.size + 1),
        )

    monkeypatch.setattr(
        subject.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("refused")),
    )
    with pytest.raises(RuntimeError, match="opened safely"):
        subject._verify_materialized_entry(source, entry)


def test_materialized_source_readback_bounds_growth_and_path_disappearance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    payload = b"x"
    entry = _entry(payload)
    target = source / entry.path
    target.write_bytes(payload)
    target.chmod(0o644)

    monkeypatch.setattr(subject.os, "read", lambda _descriptor, _size: b"xx")
    with pytest.raises(RuntimeError, match="authenticated size"):
        subject._verify_materialized_entry(source, entry)

    monkeypatch.undo()
    target.write_bytes(payload)
    real_lstat = subject.os.lstat
    calls = 0

    def disappearing_lstat(path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FileNotFoundError(path)
        return real_lstat(path)

    monkeypatch.setattr(subject.os, "lstat", disappearing_lstat)
    with pytest.raises(RuntimeError, match="changed while hashing"):
        subject._verify_materialized_entry(source, entry)


def test_materialized_source_readback_rejects_entry_count_over_budget(tmp_path: Path) -> None:
    entry = subject.ReleaseEntry(PurePosixPath("x.py"), "a" * 40, 1)
    with pytest.raises(RuntimeError, match="entry budget"):
        subject._verify_materialized_sources(
            tmp_path,
            [entry] * (subject.MAX_RELEASE_ENTRIES + 1),
        )


def test_materializer_rejects_an_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()

    with pytest.raises(RuntimeError, match="already exists"):
        subject.materialize_reviewed_sources(
            tmp_path,
            destination,
            "a" * 40,
            git=SimpleNamespace(),
        )


def test_destination_rejects_invalid_untrusted_and_raced_namespaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    git = SimpleNamespace(is_ignored=lambda _path: True)
    with pytest.raises(ValueError, match="destination is invalid"):
        subject._checked_destination(tmp_path, Path("bad\nname"), git)

    destination = tmp_path / "untrusted"
    monkeypatch.setattr(
        subject,
        "storage_creation_boundary_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(PermissionError, match="not a trusted namespace"):
        subject._checked_destination(tmp_path, destination, git)

    def race(_parent, intended, **_kwargs):
        intended.mkdir()
        return True

    monkeypatch.setattr(subject, "storage_creation_boundary_is_trusted", race)
    with pytest.raises(ValueError, match="must not already exist"):
        subject._checked_destination(tmp_path, tmp_path / "raced", git)


def test_private_environment_handles_missing_and_invalid_windows_loader_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    source = tmp_path / "source"
    scratch = tmp_path / "scratch"
    source.mkdir()
    scratch.mkdir()
    monkeypatch.setattr(subject, "sanitized_executable_search_path", lambda *_args, **_kwargs: "X")
    ambient = dict(os.environ)
    ambient.pop("SYSTEMROOT", None)
    ambient["WINDIR"] = "bad\x00value"
    ambient["PATHEXT"] = ".EXE"
    os_proxy = SimpleNamespace(name="nt", environ=ambient, devnull=os.devnull)
    monkeypatch.setattr(subject, "os", os_proxy)

    environment = subject._private_build_environment(
        root,
        source,
        scratch,
        timestamp=1,
    )

    assert "SYSTEMROOT" not in environment
    assert "WINDIR" not in environment
    assert environment["PATHEXT"] == ".EXE"

    other_scratch = tmp_path / "other-scratch"
    other_scratch.mkdir()
    os_proxy.name = "posix"
    posix_environment = subject._private_build_environment(
        root,
        source,
        other_scratch,
        timestamp=2,
    )
    assert "PATHEXT" not in posix_environment


def _artifact_metadata(metadata, **changes):
    values = {
        "st_dev": metadata.st_dev,
        "st_ino": metadata.st_ino,
        "st_mode": metadata.st_mode,
        "st_size": metadata.st_size,
        "st_mtime_ns": metadata.st_mtime_ns,
        "st_ctime_ns": getattr(metadata, "st_ctime_ns", 0),
        "st_file_attributes": int(getattr(metadata, "st_file_attributes", 0) or 0),
        "st_nlink": metadata.st_nlink,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_artifact_identity_requires_stable_inode_and_open_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "one.whl"
    artifact.write_bytes(b"abc")
    metadata = subject.os.lstat(artifact)

    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: _artifact_metadata(metadata, st_ino=0),
    )
    with pytest.raises(RuntimeError, match="no stable identity"):
        subject._artifact_identity(artifact)

    monkeypatch.setattr(subject.os, "lstat", lambda _path: metadata)
    real_fstat = subject.os.fstat
    monkeypatch.setattr(
        subject.os,
        "fstat",
        lambda descriptor: _artifact_metadata(real_fstat(descriptor), st_size=4),
    )
    with pytest.raises(RuntimeError, match="changed before hashing"):
        subject._artifact_identity(artifact)


def test_artifact_identity_bounds_reads_and_rechecks_after_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "one.whl"
    artifact.write_bytes(b"abc")
    monkeypatch.setattr(subject, "MAX_ARTIFACT_FILE_BYTES", 3)
    monkeypatch.setattr(subject.os, "read", lambda _descriptor, _size: b"abcd")
    with pytest.raises(RuntimeError, match="file-size budget"):
        subject._artifact_identity(artifact)

    monkeypatch.undo()
    artifact.write_bytes(b"abc")
    real_fstat = subject.os.fstat
    calls = 0

    def fstat(descriptor):
        nonlocal calls
        calls += 1
        metadata = real_fstat(descriptor)
        return (
            _artifact_metadata(metadata, st_mtime_ns=metadata.st_mtime_ns + 1)
            if calls == 2
            else metadata
        )

    monkeypatch.setattr(subject.os, "fstat", fstat)
    with pytest.raises(RuntimeError, match="changed while hashing"):
        subject._artifact_identity(artifact)


def test_artifact_discovery_can_capture_identity_without_prior_directory_snapshot(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "one.whl"
    sdist = tmp_path / "one.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")

    observed_wheel, observed_sdist, identities = subject._artifacts(tmp_path)

    assert (observed_wheel, observed_sdist) == (wheel, sdist)
    assert len(identities) == 2


class _NativeCall:
    def __init__(self, result: int) -> None:
        self.result = result
        self.argtypes = None
        self.restype = None

    def __call__(self, *_args) -> int:
        return self.result


@pytest.mark.parametrize(
    ("result", "native_error", "exception"),
    (
        (0, 0, None),
        (-1, errno.EEXIST, FileExistsError),
        (-1, errno.EINVAL, RuntimeError),
        (-1, errno.EPERM, OSError),
    ),
)
def test_linux_atomic_publication_maps_native_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: int,
    native_error: int,
    exception,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    rename = _NativeCall(result)
    monkeypatch.setattr(
        subject.ctypes,
        "CDLL",
        lambda *_args, **_kwargs: SimpleNamespace(renameat2=rename),
    )
    monkeypatch.setattr(subject.ctypes, "get_errno", lambda: native_error)
    monkeypatch.setattr(subject.os, "open", lambda *_args, **_kwargs: 17)
    closed: list[int] = []
    monkeypatch.setattr(subject.os, "close", closed.append)

    if exception is None:
        subject._linux_rename_no_replace(source, destination)
    else:
        with pytest.raises(exception):
            subject._linux_rename_no_replace(source, destination)
    assert closed == [17]


def test_linux_atomic_publication_requires_renameat2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject.ctypes,
        "CDLL",
        lambda *_args, **_kwargs: SimpleNamespace(renameat2=None),
    )

    with pytest.raises(RuntimeError, match="unsupported on this Linux host"):
        subject._linux_rename_no_replace(tmp_path / "source", tmp_path / "destination")


@pytest.mark.parametrize(
    ("result", "native_error", "exception"),
    (
        (1, 0, None),
        (0, 183, FileExistsError),
        (0, 5, OSError),
    ),
)
def test_windows_atomic_publication_maps_native_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: int,
    native_error: int,
    exception,
) -> None:
    move = _NativeCall(result)
    monkeypatch.setattr(
        subject.ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: SimpleNamespace(MoveFileExW=move),
        raising=False,
    )
    monkeypatch.setattr(
        subject.ctypes,
        "get_last_error",
        lambda: native_error,
        raising=False,
    )

    if exception is None:
        subject._windows_move_no_replace(tmp_path / "source", tmp_path / "destination")
    else:
        with pytest.raises(exception):
            subject._windows_move_no_replace(tmp_path / "source", tmp_path / "destination")


def test_atomic_publication_dispatches_to_supported_native_primitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    calls: list[str] = []
    monkeypatch.setattr(
        subject,
        "_windows_move_no_replace",
        lambda *_args: calls.append("windows"),
    )
    monkeypatch.setattr(
        subject,
        "_linux_rename_no_replace",
        lambda *_args: calls.append("linux"),
    )

    subject._publish_no_replace(source, destination, platform_name="nt")
    monkeypatch.setattr(subject.sys, "platform", "linux")
    subject._publish_no_replace(source, destination, platform_name="posix")
    assert calls == ["windows", "linux"]


def test_cli_main_reports_success_and_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    wheel = tmp_path / "one.whl"
    sdist = tmp_path / "one.tar.gz"
    monkeypatch.setattr(subject, "build_distributions", lambda *_args, **_kwargs: (wheel, sdist))
    assert subject.main(["dist", "--expected-commit", "a" * 40]) == 0
    assert "passed: one.whl, one.tar.gz" in capsys.readouterr().out

    def fail(*_args, **_kwargs):
        raise RuntimeError("controlled failure")

    monkeypatch.setattr(subject, "build_distributions", fail)
    assert subject.main(["dist", "--expected-commit", "a" * 40]) == 1
    assert "controlled failure" in capsys.readouterr().err


def test_direct_script_entrypoint_executes_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", [str(Path(subject.__file__)), "--help"])

    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(Path(subject.__file__)), run_name="__main__")

    assert raised.value.code == 0
