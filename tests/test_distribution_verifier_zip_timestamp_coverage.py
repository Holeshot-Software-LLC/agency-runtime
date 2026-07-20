"""Exact timestamp and ZIP cross-view coverage for the release verifier."""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import verify_distribution as subject

CANONICAL_TIMESTAMP = (2024, 1, 2, 3, 4, 6)
CANONICAL_EPOCH = 1_704_164_646


def _wheel_item(
    name: str = "package/module.py",
    *,
    payload_size: int = 4,
    timestamp: tuple[int, int, int, int, int, int] = CANONICAL_TIMESTAMP,
    header_offset: int = 0,
) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, timestamp)
    item.create_system = subject.CANONICAL_ZIP_SYSTEM
    item.create_version = subject.CANONICAL_ZIP_VERSION
    item.extract_version = subject.CANONICAL_ZIP_VERSION
    item.reserved = 0
    item.flag_bits = 0x800 if not name.isascii() else 0
    item.compress_type = zipfile.ZIP_STORED
    item.CRC = 0x1234ABCD
    item.compress_size = payload_size
    item.file_size = payload_size
    item.extra = b""
    item.comment = b""
    item.volume = 0
    item.internal_attr = 0
    item.external_attr = subject.CANONICAL_WHEEL_MODE << 16
    item.header_offset = header_offset
    return item


def _central_fields(item: zipfile.ZipInfo) -> dict[str, int]:
    dos_time, dos_date = subject._dos_zip_fields(item)
    return {
        "made_by": (item.create_system << 8) | item.create_version,
        "extract": (item.reserved << 8) | item.extract_version,
        "flags": item.flag_bits,
        "method": item.compress_type,
        "modified_time": dos_time,
        "modified_date": dos_date,
        "crc": item.CRC,
        "compressed_size": item.compress_size,
        "file_size": item.file_size,
        "volume": item.volume,
        "internal_attr": item.internal_attr,
        "external_attr": item.external_attr,
        "local_offset": item.header_offset,
    }


def _central_record(
    item: zipfile.ZipInfo,
    *,
    overrides: dict[str, int] | None = None,
    encoded_name: bytes | None = None,
    extra: bytes = b"",
    comment: bytes = b"",
) -> bytes:
    fields = _central_fields(item)
    fields.update(overrides or {})
    name = subject._encoded_zip_name(item) if encoded_name is None else encoded_name
    header = b"PK\x01\x02" + struct.pack(
        "<6H3L5H2L",
        fields["made_by"],
        fields["extract"],
        fields["flags"],
        fields["method"],
        fields["modified_time"],
        fields["modified_date"],
        fields["crc"],
        fields["compressed_size"],
        fields["file_size"],
        len(name),
        len(extra),
        len(comment),
        fields["volume"],
        fields["internal_attr"],
        fields["external_attr"],
        fields["local_offset"],
    )
    return header + name + extra + comment


def _local_fields(item: zipfile.ZipInfo) -> dict[str, int]:
    dos_time, dos_date = subject._dos_zip_fields(item)
    return {
        "extract_version": item.extract_version,
        "flags": item.flag_bits,
        "method": item.compress_type,
        "modified_time": dos_time,
        "modified_date": dos_date,
        "crc": item.CRC,
        "compressed_size": item.compress_size,
        "file_size": item.file_size,
    }


def _local_record(
    item: zipfile.ZipInfo,
    *,
    overrides: dict[str, int] | None = None,
    encoded_name: bytes | None = None,
    extra: bytes = b"",
) -> bytes:
    fields = _local_fields(item)
    fields.update(overrides or {})
    name = subject._encoded_zip_name(item) if encoded_name is None else encoded_name
    header = struct.pack(
        "<I5H3L2H",
        0x04034B50,
        fields["extract_version"],
        fields["flags"],
        fields["method"],
        fields["modified_time"],
        fields["modified_date"],
        fields["crc"],
        fields["compressed_size"],
        fields["file_size"],
        len(name),
        len(extra),
    )
    return header + name + extra + (b"x" * fields["compressed_size"])


@pytest.mark.parametrize("value", [True, "1", 1.5, -1, 2**32])
def test_canonical_zip_timestamp_rejects_non_uint32_values(value: Any) -> None:
    with pytest.raises(ValueError, match="unsigned 32-bit"):
        subject._canonical_zip_timestamp(value)


