"""Hosted line-ending proof uses a clean checkout with physically different bytes."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import prove_autocrlf_checkout as subject


def _git(repository: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    return completed.stdout


def _repository(tmp_path: Path) -> tuple[Path, str, bytes]:
    repository = tmp_path / "repo"
    repository.mkdir()
    _git(repository, "init", "--initial-branch=main")
    _git(repository, "config", "user.name", "Release Test")
    _git(repository, "config", "user.email", "release@example.invalid")
    (repository / ".gitattributes").write_bytes(b"* text=auto eol=lf\n")
    canonical = b"License line one\nLicense line two\n"
    (repository / "LICENSE").write_bytes(canonical)
    _git(repository, "-c", "core.autocrlf=false", "add", ".")
    _git(repository, "commit", "-m", "fixture")
    commit = _git(repository, "rev-parse", "HEAD").decode("ascii").strip()
    return repository, commit, canonical


def test_probe_is_idempotent_and_proves_clean_crlf_against_reviewed_lf(
    tmp_path: Path,
) -> None:
    repository, commit, canonical = _repository(tmp_path)

    first = subject.prepare_autocrlf_checkout(repository, commit)
    second = subject.prepare_autocrlf_checkout(repository, commit)

    physical = canonical.replace(b"\n", b"\r\n")
    assert first == second
    assert first == {
        "autocrlf_scope": "command",
        "blob_sha256": hashlib.sha256(canonical).hexdigest(),
        "commit": commit,
        "core.autocrlf": True,
        "git_status": "clean",
        "path": "LICENSE",
        "physical_line_endings": "crlf",
        "physical_sha256": hashlib.sha256(physical).hexdigest(),
        "reviewed_blob": _git(repository, "rev-parse", "HEAD:LICENSE").decode("ascii").strip(),
        "reviewed_line_endings": "lf",
    }
    assert (repository / "LICENSE").read_bytes() == physical
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == b""
    assert _git(repository, "hash-object", "--no-filters", "LICENSE").strip() != (
        _git(repository, "rev-parse", "HEAD:LICENSE").strip()
    )


def test_probe_refuses_dirty_checkout_without_mutating_fixed_source(tmp_path: Path) -> None:
    repository, commit, canonical = _repository(tmp_path)
    (repository / "unexpected.txt").write_text("dirty\n", encoding="utf-8")

    with pytest.raises(subject.ReleaseGitError, match="Git-clean checkout"):
        subject.prepare_autocrlf_checkout(repository, commit)

    assert (repository / "LICENSE").read_bytes() == canonical


def test_probe_succeeds_in_linked_worktree_without_shared_metadata_side_effect(
    tmp_path: Path,
) -> None:
    repository, commit, canonical = _repository(tmp_path)
    linked = tmp_path / "linked"
    _git(repository, "worktree", "add", "--detach", str(linked), commit)
    git_dir = Path(_git(linked, "rev-parse", "--absolute-git-dir").decode().strip())
    common_dir = Path(_git(linked, "rev-parse", "--git-common-dir").decode().strip()).resolve()
    assert git_dir.resolve() != common_dir
    common_config = common_dir / "config"
    before_config = common_config.read_bytes()
    attributes = common_dir / "info" / "attributes"
    assert not attributes.exists()

    receipt = subject.prepare_autocrlf_checkout(linked, commit)

    assert receipt["git_status"] == "clean"
    assert receipt["physical_line_endings"] == "crlf"
    assert common_config.read_bytes() == before_config
    assert not attributes.exists()
    assert (linked / "LICENSE").read_bytes() == canonical.replace(b"\n", b"\r\n")
    assert _git(linked, "status", "--porcelain=v1", "--untracked-files=all") == b""


def test_probe_cli_emits_bounded_machine_readable_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository, commit, _canonical = _repository(tmp_path)

    assert (
        subject.main(
            [
                "--repository",
                str(repository),
                "--expected-commit",
                commit,
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["autocrlf_scope"] == "command"
    assert receipt["commit"] == commit
    assert receipt["core.autocrlf"] is True
    assert receipt["git_status"] == "clean"
    assert receipt["physical_line_endings"] == "crlf"
    assert receipt["reviewed_line_endings"] == "lf"


@pytest.mark.parametrize("value", ["abc", "A" * 40, "0" * 39, "0" * 65])
def test_probe_requires_one_full_lowercase_object_id(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValueError, match="full lowercase Git object ID"):
        subject.prepare_autocrlf_checkout(tmp_path, value)


def _metadata(
    *,
    mode: int = stat.S_IFREG | 0o644,
    inode: int = 7,
    device: int = 3,
    size: int = 1,
    links: int = 1,
    attributes: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        st_dev=device,
        st_file_attributes=attributes,
        st_ino=inode,
        st_mode=mode,
        st_nlink=links,
        st_size=size,
    )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        (_metadata(mode=stat.S_IFLNK | 0o777), "real regular file"),
        (_metadata(attributes=subject._WINDOWS_REPARSE_POINT), "real regular file"),
        (_metadata(mode=stat.S_IFDIR | 0o755), "real regular file"),
        (_metadata(inode=0), "stable filesystem identity"),
        (_metadata(links=2), "must not be hard-linked"),
    ],
)
def test_file_identity_rejects_aliasing_and_unstable_metadata(
    metadata: SimpleNamespace,
    message: str,
) -> None:
    with pytest.raises(subject.ReleaseGitError, match=message):
        subject._file_identity(metadata, label="probe")


def test_fixed_git_command_uses_only_the_public_bounded_api() -> None:
    calls: list[tuple[tuple[str, ...], dict[str, int]]] = []

    class Git:
        @staticmethod
        def run_autocrlf_proof_bytes(
            arguments: tuple[str, ...],
            **limits: int,
        ) -> bytes:
            calls.append((arguments, limits))
            return b"ok"

    assert subject._checked_fixed_git_command(Git(), ("fixed",)) == b"ok"
    assert calls == [
        (
            ("fixed",),
            {
                "timeout": 30,
                "max_stdout_bytes": subject._MAX_PROBE_BYTES,
                "max_stderr_bytes": 4 * 1024,
            },
        )
    ]


def test_autocrlf_override_requires_one_exact_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "_checked_fixed_git_command", lambda *_args: b"false\n")

    with pytest.raises(subject.ReleaseGitError, match="one exact command-scoped true"):
        subject._require_autocrlf_override(SimpleNamespace())


def _command_outputs(
    monkeypatch: pytest.MonkeyPatch,
    *outputs: bytes,
) -> SimpleNamespace:
    values = iter(outputs)
    monkeypatch.setattr(subject, "_checked_fixed_git_command", lambda *_args: next(values))
    return SimpleNamespace()


def test_reviewed_checkout_rejects_wrong_head_and_dirty_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = "1" * 40
    with pytest.raises(subject.ReleaseGitError, match="HEAD does not match"):
        subject._require_reviewed_clean_checkout(
            _command_outputs(monkeypatch, b"2" * 40 + b"\n"),
            commit,
        )
    with pytest.raises(subject.ReleaseGitError, match="Git-clean checkout"):
        subject._require_reviewed_clean_checkout(
            _command_outputs(
                monkeypatch,
                commit.encode("ascii") + b"\n",
                b" M LICENSE\x00",
            ),
            commit,
        )


def _blob_entry(
    payload: bytes,
    *,
    algorithm: str = "sha1",
    object_id: str | None = None,
    size: int | None = None,
) -> tuple[bytes, str]:
    digest = hashlib.new(algorithm)
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    identity = object_id or digest.hexdigest()
    manifest = f"100644 blob {identity} {len(payload) if size is None else size}\tLICENSE\0".encode(
        "ascii"
    )
    return manifest, identity


def test_canonical_blob_accepts_sha256_and_rejects_malformed_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"canonical\n"
    manifest, identity = _blob_entry(payload, algorithm="sha256")
    assert subject._canonical_probe_blob(
        _command_outputs(monkeypatch, manifest, payload),
        "1" * 64,
    ) == (identity, payload)
    with pytest.raises(subject.ReleaseGitError, match="one regular reviewed Git blob"):
        subject._canonical_probe_blob(
            _command_outputs(monkeypatch, b"malformed"),
            "1" * 40,
        )


@pytest.mark.parametrize("size", [0, subject._MAX_PROBE_BYTES + 1])
def test_canonical_blob_rejects_invalid_size(
    size: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _identity = _blob_entry(b"x\n", size=size)
    with pytest.raises(subject.ReleaseGitError, match="byte budget"):
        subject._canonical_probe_blob(
            _command_outputs(monkeypatch, manifest),
            "1" * 40,
        )


def test_canonical_blob_rejects_size_and_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"x\n"
    manifest, _identity = _blob_entry(payload, size=len(payload) + 1)
    with pytest.raises(subject.ReleaseGitError, match="size is inconsistent"):
        subject._canonical_probe_blob(
            _command_outputs(monkeypatch, manifest, payload),
            "1" * 40,
        )

    manifest, _identity = _blob_entry(payload, object_id="0" * 40)
    with pytest.raises(subject.ReleaseGitError, match="identity is inconsistent"):
        subject._canonical_probe_blob(
            _command_outputs(monkeypatch, manifest, payload),
            "1" * 40,
        )


@pytest.mark.parametrize("payload", [b"no newline", b"has\r\n"])
def test_canonical_blob_requires_lf_only_text(
    payload: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, _identity = _blob_entry(payload)
    with pytest.raises(subject.ReleaseGitError, match="canonical LF text"):
        subject._canonical_probe_blob(
            _command_outputs(monkeypatch, manifest, payload),
            "1" * 40,
        )


def test_real_probe_rejects_missing_oversize_and_hardlinked_source(tmp_path: Path) -> None:
    with pytest.raises(subject.ReleaseGitError, match="source is unavailable"):
        subject._real_regular_probe(tmp_path)

    source = tmp_path / "LICENSE"
    source.write_bytes(b"x" * (subject._MAX_PROBE_BYTES + 1))
    with pytest.raises(subject.ReleaseGitError, match="byte budget"):
        subject._real_regular_probe(tmp_path)

    source.write_bytes(b"safe\n")
    alias = tmp_path / "alias"
    os.link(source, alias)
    with pytest.raises(subject.ReleaseGitError, match="must not be hard-linked"):
        subject._real_regular_probe(tmp_path)


def test_descriptor_reads_are_exact_and_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "payload"
    path.write_bytes(b"abc")
    descriptor = os.open(path, os.O_RDONLY | subject._OPEN_BINARY)
    try:
        with pytest.raises(subject.ReleaseGitError, match="read was truncated"):
            subject._read_descriptor(descriptor, 4)
        os.lseek(descriptor, 0, os.SEEK_SET)
        with pytest.raises(subject.ReleaseGitError, match="grew"):
            subject._read_descriptor(descriptor, 2)
        os.lseek(descriptor, 0, os.SEEK_SET)
        monkeypatch.setattr(subject, "_COPY_CHUNK_BYTES", 1)
        assert subject._read_descriptor(descriptor, 3) == b"abc"
    finally:
        os.close(descriptor)


def test_descriptor_write_rejects_zero_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "payload"
    path.write_bytes(b"x")
    descriptor = os.open(path, os.O_RDWR | subject._OPEN_BINARY)
    monkeypatch.setattr(subject.os, "write", lambda *_args: 0)
    try:
        with pytest.raises(subject.ReleaseGitError, match="made no progress"):
            subject._write_descriptor(descriptor, b"replacement")
    finally:
        os.close(descriptor)


def _identity_for(path: Path) -> subject._FileIdentity:
    return subject._file_identity(os.lstat(path), label="fixture")


def test_rewrite_rejects_open_identity_and_unexpected_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = tmp_path / "LICENSE"
    probe.write_bytes(b"canonical\n")
    expected = _identity_for(probe)
    changed = subject._FileIdentity(
        expected.device,
        expected.inode + 1,
        expected.mode,
        expected.attributes,
        expected.links,
    )
    monkeypatch.setattr(
        subject,
        "_real_regular_probe",
        lambda _root: (probe, expected, probe.stat().st_size),
    )
    monkeypatch.setattr(subject, "_file_identity", lambda *_args, **_kwargs: changed)
    with pytest.raises(subject.ReleaseGitError, match="changed identity while opening"):
        subject._rewrite_probe(tmp_path, b"canonical\n", b"canonical\r\n")

    monkeypatch.undo()
    probe.write_bytes(b"unexpected")
    with pytest.raises(subject.ReleaseGitError, match="unexpected physical bytes"):
        subject._rewrite_probe(tmp_path, b"canonical\n", b"canonical\r\n")


def test_rewrite_rejects_descriptor_identity_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = tmp_path / "LICENSE"
    probe.write_bytes(b"canonical\n")
    expected = _identity_for(probe)
    changed = subject._FileIdentity(
        expected.device,
        expected.inode + 1,
        expected.mode,
        expected.attributes,
        expected.links,
    )
    identities = iter((expected, expected, changed))
    monkeypatch.setattr(subject, "_file_identity", lambda *_args, **_kwargs: next(identities))

    with pytest.raises(subject.ReleaseGitError, match="opened source changed identity"):
        subject._rewrite_probe(tmp_path, b"canonical\n", b"canonical\r\n")


def test_rewrite_wraps_open_errors_without_closing_invalid_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "LICENSE").write_bytes(b"canonical\n")
    closes: list[int] = []
    monkeypatch.setattr(
        subject.os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError())
    )
    monkeypatch.setattr(subject.os, "close", lambda descriptor: closes.append(descriptor))

    with pytest.raises(subject.ReleaseGitError, match="open its fixed source safely"):
        subject._rewrite_probe(tmp_path, b"canonical\n", b"canonical\r\n")

    assert closes == []


def test_rewrite_wraps_body_oserror_and_closes_open_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = tmp_path / "LICENSE"
    probe.write_bytes(b"canonical\n")
    real_open = subject.os.open
    real_close = subject.os.close
    opened: list[int] = []
    closed: list[int] = []

    def tracked_open(*args: Any, **kwargs: Any) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def tracked_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    monkeypatch.setattr(subject.os, "open", tracked_open)
    monkeypatch.setattr(subject.os, "close", tracked_close)
    monkeypatch.setattr(subject.os, "fstat", lambda _descriptor: (_ for _ in ()).throw(OSError()))

    with pytest.raises(subject.ReleaseGitError, match="rewrite its fixed source safely"):
        subject._rewrite_probe(tmp_path, b"canonical\n", b"canonical\r\n")

    assert opened == closed


@pytest.mark.parametrize("change", ["identity", "size"])
def test_rewrite_rejects_final_path_identity_or_size_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    probe = tmp_path / "LICENSE"
    canonical = b"canonical\n"
    physical = b"canonical\r\n"
    probe.write_bytes(canonical)
    expected = _identity_for(probe)
    changed = subject._FileIdentity(
        expected.device,
        expected.inode + 1,
        expected.mode,
        expected.attributes,
        expected.links,
    )
    final_identity = changed if change == "identity" else expected
    final_size = len(physical) + 1 if change == "size" else len(physical)
    observations = iter(
        (
            (probe, expected, len(canonical)),
            (probe, final_identity, final_size),
        )
    )
    monkeypatch.setattr(subject, "_real_regular_probe", lambda _root: next(observations))

    with pytest.raises(subject.ReleaseGitError, match="identity after rewrite"):
        subject._rewrite_probe(tmp_path, canonical, physical)


@pytest.mark.parametrize(
    ("canonical", "physical", "observed", "message"),
    [
        (b"canonical\n", b"canonical\r\n", b"wrong\r\n", "exact physical CRLF"),
        (b"canonical\n", b"no-crlf", b"no-crlf", "exact physical CRLF"),
        (b"same\r\n", b"same\r\n", b"same\r\n", "diverge physically"),
    ],
)
def test_rewrite_rejects_invalid_readback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical: bytes,
    physical: bytes,
    observed: bytes,
    message: str,
) -> None:
    probe = tmp_path / "LICENSE"
    probe.write_bytes(canonical)
    reads = iter((canonical, observed))
    monkeypatch.setattr(subject, "_read_descriptor", lambda *_args: next(reads))

    with pytest.raises(subject.ReleaseGitError, match=message):
        subject._rewrite_probe(tmp_path, canonical, physical)


@pytest.mark.parametrize("change", ["identity", "size"])
def test_final_read_rejects_pre_open_path_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    probe = tmp_path / "LICENSE"
    payload = b"physical\r\n"
    probe.write_bytes(payload)
    expected = _identity_for(probe)
    changed = subject._FileIdentity(
        expected.device,
        expected.inode + 1,
        expected.mode,
        expected.attributes,
        expected.links,
    )
    monkeypatch.setattr(
        subject,
        "_real_regular_probe",
        lambda _root: (
            probe,
            changed if change == "identity" else expected,
            len(payload) + (change == "size"),
        ),
    )

    with pytest.raises(subject.ReleaseGitError, match="changed before its final read"):
        subject._final_probe_read(tmp_path, expected, payload)


def test_final_read_wraps_open_failure_without_closing_an_invalid_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = tmp_path / "LICENSE"
    probe.write_bytes(b"physical\r\n")
    expected = _identity_for(probe)
    closed: list[int] = []
    monkeypatch.setattr(
        subject.os,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
    )
    monkeypatch.setattr(subject.os, "close", lambda descriptor: closed.append(descriptor))

    with pytest.raises(subject.ReleaseGitError, match="open its final source safely"):
        subject._final_probe_read(tmp_path, expected, b"physical\r\n")

    assert closed == []


@pytest.mark.parametrize("stage", ["before", "during"])
def test_final_read_rejects_descriptor_identity_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    probe = tmp_path / "LICENSE"
    payload = b"physical\r\n"
    probe.write_bytes(payload)
    expected = _identity_for(probe)
    changed = subject._FileIdentity(
        expected.device,
        expected.inode + 1,
        expected.mode,
        expected.attributes,
        expected.links,
    )
    identities = iter((changed,) if stage == "before" else (expected, changed))
    monkeypatch.setattr(subject, "_file_identity", lambda *_args, **_kwargs: next(identities))
    monkeypatch.setattr(
        subject,
        "_real_regular_probe",
        lambda _root: (probe, expected, len(payload)),
    )

    with pytest.raises(subject.ReleaseGitError, match=f"identity {stage} its final read"):
        subject._final_probe_read(tmp_path, expected, payload)


def test_final_read_wraps_descriptor_oserror_and_closes_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = tmp_path / "LICENSE"
    payload = b"physical\r\n"
    probe.write_bytes(payload)
    expected = _identity_for(probe)
    real_open = subject.os.open
    real_close = subject.os.close
    opened: list[int] = []
    closed: list[int] = []

    def tracked_open(*args: Any, **kwargs: Any) -> int:
        descriptor = real_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def tracked_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    monkeypatch.setattr(subject.os, "open", tracked_open)
    monkeypatch.setattr(subject.os, "close", tracked_close)
    monkeypatch.setattr(
        subject,
        "_read_descriptor",
        lambda *_args: (_ for _ in ()).throw(OSError()),
    )

    with pytest.raises(subject.ReleaseGitError, match="read its final source safely"):
        subject._final_probe_read(tmp_path, expected, payload)

    assert opened == closed


@pytest.mark.parametrize("change", ["identity", "size"])
def test_final_read_rejects_post_close_path_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    probe = tmp_path / "LICENSE"
    payload = b"physical\r\n"
    probe.write_bytes(payload)
    expected = _identity_for(probe)
    changed = subject._FileIdentity(
        expected.device,
        expected.inode + 1,
        expected.mode,
        expected.attributes,
        expected.links,
    )
    observations = iter(
        (
            (probe, expected, len(payload)),
            (
                probe,
                changed if change == "identity" else expected,
                len(payload) + (change == "size"),
            ),
        )
    )
    monkeypatch.setattr(subject, "_real_regular_probe", lambda _root: next(observations))

    with pytest.raises(subject.ReleaseGitError, match="changed after its final read"):
        subject._final_probe_read(tmp_path, expected, payload)


def test_final_read_rejects_wrong_same_size_bytes(
    tmp_path: Path,
) -> None:
    probe = tmp_path / "LICENSE"
    observed = b"wrong---\r\n"
    expected_payload = b"right---\r\n"
    assert len(observed) == len(expected_payload)
    probe.write_bytes(observed)

    with pytest.raises(subject.ReleaseGitError, match="not exact physical CRLF"):
        subject._final_probe_read(tmp_path, _identity_for(probe), expected_payload)


def test_receipt_uses_post_git_identity_bound_reread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = "1" * 40
    canonical = b"canonical\n"
    physical = b"canonical\r\n"
    repository = tmp_path.resolve()
    identity = subject._FileIdentity(1, 2, stat.S_IFREG | 0o644, 0, 1)
    first_git = SimpleNamespace(name="first")
    second_git = SimpleNamespace(name="second")
    discovered = iter((first_git, second_git))
    events: list[str] = []

    monkeypatch.setattr(
        subject.ReleaseGit,
        "discover",
        lambda root: (events.append(f"discover:{Path(root).name}"), next(discovered))[1],
    )
    monkeypatch.setattr(
        subject,
        "_require_autocrlf_override",
        lambda git: events.append(f"autocrlf:{git.name}"),
    )
    monkeypatch.setattr(
        subject,
        "_require_reviewed_clean_checkout",
        lambda git, _commit: events.append(f"clean:{git.name}"),
    )
    monkeypatch.setattr(
        subject,
        "_canonical_probe_blob",
        lambda git, _commit: (
            events.append(f"blob:{git.name}"),
            ("a" * 40, canonical),
        )[1],
    )
    monkeypatch.setattr(
        subject,
        "_rewrite_probe",
        lambda *_args: (events.append("rewrite"), identity)[1],
    )
    monkeypatch.setattr(
        subject,
        "_checked_fixed_git_command",
        lambda git, _args: events.append(f"add:{git.name}") or b"",
    )

    def final_read(
        root: Path,
        observed_identity: subject._FileIdentity,
        expected: bytes,
    ) -> bytes:
        assert root == repository
        assert observed_identity == identity
        assert expected == physical
        events.append("final-read")
        return physical

    monkeypatch.setattr(
        subject,
        "_final_probe_read",
        final_read,
    )

    receipt = subject.prepare_autocrlf_checkout(repository, commit)

    assert events == [
        f"discover:{repository.name}",
        "autocrlf:first",
        "clean:first",
        "blob:first",
        "rewrite",
        "add:first",
        f"discover:{repository.name}",
        "clean:second",
        "blob:second",
        "final-read",
    ]
    assert receipt["physical_sha256"] == hashlib.sha256(physical).hexdigest()


def test_prepare_rejects_missing_repository_and_mutating_reviewed_blob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(subject.ReleaseGitError, match="repository is unavailable"):
        subject.prepare_autocrlf_checkout(tmp_path / "missing", "1" * 40)

    git = SimpleNamespace()
    monkeypatch.setattr(
        subject,
        "ReleaseGit",
        SimpleNamespace(discover=lambda _root: git),
    )
    monkeypatch.setattr(subject, "_require_autocrlf_override", lambda _git: None)
    monkeypatch.setattr(
        subject,
        "_require_reviewed_clean_checkout",
        lambda _git, _commit: None,
    )
    blobs = iter((("1" * 40, b"one\n"), ("1" * 40, b"two\n")))
    monkeypatch.setattr(subject, "_canonical_probe_blob", lambda *_args: next(blobs))
    monkeypatch.setattr(subject, "_rewrite_probe", lambda *_args: b"one\r\n")
    monkeypatch.setattr(subject, "_checked_fixed_git_command", lambda *_args: b"")

    with pytest.raises(subject.ReleaseGitError, match="blob changed during preparation"):
        subject.prepare_autocrlf_checkout(tmp_path, "1" * 40)


def test_main_returns_bounded_friendly_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        subject,
        "prepare_autocrlf_checkout",
        lambda *_args: (_ for _ in ()).throw(ValueError("x" * 600)),
    )

    assert subject.main(["--expected-commit", "1" * 40]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Autocrlf checkout proof failed: " + "x" * 512 + "\n"
