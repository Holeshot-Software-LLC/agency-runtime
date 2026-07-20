"""End-to-end mutation tests for exact wheel and sdist container boundaries."""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import os
import struct
import tarfile
import zipfile
import zlib
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts import verify_distribution as subject
from tests.test_distribution_verifier_hardening import (
    PACKAGE_PATH,
    VERSION,
    _artifact_timestamp,
    _artifacts,
    _repository,
    _sdist,
    _stored_gzip,
    _verify,
)


def _rewrite_wheel(
    wheel: Path,
    mutate: Callable[[zipfile.ZipInfo, int], None],
) -> None:
    with zipfile.ZipFile(wheel) as archive:
        entries = [(copy.copy(item), archive.read(item)) for item in archive.infolist()]
    with zipfile.ZipFile(wheel, "w") as archive:
        for index, (item, payload) in enumerate(entries):
            mutate(item, index)
            archive.writestr(item, payload)


def _insert_before_central_directory(wheel: Path, payload: bytes) -> None:
    raw = bytearray(wheel.read_bytes())
    marker = raw.rfind(b"PK\x05\x06")
    assert marker >= 0
    directory_offset = struct.unpack_from("<L", raw, marker + 16)[0]
    raw[directory_offset:directory_offset] = payload
    marker += len(payload)
    struct.pack_into("<L", raw, marker + 16, directory_offset + len(payload))
    wheel.write_bytes(raw)


def _mutate_first_zip_headers(
    wheel: Path,
    *,
    flags: int | None = None,
    method: int | None = None,
) -> None:
    raw = bytearray(wheel.read_bytes())
    local = raw.find(b"PK\x03\x04")
    central = raw.find(b"PK\x01\x02")
    assert local >= 0 and central >= 0
    if flags is not None:
        struct.pack_into("<H", raw, local + 6, flags)
        struct.pack_into("<H", raw, central + 8, flags)
    if method is not None:
        struct.pack_into("<H", raw, local + 8, method)
        struct.pack_into("<H", raw, central + 10, method)
    wheel.write_bytes(raw)


def _first_local_payload_offset(raw: bytes) -> int:
    assert raw[:4] == b"PK\x03\x04"
    name_size, extra_size = struct.unpack_from("<2H", raw, 26)
    return 30 + name_size + extra_size