def test_canonical_zip_timestamp_rounds_to_dos_precision_and_rejects_pre_zip_epoch() -> None:
    assert subject._canonical_zip_timestamp(CANONICAL_EPOCH + 1) == CANONICAL_TIMESTAMP
    with pytest.raises(ValueError, match="outside the ZIP range"):
        subject._canonical_zip_timestamp(0)


def test_canonical_zip_timestamp_normalizes_platform_time_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_time(_timestamp: int) -> tuple[int, ...]:
        raise OSError("platform time conversion failed")

    monkeypatch.setattr(subject.time, "gmtime", unavailable_time)
    with pytest.raises(ValueError, match="outside the supported range") as raised:
        subject._canonical_zip_timestamp(CANONICAL_EPOCH)
    assert isinstance(raised.value.__cause__, OSError)


def test_reviewed_commit_timestamp_accepts_canonical_ascii(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_git_output",
        lambda *_args, **_kwargs: f"{CANONICAL_EPOCH}\n".encode("ascii"),
    )
    assert subject._reviewed_commit_timestamp(Path("."), "a" * 40) == CANONICAL_EPOCH


@pytest.mark.parametrize(
    ("encoded", "message"),
    [
        (b"\xff", "reviewed commit timestamp is invalid"),
        (b"01", "reviewed commit timestamp is invalid"),
        (b"0", "outside the ZIP range"),
    ],
)
def test_reviewed_commit_timestamp_rejects_invalid_git_values(
    monkeypatch: pytest.MonkeyPatch,
    encoded: bytes,
    message: str,
) -> None:
    monkeypatch.setattr(subject, "_git_output", lambda *_args, **_kwargs: encoded)
    with pytest.raises(ValueError, match=message):
        subject._reviewed_commit_timestamp(Path("."), "a" * 40)


@pytest.mark.parametrize(
    ("name", "flags", "expected"),
    [
        ("package/module.py", 0, b"package/module.py"),
        ("package/caf\u00e9.py", 0x800, "package/caf\u00e9.py".encode()),
    ],
)
def test_encoded_zip_name_accepts_only_its_canonical_flag(
    name: str,
    flags: int,
    expected: bytes,
) -> None:
    item = SimpleNamespace(filename=name, flag_bits=flags)
    assert subject._encoded_zip_name(item) == expected


@pytest.mark.parametrize(
    ("name", "flags"),
    [
        ("package/module.py", 0x800),
        ("package/caf\u00e9.py", 0),
    ],
)
def test_encoded_zip_name_rejects_flag_and_name_disagreement(name: str, flags: int) -> None:
    item = SimpleNamespace(filename=name, flag_bits=flags)
    with pytest.raises(ValueError, match="encoding flag is noncanonical"):
        subject._encoded_zip_name(item)


def test_dos_zip_fields_encode_a_valid_even_second() -> None:
    item = SimpleNamespace(filename="member", date_time=CANONICAL_TIMESTAMP)
    expected_time = (3 << 11) | (4 << 5) | 3
    expected_date = ((2024 - 1980) << 9) | (1 << 5) | 2
    assert subject._dos_zip_fields(item) == (expected_time, expected_date)


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ((2024, 13, 1, 0, 0, 0), "invalid DOS timestamp"),
        ((1979, 1, 1, 0, 0, 0), "noncanonical DOS timestamp"),
        ((2108, 1, 1, 0, 0, 0), "noncanonical DOS timestamp"),
        ((2024, 1, 1, 0, 0, 1), "noncanonical DOS timestamp"),
    ],
)
def test_dos_zip_fields_reject_invalid_or_noncanonical_values(
    timestamp: tuple[int, int, int, int, int, int],
    message: str,
) -> None:
    item = SimpleNamespace(filename="member", date_time=timestamp)
    with pytest.raises(ValueError, match=message):
        subject._dos_zip_fields(item)


