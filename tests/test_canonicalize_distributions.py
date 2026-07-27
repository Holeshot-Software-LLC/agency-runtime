"""Deterministic archive normalization and adversarial ingestion contracts."""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import stat
import struct
import tarfile
import time
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import canonicalize_distributions as subject
from scripts import verify_distribution as verifier
from tests.test_distribution_verifier_hardening import (
    _artifact_timestamp,
    _artifacts,
    _fake_stat,
    _repository,
)

TIMESTAMP = 1_700_000_000


def _zip_time(timestamp: int = TIMESTAMP) -> tuple[int, int, int, int, int, int]:
    year, month, day, hour, minute, second = time.gmtime(timestamp)[:6]
    return year, month, day, hour, minute, second - second % 2


def _source_wheel(
    entries: dict[str, bytes],
    *,
    system: int = 3,
    timestamp: int = TIMESTAMP,
    ordinary_mode: int | None = None,
    ordinary_type: int = stat.S_IFREG,
    ordinary_low_bits: int = 0,
    record_mode: int = 0o664,
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries.items():
            item = zipfile.ZipInfo(name, _zip_time(timestamp))
            item.create_system = system
            item.create_version = subject.CANONICAL_ZIP_VERSION
            item.extract_version = subject.CANONICAL_ZIP_VERSION
            item.compress_type = zipfile.ZIP_DEFLATED
            if name.endswith(".dist-info/RECORD"):
                mode = stat.S_IFREG | record_mode
                low_bits = 0
            else:
                mode = ordinary_type | (
                    ordinary_mode
                    if ordinary_mode is not None
                    else (0o666 if system == 0 else 0o644)
                )
                low_bits = ordinary_low_bits
            item.external_attr = (mode << 16) | low_bits
            archive.writestr(item, payload)
    return output.getvalue()


def _source_sdist(
    entries: dict[str, bytes | None],
    *,
    windows: bool = False,
    timestamp: int = TIMESTAMP,
    fractional_pax: bool = False,
    rounded_fractional_mtime: bool = False,
    filename: str = "package-1.tar",
    file_modes: dict[str, int] | None = None,
) -> bytes:
    tar_payload = io.BytesIO()
    with tarfile.open(fileobj=tar_payload, mode="w:", format=tarfile.PAX_FORMAT) as archive:
        for name, payload in entries.items():
            directory = payload is None
            item = tarfile.TarInfo(f"{name}/" if directory else name)
            item.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
            default_mode = (
                (0o777 if windows else 0o755) if directory else (0o666 if windows else 0o644)
            )
            item.mode = (file_modes or {}).get(name, default_mode)
            item.uid = 0 if windows else 1000
            item.gid = 0 if windows else 1000
            item.uname = "" if windows else "builder"
            item.gname = "" if windows else "builder"
            item.mtime = timestamp + 0.75 if rounded_fractional_mtime else timestamp
            if fractional_pax:
                item.pax_headers = {"mtime": f"{timestamp}.25"}
            item.size = 0 if directory else len(payload or b"")
            archive.addfile(item, None if directory else io.BytesIO(payload or b""))
    output = io.BytesIO()
    with gzip.GzipFile(
        filename=filename,
        mode="wb",
        fileobj=output,
        compresslevel=9,
        mtime=timestamp + 20,
    ) as archive:
        archive.write(tar_payload.getvalue())
    return output.getvalue()


def _basic_wheel() -> bytes:
    return _source_wheel(
        {
            "package-1.dist-info/RECORD": b"record",
            "package/module.py": b"payload",
        }
    )


def _basic_sdist(*, windows: bool = False) -> bytes:
    return _source_sdist(
        {
            "package-1": None,
            "package-1/package": None,
            "package-1/package/module.py": b"payload",
        },
        windows=windows,
        fractional_pax=True,
    )


@pytest.mark.parametrize("system", [0, 3], ids=("windows", "linux"))
def test_wheel_normalization_is_platform_independent_and_idempotent(system: int) -> None:
    source = _source_wheel(
        {
            "package/module.py": b"payload",
            "package-1.dist-info/RECORD": b"record",
        },
        system=system,
    )

    canonical = subject.canonicalize_wheel_bytes(source, timestamp=TIMESTAMP)
    assert subject.canonicalize_wheel_bytes(canonical, timestamp=TIMESTAMP) == canonical

    with zipfile.ZipFile(io.BytesIO(canonical)) as archive:
        infos = archive.infolist()
    assert [item.filename for item in infos] == sorted(item.filename for item in infos)
    assert {
        (
            item.create_system,
            item.create_version,
            item.extract_version,
            item.flag_bits,
            item.compress_type,
            item.date_time,
            item.volume,
            item.internal_attr,
            item.external_attr,
        )
        for item in infos
    } == {
        (
            3,
            20,
            20,
            0,
            zipfile.ZIP_STORED,
            _zip_time(),
            0,
            0,
            (stat.S_IFREG | mode) << 16,
        )
        for mode in (0o644, 0o664)
    }


def test_wheel_normalization_accepts_owner_private_posix_source_modes() -> None:
    source = _source_wheel(
        {
            "package/private.py": b"private",
            "package-1.dist-info/RECORD": b"record",
        },
        ordinary_mode=0o600,
    )

    canonical = subject.canonicalize_wheel_bytes(source, timestamp=TIMESTAMP)

    with zipfile.ZipFile(io.BytesIO(canonical)) as archive:
        modes = {
            item.filename: stat.S_IMODE(item.external_attr >> 16) for item in archive.infolist()
        }
    assert modes == {
        "package-1.dist-info/RECORD": 0o664,
        "package/private.py": 0o644,
    }
    assert subject.canonicalize_wheel_bytes(canonical, timestamp=TIMESTAMP) == canonical


def test_owner_private_and_public_posix_source_modes_converge_exactly() -> None:
    entries = {
        "package/private.py": b"private",
        "package-1.dist-info/RECORD": b"record",
    }

    private = subject.canonicalize_wheel_bytes(
        _source_wheel(entries, ordinary_mode=0o600),
        timestamp=TIMESTAMP,
    )
    public = subject.canonicalize_wheel_bytes(
        _source_wheel(entries, ordinary_mode=0o644),
        timestamp=TIMESTAMP,
    )

    assert private == public


def test_windows_private_source_mode_remains_rejected() -> None:
    source = _source_wheel(
        {
            "package/private.py": b"private",
            "package-1.dist-info/RECORD": b"record",
        },
        system=0,
        ordinary_mode=0o600,
    )

    with pytest.raises(ValueError, match="finite build allowlist"):
        subject.canonicalize_wheel_bytes(source, timestamp=TIMESTAMP)


@pytest.mark.parametrize("record_mode", [0o600, 0o644])
def test_unreviewed_record_modes_remain_rejected(record_mode: int) -> None:
    source = _source_wheel(
        {
            "package/private.py": b"private",
            "package-1.dist-info/RECORD": b"record",
        },
        record_mode=record_mode,
    )

    with pytest.raises(ValueError, match="finite build allowlist"):
        subject.canonicalize_wheel_bytes(source, timestamp=TIMESTAMP)


@pytest.mark.parametrize(
    ("ordinary_type", "ordinary_mode", "ordinary_low_bits"),
    [
        (stat.S_IFREG, 0o400, 0),
        (stat.S_IFREG, 0o640, 0),
        (stat.S_IFREG, 0o700, 0),
        (stat.S_IFREG, 0o4700, 0),
        (stat.S_IFREG, 0o755, 0),
        (stat.S_IFREG, 0o777, 0),
        (stat.S_IFLNK, 0o600, 0),
        (stat.S_IFDIR, 0o600, 0),
        (stat.S_IFREG, 0o600, 1),
    ],
)
def test_wheel_normalization_rejects_unreviewed_posix_source_modes(
    ordinary_type: int,
    ordinary_mode: int,
    ordinary_low_bits: int,
) -> None:
    source = _source_wheel(
        {
            "package/private.py": b"private",
            "package-1.dist-info/RECORD": b"record",
        },
        ordinary_mode=ordinary_mode,
        ordinary_type=ordinary_type,
        ordinary_low_bits=ordinary_low_bits,
    )

    with pytest.raises(ValueError, match="finite build allowlist"):
        subject.canonicalize_wheel_bytes(source, timestamp=TIMESTAMP)


def test_zip_info_validation_rejects_special_posix_source_mode() -> None:
    raw = _source_wheel(
        {
            "package/private.py": b"private",
            "package-1.dist-info/RECORD": b"record",
        },
        ordinary_mode=0o600,
    )
    infos, _directory_offset, _eocd, _members = _wheel_views(raw)
    special = copy.copy(next(item for item in infos if item.filename == "package/private.py"))
    special.external_attr = (stat.S_IFLNK | 0o600) << 16

    with pytest.raises(ValueError, match="finite build allowlist"):
        subject._validate_source_zip_info(special, timestamp=_zip_time())


@pytest.mark.parametrize("windows", [False, True], ids=("linux", "windows"))
def test_sdist_normalization_scrubs_host_metadata_and_is_idempotent(windows: bool) -> None:
    source = _basic_sdist(windows=windows)

    canonical = subject.canonicalize_sdist_bytes(
        source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    assert (
        subject.canonicalize_sdist_bytes(
            canonical,
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )
        == canonical
    )
    assert int.from_bytes(canonical[4:8], "little") == TIMESTAMP
    with tarfile.open(fileobj=io.BytesIO(canonical), mode="r:gz") as archive:
        items = archive.getmembers()
    assert [item.name for item in items] == sorted(item.name for item in items)
    assert all(
        item.uid == item.gid == 0
        and item.uname == item.gname == ""
        and item.mtime == TIMESTAMP
        and item.mode == (0o755 if item.isdir() else 0o644)
        for item in items
    )


def test_windows_and_linux_sources_produce_identical_canonical_bytes() -> None:
    entries = {
        "package/module.py": b"payload",
        "package-1.dist-info/RECORD": b"record",
    }
    windows_wheel = subject.canonicalize_wheel_bytes(
        _source_wheel(entries, system=0),
        timestamp=TIMESTAMP,
    )
    linux_wheel = subject.canonicalize_wheel_bytes(
        _source_wheel(entries, system=3),
        timestamp=TIMESTAMP,
    )
    windows_sdist = subject.canonicalize_sdist_bytes(
        _basic_sdist(windows=True),
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    linux_sdist = subject.canonicalize_sdist_bytes(
        _basic_sdist(windows=False),
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )

    assert windows_wheel == linux_wheel
    assert windows_sdist == linux_sdist


def test_private_posix_sdist_modes_converge_with_public_modes() -> None:
    entries: dict[str, bytes | None] = {
        "package-1": None,
        "package-1/package": None,
        "package-1/package/module.py": b"payload",
    }
    private_source = _source_sdist(
        entries,
        file_modes={
            "package-1": 0o700,
            "package-1/package": 0o700,
            "package-1/package/module.py": 0o600,
        },
    )
    public_source = _source_sdist(entries)

    private_canonical = subject.canonicalize_sdist_bytes(
        private_source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    public_canonical = subject.canonicalize_sdist_bytes(
        public_source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )

    assert private_canonical == public_canonical
    with tarfile.open(fileobj=io.BytesIO(private_canonical), mode="r:gz") as archive:
        assert archive.getmember("package-1").mode == 0o755
        assert archive.getmember("package-1/package").mode == 0o755
        assert archive.getmember("package-1/package/module.py").mode == 0o644


@pytest.mark.parametrize(
    "mode",
    [0o000, 0o600, 0o644, 0o711, 0o750, 0o770, 0o775, 0o1700, 0o2700, 0o4700],
)
def test_sdist_rejects_unreviewed_directory_modes(mode: int) -> None:
    entries: dict[str, bytes | None] = {
        "package-1": None,
        "package-1/package": None,
        "package-1/package/module.py": b"payload",
    }
    with pytest.raises(ValueError, match="directory header"):
        subject.canonicalize_sdist_bytes(
            _source_sdist(entries, file_modes={"package-1": mode}),
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )


@pytest.mark.parametrize(
    "mode",
    [0o000, 0o400, 0o640, 0o700, 0o755, 0o1600, 0o2600, 0o4600, 0o4700, 0o777],
)
def test_sdist_rejects_unreviewed_regular_file_modes(mode: int) -> None:
    entries: dict[str, bytes | None] = {
        "package-1": None,
        "package-1/package": None,
        "package-1/package/module.py": b"payload",
    }
    with pytest.raises(ValueError, match="file header"):
        subject.canonicalize_sdist_bytes(
            _source_sdist(entries, file_modes={"package-1/package/module.py": mode}),
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )


def test_sdist_source_mode_allowlists_are_exact_across_all_permission_bits() -> None:
    ordinary = "package-1/package/module.py"
    executable = f"package-1/{subject.NATIVE_OPERATOR_PRESENCE_EXECUTABLE}"
    for mode in range(0o10000):
        assert subject._source_tar_file_mode_allowed(ordinary, mode) is (
            mode in {0o600, 0o644, 0o666}
        )
        assert subject._source_tar_file_mode_allowed(executable, mode) is (
            mode in {0o600, 0o644, 0o666, 0o777}
        )
        assert (mode in subject.SOURCE_TAR_DIRECTORY_MODES) is (mode in {0o700, 0o755, 0o777})


def test_sdist_normalizes_only_governed_windows_executable_mode() -> None:
    executable = f"package-1/{subject.NATIVE_OPERATOR_PRESENCE_EXECUTABLE}"
    parts = Path(executable).as_posix().split("/")
    entries: dict[str, bytes | None] = {
        "/".join(parts[:index]): None for index in range(1, len(parts))
    }
    entries[executable] = b"reviewed-pe"

    windows_source = _source_sdist(entries, windows=True, file_modes={executable: 0o777})
    linux_source = _source_sdist(entries, file_modes={executable: 0o644})
    windows_canonical = subject.canonicalize_sdist_bytes(
        windows_source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    linux_canonical = subject.canonicalize_sdist_bytes(
        linux_source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )

    assert windows_canonical == linux_canonical
    with tarfile.open(fileobj=io.BytesIO(windows_canonical), mode="r:gz") as archive:
        assert archive.getmember(executable).mode == 0o644

    arbitrary = "package-1/package/unreviewed.exe"
    bad_entries = {
        "package-1": None,
        "package-1/package": None,
        arbitrary: b"unreviewed",
    }
    with pytest.raises(ValueError, match="file header"):
        subject.canonicalize_sdist_bytes(
            _source_sdist(bad_entries, windows=True, file_modes={arbitrary: 0o777}),
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )


def test_generated_metadata_eol_variants_converge_without_mutating_source_payloads() -> None:
    record_name = "package-1.dist-info/RECORD"
    source_payload = b"source CRLF is reviewed and remains exact\r\n"

    def wheel_entries(eol: bytes) -> dict[str, bytes]:
        return {
            "package/module.py": source_payload,
            "package-1.dist-info/METADATA": b"Metadata-Version: 2.4" + eol + eol,
            "package-1.dist-info/WHEEL": b"Wheel-Version: 1.0" + eol,
            "package-1.dist-info/entry_points.txt": b"[console_scripts]" + eol,
            "package-1.dist-info/top_level.txt": b"package" + eol,
            record_name: b"backend-specific record" + eol,
        }

    windows_wheel = subject.canonicalize_wheel_bytes(
        _source_wheel(wheel_entries(b"\r\n"), system=0),
        timestamp=TIMESTAMP,
    )
    linux_wheel = subject.canonicalize_wheel_bytes(
        _source_wheel(wheel_entries(b"\n"), system=3),
        timestamp=TIMESTAMP,
    )
    assert windows_wheel == linux_wheel
    with zipfile.ZipFile(io.BytesIO(windows_wheel)) as archive:
        wheel_payloads = {item.filename: archive.read(item) for item in archive.infolist()}
    assert wheel_payloads["package/module.py"] == source_payload
    assert b"\r" not in wheel_payloads["package-1.dist-info/METADATA"]
    assert wheel_payloads[record_name] == subject._canonical_wheel_record_payload(
        record_name,
        wheel_payloads,
    )

    def sdist_entries(eol: bytes) -> dict[str, bytes | None]:
        return {
            "package-1": None,
            "package-1/agency_runtime.egg-info": None,
            "package-1/README.md": source_payload,
            "package-1/PKG-INFO": b"Metadata-Version: 2.4" + eol + eol,
            "package-1/agency_runtime.egg-info/PKG-INFO": (b"Metadata-Version: 2.4" + eol + eol),
            "package-1/agency_runtime.egg-info/SOURCES.txt": (b"README.md" + eol + b"setup.cfg"),
            "package-1/setup.cfg": b"[egg_info]" + eol + b"tag_date = 0" + eol,
        }

    windows_sdist = subject.canonicalize_sdist_bytes(
        _source_sdist(sdist_entries(b"\r\n"), windows=True),
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    linux_sdist = subject.canonicalize_sdist_bytes(
        _source_sdist(sdist_entries(b"\n"), windows=False),
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    assert windows_sdist == linux_sdist
    with tarfile.open(fileobj=io.BytesIO(windows_sdist), mode="r:gz") as archive:
        sdist_payloads = {
            item.name: archive.extractfile(item).read() for item in archive if item.isfile()
        }
    assert sdist_payloads["package-1/README.md"] == source_payload
    assert b"\r" not in sdist_payloads["package-1/PKG-INFO"]
    assert not sdist_payloads["package-1/agency_runtime.egg-info/SOURCES.txt"].endswith(b"\n")


def test_sdist_sources_manifest_is_rebuilt_from_actual_members() -> None:
    source = _source_sdist(
        {
            "package-1": None,
            "package-1/package": None,
            "package-1/package/module.py": b"module",
            "package-1/agency_runtime.egg-info": None,
            "package-1/agency_runtime.egg-info/SOURCES.txt": (
                b"package/module.py\npackage/module.py\nmissing.py\n"
            ),
            "package-1/PKG-INFO": b"metadata",
            "package-1/setup.cfg": b"generated",
        }
    )

    canonical = subject.canonicalize_sdist_bytes(
        source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    with tarfile.open(fileobj=io.BytesIO(canonical), mode="r:gz") as archive:
        payload = archive.extractfile("package-1/agency_runtime.egg-info/SOURCES.txt").read()

    assert payload == b"agency_runtime.egg-info/SOURCES.txt\npackage/module.py"


def test_wheel_generated_metadata_contract_rejects_multiple_record_roots() -> None:
    assert subject._canonical_wheel_entries([("package/module.py", b"source")]) == [
        ("package/module.py", b"source")
    ]
    with pytest.raises(ValueError, match="more than one generated RECORD"):
        subject._canonical_wheel_entries(
            [
                ("one.dist-info/RECORD", b"one"),
                ("two.dist-info/RECORD", b"two"),
            ]
        )


def test_sdist_accepts_pax_writer_nearest_even_mtime_header() -> None:
    source = _source_sdist(
        {
            "package-1": None,
            "package-1/package": None,
            "package-1/package/module.py": b"payload",
        },
        rounded_fractional_mtime=True,
    )
    tar_payload = gzip.decompress(source)
    pax_size = subject._canonical_octal(tar_payload[124:136], label="size")
    member_offset = (
        tarfile.BLOCKSIZE
        + ((pax_size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE) * tarfile.BLOCKSIZE
    )

    assert subject._parse_pax_payload(
        tar_payload[tarfile.BLOCKSIZE : tarfile.BLOCKSIZE + pax_size]
    ) == {"mtime": f"{TIMESTAMP}.75"}
    assert (
        subject._canonical_octal(
            tar_payload[member_offset + 136 : member_offset + 148],
            label="mtime",
        )
        == TIMESTAMP + 1
    )

    canonical = subject.canonicalize_sdist_bytes(
        source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )

    assert verifier._sdist_payload(
        io.BytesIO(canonical),
        expected_root="package-1",
        expected_timestamp=TIMESTAMP,
    )


@pytest.mark.parametrize(
    ("encoded", "header"),
    (
        (f"{TIMESTAMP}.25", TIMESTAMP),
        (f"{TIMESTAMP}.5", TIMESTAMP),
        (f"{TIMESTAMP + 1}.5", TIMESTAMP + 2),
        (f"{TIMESTAMP}.75", TIMESTAMP + 1),
    ),
)
def test_pax_mtime_validation_uses_exact_nearest_even_rounding(
    encoded: str,
    header: int,
) -> None:
    subject._validate_source_pax_records({"mtime": encoded}, raw_mtime=header)


def test_canonical_fixed_fixtures_match_owned_byte_contract_goldens() -> None:
    wheel = subject.canonicalize_wheel_bytes(_basic_wheel(), timestamp=TIMESTAMP)
    sdist = subject.canonicalize_sdist_bytes(
        _basic_sdist(),
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )

    assert len(wheel) == 367
    assert hashlib.sha256(wheel).hexdigest() == (
        "f0e9396721d662ebd986af8e32e62f2e4b7aaf92b3a202f22db20881383ff701"
    )
    assert len(sdist) == 10_277
    assert hashlib.sha256(sdist).hexdigest() == (
        "50309bb9b629c124059c430e243f9c775f30e903dfdf0cf368a6948822f8a7e9"
    )


def test_long_and_unicode_pax_paths_round_trip_with_exact_placeholders() -> None:
    long_directory = f"package-1/{'d' * 120}"
    unicode_file = "package-1/caf\u00e9.txt"
    source = _source_sdist(
        {
            "package-1": None,
            long_directory: None,
            f"{long_directory}/file.txt": b"long",
            unicode_file: b"unicode",
        }
    )

    canonical = subject.canonicalize_sdist_bytes(
        source,
        timestamp=TIMESTAMP,
        expected_filename="package-1.tar.gz",
    )
    tar_payload = gzip.decompress(canonical)
    verifier._preflight_tar_layout(tar_payload, expected_mtime=TIMESTAMP)
    with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
        assert {item.name for item in archive} == {
            "package-1",
            long_directory,
            f"{long_directory}/file.txt",
            unicode_file,
        }


@pytest.mark.parametrize(("length", "uses_pax"), [(99, False), (100, False), (101, True)])
def test_ustar_name_boundary_is_exact_and_idempotent(
    length: int,
    uses_pax: bool,
) -> None:
    name = "r/" + ("x" * (length - 2))
    tar_payload = subject._canonical_tar_payload(
        [
            subject._TarEntry("r", None),
            subject._TarEntry(name, b"payload"),
        ],
        timestamp=TIMESTAMP,
    )
    gzip_payload = subject._canonical_stored_gzip(
        tar_payload,
        filename="r.tar",
        timestamp=TIMESTAMP,
    )

    canonical = subject.canonicalize_sdist_bytes(
        gzip_payload,
        timestamp=TIMESTAMP,
        expected_filename="r.tar.gz",
    )

    assert canonical == gzip_payload
    assert tar_payload[512 + 156 : 512 + 157] == (tarfile.XHDTYPE if uses_pax else tarfile.REGTYPE)
    assert verifier._sdist_payload(
        io.BytesIO(canonical),
        expected_root="r",
        expected_timestamp=TIMESTAMP,
    )


@pytest.mark.parametrize(
    "wheel_name",
    ("package-1-py3-none-any.whl", "package-1-py3-none-win_amd64.whl"),
)
def test_file_wrapper_preserves_portable_and_windows_wheel_filenames(
    tmp_path: Path,
    wheel_name: str,
) -> None:
    wheel = tmp_path / wheel_name
    sdist = tmp_path / "package-1.tar.gz"
    wheel.write_bytes(_basic_wheel())
    sdist.write_bytes(_basic_sdist())

    subject.canonicalize_distributions(wheel, sdist, timestamp=TIMESTAMP)

    assert verifier._wheel_payload(wheel, expected_timestamp=TIMESTAMP)
    assert verifier._sdist_payload(
        sdist,
        expected_root="package-1",
        expected_timestamp=TIMESTAMP,
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted((sdist.name, wheel.name))


def test_repo_fixture_canonicalization_is_byte_idempotent(tmp_path: Path) -> None:
    _repository_path, payloads = _repository(tmp_path)
    dist = _artifacts(tmp_path, payloads)
    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))
    timestamp = _artifact_timestamp(wheel)

    subject.canonicalize_distributions(wheel, sdist, timestamp=timestamp)
    first = wheel.read_bytes(), sdist.read_bytes()
    subject.canonicalize_distributions(wheel, sdist, timestamp=timestamp)

    assert (wheel.read_bytes(), sdist.read_bytes()) == first


@pytest.mark.parametrize("timestamp", [-1, True, 2**32])
def test_timestamp_contract_rejects_non_unsigned_32_bit_values(timestamp: object) -> None:
    with pytest.raises(ValueError, match="unsigned 32-bit"):
        subject._canonical_zip_timestamp(timestamp)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unsigned 32-bit"):
        verifier._canonical_zip_timestamp(timestamp)  # type: ignore[arg-type]


def test_timestamp_contract_accepts_unsigned_32_bit_maximum() -> None:
    assert subject._canonical_zip_timestamp(2**32 - 1) == (2106, 2, 7, 6, 28, 14)


def test_unknown_zip_creator_and_raw_central_count_mismatch_fail_before_zipfile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unknown = bytearray(_basic_wheel())
    central = unknown.find(b"PK\x01\x02")
    made_by = struct.unpack_from("<H", unknown, central + 4)[0]
    struct.pack_into("<H", unknown, central + 4, (99 << 8) | (made_by & 0xFF))
    with pytest.raises(ValueError, match="finite build allowlist"):
        subject.canonicalize_wheel_bytes(bytes(unknown), timestamp=TIMESTAMP)

    mismatched = bytearray(_basic_wheel())
    eocd = mismatched.rfind(b"PK\x05\x06")
    struct.pack_into("<H", mismatched, eocd + 8, 1)
    struct.pack_into("<H", mismatched, eocd + 10, 1)
    monkeypatch.setattr(
        subject.zipfile,
        "ZipFile",
        lambda *_args, **_kwargs: pytest.fail("count mismatch reached ZipFile"),
    )
    with pytest.raises(ValueError, match="count mismatch"):
        subject.canonicalize_wheel_bytes(bytes(mismatched), timestamp=TIMESTAMP)


def test_portable_alias_and_casefold_prefix_collisions_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        subject.canonicalize_wheel_bytes(
            _source_wheel({"package/Foo.py": b"a", "package/foo.py": b"b"}),
            timestamp=TIMESTAMP,
        )
    with pytest.raises(ValueError, match="file-prefix collision"):
        subject.canonicalize_wheel_bytes(
            _source_wheel({"package/Foo": b"a", "package/foo/child": b"b"}),
            timestamp=TIMESTAMP,
        )


@pytest.mark.parametrize(
    "name",
    ("com¹", "CoM².txt", "COM³", "lpt¹", "LpT².md", "LPT³"),
)
def test_canonicalizer_rejects_superscript_windows_device_names(name: str) -> None:
    with pytest.raises(ValueError, match="unsafe archive member"):
        subject.safe_release_name(f"agency_runtime/{name}")


def test_direct_utf8_ustar_name_without_pax_is_rejected() -> None:
    payload = bytearray(gzip.decompress(_basic_sdist()))
    offset = 0
    while payload[offset + 156 : offset + 157] == tarfile.XHDTYPE:
        size = int(payload[offset + 124 : offset + 136].rstrip(b"\0 "), 8)
        offset += 512 + ((size + 511) // 512) * 512
    name = "package-1/caf\u00e9".encode()
    payload[offset : offset + 100] = name + (b"\0" * (100 - len(name)))
    payload[offset + 148 : offset + 156] = b"        "
    checksum = sum(payload[offset : offset + 512])
    payload[offset + 148 : offset + 156] = f"{checksum:06o}\0 ".encode()
    output = io.BytesIO()
    with gzip.GzipFile(
        filename="package-1.tar",
        mode="wb",
        fileobj=output,
        mtime=TIMESTAMP,
    ) as archive:
        archive.write(payload)

    with pytest.raises(ValueError, match="portable ASCII"):
        subject.canonicalize_sdist_bytes(
            output.getvalue(),
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )


def _first_central(raw: bytes | bytearray) -> int:
    offset = raw.find(b"PK\x01\x02")
    assert offset >= 0
    return offset


def _first_local(raw: bytes | bytearray) -> int:
    offset = raw.find(b"PK\x03\x04")
    assert offset >= 0
    return offset


@pytest.mark.parametrize(
    ("offset", "encoding", "value"),
    [
        (6, "<H", 21),  # extract
        (8, "<H", 2),  # flags
        (10, "<H", zipfile.ZIP_STORED),
        (12, "<H", 0),  # DOS time
        (14, "<H", 0),  # DOS date
        (20, "<L", subject.MAX_ARTIFACT_BYTES + 1),
        (24, "<L", 0xFFFFFFFF),
        (28, "<H", 0),  # empty name
        (30, "<H", 1),  # extra
        (32, "<H", 1),  # comment
        (34, "<H", 1),  # volume
        (36, "<H", 1),  # internal attrs
        (42, "<L", 0xFFFFFFFF),  # local offset
    ],
)
def test_raw_zip_preflight_rejects_every_bounded_field_class(
    offset: int,
    encoding: str,
    value: int,
) -> None:
    raw = bytearray(_basic_wheel())
    struct.pack_into(encoding, raw, _first_central(raw) + offset, value)

    with pytest.raises(ValueError, match=r"allowlist|bounded layout|count mismatch"):
        subject.canonicalize_wheel_bytes(bytes(raw), timestamp=TIMESTAMP)


def test_raw_zip_preflight_rejects_invalid_names_ratio_and_output_order() -> None:
    invalid_name = bytearray(_basic_wheel())
    central = _first_central(invalid_name)
    name_size = struct.unpack_from("<H", invalid_name, central + 28)[0]
    invalid_name[central + 46 : central + 46 + name_size] = b"\xff" * name_size
    with pytest.raises(ValueError, match="filename is invalid"):
        subject.canonicalize_wheel_bytes(bytes(invalid_name), timestamp=TIMESTAMP)

    ratio = bytearray(_basic_wheel())
    struct.pack_into("<L", ratio, _first_central(ratio) + 24, 10_000)
    with pytest.raises(ValueError, match="compression ratio"):
        subject.canonicalize_wheel_bytes(bytes(ratio), timestamp=TIMESTAMP)

    raw = _source_wheel({"z": b"z", "a": b"a"})
    offset, eocd, members = subject._zip_directory_contract(raw)
    with pytest.raises(ValueError, match="sorted order"):
        subject._preflight_source_zip_records(
            raw,
            directory_offset=offset,
            eocd=eocd,
            members=members,
            timestamp=_zip_time(),
            require_sorted=True,
        )


def test_zip_directory_contract_rejects_size_trailer_and_eocd_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="container size"):
        subject._zip_directory_contract(b"")
    monkeypatch.setattr(subject, "MAX_ARTIFACT_BYTES", 1)
    with pytest.raises(ValueError, match="container size"):
        subject._zip_directory_contract(_basic_wheel())
    monkeypatch.undo()

    trailing = _basic_wheel() + b"x"
    with pytest.raises(ValueError, match="end record"):
        subject._zip_directory_contract(trailing)

    for field_offset in (4, 6, 8, 10, 20):
        raw = bytearray(_basic_wheel())
        eocd = raw.rfind(b"PK\x05\x06")
        encoding = "<H"
        current = struct.unpack_from(encoding, raw, eocd + field_offset)[0]
        struct.pack_into(encoding, raw, eocd + field_offset, current ^ 1)
        with pytest.raises(ValueError, match="central directory contract"):
            subject._zip_directory_contract(bytes(raw))


def test_low_level_member_budgets_and_exact_deflate_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="member count"):
        subject._member_budget(
            count=subject.MAX_ARCHIVE_MEMBERS + 1,
            size=0,
            total=0,
            artifact="fixture",
        )
    with pytest.raises(ValueError, match="declared size"):
        subject._member_budget(
            count=1,
            size=-1,
            total=0,
            artifact="fixture",
        )
    with pytest.raises(ValueError, match="total uncompressed"):
        subject._member_budget(
            count=1,
            size=1,
            total=subject.MAX_ARCHIVE_TOTAL_BYTES,
            artifact="fixture",
        )
    assert subject._portable_alias("Pkg/Caf\u00e9") == "pkg/caf\u00e9"

    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    compressed = compressor.compress(b"payload") + compressor.flush()
    subject._require_exact_deflate(compressed, size=7, name="member")
    for invalid, size, message in (
        (compressed + b"x", 7, "boundary"),
        (compressed, 6, "boundary"),
        (compressed[:-1], 7, "invalid"),
        (b"invalid", 7, "invalid"),
    ):
        with pytest.raises(ValueError, match=message):
            subject._require_exact_deflate(invalid, size=size, name="member")

    class Stalled:
        eof = False
        unused_data = b""
        unconsumed_tail = b"x"

        def decompress(self, payload: bytes, _limit: int) -> bytes:
            self.unconsumed_tail = payload
            return b""

        def flush(self, _limit: int) -> bytes:
            return b""

    monkeypatch.setattr(subject.zlib, "decompressobj", lambda *_args: Stalled())
    with pytest.raises(ValueError, match="invalid"):
        subject._require_exact_deflate(b"x", size=1, name="member")


def test_filesystem_reader_and_replacement_cleanup_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "artifact"
    source.write_bytes(b"payload")
    assert subject._read_bounded_regular_file(source) == b"payload"

    monkeypatch.setattr(subject.os, "lstat", lambda _path: _fake_stat(mode=stat.S_IFDIR))
    with pytest.raises(ValueError, match="single-link regular"):
        subject._read_bounded_regular_file(source)
    monkeypatch.undo()

    monkeypatch.setattr(
        subject.os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError())
    )
    with pytest.raises(ValueError, match="opened safely"):
        subject._read_bounded_regular_file(source)
    monkeypatch.undo()

    real_replace = subject.os.replace
    monkeypatch.setattr(
        subject.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )
    with pytest.raises(OSError, match="replace failed"):
        subject._replace_regular_file(source, b"new")
    assert source.read_bytes() == b"payload"
    assert not list(tmp_path.glob(".*.canonical-*.tmp"))
    monkeypatch.setattr(subject.os, "replace", real_replace)


def test_second_artifact_replace_failure_leaves_no_canonical_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wheel = tmp_path / "package-1-py3-none-any.whl"
    sdist = tmp_path / "package-1.tar.gz"
    wheel.write_bytes(_basic_wheel())
    sdist.write_bytes(_basic_sdist())
    original = subject.os.replace
    calls = 0

    def fail_second(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("second replacement failed")
        original(source, destination)

    monkeypatch.setattr(subject.os, "replace", fail_second)
    with pytest.raises(OSError, match="second replacement failed"):
        subject.canonicalize_distributions(wheel, sdist, timestamp=TIMESTAMP)
    assert wheel.exists() and sdist.exists()
    assert not list(tmp_path.glob(".*.canonical-*.tmp"))


def test_timestamp_conversion_normalizes_platform_failures_and_pre_zip_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject.time,
        "gmtime",
        lambda _timestamp: (_ for _ in ()).throw(OSError("unsupported")),
    )
    with pytest.raises(ValueError, match="supported range"):
        subject._canonical_zip_timestamp(TIMESTAMP)

    monkeypatch.undo()
    with pytest.raises(ValueError, match="ZIP range"):
        subject._canonical_zip_timestamp(0)


def test_bounded_file_reader_detects_every_identity_and_size_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "artifact"
    path.write_bytes(b"payload")
    real_lstat = subject.os.lstat
    real_fstat = subject.os.fstat
    before = real_lstat(path)
    changed = SimpleNamespace(
        **{name: getattr(before, name) for name in dir(before) if name.startswith("st_")}
    )
    changed.st_ino = before.st_ino + 1

    monkeypatch.setattr(subject.os, "fstat", lambda _descriptor: changed)
    with pytest.raises(ValueError, match="changed while it was opened"):
        subject._read_bounded_regular_file(path)
    monkeypatch.undo()

    declared_one = _fake_stat(size=1)
    monkeypatch.setattr(subject.os, "lstat", lambda _path: declared_one)
    monkeypatch.setattr(subject.os, "fstat", lambda _descriptor: declared_one)
    with pytest.raises(ValueError, match="exceeds its size boundary"):
        subject._read_bounded_regular_file(path)
    monkeypatch.undo()

    declared_long = _fake_stat(size=8)
    monkeypatch.setattr(subject.os, "lstat", lambda _path: declared_long)
    monkeypatch.setattr(subject.os, "fstat", lambda _descriptor: declared_long)
    with pytest.raises(ValueError, match="shorter than its declared size"):
        subject._read_bounded_regular_file(path)
    monkeypatch.undo()

    calls = 0

    def changing_fstat(descriptor: int) -> object:
        nonlocal calls
        calls += 1
        return real_fstat(descriptor) if calls == 1 else changed

    monkeypatch.setattr(subject.os, "fstat", changing_fstat)
    with pytest.raises(ValueError, match="changed while it was read"):
        subject._read_bounded_regular_file(path)
    monkeypatch.undo()

    calls = 0

    def changing_lstat(target: Path) -> object:
        nonlocal calls
        calls += 1
        return real_lstat(target) if calls == 1 else changed

    monkeypatch.setattr(subject.os, "lstat", changing_lstat)
    with pytest.raises(ValueError, match="path changed while it was read"):
        subject._read_bounded_regular_file(path)


class _MemberArchive:
    def __init__(self, payload: bytes | None) -> None:
        self.payload = payload

    def open(self, _item: object, _mode: str) -> io.BytesIO:
        assert self.payload is not None
        return io.BytesIO(self.payload)


def test_zip_member_reader_rejects_overlong_short_and_unreadable_members() -> None:
    item = SimpleNamespace(filename="member", file_size=1)
    with pytest.raises(ValueError, match="exceeds its declared size"):
        subject._read_zip_member(_MemberArchive(b"xx"), item)  # type: ignore[arg-type]
    item.file_size = 2
    with pytest.raises(ValueError, match="shorter than its declared size"):
        subject._read_zip_member(_MemberArchive(b"x"), item)  # type: ignore[arg-type]


def test_deflate_rejects_a_complete_stream_before_declared_input_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    compressed = compressor.compress(b"payload") + compressor.flush()
    monkeypatch.setattr(subject, "READ_CHUNK_BYTES", len(compressed))
    with pytest.raises(ValueError, match="boundary is invalid"):
        subject._require_exact_deflate(compressed + b"x", size=7, name="member")


def _wheel_views(
    raw: bytes,
) -> tuple[list[zipfile.ZipInfo], int, int, int]:
    directory_offset, eocd, members = subject._zip_directory_contract(raw)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
    return infos, directory_offset, eocd, members


def test_zip_cross_view_validators_reject_signature_field_and_landing_faults() -> None:
    raw = _basic_wheel()
    infos, directory_offset, eocd, members = _wheel_views(raw)

    bad_preflight = bytearray(raw)
    bad_preflight[directory_offset : directory_offset + 4] = b"bad!"
    with pytest.raises(ValueError, match="unknown record or count mismatch"):
        subject._preflight_source_zip_records(
            bytes(bad_preflight),
            directory_offset=directory_offset,
            eocd=eocd,
            members=members,
            timestamp=_zip_time(),
        )

    with pytest.raises(ValueError, match="unknown record or gap"):
        subject._validate_zip_central_records(
            raw,
            infos,
            directory_offset=0,
            eocd=eocd,
        )

    bad_central = bytearray(raw)
    crc = struct.unpack_from("<L", bad_central, directory_offset + 16)[0]
    struct.pack_into("<L", bad_central, directory_offset + 16, crc ^ 1)
    with pytest.raises(ValueError, match="central record is noncanonical"):
        subject._validate_zip_central_records(
            bytes(bad_central),
            infos,
            directory_offset=directory_offset,
            eocd=eocd,
        )

    with pytest.raises(ValueError, match="unknown record or gap"):
        subject._validate_zip_central_records(
            raw,
            infos[:-1],
            directory_offset=directory_offset,
            eocd=eocd,
        )

    shifted = copy.copy(infos[0])
    shifted.header_offset += 1
    with pytest.raises(ValueError, match="prefix, gap, or overlap"):
        subject._validate_zip_local_records(
            raw,
            [shifted, *infos[1:]],
            directory_offset=directory_offset,
        )

    bad_local = bytearray(raw)
    local_crc = struct.unpack_from("<L", bad_local, infos[0].header_offset + 14)[0]
    struct.pack_into("<L", bad_local, infos[0].header_offset + 14, local_crc ^ 1)
    with pytest.raises(ValueError, match="local record is noncanonical"):
        subject._validate_zip_local_records(
            bytes(bad_local),
            infos,
            directory_offset=directory_offset,
        )

    with pytest.raises(ValueError, match="prefix, gap, or overlap"):
        subject._validate_zip_local_records(
            raw,
            infos[:-1],
            directory_offset=directory_offset,
        )


def test_source_zip_info_rejects_encoding_name_header_ratio_and_stored_size() -> None:
    raw = _basic_wheel()
    infos, _directory_offset, _eocd, _members = _wheel_views(raw)
    item = infos[0]

    encoded = copy.copy(item)
    encoded.filename = "caf\u00e9"
    encoded.flag_bits = 0
    with pytest.raises(ValueError, match="encoding flag"):
        subject._encoded_zip_name(encoded)

    directory = copy.copy(item)
    directory.filename = "package/"
    with pytest.raises(ValueError, match="noncanonical file name"):
        subject._validate_source_zip_info(directory, timestamp=_zip_time())

    header = copy.copy(item)
    header.create_version += 1
    with pytest.raises(ValueError, match="finite build allowlist"):
        subject._validate_source_zip_info(header, timestamp=_zip_time())

    ratio = copy.copy(item)
    ratio.file_size = subject.MAX_ZIP_COMPRESSION_RATIO + 1
    ratio.compress_size = 1
    with pytest.raises(ValueError, match="compression ratio"):
        subject._validate_source_zip_info(ratio, timestamp=_zip_time())

    canonical = subject.canonicalize_wheel_bytes(raw, timestamp=TIMESTAMP)
    stored_infos, stored_offset, _stored_eocd, _stored_members = _wheel_views(canonical)
    stored = bytearray(canonical)
    struct.pack_into("<L", stored, stored_offset + 20, stored_infos[0].compress_size + 1)
    with pytest.raises(ValueError, match="finite build allowlist"):
        subject.canonicalize_wheel_bytes(bytes(stored), timestamp=TIMESTAMP)


def _stored_gzip_block_offset(raw: bytes) -> int:
    offset = raw.find(b"\0", 10)
    assert offset >= 0
    return offset + 1


def test_stored_gzip_parser_enforces_headers_segmentation_bounds_and_trailer() -> None:
    valid = subject._canonical_stored_gzip(
        b"payload",
        filename="fixture.tar",
        timestamp=TIMESTAMP,
    )
    block = _stored_gzip_block_offset(valid)
    with pytest.raises(ValueError, match="truncated"):
        subject._stored_gzip_payload(
            valid,
            payload_start=len(valid) - 8,
            maximum_payload=100,
        )

    invalid_marker = bytearray(valid)
    invalid_marker[block] = 2
    with pytest.raises(ValueError, match="block header"):
        subject._stored_gzip_payload(
            bytes(invalid_marker),
            payload_start=block,
            maximum_payload=100,
        )

    invalid_inverse = bytearray(valid)
    invalid_inverse[block + 3] ^= 1
    with pytest.raises(ValueError, match="block length"):
        subject._stored_gzip_payload(
            bytes(invalid_inverse),
            payload_start=block,
            maximum_payload=100,
        )

    oversized = bytearray(valid)
    struct.pack_into("<HH", oversized, block + 1, 100, ~100 & 0xFFFF)
    with pytest.raises(ValueError, match="exceeds its boundary"):
        subject._stored_gzip_payload(
            bytes(oversized),
            payload_start=block,
            maximum_payload=100,
        )

    nonfinal_short = bytearray(valid)
    nonfinal_short[block] = 0
    with pytest.raises(ValueError, match="segmentation"):
        subject._stored_gzip_payload(
            bytes(nonfinal_short),
            payload_start=block,
            maximum_payload=100,
        )

    with pytest.raises(ValueError, match="exact boundary"):
        subject._stored_gzip_payload(
            valid,
            payload_start=block,
            maximum_payload=1,
        )

    full = subject._canonical_stored_gzip(
        b"x" * 65_535,
        filename="fixture.tar",
        timestamp=TIMESTAMP,
    )
    full_block = _stored_gzip_block_offset(full)
    missing_final = bytearray(full)
    missing_final[full_block] = 0
    with pytest.raises(ValueError, match="trailing or missing"):
        subject._stored_gzip_payload(
            bytes(missing_final),
            payload_start=full_block,
            maximum_payload=100_000,
        )

    final_empty = bytearray(missing_final)
    final_empty[-8:-8] = b"\x01\x00\x00\xff\xff"
    with pytest.raises(ValueError, match="segmentation"):
        subject._stored_gzip_payload(
            bytes(final_empty),
            payload_start=full_block,
            maximum_payload=100_000,
        )

    trailing = bytearray(valid)
    trailing[-8:-8] = b"x"
    with pytest.raises(ValueError, match="trailing or missing"):
        subject._stored_gzip_payload(
            bytes(trailing),
            payload_start=block,
            maximum_payload=100,
        )

    bad_trailer = bytearray(valid)
    bad_trailer[-8] ^= 1
    with pytest.raises(ValueError, match="trailer"):
        subject._stored_gzip_payload(
            bytes(bad_trailer),
            payload_start=block,
            maximum_payload=100,
        )

    multiple = subject._canonical_stored_gzip(
        b"x" * 70_000,
        filename="fixture.tar",
        timestamp=TIMESTAMP,
    )
    assert (
        subject._stored_gzip_payload(
            multiple,
            payload_start=_stored_gzip_block_offset(multiple),
            maximum_payload=100_000,
        )
        == b"x" * 70_000
    )
    empty = subject._canonical_stored_gzip(
        b"",
        filename="fixture.tar",
        timestamp=TIMESTAMP,
    )
    assert (
        subject._stored_gzip_payload(
            empty,
            payload_start=_stored_gzip_block_offset(empty),
            maximum_payload=1,
        )
        == b""
    )


def test_gzip_source_parser_rejects_header_name_stream_and_final_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="gzip header"):
        subject._gzip_tar_payload(b"invalid", expected_filename="fixture.tar")
    unterminated = b"\x1f\x8b\x08\x08\0\0\0\0\x02\xff" + (b"x" * 256)
    with pytest.raises(ValueError, match="gzip filename"):
        subject._gzip_tar_payload(unterminated, expected_filename="fixture.tar")
    non_ascii = b"\x1f\x8b\x08\x08\0\0\0\0\x02\xff\xff\0payload"
    with pytest.raises(ValueError, match="gzip filename"):
        subject._gzip_tar_payload(non_ascii, expected_filename="fixture.tar")
    with pytest.raises(ValueError, match="does not match"):
        subject._gzip_tar_payload(_basic_sdist(), expected_filename="other.tar")

    dynamic = _basic_sdist()
    monkeypatch.setattr(subject, "READ_CHUNK_BYTES", len(dynamic))
    with pytest.raises(ValueError, match="exact boundary"):
        subject._gzip_tar_payload(dynamic + b"x", expected_filename="package-1.tar")
    monkeypatch.undo()

    class Broken:
        eof = False
        unused_data = b""
        unconsumed_tail = b""

        def decompress(self, _chunk: bytes, _limit: int) -> bytes:
            raise zlib.error("broken")

        def flush(self, _limit: int) -> bytes:
            return b""

    monkeypatch.setattr(subject.zlib, "decompressobj", lambda *_args: Broken())
    with pytest.raises(ValueError, match="gzip stream is invalid"):
        subject._gzip_tar_payload(dynamic, expected_filename="package-1.tar")
    monkeypatch.undo()

    with pytest.raises(ValueError, match="gzip stream is invalid"):
        subject._gzip_tar_payload(dynamic[:-8], expected_filename="package-1.tar")


def test_scalar_tar_parsers_reject_malformed_fields_and_pax_records() -> None:
    with pytest.raises(ValueError, match="mode field"):
        subject._canonical_octal(b"0000000 ", label="mode")
    with pytest.raises(ValueError, match="uname field"):
        subject._nul_padded(b"name\0x", label="uname", allow_empty=True)
    with pytest.raises(ValueError, match="PAX payload is malformed"):
        subject._parse_pax_payload(b"invalid")
    with pytest.raises(ValueError, match="length is noncanonical"):
        subject._parse_pax_payload(b"99 path=x\n")
    with pytest.raises(ValueError, match="PAX text is invalid"):
        subject._parse_pax_payload(b"9 path=\xff\n")
    with pytest.raises(ValueError, match="unsupported or duplicated"):
        subject._parse_pax_payload(b"13 comment=x\n")
    duplicate = subject._pax_path_record("one") + subject._pax_path_record("two")
    with pytest.raises(ValueError, match="unsupported or duplicated"):
        subject._parse_pax_payload(duplicate)
    with pytest.raises(ValueError, match="PAX base name"):
        subject._source_tar_name(b"bad" + (b"\0" * 97), pax_path="expected")


def _checked_tar_header(header: bytes | bytearray) -> bytes:
    result = bytearray(header)
    result[148:156] = b"        "
    result[148:156] = f"{sum(result):06o}\0 ".encode("ascii")
    return bytes(result)


def _tar_record(
    name: str,
    *,
    member_type: bytes = tarfile.REGTYPE,
    payload: bytes = b"",
    mode: int | None = None,
    modified: int = TIMESTAMP,
) -> bytes:
    encoded = name.encode("ascii")
    header = subject._canonical_tar_header(
        encoded,
        mode=(0o755 if member_type == tarfile.DIRTYPE else 0o644) if mode is None else mode,
        size=len(payload),
        modified=modified,
        member_type=member_type,
    )
    return header + payload + (b"\0" * (-len(payload) % tarfile.BLOCKSIZE))


def _tar_container(*records: bytes) -> bytes:
    payload = bytearray(b"".join(records))
    payload.extend(b"\0" * 1_024)
    payload.extend(b"\0" * (-len(payload) % 10_240))
    return bytes(payload)


def test_wheel_rejects_mixed_source_methods_and_stored_size_mismatch() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for index, method in enumerate((zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED)):
            item = zipfile.ZipInfo(f"package/{index}", _zip_time())
            item.create_system = 3
            item.create_version = subject.CANONICAL_ZIP_VERSION
            item.extract_version = subject.CANONICAL_ZIP_VERSION
            item.compress_type = method
            item.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(item, b"payload")
    with pytest.raises(ValueError, match="one canonical compression method"):
        subject.canonicalize_wheel_bytes(output.getvalue(), timestamp=TIMESTAMP)

    canonical = subject.canonicalize_wheel_bytes(_basic_wheel(), timestamp=TIMESTAMP)
    infos, directory_offset, _eocd, _members = _wheel_views(canonical)
    item = copy.copy(infos[0])
    raw = bytearray(canonical)
    item.compress_size += 1
    struct.pack_into("<L", raw, item.header_offset + 18, item.compress_size)
    with pytest.raises(ValueError, match="stored member has a noncanonical size"):
        subject._validate_zip_local_records(
            bytes(raw),
            [item],
            directory_offset=directory_offset,
        )


def test_wheel_high_level_contract_exception_and_output_size_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _basic_wheel()
    _infos, directory_offset, _eocd, _members = _wheel_views(raw)

    class EmptyArchive:
        comment = b""
        start_dir = directory_offset

        def __enter__(self) -> EmptyArchive:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def infolist(self) -> list[zipfile.ZipInfo]:
            return []

    monkeypatch.setattr(subject.zipfile, "ZipFile", lambda *_args, **_kwargs: EmptyArchive())
    with pytest.raises(ValueError, match="central directory contract"):
        subject.canonicalize_wheel_bytes(raw, timestamp=TIMESTAMP)
    monkeypatch.undo()

    monkeypatch.setattr(
        subject.zipfile,
        "ZipFile",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(zipfile.BadZipFile("broken")),
    )
    with pytest.raises(ValueError, match="source container is invalid"):
        subject.canonicalize_wheel_bytes(raw, timestamp=TIMESTAMP)
    monkeypatch.undo()

    monkeypatch.setattr(
        subject,
        "_canonical_wheel_payload",
        lambda *_args, **_kwargs: b"x" * (subject.MAX_ARTIFACT_BYTES + 1),
    )
    with pytest.raises(ValueError, match="canonical wheel exceeds"):
        subject.canonicalize_wheel_bytes(raw, timestamp=TIMESTAMP)


def test_raw_tar_header_and_pax_metadata_faults_are_rejected() -> None:
    header = subject._canonical_tar_header(
        b"source/file",
        mode=0o644,
        size=0,
        modified=TIMESTAMP,
        member_type=tarfile.REGTYPE,
    )
    with pytest.raises(ValueError, match="header is truncated"):
        subject._validate_source_tar_header(header[:-1])

    spelling = bytearray(header)
    spelling[148:156] = b"00000000"
    with pytest.raises(ValueError, match="checksum spelling"):
        subject._validate_source_tar_header(bytes(spelling))

    checksum = bytearray(header)
    checksum[0] ^= 1
    with pytest.raises(ValueError, match="checksum is invalid"):
        subject._validate_source_tar_header(bytes(checksum))

    member_type = bytearray(header)
    member_type[156:157] = tarfile.SYMTYPE
    with pytest.raises(ValueError, match="member type is unsupported"):
        subject._validate_source_tar_header(_checked_tar_header(member_type))

    reserved = bytearray(header)
    reserved[157] = 1
    with pytest.raises(ValueError, match="reserved fields"):
        subject._validate_source_tar_header(_checked_tar_header(reserved))

    pax = bytearray(
        subject._canonical_tar_header(
            b"././@PaxHeader",
            mode=0,
            size=0,
            modified=0,
            member_type=tarfile.XHDTYPE,
        )
    )
    pax[100:108] = b"0000001\0"
    with pytest.raises(ValueError, match="PAX tar header"):
        subject._validate_source_tar_header(_checked_tar_header(pax))

    with pytest.raises(ValueError, match="PAX topology"):
        subject._validate_source_pax_records({}, raw_mtime=TIMESTAMP)
    with pytest.raises(ValueError, match="PAX mtime is noncanonical"):
        subject._validate_source_pax_records({"mtime": "01"}, raw_mtime=TIMESTAMP)
    with pytest.raises(ValueError, match="PAX mtime is noncanonical"):
        subject._validate_source_pax_records({"mtime": "-1.5"}, raw_mtime=-2)
    subject._validate_source_pax_records(
        {"mtime": f"{TIMESTAMP}.75"},
        raw_mtime=TIMESTAMP + 1,
    )
    with pytest.raises(ValueError, match="differs from its tar header"):
        subject._validate_source_pax_records(
            {"mtime": f"{TIMESTAMP}.75"},
            raw_mtime=TIMESTAMP,
        )
    with pytest.raises(ValueError, match="differs from its tar header"):
        subject._validate_source_pax_records({"mtime": "2"}, raw_mtime=1)


def test_raw_tar_layout_rejects_end_padding_pax_and_boundary_faults() -> None:
    with pytest.raises(ValueError, match="length is noncanonical"):
        subject._validate_source_tar_layout(b"")

    invalid_end = (b"\0" * 512) + b"x" + (b"\0" * (10_240 - 513))
    with pytest.raises(ValueError, match="end marker"):
        subject._validate_source_tar_layout(invalid_end)

    base = bytearray(_tar_container(_tar_record("source/file")))
    base[-1] = ord("x")
    with pytest.raises(ValueError, match="nonzero trailing data"):
        subject._validate_source_tar_layout(bytes(base))

    pax_payload = subject._pax_path_record("source/file")
    pax_record = _tar_record(
        "././@PaxHeader",
        member_type=tarfile.XHDTYPE,
        payload=pax_payload,
        mode=0,
        modified=0,
    )
    with pytest.raises(ValueError, match="orphan PAX"):
        subject._validate_source_tar_layout(_tar_container(pax_record))

    with pytest.raises(ValueError, match="zero padding"):
        subject._validate_source_tar_layout(
            _tar_container(_tar_record("source/file")) + (b"\0" * 10_240)
        )

    padded = bytearray(_tar_container(_tar_record("source/file", payload=b"x")))
    padded[513] = 1
    with pytest.raises(ValueError, match="member boundary"):
        subject._validate_source_tar_layout(bytes(padded))

    oversized_payload = b"x" * (64 * 1_024 + 1)
    oversized_pax = _tar_record(
        "././@PaxHeader",
        member_type=tarfile.XHDTYPE,
        payload=oversized_payload,
        mode=0,
        modified=0,
    )
    with pytest.raises(ValueError, match="PAX header boundary"):
        subject._validate_source_tar_layout(_tar_container(oversized_pax))

    missing_end = b"".join(_tar_record(f"source/{index}") for index in range(20))
    with pytest.raises(ValueError, match="end marker is missing"):
        subject._validate_source_tar_layout(missing_end)


class _FakeTarArchive:
    def __init__(
        self,
        items: list[tarfile.TarInfo],
        *,
        pax_headers: dict[str, str] | None = None,
        payload: bytes = b"x",
    ) -> None:
        self.items = items
        self.pax_headers = pax_headers or {}
        self.payload = payload

    def __enter__(self) -> _FakeTarArchive:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self):
        return iter(self.items)

    def extractfile(self, _item: tarfile.TarInfo) -> io.BytesIO:
        return io.BytesIO(self.payload)


def _fake_tar_item(
    name: str,
    *,
    member_type: bytes = tarfile.REGTYPE,
    mode: int | None = None,
    size: int = 1,
) -> tarfile.TarInfo:
    item = tarfile.TarInfo(name)
    item.type = member_type
    item.mode = (0o755 if member_type == tarfile.DIRTYPE else 0o644) if mode is None else mode
    item.size = 0 if member_type == tarfile.DIRTYPE else size
    return item


def test_tar_member_reader_and_high_level_semantic_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _fake_tar_item("source/file")

    class Missing:
        def extractfile(self, _item: tarfile.TarInfo) -> None:
            return None

    with pytest.raises(ValueError, match="could not be read"):
        subject._read_tar_member(Missing(), item)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exceeds its declared size"):
        subject._read_tar_member(_FakeTarArchive([], payload=b"xx"), item)  # type: ignore[arg-type]
    item.size = 2
    with pytest.raises(ValueError, match="shorter than its declared size"):
        subject._read_tar_member(_FakeTarArchive([], payload=b"x"), item)  # type: ignore[arg-type]

    def source_entries(archive: _FakeTarArchive) -> list[subject._TarEntry]:
        monkeypatch.setattr(subject.tarfile, "open", lambda **_kwargs: archive)
        try:
            return subject._source_tar_entries(b"ignored")
        finally:
            monkeypatch.undo()

    with pytest.raises(ValueError, match="global PAX state"):
        source_entries(_FakeTarArchive([], pax_headers={"comment": "x"}))

    unsupported = _fake_tar_item("source/link", member_type=tarfile.SYMTYPE)
    with pytest.raises(ValueError, match="unsupported member"):
        source_entries(_FakeTarArchive([unsupported]))

    for member_type in (
        tarfile.LNKTYPE,
        tarfile.CHRTYPE,
        tarfile.BLKTYPE,
        tarfile.FIFOTYPE,
    ):
        unsupported = _fake_tar_item("source/special", member_type=member_type)
        with pytest.raises(ValueError, match="unsupported member"):
            source_entries(_FakeTarArchive([unsupported]))

    unsupported_pax = _fake_tar_item("source/file")
    unsupported_pax.pax_headers = {"comment": "x"}
    with pytest.raises(ValueError, match="unsupported PAX state"):
        source_entries(_FakeTarArchive([unsupported_pax]))

    owner = _fake_tar_item("source/file")
    owner.uid = -1
    with pytest.raises(ValueError, match="owner metadata"):
        source_entries(_FakeTarArchive([owner]))

    duplicate = [_fake_tar_item("source/file"), _fake_tar_item("source/file")]
    with pytest.raises(ValueError, match="duplicate member"):
        source_entries(_FakeTarArchive(duplicate))

    directory = _fake_tar_item("source", member_type=tarfile.DIRTYPE, mode=0o750)
    with pytest.raises(ValueError, match="directory header"):
        source_entries(_FakeTarArchive([directory]))

    directory = _fake_tar_item("source", member_type=tarfile.DIRTYPE, mode=0o700)
    directory.size = 1
    with pytest.raises(ValueError, match="directory header"):
        source_entries(_FakeTarArchive([directory]))

    file_mode = _fake_tar_item("source/file", mode=0o640)
    with pytest.raises(ValueError, match="file header"):
        source_entries(_FakeTarArchive([file_mode]))

    monkeypatch.setattr(
        subject.tarfile,
        "open",
        lambda **_kwargs: (_ for _ in ()).throw(tarfile.ReadError("broken")),
    )
    with pytest.raises(ValueError, match="tar container is invalid"):
        subject._source_tar_entries(b"ignored")
    monkeypatch.undo()

    with pytest.raises(ValueError, match="directory topology"):
        source_entries(_FakeTarArchive([_fake_tar_item("source/file")]))


def test_manual_tar_field_and_canonical_output_size_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="numeric field"):
        subject._tar_octal(8**7, 8)
    with pytest.raises(ValueError, match="tar name"):
        subject._canonical_tar_header(
            b"",
            mode=0o644,
            size=0,
            modified=TIMESTAMP,
            member_type=tarfile.REGTYPE,
        )

    raw = _basic_sdist()
    real_writer = subject._canonical_tar_payload

    def lower_tar_limit(*args, **kwargs) -> bytes:
        payload = real_writer(*args, **kwargs)
        monkeypatch.setattr(subject, "MAX_TAR_CONTAINER_BYTES", 1)
        return payload

    monkeypatch.setattr(subject, "_canonical_tar_payload", lower_tar_limit)
    with pytest.raises(ValueError, match="tar exceeds its container"):
        subject.canonicalize_sdist_bytes(
            raw,
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )
    monkeypatch.undo()

    def lower_artifact_limit(*args, **kwargs) -> bytes:
        payload = real_writer(*args, **kwargs)
        monkeypatch.setattr(subject, "MAX_ARTIFACT_BYTES", 1)
        return payload

    monkeypatch.setattr(subject, "_canonical_tar_payload", lower_artifact_limit)
    with pytest.raises(ValueError, match="compressed artifact limits"):
        subject.canonicalize_sdist_bytes(
            raw,
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )
    monkeypatch.undo()

    def lower_ratio(*args, **kwargs) -> bytes:
        payload = real_writer(*args, **kwargs)
        monkeypatch.setattr(subject, "MAX_ZIP_COMPRESSION_RATIO", 0)
        return payload

    monkeypatch.setattr(subject, "_canonical_tar_payload", lower_ratio)
    with pytest.raises(ValueError, match="compressed artifact limits"):
        subject.canonicalize_sdist_bytes(
            raw,
            timestamp=TIMESTAMP,
            expected_filename="package-1.tar.gz",
        )
