"""Adversarial archive and committed-release verification tests."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import time
import warnings
import zipfile
import zlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import verify_distribution as subject

PACKAGE_PATH = "agency_runtime/__init__.py"
SCRIPT_PATH = "scripts/release.py"
TEST_PATH = "tests/test_release.py"
PYPROJECT_PATH = "pyproject.toml"
LICENSE_PATH = "LICENSE"
README_PATH = "README.md"
VERSION = "0.1.0"
DIST_INFO = f"agency_runtime-{VERSION}.dist-info"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={root}",
            "-c",
            "core.longpaths=true",
            *args,
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "--verify", "HEAD^{commit}").stdout.strip()


def _repository(root: Path) -> tuple[Path, dict[str, bytes]]:
    repository = root / "repository"
    payloads = {
        PACKAGE_PATH: b'__version__ = "0.1.0"\n',
        SCRIPT_PATH: b'print("release")\n',
        TEST_PATH: b"def test_release():\n    assert True\n",
        PYPROJECT_PATH: (
            b"[build-system]\n"
            b'requires = ["setuptools==83.0.0"]\n'
            b'build-backend = "setuptools.build_meta"\n'
            b"\n[project]\n"
            b'name = "agency-runtime"\n'
            b'dynamic = ["version"]\n'
            b'description = "Release fixture"\n'
            b'readme = "README.md"\n'
            b'requires-python = ">=3.10"\n'
            b'license = "MIT"\n'
            b'license-files = ["LICENSE"]\n'
            b'authors = [{name = "Release Test"}]\n'
            b'keywords = ["release", "test"]\n'
            b"classifiers = [\n"
            b'  "Operating System :: Microsoft :: Windows",\n'
            b'  "Operating System :: POSIX :: Linux",\n'
            b'  "Programming Language :: Python :: 3.10",\n'
            b'  "Programming Language :: Python :: 3.11",\n'
            b'  "Programming Language :: Python :: 3.12",\n'
            b'  "Programming Language :: Python :: 3.13",\n'
            b'  "Programming Language :: Python :: 3.14",\n'
            b"]\n"
            b'dependencies = ["pyyaml>=6.0,<7"]\n'
        ),
        LICENSE_PATH: b"test license\n",
        README_PATH: b"# Fixture\n",
    }
    for name, payload in payloads.items():
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    _git(repository, "init")
    _git(repository, "config", "user.email", "release@example.invalid")
    _git(repository, "config", "user.name", "Release Test")
    _git(repository, "add", "--all")
    _git(repository, "commit", "-m", "release fixture")
    return repository, payloads


def _metadata(
    *,
    version: str = VERSION,
    dependencies: tuple[str, ...] = ("PyYAML<7,>=6.0",),
    extra_headers: tuple[str, ...] = (),
) -> bytes:
    classifiers = "".join(
        f"Classifier: {classifier}\n" for classifier in sorted(subject.REQUIRED_CLASSIFIERS)
    )
    requirements = "".join(f"Requires-Dist: {dependency}\n" for dependency in dependencies)
    extras = "".join(f"{header}\n" for header in extra_headers)
    return (
        "Metadata-Version: 2.4\n"
        "Name: agency-runtime\n"
        f"Version: {version}\n"
        "Summary: Release fixture\n"
        "Author: Release Test\n"
        "Requires-Python: >=3.10\n"
        "License-Expression: MIT\n"
        "Keywords: release,test\n"
        f"{classifiers}"
        "Description-Content-Type: text/markdown\n"
        "License-File: LICENSE\n"
        f"{requirements}"
        "Dynamic: license-file\n"
        f"{extras}"
        "\n"
        "# Fixture\n"
    ).encode()


def _record_payload(payloads: dict[str, bytes]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, payload in sorted(payloads.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
        writer.writerow((name, f"sha256={digest}", str(len(payload))))
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    return output.getvalue().encode()


def _artifact_timestamp(path: Path) -> int:
    repository = path.parent.parent / "repository"
    if (repository / ".git").is_dir():
        return int(_git(repository, "show", "-s", "--format=%ct", "HEAD").stdout.strip())
    return int(time.time())


def _zip_timestamp(timestamp: int) -> tuple[int, int, int, int, int, int]:
    year, month, day, hour, minute, second = time.gmtime(timestamp)[:6]
    return year, month, day, hour, minute, second - second % 2


def _wheel(
    path: Path,
    package_payload: bytes,
    *,
    entry_point: str = "agency_runtime.cli.main:main",
    entry_points_payload: bytes | None = None,
    metadata_payload: bytes | None = None,
    wheel_payload: bytes | None = None,
    license_payload: bytes = b"test license\n",
    extra: dict[str, bytes] | None = None,
    record_payload: bytes | None = None,
    package_directory: bool = False,
) -> None:
    payloads = {
        f"{DIST_INFO}/METADATA": _metadata() if metadata_payload is None else metadata_payload,
        f"{DIST_INFO}/WHEEL": (
            b"Wheel-Version: 1.0\nGenerator: release-test\n"
            b"Root-Is-Purelib: true\nTag: py3-none-any\n"
            if wheel_payload is None
            else wheel_payload
        ),
        f"{DIST_INFO}/entry_points.txt": (
            f"[console_scripts]\nagency = {entry_point}\n".encode()
            if entry_points_payload is None
            else entry_points_payload
        ),
        f"{DIST_INFO}/licenses/LICENSE": license_payload,
        f"{DIST_INFO}/top_level.txt": b"agency_runtime\n",
    }
    if not package_directory:
        payloads[PACKAGE_PATH] = package_payload
    payloads.update(extra or {})
    payloads[f"{DIST_INFO}/RECORD"] = (
        _record_payload(payloads) if record_payload is None else record_payload
    )
    timestamp = _zip_timestamp(_artifact_timestamp(path))
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name, payload in sorted(payloads.items()):
            item = zipfile.ZipInfo(name, timestamp)
            item.create_system = subject.CANONICAL_ZIP_SYSTEM
            item.create_version = subject.CANONICAL_ZIP_VERSION
            item.extract_version = subject.CANONICAL_ZIP_VERSION
            item.compress_type = zipfile.ZIP_STORED
            item.external_attr = (
                subject.CANONICAL_RECORD_MODE
                if name.endswith(".dist-info/RECORD")
                else subject.CANONICAL_WHEEL_MODE
            ) << 16
            archive.writestr(item, payload)
        if package_directory:
            item = zipfile.ZipInfo(f"{PACKAGE_PATH}/", timestamp)
            item.create_system = subject.CANONICAL_ZIP_SYSTEM
            item.create_version = subject.CANONICAL_ZIP_VERSION
            item.extract_version = subject.CANONICAL_ZIP_VERSION
            item.compress_type = zipfile.ZIP_STORED
            item.external_attr = subject.CANONICAL_WHEEL_MODE << 16
            archive.writestr(item, b"")


def _stored_gzip(payload: bytes, *, filename: str, timestamp: int) -> bytes:
    output = bytearray(
        b"\x1f\x8b\x08\x08"
        + struct.pack("<L", timestamp)
        + b"\x00\xff"
        + filename.encode("ascii")
        + b"\0"
    )
    chunks = (
        [payload[offset : offset + 65_535] for offset in range(0, len(payload), 65_535)]
        if payload
        else [b""]
    )
    for index, chunk in enumerate(chunks):
        output.append(1 if index == len(chunks) - 1 else 0)
        output.extend(struct.pack("<HH", len(chunk), ~len(chunk) & 0xFFFF))
        output.extend(chunk)
    output.extend(struct.pack("<LL", zlib.crc32(payload) & 0xFFFFFFFF, len(payload)))
    return bytes(output)


@contextmanager
def _stored_tar_archive(path: Path) -> Iterator[tarfile.TarFile]:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w:") as archive:
        yield archive
    path.write_bytes(
        _stored_gzip(
            payload.getvalue(),
            filename=path.name[:-3],
            timestamp=0,
        )
    )


def _sdist_generated(
    payloads: dict[str, bytes],
    *,
    metadata_payload: bytes | None = None,
) -> dict[str, bytes]:
    result = dict(payloads)
    package_info = _metadata() if metadata_payload is None else metadata_payload
    result.update(
        {
            "PKG-INFO": package_info,
            "agency_runtime.egg-info/PKG-INFO": package_info,
            "agency_runtime.egg-info/dependency_links.txt": b"",
            "agency_runtime.egg-info/entry_points.txt": (
                b"[console_scripts]\nagency = agency_runtime.cli.main:main\n"
            ),
            "agency_runtime.egg-info/requires.txt": b"pyyaml<7,>=6.0\n",
            "agency_runtime.egg-info/top_level.txt": b"agency_runtime\n",
            "setup.cfg": b"[egg_info]\ntag_build =\ntag_date = 0\n",
        }
    )
    sources_name = "agency_runtime.egg-info/SOURCES.txt"
    sources = (set(result) | {sources_name}) - {"PKG-INFO", "setup.cfg"}
    result[sources_name] = "\n".join(
        sorted(
            sources,
            key=lambda name: (
                name.rpartition("/")[0] if "/" in name else "",
                name.rpartition("/")[2],
            ),
        )
    ).encode()
    return result


def _sdist(
    path: Path,
    payloads: dict[str, bytes],
    *,
    root: str = f"agency_runtime-{VERSION}",
    extra: dict[str, bytes] | None = None,
    typed_members: dict[str, bytes] | None = None,
    metadata_payload: bytes | None = None,
) -> None:
    artifact_payloads = _sdist_generated(payloads, metadata_payload=metadata_payload)
    artifact_payloads.update(extra or {})
    for name in typed_members or {}:
        artifact_payloads.pop(name, None)
    timestamp = _artifact_timestamp(path)
    tar_payload = io.BytesIO()
    with tarfile.open(fileobj=tar_payload, mode="w:", format=tarfile.PAX_FORMAT) as archive:
        directories = {
            parent.as_posix()
            for name in {*artifact_payloads, *(typed_members or {})}
            for parent in reversed(Path(name).parents[:-1])
            if parent.as_posix() != "."
        } - set(artifact_payloads)
        members: dict[str, tuple[bytes, bytes | None]] = {
            root: (tarfile.DIRTYPE, None),
            **{f"{root}/{directory}": (tarfile.DIRTYPE, None) for directory in directories},
            **{
                f"{root}/{name}": (tarfile.REGTYPE, payload)
                for name, payload in artifact_payloads.items()
            },
            **{
                f"{root}/{name}": (member_type, None)
                for name, member_type in (typed_members or {}).items()
            },
        }
        for name, (member_type, payload) in sorted(members.items()):
            member = tarfile.TarInfo(f"{name}/" if member_type == tarfile.DIRTYPE else name)
            member.type = member_type
            member.mode = 0o755 if member_type == tarfile.DIRTYPE else 0o644
            member.size = 0 if payload is None else len(payload)
            member.mtime = timestamp
            archive.addfile(member, None if payload is None else io.BytesIO(payload))
    path.write_bytes(
        _stored_gzip(
            tar_payload.getvalue(),
            filename=path.name[:-3],
            timestamp=timestamp,
        )
    )


def _artifacts(
    root: Path,
    payloads: dict[str, bytes],
    *,
    package_payload: bytes | None = None,
    entry_point: str = "agency_runtime.cli.main:main",
    extra_wheel: dict[str, bytes] | None = None,
    metadata_payload: bytes | None = None,
) -> Path:
    dist = root / "dist"
    dist.mkdir()
    selected_package = payloads[PACKAGE_PATH] if package_payload is None else package_payload
    artifact_payloads = dict(payloads)
    artifact_payloads[PACKAGE_PATH] = selected_package
    _wheel(
        dist / f"agency_runtime-{VERSION}-py3-none-any.whl",
        selected_package,
        entry_point=entry_point,
        extra=extra_wheel,
        metadata_payload=metadata_payload,
    )
    _sdist(
        dist / f"agency_runtime-{VERSION}.tar.gz",
        artifact_payloads,
        metadata_payload=metadata_payload,
    )
    return dist


def _verify(
    monkeypatch: pytest.MonkeyPatch,
    dist: Path,
    repository: Path,
    *,
    expected_commit: str | None = None,
) -> list[str]:
    monkeypatch.setattr(subject, "REQUIRED_PACKAGE_FILES", set())
    monkeypatch.setattr(subject, "REQUIRED_SDIST_FILES", set())
    return subject.verify(
        dist,
        repository_root=repository,
        expected_commit=expected_commit or _head(repository),
    )


def test_clean_committed_archives_pass_and_bind_every_scoped_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)

    assert _verify(monkeypatch, dist, repository) == []

    changed = b'__version__ = "9.9.9"\n'
    _wheel(dist / f"agency_runtime-{VERSION}-py3-none-any.whl", changed)
    tampered = dict(payloads)
    tampered[PACKAGE_PATH] = changed
    _sdist(dist / f"agency_runtime-{VERSION}.tar.gz", tampered)
    failures = _verify(monkeypatch, dist, repository)
    assert "wheel payload differs from committed HEAD: agency_runtime/__init__.py" in failures
    assert (
        "sdist package payload differs from committed HEAD: agency_runtime/__init__.py" in failures
    )


@pytest.mark.parametrize(
    "injected_header",
    (
        "X-Unreviewed: shared",
        "Project-URL: Forged, https://example.invalid",
    ),
)
def test_shared_wheel_and_sdist_metadata_injections_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    injected_header: str,
) -> None:
    repository, payloads = _repository(tmp_path)
    metadata_payload = _metadata(extra_headers=(injected_header,))
    dist = _artifacts(
        tmp_path,
        payloads,
        metadata_payload=metadata_payload,
    )

    failures = _verify(monkeypatch, dist, repository)
    for label in (
        "wheel METADATA",
        "sdist PKG-INFO",
        "sdist agency_runtime.egg-info/PKG-INFO",
    ):
        assert any(
            failure.startswith(f"{label} contains unsupported or unexpected core metadata")
            for failure in failures
        )
    assert "wheel METADATA headers differ from sdist PKG-INFO" not in failures
    assert "sdist PKG-INFO copies differ" not in failures


def test_full_artifacts_reject_noncanonical_record_and_sources_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    sdist = dist / f"agency_runtime-{VERSION}.tar.gz"

    with zipfile.ZipFile(wheel) as archive:
        canonical_record = archive.read(f"{DIST_INFO}/RECORD")
    record_lines = canonical_record.splitlines()
    for mutated_record in (
        b"\n".join(reversed(record_lines)) + b"\n",
        canonical_record.replace(b"\n", b"\r\n"),
    ):
        _wheel(
            wheel,
            payloads[PACKAGE_PATH],
            record_payload=mutated_record,
        )
        failures = _verify(monkeypatch, dist, repository)
        assert any("wheel RECORD bytes are noncanonical" in failure for failure in failures)

    _wheel(wheel, payloads[PACKAGE_PATH])
    sources_name = "agency_runtime.egg-info/SOURCES.txt"
    canonical_sources = _sdist_generated(payloads)[sources_name]
    source_lines = canonical_sources.splitlines()
    for mutated_sources in (
        b"\n".join(reversed(source_lines)) + b"\n",
        canonical_sources.replace(b"\n", b"\r\n"),
    ):
        _sdist(
            sdist,
            payloads,
            extra={sources_name: mutated_sources},
        )
        failures = _verify(monkeypatch, dist, repository)
        assert any(
            "SOURCES.txt does not match the exact backend-order LF manifest" in failure
            for failure in failures
        )


@pytest.mark.parametrize("support_path", [SCRIPT_PATH, TEST_PATH])
def test_sdist_release_support_bytes_are_bound_to_committed_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    support_path: str,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    tampered = dict(payloads)
    tampered[support_path] = b"tampered\n"
    _sdist(dist / f"agency_runtime-{VERSION}.tar.gz", tampered)

    assert f"sdist release support payload differs from committed HEAD: {support_path}" in _verify(
        monkeypatch, dist, repository
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"evil_package/payload.py": b"pass\n"},
        {"evil.py": b"pass\n"},
        {f"agency_runtime-{VERSION}.data/scripts/evil": b"payload"},
    ],
)
def test_wheel_rejects_every_unexpected_installable_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra: dict[str, bytes],
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads, extra_wheel=extra)

    failures = _verify(monkeypatch, dist, repository)
    assert any(failure.startswith("wheel contains unexpected payload:") for failure in failures)


def test_wheel_rejects_noncanonical_console_entry_point(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads, entry_point="other.module:main")

    assert "wheel console entry point contract is invalid" in _verify(monkeypatch, dist, repository)


@pytest.mark.parametrize("dirty_kind", ["tracked", "untracked"])
def test_verifier_requires_a_clean_tracked_and_untracked_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dirty_kind: str,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    target = repository / (PACKAGE_PATH if dirty_kind == "tracked" else "untracked.txt")
    target.write_text("dirty\n", encoding="utf-8")

    assert _verify(monkeypatch, dist, repository) == [
        "distribution verification requires a clean Git checkout with no tracked or "
        "untracked changes"
    ]


def test_verifier_fails_clearly_outside_a_git_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()

    failures = _verify(monkeypatch, dist, tmp_path, expected_commit="0" * 40)
    assert len(failures) == 1
    assert failures[0].startswith(
        "distribution verification requires a clean Git checkout at the reviewed HEAD:"
    )


@pytest.mark.parametrize(
    "name",
    [
        "/absolute.py",
        "C:/drive.py",
        "C:drive.py",
        "../traversal.py",
        "agency_runtime/../traversal.py",
        "agency_runtime\\backslash.py",
        "agency_runtime//alias.py",
        "agency_runtime/./alias.py",
    ],
)
def test_archive_member_names_must_be_canonical_and_portable(name: str) -> None:
    with pytest.raises(ValueError, match="unsafe archive member"):
        subject._safe_name(name)


def test_zip_and_tar_reject_duplicate_or_case_aliasing_members(tmp_path: Path) -> None:
    wheel = tmp_path / "duplicate.whl"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(wheel, mode="w") as archive:
            archive.writestr("agency_runtime/x.py", b"first")
            archive.writestr("agency_runtime/x.py", b"second")
    with pytest.raises(ValueError, match="duplicate or aliasing"):
        subject._wheel_payload(wheel)

    sdist = tmp_path / "duplicate.tar.gz"
    with _stored_tar_archive(sdist) as archive:
        for name in ("source/agency_runtime/x.py", "source/AGENCY_RUNTIME/x.py"):
            member = tarfile.TarInfo(name)
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="duplicate or aliasing"):
        subject._sdist_payload(sdist)


@pytest.mark.parametrize(
    "name",
    [
        "README.md.",
        "README.md ",
        "NUL",
        "nul.txt",
        "docs/COM1.md",
        "com¹",
        "CoM².txt",
        "COM³",
        "lpt¹",
        "LpT².md",
        "LPT³",
        "CLOCK$.log",
        "docs/name?.md",
    ],
)
def test_win32_alias_and_device_components_are_not_portable(name: str) -> None:
    with pytest.raises(ValueError, match="unsafe archive member"):
        subject._safe_name(name)


def test_real_sdist_rejects_win32_alias_payloads(tmp_path: Path) -> None:
    for index, name in enumerate(("README.md.", "NUL.txt")):
        path = tmp_path / f"unsafe-{index}.tar.gz"
        with _stored_tar_archive(path) as archive:
            payload = b"unsafe"
            member = tarfile.TarInfo(f"source/{name}")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        with pytest.raises(ValueError, match="unsafe archive member"):
            subject._sdist_payload(path)


def test_directories_and_tar_special_members_cannot_satisfy_required_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    sdist = dist / f"agency_runtime-{VERSION}.tar.gz"

    _wheel(wheel, payloads[PACKAGE_PATH], package_directory=True)
    assert _verify(monkeypatch, dist, repository) == [
        f"wheel contains a directory member: {PACKAGE_PATH}/"
    ]

    _wheel(wheel, payloads[PACKAGE_PATH])
    _sdist(sdist, payloads, typed_members={SCRIPT_PATH: tarfile.DIRTYPE})
    failures = _verify(monkeypatch, dist, repository)
    assert failures == ["sdist directory entries must exactly match file parent directories"]

    for member_type in (tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE):
        _sdist(sdist, payloads, typed_members={"device": member_type})
        assert _verify(monkeypatch, dist, repository) == [
            f"sdist contains an unsupported member type: agency_runtime-{VERSION}/device"
        ]


def test_every_committed_sdist_input_is_byte_bound_and_root_installers_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    sdist = dist / f"agency_runtime-{VERSION}.tar.gz"

    tampered = dict(payloads)
    tampered[PYPROJECT_PATH] = payloads[PYPROJECT_PATH].replace(
        b"setuptools.build_meta",
        b"attacker.build_backend",
    )
    _sdist(sdist, tampered)
    assert "sdist release support payload differs from committed HEAD: pyproject.toml" in _verify(
        monkeypatch, dist, repository
    )

    _sdist(sdist, payloads, extra={"setup.py": b"raise SystemExit('attacker')\n"})
    assert "sdist contains unexpected payload: setup.py" in _verify(
        monkeypatch,
        dist,
        repository,
    )

    _sdist(sdist, payloads, extra={"setup.cfg": b"[build_ext]\ninplace = 1\n"})
    assert "sdist generated setup.cfg contract is invalid" in _verify(
        monkeypatch,
        dist,
        repository,
    )


def test_independent_verifier_rejects_executable_release_inputs(tmp_path: Path) -> None:
    repository, _payloads = _repository(tmp_path)
    _git(repository, "update-index", "--chmod=+x", SCRIPT_PATH)
    _git(repository, "commit", "-m", "mark release input executable")

    with pytest.raises(ValueError, match="non-executable regular file"):
        subject._tracked_release_payloads(repository, _head(repository))


def test_artifact_version_filename_and_sdist_root_are_bound_to_committed_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    sdist = dist / f"agency_runtime-{VERSION}.tar.gz"
    wrong_wheel = dist / "agency_runtime-9.9.9-py3-none-any.whl"
    wrong_sdist = dist / "agency_runtime-9.9.9.tar.gz"
    wheel.rename(wrong_wheel)
    sdist.rename(wrong_sdist)

    assert _verify(monkeypatch, dist, repository) == [
        f"expected exact wheel filename: {wheel.name}",
        f"expected exact sdist filename: {sdist.name}",
    ]

    wrong_wheel.rename(wheel)
    wrong_sdist.rename(sdist)
    _sdist(sdist, payloads, root="agency_runtime-9.9.9")
    assert _verify(monkeypatch, dist, repository) == [
        "sdist has unexpected top-level directory: agency_runtime-9.9.9"
    ]


@pytest.mark.parametrize(
    "dependencies",
    [
        ("PyYAML<7,>=6.0", "attacker-package>=1"),
        ("PyYAML<7,>=6.0", "pyyaml>=6.0,<7"),
        ("PyYAML<8,>=6.0",),
    ],
)
def test_wheel_dependencies_must_exactly_match_committed_pyproject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dependencies: tuple[str, ...],
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    _wheel(
        dist / f"agency_runtime-{VERSION}-py3-none-any.whl",
        payloads[PACKAGE_PATH],
        metadata_payload=_metadata(dependencies=dependencies),
    )

    failures = _verify(monkeypatch, dist, repository)
    assert any("dependency metadata" in failure for failure in failures)


def test_wheel_license_and_singleton_core_headers_are_exact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"

    _wheel(wheel, payloads[PACKAGE_PATH], license_payload=b"attacker license\n")
    assert "wheel license payload differs from committed HEAD" in _verify(
        monkeypatch,
        dist,
        repository,
    )

    for header in ("Name: agency-runtime", f"Version: {VERSION}", "Requires-Python: >=3.10"):
        _wheel(
            wheel,
            payloads[PACKAGE_PATH],
            metadata_payload=_metadata(extra_headers=(header,)),
        )
        failures = _verify(monkeypatch, dist, repository)
        assert any("must contain exactly one" in failure for failure in failures)


def test_detached_reviewed_commit_passes_but_repointed_head_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    reviewed = _head(repository)
    dist = _artifacts(tmp_path, payloads)
    _git(repository, "checkout", "--detach", reviewed)

    assert _verify(monkeypatch, dist, repository, expected_commit=reviewed) == []

    _git(repository, "commit", "--allow-empty", "-m", "repoint")
    failures = _verify(monkeypatch, dist, repository, expected_commit=reviewed)
    assert failures == [
        "distribution verification live HEAD does not match the reviewed commit: "
        f"expected {reviewed}, found {_head(repository)}"
    ]


def test_entry_point_defaults_cannot_inherit_the_required_agency_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    _wheel(
        dist / f"agency_runtime-{VERSION}-py3-none-any.whl",
        payloads[PACKAGE_PATH],
        entry_points_payload=(
            b"[DEFAULT]\nagency = agency_runtime.cli.main:main\n[console_scripts]\n"
        ),
    )

    assert "wheel console entry point contract is invalid" in _verify(
        monkeypatch,
        dist,
        repository,
    )


@pytest.mark.parametrize(
    "wheel_control",
    [
        b"Wheel-Version: 1.1\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        b"Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: py3-none-any\n",
        b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\nX-Tag: py3-none-any\n",
        (
            b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\n"
            b"Tag: py3-none-any\nTag: cp313-cp313-win_amd64\n"
        ),
    ],
)
def test_wheel_control_metadata_requires_one_exact_pure_python_tag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wheel_control: bytes,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    _wheel(
        dist / f"agency_runtime-{VERSION}-py3-none-any.whl",
        payloads[PACKAGE_PATH],
        wheel_payload=wheel_control,
    )

    assert any(
        failure.startswith("wheel control metadata")
        for failure in _verify(monkeypatch, dist, repository)
    )


def test_record_requires_exact_unique_rows_hashes_sizes_and_self_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as archive:
        valid_record = archive.read(f"{DIST_INFO}/RECORD")

    cases = {
        "missing": b"",
        "duplicate": valid_record + b"AGENCY_RUNTIME/__init__.py,sha256=invalid,0\n",
        "extra": valid_record + b"attacker.py,sha256=invalid,0\n",
        "bad hash": valid_record.replace(b"sha256=", b"sha256=invalid", 1),
        "bad self": valid_record.replace(
            f"{DIST_INFO}/RECORD,,\n".encode(),
            f"{DIST_INFO}/RECORD,sha256=invalid,1\n".encode(),
        ),
    }
    expected_fragments = {
        "missing": "wheel RECORD missing members:",
        "duplicate": "wheel RECORD is malformed, duplicated, or noncanonical",
        "extra": "wheel RECORD contains extra members: attacker.py",
        "bad hash": "wheel RECORD hash or size mismatch:",
        "bad self": "wheel RECORD self row must have empty hash and size",
    }
    for label, record in cases.items():
        _wheel(wheel, payloads[PACKAGE_PATH], record_payload=record)
        failures = _verify(monkeypatch, dist, repository)
        assert any(expected_fragments[label] in failure for failure in failures), label


def test_generated_sdist_metadata_is_semantically_validated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    sdist = dist / f"agency_runtime-{VERSION}.tar.gz"

    injected = _metadata(dependencies=("PyYAML<7,>=6.0", "attacker>=1"))
    _sdist(
        sdist,
        payloads,
        extra={
            "PKG-INFO": injected,
            "agency_runtime.egg-info/PKG-INFO": injected,
        },
    )
    assert any(
        "dependency metadata" in failure for failure in _verify(monkeypatch, dist, repository)
    )

    _sdist(
        sdist,
        payloads,
        extra={"agency_runtime.egg-info/SOURCES.txt": b"pyproject.toml\n"},
    )
    assert (
        "sdist generated SOURCES.txt does not match the exact backend-order LF manifest"
        in _verify(monkeypatch, dist, repository)
    )

    _sdist(
        sdist,
        payloads,
        extra={
            "agency_runtime.egg-info/entry_points.txt": (
                b"[DEFAULT]\nagency = agency_runtime.cli.main:main\n[console_scripts]\n"
            )
        },
    )
    assert "sdist console entry point contract is invalid" in _verify(
        monkeypatch,
        dist,
        repository,
    )


def test_archive_resource_limits_fail_before_unbounded_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheel = tmp_path / "bounded.whl"

    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr("one", b"12345")
    monkeypatch.setattr(subject, "MAX_ARCHIVE_MEMBER_BYTES", 4)
    with pytest.raises(ValueError, match="declared size limit"):
        subject._wheel_payload(wheel)

    monkeypatch.setattr(subject, "MAX_ARCHIVE_MEMBER_BYTES", 10)
    monkeypatch.setattr(subject, "MAX_ARCHIVE_TOTAL_BYTES", 5)
    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr("one", b"123")
        archive.writestr("two", b"456")
    with pytest.raises(ValueError, match="total uncompressed size limit"):
        subject._wheel_payload(wheel)

    monkeypatch.setattr(subject, "MAX_ARCHIVE_TOTAL_BYTES", 20)
    monkeypatch.setattr(subject, "MAX_ARCHIVE_MEMBERS", 1)
    with pytest.raises(ValueError, match="member count limit"):
        subject._wheel_payload(wheel)

    sdist = tmp_path / "bounded.tar.gz"
    with _stored_tar_archive(sdist) as archive:
        for name in ("source/one", "source/two"):
            member = tarfile.TarInfo(name)
            member.size = 0
            archive.addfile(member, io.BytesIO())
    with pytest.raises(ValueError, match="member count limit"):
        subject._sdist_payload(sdist)

    monkeypatch.setattr(subject, "MAX_ARCHIVE_MEMBERS", 10)
    monkeypatch.setattr(subject, "MAX_ARCHIVE_MEMBER_BYTES", 2_000)
    monkeypatch.setattr(subject, "MAX_ARCHIVE_TOTAL_BYTES", 2_000)
    monkeypatch.setattr(subject, "MAX_ZIP_COMPRESSION_RATIO", 2)
    with zipfile.ZipFile(wheel, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("compressed", b"0" * 1_000)
    with pytest.raises(ValueError, match="compression ratio limit"):
        subject._wheel_payload(wheel)


def test_final_checkout_reuses_the_original_frozen_git_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    original = subject._reviewed_checkout
    sessions: list[object] = []

    def recording_checkout(
        root: Path,
        expected_commit: str,
        *,
        git: object | None = None,
    ) -> str:
        sessions.append(git)
        return original(root, expected_commit, git=git)

    monkeypatch.setattr(subject, "_reviewed_checkout", recording_checkout)

    assert _verify(monkeypatch, dist, repository) == []
    assert len(sessions) == 2
    assert sessions[0] is sessions[1]
    assert sessions[0] is not None


def test_sdist_parent_directories_are_permitted_but_wheel_directories_are_rejected(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "modes.whl"
    directory = zipfile.ZipInfo("package/")
    directory.create_system = 3
    directory.external_attr = (stat.S_IFDIR | 0o755) << 16
    regular = zipfile.ZipInfo("package/module.py")
    regular.create_system = 3
    regular.external_attr = (stat.S_IFREG | 0o644) << 16
    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr(directory, b"")
        archive.writestr(regular, b"pass\n")

    with pytest.raises(ValueError, match="directory member"):
        subject._wheel_payload(wheel)

    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr(regular, b"pass\n")
    names, payloads = subject._wheel_payload(wheel)
    assert names == {"package/module.py"}
    assert payloads == {"package/module.py": b"pass\n"}

    executable = zipfile.ZipInfo("package/module.py")
    executable.create_system = 3
    executable.external_attr = (stat.S_IFREG | 0o755) << 16
    with zipfile.ZipFile(wheel, mode="w") as archive:
        archive.writestr(executable, b"pass\n")
    with pytest.raises(ValueError, match="executable regular file"):
        subject._wheel_payload(wheel)

    sdist = tmp_path / "modes.tar.gz"
    with _stored_tar_archive(sdist) as archive:
        root = tarfile.TarInfo("source/")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        archive.addfile(root)
        package = tarfile.TarInfo("source/package/")
        package.type = tarfile.DIRTYPE
        package.mode = 0o755
        archive.addfile(package)
        member = tarfile.TarInfo("source/package/module.py")
        member.mode = 0o644
        member.size = 5
        archive.addfile(member, io.BytesIO(b"pass\n"))

    names, payloads = subject._sdist_payload(sdist)
    assert "package/module.py" in names
    assert payloads["package/module.py"] == b"pass\n"

    with _stored_tar_archive(sdist) as archive:
        member = tarfile.TarInfo("source/package/module.py")
        member.mode = 0o755
        member.size = 5
        archive.addfile(member, io.BytesIO(b"pass\n"))
    with pytest.raises(ValueError, match="executable regular file"):
        subject._sdist_payload(sdist)


def test_distribution_boundary_rejects_non_directory_and_unexpected_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    not_directory = tmp_path / "artifact-file"
    not_directory.write_bytes(b"not a directory")
    assert _verify(monkeypatch, not_directory, repository) == [
        "distribution directory must be a real non-link directory"
    ]

    dist = _artifacts(tmp_path, payloads)
    linked_dist = tmp_path / "linked-dist"
    try:
        linked_dist.symlink_to(dist, target_is_directory=True)
    except OSError:
        linked_dist = None
    if linked_dist is not None:
        assert _verify(monkeypatch, linked_dist, repository) == [
            "distribution directory must be a real non-link directory"
        ]

    (dist / "unexpected.txt").write_text("poison", encoding="utf-8")
    assert _verify(monkeypatch, dist, repository) == [
        "distribution directory exceeds its physical entry limit"
    ]


def test_distribution_boundary_rejects_artifact_hardlinks_and_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    hardlink_source = tmp_path / "hardlink-source.whl"
    wheel.replace(hardlink_source)
    os.link(hardlink_source, wheel)

    assert _verify(monkeypatch, dist, repository) == [
        f"distribution artifact must have exactly one hard link: {wheel.name}"
    ]

    wheel.unlink()
    try:
        wheel.symlink_to(hardlink_source)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    assert _verify(monkeypatch, dist, repository) == [
        f"distribution artifact must be a real regular file: {wheel.name}"
    ]


def test_distribution_boundary_enforces_physical_artifact_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    monkeypatch.setattr(subject, "MAX_ARTIFACT_PHYSICAL_BYTES", wheel.stat().st_size - 1)

    assert _verify(monkeypatch, dist, repository) == [
        f"distribution artifact exceeds the physical size limit: {wheel.name}"
    ]


def test_artifact_path_swap_is_blocked_or_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"
    replacement = tmp_path / "replacement.whl"
    shutil.copy2(wheel, replacement)
    original = subject._wheel_payload
    outcome = {"blocked": False, "swapped": False}

    def swap_after_read(
        source: Path | io.BufferedIOBase,
        **kwargs: object,
    ) -> tuple[set[str], dict[str, bytes]]:
        result = original(source, **kwargs)
        try:
            os.replace(replacement, wheel)
        except OSError:
            if os.name != "nt":
                raise
            outcome["blocked"] = True
        else:
            outcome["swapped"] = True
        return result

    monkeypatch.setattr(subject, "_wheel_payload", swap_after_read)
    failures = _verify(monkeypatch, dist, repository)

    if os.name == "nt":
        assert outcome == {"blocked": True, "swapped": False}
        assert failures == []
    else:
        assert outcome == {"blocked": False, "swapped": True}
        assert any(
            "artifact path changed" in failure or "distribution directory changed" in failure
            for failure in failures
        )


def test_distribution_directory_path_swap_is_blocked_or_detected(tmp_path: Path) -> None:
    directory = tmp_path / "dist"
    directory.mkdir()
    moved = tmp_path / "moved-dist"
    blocked = False
    detected = False
    try:
        with subject._bound_distribution_directory(directory):
            try:
                directory.rename(moved)
            except OSError:
                blocked = True
    except ValueError as exc:
        assert "distribution directory changed" in str(exc)
        detected = True

    assert blocked is not detected
    if blocked:
        assert directory.is_dir()
    else:
        assert moved.is_dir()


def test_committed_manifest_has_entry_file_and_aggregate_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, _payloads = _repository(tmp_path)
    commit = _head(repository)

    monkeypatch.setattr(subject, "MAX_RELEASE_ENTRIES", 1)
    with pytest.raises(ValueError, match="entry limit"):
        subject._tracked_release_payloads(repository, commit)

    monkeypatch.setattr(subject, "MAX_RELEASE_ENTRIES", subject.MAX_ARCHIVE_MEMBERS)
    monkeypatch.setattr(subject, "MAX_RELEASE_FILE_BYTES", 1)
    with pytest.raises(ValueError, match="file-size limit"):
        subject._tracked_release_payloads(repository, commit)

    monkeypatch.setattr(subject, "MAX_RELEASE_FILE_BYTES", subject.MAX_ARCHIVE_MEMBER_BYTES)
    monkeypatch.setattr(subject, "MAX_RELEASE_TOTAL_BYTES", 1)
    with pytest.raises(ValueError, match="aggregate byte limit"):
        subject._tracked_release_payloads(repository, commit)


@pytest.mark.parametrize(
    "encoded_size",
    [b"", b"-1", b"+1", b"01", b"1x"],
)
def test_committed_manifest_size_is_canonical(encoded_size: bytes) -> None:
    separator = b" " if encoded_size else b""
    manifest = (
        b"100644 blob " + b"0" * 40 + separator + encoded_size + b"\tagency_runtime/__init__.py\0"
    )
    with pytest.raises(ValueError, match="manifest is malformed"):
        subject._parse_tracked_release_manifest(manifest)


def _fake_stat(
    *,
    mode: int = stat.S_IFREG | 0o644,
    inode: int = 7,
    size: int = 1,
    links: int = 1,
    attributes: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        st_dev=2,
        st_ino=inode,
        st_mode=mode,
        st_size=size,
        st_mtime_ns=3,
        st_ctime_ns=4,
        st_file_attributes=attributes,
        st_nlink=links,
    )


def test_filesystem_identity_rejects_missing_identity_and_detects_stat_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="no stable identity"):
        subject._filesystem_identity(_fake_stat(inode=0))
    expected = subject._filesystem_identity(_fake_stat())
    assert not subject._same_identity(_fake_stat(inode=0), expected)

    def fail_lstat(_path: Path) -> os.stat_result:
        raise OSError("gone")

    monkeypatch.setattr(subject.os, "lstat", fail_lstat)
    with pytest.raises(ValueError, match="must be a real directory"):
        subject._real_directory_identity(tmp_path)
    with pytest.raises(ValueError, match="changed during verification"):
        subject._require_directory_identity(tmp_path, expected)


def test_windows_descriptor_closes_native_handle_when_fd_conversion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ctypes

    closed: list[int] = []

    class NativeCall:
        def __init__(self, result: object, *, capture: list[int] | None = None) -> None:
            self.result = result
            self.capture = capture
            self.argtypes: object = None
            self.restype: object = None

        def __call__(self, *args: object) -> object:
            if self.capture is not None:
                self.capture.append(int(args[0]))
            return self.result

    create = NativeCall(123)
    close = NativeCall(1, capture=closed)
    msvcrt = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "msvcrt", msvcrt)
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: SimpleNamespace(CreateFileW=create, CloseHandle=close),
        raising=False,
    )

    def fail_conversion(_handle: int, _flags: int) -> int:
        raise OSError("conversion failed")

    monkeypatch.setattr(msvcrt, "open_osfhandle", fail_conversion, raising=False)
    with pytest.raises(OSError, match="conversion failed"):
        subject._windows_descriptor(tmp_path, directory=False)
    assert closed == [123]

    create.result = None
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5, raising=False)
    with pytest.raises(OSError, match="could not be opened"):
        subject._windows_descriptor(tmp_path, directory=True)


def test_posix_descriptor_paths_are_constructed_without_link_following(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "artifact"
    open_calls: list[tuple[object, int, int | None]] = []
    stat_calls: list[tuple[object, int | None, bool]] = []

    def recording_open(
        target: object,
        flags: int,
        *,
        dir_fd: int | None = None,
    ) -> int:
        open_calls.append((target, flags, dir_fd))
        return 41

    def recording_stat(
        target: object,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        stat_calls.append((target, dir_fd, follow_symlinks))
        return _fake_stat()  # type: ignore[return-value]

    monkeypatch.setattr(subject.os, "name", "posix")
    monkeypatch.setattr(subject.os, "open", recording_open)
    monkeypatch.setattr(subject.os, "stat", recording_stat)

    assert subject._open_descriptor(path, directory=True) == 41
    assert subject._open_child_descriptor(tmp_path, 17, "artifact") == 41
    assert subject._child_lstat(tmp_path, 17, "artifact").st_ino == 7
    assert open_calls[0][0] == path
    assert open_calls[1] == ("artifact", open_calls[1][1], 17)
    assert stat_calls == [("artifact", 17, False)]


def test_descriptor_helpers_use_bound_windows_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "artifact"
    descriptor_calls: list[tuple[Path, bool]] = []
    lstat_calls: list[Path] = []

    def descriptor(target: Path, *, directory: bool) -> int:
        descriptor_calls.append((target, directory))
        return 41

    def lstat(target: Path) -> os.stat_result:
        lstat_calls.append(target)
        return _fake_stat()  # type: ignore[return-value]

    monkeypatch.setattr(subject.os, "name", "nt")
    monkeypatch.setattr(subject, "_windows_descriptor", descriptor)
    monkeypatch.setattr(subject.os, "lstat", lstat)

    assert subject._open_descriptor(path, directory=True) == 41
    assert subject._open_child_descriptor(tmp_path, 17, "artifact") == 41
    assert subject._child_lstat(tmp_path, 17, "artifact").st_ino == 7
    assert descriptor_calls == [
        (path, True),
        (tmp_path / "artifact", False),
    ]
    assert lstat_calls == [tmp_path / "artifact"]


def test_distribution_directory_fault_injection_covers_open_and_identity_races(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = subject._filesystem_identity(_fake_stat(mode=stat.S_IFDIR | 0o700))
    monkeypatch.setattr(subject, "_real_directory_identity", lambda _path: identity)

    def fail_open(_path: Path, *, directory: bool) -> int:
        assert directory
        raise OSError("blocked")

    monkeypatch.setattr(subject, "_open_descriptor", fail_open)
    with (
        pytest.raises(ValueError, match="could not be opened safely"),
        subject._bound_distribution_directory(tmp_path),
    ):
        pytest.fail("unreachable")

    closed: list[int] = []
    monkeypatch.setattr(subject, "_open_descriptor", lambda _path, *, directory: 73)
    monkeypatch.setattr(subject.os, "fstat", lambda _fd: _fake_stat(inode=99))
    monkeypatch.setattr(subject.os, "close", closed.append)
    with (
        pytest.raises(ValueError, match="changed while it was opened"),
        subject._bound_distribution_directory(tmp_path),
    ):
        pytest.fail("unreachable")
    assert closed == [73]

    results = iter((True, False))
    monkeypatch.setattr(
        subject.os,
        "fstat",
        lambda _fd: _fake_stat(mode=stat.S_IFDIR | 0o700),
    )
    monkeypatch.setattr(subject, "_same_identity", lambda _metadata, _expected: next(results))
    monkeypatch.setattr(subject, "_require_directory_identity", lambda _path, _expected: None)
    with (
        pytest.raises(ValueError, match="changed during verification"),
        subject._bound_distribution_directory(tmp_path),
    ):
        pass


def test_directory_and_artifact_binding_faults_are_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Scan:
        def __enter__(self) -> list[SimpleNamespace]:
            return [SimpleNamespace(name="same"), SimpleNamespace(name="same")]

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(subject.os, "scandir", lambda _target: Scan())
    with pytest.raises(ValueError, match="duplicate child names"):
        subject._directory_names(tmp_path, 1)

    binding = subject._ArtifactBinding(
        "artifact.whl",
        subject._filesystem_identity(_fake_stat()),
    )
    monkeypatch.setattr(subject, "_directory_names", lambda _path, _fd: [])
    with pytest.raises(ValueError, match="contents changed"):
        subject._require_artifact_bindings(tmp_path, 1, (binding, binding))

    monkeypatch.setattr(subject, "_directory_names", lambda _path, _fd: ["artifact.whl"])
    monkeypatch.setattr(subject, "_child_lstat", lambda *_args: _fake_stat(inode=99))
    with pytest.raises(ValueError, match="artifact path changed"):
        subject._require_artifact_bindings(tmp_path, 1, (binding,))


@pytest.mark.parametrize(
    ("same_results", "message"),
    [
        ([False], "changed while it was opened"),
        ([True, False], "artifact path changed"),
        ([True, True, False], "changed while it was read"),
        ([True, True, True, False], "artifact path changed"),
    ],
)
def test_bound_artifact_detects_every_open_read_and_path_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    same_results: list[bool],
    message: str,
) -> None:
    artifact = tmp_path / "artifact.whl"
    artifact.write_bytes(b"x")
    baseline = os.stat(artifact)
    binding = subject._ArtifactBinding(
        artifact.name,
        subject._filesystem_identity(baseline),
    )
    monkeypatch.setattr(
        subject,
        "_open_child_descriptor",
        lambda *_args: os.open(artifact, os.O_RDONLY),
    )
    monkeypatch.setattr(subject, "_child_lstat", lambda *_args: baseline)
    results = iter(same_results)
    monkeypatch.setattr(subject, "_same_identity", lambda *_args: next(results))
    with (
        pytest.raises(ValueError, match=message),
        subject._bound_artifact(tmp_path, 1, binding),
    ):
        pass


def test_bound_artifact_wraps_safe_open_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding = subject._ArtifactBinding(
        "artifact.whl",
        subject._filesystem_identity(_fake_stat()),
    )

    def fail_open(*_args: object) -> int:
        raise OSError("blocked")

    monkeypatch.setattr(subject, "_open_child_descriptor", fail_open)
    with (
        pytest.raises(ValueError, match="could not be opened safely"),
        subject._bound_artifact(tmp_path, 1, binding),
    ):
        pytest.fail("unreachable")


def test_release_source_classification_covers_each_supported_namespace() -> None:
    assert subject._is_sdist_source("docs/guide.md")
    assert not subject._is_sdist_source("docs/guide.txt")
    assert subject._is_sdist_source("examples/fixture.yaml")
    assert subject._is_sdist_source("examples/fixture.yml")
    assert subject._is_sdist_source("examples/fixture.md")
    assert subject._is_sdist_source("examples/fixture.json")
    assert not subject._is_sdist_source("examples/payload.exe")
    assert not subject._is_sdist_source("unscoped.txt")


def test_release_git_and_git_output_wrap_trusted_runner_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_discovery(_root: Path) -> object:
        raise subject.ReleaseGitError("untrusted")

    monkeypatch.setattr(subject.ReleaseGit, "discover", fail_discovery)
    with pytest.raises(ValueError, match="trusted release Git unavailable"):
        subject._release_git(tmp_path)

    class FailingGit:
        def run_bytes(self, *_args: object, **_kwargs: object) -> bytes:
            raise subject.ReleaseGitError("runner failed")

    with pytest.raises(ValueError, match="runner failed"):
        subject._git_output(tmp_path, ["status"], git=FailingGit())  # type: ignore[arg-type]


def test_reviewed_checkout_rejects_noncanonical_commit_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="full lowercase commit"):
        subject._reviewed_checkout(tmp_path, "HEAD")

    monkeypatch.setattr(subject, "_git_output", lambda *_args, **_kwargs: b"f" * 40)
    with pytest.raises(ValueError, match="expected commit is not canonical"):
        subject._reviewed_checkout(tmp_path, "0" * 40)


def test_manifest_parser_handles_unscoped_duplicates_utf8_and_hash_algorithms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ignored = b"100644 blob " + b"1" * 40 + b" 1\tunscoped.txt\0"
    assert subject._parse_tracked_release_manifest(ignored) == ({}, set())

    duplicate = (
        b"100644 blob "
        + b"1" * 40
        + b" 1\tagency_runtime/x.py\0"
        + b"100644 blob "
        + b"2" * 40
        + b" 1\tagency_runtime/x.py\0"
    )
    with pytest.raises(ValueError, match="duplicated"):
        subject._parse_tracked_release_manifest(duplicate)

    malformed_utf8 = b"100644 blob " + b"1" * 40 + b" 1\tagency_runtime/\xff.py\0"
    with pytest.raises(ValueError, match="manifest is malformed"):
        subject._parse_tracked_release_manifest(malformed_utf8)

    mixed = (
        b"100644 blob "
        + b"1" * 40
        + b" 1\tagency_runtime/x.py\0"
        + b"100644 blob "
        + b"2" * 64
        + b" 1\tLICENSE\0"
        + b"100644 blob "
        + b"3" * 40
        + b" 1\tpyproject.toml\0"
    )
    outputs = iter((b"true", mixed))
    monkeypatch.setattr(subject, "_git_output", lambda *_args, **_kwargs: next(outputs))
    with pytest.raises(ValueError, match="mixes object hash algorithms"):
        subject._tracked_release_payloads(Path("ignored"), "0" * 40)

    incomplete_outputs = iter(
        (
            b"true",
            b"100644 blob " + b"1" * 40 + b" 1\tagency_runtime/x.py\0",
        )
    )
    monkeypatch.setattr(
        subject,
        "_git_output",
        lambda *_args, **_kwargs: next(incomplete_outputs),
    )
    with pytest.raises(ValueError, match="manifest is incomplete"):
        subject._tracked_release_payloads(Path("ignored"), "0" * 40)

    monkeypatch.setattr(subject, "_git_output", lambda *_args, **_kwargs: b"false")
    with pytest.raises(ValueError, match="Git worktree checkout"):
        subject._tracked_release_payloads(Path("ignored"), "0" * 40)


def test_committed_blob_and_literal_version_reject_untrusted_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "_git_output", lambda *_args, **_kwargs: b"payload")
    with pytest.raises(ValueError, match="failed independent object verification"):
        subject._committed_blob(tmp_path, "0" * 40)

    for payload in (
        b"\xff",
        b"this is not python",
        b"pass\n",
        b'__version__ = "1.0.0"\n__version__ = "1.0.1"\n',
        b'__version__: str = "1.0.0"\n',
        b'left = right = "1.0.0"\n',
        b'__version__ = "01.0.0"\n',
        b"__version__ = 100\n",
    ):
        with pytest.raises(ValueError, match=r"release version source|canonical literal"):
            subject._literal_release_version(payload, source="fixture.py")

    assert (
        subject._literal_release_version(
            b'"""module"""\nother = 1\n__version__ = "1.2.3rc1"\n',
            source="fixture.py",
        )
        == "1.2.3rc1"
    )


def test_dependency_normalization_covers_urls_markers_extras_and_validation() -> None:
    normalized = subject._normalized_requirement(
        "Example[Foo] @ https://example.invalid/archive.whl ; python_version >= '3.10'",
        extra="Feature_Name",
        additional_marker="sys_platform == 'win32'",
    )
    assert normalized.startswith("example[foo]@https://example.invalid/archive.whl;")
    assert 'extra == "feature-name"' in normalized
    assert "sys_platform" in normalized

    with pytest.raises(ValueError, match="invalid release dependency"):
        subject._normalized_requirement("not a valid requirement !!!")
    with pytest.raises(ValueError, match="invalid release dependency"):
        subject._normalized_requirement("valid>=1", additional_marker="invalid marker !!!")
    with pytest.raises(ValueError, match="must be a list"):
        subject._normalized_dependencies("dependency", source="fixture")
    with pytest.raises(ValueError, match="must be a list"):
        subject._normalized_dependencies([1], source="fixture")
    with pytest.raises(ValueError, match="contain duplicates"):
        subject._normalized_dependencies(["PyYAML>=6", "pyyaml>=6"], source="fixture")


def test_committed_project_contract_validates_optional_dependency_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = {"agency_runtime/__init__.py": "v"}
    support = {"pyproject.toml": "p", "LICENSE": "l", "README.md": "r"}

    def complete_project(payload: bytes) -> bytes:
        return (
            b"[project]\n"
            b'name = "agency-runtime"\n'
            b'dynamic = ["version"]\n'
            b'description = "Fixture"\n'
            b'readme = "README.md"\n'
            b'requires-python = ">=3.10"\n'
            b'license = "MIT"\n'
            b'license-files = ["LICENSE"]\n'
            b'authors = [{name = "Fixture"}]\n'
            b'keywords = ["fixture"]\n'
            b'classifiers = ["Operating System :: POSIX :: Linux"]\n' + payload
        )

    def blobs_for(pyproject: bytes) -> None:
        payloads = iter(
            (
                b'__version__ = "1.0.0"\n',
                pyproject,
                b"license",
                b"# Fixture\n",
            )
        )
        monkeypatch.setattr(subject, "_committed_blob", lambda *_args, **_kwargs: next(payloads))

    blobs_for(complete_project(b'dependencies=[]\noptional-dependencies = "bad"\n'))
    with pytest.raises(ValueError, match="optional dependencies are malformed"):
        subject._committed_project_contract(tmp_path, package, support)

    blobs_for(
        complete_project(
            b'dependencies=["one>=1"]\n[project.optional-dependencies]\nfoo=["two>=2"]\n'
        )
    )
    contract = subject._committed_project_contract(
        tmp_path,
        package,
        support,
    )
    assert contract.version == "1.0.0"
    assert contract.dependencies == ("one>=1", 'two>=2;extra == "foo"')
    assert contract.license_payload == b"license"

    blobs_for(
        complete_project(
            b'dependencies=[]\n[project.optional-dependencies]\nfoo=["one>=1"]\nFoo=["one>=1"]\n'
        )
    )
    with pytest.raises(ValueError, match="dependency metadata contains duplicates"):
        subject._committed_project_contract(tmp_path, package, support)

    blobs_for(b"not toml")
    with pytest.raises(ValueError, match="project metadata is malformed"):
        subject._committed_project_contract(tmp_path, package, support)

    blobs_for(b"project = []\n")
    with pytest.raises(ValueError, match="project metadata is malformed"):
        subject._committed_project_contract(tmp_path, package, support)

    blobs_for(complete_project(b"dependencies=[]\n"))
    with pytest.raises(ValueError, match="project metadata is malformed"):
        subject._committed_project_contract(
            tmp_path,
            package,
            {"pyproject.toml": "p", "LICENSE": "l"},
        )


def test_junk_classification_and_member_reader_faults() -> None:
    assert subject._junk_reason("package/__pycache__/module.py") == "generated directory or file"
    assert subject._junk_reason("package/.env.production") == "environment secret file"
    assert subject._junk_reason("package/runtime.sqlite") == "generated/runtime suffix"
    assert subject._junk_reason("package/runtime.db-wal") == "generated/runtime sidecar"
    assert subject._junk_reason("package/.env.example") is None

    with pytest.raises(ValueError, match="unable to read"):
        subject._read_member(object(), declared_size=0, label="fixture")

    class NonBytes:
        def read(self, _size: int) -> str:
            return "not bytes"

    with pytest.raises(ValueError, match="did not yield bytes"):
        subject._read_member(NonBytes(), declared_size=1, label="fixture")

    with pytest.raises(ValueError, match="exceeds its declared size"):
        subject._read_member(io.BytesIO(b"xx"), declared_size=1, label="fixture")
    with pytest.raises(ValueError, match="shorter than its declared size"):
        subject._read_member(io.BytesIO(b"x"), declared_size=2, label="fixture")
    assert subject._read_member(io.BytesIO(b""), declared_size=0, label="fixture") == b""


def test_zip_preflight_rejects_missing_noncanonical_and_multidisk_records(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.whl"
    missing.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match="missing a canonical ZIP end record"):
        subject._preflight_zip_member_count(missing)

    canonical = tmp_path / "canonical.whl"
    with zipfile.ZipFile(canonical, "w") as archive:
        archive.writestr("file", b"x")
    raw = bytearray(canonical.read_bytes())
    marker = raw.rfind(b"PK\x05\x06")

    noncanonical = tmp_path / "noncanonical.whl"
    bad_comment = bytearray(raw)
    struct.pack_into("<H", bad_comment, marker + 20, 1)
    noncanonical.write_bytes(bad_comment)
    with pytest.raises(ValueError, match="archive comment or trailing data"):
        subject._preflight_zip_member_count(noncanonical)

    multidisk = tmp_path / "multidisk.whl"
    bad_disk = bytearray(raw)
    struct.pack_into("<H", bad_disk, marker + 4, 1)
    multidisk.write_bytes(bad_disk)
    with pytest.raises(ValueError, match="single-disk non-ZIP64"):
        subject._preflight_zip_member_count(multidisk)

    with canonical.open("rb") as stream:
        subject._preflight_zip_member_count(stream)
        assert stream.tell() == 0
