"""Focused archive, metadata, and CLI coverage for the release verifier."""

from __future__ import annotations

import io
import runpy
import stat
import struct
import sys
import tarfile
import zipfile
import zlib
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import verify_distribution as subject
from tests.test_distribution_verifier_hardening import (
    DIST_INFO,
    VERSION,
    _fake_stat,
    _metadata,
    _stored_gzip,
    _stored_tar_archive,
)


def test_directory_identity_rejects_a_replaced_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = subject._filesystem_identity(_fake_stat(mode=stat.S_IFDIR | 0o700))
    monkeypatch.setattr(
        subject.os,
        "lstat",
        lambda _path: _fake_stat(mode=stat.S_IFDIR | 0o700, inode=99),
    )
    with pytest.raises(ValueError, match="changed during verification"):
        subject._require_directory_identity(tmp_path, expected)


def test_directory_scan_stops_at_the_third_physical_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Scan:
        def __init__(self) -> None:
            self.entries = iter(
                SimpleNamespace(name=name)
                for name in ("one.whl", "two.tar.gz", "overflow", "must-not-read")
            )
            self.consumed = 0

        def __enter__(self) -> Scan:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> Scan:
            return self

        def __next__(self) -> SimpleNamespace:
            self.consumed += 1
            return next(self.entries)

    scan = Scan()
    monkeypatch.setattr(subject.os, "scandir", lambda _target: scan)

    with pytest.raises(ValueError, match="physical entry limit"):
        subject._directory_names(tmp_path, 17)
    assert scan.consumed == 3


def test_posix_file_descriptor_path_omits_the_directory_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, int]] = []

    def recording_open(path: object, flags: int) -> int:
        calls.append((path, flags))
        return 9

    monkeypatch.setattr(subject.os, "name", "posix")
    monkeypatch.setattr(subject.os, "open", recording_open)
    assert subject._open_descriptor(tmp_path, directory=False) == 9
    assert calls == [(tmp_path, calls[0][1])]


def test_wheel_rejects_noncanonical_directories_and_nonregular_members(tmp_path: Path) -> None:
    wheel = tmp_path / "invalid.whl"
    directory = zipfile.ZipInfo("package/")
    directory.create_system = 3
    directory.external_attr = (stat.S_IFREG | 0o644) << 16
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(directory, b"")
    with pytest.raises(ValueError, match="directory member"):
        subject._wheel_payload(wheel)

    link = zipfile.ZipInfo("package/link")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o644) << 16
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(link, b"target")
    with pytest.raises(ValueError, match="non-regular member"):
        subject._wheel_payload(wheel)


def _write_single_tar(path: Path, member: tarfile.TarInfo, payload: bytes = b"") -> None:
    with _stored_tar_archive(path) as archive:
        archive.addfile(member, io.BytesIO(payload) if member.size else None)


def test_sdist_rejects_noncanonical_directories_regular_files_and_roots(tmp_path: Path) -> None:
    sdist = tmp_path / "invalid.tar.gz"
    directory = tarfile.TarInfo("source/package")
    directory.type = tarfile.DIRTYPE
    directory.size = 1
    _write_single_tar(sdist, directory, b"x")
    with pytest.raises(ValueError, match="noncanonical directory"):
        subject._sdist_payload(sdist)

    regular = tarfile.TarInfo("source/file/")
    regular.type = tarfile.REGTYPE
    regular.size = 0
    _write_single_tar(sdist, regular)
    with pytest.raises(ValueError, match="noncanonical regular file"):
        subject._sdist_payload(sdist)

    with _stored_tar_archive(sdist) as archive:
        for name in ("one/file", "two/file"):
            member = tarfile.TarInfo(name)
            member.size = 0
            archive.addfile(member, io.BytesIO())
    with pytest.raises(ValueError, match="one top-level directory"):
        subject._sdist_payload(sdist)

    root_file = tarfile.TarInfo("source")
    root_file.size = 0
    _write_single_tar(sdist, root_file)
    with pytest.raises(ValueError, match="explicit top-level directory"):
        subject._sdist_payload(sdist)


def test_sdist_reports_an_unreadable_validated_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tarfile.TarInfo("source/")
    root.type = tarfile.DIRTYPE
    member = tarfile.TarInfo("source/file")
    member.size = 0

    class Archive:
        def __init__(self) -> None:
            self.pax_headers: dict[str, str] = {}

        def __enter__(self) -> Archive:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> Iterator[tarfile.TarInfo]:
            return iter((root, member))

        def extractfile(self, _member: tarfile.TarInfo) -> None:
            return None

    monkeypatch.setattr(
        subject,
        "_bounded_gzip_payload",
        lambda _source, **_kwargs: b"\0" * 10_240,
    )
    monkeypatch.setattr(subject.tarfile, "open", lambda **_kwargs: Archive())
    with pytest.raises(ValueError, match="unable to read sdist member"):
        subject._sdist_payload(io.BytesIO())


def test_metadata_and_scoped_payload_helpers_report_absent_and_unexpected_files() -> None:
    with pytest.raises(ValueError, match="one METADATA file"):
        subject._metadata({})
    assert subject._unexpected_scoped_payload_failures(
        "sdist",
        {"scripts/release.py", "outside.txt"},
        set(),
        prefixes=("scripts/",),
    ) == ["sdist contains unexpected source payload: scripts/release.py"]
    assert (
        subject._unexpected_scoped_payload_failures(
            "sdist",
            {"outside.txt"},
            set(),
            prefixes=("scripts/",),
        )
        == []
    )
    assert subject._junk_failures("wheel", {"package/.env.production"}) == [
        "wheel contains generated junk: package/.env.production (environment secret file)"
    ]
    assert subject._junk_failures("wheel", {"package/module.py"}) == []


def test_artifact_identity_failures_cover_each_independent_exact_filename() -> None:
    expected_wheel = Path(f"agency_runtime-{VERSION}-py3-none-any.whl")
    expected_sdist = Path(f"agency_runtime-{VERSION}.tar.gz")

    assert subject._artifact_identity_failures(
        [expected_wheel],
        [Path("wrong.tar.gz")],
        version=VERSION,
    ) == [f"expected exact sdist filename: {expected_sdist.name}"]
    assert subject._artifact_identity_failures(
        [Path("wrong.whl")],
        [expected_sdist],
        version=VERSION,
    ) == [f"expected exact wheel filename: {expected_wheel.name}"]


def test_console_top_level_and_project_metadata_failure_branches() -> None:
    assert subject._console_scripts_payload_failures(b"\xff", label="wheel") == [
        "wheel console entry point contract is invalid"
    ]
    assert subject._console_script_failures(DIST_INFO, {}) == []
    assert subject._top_level_package_failures(DIST_INFO, {}) == []
    assert subject._top_level_package_failures(
        DIST_INFO,
        {f"{DIST_INFO}/top_level.txt": b"\xff"},
    ) == ["wheel top-level package contract is invalid"]

    class Metadata:
        defects = ("malformed",)

        def get_all(self, name: str, default: list[str]) -> list[str]:
            values = {
                "Metadata-Version": ["1.0"],
                "Name": ["agency-runtime"],
                "Version": [VERSION],
                "Requires-Python": [">=3.10"],
                "License-Expression": ["MIT"],
                "Requires-Dist": [],
                "Classifier": [],
            }
            return values.get(name, default)

    failures = subject._project_metadata_failures(
        Metadata(),  # type: ignore[arg-type]
        label="fixture",
        expected_version=VERSION,
        expected_dependencies=(),
        expected_core_metadata=((), ""),
        require_classifiers=True,
    )
    assert "fixture contains malformed email metadata" in failures
    assert "fixture has unexpected Metadata-Version: '1.0'" in failures
    assert any(failure.startswith("missing classifiers:") for failure in failures)
    assert not any(
        failure.startswith("missing classifiers:")
        for failure in subject._project_metadata_failures(
            Metadata(),  # type: ignore[arg-type]
            label="fixture",
            expected_version=VERSION,
            expected_dependencies=(),
            expected_core_metadata=((), ""),
            require_classifiers=False,
        )
    )


