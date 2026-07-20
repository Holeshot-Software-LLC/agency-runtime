"""Hostile-boundary coverage for the release Git transport."""

from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import release_git

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")


def _git(
    repository: Path,
    *arguments: str,
    git_dir_only: bool = False,
) -> subprocess.CompletedProcess[str]:
    prefix = (
        ["git", "--git-dir", str(repository / ".git")]
        if git_dir_only
        else ["git", "-C", str(repository)]
    )
    return subprocess.run(
        [*prefix, *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    return repository


def _completed(
    *,
    returncode: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> SimpleNamespace:
    return SimpleNamespace(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
        stdout_truncated=False,
        stderr_truncated=False,
    )


def test_discovery_rejects_core_worktree_redirect(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    attacker = tmp_path / "attacker-worktree"
    attacker.mkdir()
    _git(
        repository,
        "config",
        "core.worktree",
        str(attacker),
        git_dir_only=True,
    )

    with pytest.raises(release_git.ReleaseGitError, match="exact Git worktree top-level"):
        release_git.ReleaseGit.discover(repository)


@pytest.mark.parametrize(
    "name",
    (
        "filter.hostile.process",
        "merge.hostile.driver",
        "diff.hostile.textconv",
        "diff.external",
    ),
)
def test_discovery_rejects_worktree_scoped_executable_config(
    tmp_path: Path,
    name: str,
) -> None:
    repository = _repository(tmp_path)
    _git(repository, "config", "extensions.worktreeConfig", "true")
    _git(repository, "config", "--worktree", name, "hostile-command")

    with pytest.raises(release_git.ReleaseGitError, match=r"executable .* configuration"):
        release_git.ReleaseGit.discover(repository)


def test_bound_calls_use_git_directory_cwd_exact_environment_and_root_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    for name in (
        "DYLD_INSERT_LIBRARIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
        "HOME",
        "HTTP_PROXY",
        "LD_PRELOAD",
        "PYTHONPATH",
    ):
        monkeypatch.setenv(name, "attacker")
    session = release_git.ReleaseGit.discover(repository)
    captured: list[dict[str, object]] = []

    def run(argv, **kwargs):
        captured.append({"argv": argv, **kwargs})
        return _completed(stdout=b"clean")

    monkeypatch.setattr(release_git, "run_bounded_binary_process", run)

    assert (
        session.run_bytes(
            ["status", "--porcelain=v1"],
            max_stdout_bytes=123,
            max_stderr_bytes=45,
        )
        == b"clean"
    )

    invocation = captured[-1]
    argv = invocation["argv"]
    environment = invocation["env"]
    assert invocation["cwd"] == str(session.process_cwd)
    assert session.process_cwd == Path(session.launcher[0]).parent.resolve(strict=True)
    assert session.process_cwd != repository
    assert argv.executable_identities == session.launcher.executable_identities
    assert argv.frozen_launcher == session.launcher.frozen_launcher
    assert argv[:5] == [
        session.launcher[0],
        "--no-pager",
        "--no-replace-objects",
        "-C",
        str(repository.resolve()),
    ]
    assert f"core.worktree={repository.resolve()}" in argv
    assert "core.bare=false" in argv
    assert environment["PATH"] == str(session.process_cwd)
    assert environment["GIT_DIR"] == str(session.git_dir)
    assert environment["GIT_COMMON_DIR"] == str(session.common_dir)
    assert environment["GIT_WORK_TREE"] == str(session.root)
    expected_names = {
        "GIT_ASKPASS",
        "GIT_ATTR_NOSYSTEM",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_DIR",
        "GIT_EDITOR",
        "GIT_MERGE_AUTOEDIT",
        "GIT_NO_LAZY_FETCH",
        "GIT_NO_REPLACE_OBJECTS",
        "GIT_OPTIONAL_LOCKS",
        "GIT_PAGER",
        "GIT_SEQUENCE_EDITOR",
        "GIT_TERMINAL_PROMPT",
        "GIT_WORK_TREE",
        "LANG",
        "LC_ALL",
        "PATH",
    }
    assert set(environment) == expected_names
    assert invocation["max_stdout_bytes"] == 123
    assert invocation["max_stderr_bytes"] == 45


def test_linked_worktree_keeps_distinct_git_and_common_directories(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    _git(
        repository,
        "-c",
        "user.name=Release Test",
        "-c",
        "user.email=release@example.invalid",
        "commit",
        "--allow-empty",
        "--quiet",
        "-m",
        "base",
    )
    linked = tmp_path / "linked-worktree"
    _git(repository, "worktree", "add", "--quiet", "--detach", str(linked), "HEAD")

    session = release_git.ReleaseGit.discover(linked)

    assert session.root == linked.resolve()
    assert session.git_dir != session.common_dir
    assert session.run_bytes(["rev-parse", "--verify", "HEAD"]).strip()


def test_repository_metadata_identity_drift_fails_before_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)
    original = session.git_dir
    displaced = original.with_name(f"{original.name}-displaced")
    original.rename(displaced)
    original.mkdir()
    launched = False

    def run(*_args, **_kwargs):
        nonlocal launched
        launched = True
        return _completed()

    monkeypatch.setattr(release_git, "run_bounded_binary_process", run)

    with pytest.raises(release_git.ReleaseGitError, match="changed identity"):
        session.run_bytes(["status", "--porcelain=v1"])
    assert launched is False


def test_identity_drift_during_process_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)
    checks = 0
    original = release_git._require_identities

    def require(identities):
        nonlocal checks
        checks += 1
        if checks == 2:
            raise release_git.ReleaseGitError("release Git directory changed identity")
        original(identities)

    monkeypatch.setattr(release_git, "_require_identities", require)
    monkeypatch.setattr(
        release_git,
        "run_bounded_binary_process",
        lambda *_args, **_kwargs: _completed(),
    )

    with pytest.raises(release_git.ReleaseGitError, match="changed identity"):
        session.run_bytes(["status", "--porcelain=v1"])
    assert checks == 2


def test_config_scope_parser_rejects_non_neutralized_scope() -> None:
    payload = b"global\x00file:/tmp/config\x00filter.hostile.process\x00"

    with pytest.raises(release_git.ReleaseGitError, match="unexpected effective"):
        release_git._config_names(payload)


def test_command_validation_rejects_alias_execution_and_malformed_arguments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    _git(repository, "config", "alias.hostile", "!echo should-not-run")
    session = release_git.ReleaseGit.discover(repository)
    launched = False

    def run(*_args, **_kwargs):
        nonlocal launched
        launched = True
        return _completed()

    monkeypatch.setattr(release_git, "run_bounded_binary_process", run)

    with pytest.raises(ValueError, match="not allowed"):
        session.run_bytes(["hostile"])
    assert launched is False
    with pytest.raises(TypeError, match="non-empty"):
        release_git._validate_arguments([])
    with pytest.raises(TypeError, match="non-empty"):
        release_git._validate_arguments("status")
    with pytest.raises(ValueError, match="invalid item"):
        release_git._validate_arguments(["status", "bad\nargument"])
    with pytest.raises(ValueError, match="explicit non-option"):
        release_git._validate_arguments(["--version"])


@pytest.mark.parametrize(
    "arguments",
    (
        ["config", "--local", "filter.hostile.process", "attacker"],
        ["diff", "--ext-diff"],
        ["show", "--textconv", "HEAD"],
        ["status", "--porcelain=v2"],
        ["cat-file", "--batch-check"],
        ["check-ignore", "-q", "--no-index", "--", "../outside"],
        ["check-ignore", "-q", "--no-index", "--", ":(top)dist/release"],
        ["check-ignore", "-q", "--no-index", "--", "dist/:magic/release"],
        ["ls-tree", "-r", "-l", "-z", "HEAD", "--", "agency_runtime"],
    ),
)
def test_public_session_rejects_mutating_or_noncanonical_git_grammar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    arguments: list[str],
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)
    monkeypatch.setattr(
        release_git,
        "run_bounded_binary_process",
        lambda *_args, **_kwargs: pytest.fail("unapproved Git grammar reached the process runner"),
    )

    with pytest.raises(ValueError, match="not allowed"):
        session.run_bytes(arguments)


def test_config_inspection_grammar_is_private_and_exact() -> None:
    arguments = release_git._CONFIG_INSPECTION_ARGUMENTS

    assert release_git._safe_repository_path("agency_runtime/core.py") is True
    assert release_git._safe_repository_path(r"agency_runtime\core.py") is False
    assert release_git._safe_repository_path(":(top)dist/release") is False
    assert release_git._safe_repository_path("dist/:magic/release") is False
    with pytest.raises(ValueError, match="not allowed"):
        release_git._validate_arguments(arguments)
    assert (
        release_git._validate_arguments(
            arguments,
            allow_config_inspection=True,
        )
        == arguments
    )
    with pytest.raises(ValueError, match="not allowed"):
        release_git._validate_arguments(
            (*arguments[:-1], "--get-regexp"),
            allow_config_inspection=True,
        )
    object_id = "a" * 40
    assert release_git._validate_arguments(
        ("ls-tree", "-r", "-l", "-z", object_id, "--", "agency_runtime")
    ) == ("ls-tree", "-r", "-l", "-z", object_id, "--", "agency_runtime")
    assert release_git._validate_arguments(
        (
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            object_id,
            "--",
            "agency_runtime",
        )
    ) == (
        "ls-tree",
        "-r",
        "-l",
        "-z",
        "--full-tree",
        object_id,
        "--",
        "agency_runtime",
    )
    with pytest.raises(ValueError, match="not allowed"):
        release_git._validate_arguments(
            ("ls-tree", "--name-only", object_id, "--", "agency_runtime")
        )
    with pytest.raises(ValueError, match="not allowed"):
        release_git._validate_arguments(("ls-tree", "-r", "-l", "-z", object_id, "--"))


@pytest.mark.parametrize(
    "arguments",
    (
        ("config", "--get-all", "core.autocrlf"),
        ("rev-parse", "--verify", "HEAD^{commit}"),
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        ),
        (
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            "a" * 40,
            "--",
            release_git.AUTOCRLF_PROOF_PATH,
        ),
        (
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            "b" * 64,
            "--",
            release_git.AUTOCRLF_PROOF_PATH,
        ),
        ("cat-file", "blob", "a" * 40),
        ("cat-file", "blob", "b" * 64),
        ("add", "--", release_git.AUTOCRLF_PROOF_PATH),
    ),
)
def test_autocrlf_proof_grammar_accepts_only_its_fixed_commands(
    arguments: tuple[str, ...],
) -> None:
    assert release_git._validate_autocrlf_proof_arguments(arguments) == arguments


@pytest.mark.parametrize(
    "arguments",
    (
        ("config", "--get-all", "core.eol"),
        ("rev-parse", "--verify", "HEAD"),
        ("status", "--porcelain=v1", "-z", "--untracked-files=all"),
        (
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            "a" * 39,
            "--",
            release_git.AUTOCRLF_PROOF_PATH,
        ),
        (
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            "a" * 40,
            "--",
            "README.md",
        ),
        ("cat-file", "commit", "a" * 40),
        ("cat-file", "blob", "a" * 39),
        ("add", "--", "README.md"),
        ("reset", "--hard"),
    ),
)
def test_autocrlf_proof_grammar_rejects_every_near_miss(
    arguments: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match=r"autocrlf proof .* arguments are not allowed"):
        release_git._validate_autocrlf_proof_arguments(arguments)


@pytest.mark.parametrize(
    "arguments",
    (
        ("config", "--get-all", "core.autocrlf"),
        ("add", "--", release_git.AUTOCRLF_PROOF_PATH),
        ("-c", "core.autocrlf=true", "status", "--porcelain=v1"),
    ),
)
def test_standard_session_does_not_inherit_the_autocrlf_proof_surface(
    arguments: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match=r"not allowed|explicit non-option"):
        release_git._validate_arguments(arguments)


def test_autocrlf_public_api_injects_one_exact_command_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)
    captured: list[tuple[object, dict[str, object]]] = []

    def run(argv, **kwargs):
        captured.append((argv, kwargs))
        return _completed(stdout=b"true\n")

    monkeypatch.setattr(release_git, "run_bounded_binary_process", run)

    assert (
        session.run_autocrlf_proof_bytes(
            ("config", "--get-all", "core.autocrlf"),
            max_stdout_bytes=123,
            max_stderr_bytes=45,
            timeout=6,
        )
        == b"true\n"
    )

    argv, invocation = captured[-1]
    rendered = tuple(argv)
    assert rendered.count("-c") == len(release_git._SAFE_GIT_CONFIG) + 3
    assert rendered.count("core.autocrlf=true") == 1
    config_index = rendered.index("config")
    assert rendered[config_index - 2 : config_index] == ("-c", "core.autocrlf=true")
    assert invocation["cwd"] == str(session.process_cwd)
    assert invocation["env"] == dict(session.environment)
    assert invocation["input_bytes"] is None
    assert invocation["max_stdout_bytes"] == 123
    assert invocation["max_stderr_bytes"] == 45
    assert invocation["timeout"] == 6