def test_canonical_wheel_info_accepts_regular_record_and_optional_timestamp() -> None:
    regular = _wheel_item()
    subject._validate_canonical_wheel_info(regular, expected_timestamp=None)
    subject._validate_canonical_wheel_info(
        regular,
        expected_timestamp=CANONICAL_TIMESTAMP,
    )

    record = _wheel_item("package-1.0.dist-info/RECORD")
    record.external_attr = subject.CANONICAL_RECORD_MODE << 16
    subject._validate_canonical_wheel_info(
        record,
        expected_timestamp=CANONICAL_TIMESTAMP,
    )


@pytest.mark.parametrize(
    "attribute",
    [
        "create_system",
        "create_version",
        "extract_version",
        "reserved",
        "volume",
        "internal_attr",
        "external_attr",
    ],
)
def test_canonical_wheel_info_rejects_each_header_cross_view_mismatch(
    attribute: str,
) -> None:
    item = _wheel_item()
    setattr(item, attribute, getattr(item, attribute) + 1)
    with pytest.raises(ValueError, match="member header is noncanonical"):
        subject._validate_canonical_wheel_info(
            item,
            expected_timestamp=CANONICAL_TIMESTAMP,
        )


def test_canonical_wheel_info_rejects_a_reviewed_timestamp_mismatch() -> None:
    item = _wheel_item()
    with pytest.raises(ValueError, match="timestamp does not match the reviewed commit"):
        subject._validate_canonical_wheel_info(
            item,
            expected_timestamp=(2024, 1, 2, 3, 4, 8),
        )


@pytest.mark.parametrize("name", ["package/module.py", "package/caf\u00e9.py"])
def test_preflight_and_parsed_central_views_accept_the_same_record(name: str) -> None:
    item = _wheel_item(name)
    record = _central_record(item)
    prefix = b"pad"
    directory_offset = len(prefix)
    directory_end = directory_offset + len(record)

    preflight_stream = io.BytesIO(prefix + record)
    subject._preflight_zip_central_records(
        preflight_stream,
        directory_offset=directory_offset,
        directory_end=directory_end,
        members=1,
    )

    parsed_stream = io.BytesIO(prefix + record)
    subject._validate_zip_central_records(
        SimpleNamespace(fp=parsed_stream),
        [item],
        directory_offset=directory_offset,
        directory_end=directory_end,
    )


@pytest.mark.parametrize("record", [b"short", b"NOPE" + (b"\0" * 42)])
def test_preflight_central_view_rejects_truncated_and_unknown_records(record: bytes) -> None:
    with pytest.raises(ValueError, match="unknown record or count mismatch"):
        subject._preflight_zip_central_records(
            io.BytesIO(record),
            directory_offset=0,
            directory_end=len(record),
            members=1,
        )


@pytest.mark.parametrize("name_size", [0, subject.MAX_ARCHIVE_NAME_BYTES + 1])
def test_preflight_central_view_rejects_noncanonical_name_bounds(name_size: int) -> None:
    item = _wheel_item()
    record = _central_record(item)
    raw = bytearray(record[:46])
    struct.pack_into("<H", raw, 28, name_size)
    with pytest.raises(ValueError, match="record exceeds its bounded layout"):
        subject._preflight_zip_central_records(
            io.BytesIO(raw),
            directory_offset=0,
            directory_end=46 + name_size,
            members=1,
        )


def test_preflight_central_view_rejects_a_record_past_its_boundary() -> None:
    record = _central_record(_wheel_item())
    with pytest.raises(ValueError, match="record exceeds its bounded layout"):
        subject._preflight_zip_central_records(
            io.BytesIO(record),
            directory_offset=0,
            directory_end=len(record) - 1,
            members=1,
        )


@pytest.mark.parametrize(
    ("extra", "comment"),
    [
        (b"x", b""),
        (b"", b"x"),
    ],
)
def test_preflight_central_view_rejects_member_metadata(
    extra: bytes,
    comment: bytes,
) -> None:
    record = _central_record(_wheel_item(), extra=extra, comment=comment)
    with pytest.raises(ValueError, match="comment or extra field"):
        subject._preflight_zip_central_records(
            io.BytesIO(record),
            directory_offset=0,
            directory_end=len(record),
            members=1,
        )


def test_preflight_central_view_rejects_invalid_utf8_name() -> None:
    item = _wheel_item("package/\u00e9.py")
    record = _central_record(item, encoded_name=b"\xff\xff")
    with pytest.raises(ValueError, match="filename is invalid"):
        subject._preflight_zip_central_records(
            io.BytesIO(record),
            directory_offset=0,
            directory_end=len(record),
            members=1,
        )


