"""Trusted, bounded Git transport for release construction and verification."""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any

from agency_runtime.core.owned_process import run_bounded_binary_process
from agency_runtime.core.process_argv import (
    PreparedProcessArgv,
    freeze_process_argv,
    prepare_process_argv,
    resolve_executable_path,
    sanitized_executable_search_path,
)

DEFAULT_STDOUT_BYTES = 64 * 1024
DEFAULT_STDERR_BYTES = 64 * 1024
GIT_TIMEOUT_SECONDS = 120
AUTOCRLF_PROOF_PATH = "LICENSE"
_MAX_IDENTITY_OUTPUT_BYTES = 96 * 1024
_WINDOWS_REPARSE_POINT = 0x400
_AUTOCRLF_PROOF_CONFIG = "core.autocrlf=true"

_SAFE_GIT_CONFIG = (
    "core.hooksPath=",
    "core.fsmonitor=false",
    "core.longpaths=true",
    "core.attributesFile=",
    "core.pager=",
    "core.alternateRefsCommand=",
    "credential.interactive=never",
    "diff.external=",
    "submodule.recurse=false",
    "protocol.allow=never",
    "gc.auto=0",
)
_SAFE_GIT_ENVIRONMENT = {
    "GIT_ASKPASS": "",
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_EDITOR": "",
    "GIT_MERGE_AUTOEDIT": "no",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_PAGER": "",
    "GIT_SEQUENCE_EDITOR": "",
    "GIT_TERMINAL_PROMPT": "0",
}
_CONFIG_SCOPES = frozenset({"command", "local", "worktree"})
_ALLOWED_COMMANDS = frozenset(
    {
        "cat-file",
        "check-ignore",
        "ls-tree",
        "rev-parse",
        "show",
        "status",
    }
)
_CONFIG_INSPECTION_ARGUMENTS = (
    "config",
    "--includes",
    "--show-origin",
    "--show-scope",
    "--null",
    "--name-only",
    "--list",
)
_FULL_OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SAFE_REVISION = re.compile(
    r"(?:HEAD(?:\^\{commit\})?|(?:[0-9a-f]{40}|[0-9a-f]{64})(?:\^\{commit\})?)\Z"
)


class ReleaseGitError(RuntimeError):
    """One trusted release Git operation failed closed."""


@dataclass(frozen=True, slots=True)
class _DirectoryIdentity:
    """Filesystem identity for one release-session directory boundary."""

    path: Path
    device: int
    inode: int
    mode: int
    file_attributes: int