def test_ignore_probe_rejects_git_pathspec_magic_before_launch(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)

    with pytest.raises(ValueError, match="not allowed"):
        session.is_ignored(":(top)unignored-release")


def test_ignore_probe_accepts_both_git_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)
    results = iter((_completed(returncode=0), _completed(returncode=1)))
    monkeypatch.setattr(
        release_git.ReleaseGit,
        "_run_result",
        lambda *_args, **_kwargs: next(results),
    )

    assert session.is_ignored("dist/release") is True
    assert session.is_ignored("dist/release") is False


def test_path_and_directory_identity_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(release_git.ReleaseGitError, match="control character"):
        release_git._path_text(Path("bad\npath"), label="test")
    with pytest.raises(release_git.ReleaseGitError, match="unavailable"):
        release_git._directory_identity(tmp_path / "missing", label="test")

    regular = tmp_path / "regular"
    regular.write_text("not a directory", encoding="utf-8")
    with pytest.raises(release_git.ReleaseGitError, match="real directory"):
        release_git._directory_identity(regular, label="test")

    monkeypatch.setattr(
        release_git.os,
        "lstat",
        lambda _path: SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o700,
            st_file_attributes=0,
            st_ino=0,
            st_dev=1,
        ),
    )
    with pytest.raises(release_git.ReleaseGitError, match="stable filesystem identity"):
        release_git._directory_identity(tmp_path, label="test")


