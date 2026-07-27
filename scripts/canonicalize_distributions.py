"""Normalize trusted build outputs to one bounded, platform-independent container format."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import re
import stat
import struct
import tarfile
import tempfile
import time
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path, PurePosixPath

try:  # Support both ``python -m scripts...`` and direct script execution.
    from scripts.release_contract import (
        CANONICAL_LF_SDIST_GENERATED_FILES,
        CANONICAL_LF_WHEEL_GENERATED_FILES,
        CANONICAL_RECORD_MODE,
        CANONICAL_WHEEL_MODE,
        CANONICAL_ZIP_METHOD,
        CANONICAL_ZIP_SYSTEM,
        CANONICAL_ZIP_VERSION,
        MAX_ARCHIVE_MEMBER_BYTES,
        MAX_ARCHIVE_MEMBERS,
        MAX_ARCHIVE_NAME_BYTES,
        MAX_ARCHIVE_TOTAL_BYTES,
        MAX_ARTIFACT_PHYSICAL_BYTES,
        MAX_TAR_CONTAINER_BYTES,
        MAX_ZIP_COMPRESSION_RATIO,
        NATIVE_OPERATOR_PRESENCE_EXECUTABLE,
        safe_release_name,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - direct-script compatibility
    if exc.name != "scripts":
        raise
    from release_contract import (  # type: ignore[no-redef]
        CANONICAL_LF_SDIST_GENERATED_FILES,
        CANONICAL_LF_WHEEL_GENERATED_FILES,
        CANONICAL_RECORD_MODE,
        CANONICAL_WHEEL_MODE,
        CANONICAL_ZIP_METHOD,
        CANONICAL_ZIP_SYSTEM,
        CANONICAL_ZIP_VERSION,
        MAX_ARCHIVE_MEMBER_BYTES,
        MAX_ARCHIVE_MEMBERS,
        MAX_ARCHIVE_NAME_BYTES,
        MAX_ARCHIVE_TOTAL_BYTES,
        MAX_ARTIFACT_PHYSICAL_BYTES,
        MAX_TAR_CONTAINER_BYTES,
        MAX_ZIP_COMPRESSION_RATIO,
        NATIVE_OPERATOR_PRESENCE_EXECUTABLE,
        safe_release_name,
    )

MAX_ARTIFACT_BYTES = MAX_ARTIFACT_PHYSICAL_BYTES
READ_CHUNK_BYTES = 64 * 1024

SOURCE_ZIP_METHOD = zipfile.ZIP_DEFLATED
SOURCE_WHEEL_MODES = {
    0: {
        "ordinary": stat.S_IFREG | 0o666,
        "record": stat.S_IFREG | 0o664,
    },
    3: {
        "ordinary": stat.S_IFREG | 0o644,
        "record": stat.S_IFREG | 0o664,
    },
}
SOURCE_TAR_FILE_MODES = {0o644, 0o666}
SOURCE_TAR_DIRECTORY_MODES = {0o755, 0o777}
_ZERO_BLOCK = b"\0" * tarfile.BLOCKSIZE
_PAX_RECORD = re.compile(rb"(0|[1-9][0-9]*) ([^=\n]+)=([^\n]*)\n")


@dataclass(frozen=True, slots=True)
class _TarEntry:
    name: str
    payload: bytes | None

    @property
    def is_directory(self) -> bool:
        return self.payload is None


def _source_tar_file_mode_allowed(name: str, mode: int) -> bool:
    if mode in SOURCE_TAR_FILE_MODES:
        return True
    parts = PurePosixPath(name).parts
    if len(parts) < 2:
        return False
    relative = PurePosixPath(*parts[1:]).as_posix()
    # setuptools receives CPython's synthetic Windows .exe execute bits and
    # writes them into the raw sdist. Accept only the one governed native path
    # and only the exact observed writable projection; canonical output is 0644.
    return mode == 0o777 and relative == NATIVE_OPERATOR_PRESENCE_EXECUTABLE


def _canonical_zip_timestamp(timestamp: int) -> tuple[int, int, int, int, int, int]:
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, int)
        or timestamp < 0
        or timestamp >= 2**32
    ):
        raise ValueError("canonical archive timestamp must fit the unsigned 32-bit format")
    try:
        year, month, day, hour, minute, second = time.gmtime(timestamp)[:6]
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("canonical archive timestamp is outside the supported range") from exc
    if year < 1980:
        raise ValueError("canonical archive timestamp is outside the ZIP range")
    return year, month, day, hour, minute, second - (second % 2)


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse)


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        0 if os.name == "nt" else int(metadata.st_ctime_ns),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
        int(getattr(metadata, "st_nlink", 0) or 0),
    )


def _read_bounded_regular_file(path: Path) -> bytes:
    before = os.lstat(path)
    if (
        _is_link_or_reparse(before)
        or not stat.S_ISREG(before.st_mode)
        or int(getattr(before, "st_nlink", 0) or 0) != 1
        or int(before.st_size) > MAX_ARTIFACT_BYTES
        or int(before.st_ino) <= 0
    ):
        raise ValueError(f"distribution input must be a bounded single-link regular file: {path}")
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"distribution input could not be opened safely: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before):
            raise ValueError(f"distribution input changed while it was opened: {path}")
        chunks: list[bytes] = []
        observed = 0
        while True:
            chunk = os.read(descriptor, READ_CHUNK_BYTES)
            if not chunk:
                break
            observed += len(chunk)
            if observed > int(before.st_size) or observed > MAX_ARTIFACT_BYTES:
                raise ValueError(f"distribution input exceeds its size boundary: {path}")
            chunks.append(chunk)
        if observed != int(before.st_size):
            raise ValueError(f"distribution input is shorter than its declared size: {path}")
        if _identity(os.fstat(descriptor)) != _identity(before):
            raise ValueError(f"distribution input changed while it was read: {path}")
    finally:
        os.close(descriptor)
    if _identity(os.lstat(path)) != _identity(before):
        raise ValueError(f"distribution input path changed while it was read: {path}")
    return b"".join(chunks)


def _replace_regular_file(path: Path, payload: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.canonical-",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            for offset in range(0, len(payload), READ_CHUNK_BYTES):
                stream.write(payload[offset : offset + READ_CHUNK_BYTES])
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            temporary.unlink()


def _member_budget(
    *,
    count: int,
    size: int,
    total: int,
    artifact: str,
) -> int:
    if count > MAX_ARCHIVE_MEMBERS:
        raise ValueError(f"{artifact} exceeds the archive member count limit")
    if size < 0 or size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ValueError(f"{artifact} member exceeds the declared size limit")
    updated = total + size
    if updated > MAX_ARCHIVE_TOTAL_BYTES:
        raise ValueError(f"{artifact} exceeds the total uncompressed size limit")
    return updated


def _portable_alias(name: str) -> str:
    return "/".join(
        unicodedata.normalize("NFC", component).casefold()
        for component in PurePosixPath(name).parts
    )


def _read_zip_member(archive: zipfile.ZipFile, item: zipfile.ZipInfo) -> bytes:
    chunks: list[bytes] = []
    observed = 0
    with archive.open(item, "r") as stream:
        while True:
            chunk = stream.read(min(READ_CHUNK_BYTES, item.file_size + 1 - observed))
            if not chunk:
                break
            observed += len(chunk)
            if observed > item.file_size:
                raise ValueError(f"wheel member exceeds its declared size: {item.filename}")
            chunks.append(chunk)
    if observed != item.file_size:
        raise ValueError(f"wheel member is shorter than its declared size: {item.filename}")
    return b"".join(chunks)


def _require_exact_deflate(payload: bytes, *, size: int, name: str) -> None:
    decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
    observed = 0
    cursor = 0
    try:
        while cursor < len(payload):
            chunk = payload[cursor : cursor + READ_CHUNK_BYTES]
            cursor += len(chunk)
            pending = chunk
            while pending:
                inflated = decompressor.decompress(
                    pending,
                    min(READ_CHUNK_BYTES, max(1, size + 1 - observed)),
                )
                observed += len(inflated)
                if observed > size or decompressor.unused_data:
                    raise ValueError(f"wheel compressed member boundary is invalid: {name}")
                remaining = decompressor.unconsumed_tail
                if remaining == pending and not inflated:
                    raise ValueError(f"wheel compressed member is invalid: {name}")
                pending = remaining
            if decompressor.eof and cursor < len(payload):
                raise ValueError(f"wheel compressed member boundary is invalid: {name}")
        observed += len(decompressor.flush(min(READ_CHUNK_BYTES, max(1, size + 1 - observed))))
    except zlib.error as exc:
        raise ValueError(f"wheel compressed member is invalid: {name}") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or observed != size
    ):
        raise ValueError(f"wheel compressed member is invalid: {name}")


def _zip_directory_contract(raw: bytes) -> tuple[int, int, int]:
    if len(raw) < 22 or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("wheel container size is invalid")
    eocd = raw.rfind(b"PK\x05\x06")
    if eocd != len(raw) - 22:
        raise ValueError("wheel end record or trailing-data boundary is invalid")
    (
        disk,
        directory_disk,
        disk_members,
        members,
        directory_size,
        directory_offset,
        comment_size,
    ) = struct.unpack_from("<4H2LH", raw, eocd + 4)
    if (
        disk
        or directory_disk
        or disk_members != members
        or members in {0, 0xFFFF}
        or comment_size
        or members > MAX_ARCHIVE_MEMBERS
        or directory_offset + directory_size != eocd
    ):
        raise ValueError("wheel central directory contract is invalid")
    return directory_offset, eocd, members


def _preflight_source_zip_records(
    raw: bytes,
    *,
    directory_offset: int,
    eocd: int,
    members: int,
    timestamp: tuple[int, int, int, int, int, int],
    require_sorted: bool = False,
    expected_method: int | None = None,
) -> None:
    year, month, day, hour, minute, second = timestamp
    expected_time = (hour << 11) | (minute << 5) | second // 2
    expected_date = ((year - 1980) << 9) | (month << 5) | day
    offset = directory_offset
    total = 0
    aliases: set[str] = set()
    names: list[str] = []
    methods: set[int] = set()
    for count in range(1, members + 1):
        if offset + 46 > eocd or raw[offset : offset + 4] != b"PK\x01\x02":
            raise ValueError("wheel central directory contains an unknown record or count mismatch")
        (
            made_by,
            extract,
            flags,
            method,
            modified_time,
            modified_date,
            _crc,
            compressed_size,
            file_size,
            name_size,
            extra_size,
            comment_size,
            volume,
            internal_attr,
            external_attr,
            local_offset,
        ) = struct.unpack_from("<6H3L5H2L", raw, offset + 4)
        end = offset + 46 + name_size + extra_size + comment_size
        if (
            end > eocd
            or not 0 < name_size <= MAX_ARCHIVE_NAME_BYTES
            or extra_size
            or comment_size
            or extract != CANONICAL_ZIP_VERSION
            or flags not in {0, 0x800}
            or method not in {SOURCE_ZIP_METHOD, CANONICAL_ZIP_METHOD}
            or modified_time != expected_time
            or modified_date != expected_date
            or compressed_size > MAX_ARTIFACT_BYTES
            or file_size == 0xFFFFFFFF
            or compressed_size == 0xFFFFFFFF
            or volume
            or internal_attr
            or local_offset >= directory_offset
        ):
            raise ValueError("wheel source central record is outside the finite build allowlist")
        encoded_name = raw[offset + 46 : offset + 46 + name_size]
        try:
            name = encoded_name.decode("utf-8" if flags else "ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("wheel source central filename is invalid") from exc
        expected_flags = 0x800 if not name.isascii() else 0
        system, version = made_by >> 8, made_by & 0xFF
        mode_key = "record" if name.endswith(".dist-info/RECORD") else "ordinary"
        expected_mode = SOURCE_WHEEL_MODES.get(system, {}).get(mode_key)
        normalized = safe_release_name(name).as_posix()
        alias = _portable_alias(normalized)
        if (
            version != CANONICAL_ZIP_VERSION
            or flags != expected_flags
            or expected_mode is None
            or external_attr != expected_mode << 16
            or (method == CANONICAL_ZIP_METHOD and system != CANONICAL_ZIP_SYSTEM)
            or (method == CANONICAL_ZIP_METHOD and compressed_size != file_size)
        ):
            raise ValueError("wheel source central record is outside the finite build allowlist")
        if alias in aliases:
            raise ValueError(f"wheel contains a duplicate or aliasing member: {normalized}")
        aliases.add(alias)
        names.append(normalized)
        methods.add(method)
        total = _member_budget(
            count=count,
            size=file_size,
            total=total,
            artifact="wheel",
        )
        if (
            method == SOURCE_ZIP_METHOD
            and file_size
            and (compressed_size <= 0 or file_size / compressed_size > MAX_ZIP_COMPRESSION_RATIO)
        ):
            raise ValueError(f"wheel member exceeds the compression ratio limit: {name}")
        offset = end
    if offset != eocd:
        raise ValueError("wheel central directory contains an unknown record or count mismatch")
    if len(methods) != 1 or (expected_method is not None and methods != {expected_method}):
        raise ValueError("wheel members must use one canonical compression method")
    if require_sorted and names != sorted(names):
        raise ValueError("canonical wheel members are not in sorted order")
    for name in names:
        parts = PurePosixPath(_portable_alias(name)).parts
        if any(
            PurePosixPath(*parts[:index]).as_posix() in aliases for index in range(1, len(parts))
        ):
            raise ValueError(f"wheel contains a file-prefix collision: {name}")


def _encoded_zip_name(item: zipfile.ZipInfo) -> bytes:
    expected_flag = 0x800 if not item.filename.isascii() else 0
    if item.flag_bits != expected_flag:
        raise ValueError(f"wheel filename encoding flag is noncanonical: {item.filename}")
    return item.filename.encode("utf-8" if expected_flag else "ascii")


def _validate_source_zip_info(
    item: zipfile.ZipInfo,
    *,
    timestamp: tuple[int, int, int, int, int, int],
) -> None:
    name = safe_release_name(item.filename).as_posix()
    if name != item.filename or item.is_dir():
        raise ValueError(f"wheel contains a noncanonical file name: {item.filename}")
    is_record = item.filename.endswith(".dist-info/RECORD")
    mode_key = "record" if is_record else "ordinary"
    expected_mode = SOURCE_WHEEL_MODES.get(item.create_system, {}).get(mode_key)
    if (
        expected_mode is None
        or item.create_version != CANONICAL_ZIP_VERSION
        or item.extract_version != CANONICAL_ZIP_VERSION
        or item.reserved != 0
        or item.compress_type not in {SOURCE_ZIP_METHOD, CANONICAL_ZIP_METHOD}
        or item.date_time != timestamp
        or item.volume != 0
        or item.internal_attr != 0
        or item.external_attr != expected_mode << 16
        or item.extra
        or item.comment
        or (
            item.compress_type == CANONICAL_ZIP_METHOD
            and (item.create_system != CANONICAL_ZIP_SYSTEM or item.compress_size != item.file_size)
        )
    ):
        raise ValueError(
            f"wheel source header is outside the finite build allowlist: {item.filename}"
        )
    _encoded_zip_name(item)
    if (
        item.compress_type == SOURCE_ZIP_METHOD
        and item.file_size
        and (
            item.compress_size <= 0
            or item.file_size / item.compress_size > MAX_ZIP_COMPRESSION_RATIO
        )
    ):
        raise ValueError(f"wheel member exceeds the compression ratio limit: {item.filename}")


def _validate_zip_central_records(
    raw: bytes,
    infos: list[zipfile.ZipInfo],
    *,
    directory_offset: int,
    eocd: int,
) -> None:
    offset = directory_offset
    for item in infos:
        if offset + 46 > eocd or raw[offset : offset + 4] != b"PK\x01\x02":
            raise ValueError("wheel central directory contains an unknown record or gap")
        (
            made_by,
            extract,
            flags,
            method,
            modified_time,
            modified_date,
            crc,
            compressed_size,
            file_size,
            name_size,
            extra_size,
            comment_size,
            volume,
            internal_attr,
            external_attr,
            local_offset,
        ) = struct.unpack_from("<6H3L5H2L", raw, offset + 4)
        end = offset + 46 + name_size + extra_size + comment_size
        encoded_name = raw[offset + 46 : offset + 46 + name_size]
        year, month, day, hour, minute, second = item.date_time
        dos_time = (hour << 11) | (minute << 5) | second // 2
        dos_date = ((year - 1980) << 9) | (month << 5) | day
        if (
            end > eocd
            or made_by != (item.create_system << 8) | item.create_version
            or extract != (item.reserved << 8) | item.extract_version
            or flags != item.flag_bits
            or method != item.compress_type
            or modified_time != dos_time
            or modified_date != dos_date
            or crc != item.CRC
            or compressed_size != item.compress_size
            or file_size != item.file_size
            or encoded_name != _encoded_zip_name(item)
            or extra_size
            or comment_size
            or volume != item.volume
            or internal_attr != item.internal_attr
            or external_attr != item.external_attr
            or local_offset != item.header_offset
        ):
            raise ValueError(f"wheel central record is noncanonical: {item.filename}")
        offset = end
    if offset != eocd:
        raise ValueError("wheel central directory contains an unknown record or gap")


def _validate_zip_local_records(
    raw: bytes,
    infos: list[zipfile.ZipInfo],
    *,
    directory_offset: int,
) -> None:
    expected_offset = 0
    for item in infos:
        offset = item.header_offset
        if offset != expected_offset or offset + 30 > directory_offset:
            raise ValueError("wheel local records contain a prefix, gap, or overlap")
        (
            extract,
            flags,
            method,
            modified_time,
            modified_date,
            crc,
            compressed_size,
            file_size,
            name_size,
            extra_size,
        ) = struct.unpack_from("<5H3L2H", raw, offset + 4)
        name_start = offset + 30
        data_start = name_start + name_size + extra_size
        data_end = data_start + compressed_size
        year, month, day, hour, minute, second = item.date_time
        dos_time = (hour << 11) | (minute << 5) | second // 2
        dos_date = ((year - 1980) << 9) | (month << 5) | day
        if (
            raw[offset : offset + 4] != b"PK\x03\x04"
            or data_end > directory_offset
            or extract != (item.reserved << 8) | item.extract_version
            or flags != item.flag_bits
            or method != item.compress_type
            or modified_time != dos_time
            or modified_date != dos_date
            or crc != item.CRC
            or compressed_size != item.compress_size
            or file_size != item.file_size
            or raw[name_start : name_start + name_size] != _encoded_zip_name(item)
            or extra_size
        ):
            raise ValueError(f"wheel local record is noncanonical: {item.filename}")
        if item.compress_type == SOURCE_ZIP_METHOD:
            _require_exact_deflate(
                raw[data_start:data_end],
                size=item.file_size,
                name=item.filename,
            )
        elif compressed_size != file_size:
            raise ValueError(f"wheel stored member has a noncanonical size: {item.filename}")
        expected_offset = data_end
    if expected_offset != directory_offset:
        raise ValueError("wheel local records contain a prefix, gap, or overlap")


def _canonical_wheel_payload(
    entries: list[tuple[str, bytes]],
    *,
    timestamp: tuple[int, int, int, int, int, int],
) -> bytes:
    year, month, day, hour, minute, second = timestamp
    dos_time = (hour << 11) | (minute << 5) | second // 2
    dos_date = ((year - 1980) << 9) | (month << 5) | day
    local_records = bytearray()
    central_records = bytearray()
    for name, payload in sorted(entries):
        encoded_name = name.encode("utf-8" if not name.isascii() else "ascii")
        flags = 0x800 if not name.isascii() else 0
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        offset = len(local_records)
        local_records.extend(
            struct.pack(
                "<I5H3L2H",
                0x04034B50,
                CANONICAL_ZIP_VERSION,
                flags,
                CANONICAL_ZIP_METHOD,
                dos_time,
                dos_date,
                crc,
                len(payload),
                len(payload),
                len(encoded_name),
                0,
            )
        )
        local_records.extend(encoded_name)
        local_records.extend(payload)
        mode = CANONICAL_RECORD_MODE if name.endswith(".dist-info/RECORD") else CANONICAL_WHEEL_MODE
        central_records.extend(
            struct.pack(
                "<I6H3L5H2L",
                0x02014B50,
                (CANONICAL_ZIP_SYSTEM << 8) | CANONICAL_ZIP_VERSION,
                CANONICAL_ZIP_VERSION,
                flags,
                CANONICAL_ZIP_METHOD,
                dos_time,
                dos_date,
                crc,
                len(payload),
                len(payload),
                len(encoded_name),
                0,
                0,
                0,
                0,
                mode << 16,
                offset,
            )
        )
        central_records.extend(encoded_name)
    directory_offset = len(local_records)
    member_count = len(entries)
    return bytes(
        local_records
        + central_records
        + struct.pack(
            "<I4H2LH",
            0x06054B50,
            0,
            0,
            member_count,
            member_count,
            len(central_records),
            directory_offset,
            0,
        )
    )


def _wheel_generated_relative(name: str) -> str | None:
    parts = PurePosixPath(name).parts
    if len(parts) == 2 and parts[0].endswith(".dist-info"):
        return parts[1]
    return None


def _canonical_lf_text(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _canonical_wheel_record_payload(
    record_name: str,
    payloads: dict[str, bytes],
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    for name in sorted(set(payloads) - {record_name}):
        digest = base64.urlsafe_b64encode(hashlib.sha256(payloads[name]).digest()).rstrip(b"=")
        writer.writerow((name, f"sha256={digest.decode('ascii')}", str(len(payloads[name]))))
    writer.writerow((record_name, "", ""))
    return output.getvalue().encode("utf-8")


def _canonical_wheel_entries(entries: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    payloads = {
        name: (
            _canonical_lf_text(payload)
            if _wheel_generated_relative(name) in CANONICAL_LF_WHEEL_GENERATED_FILES
            else payload
        )
        for name, payload in entries
    }
    record_names = sorted(name for name in payloads if _wheel_generated_relative(name) == "RECORD")
    if len(record_names) > 1:
        raise ValueError("wheel source contains more than one generated RECORD")
    if record_names:
        record_name = record_names[0]
        payloads[record_name] = _canonical_wheel_record_payload(record_name, payloads)
    return sorted(payloads.items())


def canonicalize_wheel_bytes(raw: bytes, *, timestamp: int) -> bytes:
    """Return one deterministic wheel container after bounded source validation."""

    expected_timestamp = _canonical_zip_timestamp(timestamp)
    directory_offset, eocd, expected_members = _zip_directory_contract(raw)
    _preflight_source_zip_records(
        raw,
        directory_offset=directory_offset,
        eocd=eocd,
        members=expected_members,
        timestamp=expected_timestamp,
    )
    entries: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as archive:
            infos = archive.infolist()
            if len(infos) != expected_members or archive.start_dir != directory_offset:
                raise ValueError("wheel central directory contract is invalid")
            _validate_zip_central_records(
                raw,
                infos,
                directory_offset=directory_offset,
                eocd=eocd,
            )
            for item in infos:
                _validate_source_zip_info(item, timestamp=expected_timestamp)
            _validate_zip_local_records(raw, infos, directory_offset=directory_offset)
            for item in infos:
                normalized = safe_release_name(item.filename).as_posix()
                entries.append((normalized, _read_zip_member(archive, item)))
    except (NotImplementedError, RuntimeError, zipfile.BadZipFile, zlib.error) as exc:
        raise ValueError("wheel source container is invalid") from exc

    canonical = _canonical_wheel_payload(
        _canonical_wheel_entries(entries),
        timestamp=expected_timestamp,
    )
    if len(canonical) > MAX_ARTIFACT_BYTES:
        raise ValueError("canonical wheel exceeds the artifact size limit")
    canonical_offset, canonical_eocd, canonical_members = _zip_directory_contract(canonical)
    _preflight_source_zip_records(
        canonical,
        directory_offset=canonical_offset,
        eocd=canonical_eocd,
        members=canonical_members,
        timestamp=expected_timestamp,
        require_sorted=True,
        expected_method=CANONICAL_ZIP_METHOD,
    )
    return canonical


def _stored_gzip_payload(
    raw: bytes,
    *,
    payload_start: int,
    maximum_payload: int,
) -> bytes:
    trailer_start = len(raw) - 8
    if payload_start >= trailer_start:
        raise ValueError("sdist source stored gzip stream is truncated")
    payload = bytearray()
    cursor = payload_start
    final = False
    while cursor < trailer_start:
        marker = raw[cursor]
        cursor += 1
        if marker not in {0, 1} or cursor + 4 > trailer_start:
            raise ValueError("sdist source stored gzip block header is noncanonical")
        block_size, inverse_size = struct.unpack_from("<HH", raw, cursor)
        cursor += 4
        if inverse_size != (~block_size & 0xFFFF):
            raise ValueError("sdist source stored gzip block length is invalid")
        block_end = cursor + block_size
        if block_end > trailer_start:
            raise ValueError("sdist source stored gzip block exceeds its boundary")
        final = marker == 1
        if (not final and block_size != 65_535) or (final and not block_size and payload):
            raise ValueError("sdist source stored gzip segmentation is noncanonical")
        payload.extend(raw[cursor:block_end])
        if len(payload) > maximum_payload:
            raise ValueError("sdist source gzip stream exceeds its exact boundary")
        cursor = block_end
        if final:
            break
    if not final or cursor != trailer_start:
        raise ValueError("sdist source stored gzip stream has trailing or missing blocks")
    expected_crc, expected_size = struct.unpack_from("<LL", raw, trailer_start)
    if expected_crc != zlib.crc32(payload) & 0xFFFFFFFF or expected_size != len(payload):
        raise ValueError("sdist source stored gzip trailer is invalid")
    return bytes(payload)


def _gzip_tar_payload(raw: bytes, *, expected_filename: str) -> bytes:
    if (
        len(raw) < 11
        or len(raw) > MAX_ARTIFACT_BYTES
        or raw[:4] != b"\x1f\x8b\x08\x08"
        or raw[8] not in {0, 2}
        or raw[9] != 255
    ):
        raise ValueError("sdist source gzip header is invalid")
    terminator = raw.find(b"\0", 10, 266)
    if terminator < 0:
        raise ValueError("sdist source gzip filename is invalid")
    try:
        filename = raw[10:terminator].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("sdist source gzip filename is invalid") from exc
    if filename != expected_filename:
        raise ValueError("sdist source gzip filename does not match the artifact")
    maximum_payload = min(MAX_TAR_CONTAINER_BYTES, len(raw) * MAX_ZIP_COMPRESSION_RATIO)
    if raw[8] == 0:
        return _stored_gzip_payload(
            raw,
            payload_start=terminator + 1,
            maximum_payload=maximum_payload,
        )
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    payload = bytearray()
    cursor = 0
    try:
        while cursor < len(raw):
            chunk = raw[cursor : cursor + READ_CHUNK_BYTES]
            cursor += len(chunk)
            payload.extend(
                decompressor.decompress(
                    chunk,
                    max(1, maximum_payload + 1 - len(payload)),
                )
            )
            if (
                len(payload) > maximum_payload
                or decompressor.unconsumed_tail
                or (decompressor.eof and cursor < len(raw))
            ):
                raise ValueError("sdist source gzip stream exceeds its exact boundary")
        payload.extend(decompressor.flush(max(1, maximum_payload + 1 - len(payload))))
    except zlib.error as exc:
        raise ValueError("sdist source gzip stream is invalid") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or len(payload) > maximum_payload
    ):
        raise ValueError("sdist source gzip stream is invalid")
    return bytes(payload)


def _canonical_stored_gzip(
    payload: bytes,
    *,
    filename: str,
    timestamp: int,
) -> bytes:
    encoded_filename = filename.encode("ascii")
    output = bytearray(
        b"\x1f\x8b\x08\x08" + struct.pack("<L", timestamp) + b"\x00\xff" + encoded_filename + b"\0"
    )
    if not payload:
        output.extend(b"\x01\x00\x00\xff\xff")
    else:
        view = memoryview(payload)
        for offset in range(0, len(payload), 65_535):
            chunk = view[offset : offset + 65_535]
            final = offset + len(chunk) == len(payload)
            output.append(1 if final else 0)
            output.extend(struct.pack("<HH", len(chunk), ~len(chunk) & 0xFFFF))
            output.extend(chunk)
    output.extend(struct.pack("<LL", zlib.crc32(payload) & 0xFFFFFFFF, len(payload)))
    return bytes(output)


def _canonical_octal(field: bytes, *, label: str) -> int:
    if len(field) < 2 or field[-1:] != b"\0" or re.fullmatch(rb"[0-7]+", field[:-1]) is None:
        raise ValueError(f"sdist source tar {label} field is noncanonical")
    return int(field[:-1], 8)


def _nul_padded(field: bytes, *, label: str, allow_empty: bool) -> bytes:
    value, marker, padding = field.partition(b"\0")
    if not marker or any(padding) or (not allow_empty and not value):
        raise ValueError(f"sdist source tar {label} field is noncanonical")
    return value


def _parse_pax_payload(payload: bytes) -> dict[str, str]:
    records: dict[str, str] = {}
    offset = 0
    while offset < len(payload):
        match = _PAX_RECORD.match(payload, offset)
        if match is None:
            raise ValueError("sdist source PAX payload is malformed")
        encoded_length, encoded_key, encoded_value = match.groups()
        length = int(encoded_length)
        end = offset + length
        if end != match.end() or str(length).encode("ascii") != encoded_length:
            raise ValueError("sdist source PAX record length is noncanonical")
        try:
            key = encoded_key.decode("ascii")
            value = encoded_value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("sdist source PAX text is invalid") from exc
        if key not in {"mtime", "path"} or key in records:
            raise ValueError("sdist source PAX keys are unsupported or duplicated")
        records[key] = value
        offset = end
    return records


def _source_tar_name(field: bytes, *, pax_path: str | None) -> bytes:
    if pax_path is None:
        value = field if b"\0" not in field else _nul_padded(field, label="name", allow_empty=False)
        try:
            value.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("sdist source tar name must use portable ASCII") from exc
        return value
    placeholder = pax_path.encode("ascii", errors="replace")[: len(field)]
    expected = placeholder + (b"\0" * (len(field) - len(placeholder)))
    if field != expected:
        raise ValueError("sdist source tar PAX base name is noncanonical")
    return placeholder


def _validate_source_tar_header(
    header: bytes,
    *,
    pax_path: str | None = None,
) -> tuple[int, bytes, int]:
    if len(header) != tarfile.BLOCKSIZE:
        raise ValueError("sdist source tar header is truncated")
    checksum_field = header[148:156]
    if re.fullmatch(rb"[0-7]{6}\0 ", checksum_field) is None:
        raise ValueError("sdist source tar checksum spelling is noncanonical")
    expected_checksum = int(checksum_field[:6], 8)
    observed_checksum = sum(header[:148]) + (8 * ord(" ")) + sum(header[156:])
    if observed_checksum != expected_checksum:
        raise ValueError("sdist source tar checksum is invalid")
    _source_tar_name(header[0:100], pax_path=pax_path)
    _canonical_octal(header[100:108], label="mode")
    _canonical_octal(header[108:116], label="uid")
    _canonical_octal(header[116:124], label="gid")
    size = _canonical_octal(header[124:136], label="size")
    modified = _canonical_octal(header[136:148], label="mtime")
    member_type = header[156:157]
    if member_type not in {tarfile.REGTYPE, tarfile.DIRTYPE, tarfile.XHDTYPE}:
        raise ValueError("sdist source tar member type is unsupported")
    if (
        any(header[157:257])
        or header[257:263] != b"ustar\0"
        or header[263:265] != b"00"
        or any(header[329:345])
        or any(header[345:512])
    ):
        raise ValueError("sdist source tar reserved fields are noncanonical")
    _nul_padded(header[265:297], label="uname", allow_empty=True)
    _nul_padded(header[297:329], label="gname", allow_empty=True)
    if member_type == tarfile.XHDTYPE and (
        header[:100].split(b"\0", 1)[0] != b"././@PaxHeader"
        or _canonical_octal(header[100:108], label="mode")
        or _canonical_octal(header[108:116], label="uid")
        or _canonical_octal(header[116:124], label="gid")
        or modified
        or any(header[265:329])
    ):
        raise ValueError("sdist source PAX tar header is noncanonical")
    return size, member_type, modified


def _validate_source_pax_records(
    records: dict[str, str],
    *,
    raw_mtime: int,
) -> None:
    if set(records) not in ({"mtime"}, {"path"}, {"mtime", "path"}):
        raise ValueError("sdist source PAX topology is noncanonical")
    path = records.get("path")
    if path is not None:
        safe_release_name(path[:-1] if path.endswith("/") else path)
    encoded_mtime = records.get("mtime")
    if encoded_mtime is None:
        return
    if (
        len(encoded_mtime) > 32
        or re.fullmatch(
            r"(?:0|[1-9][0-9]*)(?:\.(?:0|[0-9]*[1-9]))?",
            encoded_mtime,
        )
        is None
    ):
        raise ValueError("sdist source PAX mtime is noncanonical")
    pax_mtime = Decimal(encoded_mtime)
    # ``tarfile.PAX_FORMAT`` preserves a float mtime in the extended
    # header, but writes its nearest-even integer into the adjacent USTAR
    # header.  Directory mtimes created during a Windows build commonly have
    # sub-second values above .5, so truncation rejects valid setuptools
    # output.  Decimal keeps this source-container check exact and independent
    # of the host float implementation.
    header_mtime = int(pax_mtime.to_integral_value(rounding=ROUND_HALF_EVEN))
    if header_mtime != raw_mtime:
        raise ValueError("sdist source PAX mtime differs from its tar header")


def _validate_source_tar_layout(payload: bytes) -> None:
    if not payload or len(payload) % 10_240:
        raise ValueError("sdist source tar length is noncanonical")
    offset = 0
    pending_pax: dict[str, str] | None = None
    member_count = 0
    total_size = 0
    while offset + tarfile.BLOCKSIZE <= len(payload):
        header = payload[offset : offset + tarfile.BLOCKSIZE]
        if header == _ZERO_BLOCK:
            if payload[offset + 512 : offset + 1_024] != _ZERO_BLOCK:
                raise ValueError("sdist source tar end marker is invalid")
            if any(payload[offset + 1_024 :]):
                raise ValueError("sdist source tar contains nonzero trailing data")
            if pending_pax is not None:
                raise ValueError("sdist source tar contains an orphan PAX header")
            canonical_length = ((offset + 1_024 + 10_239) // 10_240) * 10_240
            if canonical_length != len(payload):
                raise ValueError("sdist source tar zero padding is noncanonical")
            return
        size, member_type, modified = _validate_source_tar_header(
            header,
            pax_path=None if pending_pax is None else pending_pax.get("path"),
        )
        data_start = offset + 512
        data_end = data_start + size
        next_offset = data_start + ((size + 511) // 512) * 512
        if next_offset > len(payload) or any(payload[data_end:next_offset]):
            raise ValueError("sdist source tar member boundary is invalid")
        if member_type == tarfile.XHDTYPE:
            if pending_pax is not None or size > 64 * 1_024:
                raise ValueError("sdist source PAX header boundary is invalid")
            pending_pax = _parse_pax_payload(payload[data_start:data_end])
        else:
            member_count += 1
            total_size = _member_budget(
                count=member_count,
                size=size if member_type == tarfile.REGTYPE else 0,
                total=total_size,
                artifact="sdist",
            )
            if pending_pax is not None:
                _validate_source_pax_records(pending_pax, raw_mtime=modified)
            pending_pax = None
        offset = next_offset
    raise ValueError("sdist source tar end marker is missing")


def _read_tar_member(archive: tarfile.TarFile, item: tarfile.TarInfo) -> bytes:
    extracted = archive.extractfile(item)
    if extracted is None:
        raise ValueError(f"sdist member could not be read: {item.name}")
    chunks: list[bytes] = []
    observed = 0
    with extracted:
        while True:
            chunk = extracted.read(min(READ_CHUNK_BYTES, item.size + 1 - observed))
            if not chunk:
                break
            observed += len(chunk)
            if observed > item.size:
                raise ValueError(f"sdist member exceeds its declared size: {item.name}")
            chunks.append(chunk)
    if observed != item.size:
        raise ValueError(f"sdist member is shorter than its declared size: {item.name}")
    return b"".join(chunks)


def _source_tar_entries(payload: bytes) -> list[_TarEntry]:
    entries: list[_TarEntry] = []
    seen: set[str] = set()
    aliases: set[str] = set()
    total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            if archive.pax_headers:
                raise ValueError("sdist source contains global PAX state")
            for count, item in enumerate(archive, start=1):
                if item.type not in {tarfile.REGTYPE, tarfile.DIRTYPE}:
                    raise ValueError(f"sdist source contains an unsupported member: {item.name}")
                if set(item.pax_headers) - {"mtime", "path"}:
                    raise ValueError(f"sdist source contains unsupported PAX state: {item.name}")
                if (
                    item.uid < 0
                    or item.gid < 0
                    or item.uid > 0o7777777
                    or item.gid > 0o7777777
                    or item.devmajor
                    or item.devminor
                    or any(
                        len(value.encode("ascii", errors="strict")) > 31
                        or any(ord(character) < 32 or ord(character) > 126 for character in value)
                        for value in (item.uname, item.gname)
                    )
                ):
                    raise ValueError(f"sdist source owner metadata is invalid: {item.name}")
                path = safe_release_name(item.name)
                canonical = path.as_posix()
                alias = _portable_alias(canonical)
                if canonical in seen or alias in aliases:
                    raise ValueError(f"sdist source contains a duplicate member: {canonical}")
                seen.add(canonical)
                aliases.add(alias)
                if item.isdir():
                    if item.size or item.mode not in SOURCE_TAR_DIRECTORY_MODES:
                        raise ValueError(
                            f"sdist source directory header is outside the build allowlist: {item.name}"
                        )
                    entry = _TarEntry(canonical, None)
                    size = 0
                else:
                    if not _source_tar_file_mode_allowed(canonical, item.mode):
                        raise ValueError(
                            f"sdist source file header is outside the build allowlist: {item.name}"
                        )
                    size = item.size
                    entry = _TarEntry(canonical, b"")
                total = _member_budget(
                    count=count,
                    size=size,
                    total=total,
                    artifact="sdist",
                )
                if not item.isdir():
                    entry = _TarEntry(canonical, _read_tar_member(archive, item))
                entries.append(entry)
    except (tarfile.TarError, UnicodeError) as exc:
        raise ValueError("sdist source tar container is invalid") from exc
    files = {entry.name for entry in entries if not entry.is_directory}
    directories = {entry.name for entry in entries if entry.is_directory}
    roots = {PurePosixPath(entry.name).parts[0] for entry in entries}
    required_directories = {
        PurePosixPath(*parts[:index]).as_posix()
        for name in files
        for parts in (PurePosixPath(name).parts,)
        for index in range(1, len(parts))
    }
    if len(roots) != 1 or directories != required_directories:
        raise ValueError("sdist source directory topology is noncanonical")
    normalized: list[_TarEntry] = []
    for entry in entries:
        parts = PurePosixPath(entry.name).parts
        relative = PurePosixPath(*parts[1:]).as_posix()
        if (
            not entry.is_directory
            and relative in CANONICAL_LF_SDIST_GENERATED_FILES
            and entry.payload is not None
        ):
            normalized.append(_TarEntry(entry.name, _canonical_lf_text(entry.payload)))
        else:
            normalized.append(entry)
    return normalized


def _tar_octal(value: int, width: int) -> bytes:
    encoded = f"{value:0{width - 1}o}".encode("ascii")
    if len(encoded) != width - 1:
        raise ValueError("canonical tar numeric field exceeds its fixed-width boundary")
    return encoded + b"\0"


def _pax_path_record(path: str) -> bytes:
    body = b" path=" + path.encode("utf-8") + b"\n"
    length = len(body) + 1
    while len(str(length)) + len(body) != length:
        length = len(str(length)) + len(body)
    return str(length).encode("ascii") + body


def _canonical_tar_header(
    name: bytes,
    *,
    mode: int,
    size: int,
    modified: int,
    member_type: bytes,
) -> bytes:
    if not 0 < len(name) <= 100:
        raise ValueError("canonical tar name exceeds its fixed-width boundary")
    header = bytearray(tarfile.BLOCKSIZE)
    header[: len(name)] = name
    header[100:108] = _tar_octal(mode, 8)
    header[108:116] = _tar_octal(0, 8)
    header[116:124] = _tar_octal(0, 8)
    header[124:136] = _tar_octal(size, 12)
    header[136:148] = _tar_octal(modified, 12)
    header[148:156] = b"        "
    header[156:157] = member_type
    header[257:263] = b"ustar\0"
    header[263:265] = b"00"
    checksum = sum(header)
    header[148:156] = f"{checksum:06o}\0 ".encode("ascii")
    return bytes(header)


def _canonical_tar_payload(entries: list[_TarEntry], *, timestamp: int) -> bytes:
    output = bytearray()
    for entry in sorted(entries, key=lambda candidate: candidate.name):
        path = f"{entry.name}/" if entry.is_directory else entry.name
        encoded_path = path.encode("utf-8")
        needs_pax = not path.isascii() or len(encoded_path) > 100
        if needs_pax:
            pax_payload = _pax_path_record(path)
            output.extend(
                _canonical_tar_header(
                    b"././@PaxHeader",
                    mode=0,
                    size=len(pax_payload),
                    modified=0,
                    member_type=tarfile.XHDTYPE,
                )
            )
            output.extend(pax_payload)
            output.extend(b"\0" * (-len(pax_payload) % tarfile.BLOCKSIZE))
            encoded_name = path.encode("ascii", errors="replace")[:100]
        else:
            encoded_name = encoded_path
        payload = b"" if entry.is_directory else entry.payload or b""
        output.extend(
            _canonical_tar_header(
                encoded_name,
                mode=0o755 if entry.is_directory else 0o644,
                size=len(payload),
                modified=timestamp,
                member_type=tarfile.DIRTYPE if entry.is_directory else tarfile.REGTYPE,
            )
        )
        output.extend(payload)
        output.extend(b"\0" * (-len(payload) % tarfile.BLOCKSIZE))
    output.extend(b"\0" * (2 * tarfile.BLOCKSIZE))
    output.extend(b"\0" * (-len(output) % 10_240))
    return bytes(output)


def canonicalize_sdist_bytes(
    raw: bytes,
    *,
    timestamp: int,
    expected_filename: str,
) -> bytes:
    """Return one deterministic PAX sdist after bounded source validation."""

    _canonical_zip_timestamp(timestamp)
    tar_payload = _gzip_tar_payload(raw, expected_filename=expected_filename[:-3])
    _validate_source_tar_layout(tar_payload)
    entries = _source_tar_entries(tar_payload)

    canonical_tar = _canonical_tar_payload(entries, timestamp=timestamp)
    if len(canonical_tar) > MAX_TAR_CONTAINER_BYTES:
        raise ValueError("canonical sdist tar exceeds its container size limit")

    canonical = _canonical_stored_gzip(
        canonical_tar,
        filename=expected_filename[:-3],
        timestamp=timestamp,
    )
    if (
        len(canonical) > MAX_ARTIFACT_BYTES
        or len(canonical_tar) > len(canonical) * MAX_ZIP_COMPRESSION_RATIO
    ):
        raise ValueError("canonical sdist exceeds its compressed artifact limits")
    return canonical


def canonicalize_distributions(
    wheel: Path,
    sdist: Path,
    *,
    timestamp: int,
) -> None:
    """Replace two validated outputs inside the builder's unpublished staging namespace."""

    wheel_payload = canonicalize_wheel_bytes(
        _read_bounded_regular_file(wheel),
        timestamp=timestamp,
    )
    sdist_payload = canonicalize_sdist_bytes(
        _read_bounded_regular_file(sdist),
        timestamp=timestamp,
        expected_filename=sdist.name,
    )
    _replace_regular_file(wheel, wheel_payload)
    _replace_regular_file(sdist, sdist_payload)