def test_preflight_central_view_enforces_physical_and_ratio_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    physical = _wheel_item(payload_size=4)
    physical_record = _central_record(physical)
    monkeypatch.setattr(subject, "MAX_ARTIFACT_PHYSICAL_BYTES", 3)
    with pytest.raises(ValueError, match="compressed member exceeds"):
        subject._preflight_zip_central_records(
            io.BytesIO(physical_record),
            directory_offset=0,
            directory_end=len(physical_record),
            members=1,
        )

    monkeypatch.setattr(subject, "MAX_ARTIFACT_PHYSICAL_BYTES", 1_000)
    zero_compressed = _wheel_item(payload_size=1)
    zero_record = _central_record(
        zero_compressed,
        overrides={"compressed_size": 0},
    )
    with pytest.raises(ValueError, match="compression ratio limit"):
        subject._preflight_zip_central_records(
            io.BytesIO(zero_record),
            directory_offset=0,
            directory_end=len(zero_record),
            members=1,
        )

    ratio = _wheel_item(payload_size=subject.MAX_ZIP_COMPRESSION_RATIO + 1)
    ratio_record = _central_record(ratio, overrides={"compressed_size": 1})
    with pytest.raises(ValueError, match="compression ratio limit"):
        subject._preflight_zip_central_records(
            io.BytesIO(ratio_record),
            directory_offset=0,
            directory_end=len(ratio_record),
            members=1,
        )


@pytest.mark.parametrize(
    ("constant", "value", "message"),
    [
        ("MAX_ARCHIVE_MEMBERS", 0, "member count limit"),
        ("MAX_ARCHIVE_MEMBER_BYTES", 3, "declared size limit"),
        ("MAX_ARCHIVE_TOTAL_BYTES", 3, "total uncompressed size limit"),
    ],
)
def test_preflight_central_view_enforces_each_uncompressed_budget(
    monkeypatch: pytest.MonkeyPatch,
    constant: str,
    value: int,
    message: str,
) -> None:
    item = _wheel_item(payload_size=4)
    record = _central_record(item)
    monkeypatch.setattr(subject, constant, value)
    with pytest.raises(ValueError, match=message):
        subject._preflight_zip_central_records(
            io.BytesIO(record),
            directory_offset=0,
            directory_end=len(record),
            members=1,
        )


def test_preflight_central_view_requires_exact_final_offset() -> None:
    record = _central_record(_wheel_item())
    with pytest.raises(ValueError, match="unknown record or count mismatch"):
        subject._preflight_zip_central_records(
            io.BytesIO(record),
            directory_offset=0,
            directory_end=len(record) + 1,
            members=1,
        )


def test_parsed_central_view_rejects_closed_truncated_and_unknown_records() -> None:
    item = _wheel_item()
    with pytest.raises(ValueError, match="archive was closed"):
        subject._validate_zip_central_records(
            SimpleNamespace(fp=None),
            [item],
            directory_offset=0,
            directory_end=0,
        )

    for record in (b"short", b"NOPE" + (b"\0" * 42)):
        with pytest.raises(ValueError, match="unknown record or gap"):
            subject._validate_zip_central_records(
                SimpleNamespace(fp=io.BytesIO(record)),
                [item],
                directory_offset=0,
                directory_end=len(record),
            )


@pytest.mark.parametrize(
    "field",
    [
        "made_by",
        "extract",
        "flags",
        "method",
        "modified_time",
        "modified_date",
        "crc",
        "compressed_size",
        "file_size",
        "volume",
        "internal_attr",
        "external_attr",
        "local_offset",
    ],
)
def test_parsed_central_view_rejects_each_numeric_mismatch(field: str) -> None:
    item = _wheel_item()
    fields = _central_fields(item)
    record = _central_record(item, overrides={field: fields[field] + 1})
    with pytest.raises(ValueError, match="central record differs from parsed metadata"):
        subject._validate_zip_central_records(
            SimpleNamespace(fp=io.BytesIO(record)),
            [item],
            directory_offset=0,
            directory_end=len(record),
        )