def test_environment_requires_a_complete_repository_binding(tmp_path: Path) -> None:
    with pytest.raises(release_git.ReleaseGitError, match="binding is incomplete"):
        release_git._git_environment(tmp_path, repository=tmp_path)


@pytest.mark.parametrize(
    ("result", "message"),
    (
        (
            SimpleNamespace(
                timed_out=True,
                stdout_truncated=False,
                stderr_truncated=False,
                returncode=0,
                stdout=b"",
                stderr=b"",
            ),
            "time limit",
        ),
        (
            SimpleNamespace(
                timed_out=False,
                stdout_truncated=False,
                stderr_truncated=True,
                returncode=0,
                stdout=b"",
                stderr=b"",
            ),
            "output limit",
        ),
        (
            SimpleNamespace(
                timed_out=False,
                stdout_truncated=False,
                stderr_truncated=False,
                returncode=2,
                stdout=b"",
                stderr=b"hostile failure\n",
            ),
            "hostile failure",
        ),
        (
            SimpleNamespace(
                timed_out=False,
                stdout_truncated=False,
                stderr_truncated=False,
                returncode=2,
                stdout=b"",
                stderr=b"",
            ),
            "failed with exit code 2",
        ),
        (
            SimpleNamespace(
                timed_out=False,
                stdout_truncated=False,
                stderr_truncated=False,
                returncode=-9,
                stdout=b"",
                stderr=b"",
            ),
            "terminated by signal 9",
        ),
    ),
)
def test_checked_output_rejects_incomplete_or_failed_processes(result, message: str) -> None:
    with pytest.raises(release_git.ReleaseGitError, match=message):
        release_git._checked_output(result, accepted=frozenset({0}))


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        (b"one\ntwo\nthree", "malformed"),
        (b"one\ntwo\n", "incomplete"),
        (b"\xff\none\ntwo\n", "not UTF-8"),
        (b"bad\x7fpath\none\ntwo\n", "unsupported character"),
        (b"missing-one\nmissing-two\nmissing-three\n", "unavailable"),
    ),
)
def test_repository_identity_parser_rejects_untrusted_output(
    tmp_path: Path,
    payload: bytes,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(release_git.ReleaseGitError, match=message):
        release_git._decode_identity_paths(payload)


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        (b"local\x00origin\x00name", "malformed"),
        (b"local\x00origin\x00\xff\x00", "metadata is invalid"),
    ),
)
def test_config_parser_rejects_malformed_or_non_utf8_metadata(
    payload: bytes,
    message: str,
) -> None:
    with pytest.raises(release_git.ReleaseGitError, match=message):
        release_git._config_names(payload)