def test_wheel_control_and_record_helpers_cover_absent_and_malformed_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert subject._wheel_control_failures(DIST_INFO, {}) == []
    with monkeypatch.context() as patch:
        parser = SimpleNamespace(parsebytes=lambda _payload: (_ for _ in ()).throw(TypeError()))
        patch.setattr(subject, "BytesParser", lambda **_kwargs: parser)
        assert subject._wheel_control_failures(
            DIST_INFO,
            {f"{DIST_INFO}/WHEEL": b"payload"},
        ) == ["wheel control metadata is invalid"]

    duplicate_generator = (
        b"Wheel-Version: 1.0\n"
        b"Generator: one\n"
        b"Generator: two\n"
        b"Root-Is-Purelib: true\n"
        b"Tag: py3-none-any\n\nbody\n"
    )
    failures = subject._wheel_control_failures(
        DIST_INFO,
        {f"{DIST_INFO}/WHEEL": duplicate_generator},
    )
    assert "wheel control metadata has duplicate generator headers" in failures
    assert "wheel control metadata contains an unexpected body" in failures

    assert subject._record_failures(DIST_INFO, {}) == []
    assert subject._record_failures(
        DIST_INFO,
        {f"{DIST_INFO}/RECORD": b"only,two\n"},
    ) == ["wheel RECORD is malformed, duplicated, or noncanonical"]


def test_generated_metadata_parsers_reject_malformed_payloads() -> None:
    assert subject._setup_cfg_failures(b"\xff") == ["sdist generated setup.cfg contract is invalid"]
    assert subject._sources_manifest_failures(b"", {}) == [
        "sdist generated SOURCES.txt is malformed or duplicated"
    ]
    assert subject._sources_manifest_failures(b"\xff", {}) == [
        "sdist generated SOURCES.txt is malformed or duplicated"
    ]
    assert (
        subject._sources_manifest_failures(
            b"agency_runtime.egg-info/SOURCES.txt",
            {"agency_runtime.egg-info/SOURCES.txt": b"placeholder"},
        )
        == []
    )
    assert subject._sources_manifest_failures(
        b"agency_runtime.egg-info/SOURCES.txt\n",
        {"agency_runtime.egg-info/SOURCES.txt": b"placeholder"},
    ) == ["sdist generated SOURCES.txt does not match the exact sorted LF payload manifest"]
    assert subject._generated_lf_failures("generated", b"line\r\n") == [
        "generated must use canonical LF line endings"
    ]
    assert subject._generated_lf_failures("generated", b"line\n") == []
    with pytest.raises(ValueError, match="not UTF-8"):
        subject._requires_txt_dependencies(b"\xff")
    with pytest.raises(ValueError, match="invalid extra section"):
        subject._requires_txt_dependencies(b"[!]\npackage>=1\n")
    with pytest.raises(ValueError, match="contain duplicates"):
        subject._requires_txt_dependencies(b"package>=1\n\npackage>=1\n")
    assert subject._requires_txt_dependencies(
        b"[feature]\npackage>=1\n[other:sys_platform == 'win32']\nother-package>=2\n"
    ) == (
        'other-package>=2;sys_platform == "win32" and extra == "other"',
        'package>=1;extra == "feature"',
    )


def test_sdist_generated_metadata_aggregates_every_optional_contract() -> None:
    expected_core_metadata = subject._canonical_project_metadata_projection(
        BytesParser(policy=policy.default).parsebytes(_metadata())
    )
    missing = subject._sdist_generated_metadata_failures(
        {},
        expected_version=VERSION,
        expected_dependencies=(),
        expected_core_metadata=expected_core_metadata,
    )
    assert any(failure.startswith("sdist missing generated metadata files:") for failure in missing)

    payloads: dict[str, bytes] = {
        "PKG-INFO": _metadata(),
        "agency_runtime.egg-info/PKG-INFO": _metadata() + b"X-Other: value\n",
        "agency_runtime.egg-info/dependency_links.txt": b"https://example.invalid\n",
        "agency_runtime.egg-info/entry_points.txt": b"\xff",
        "agency_runtime.egg-info/requires.txt": b"\xff",
        "agency_runtime.egg-info/top_level.txt": b"\xff",
        "agency_runtime.egg-info/SOURCES.txt": b"",
        "setup.cfg": b"\xff",
    }
    failures = subject._sdist_generated_metadata_failures(
        payloads,
        expected_version=VERSION,
        expected_dependencies=("required>=1",),
        expected_core_metadata=expected_core_metadata,
    )
    assert "sdist PKG-INFO copies differ" in failures
    assert "sdist generated top_level.txt contract is invalid" in failures
    assert "sdist generated requires.txt is invalid or duplicated" in failures
    assert "sdist generated requires.txt does not match committed pyproject" in failures
    assert "sdist generated dependency_links.txt must be empty" in failures
    assert "sdist generated setup.cfg contract is invalid" in failures
    assert "sdist generated SOURCES.txt is malformed or duplicated" in failures


def test_metadata_contract_reports_path_and_missing_dist_info_members() -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(_metadata())
    expected_core_metadata = subject._canonical_project_metadata_projection(metadata)
    failures = subject._metadata_failures(
        "wrong.dist-info/METADATA",
        metadata,
        {"wrong.dist-info/METADATA"},
        {"wrong.dist-info/METADATA": _metadata()},
        expected_version=VERSION,
        expected_dependencies=("pyyaml<7,>=6.0",),
        expected_license=b"license",
        expected_core_metadata=expected_core_metadata,
    )
    assert "unexpected wheel metadata path: wrong.dist-info/METADATA" in failures
    assert any(failure.startswith("wheel missing metadata file:") for failure in failures)


def _stub_verification_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    metadata_failure: bool = False,
    final_checkout_failure: bool = False,
) -> None:
    git = object()
    monkeypatch.setattr(subject, "_release_git", lambda _root: git)
    checkout_calls = 0

    def checkout(_root: Path, expected: str, *, git: object) -> str:
        nonlocal checkout_calls
        checkout_calls += 1
        if final_checkout_failure and checkout_calls == 2:
            raise ValueError("final checkout changed")
        return expected

    monkeypatch.setattr(subject, "_reviewed_checkout", checkout)
    monkeypatch.setattr(
        subject,
        "_reviewed_commit_timestamp",
        lambda *_args, **_kwargs: 0,
    )
    monkeypatch.setattr(
        subject,
        "_tracked_release_payloads",
        lambda *_args, **_kwargs: (
            {"agency_runtime/__init__.py": "0" * 40},
            {"LICENSE": "1" * 40, "pyproject.toml": "2" * 40},
            "sha1",
        ),
    )
    monkeypatch.setattr(
        subject,
        "_committed_project_contract",
        lambda *_args, **_kwargs: subject._CommittedProjectContract(
            version=VERSION,
            dependencies=(),
            license_payload=b"license",
            core_metadata=subject._canonical_project_metadata_projection(
                BytesParser(policy=policy.default).parsebytes(_metadata(dependencies=()))
            ),
        ),
    )

    @contextmanager
    def artifacts(*_args: object, **_kwargs: object) -> Iterator[tuple[io.BytesIO, io.BytesIO]]:
        yield io.BytesIO(), io.BytesIO()

    monkeypatch.setattr(subject, "_bound_distribution_artifacts", artifacts)
    metadata_name = f"{DIST_INFO}/METADATA"
    monkeypatch.setattr(
        subject,
        "_wheel_payload",
        lambda _stream, **_kwargs: ({metadata_name}, {metadata_name: _metadata(dependencies=())}),
    )
    monkeypatch.setattr(subject, "_sdist_payload", lambda *_args, **_kwargs: (set(), {}))
    if metadata_failure:
        monkeypatch.setattr(
            subject,
            "_metadata",
            lambda _payloads: (_ for _ in ()).throw(ValueError("metadata rejected")),
        )


def test_verify_requires_correlation_and_reports_metadata_and_final_checkout_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert subject.verify(tmp_path) == [
        "distribution verification requires an expected reviewed commit"
    ]

    _stub_verification_pipeline(monkeypatch, metadata_failure=True)
    assert subject.verify(tmp_path, expected_commit="0" * 40) == ["metadata rejected"]

    monkeypatch.undo()
    _stub_verification_pipeline(monkeypatch, final_checkout_failure=True)
    failures = subject.verify(tmp_path, expected_commit="0" * 40)
    assert "final checkout changed" in failures


