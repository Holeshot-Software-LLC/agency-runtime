"""Adversarial archive and committed-release verification tests."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import subprocess
import tarfile
import warnings
import zipfile
from pathlib import Path

import pytest

from scripts import verify_distribution as subject

PACKAGE_PATH = "agency_runtime/__init__.py"
SCRIPT_PATH = "scripts/release.py"
TEST_PATH = "tests/test_release.py"
PYPROJECT_PATH = "pyproject.toml"
LICENSE_PATH = "LICENSE"
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
            b'dependencies = ["pyyaml>=6.0,<7"]\n'
        ),
        LICENSE_PATH: b"test license\n",
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
        "Requires-Python: >=3.10\n"
        "License-Expression: MIT\n"
        f"{classifiers}"
        f"{requirements}"
        f"{extras}"
        "\n"
    ).encode()


def _record_payload(payloads: dict[str, bytes]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name, payload in sorted(payloads.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
        writer.writerow((name, f"sha256={digest}", str(len(payload))))
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    return output.getvalue().encode()


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
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in payloads.items():
            archive.writestr(name, payload)
        if package_directory:
            archive.writestr(f"{PACKAGE_PATH}/", b"")


def _sdist_generated(payloads: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(payloads)
    package_info = _metadata()
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
    result[sources_name] = ("\n".join(sorted(sources)) + "\n").encode()
    return result


def _sdist(
    path: Path,
    payloads: dict[str, bytes],
    *,
    root: str = f"agency_runtime-{VERSION}",
    extra: dict[str, bytes] | None = None,
    typed_members: dict[str, bytes] | None = None,
) -> None:
    artifact_payloads = _sdist_generated(payloads)
    artifact_payloads.update(extra or {})
    for name in typed_members or {}:
        artifact_payloads.pop(name, None)
    with tarfile.open(path, mode="w:gz") as archive:
        for name, payload in artifact_payloads.items():
            member = tarfile.TarInfo(f"{root}/{name}")
            member.size = len(payload)
            member.mtime = 0
            archive.addfile(member, io.BytesIO(payload))
        for name, member_type in (typed_members or {}).items():
            member = tarfile.TarInfo(f"{root}/{name}")
            member.type = member_type
            member.size = 0
            member.mtime = 0
            archive.addfile(member)


def _artifacts(
    root: Path,
    payloads: dict[str, bytes],
    *,
    package_payload: bytes | None = None,
    entry_point: str = "agency_runtime.cli.main:main",
    extra_wheel: dict[str, bytes] | None = None,
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
    )
    _sdist(dist / f"agency_runtime-{VERSION}.tar.gz", artifact_payloads)
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
    with tarfile.open(sdist, mode="w:gz") as archive:
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
        with tarfile.open(path, mode="w:gz") as archive:
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
        f"wheel contains a non-file member: {PACKAGE_PATH}/"
    ]

    _wheel(wheel, payloads[PACKAGE_PATH])
    _sdist(sdist, payloads, typed_members={SCRIPT_PATH: tarfile.DIRTYPE})
    failures = _verify(monkeypatch, dist, repository)
    assert f"sdist missing required files: {SCRIPT_PATH}" in failures

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
    assert "sdist generated SOURCES.txt does not match the exact payload manifest" in _verify(
        monkeypatch, dist, repository
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
    with tarfile.open(sdist, mode="w:gz") as archive:
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