def _append_canonical_wheel_member(wheel: Path, name: str, payload: bytes) -> None:
    with zipfile.ZipFile(wheel) as archive:
        timestamp = archive.infolist()[0].date_time
    item = zipfile.ZipInfo(name, timestamp)
    item.create_system = subject.CANONICAL_ZIP_SYSTEM
    item.create_version = subject.CANONICAL_ZIP_VERSION
    item.extract_version = subject.CANONICAL_ZIP_VERSION
    item.compress_type = zipfile.ZIP_STORED
    item.external_attr = subject.CANONICAL_WHEEL_MODE << 16
    with zipfile.ZipFile(wheel, "a", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(item, payload)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("archive-comment", "archive comment"),
        ("prefix", "central directory layout is noncanonical"),
        ("member-comment", "comment or extra field"),
        ("member-extra", "comment or extra field"),
        ("orphan-directory", "directory member"),
        ("long-component", "unsafe archive member"),
        ("file-prefix", "file-prefix collision"),
        ("gap", "gap or unreferenced local record"),
        ("orphan-local-record", "gap or unreferenced local record"),
        ("encrypted", "encrypted member"),
        ("unknown-flag", "unsupported ZIP flags"),
        ("data-descriptor-flag", "unsupported ZIP flags"),
        ("unsupported-method", "unsupported compression method"),
        ("deflate-trailing-data", "stored member has a noncanonical size"),
        ("invalid-deflate", "unsupported or invalid compressed data"),
        ("central-header-offset", "prefix, gap, or unreferenced local record"),
        ("local-version", "local header differs"),
        ("local-time", "local header differs"),
        ("local-date", "local header differs"),
        ("local-crc", "local header differs"),
    ],
)
def test_full_verify_rejects_noncanonical_wheel_container_mutations(  # noqa: C901
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected: str,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = dist / f"agency_runtime-{VERSION}-py3-none-any.whl"

    if mutation == "archive-comment":
        with zipfile.ZipFile(wheel, "a") as archive:
            archive.comment = b"comment"
    elif mutation == "prefix":
        wheel.write_bytes(b"prefix" + wheel.read_bytes())
    elif mutation == "member-comment":
        _rewrite_wheel(
            wheel,
            lambda item, index: setattr(item, "comment", b"comment") if index == 0 else None,
        )
    elif mutation == "member-extra":
        _rewrite_wheel(
            wheel,
            lambda item, index: setattr(item, "extra", b"\x99\x99\x00\x00") if index == 0 else None,
        )
    elif mutation == "orphan-directory":
        _append_canonical_wheel_member(wheel, "orphan-empty/", b"")
    elif mutation == "long-component":
        _append_canonical_wheel_member(wheel, f"{'x' * 300}/file.py", b"pass\n")
    elif mutation == "file-prefix":
        _append_canonical_wheel_member(wheel, f"{PACKAGE_PATH}/child", b"collision")
    elif mutation == "gap":
        _insert_before_central_directory(wheel, b"gap")
    elif mutation == "orphan-local-record":
        name = b"orphan"
        compressed = zlib.compressobj(wbits=-15)
        data = compressed.compress(b"") + compressed.flush()
        local = struct.pack(
            "<I5H3L2H",
            0x04034B50,
            20,
            0,
            zipfile.ZIP_DEFLATED,
            0,
            0,
            0,
            len(data),
            0,
            len(name),
            0,
        )
        _insert_before_central_directory(wheel, local + name + data)
    elif mutation == "encrypted":
        _mutate_first_zip_headers(wheel, flags=1)
    elif mutation == "unknown-flag":
        _mutate_first_zip_headers(wheel, flags=2)
    elif mutation == "data-descriptor-flag":
        _mutate_first_zip_headers(wheel, flags=8)
    elif mutation == "unsupported-method":
        _mutate_first_zip_headers(wheel, method=99)
    elif mutation == "deflate-trailing-data":
        raw = bytearray(wheel.read_bytes())
        local = raw.find(b"PK\x03\x04")
        central = raw.find(b"PK\x01\x02")
        end = raw.rfind(b"PK\x05\x06")
        assert local >= 0 and central >= 0 and end >= 0
        compressed_size = struct.unpack_from("<L", raw, local + 18)[0]
        payload_end = _first_local_payload_offset(raw) + compressed_size
        directory_offset = struct.unpack_from("<L", raw, end + 16)[0]
        trailing = b"hidden"
        raw[payload_end:payload_end] = trailing
        central += len(trailing)
        end += len(trailing)
        struct.pack_into("<L", raw, local + 18, compressed_size + len(trailing))
        struct.pack_into("<L", raw, central + 20, compressed_size + len(trailing))
        struct.pack_into("<L", raw, end + 16, directory_offset + len(trailing))
        wheel.write_bytes(raw)
    elif mutation == "invalid-deflate":
        raw = bytearray(wheel.read_bytes())
        raw[_first_local_payload_offset(raw)] ^= 0xFF
        wheel.write_bytes(raw)
    elif mutation == "central-header-offset":
        raw = bytearray(wheel.read_bytes())
        central = raw.find(b"PK\x01\x02")
        current = struct.unpack_from("<L", raw, central + 42)[0]
        struct.pack_into("<L", raw, central + 42, current + 1)
        wheel.write_bytes(raw)
    elif mutation in {"local-version", "local-time", "local-date", "local-crc"}:
        raw = bytearray(wheel.read_bytes())
        offsets = {
            "local-version": (4, "<H"),
            "local-time": (10, "<H"),
            "local-date": (12, "<H"),
            "local-crc": (14, "<L"),
        }
        offset, encoding = offsets[mutation]
        current = struct.unpack_from(encoding, raw, offset)[0]
        struct.pack_into(encoding, raw, offset, current ^ 1)
        wheel.write_bytes(raw)
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)

    failures = _verify(monkeypatch, dist, repository)
    assert len(failures) == 1
    assert expected in failures[0]


def _write_custom_sdist(
    path: Path,
    *,
    format: int = tarfile.PAX_FORMAT,
    pax_headers: dict[str, str] | None = None,
    member_name: str = f"agency_runtime-{VERSION}/file",
    member_pax: dict[str, str] | None = None,
    member_type: bytes = tarfile.REGTYPE,
) -> None:
    timestamp = _artifact_timestamp(path)
    payload = io.BytesIO()
    with tarfile.open(
        fileobj=payload,
        mode="w:",
        format=format,
        pax_headers=pax_headers,
    ) as archive:
        root = tarfile.TarInfo(f"agency_runtime-{VERSION}/")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        root.mtime = timestamp
        archive.addfile(root)
        member = tarfile.TarInfo(member_name)
        member.type = member_type
        member.mode = 0o755 if member_type == tarfile.DIRTYPE else 0o644
        member.mtime = timestamp
        member.size = 0
        member.pax_headers = member_pax or {}
        archive.addfile(member, io.BytesIO() if member_type == tarfile.REGTYPE else None)
    _write_canonical_gzip(path, payload.getvalue())