def test_main_reports_success_and_each_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(subject, "verify", lambda *_args, **_kwargs: [])
    assert subject.main([str(tmp_path), "--expected-commit", "0" * 40]) == 0
    assert "Distribution verification passed" in capsys.readouterr().out

    monkeypatch.setattr(subject, "verify", lambda *_args, **_kwargs: ["one", "two"])
    assert subject.main([str(tmp_path), "--expected-commit", "0" * 40]) == 1
    assert "- one\n- two" in capsys.readouterr().err


def test_script_entrypoint_exits_with_main_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(subject.__file__),
            str(tmp_path),
            "--expected-commit",
            "0" * 40,
        ],
    )
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(subject.__file__), run_name="__main__")
    assert raised.value.code == 1


def _canonical_gzip(payload: bytes, *, filename: str = "fixture.tar") -> bytes:
    return _stored_gzip(payload, filename=filename, timestamp=0)


def _pax_record(key: str, value: str) -> bytes:
    body = f" {key}={value}\n".encode()
    length = len(body) + 1
    while len(str(length)) + len(body) != length:
        length = len(str(length)) + len(body)
    return f"{length}".encode() + body


def _tar_record(
    *,
    name: str = "source/file",
    member_type: bytes = tarfile.REGTYPE,
    payload: bytes = b"",
) -> bytes:
    item = tarfile.TarInfo(name)
    item.type = member_type
    item.mode = 0o644
    item.size = len(payload)
    header = item.tobuf(format=tarfile.PAX_FORMAT)
    padding = b"\0" * ((512 - len(payload) % 512) % 512)
    return header + payload + padding


def _tar_container(*records: bytes) -> bytes:
    content = b"".join(records) + (b"\0" * 1_024)
    return content + (b"\0" * ((10_240 - len(content) % 10_240) % 10_240))


def test_zip_physical_and_internal_fault_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheel = tmp_path / "bounded.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("file", b"payload")
    monkeypatch.setattr(subject, "MAX_ARTIFACT_PHYSICAL_BYTES", wheel.stat().st_size - 1)
    with pytest.raises(ValueError, match="physical size limit"):
        subject._preflight_zip_member_count(wheel)

    item = SimpleNamespace(filename="member", header_offset=0)
    with pytest.raises(ValueError, match="archive was closed"):
        subject._zip_local_data_end(SimpleNamespace(fp=None), item)
    with pytest.raises(ValueError, match="local header is invalid"):
        subject._zip_local_data_end(SimpleNamespace(fp=io.BytesIO(b"invalid")), item)

    header = struct.pack(
        "<I5H3L2H",
        0x04034B50,
        20,
        0x800,
        zipfile.ZIP_STORED,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
    )
    with pytest.raises(ValueError, match="local filename is invalid"):
        subject._zip_local_data_end(
            SimpleNamespace(fp=io.BytesIO(header + b"\xff")),
            item,
        )


def test_wheel_parser_rechecks_archive_and_central_directory_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "ignored.whl"
    source.write_bytes(b"ignored")
    monkeypatch.setattr(subject, "_preflight_zip_member_count", lambda _source: (1, 0, 0))

    class Archive:
        def __init__(self, *, comment: bytes, start_dir: int) -> None:
            self.comment = comment
            self.start_dir = start_dir

        def __enter__(self) -> Archive:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def infolist(self) -> list[zipfile.ZipInfo]:
            return []

    monkeypatch.setattr(
        subject.zipfile, "ZipFile", lambda _source: Archive(comment=b"x", start_dir=0)
    )
    with pytest.raises(ValueError, match="archive comment"):
        subject._wheel_payload(source)

    monkeypatch.setattr(
        subject.zipfile, "ZipFile", lambda _source: Archive(comment=b"", start_dir=1)
    )
    with pytest.raises(ValueError, match="central directory layout"):
        subject._wheel_payload(source)


def test_bounded_gzip_accepts_seek_fallback_and_rejects_unbounded_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _canonical_gzip(b"\0" * 10_240)
    assert (
        subject._bounded_gzip_payload(
            io.BytesIO(payload),
            expected_filename="fixture.tar",
        )
        == b"\0" * 10_240
    )

    class Unbounded:
        def fileno(self) -> int:
            raise OSError("no descriptor")

        def tell(self) -> int:
            raise OSError("not seekable")

    with pytest.raises(ValueError, match="bounded seekable stream"):
        subject._bounded_gzip_payload(Unbounded())  # type: ignore[arg-type]

    monkeypatch.setattr(subject, "MAX_ARTIFACT_PHYSICAL_BYTES", len(payload) - 1)
    with pytest.raises(ValueError, match="physical size limit"):
        subject._bounded_gzip_payload(io.BytesIO(payload))
    archive = tmp_path / "fixture.tar.gz"
    archive.write_bytes(payload)
    with pytest.raises(ValueError, match="physical size limit"):
        subject._bounded_gzip_payload(archive)


def test_bounded_gzip_normalizes_stream_decompress_and_limit_faults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _canonical_gzip(b"\0" * 10_240)

    class NonBytes(io.BytesIO):
        def read(self, _size: int = -1) -> str:
            return "not bytes"

    with pytest.raises(ValueError, match="did not yield bytes"):
        subject._bounded_gzip_payload(NonBytes(payload))

    class SizedChunks:
        def __init__(self, chunks: list[bytes]) -> None:
            self.stream = io.BytesIO(b"".join(chunks))

        def fileno(self) -> int:
            return 17

        def seek(self, *_args: object) -> int:
            return self.stream.seek(*_args)

        def read(self, size: int) -> bytes:
            return self.stream.read(size)

    monkeypatch.setattr(subject.os, "fstat", lambda _fd: SimpleNamespace(st_size=1))
    with pytest.raises(ValueError, match=r"physical size limit|requested boundary"):
        subject._bounded_gzip_payload(SizedChunks([payload]))  # type: ignore[arg-type]

    monkeypatch.setattr(
        subject.os,
        "fstat",
        lambda _fd: SimpleNamespace(st_size=len(payload) + 1),
    )
    with pytest.raises(ValueError, match="trailing data"):
        subject._bounded_gzip_payload(
            SizedChunks([payload, b"x"]),  # type: ignore[arg-type]
            expected_filename="fixture.tar",
        )

    split = len(payload) // 2
    monkeypatch.setattr(
        subject.os,
        "fstat",
        lambda _fd: SimpleNamespace(st_size=len(payload)),
    )
    assert (
        subject._bounded_gzip_payload(
            SizedChunks([payload[:split], payload[split:]]),  # type: ignore[arg-type]
            expected_filename="fixture.tar",
        )
        == b"\0" * 10_240
    )

    invalid = bytearray(payload)
    compressed_offset = invalid.find(b"\0", 10) + 1
    invalid[compressed_offset] ^= 0xFF
    with pytest.raises(ValueError, match=r"block header|block length|trailer"):
        subject._bounded_gzip_payload(
            io.BytesIO(bytes(invalid)),
            expected_filename="fixture.tar",
        )

    with pytest.raises(
        ValueError,
        match=r"truncated|block exceeds|trailing data|decompressed tar exceeds",
    ):
        subject._bounded_gzip_payload(
            io.BytesIO(payload[:-8]),
            expected_filename="fixture.tar",
        )

    monkeypatch.setattr(subject, "MAX_TAR_CONTAINER_BYTES", 1)
    with pytest.raises(ValueError, match="decompressed tar exceeds"):
        subject._bounded_gzip_payload(
            io.BytesIO(payload),
            expected_filename="fixture.tar",
        )


def test_bounded_gzip_block_length_and_overflow_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compressed = _canonical_gzip(b"")
    invalid_length = bytearray(compressed)
    block = invalid_length.find(b"\0", 10) + 1
    invalid_length[block + 3] ^= 1
    with pytest.raises(ValueError, match="block length is invalid"):
        subject._bounded_gzip_payload(io.BytesIO(invalid_length))

    nonempty = _canonical_gzip(b"xx")
    monkeypatch.setattr(subject, "MAX_TAR_CONTAINER_BYTES", 1)
    with pytest.raises(ValueError, match="decompressed tar exceeds"):
        subject._bounded_gzip_payload(
            io.BytesIO(nonempty),
            expected_filename="fixture.tar",
        )