@pytest.mark.parametrize(
    ("encoded_name", "extra", "comment"),
    [
        (b"qackage/module.py", b"", b""),
        (None, b"x", b""),
        (None, b"", b"x"),
    ],
)
def test_parsed_central_view_rejects_each_byte_sequence_mismatch(
    encoded_name: bytes | None,
    extra: bytes,
    comment: bytes,
) -> None:
    item = _wheel_item()
    record = _central_record(
        item,
        encoded_name=encoded_name,
        extra=extra,
        comment=comment,
    )
    with pytest.raises(ValueError, match="central record differs from parsed metadata"):
        subject._validate_zip_central_records(
            SimpleNamespace(fp=io.BytesIO(record)),
            [item],
            directory_offset=0,
            directory_end=len(record),
        )


@pytest.mark.parametrize("directory_end_delta", [-1, 1])
def test_parsed_central_view_rejects_cross_view_boundaries(
    directory_end_delta: int,
) -> None:
    item = _wheel_item()
    record = _central_record(item)
    with pytest.raises(ValueError, match="central"):
        subject._validate_zip_central_records(
            SimpleNamespace(fp=io.BytesIO(record)),
            [item],
            directory_offset=0,
            directory_end=len(record) + directory_end_delta,
        )


@pytest.mark.parametrize("name", ["package/module.py", "package/caf\u00e9.py"])
def test_local_view_accepts_matching_ascii_and_utf8_headers(name: str) -> None:
    prefix = b"pad"
    item = _wheel_item(name, header_offset=len(prefix))
    record = _local_record(item)
    archive = SimpleNamespace(fp=io.BytesIO(prefix + record))
    expected_end = (
        item.header_offset + 30 + len(subject._encoded_zip_name(item)) + item.compress_size
    )
    assert subject._zip_local_data_end(archive, item) == expected_end


def test_local_view_rejects_closed_truncated_and_unknown_headers() -> None:
    item = _wheel_item()
    with pytest.raises(ValueError, match="archive was closed"):
        subject._zip_local_data_end(SimpleNamespace(fp=None), item)

    for record in (b"short", b"NOPE" + (b"\0" * 26)):
        with pytest.raises(ValueError, match="local header is invalid"):
            subject._zip_local_data_end(
                SimpleNamespace(fp=io.BytesIO(record)),
                item,
            )


def test_local_view_rejects_invalid_utf8_filename() -> None:
    item = _wheel_item("\u00e9")
    record = _local_record(item, encoded_name=b"\xff\xff")
    with pytest.raises(ValueError, match="local filename is invalid"):
        subject._zip_local_data_end(
            SimpleNamespace(fp=io.BytesIO(record)),
            item,
        )


@pytest.mark.parametrize(
    "field",
    [
        "extract_version",
        "flags",
        "method",
        "modified_time",
        "modified_date",
        "crc",
        "compressed_size",
        "file_size",
    ],
)
def test_local_view_rejects_each_numeric_cross_view_mismatch(field: str) -> None:
    item = _wheel_item()
    fields = _local_fields(item)
    record = _local_record(item, overrides={field: fields[field] + 1})
    with pytest.raises(ValueError, match="local header differs from its central record"):
        subject._zip_local_data_end(
            SimpleNamespace(fp=io.BytesIO(record)),
            item,
        )


@pytest.mark.parametrize(
    ("encoded_name", "extra"),
    [
        (b"qackage/module.py", b""),
        (None, b"x"),
    ],
)
def test_local_view_rejects_each_byte_sequence_cross_view_mismatch(
    encoded_name: bytes | None,
    extra: bytes,
) -> None:
    item = _wheel_item()
    record = _local_record(item, encoded_name=encoded_name, extra=extra)
    with pytest.raises(ValueError, match="local header differs from its central record"):
        subject._zip_local_data_end(
            SimpleNamespace(fp=io.BytesIO(record)),
            item,
        )


def test_local_view_rejects_noncanonical_stored_size() -> None:
    item = _wheel_item(payload_size=2)
    item.file_size = 1
    record = _local_record(item)
    with pytest.raises(ValueError, match="stored member has a noncanonical size"):
        subject._zip_local_data_end(
            SimpleNamespace(fp=io.BytesIO(record)),
            item,
        )