def test_config_parser_ignores_command_scope_and_returns_repository_scopes() -> None:
    payload = b"command\x00command line:\x00core.bare\x00local\x00file:.git/config\x00user.name\x00"

    assert release_git._config_names(payload) == ("user.name",)


def test_discovery_rejects_missing_repository_and_non_native_launcher(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(release_git.ReleaseGitError, match="repository is unavailable"):
        release_git.ReleaseGit.discover(tmp_path / "missing")

    repository = _repository(tmp_path)
    monkeypatch.setattr(
        release_git,
        "freeze_process_argv",
        lambda *_args, **_kwargs: SimpleNamespace(argument_offset=0, artifact_paths=()),
    )
    with pytest.raises(release_git.ReleaseGitError, match="one native executable"):
        release_git.ReleaseGit.discover(repository)


def test_session_rejects_repository_binding_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)
    monkeypatch.setattr(
        release_git,
        "_probe_repository_identity",
        lambda *_args, **_kwargs: (repository.resolve(), tmp_path, session.common_dir),
    )

    with pytest.raises(release_git.ReleaseGitError, match="binding changed identity"):
        session._require_repository_binding()


@pytest.mark.parametrize("accepted", ((), (True,), ("0",)))
def test_session_rejects_invalid_accepted_exit_codes(
    tmp_path: Path,
    accepted,
) -> None:
    repository = _repository(tmp_path)
    session = release_git.ReleaseGit.discover(repository)

    with pytest.raises(ValueError, match="non-empty integers"):
        session.run_bytes(["status", "--porcelain=v1"], accepted=accepted)