@pytest.mark.parametrize(
    ("header", "message"),
    [
        (b"", "header is noncanonical"),
        (b"\x1f\x8b\x08\x08\0\0\0\0\x02\xfffixture.tar\0", "compression header"),
        (b"\x1f\x8b\x08\x08\0\0\0\0\0\xff" + b"x" * 256, "filename is missing"),
        (b"\x1f\x8b\x08\x08\0\0\0\0\0\xff\xff\0", "portable ASCII"),
        (b"\x1f\x8b\x08\x08\0\0\0\0\0\xff\0", "filename is noncanonical"),
        (b"\x1f\x8b\x08\x08\0\0\0\0\0\xffdir/file.tar\0", "filename is noncanonical"),
        (b"\x1f\x8b\x08\x08\0\0\0\0\0\xfffixture\0", "filename is noncanonical"),
    ],
)
def test_gzip_header_contract_rejects_noncanonical_fields(
    header: bytes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        subject._validate_gzip_header(header, source=io.BytesIO())


def test_gzip_header_derives_a_pathlike_stream_name() -> None:
    header = b"\x1f\x8b\x08\x08\0\0\0\0\0\xfffixture.tar\0"
    subject._validate_gzip_header(
        header,
        source=SimpleNamespace(name=Path("fixture.tar.gz")),  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"invalid", "length is malformed"),
        (b"05 path=x\n", "length is noncanonical"),
        (b"99 path=x\n", "exceeds its header boundary"),
        (b"7 path\n", "record is malformed"),
        (b"6 \xff=x\n", "record text is invalid"),
        (_pax_record("comment", "x"), "key is unsupported"),
        (_pax_record("path", "one") + _pax_record("path", "two"), "key is duplicated"),
    ],
)
def test_pax_record_parser_rejects_malformed_unknown_and_duplicate_records(
    payload: bytes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        subject._parse_pax_records(payload)


def test_pax_record_parser_accepts_the_canonical_allowlist() -> None:
    assert subject._parse_pax_records(
        _pax_record("mtime", "1.25") + _pax_record("path", "source/file"),
    ) == {"mtime": "1.25", "path": "source/file"}


def test_tar_preflight_rejects_end_pax_and_boundary_faults() -> None:
    with pytest.raises(ValueError, match="container length"):
        subject._preflight_tar_layout(b"")
    with pytest.raises(ValueError, match="two zero blocks"):
        subject._preflight_tar_layout((b"\0" * 512) + b"x" + (b"\0" * 9_727))

    pax = _pax_record("path", "source/file")
    pax_record = _tar_record(name="PaxHeaders/file", member_type=tarfile.XHDTYPE, payload=pax)
    with pytest.raises(ValueError, match="orphan PAX"):
        subject._preflight_tar_layout(_tar_container(pax_record))
    with pytest.raises(ValueError, match="chained PAX"):
        subject._preflight_tar_layout(_tar_container(pax_record, pax_record))

    oversized = tarfile.TarInfo("source/file")
    oversized.size = 20_000
    with pytest.raises(ValueError, match="container boundary"):
        subject._preflight_tar_layout(
            oversized.tobuf(format=tarfile.PAX_FORMAT) + (b"x" * (10_240 - 512))
        )

    headers = b"".join(_tar_record(name=f"source/{index}") for index in range(20))
    with pytest.raises(ValueError, match="missing its canonical end marker"):
        subject._preflight_tar_layout(headers)


def test_tar_member_budget_rejects_member_4097_before_tarfile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _tar_container(*(_tar_record(name=f"source/{index:04d}") for index in range(4_097)))
    monkeypatch.setattr(subject, "_bounded_gzip_payload", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(
        subject.tarfile,
        "open",
        lambda **_kwargs: pytest.fail("oversized member roster reached tarfile"),
    )

    with pytest.raises(ValueError, match="archive member count limit"):
        subject._sdist_payload(io.BytesIO())


def test_tar_size_and_high_level_pax_validation_faults() -> None:
    with pytest.raises(ValueError, match="noncanonical size"):
        subject._tar_member_size(b"\0" * 512)

    item = tarfile.TarInfo("source/file")
    item.pax_headers = {"comment": "x"}
    with pytest.raises(ValueError, match="unsupported PAX headers"):
        subject._validate_pax_headers(item)
    item.pax_headers = {"path": "other"}
    with pytest.raises(ValueError, match="noncanonical PAX path"):
        subject._validate_pax_headers(item)
    item.pax_headers = {"mtime": "01.0"}
    with pytest.raises(ValueError, match="noncanonical PAX mtime"):
        subject._validate_pax_headers(item)


def test_sdist_parser_rejects_high_level_global_pax_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Archive:
        def __init__(self) -> None:
            self.pax_headers = {"comment": "x"}

        def __enter__(self) -> Archive:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(
        subject,
        "_bounded_gzip_payload",
        lambda *_args, **_kwargs: b"\0" * 10_240,
    )
    monkeypatch.setattr(subject.tarfile, "open", lambda **_kwargs: Archive())
    with pytest.raises(ValueError, match="global PAX"):
        subject._sdist_payload(io.BytesIO())


def test_zip_preflight_rejects_a_central_directory_offset_mismatch(tmp_path: Path) -> None:
    wheel = tmp_path / "offset.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("member", b"")
    raw = bytearray(wheel.read_bytes())
    marker = raw.rfind(b"PK\x05\x06")
    assert marker >= 0
    offset = struct.unpack_from("<L", raw, marker + 16)[0]
    struct.pack_into("<L", raw, marker + 16, offset + 1)
    wheel.write_bytes(raw)

    with pytest.raises(ValueError, match="central directory layout is noncanonical"):
        subject._preflight_zip_member_count(wheel)


def test_zip_local_header_rejects_a_central_record_mismatch() -> None:
    item = _wheel_item()
    header = struct.pack(
        "<I5H3L2H",
        0x04034B50,
        item.extract_version + 1,
        item.flag_bits,
        item.compress_type,
        0,
        33,
        item.CRC,
        item.compress_size,
        item.file_size,
        len(item.filename),
        0,
    )
    archive = SimpleNamespace(fp=io.BytesIO(header + item.filename.encode("cp437")))

    with pytest.raises(ValueError, match="local header differs from its central record"):
        subject._zip_local_data_end(archive, item)


def test_archive_file_prefix_collisions_are_rejected() -> None:
    with pytest.raises(ValueError, match="file-prefix collision"):
        subject._require_no_file_prefix_collisions(
            {"source/file", "source/file/child"},
            artifact="fixture",
        )


class _WheelArchive:
    def __init__(self, item: zipfile.ZipInfo, *, start_dir: int) -> None:
        self.comment = b""
        self.start_dir = start_dir
        self._item = item

    def __enter__(self) -> _WheelArchive:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def infolist(self) -> list[zipfile.ZipInfo]:
        return [self._item]

    def open(self, _item: zipfile.ZipInfo, *, mode: str) -> io.BytesIO:
        assert mode == "r"
        return io.BytesIO()


def _wheel_item() -> zipfile.ZipInfo:
    item = zipfile.ZipInfo("member")
    item.header_offset = 0
    item.CRC = 0
    item.compress_size = 0
    item.file_size = 0
    return item


def _exercise_wheel_item(
    monkeypatch: pytest.MonkeyPatch,
    item: zipfile.ZipInfo,
    *,
    start_dir: int = 1,
    local_end: int = 1,
) -> tuple[set[str], dict[str, bytes]]:
    monkeypatch.setattr(
        subject,
        "_preflight_zip_member_count",
        lambda _source: (1, start_dir, 1),
    )
    monkeypatch.setattr(
        subject.zipfile,
        "ZipFile",
        lambda _source: _WheelArchive(item, start_dir=start_dir),
    )
    monkeypatch.setattr(subject, "_validate_zip_central_records", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(subject, "_zip_local_data_end", lambda _archive, _item: local_end)
    return subject._wheel_payload(io.BytesIO())


@pytest.mark.parametrize(
    ("attribute", "value", "message"),
    [
        ("header_offset", 1, "prefix, gap, or unreferenced local record"),
        ("comment", b"x", "comment or extra field"),
        ("extra", b"\x99\x99\x00\x00", "comment or extra field"),
        ("flag_bits", 1, "encrypted member"),
        ("flag_bits", 2, "unsupported ZIP flags"),
        ("compress_type", 99, "unsupported compression method"),
    ],
)
def test_wheel_parser_rejects_each_refactored_member_boundary(
    monkeypatch: pytest.MonkeyPatch,
    attribute: str,
    value: object,
    message: str,
) -> None:
    item = _wheel_item()
    setattr(item, attribute, value)

    with pytest.raises(ValueError, match=message):
        _exercise_wheel_item(monkeypatch, item)


def test_wheel_parser_rejects_a_final_local_directory_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _wheel_item()
    with pytest.raises(ValueError, match="gap or unreferenced local record"):
        _exercise_wheel_item(monkeypatch, item, start_dir=2, local_end=1)


def test_wheel_parser_normalizes_runtime_decompression_faults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_preflight_zip_member_count",
        lambda _source: (1, 0, 0),
    )

    def fail_zipfile(_source: object) -> zipfile.ZipFile:
        raise RuntimeError("decompressor failed")

    monkeypatch.setattr(subject.zipfile, "ZipFile", fail_zipfile)
    with pytest.raises(ValueError, match="unsupported or invalid compressed data"):
        subject._wheel_payload(io.BytesIO())


def test_single_gzip_decompressor_rejects_unused_trailing_data() -> None:
    first = _canonical_gzip(b"", filename="fixture.tar")
    second = _canonical_gzip(b"", filename="fixture.tar")
    payload = first + second

    with pytest.raises(ValueError, match="trailing data or multiple gzip members"):
        subject._decompress_single_gzip(
            io.BytesIO(payload),
            source=io.BytesIO(payload),
            physical_size=len(payload),
            expected_filename="fixture.tar",
        )


def test_gzip_header_rejects_an_expected_filename_mismatch() -> None:
    with pytest.raises(ValueError, match="filename does not match"):
        subject._validate_gzip_header(
            _canonical_gzip(b"", filename="fixture.tar"),
            source=io.BytesIO(),
            expected_filename="other.tar",
        )


def test_tar_preflight_rejects_nonzero_tail_and_excess_padding() -> None:
    canonical = _tar_container(_tar_record())
    nonzero_tail = bytearray(canonical)
    nonzero_tail[-1] = 1
    with pytest.raises(ValueError, match="nonzero trailing data"):
        subject._preflight_tar_layout(bytes(nonzero_tail))

    with pytest.raises(ValueError, match="excess zero padding"):
        subject._preflight_tar_layout(canonical + (b"\0" * 10_240))


@pytest.mark.parametrize(
    ("member_type", "payload", "message"),
    [
        (tarfile.GNUTYPE_LONGNAME, b"member\0", "unsupported extended header"),
        (
            tarfile.XHDTYPE,
            b"x" * (subject.MAX_PAX_HEADER_BYTES + 1),
            "PAX header exceeds its size limit",
        ),
    ],
    ids=("gnu-longname", "oversized-pax"),
)
def test_tar_preflight_rejects_refactored_extended_header_boundaries(
    member_type: bytes,
    payload: bytes,
    message: str,
) -> None:
    container = _tar_container(
        _tar_record(
            name="PaxHeaders/member",
            member_type=member_type,
            payload=payload,
        )
    )
    with pytest.raises(ValueError, match=message):
        subject._preflight_tar_layout(container)


def test_high_level_pax_validation_accepts_a_matching_path_before_mtime() -> None:
    item = tarfile.TarInfo("source/file")
    item.pax_headers = {"path": "source/file", "mtime": "1.0"}

    subject._validate_pax_headers(item)


def test_stored_wheel_member_requires_exact_compressed_size() -> None:
    item = _wheel_item()
    item.compress_type = zipfile.ZIP_STORED
    item.compress_size = 2
    item.file_size = 1
    header = struct.pack(
        "<I5H3L2H",
        0x04034B50,
        item.extract_version,
        item.flag_bits,
        item.compress_type,
        0,
        33,
        item.CRC,
        item.compress_size,
        item.file_size,
        len(item.filename),
        0,
    )
    archive = SimpleNamespace(fp=io.BytesIO(header + item.filename.encode("cp437") + b"xx"))

    with pytest.raises(ValueError, match="stored member has a noncanonical size"):
        subject._zip_local_data_end(archive, item)


def test_wheel_member_budget_fails_before_deflate_inflation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _wheel_item()
    item.compress_type = zipfile.ZIP_DEFLATED
    item.compress_size = 1
    item.file_size = subject.MAX_ARCHIVE_MEMBER_BYTES + 1
    monkeypatch.setattr(
        subject.zlib,
        "decompressobj",
        lambda *_args: pytest.fail("oversized member reached the inflater"),
    )
    monkeypatch.setattr(
        subject,
        "_preflight_zip_member_count",
        lambda _source: (1, 1, 1),
    )
    monkeypatch.setattr(
        subject.zipfile,
        "ZipFile",
        lambda _source: _WheelArchive(item, start_dir=1),
    )
    monkeypatch.setattr(subject, "_validate_zip_central_records", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        subject,
        "_zip_local_data_end",
        lambda *_args: pytest.fail("oversized member reached its local compressed stream"),
    )

    with pytest.raises(ValueError, match="declared size limit"):
        subject._wheel_payload(io.BytesIO())


@pytest.mark.parametrize(
    ("compressed_size", "file_size", "message"),
    [
        (1, subject.MAX_ARCHIVE_MEMBER_BYTES + 1, "declared size limit"),
        (subject.MAX_ARTIFACT_PHYSICAL_BYTES + 1, 0, "physical size limit"),
        (1, subject.MAX_ZIP_COMPRESSION_RATIO + 1, "compression ratio limit"),
    ],
)
def test_deflate_stream_rejects_unsafe_budgets_before_creating_an_inflater(
    monkeypatch: pytest.MonkeyPatch,
    compressed_size: int,
    file_size: int,
    message: str,
) -> None:
    monkeypatch.setattr(
        subject.zlib,
        "decompressobj",
        lambda *_args: pytest.fail("unsafe budget reached the inflater"),
    )

    with pytest.raises(ValueError, match=message):
        subject._require_exact_deflate_stream(
            io.BytesIO(),
            compressed_size=compressed_size,
            file_size=file_size,
            label="member",
        )


def test_tar_preflight_rejects_nonzero_member_alignment_padding() -> None:
    record = bytearray(_tar_record(payload=b"x"))
    record[513] = 1

    with pytest.raises(ValueError, match="padding must contain only zero bytes"):
        subject._preflight_tar_layout(_tar_container(bytes(record)))


def _parsed_core_metadata(payload: bytes) -> Message:
    return BytesParser(policy=policy.default).parsebytes(payload)


def test_core_metadata_parity_ignores_only_presentation_differences() -> None:
    wheel = _parsed_core_metadata(
        b"Metadata-Version: 2.4\n"
        b"Summary: folded\n"
        b" value\n"
        b"Classifier: Beta\n"
        b"Classifier: Alpha\n"
        b"\n"
        b"same body\r\n"
    )
    sdist = {
        "PKG-INFO": (
            b"Classifier: Alpha\n"
            b"Metadata-Version: 2.4\n"
            b"Classifier: Beta\n"
            b"Summary: folded value\n"
            b"\n"
            b"same body\n"
        )
    }

    assert subject._metadata_parity_failures(wheel, sdist) == []
    assert subject._metadata_parity_failures(wheel, {}) == []


def test_core_metadata_projection_decodes_the_raw_utf8_body_without_replacement() -> None:
    metadata = _parsed_core_metadata(
        b"Metadata-Version: 2.4\r\n\r\nproduction-ready \xe2\x80\x94 without replacement\r\n"
    )

    _headers, body = subject._canonical_project_metadata_projection(metadata)

    assert body == "production-ready \u2014 without replacement\n"

    invalid = _parsed_core_metadata(b"Metadata-Version: 2.4\n\n\xff\n")
    with pytest.raises(ValueError, match="body is not UTF-8"):
        subject._canonical_project_metadata_projection(invalid)


def test_core_metadata_parity_rejects_header_and_body_differences() -> None:
    wheel = _parsed_core_metadata(b"Metadata-Version: 2.4\nSummary: reviewed\n\nreviewed body\n")
    failures = subject._metadata_parity_failures(
        wheel,
        {"PKG-INFO": (b"Metadata-Version: 2.4\nSummary: substituted\n\nsubstituted body\n")},
    )

    assert failures == [
        "wheel METADATA headers differ from sdist PKG-INFO",
        "wheel METADATA body differs from sdist PKG-INFO",
    ]


def test_core_metadata_parity_rejects_a_non_text_body() -> None:
    wheel = Message()
    wheel.set_payload([Message()])

    assert subject._metadata_parity_failures(wheel, {"PKG-INFO": _metadata()}) == [
        "wheel METADATA and sdist PKG-INFO cannot be compared safely"
    ]


def _raw_deflate(payload: bytes) -> bytes:
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    return compressor.compress(payload) + compressor.flush()


def test_exact_deflate_stream_accepts_one_complete_raw_member() -> None:
    payload = b"reviewed payload"
    compressed = _raw_deflate(payload)

    subject._require_exact_deflate_stream(
        io.BytesIO(compressed),
        compressed_size=len(compressed),
        file_size=len(payload),
        label="member",
    )


def test_deflated_local_wheel_member_runs_the_exact_stream_validator() -> None:
    payload = b"reviewed payload"
    compressed = _raw_deflate(payload)
    item = _wheel_item()
    item.compress_type = zipfile.ZIP_DEFLATED
    item.compress_size = len(compressed)
    item.file_size = len(payload)
    item.CRC = zlib.crc32(payload)
    name = item.filename.encode("ascii")
    header = struct.pack(
        "<I5H3L2H",
        0x04034B50,
        item.extract_version,
        item.flag_bits,
        item.compress_type,
        0,
        33,
        item.CRC,
        item.compress_size,
        item.file_size,
        len(name),
        0,
    )
    archive = SimpleNamespace(fp=io.BytesIO(header + name + compressed))

    assert subject._zip_local_data_end(archive, item) == len(header + name + compressed)


def test_wheel_container_rejects_noncanonical_compression_and_ratio() -> None:
    item = _wheel_item()
    item.compress_type = zipfile.ZIP_DEFLATED
    with pytest.raises(ValueError, match="compression method is noncanonical"):
        subject._validate_wheel_member_container(
            item,
            name=item.filename,
            canonical_timestamp=item.date_time,
        )

    item.compress_size = 1
    item.file_size = subject.MAX_ZIP_COMPRESSION_RATIO + 1
    with pytest.raises(ValueError, match="compression ratio limit"):
        subject._validate_wheel_member_container(
            item,
            name=item.filename,
            canonical_timestamp=None,
        )


def test_wheel_payload_rejects_noncanonical_member_order(tmp_path: Path) -> None:
    wheel = tmp_path / "unsorted.whl"
    with zipfile.ZipFile(wheel, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("b", b"")
        archive.writestr("a", b"")

    with pytest.raises(ValueError, match="not in canonical sorted order"):
        subject._wheel_payload(wheel)


@pytest.mark.parametrize(
    "stream",
    [
        SimpleNamespace(read=lambda _size: "not bytes"),
        io.BytesIO(),
    ],
    ids=("non-bytes", "truncated"),
)
def test_exact_deflate_stream_rejects_invalid_source_reads(stream: object) -> None:
    with pytest.raises(ValueError, match="unsupported or invalid compressed data"):
        subject._require_exact_deflate_stream(
            stream,  # type: ignore[arg-type]
            compressed_size=1,
            file_size=0,
            label="member",
        )


def test_exact_deflate_stream_rejects_declared_size_and_trailing_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compressed = _raw_deflate(b"ab")
    with pytest.raises(ValueError, match="exceeds its declared size"):
        subject._require_exact_deflate_stream(
            io.BytesIO(compressed),
            compressed_size=len(compressed),
            file_size=1,
            label="member",
        )

    trailing = compressed + b"x"
    with pytest.raises(ValueError, match="trailing compressed data"):
        subject._require_exact_deflate_stream(
            io.BytesIO(trailing),
            compressed_size=len(trailing),
            file_size=2,
            label="member",
        )

    monkeypatch.setattr(subject, "READ_CHUNK_BYTES", len(compressed))
    with pytest.raises(ValueError, match="trailing compressed data"):
        subject._require_exact_deflate_stream(
            io.BytesIO(trailing),
            compressed_size=len(trailing),
            file_size=2,
            label="member",
        )


def test_exact_deflate_stream_rejects_stalled_invalid_and_incomplete_inflaters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StalledInflater:
        eof = False
        unused_data = b""
        unconsumed_tail = b"x"

        def decompress(self, payload: bytes, _maximum: int) -> bytes:
            self.unconsumed_tail = payload
            return b""

        def flush(self, _maximum: int) -> bytes:
            return b""

    monkeypatch.setattr(subject.zlib, "decompressobj", lambda *_args: StalledInflater())
    with pytest.raises(ValueError, match="unsupported or invalid compressed data"):
        subject._require_exact_deflate_stream(
            io.BytesIO(b"x"),
            compressed_size=1,
            file_size=0,
            label="member",
        )

    monkeypatch.undo()
    with pytest.raises(ValueError, match="unsupported or invalid compressed data"):
        subject._require_exact_deflate_stream(
            io.BytesIO(b"\xff"),
            compressed_size=1,
            file_size=0,
            label="member",
        )

    compressed = _raw_deflate(b"payload")
    with pytest.raises(ValueError, match="unsupported or invalid compressed data"):
        subject._require_exact_deflate_stream(
            io.BytesIO(compressed[:-1]),
            compressed_size=len(compressed) - 1,
            file_size=7,
            label="member",
        )


@pytest.mark.parametrize(
    ("unused_data", "unconsumed_tail", "flushed"),
    [
        (b"x", b"", b""),
        (b"", b"x", b""),
        (b"", b"", b"x"),
    ],
    ids=("unused-data", "unconsumed-tail", "wrong-size"),
)
def test_exact_deflate_stream_rechecks_final_inflater_state(
    monkeypatch: pytest.MonkeyPatch,
    unused_data: bytes,
    unconsumed_tail: bytes,
    flushed: bytes,
) -> None:
    class FinalInflater:
        eof = True

        def __init__(self) -> None:
            self.unused_data = unused_data
            self.unconsumed_tail = unconsumed_tail

        def decompress(self, _payload: bytes, _maximum: int) -> bytes:
            return b""

        def flush(self, _maximum: int) -> bytes:
            return flushed

    monkeypatch.setattr(subject.zlib, "decompressobj", lambda *_args: FinalInflater())
    with pytest.raises(ValueError, match="unsupported or invalid compressed data"):
        subject._require_exact_deflate_stream(
            io.BytesIO(),
            compressed_size=0,
            file_size=0,
            label="member",
        )


class _OversizedRead:
    def read(self, _size: int) -> bytes:
        return b"xx"


class _NonByteRead:
    def read(self, _size: int) -> str:
        return "not bytes"


def test_bounded_gzip_reader_rejects_each_exact_read_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="did not yield bytes"):
        subject._BoundedGzipReader(_NonByteRead(), 1).read_exact(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="stream is truncated"):
        subject._BoundedGzipReader(io.BytesIO(), 1).read_exact(1)
    with pytest.raises(ValueError, match="requested boundary"):
        subject._BoundedGzipReader(_OversizedRead(), 2).read_exact(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="physical size limit"):
        subject._BoundedGzipReader(io.BytesIO(b"x"), 0).read_exact(1)

    reader = subject._BoundedGzipReader(
        io.BytesIO(b"x"),
        subject.MAX_ARTIFACT_PHYSICAL_BYTES + 1,
        observed=subject.MAX_ARTIFACT_PHYSICAL_BYTES,
    )
    with pytest.raises(ValueError, match="physical size limit"):
        reader.read_exact(1)


def test_bounded_gzip_reader_rejects_each_eof_fault() -> None:
    with pytest.raises(ValueError, match="did not yield bytes"):
        subject._BoundedGzipReader(_NonByteRead(), 0).require_eof()  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="shorter than its physical size"):
        subject._BoundedGzipReader(io.BytesIO(b"x"), 0).require_eof()
    with pytest.raises(ValueError, match="shorter than its physical size"):
        subject._BoundedGzipReader(io.BytesIO(), 1).require_eof()


def test_stored_gzip_header_reader_exhausts_its_bounded_filename_scan() -> None:
    payload = b"\x1f\x8b\x08\x08\0\0\0\0\0\xff" + (b"x" * (subject.MAX_ARCHIVE_COMPONENT_BYTES + 1))
    reader = subject._BoundedGzipReader(io.BytesIO(payload), len(payload))

    assert subject._read_stored_gzip_header(reader) == payload


def test_stored_gzip_header_rejects_a_mismatched_reviewed_timestamp() -> None:
    header = b"\x1f\x8b\x08\x08\0\0\0\0\0\xfffixture.tar\0"

    with pytest.raises(ValueError, match="timestamp does not match"):
        subject._validate_gzip_header(
            header,
            source=io.BytesIO(),
            expected_mtime=1,
        )


def _gzip_block(*, marker: int, payload: bytes) -> bytes:
    size = len(payload)
    return bytes([marker]) + struct.pack("<HH", size, ~size & 0xFFFF) + payload


def _stored_gzip_from_blocks(
    *blocks: bytes,
    payload: bytes,
    trailer: bytes | None = None,
) -> bytes:
    header = b"\x1f\x8b\x08\x08\0\0\0\0\0\xfffixture.tar\0"
    canonical_trailer = struct.pack("<LL", zlib.crc32(payload), len(payload))
    return header + b"".join(blocks) + (canonical_trailer if trailer is None else trailer)


def test_stored_gzip_reader_accepts_canonical_multiblock_segmentation() -> None:
    payload = b"a" * 65_536
    compressed = _stored_gzip_from_blocks(
        _gzip_block(marker=0, payload=payload[:65_535]),
        _gzip_block(marker=1, payload=payload[65_535:]),
        payload=payload,
    )

    assert (
        subject._decompress_single_gzip(
            io.BytesIO(compressed),
            source=io.BytesIO(compressed),
            physical_size=len(compressed),
            expected_filename="fixture.tar",
        )
        == payload
    )


@pytest.mark.parametrize(
    ("compressed", "message"),
    [
        (
            _stored_gzip_from_blocks(
                _gzip_block(marker=2, payload=b""),
                payload=b"",
            ),
            "block header is noncanonical",
        ),
        (
            _stored_gzip_from_blocks(
                b"\x01\xff\xff\0\0",
                payload=b"",
            ),
            "block exceeds its boundary",
        ),
        (
            _stored_gzip_from_blocks(
                _gzip_block(marker=0, payload=b"x"),
                payload=b"x",
            ),
            "segmentation is noncanonical",
        ),
        (
            _stored_gzip_from_blocks(
                _gzip_block(marker=0, payload=b"x" * 65_535),
                _gzip_block(marker=1, payload=b""),
                payload=b"x" * 65_535,
            ),
            "segmentation is noncanonical",
        ),
        (
            _stored_gzip_from_blocks(
                _gzip_block(marker=0, payload=b"x" * 65_535),
                payload=b"x" * 65_535,
            ),
            "trailing data or multiple gzip members",
        ),
        (
            _stored_gzip_from_blocks(
                _gzip_block(marker=1, payload=b""),
                b"x",
                payload=b"",
            ),
            "trailing data or multiple gzip members",
        ),
        (
            _stored_gzip_from_blocks(
                _gzip_block(marker=1, payload=b""),
                payload=b"",
                trailer=b"\x01" + (b"\0" * 7),
            ),
            "trailer is invalid",
        ),
    ],
    ids=(
        "unknown-marker",
        "block-overflow",
        "short-nonfinal",
        "empty-final-after-data",
        "missing-final",
        "data-after-final",
        "bad-trailer",
    ),
)
def test_stored_gzip_reader_rejects_noncanonical_blocks(
    compressed: bytes,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        subject._decompress_single_gzip(
            io.BytesIO(compressed),
            source=io.BytesIO(compressed),
            physical_size=len(compressed),
            expected_filename="fixture.tar",
        )


def test_stored_gzip_payload_rejects_a_missing_block() -> None:
    reader = subject._BoundedGzipReader(io.BytesIO(b"\0" * 8), 8)

    with pytest.raises(ValueError, match="trailing data or multiple gzip members"):
        subject._read_stored_gzip_payload(reader, maximum_payload=0)


def _canonical_tar_header(
    *,
    name: str,
    member_type: bytes,
    mode: int,
    size: int = 0,
    mtime: int = 0,
) -> bytes:
    header = bytearray(512)
    encoded_name = name.encode("ascii")
    header[: len(encoded_name)] = encoded_name
    header[100:108] = f"{mode:07o}\0".encode("ascii")
    header[108:116] = b"0000000\0"
    header[116:124] = b"0000000\0"
    header[124:136] = f"{size:011o}\0".encode("ascii")
    header[136:148] = f"{mtime:011o}\0".encode("ascii")
    header[148:156] = b"        "
    header[156:157] = member_type
    header[257:263] = b"ustar\0"
    header[263:265] = b"00"
    return _with_tar_checksum(header)


def _with_tar_checksum(header: bytearray | bytes) -> bytes:
    updated = bytearray(header)
    updated[148:156] = b"        "
    updated[148:156] = f"{sum(updated):06o}\0 ".encode("ascii")
    return bytes(updated)


def test_exact_tar_field_parsers_cover_canonical_and_fault_boundaries() -> None:
    assert subject._tar_canonical_octal(b"0000644\0", label="mode") == 0o644
    with pytest.raises(ValueError, match="noncanonical mode"):
        subject._tar_canonical_octal(b"0000644 ", label="mode")

    assert subject._tar_nul_padded(b"name\0\0", label="name", allow_empty=False) == b"name"
    for field in (b"namexx", b"name\0x", b"\0\0"):
        with pytest.raises(ValueError, match="noncanonical name"):
            subject._tar_nul_padded(field, label="name", allow_empty=False)


def test_exact_tar_name_parser_handles_full_width_and_pax_placeholders() -> None:
    full_width = b"x" * 100
    assert subject._tar_header_name(full_width, pax_path=None) == full_width
    with pytest.raises(ValueError, match="portable ASCII"):
        subject._tar_header_name(b"\xff" + (b"\0" * 99), pax_path=None)
    with pytest.raises(ValueError, match="noncanonical PAX base name"):
        subject._tar_header_name(b"x" + (b"\0" * 99), pax_path="different")

    pax_path = "source/" + ("x" * 100)
    expected = pax_path.encode("ascii")[:100]
    assert subject._tar_header_name(expected, pax_path=pax_path) == expected


def test_exact_tar_header_rejects_checksum_and_type_specific_faults() -> None:
    regular = _canonical_tar_header(
        name="source/file",
        member_type=tarfile.REGTYPE,
        mode=0o644,
    )
    directory = _canonical_tar_header(
        name="source/",
        member_type=tarfile.DIRTYPE,
        mode=0o755,
    )
    pax = _canonical_tar_header(
        name="././@PaxHeader",
        member_type=tarfile.XHDTYPE,
        mode=0,
    )
    assert subject._validate_canonical_tar_header(regular, expected_mtime=0) == (
        0,
        tarfile.REGTYPE,
    )
    assert subject._validate_canonical_tar_header(directory, expected_mtime=0) == (
        0,
        tarfile.DIRTYPE,
    )
    assert subject._validate_canonical_tar_header(pax, expected_mtime=0) == (
        0,
        tarfile.XHDTYPE,
    )

    misspelled_checksum = bytearray(regular)
    misspelled_checksum[154] = ord(" ")
    with pytest.raises(ValueError, match="checksum spelling"):
        subject._validate_canonical_tar_header(bytes(misspelled_checksum), expected_mtime=0)

    invalid_checksum = bytearray(regular)
    invalid_checksum[148:156] = b"000000\0 "
    with pytest.raises(ValueError, match="checksum is invalid"):
        subject._validate_canonical_tar_header(bytes(invalid_checksum), expected_mtime=0)

    bad_pax = bytearray(pax)
    bad_pax[100:108] = b"0000644\0"
    with pytest.raises(ValueError, match="PAX tar header is noncanonical"):
        subject._validate_canonical_tar_header(_with_tar_checksum(bad_pax), expected_mtime=0)

    bad_regular = bytearray(regular)
    bad_regular[100:108] = b"0000600\0"
    with pytest.raises(ValueError, match="regular-file tar header is noncanonical"):
        subject._validate_canonical_tar_header(
            _with_tar_checksum(bad_regular),
            expected_mtime=0,
        )

    bad_directory = bytearray(directory)
    bad_directory[100:108] = b"0000644\0"
    with pytest.raises(ValueError, match="directory tar header is noncanonical"):
        subject._validate_canonical_tar_header(
            _with_tar_checksum(bad_directory),
            expected_mtime=0,
        )


def test_canonical_pax_payload_requires_only_a_necessary_path() -> None:
    for records in ({}, {"path": "short"}, {"path": "x" * 101, "mtime": "0"}):
        with pytest.raises(ValueError, match="PAX payload is noncanonical"):
            subject._require_canonical_pax_payload(records)

    subject._require_canonical_pax_payload({"path": "x" * 101})
    subject._require_canonical_pax_payload({"path": "source/na\u00efve"})


def _canonical_tar_info(
    name: str,
    *,
    member_type: bytes = tarfile.REGTYPE,
    mtime: int = 0,
) -> tarfile.TarInfo:
    item = tarfile.TarInfo(name)
    item.type = member_type
    item.mode = 0o755 if member_type == tarfile.DIRTYPE else 0o644
    item.size = 0
    item.uid = 0
    item.gid = 0
    item.uname = ""
    item.gname = ""
    item.devmajor = 0
    item.devminor = 0
    item.mtime = mtime
    return item


class _TarRoster:
    def __init__(self, *items: tarfile.TarInfo) -> None:
        self.pax_headers: dict[str, str] = {}
        self.items = items

    def __iter__(self) -> Iterator[tarfile.TarInfo]:
        return iter(self.items)


def test_high_level_pax_and_tar_member_canonical_faults() -> None:
    item = _canonical_tar_info("source/file")
    item.pax_headers = {"mtime": "0"}
    with pytest.raises(ValueError, match="noncanonical PAX headers"):
        subject._validate_pax_headers(item, expected_mtime=0)

    item.pax_headers = {"path": "source/file/"}
    with pytest.raises(ValueError, match="noncanonical PAX path"):
        subject._validate_pax_headers(item)

    unsupported = _canonical_tar_info("source/link", member_type=tarfile.SYMTYPE)
    with pytest.raises(ValueError, match="unsupported member type"):
        subject._validated_tar_members(_TarRoster(unsupported))  # type: ignore[arg-type]

    wrong_timestamp = _canonical_tar_info("source/file", mtime=1)
    with pytest.raises(ValueError, match="member header is noncanonical"):
        subject._validated_tar_members(  # type: ignore[arg-type]
            _TarRoster(wrong_timestamp),
            expected_mtime=0,
        )

    unsorted = _TarRoster(
        _canonical_tar_info("source/b"),
        _canonical_tar_info("source/a"),
    )
    with pytest.raises(ValueError, match="not in canonical sorted order"):
        subject._validated_tar_members(unsorted, expected_mtime=0)  # type: ignore[arg-type]


def _valid_reviewed_project() -> dict[str, object]:
    return {
        "name": "agency-runtime",
        "dynamic": ["version"],
        "description": "Fixture",
        "readme": "README.md",
        "requires-python": ">=3.10",
        "license": "MIT",
        "license-files": ["LICENSE"],
        "authors": [{"name": "Fixture"}],
        "keywords": ["fixture"],
        "classifiers": ["Fixture :: Classifier"],
        "urls": {"Homepage": "https://example.invalid"},
        "dependencies": [],
        "optional-dependencies": {"Feature": []},
    }


def test_expected_core_metadata_projection_covers_optional_and_empty_fields() -> None:
    project = _valid_reviewed_project()
    headers, body = subject._expected_core_metadata_projection(
        project,
        version=VERSION,
        dependencies=('dependency>=1;extra == "feature"',),
        readme_payload=b"# Fixture\r\n",
    )
    assert ("keywords", "fixture") in headers
    assert ("project-url", "Homepage, https://example.invalid") in headers
    assert ("provides-extra", "feature") in headers
    assert body == "# Fixture\n"

    project.update({"keywords": [], "urls": {}, "optional-dependencies": {}})
    headers, _body = subject._expected_core_metadata_projection(
        project,
        version=VERSION,
        dependencies=(),
        readme_payload=b"",
    )
    assert not {name for name, _value in headers} & {
        "keywords",
        "project-url",
        "provides-extra",
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("name", "other"),
        ("requires-python", ">=3.11"),
        ("license", "Apache-2.0"),
        ("readme", "OTHER.md"),
        ("dynamic", []),
        ("description", None),
        ("description", ""),
        ("authors", None),
        ("authors", []),
        ("authors", [1]),
        ("authors", [{"email": "fixture@example.invalid"}]),
        ("authors", [{"name": 1}]),
        ("authors", [{"name": ""}]),
        ("keywords", None),
        ("keywords", [1]),
        ("keywords", [""]),
        ("keywords", ["same", "same"]),
        ("classifiers", None),
        ("classifiers", [1]),
        ("classifiers", [""]),
        ("classifiers", ["same", "same"]),
        ("license-files", []),
        ("urls", None),
        ("urls", {1: "https://example.invalid"}),
        ("urls", {"": "https://example.invalid"}),
        ("urls", {"Homepage": 1}),
        ("urls", {"Homepage": ""}),
        ("optional-dependencies", None),
    ],
)
def test_expected_core_metadata_projection_rejects_each_malformed_field(
    key: str,
    value: object,
) -> None:
    project = _valid_reviewed_project()
    project[key] = value

    with pytest.raises(ValueError, match="core metadata contract is malformed"):
        subject._expected_core_metadata_projection(
            project,
            version=VERSION,
            dependencies=(),
            readme_payload=b"# Fixture\n",
        )


def test_expected_core_metadata_projection_rejects_utf8_and_extra_aliases() -> None:
    project = _valid_reviewed_project()
    with pytest.raises(ValueError, match="README is not UTF-8"):
        subject._expected_core_metadata_projection(
            project,
            version=VERSION,
            dependencies=(),
            readme_payload=b"\xff",
        )

    project["optional-dependencies"] = {"Feature": [], "feature": []}
    with pytest.raises(ValueError, match="extra names are not canonical and unique"):
        subject._expected_core_metadata_projection(
            project,
            version=VERSION,
            dependencies=(),
            readme_payload=b"",
        )


def test_canonical_metadata_projection_normalizes_dependencies_and_extras() -> None:
    metadata = BytesParser(policy=policy.default).parsebytes(
        b"Metadata-Version: 2.4\n"
        b"Requires-Dist: PyYAML >= 6\n"
        b"Provides-Extra: Feature_Name\n"
        b"\n"
        b"body\r\n"
    )

    headers, body = subject._canonical_project_metadata_projection(metadata)
    assert ("requires-dist", "pyyaml>=6") in headers
    assert ("provides-extra", "feature-name") in headers
    assert body == "body\n"
    assert (
        subject._metadata_counter_summary(Counter({("x-header", "value"): 2}))
        == "x-header='value' x2"
    )

    metadata.set_payload([Message()])
    with pytest.raises(ValueError, match="body is not plain text"):
        subject._canonical_project_metadata_projection(metadata)


def test_project_metadata_projection_reports_missing_headers_and_readme_body() -> None:
    canonical = BytesParser(policy=policy.default).parsebytes(_metadata())
    expected_headers, expected_body = subject._canonical_project_metadata_projection(canonical)
    altered = BytesParser(policy=policy.default).parsebytes(
        _metadata()
        .replace(b"Summary: Release fixture\n", b"")
        .replace(
            b"# Fixture\n",
            b"# Altered\n",
        )
    )

    failures = subject._project_metadata_failures(
        altered,
        label="fixture",
        expected_version=VERSION,
        expected_dependencies=("pyyaml<7,>=6.0",),
        expected_core_metadata=(expected_headers, expected_body),
        require_classifiers=True,
    )
    assert any("is missing or alters reviewed core metadata" in failure for failure in failures)
    assert "fixture description body does not match committed README" in failures