def _path_text(path: Path, *, label: str) -> str:
    text = str(path)
    if (
        not text
        or "\x00" in text
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        raise ReleaseGitError(f"{label} path contains an unsupported control character")
    return text


def _directory_identity(path: Path, *, label: str) -> _DirectoryIdentity:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise ReleaseGitError(f"{label} directory is unavailable: {path}") from exc
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    if (
        stat.S_ISLNK(metadata.st_mode)
        or attributes & _WINDOWS_REPARSE_POINT
        or not stat.S_ISDIR(metadata.st_mode)
    ):
        raise ReleaseGitError(f"{label} must be a real directory: {path}")
    inode = int(metadata.st_ino)
    if inode <= 0:
        raise ReleaseGitError(f"{label} has no stable filesystem identity: {path}")
    return _DirectoryIdentity(
        path=path,
        device=int(metadata.st_dev),
        inode=inode,
        mode=int(metadata.st_mode),
        file_attributes=attributes,
    )


def _directory_identities(
    entries: Sequence[tuple[Path, str]],
) -> tuple[_DirectoryIdentity, ...]:
    identities: list[_DirectoryIdentity] = []
    seen: set[str] = set()
    for path, label in entries:
        key = os.path.normcase(str(path))
        if key not in seen:
            identities.append(_directory_identity(path, label=label))
            seen.add(key)
    return tuple(identities)


def _require_identities(identities: Sequence[_DirectoryIdentity]) -> None:
    for expected in identities:
        current = _directory_identity(expected.path, label="release session")
        if current != expected:
            raise ReleaseGitError(f"release Git directory changed identity: {expected.path}")


def _git_environment(
    executable_directory: Path,
    *,
    repository: Path | None = None,
    git_dir: Path | None = None,
    common_dir: Path | None = None,
) -> Mapping[str, str]:
    environment = {
        "PATH": _path_text(executable_directory, label="Git executable"),
        **_SAFE_GIT_ENVIRONMENT,
        "LANG": "C",
        "LC_ALL": "C",
    }
    if repository is not None or git_dir is not None or common_dir is not None:
        if repository is None or git_dir is None or common_dir is None:
            raise ReleaseGitError("release Git repository binding is incomplete")
        environment.update(
            {
                "GIT_COMMON_DIR": _path_text(common_dir, label="Git common"),
                "GIT_DIR": _path_text(git_dir, label="Git"),
                "GIT_WORK_TREE": _path_text(repository, label="repository"),
            }
        )
    return MappingProxyType(environment)


def _safe_repository_path(value: str) -> bool:
    if value.startswith(("-", ":")) or "\\" in value:
        return False
    candidate = PurePosixPath(value)
    return bool(
        value
        and not candidate.is_absolute()
        and value == candidate.as_posix()
        and all(
            part not in {"", ".", ".."} and not part.startswith(":") for part in candidate.parts
        )
    )


def _validate_command_grammar(
    arguments: tuple[str, ...],
    *,
    allow_config_inspection: bool,
) -> None:
    command = arguments[0]
    if allow_config_inspection and arguments == _CONFIG_INSPECTION_ARGUMENTS:
        return
    if command not in _ALLOWED_COMMANDS:
        raise ValueError(f"release Git command is not allowed: {command}")

    suffix = arguments[1:]
    valid = False
    if command == "rev-parse":
        valid = suffix in {
            (
                "--path-format=absolute",
                "--show-toplevel",
                "--absolute-git-dir",
                "--git-common-dir",
            ),
            ("--is-inside-work-tree",),
        } or (
            len(suffix) == 2
            and suffix[0] == "--verify"
            and _SAFE_REVISION.fullmatch(suffix[1]) is not None
        )
    elif command == "status":
        valid = suffix in {
            ("--porcelain=v1",),
            (
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignore-submodules=none",
            ),
        }
    elif command == "show":
        valid = (
            len(suffix) == 3
            and suffix[:2] == ("-s", "--format=%ct")
            and _FULL_OBJECT_ID.fullmatch(suffix[2]) is not None
        )
    elif command == "cat-file":
        valid = suffix == ("--batch",) or (
            len(suffix) == 2
            and suffix[0] == "blob"
            and _FULL_OBJECT_ID.fullmatch(suffix[1]) is not None
        )
    elif command == "check-ignore":
        valid = (
            len(suffix) == 4
            and suffix[:3] == ("-q", "--no-index", "--")
            and _safe_repository_path(suffix[3])
        )
    else:
        cursor = 0
        expected_prefix = ("-r", "-l", "-z")
        if suffix[:3] == expected_prefix:
            cursor = 3
            if cursor < len(suffix) and suffix[cursor] == "--full-tree":
                cursor += 1
            valid = bool(
                cursor + 2 < len(suffix)
                and _FULL_OBJECT_ID.fullmatch(suffix[cursor]) is not None
                and suffix[cursor + 1] == "--"
                and all(_safe_repository_path(path) for path in suffix[cursor + 2 :])
            )
    if not valid:
        raise ValueError(f"release Git {command} arguments are not allowed")


def _normalize_arguments(arguments: Sequence[str]) -> tuple[str, ...]:
    if isinstance(arguments, (str, bytes)) or not arguments:
        raise TypeError("release Git arguments must be a non-empty sequence")
    normalized = tuple(arguments)
    if any(
        not isinstance(argument, str)
        or not argument
        or "\x00" in argument
        or any(ord(character) < 32 or ord(character) == 127 for character in argument)
        for argument in normalized
    ):
        raise ValueError("release Git arguments contain an invalid item")
    if normalized[0].startswith("-"):
        raise ValueError("release Git command must be an explicit non-option name")
    return normalized


def _validate_arguments(
    arguments: Sequence[str],
    *,
    allow_config_inspection: bool = False,
) -> tuple[str, ...]:
    normalized = _normalize_arguments(arguments)
    _validate_command_grammar(
        normalized,
        allow_config_inspection=allow_config_inspection,
    )
    return normalized


def _validate_autocrlf_proof_arguments(arguments: Sequence[str]) -> tuple[str, ...]:
    """Validate the fixed command surface used by the autocrlf release proof."""

    normalized = _normalize_arguments(arguments)
    command = normalized[0]
    suffix = normalized[1:]
    valid = False
    if command == "config":
        valid = suffix == ("--get-all", "core.autocrlf")
    elif command == "rev-parse":
        valid = suffix == ("--verify", "HEAD^{commit}")
    elif command == "status":
        valid = suffix == (
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        )
    elif command == "ls-tree":
        valid = bool(
            len(suffix) == 7
            and suffix[:4] == ("-r", "-l", "-z", "--full-tree")
            and _FULL_OBJECT_ID.fullmatch(suffix[4]) is not None
            and suffix[5:] == ("--", AUTOCRLF_PROOF_PATH)
        )
    elif command == "cat-file":
        valid = bool(
            len(suffix) == 2
            and suffix[0] == "blob"
            and _FULL_OBJECT_ID.fullmatch(suffix[1]) is not None
        )
    elif command == "add":
        valid = suffix == ("--", AUTOCRLF_PROOF_PATH)
    if not valid:
        raise ValueError(f"release Git autocrlf proof {command} arguments are not allowed")
    return normalized


def _hardened_arguments(
    repository: Path,
    arguments: Sequence[str],
    *,
    bind_worktree: bool,
) -> tuple[str, ...]:
    safe_config = tuple(item for value in _SAFE_GIT_CONFIG for item in ("-c", value))
    worktree_config = (
        "-c",
        f"core.worktree={_path_text(repository, label='repository')}",
        "-c",
        "core.bare=false",
    )
    return (
        "--no-pager",
        "--no-replace-objects",
        "-C",
        _path_text(repository, label="repository"),
        *(worktree_config if bind_worktree else ()),
        *safe_config,
        *arguments,
    )


def _dangerous_config_classes(names: Iterable[str]) -> set[str]:
    classes: set[str] = set()
    for raw_name in names:
        name = raw_name.strip().casefold()
        if name.startswith("filter.") and name.endswith((".clean", ".smudge", ".process")):
            classes.add("filter")
        elif name.startswith("merge.") and name.endswith(".driver"):
            classes.add("merge driver")
        elif name == "diff.external" or (
            name.startswith("diff.") and name.endswith((".command", ".textconv"))
        ):
            classes.add("diff command")
    return classes


def _checked_output(result: Any, *, accepted: frozenset[int]) -> bytes:
    if result.timed_out:
        raise ReleaseGitError("release Git command exceeded its time limit")
    if result.stdout_truncated or result.stderr_truncated:
        raise ReleaseGitError("release Git command exceeded its output limit")
    if result.returncode not in accepted:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        if not detail:
            detail = (
                f"release Git command was terminated by signal {-result.returncode}"
                if result.returncode < 0
                else f"release Git command failed with exit code {result.returncode}"
            )
        raise ReleaseGitError(detail)
    return result.stdout


def _run_frozen_git(
    launcher: PreparedProcessArgv,
    repository: Path,
    process_cwd: Path,
    environment: Mapping[str, str],
    arguments: Sequence[str],
    *,
    bind_worktree: bool,
    identities: Sequence[_DirectoryIdentity],
    input_bytes: bytes | None = None,
    accepted: frozenset[int] = frozenset({0}),
    max_stdout_bytes: int = DEFAULT_STDOUT_BYTES,
    max_stderr_bytes: int = DEFAULT_STDERR_BYTES,
    timeout: float = GIT_TIMEOUT_SECONDS,
    allow_config_inspection: bool = False,
) -> bytes:
    normalized = _validate_arguments(
        arguments,
        allow_config_inspection=allow_config_inspection,
    )
    argv = launcher.bind(
        *_hardened_arguments(
            repository,
            normalized,
            bind_worktree=bind_worktree,
        )
    )
    _require_identities(identities)
    try:
        result = run_bounded_binary_process(
            argv,
            cwd=str(process_cwd),
            env=dict(environment),
            input_bytes=input_bytes,
            timeout=timeout,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
        )
    finally:
        _require_identities(identities)
    return _checked_output(result, accepted=accepted)


def _decode_identity_paths(payload: bytes) -> tuple[Path, Path, Path]:
    if not payload.endswith(b"\n") or b"\x00" in payload or b"\r" in payload:
        raise ReleaseGitError("release Git repository identity output is malformed")
    lines = payload.splitlines()
    if len(lines) != 3 or any(not line for line in lines):
        raise ReleaseGitError("release Git repository identity output is incomplete")
    paths: list[Path] = []
    for line in lines:
        try:
            text = line.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ReleaseGitError("release Git repository identity is not UTF-8") from exc
        if any(ord(character) < 32 or ord(character) == 127 for character in text):
            raise ReleaseGitError(
                "release Git repository identity contains an unsupported character"
            )
        try:
            paths.append(Path(text).resolve(strict=True))
        except (OSError, RuntimeError, ValueError) as exc:
            raise ReleaseGitError("release Git repository identity is unavailable") from exc
    return paths[0], paths[1], paths[2]


def _probe_repository_identity(
    launcher: PreparedProcessArgv,
    repository: Path,
    process_cwd: Path,
    environment: Mapping[str, str],
    *,
    bind_worktree: bool,
    identities: Sequence[_DirectoryIdentity],
) -> tuple[Path, Path, Path]:
    payload = _run_frozen_git(
        launcher,
        repository,
        process_cwd,
        environment,
        (
            "rev-parse",
            "--path-format=absolute",
            "--show-toplevel",
            "--absolute-git-dir",
            "--git-common-dir",
        ),
        bind_worktree=bind_worktree,
        identities=identities,
        max_stdout_bytes=_MAX_IDENTITY_OUTPUT_BYTES,
    )
    return _decode_identity_paths(payload)


def _config_names(payload: bytes) -> tuple[str, ...]:
    parts = payload.split(b"\x00")
    if not parts or parts[-1] != b"" or (len(parts) - 1) % 3:
        raise ReleaseGitError("release Git configuration inspection is malformed")
    names: list[str] = []
    for index in range(0, len(parts) - 1, 3):
        encoded_scope, _origin, encoded_name = parts[index : index + 3]
        try:
            scope = encoded_scope.decode("ascii", errors="strict")
            name = encoded_name.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise ReleaseGitError("release Git configuration metadata is invalid") from exc
        if scope not in _CONFIG_SCOPES:
            raise ReleaseGitError(f"unexpected effective Git configuration scope: {scope}")
        if scope != "command":
            names.append(name)
    return tuple(names)


@dataclass(frozen=True, slots=True)
class ReleaseGit:
    """One identity-frozen Git executable and hostile-config-free repository session."""

    root: Path
    launcher: PreparedProcessArgv
    environment: Mapping[str, str]
    process_cwd: Path
    git_dir: Path
    common_dir: Path
    _identities: tuple[_DirectoryIdentity, ...]

    @classmethod
    def discover(cls, root: Path) -> ReleaseGit:
        try:
            repository = root.resolve(strict=True)
        except (OSError, RuntimeError, ValueError) as exc:
            raise ReleaseGitError("release repository is unavailable") from exc
        _path_text(repository, label="repository")
        root_identity = _directory_identity(repository, label="repository")

        search_path = sanitized_executable_search_path(
            os.environ.get("PATH", ""),
            current_directory=repository,
            forbidden_roots=(repository,),
        )
        resolved = resolve_executable_path(
            "git",
            search_path=search_path,
            current_directory=repository,
        )
        prepared = prepare_process_argv([resolved])
        frozen = freeze_process_argv(prepared, forbidden_roots=(repository,))
        if frozen.argument_offset != 1 or len(frozen.artifact_paths) != 1:
            raise ReleaseGitError("release Git must resolve to one native executable")
        process_cwd = Path(frozen[0]).parent.resolve(strict=True)
        process_identity = _directory_identity(
            process_cwd,
            label="Git executable parent",
        )
        discovery_identities = (root_identity, process_identity)
        discovery_environment = _git_environment(process_cwd)

        top_level, git_dir, common_dir = _probe_repository_identity(
            frozen,
            repository,
            process_cwd,
            discovery_environment,
            bind_worktree=False,
            identities=discovery_identities,
        )
        if top_level != repository:
            raise ReleaseGitError("release repository must be the exact Git worktree top-level")

        identities = _directory_identities(
            (
                (repository, "repository"),
                (git_dir, "Git metadata"),
                (common_dir, "Git common metadata"),
                (process_cwd, "Git executable parent"),
            )
        )
        environment = _git_environment(
            process_cwd,
            repository=repository,
            git_dir=git_dir,
            common_dir=common_dir,
        )
        session = cls(
            repository,
            frozen,
            environment,
            process_cwd,
            git_dir,
            common_dir,
            identities,
        )
        session._require_repository_binding()
        session._reject_executable_configuration()
        session._require_repository_binding()
        return session

    def _require_repository_binding(self) -> None:
        top_level, git_dir, common_dir = _probe_repository_identity(
            self.launcher,
            self.root,
            self.process_cwd,
            self.environment,
            bind_worktree=True,
            identities=self._identities,
        )
        if top_level != self.root or git_dir != self.git_dir or common_dir != self.common_dir:
            raise ReleaseGitError("release Git repository binding changed identity")

    def _reject_executable_configuration(self) -> None:
        inspection = _run_frozen_git(
            self.launcher,
            self.root,
            self.process_cwd,
            self.environment,
            (
                "config",
                "--includes",
                "--show-origin",
                "--show-scope",
                "--null",
                "--name-only",
                "--list",
            ),
            bind_worktree=True,
            identities=self._identities,
            allow_config_inspection=True,
        )
        dangerous = _dangerous_config_classes(_config_names(inspection))
        if dangerous:
            kinds = ", ".join(sorted(dangerous))
            raise ReleaseGitError(f"release Git operation refused executable {kinds} configuration")

    def _argv(self, arguments: Sequence[str]) -> PreparedProcessArgv:
        normalized = _validate_arguments(arguments)
        return self.launcher.bind(
            *_hardened_arguments(
                self.root,
                normalized,
                bind_worktree=True,
            )
        )

    def _autocrlf_proof_argv(self, arguments: Sequence[str]) -> PreparedProcessArgv:
        normalized = _validate_autocrlf_proof_arguments(arguments)
        return self.launcher.bind(
            *_hardened_arguments(
                self.root,
                ("-c", _AUTOCRLF_PROOF_CONFIG, *normalized),
                bind_worktree=True,
            )
        )

    def run_bytes(
        self,
        arguments: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        accepted: Iterable[int] = (0,),
        max_stdout_bytes: int = DEFAULT_STDOUT_BYTES,
        max_stderr_bytes: int = DEFAULT_STDERR_BYTES,
        timeout: float = GIT_TIMEOUT_SECONDS,
    ) -> bytes:
        """Run one bounded binary-safe Git command through the frozen executable."""

        accepted_codes = frozenset(accepted)
        if not accepted_codes or any(
            isinstance(code, bool) or not isinstance(code, int) for code in accepted_codes
        ):
            raise ValueError("accepted Git exit codes must be non-empty integers")
        result = self._run_result(
            arguments,
            input_bytes=input_bytes,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
            timeout=timeout,
        )
        return _checked_output(result, accepted=accepted_codes)

    def _run_result(
        self,
        arguments: Sequence[str],
        *,
        input_bytes: bytes | None = None,
        max_stdout_bytes: int = DEFAULT_STDOUT_BYTES,
        max_stderr_bytes: int = DEFAULT_STDERR_BYTES,
        timeout: float = GIT_TIMEOUT_SECONDS,
    ) -> Any:
        return self._run_prepared_result(
            self._argv(arguments),
            input_bytes=input_bytes,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
            timeout=timeout,
        )

    def _run_prepared_result(
        self,
        argv: PreparedProcessArgv,
        *,
        input_bytes: bytes | None = None,
        max_stdout_bytes: int = DEFAULT_STDOUT_BYTES,
        max_stderr_bytes: int = DEFAULT_STDERR_BYTES,
        timeout: float = GIT_TIMEOUT_SECONDS,
    ) -> Any:
        _require_identities(self._identities)
        try:
            return run_bounded_binary_process(
                argv,
                cwd=str(self.process_cwd),
                env=dict(self.environment),
                input_bytes=input_bytes,
                timeout=timeout,
                max_stdout_bytes=max_stdout_bytes,
                max_stderr_bytes=max_stderr_bytes,
            )
        finally:
            _require_identities(self._identities)

    def run_autocrlf_proof_bytes(
        self,
        arguments: Sequence[str],
        *,
        max_stdout_bytes: int = DEFAULT_STDOUT_BYTES,
        max_stderr_bytes: int = DEFAULT_STDERR_BYTES,
        timeout: float = GIT_TIMEOUT_SECONDS,
    ) -> bytes:
        """Run one allowlisted command with command-scoped ``core.autocrlf=true``."""

        result = self._run_prepared_result(
            self._autocrlf_proof_argv(arguments),
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
            timeout=timeout,
        )
        return _checked_output(result, accepted=frozenset({0}))

    def is_ignored(self, relative_path: str) -> bool:
        """Return whether one repository-relative sentinel is ignored."""

        result = self._run_result(
            ["check-ignore", "-q", "--no-index", "--", relative_path],
        )
        _checked_output(result, accepted=frozenset({0, 1}))
        return result.returncode == 0


__all__ = ["AUTOCRLF_PROOF_PATH", "ReleaseGit", "ReleaseGitError"]