def _write_canonical_gzip(path: Path, payload: bytes) -> None:
    path.write_bytes(
        _stored_gzip(
            payload,
            filename=path.name[:-3],
            timestamp=_artifact_timestamp(path),
        )
    )


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("second-gzip", "trailing data or multiple gzip members"),
        ("trailing-gzip-data", "trailing data or multiple gzip members"),
        ("nonzero-tar-tail", "nonzero trailing data"),
        ("orphan-directory", "exactly match file parent directories"),
        ("long-pax-directory", "unsafe archive member"),
        ("file-prefix", "file-prefix collision"),
        ("unknown-pax", "PAX record key is unsupported"),
        ("global-pax", "unsupported extended header"),
        ("gnu-longname", "noncanonical owner, device, or reserved fields"),
        ("oversized-pax", "PAX header exceeds its size limit"),
        ("gzip-header", "gzip header is noncanonical"),
        ("gzip-filename", "gzip filename does not match"),
        ("excess-zero-padding", "excess zero padding"),
    ],
)
def test_full_verify_rejects_noncanonical_sdist_container_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected: str,
) -> None:
    repository, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    sdist = dist / f"agency_runtime-{VERSION}.tar.gz"

    if mutation == "second-gzip":
        sdist.write_bytes(sdist.read_bytes() + gzip.compress(b""))
    elif mutation == "trailing-gzip-data":
        sdist.write_bytes(sdist.read_bytes() + b"trailing")
    elif mutation == "nonzero-tar-tail":
        tar_payload = bytearray(gzip.decompress(sdist.read_bytes()))
        tar_payload[-1] = ord("x")
        _write_canonical_gzip(sdist, bytes(tar_payload))
    elif mutation == "orphan-directory":
        _sdist(sdist, payloads, typed_members={"orphan": tarfile.DIRTYPE})
    elif mutation == "long-pax-directory":
        _write_custom_sdist(
            sdist,
            member_name=f"agency_runtime-{VERSION}/{'x' * 300}/",
            member_type=tarfile.DIRTYPE,
        )
    elif mutation == "file-prefix":
        _sdist(sdist, payloads, extra={f"{PACKAGE_PATH}/child": b"collision"})
    elif mutation == "unknown-pax":
        _write_custom_sdist(sdist, member_pax={"comment": "unapproved"})
    elif mutation == "global-pax":
        _write_custom_sdist(sdist, pax_headers={"comment": "unapproved"})
    elif mutation == "gnu-longname":
        _write_custom_sdist(
            sdist,
            format=tarfile.GNU_FORMAT,
            member_name=f"agency_runtime-{VERSION}/{'x' * 300}",
        )
    elif mutation == "oversized-pax":
        incompressible = "".join(
            hashlib.sha256(index.to_bytes(4, "big")).hexdigest() for index in range(1_100)
        )
        _write_custom_sdist(sdist, member_pax={"comment": incompressible})
    elif mutation == "gzip-header":
        raw = bytearray(sdist.read_bytes())
        raw[3] = 0
        sdist.write_bytes(raw)
    elif mutation == "gzip-filename":
        raw = bytearray(sdist.read_bytes())
        raw[10] = ord("x")
        sdist.write_bytes(raw)
    elif mutation == "excess-zero-padding":
        tar_payload = gzip.decompress(sdist.read_bytes())
        _write_canonical_gzip(sdist, tar_payload + (b"\0" * 10_240))
    else:  # pragma: no cover - parameter table is exhaustive
        raise AssertionError(mutation)

    failures = _verify(monkeypatch, dist, repository)
    assert len(failures) == 1
    assert expected in failures[0]


def test_main_preserves_a_link_path_for_the_verifier_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation is unavailable: {exc}")

    observed: list[Path] = []

    def capture(path: Path, **_kwargs: object) -> list[str]:
        observed.append(path)
        return ["rejected"]

    monkeypatch.setattr(subject, "verify", capture)
    assert subject.main([str(linked), "--expected-commit", "0" * 40]) == 1
    assert observed == [Path(os.path.abspath(linked))]
    assert observed[0] != target.resolve()
