"""Create and verify one Git-clean physical CRLF release-source probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.release_git import (
    AUTOCRLF_PROOF_PATH,
    ReleaseGit,
    ReleaseGitError,
)

_EXPECTED_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_PROBE_PATH = AUTOCRLF_PROOF_PATH
_MAX_PROBE_BYTES = 64 * 1024
_WINDOWS_REPARSE_POINT = 0x400
_OPEN_BINARY = getattr(os, "O_BINARY", 0)
_OPEN_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_COPY_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class _FileIdentity:
    device: int
    inode: int
    mode: int
    attributes: int
    links: int


def _file_identity(metadata: os.stat_result, *, label: str) -> _FileIdentity:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    inode = int(metadata.st_ino)
    links = int(metadata.st_nlink)
    if (
        stat.S_ISLNK(metadata.st_mode)
        or attributes & _WINDOWS_REPARSE_POINT
        or not stat.S_ISREG(metadata.st_mode)
    ):
        raise ReleaseGitError(f"{label} must be a real regular file")
    if inode <= 0:
        raise ReleaseGitError(f"{label} has no stable filesystem identity")
    if links != 1:
        raise ReleaseGitError(f"{label} must not be hard-linked")
    return _FileIdentity(
        device=int(metadata.st_dev),
        inode=inode,
        mode=int(metadata.st_mode),
        attributes=attributes,
        links=links,
    )


def _checked_fixed_git_command(git: ReleaseGit, arguments: tuple[str, ...]) -> bytes:
    """Run one fixed proof-only command through the frozen Git executable."""

    return git.run_autocrlf_proof_bytes(
        arguments,
        timeout=30,
        max_stdout_bytes=_MAX_PROBE_BYTES,
        max_stderr_bytes=4 * 1024,
    )


def _require_autocrlf_override(git: ReleaseGit) -> None:
    configured = _checked_fixed_git_command(
        git,
        ("config", "--get-all", "core.autocrlf"),
    )
    if configured != b"true\n":
        raise ReleaseGitError("autocrlf proof could not bind one exact command-scoped true value")


def _require_reviewed_clean_checkout(git: ReleaseGit, expected_commit: str) -> None:
    head = _checked_fixed_git_command(
        git,
        ("rev-parse", "--verify", "HEAD^{commit}"),
    )
    if head != expected_commit.encode("ascii") + b"\n":
        raise ReleaseGitError("autocrlf proof HEAD does not match the reviewed commit")
    status = _checked_fixed_git_command(
        git,
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=none",
        ),
    )
    if status:
        raise ReleaseGitError("autocrlf proof requires a Git-clean checkout")


def _canonical_probe_blob(git: ReleaseGit, expected_commit: str) -> tuple[str, bytes]:
    manifest = _checked_fixed_git_command(
        git,
        (
            "ls-tree",
            "-r",
            "-l",
            "-z",
            "--full-tree",
            expected_commit,
            "--",
            _PROBE_PATH,
        ),
    )
    match = re.fullmatch(
        rb"100644 blob ([0-9a-f]{40}|[0-9a-f]{64}) +([0-9]+)\tLICENSE\x00",
        manifest,
    )
    if match is None:
        raise ReleaseGitError("autocrlf proof source is not one regular reviewed Git blob")
    object_id = match.group(1).decode("ascii")
    size = int(match.group(2))
    if size <= 0 or size > _MAX_PROBE_BYTES:
        raise ReleaseGitError("autocrlf proof source exceeds its byte budget")
    payload = _checked_fixed_git_command(
        git,
        ("cat-file", "blob", object_id),
    )
    if len(payload) != size:
        raise ReleaseGitError("autocrlf proof source blob size is inconsistent")
    digest = hashlib.new("sha1" if len(object_id) == 40 else "sha256")
    digest.update(f"blob {size}\0".encode("ascii"))
    digest.update(payload)
    if digest.hexdigest() != object_id:
        raise ReleaseGitError("autocrlf proof source blob identity is inconsistent")
    if b"\n" not in payload or b"\r" in payload:
        raise ReleaseGitError("autocrlf proof source must be canonical LF text")
    return object_id, payload


def _real_regular_probe(root: Path) -> tuple[Path, _FileIdentity, int]:
    probe = root / _PROBE_PATH
    try:
        metadata = os.lstat(probe)
    except OSError as exc:
        raise ReleaseGitError("autocrlf proof working-tree source is unavailable") from exc
    identity = _file_identity(metadata, label="autocrlf proof working-tree source")
    if metadata.st_size > _MAX_PROBE_BYTES:
        raise ReleaseGitError("autocrlf proof working-tree source exceeds its byte budget")
    return probe, identity, int(metadata.st_size)


def _read_descriptor(descriptor: int, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = os.read(descriptor, min(remaining, _COPY_CHUNK_BYTES))
        if not chunk:
            raise ReleaseGitError("autocrlf proof source read was truncated")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise ReleaseGitError("autocrlf proof source grew during its bounded read")
    return b"".join(chunks)


def _write_descriptor(descriptor: int, payload: bytes) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset : offset + _COPY_CHUNK_BYTES])
        if written <= 0:
            raise ReleaseGitError("autocrlf proof source write made no progress")
        offset += written
    os.ftruncate(descriptor, len(payload))
    os.fsync(descriptor)


def _rewrite_probe(root: Path, canonical: bytes, physical_crlf: bytes) -> _FileIdentity:
    probe, expected_identity, expected_size = _real_regular_probe(root)
    try:
        descriptor = os.open(
            probe,
            os.O_RDWR | _OPEN_BINARY | _OPEN_NOFOLLOW,
        )
    except OSError as exc:
        raise ReleaseGitError("autocrlf proof could not open its fixed source safely") from exc
    try:
        opened_identity = _file_identity(
            os.fstat(descriptor),
            label="autocrlf proof opened working-tree source",
        )
        if opened_identity != expected_identity:
            raise ReleaseGitError("autocrlf proof source changed identity while opening")
        before = _read_descriptor(descriptor, expected_size)
        if before not in {canonical, physical_crlf}:
            raise ReleaseGitError("autocrlf proof source has unexpected physical bytes")
        if before != physical_crlf:
            _write_descriptor(descriptor, physical_crlf)
        os.lseek(descriptor, 0, os.SEEK_SET)
        observed = _read_descriptor(descriptor, len(physical_crlf))
        if (
            _file_identity(
                os.fstat(descriptor),
                label="autocrlf proof opened working-tree source",
            )
            != expected_identity
        ):
            raise ReleaseGitError("autocrlf proof opened source changed identity")
    except OSError as exc:
        raise ReleaseGitError("autocrlf proof could not rewrite its fixed source safely") from exc
    finally:
        os.close(descriptor)

    _probe, final_identity, final_size = _real_regular_probe(root)
    if final_identity != expected_identity or final_size != len(physical_crlf):
        raise ReleaseGitError("autocrlf proof source changed identity after rewrite")
    if observed != physical_crlf or b"\r\n" not in observed:
        raise ReleaseGitError("autocrlf proof did not create exact physical CRLF bytes")
    if observed == canonical:
        raise ReleaseGitError("autocrlf proof did not diverge physically from the Git blob")
    return expected_identity


def _final_probe_read(
    root: Path,
    expected_identity: _FileIdentity,
    expected_payload: bytes,
) -> bytes:
    probe, path_identity, path_size = _real_regular_probe(root)
    if path_identity != expected_identity or path_size != len(expected_payload):
        raise ReleaseGitError("autocrlf proof source changed before its final read")
    try:
        descriptor = os.open(
            probe,
            os.O_RDONLY | _OPEN_BINARY | _OPEN_NOFOLLOW,
        )
    except OSError as exc:
        raise ReleaseGitError("autocrlf proof could not open its final source safely") from exc
    try:
        opened_identity = _file_identity(
            os.fstat(descriptor),
            label="autocrlf proof final opened source",
        )
        if opened_identity != expected_identity:
            raise ReleaseGitError("autocrlf proof source changed identity before its final read")
        observed = _read_descriptor(descriptor, len(expected_payload))
        if (
            _file_identity(
                os.fstat(descriptor),
                label="autocrlf proof final opened source",
            )
            != expected_identity
        ):
            raise ReleaseGitError("autocrlf proof source changed identity during its final read")
    except OSError as exc:
        raise ReleaseGitError("autocrlf proof could not read its final source safely") from exc
    finally:
        os.close(descriptor)

    _probe, final_identity, final_size = _real_regular_probe(root)
    if final_identity != expected_identity or final_size != len(expected_payload):
        raise ReleaseGitError("autocrlf proof source changed after its final read")
    if observed != expected_payload:
        raise ReleaseGitError("autocrlf proof final source bytes are not exact physical CRLF")
    return observed


def prepare_autocrlf_checkout(root: Path, expected_commit: str) -> dict[str, Any]:
    """Make the fixed probe physically CRLF while Git still reports exact clean HEAD."""

    if _EXPECTED_COMMIT.fullmatch(expected_commit) is None:
        raise ValueError("expected commit must be one full lowercase Git object ID")
    try:
        repository = root.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ReleaseGitError("autocrlf proof repository is unavailable") from exc

    initial_git = ReleaseGit.discover(repository)
    _require_autocrlf_override(initial_git)
    git = initial_git
    _require_reviewed_clean_checkout(git, expected_commit)
    object_id, canonical = _canonical_probe_blob(git, expected_commit)

    physical_crlf = canonical.replace(b"\n", b"\r\n")
    rewritten_identity = _rewrite_probe(repository, canonical, physical_crlf)

    _checked_fixed_git_command(git, ("add", "--", _PROBE_PATH))
    git = ReleaseGit.discover(repository)
    _require_reviewed_clean_checkout(git, expected_commit)
    repeated_object_id, repeated_canonical = _canonical_probe_blob(git, expected_commit)
    if (repeated_object_id, repeated_canonical) != (object_id, canonical):
        raise ReleaseGitError("autocrlf proof reviewed Git blob changed during preparation")
    observed = _final_probe_read(repository, rewritten_identity, physical_crlf)

    return {
        "autocrlf_scope": "command",
        "blob_sha256": hashlib.sha256(canonical).hexdigest(),
        "commit": expected_commit,
        "core.autocrlf": True,
        "git_status": "clean",
        "path": _PROBE_PATH,
        "physical_line_endings": "crlf",
        "physical_sha256": hashlib.sha256(observed).hexdigest(),
        "reviewed_blob": object_id,
        "reviewed_line_endings": "lf",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        receipt = prepare_autocrlf_checkout(args.repository, args.expected_commit)
    except (OSError, ReleaseGitError, ValueError) as exc:
        print(f"Autocrlf checkout proof failed: {str(exc)[:512]}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
