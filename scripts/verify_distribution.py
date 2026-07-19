"""Verify built Agency Runtime wheel and source distribution contents."""

from __future__ import annotations

import argparse
import ast
import base64
import configparser
import csv
import hashlib
import io
import re
import stat
import struct
import subprocess
import sys
import tarfile
import unicodedata
import zipfile
from collections import Counter
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path, PurePosixPath, PureWindowsPath

from packaging.markers import InvalidMarker, Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 release environment
    import tomli as tomllib

REQUIRED_PACKAGE_FILES = {
    "agency_runtime/core/companion_policy.yaml",
    "agency_runtime/core/config_defaults.yaml",
    "agency_runtime/core/canary.py",
    "agency_runtime/core/configuration.py",
    "agency_runtime/core/dashboard_runtime.py",
    "agency_runtime/core/dashboard_service.py",
    "agency_runtime/core/evals/data/__init__.py",
    "agency_runtime/core/evals/data/routing_v1.py",
    "agency_runtime/dashboard/__init__.py",
    "agency_runtime/dashboard/app.css",
    "agency_runtime/dashboard/app.js",
    "agency_runtime/dashboard/charts.js",
    "agency_runtime/dashboard/index.html",
}
REQUIRED_SDIST_FILES = {
    ".editorconfig",
    ".gitattributes",
    "AGENTS.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/THREAT_MODEL.md",
    "examples/rosters/agents.json",
    "pyproject.toml",
    "scripts/verify_distribution.py",
    "tests/dashboard_ui.test.mjs",
    *REQUIRED_PACKAGE_FILES,
}
REQUIRED_CLASSIFIERS = {
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
}
FORBIDDEN_PARTS = {
    ".coverage",
    ".DS_Store",
    ".env",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "agency.yaml",
    "build",
    "dist",
}
FORBIDDEN_SUFFIXES = {".db", ".egg-link", ".pyc", ".pyo", ".sqlite", ".sqlite3"}
WHEEL_METADATA_FILES = {
    "METADATA",
    "RECORD",
    "WHEEL",
    "entry_points.txt",
    "licenses/LICENSE",
    "top_level.txt",
}
EXPECTED_CONSOLE_SCRIPTS = {"agency": "agency_runtime.cli.main:main"}
VERSION_PATTERN = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:(?:a|b|rc)(?:0|[1-9]\d*))?"
)
MAX_ARCHIVE_MEMBERS = 4_096
MAX_ARCHIVE_MEMBER_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ZIP_COMPRESSION_RATIO = 200
MAX_ARCHIVE_NAME_CHARS = 512
READ_CHUNK_BYTES = 64 * 1024
WINDOWS_RESERVED_BASENAMES = {
    "AUX",
    "CLOCK$",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
WINDOWS_INVALID_CHARS = frozenset('<>:"|?*')
SDIST_ROOT_SOURCE_FILES = {
    ".editorconfig",
    ".gitattributes",
    "AGENTS.md",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
}
SDIST_GENERATED_METADATA_FILES = {
    "PKG-INFO",
    "agency_runtime.egg-info/PKG-INFO",
    "agency_runtime.egg-info/SOURCES.txt",
    "agency_runtime.egg-info/dependency_links.txt",
    "agency_runtime.egg-info/entry_points.txt",
    "agency_runtime.egg-info/requires.txt",
    "agency_runtime.egg-info/top_level.txt",
    "setup.cfg",
}


def _safe_name(name: str) -> PurePosixPath:
    if not name or len(name) > MAX_ARCHIVE_NAME_CHARS or "\x00" in name or "\\" in name:
        raise ValueError(f"unsafe archive member: {name}")
    raw = name[:-1] if name.endswith("/") else name
    parts = raw.split("/")
    windows = PureWindowsPath(raw)
    if (
        not raw
        or any(
            part in {"", ".", ".."}
            or part.endswith((".", " "))
            or part.split(".", 1)[0].rstrip(" ").upper() in WINDOWS_RESERVED_BASENAMES
            or any(ord(character) < 32 or character in WINDOWS_INVALID_CHARS for character in part)
            for part in parts
        )
        or raw != unicodedata.normalize("NFC", raw)
        or PurePosixPath(raw).is_absolute()
        or windows.drive
        or windows.is_absolute()
    ):
        raise ValueError(f"unsafe archive member: {name}")
    path = PurePosixPath(raw)
    return path


def _register_archive_member(
    seen: dict[str, str],
    *,
    raw_name: str,
    path: PurePosixPath,
) -> None:
    key = path.as_posix().casefold()
    if previous := seen.get(key):
        raise ValueError(
            f"archive contains duplicate or aliasing members: {previous!r}, {raw_name!r}"
        )
    seen[key] = raw_name


def _is_sdist_source(name: str) -> bool:
    path = PurePosixPath(name)
    if name in SDIST_ROOT_SOURCE_FILES or name.startswith("agency_runtime/"):
        return True
    if name.startswith("scripts/"):
        return path.suffix == ".py"
    if name.startswith("tests/"):
        return path.suffix in {".mjs", ".py"}
    if name.startswith("docs/"):
        return path.suffix == ".md"
    if name.startswith("examples/"):
        return path.suffix in {".json", ".md", ".yaml", ".yml"}
    return False


def _partition_release_payloads(names: set[str]) -> tuple[set[str], set[str]]:
    """Partition committed wheel package files and other sdist source inputs."""

    package = {name for name in names if name.startswith("agency_runtime/")}
    support = {name for name in names if _is_sdist_source(name) and name not in package}
    return package, support


def _git_output(root: Path, args: list[str]) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-c", "core.longpaths=true", *args],
            cwd=root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise ValueError(
            "distribution verification requires a Git checkout and executable"
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            "distribution verification requires a clean Git checkout at the reviewed HEAD: "
            f"{detail or 'git failed'}"
        )
    return completed.stdout


def _full_object_id(value: str) -> bool:
    return bool(re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value))


def _assert_live_reviewed_commit(root: Path, reviewed_commit: str) -> None:
    live = _git_output(root, ["rev-parse", "--verify", "HEAD^{commit}"]).decode("ascii").strip()
    if live != reviewed_commit:
        raise ValueError(
            "distribution verification live HEAD does not match the reviewed commit: "
            f"expected {reviewed_commit}, found {live}"
        )


def _reviewed_checkout(root: Path, expected_commit: str) -> str:
    if not _full_object_id(expected_commit):
        raise ValueError("distribution verification requires one full lowercase commit object ID")
    resolved = (
        _git_output(root, ["rev-parse", "--verify", f"{expected_commit}^{{commit}}"])
        .decode("ascii")
        .strip()
    )
    if resolved != expected_commit:
        raise ValueError("distribution verification expected commit is not canonical")
    _assert_live_reviewed_commit(root, expected_commit)
    dirty = _git_output(
        root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"],
    )
    if dirty:
        raise ValueError(
            "distribution verification requires a clean Git checkout with no tracked or "
            "untracked changes"
        )
    return expected_commit


def _tracked_release_payloads(
    root: Path,
    reviewed_commit: str,
) -> tuple[dict[str, str], dict[str, str], str]:
    """Return clean-checkout payload paths and their committed Git blob IDs."""

    inside = _git_output(root, ["rev-parse", "--is-inside-work-tree"]).strip()
    if inside != b"true":
        raise ValueError("distribution verification requires a Git worktree checkout")

    manifest = _git_output(
        root,
        [
            "ls-tree",
            "-r",
            "-z",
            reviewed_commit,
        ],
    )
    entries: dict[str, str] = {}
    algorithms: set[str] = set()
    try:
        for item in manifest.split(b"\0"):
            if not item:
                continue
            metadata, encoded_name = item.split(b"\t", 1)
            mode, object_type, object_id = metadata.split(b" ", 2)
            name = _safe_name(encoded_name.decode("utf-8")).as_posix()
            if not _is_sdist_source(name):
                continue
            if object_type != b"blob" or mode == b"120000":
                raise ValueError(f"committed release payload must be a regular file: {name}")
            digest = object_id.decode("ascii")
            algorithm = "sha1" if len(digest) == 40 else "sha256" if len(digest) == 64 else ""
            if not algorithm or not re.fullmatch(r"[0-9a-f]+", digest):
                raise ValueError(f"committed release payload has an invalid object ID: {name}")
            if name in entries:
                raise ValueError(f"committed release payload is duplicated: {name}")
            entries[name] = digest
            algorithms.add(algorithm)
    except (UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("committed release"):
            raise
        raise ValueError("committed release payload manifest is malformed") from exc

    package_names, support_names = _partition_release_payloads(set(entries))
    package = {name: entries[name] for name in package_names}
    support = {name: entries[name] for name in support_names}
    if not package or not support or "pyproject.toml" not in support or "LICENSE" not in support:
        raise ValueError("committed release payload manifest is incomplete")
    if len(algorithms) != 1:
        raise ValueError("committed release payload manifest mixes object hash algorithms")
    return package, support, algorithms.pop()


def _committed_blob(root: Path, object_id: str) -> bytes:
    return _git_output(root, ["cat-file", "blob", object_id])


def _literal_release_version(payload: bytes, *, source: str) -> str:
    try:
        tree = ast.parse(payload.decode("utf-8"), filename=source)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"committed release version source is invalid: {source}") from exc
    values: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == "__version__"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            values.append(node.value.value)
    if len(values) != 1 or VERSION_PATTERN.fullmatch(values[0]) is None:
        raise ValueError("committed package must define one canonical literal __version__")
    return values[0]


def _normalized_requirement(
    value: str,
    *,
    extra: str | None = None,
    additional_marker: str | None = None,
) -> str:
    try:
        requirement = Requirement(value)
        parsed_additional = Marker(additional_marker) if additional_marker else None
    except (InvalidMarker, InvalidRequirement) as exc:
        raise ValueError(f"invalid release dependency: {value!r}") from exc
    normalized_extras = sorted(canonicalize_name(extra) for extra in requirement.extras)
    extras = f"[{','.join(normalized_extras)}]" if normalized_extras else ""
    normalized = f"{canonicalize_name(requirement.name)}{extras}"
    if requirement.url:
        normalized += f"@{requirement.url}"
    else:
        normalized += str(requirement.specifier)
    marker_parts = [f"({requirement.marker})"] if requirement.marker else []
    if parsed_additional is not None:
        marker_parts.append(f"({parsed_additional})")
    if extra is not None:
        marker_parts.append(f'extra == "{canonicalize_name(extra)}"')
    if marker_parts:
        normalized += f";{Marker(' and '.join(marker_parts))}"
    return normalized


def _normalized_dependencies(
    values: object,
    *,
    source: str,
    extra: str | None = None,
    additional_marker: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"{source} dependencies must be a list of requirement strings")
    normalized = tuple(
        _normalized_requirement(
            value,
            extra=extra,
            additional_marker=additional_marker,
        )
        for value in values
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{source} dependencies contain duplicates")
    return tuple(sorted(normalized))


def _committed_project_contract(
    root: Path,
    package: dict[str, str],
    support: dict[str, str],
) -> tuple[str, tuple[str, ...], bytes]:
    try:
        version_blob = _committed_blob(root, package["agency_runtime/__init__.py"])
        pyproject_blob = _committed_blob(root, support["pyproject.toml"])
        license_blob = _committed_blob(root, support["LICENSE"])
        project = tomllib.loads(pyproject_blob.decode("utf-8"))["project"]
        dependencies = list(
            _normalized_dependencies(
                project.get("dependencies"),
                source="committed pyproject",
            )
        )
        optional = project.get("optional-dependencies", {})
        if not isinstance(optional, dict) or any(not isinstance(name, str) for name in optional):
            raise ValueError("committed optional dependencies are malformed")
        for extra, values in optional.items():
            dependencies.extend(
                _normalized_dependencies(
                    values,
                    source=f"committed pyproject optional dependency {extra}",
                    extra=extra,
                )
            )
    except (KeyError, TypeError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("committed release project metadata is malformed") from exc
    version = _literal_release_version(
        version_blob,
        source="agency_runtime/__init__.py",
    )
    if len(dependencies) != len(set(dependencies)):
        raise ValueError("committed project dependency metadata contains duplicates")
    return version, tuple(sorted(dependencies)), license_blob


def _git_blob_id(payload: bytes, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    digest.update(f"blob {len(payload)}\0".encode("ascii"))
    digest.update(payload)
    return digest.hexdigest()


def _committed_payload_failures(
    artifact: str,
    payloads: dict[str, bytes],
    committed: dict[str, str],
    algorithm: str,
) -> list[str]:
    changed = sorted(
        name
        for name, object_id in committed.items()
        if name in payloads and _git_blob_id(payloads[name], algorithm) != object_id
    )
    if not changed:
        return []
    return [f"{artifact} payload differs from committed HEAD: {', '.join(changed)}"]


def _junk_reason(name: str) -> str | None:
    path = _safe_name(name)
    if any(part in FORBIDDEN_PARTS for part in path.parts):
        return "generated directory or file"
    if any(part.startswith(".env.") and part != ".env.example" for part in path.parts):
        return "environment secret file"
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        return "generated/runtime suffix"
    if path.name.endswith((".db-shm", ".db-wal", ".sqlite-shm", ".sqlite-wal")):
        return "generated/runtime sidecar"
    return None


def _check_member_limits(
    *,
    artifact: str,
    count: int,
    declared_size: int,
    accumulated_size: int,
) -> int:
    if count > MAX_ARCHIVE_MEMBERS:
        raise ValueError(f"{artifact} exceeds the archive member count limit")
    if declared_size < 0 or declared_size > MAX_ARCHIVE_MEMBER_BYTES:
        raise ValueError(f"{artifact} member exceeds the declared size limit")
    total = accumulated_size + declared_size
    if total > MAX_ARCHIVE_TOTAL_BYTES:
        raise ValueError(f"{artifact} exceeds the total uncompressed size limit")
    return total


def _read_member(stream: object, *, declared_size: int, label: str) -> bytes:
    read = getattr(stream, "read", None)
    if not callable(read):
        raise ValueError(f"unable to read archive member: {label}")
    chunks: list[bytes] = []
    observed = 0
    while True:
        chunk = read(min(READ_CHUNK_BYTES, declared_size + 1 - observed))
        if not isinstance(chunk, bytes):
            raise ValueError(f"archive member did not yield bytes: {label}")
        if not chunk:
            break
        chunks.append(chunk)
        observed += len(chunk)
        if observed > declared_size:
            raise ValueError(f"archive member exceeds its declared size: {label}")
    if observed != declared_size:
        raise ValueError(f"archive member is shorter than its declared size: {label}")
    return b"".join(chunks)


def _preflight_zip_member_count(path: Path) -> None:
    size = path.stat().st_size
    trailer_size = min(size, 65_557)
    with path.open("rb") as stream:
        stream.seek(size - trailer_size)
        trailer = stream.read(trailer_size)
    marker = trailer.rfind(b"PK\x05\x06")
    if marker < 0 or len(trailer) - marker < 22:
        raise ValueError("wheel is missing a canonical ZIP end record")
    (
        disk_number,
        directory_disk,
        disk_members,
        total_members,
        _directory_size,
        _directory_offset,
        comment_size,
    ) = struct.unpack_from("<4H2LH", trailer, marker + 4)
    if marker + 22 + comment_size != len(trailer):
        raise ValueError("wheel has a noncanonical ZIP trailer")
    if disk_number or directory_disk or disk_members != total_members or total_members == 0xFFFF:
        raise ValueError("wheel must be a single-disk non-ZIP64 archive")
    if total_members > MAX_ARCHIVE_MEMBERS:
        raise ValueError("wheel exceeds the archive member count limit")


def _wheel_payload(path: Path) -> tuple[set[str], dict[str, bytes]]:
    _preflight_zip_member_count(path)
    with zipfile.ZipFile(path) as archive:
        names = set()
        payloads: dict[str, bytes] = {}
        seen: dict[str, str] = {}
        total_size = 0
        for count, item in enumerate(archive.infolist(), start=1):
            member = _safe_name(item.filename)
            _register_archive_member(seen, raw_name=item.filename, path=member)
            name = member.as_posix()
            total_size = _check_member_limits(
                artifact="wheel",
                count=count,
                declared_size=item.file_size,
                accumulated_size=total_size,
            )
            if item.is_dir():
                raise ValueError(f"wheel contains a non-file member: {item.filename}")
            file_type = stat.S_IFMT(item.external_attr >> 16)
            if file_type not in {0, stat.S_IFREG}:
                raise ValueError(f"wheel contains a non-regular member: {item.filename}")
            if item.file_size and (
                item.compress_size <= 0
                or item.file_size / item.compress_size > MAX_ZIP_COMPRESSION_RATIO
            ):
                raise ValueError(f"wheel member exceeds the compression ratio limit: {name}")
            names.add(name)
            with archive.open(item, mode="r") as stream:
                payloads[name] = _read_member(
                    stream,
                    declared_size=item.file_size,
                    label=item.filename,
                )
        return names, payloads


def _sdist_payload(
    path: Path,
    *,
    expected_root: str | None = None,
) -> tuple[set[str], dict[str, bytes]]:
    with tarfile.open(path, mode="r:gz") as archive:
        seen: dict[str, str] = {}
        validated: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
        total_size = 0
        for count, item in enumerate(archive, start=1):
            path_name = _safe_name(item.name)
            _register_archive_member(seen, raw_name=item.name, path=path_name)
            if item.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}:
                raise ValueError(f"sdist contains an unsupported member type: {item.name}")
            canonical = path_name.as_posix()
            if item.isdir():
                if item.name not in {canonical, f"{canonical}/"} or item.size != 0:
                    raise ValueError(f"sdist contains a noncanonical directory: {item.name}")
                declared_size = 0
            else:
                if item.name != canonical:
                    raise ValueError(f"sdist contains a noncanonical regular file: {item.name}")
                declared_size = item.size
            total_size = _check_member_limits(
                artifact="sdist",
                count=count,
                declared_size=declared_size,
                accumulated_size=total_size,
            )
            validated.append((item, path_name))
        roots = {path_name.parts[0] for _item, path_name in validated}
        if len(roots) != 1:
            raise ValueError(f"sdist must have one top-level directory, found {sorted(roots)}")
        root = next(iter(roots))
        if expected_root is not None and root != expected_root:
            raise ValueError(f"sdist has unexpected top-level directory: {root}")
        names = set()
        payloads: dict[str, bytes] = {}
        for item, path_name in validated:
            stripped = PurePosixPath(*path_name.parts[1:]).as_posix()
            if stripped == ".":
                if not item.isdir():
                    raise ValueError("sdist top-level member must be a directory")
                continue
            names.add(stripped)
            if item.type in {tarfile.REGTYPE, tarfile.AREGTYPE}:
                extracted = archive.extractfile(item)
                if extracted is None:
                    raise ValueError(f"unable to read sdist member: {item.name}")
                with extracted:
                    payloads[stripped] = _read_member(
                        extracted,
                        declared_size=item.size,
                        label=item.name,
                    )
        return names, payloads


def _metadata(payloads: dict[str, bytes]) -> tuple[str, bytes]:
    matches = [
        (name, data) for name, data in payloads.items() if name.endswith(".dist-info/METADATA")
    ]
    if len(matches) != 1:
        raise ValueError(f"wheel must contain one METADATA file, found {len(matches)}")
    return matches[0]


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _missing_file_failures(
    wheel_names: set[str],
    sdist_names: set[str],
    required_package_files: set[str],
    required_sdist_files: set[str] | None = None,
) -> list[str]:
    failures: list[str] = []
    sdist_required = REQUIRED_SDIST_FILES if required_sdist_files is None else required_sdist_files
    missing_wheel = sorted(required_package_files - wheel_names)
    missing_sdist = sorted((sdist_required | required_package_files) - sdist_names)
    if missing_wheel:
        failures.append(f"wheel missing required files: {', '.join(missing_wheel)}")
    if missing_sdist:
        failures.append(f"sdist missing required files: {', '.join(missing_sdist)}")
    return failures


def _unexpected_scoped_payload_failures(
    artifact: str,
    names: set[str],
    expected: set[str],
    *,
    prefixes: tuple[str, ...],
) -> list[str]:
    observed = {name for name in names if name.startswith(prefixes)}
    unexpected = sorted(observed - expected)
    if not unexpected:
        return []
    return [f"{artifact} contains unexpected source payload: {', '.join(unexpected)}"]


def _wheel_payload_contract_failures(
    payloads: dict[str, bytes],
    committed_package_files: set[str],
    *,
    version: str,
) -> list[str]:
    dist_info = f"agency_runtime-{version}.dist-info"
    expected = committed_package_files | {
        f"{dist_info}/{relative}" for relative in WHEEL_METADATA_FILES
    }
    unexpected = sorted(set(payloads) - expected)
    if not unexpected:
        return []
    return [f"wheel contains unexpected payload: {', '.join(unexpected)}"]


def _sdist_payload_contract_failures(
    payloads: dict[str, bytes],
    committed_source_files: set[str],
) -> list[str]:
    expected = committed_source_files | SDIST_GENERATED_METADATA_FILES
    unexpected = sorted(set(payloads) - expected)
    if not unexpected:
        return []
    return [f"sdist contains unexpected payload: {', '.join(unexpected)}"]


def _artifact_identity_failures(
    wheels: list[Path],
    sdists: list[Path],
    *,
    version: str,
) -> list[str]:
    failures: list[str] = []
    expected_wheel = f"agency_runtime-{version}-py3-none-any.whl"
    expected_sdist = f"agency_runtime-{version}.tar.gz"
    if len(wheels) != 1 or wheels[0].name != expected_wheel:
        failures.append(f"expected exact wheel filename: {expected_wheel}")
    if len(sdists) != 1 or sdists[0].name != expected_sdist:
        failures.append(f"expected exact sdist filename: {expected_sdist}")
    return failures


def _junk_failures(artifact: str, names: set[str]) -> list[str]:
    junk: list[str] = []
    for name in names:
        reason = _junk_reason(name)
        if reason:
            junk.append(f"{name} ({reason})")
    if not junk:
        return []
    return [f"{artifact} contains generated junk: {', '.join(sorted(junk))}"]


def _payload_mismatch_failures(
    names: set[str], wheel_payloads: dict[str, bytes], sdist_payloads: dict[str, bytes]
) -> list[str]:
    shared = names & set(wheel_payloads) & set(sdist_payloads)
    return [
        f"wheel/sdist payload mismatch: {name}"
        for name in sorted(shared)
        if _hash(wheel_payloads[name]) != _hash(sdist_payloads[name])
    ]


def _console_scripts_payload_failures(payload: bytes, *, label: str) -> list[str]:
    try:
        entries = configparser.ConfigParser(interpolation=None, strict=True)
        entries.optionxform = str
        entries.read_string(payload.decode("utf-8"))
        observed = (
            dict(entries.items("console_scripts", raw=True))
            if not entries.defaults() and entries.sections() == ["console_scripts"]
            else {}
        )
    except (UnicodeDecodeError, configparser.Error):
        observed = {}
    if observed == EXPECTED_CONSOLE_SCRIPTS:
        return []
    return [f"{label} console entry point contract is invalid"]


def _console_script_failures(
    dist_info: str,
    wheel_payloads: dict[str, bytes],
) -> list[str]:
    payload = wheel_payloads.get(f"{dist_info}/entry_points.txt")
    if payload is None:
        return []
    return _console_scripts_payload_failures(payload, label="wheel")


def _top_level_package_failures(
    dist_info: str,
    wheel_payloads: dict[str, bytes],
) -> list[str]:
    payload = wheel_payloads.get(f"{dist_info}/top_level.txt")
    if payload is None:
        return []
    try:
        top_levels = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        top_levels = []
    if top_levels == ["agency_runtime"]:
        return []
    return ["wheel top-level package contract is invalid"]


def _singleton_header(
    metadata: Message,
    name: str,
    *,
    label: str,
) -> tuple[str | None, list[str]]:
    values = metadata.get_all(name, [])
    if len(values) == 1:
        return values[0], []
    return None, [f"{label} must contain exactly one {name} header"]


def _project_metadata_failures(
    metadata: Message,
    *,
    label: str,
    expected_version: str,
    expected_dependencies: tuple[str, ...],
    require_classifiers: bool,
) -> list[str]:
    failures: list[str] = []
    if metadata.defects:
        failures.append(f"{label} contains malformed email metadata")
    expected_headers = {
        "Metadata-Version": "2.4",
        "Name": "agency-runtime",
        "Version": expected_version,
        "Requires-Python": ">=3.10",
        "License-Expression": "MIT",
    }
    for name, expected in expected_headers.items():
        observed, singleton_failures = _singleton_header(metadata, name, label=label)
        failures.extend(singleton_failures)
        if observed is not None and observed != expected:
            failures.append(f"{label} has unexpected {name}: {observed!r}")

    requirements = metadata.get_all("Requires-Dist", [])
    try:
        observed_dependencies = _normalized_dependencies(requirements, source=label)
    except ValueError:
        observed_dependencies = ()
        failures.append(f"{label} dependency metadata is invalid or duplicated")
    if observed_dependencies != expected_dependencies:
        failures.append(f"{label} dependency metadata does not match committed pyproject")

    if require_classifiers:
        classifiers = set(metadata.get_all("Classifier", []))
        missing_classifiers = sorted(REQUIRED_CLASSIFIERS - classifiers)
        if missing_classifiers:
            failures.append(f"missing classifiers: {', '.join(missing_classifiers)}")
    return failures


def _wheel_control_failures(dist_info: str, wheel_payloads: dict[str, bytes]) -> list[str]:
    payload = wheel_payloads.get(f"{dist_info}/WHEEL")
    if payload is None:
        return []
    try:
        metadata = BytesParser(policy=policy.default).parsebytes(payload)
    except (TypeError, ValueError):
        return ["wheel control metadata is invalid"]
    header_counts = Counter(name.lower() for name, _value in metadata.raw_items())
    allowed = {"generator", "root-is-purelib", "tag", "wheel-version"}
    failures: list[str] = []
    if metadata.defects or set(header_counts) - allowed:
        failures.append("wheel control metadata contains unsupported headers or syntax")
    expected = {
        "wheel-version": "1.0",
        "root-is-purelib": "true",
        "tag": "py3-none-any",
    }
    for name, value in expected.items():
        if header_counts[name] != 1 or metadata.get(name) != value:
            failures.append(f"wheel control metadata has invalid {name}")
    if header_counts["generator"] > 1:
        failures.append("wheel control metadata has duplicate generator headers")
    body = metadata.get_payload()
    if isinstance(body, str) and body.strip():
        failures.append("wheel control metadata contains an unexpected body")
    return failures


def _record_failures(dist_info: str, wheel_payloads: dict[str, bytes]) -> list[str]:
    record_name = f"{dist_info}/RECORD"
    payload = wheel_payloads.get(record_name)
    if payload is None:
        return []
    rows: dict[str, tuple[str, str]] = {}
    seen: dict[str, str] = {}
    try:
        reader = csv.reader(io.StringIO(payload.decode("utf-8"), newline=""), strict=True)
        for row in reader:
            if len(row) != 3:
                raise ValueError("RECORD row must contain three columns")
            raw_name, digest, size = row
            path = _safe_name(raw_name)
            _register_archive_member(seen, raw_name=raw_name, path=path)
            rows[path.as_posix()] = (digest, size)
    except (UnicodeDecodeError, csv.Error, ValueError):
        return ["wheel RECORD is malformed, duplicated, or noncanonical"]

    failures: list[str] = []
    expected_names = set(wheel_payloads)
    missing = sorted(expected_names - set(rows))
    extra = sorted(set(rows) - expected_names)
    if missing:
        failures.append(f"wheel RECORD missing members: {', '.join(missing)}")
    if extra:
        failures.append(f"wheel RECORD contains extra members: {', '.join(extra)}")
    for name in sorted(expected_names & set(rows)):
        digest, size = rows[name]
        if name == record_name:
            if digest or size:
                failures.append("wheel RECORD self row must have empty hash and size")
            continue
        expected_digest = (
            base64.urlsafe_b64encode(hashlib.sha256(wheel_payloads[name]).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        if digest != f"sha256={expected_digest}" or size != str(len(wheel_payloads[name])):
            failures.append(f"wheel RECORD hash or size mismatch: {name}")
    return failures


def _setup_cfg_failures(payload: bytes) -> list[str]:
    try:
        config = configparser.ConfigParser(interpolation=None, strict=True)
        config.optionxform = str
        config.read_string(payload.decode("utf-8"))
        observed = (
            dict(config.items("egg_info", raw=True))
            if not config.defaults() and config.sections() == ["egg_info"]
            else {}
        )
    except (UnicodeDecodeError, configparser.Error):
        observed = {}
    if observed == {"tag_build": "", "tag_date": "0"}:
        return []
    return ["sdist generated setup.cfg contract is invalid"]


def _sources_manifest_failures(payload: bytes, sdist_payloads: dict[str, bytes]) -> list[str]:
    seen: dict[str, str] = {}
    observed: set[str] = set()
    try:
        lines = payload.decode("utf-8").splitlines()
        if not lines or any(not line for line in lines):
            raise ValueError("empty source manifest row")
        for line in lines:
            path = _safe_name(line)
            _register_archive_member(seen, raw_name=line, path=path)
            observed.add(path.as_posix())
    except (UnicodeDecodeError, ValueError):
        return ["sdist generated SOURCES.txt is malformed or duplicated"]
    expected = set(sdist_payloads) - {"PKG-INFO", "setup.cfg"}
    if observed == expected:
        return []
    return ["sdist generated SOURCES.txt does not match the exact payload manifest"]


def _requires_txt_dependencies(payload: bytes) -> tuple[str, ...]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("requires.txt is not UTF-8") from exc
    dependencies: list[str] = []
    current_extra: str | None = None
    current_marker: str | None = None
    for line in lines:
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            current_extra, separator, marker = section.partition(":")
            if not current_extra or not re.fullmatch(r"[A-Za-z0-9._-]+", current_extra):
                raise ValueError("requires.txt has an invalid extra section")
            current_marker = marker if separator else None
            continue
        dependencies.append(
            _normalized_requirement(
                line,
                extra=current_extra,
                additional_marker=current_marker,
            )
        )
    if len(dependencies) != len(set(dependencies)):
        raise ValueError("requires.txt dependencies contain duplicates")
    return tuple(sorted(dependencies))


def _sdist_generated_metadata_failures(
    payloads: dict[str, bytes],
    *,
    expected_version: str,
    expected_dependencies: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    missing = sorted(SDIST_GENERATED_METADATA_FILES - set(payloads))
    if missing:
        failures.append(f"sdist missing generated metadata files: {', '.join(missing)}")

    package_info_names = ("PKG-INFO", "agency_runtime.egg-info/PKG-INFO")
    for name in package_info_names:
        payload = payloads.get(name)
        if payload is not None:
            metadata = BytesParser(policy=policy.default).parsebytes(payload)
            failures.extend(
                _project_metadata_failures(
                    metadata,
                    label=f"sdist {name}",
                    expected_version=expected_version,
                    expected_dependencies=expected_dependencies,
                    require_classifiers=True,
                )
            )
    root_info = payloads.get(package_info_names[0])
    egg_info = payloads.get(package_info_names[1])
    if root_info is not None and egg_info is not None and root_info != egg_info:
        failures.append("sdist PKG-INFO copies differ")

    entry_points = payloads.get("agency_runtime.egg-info/entry_points.txt")
    if entry_points is not None:
        failures.extend(_console_scripts_payload_failures(entry_points, label="sdist"))
    top_level = payloads.get("agency_runtime.egg-info/top_level.txt")
    if top_level is not None:
        try:
            top_levels = top_level.decode("utf-8").splitlines()
        except UnicodeDecodeError:
            top_levels = []
        if top_levels != ["agency_runtime"]:
            failures.append("sdist generated top_level.txt contract is invalid")

    requires = payloads.get("agency_runtime.egg-info/requires.txt")
    if requires is not None:
        try:
            observed_dependencies = _requires_txt_dependencies(requires)
        except ValueError:
            observed_dependencies = ()
            failures.append("sdist generated requires.txt is invalid or duplicated")
        if observed_dependencies != expected_dependencies:
            failures.append("sdist generated requires.txt does not match committed pyproject")

    dependency_links = payloads.get("agency_runtime.egg-info/dependency_links.txt")
    if dependency_links is not None and dependency_links.strip():
        failures.append("sdist generated dependency_links.txt must be empty")
    setup_cfg = payloads.get("setup.cfg")
    if setup_cfg is not None:
        failures.extend(_setup_cfg_failures(setup_cfg))
    sources = payloads.get("agency_runtime.egg-info/SOURCES.txt")
    if sources is not None:
        failures.extend(_sources_manifest_failures(sources, payloads))
    return failures


def _metadata_failures(
    metadata_name: str,
    metadata: Message,
    wheel_names: set[str],
    wheel_payloads: dict[str, bytes],
    *,
    expected_version: str,
    expected_dependencies: tuple[str, ...],
    expected_license: bytes,
) -> list[str]:
    failures = _project_metadata_failures(
        metadata,
        label="wheel METADATA",
        expected_version=expected_version,
        expected_dependencies=expected_dependencies,
        require_classifiers=True,
    )
    expected_dist_info = f"agency_runtime-{expected_version}.dist-info"
    if metadata_name != f"{expected_dist_info}/METADATA":
        failures.append(f"unexpected wheel metadata path: {metadata_name}")

    for required in sorted(WHEEL_METADATA_FILES - {"METADATA"}):
        name = f"{expected_dist_info}/{required}"
        if name not in wheel_names:
            failures.append(f"wheel missing metadata file: {name}")

    license_payload = wheel_payloads.get(f"{expected_dist_info}/licenses/LICENSE")
    if license_payload is not None and license_payload != expected_license:
        failures.append("wheel license payload differs from committed HEAD")
    failures.extend(_wheel_control_failures(expected_dist_info, wheel_payloads))
    failures.extend(_console_script_failures(expected_dist_info, wheel_payloads))
    failures.extend(_top_level_package_failures(expected_dist_info, wheel_payloads))
    failures.extend(_record_failures(expected_dist_info, wheel_payloads))
    return failures


def verify(
    dist_dir: Path,
    *,
    repository_root: Path | None = None,
    expected_commit: str | None = None,
) -> list[str]:
    failures: list[str] = []
    if expected_commit is None:
        return ["distribution verification requires an expected reviewed commit"]
    root = (
        Path(__file__).resolve().parents[1]
        if repository_root is None
        else repository_root.resolve()
    )
    try:
        reviewed_commit = _reviewed_checkout(root, expected_commit)
        committed_package, committed_support, object_algorithm = _tracked_release_payloads(
            root,
            reviewed_commit,
        )
        version, expected_dependencies, expected_license = _committed_project_contract(
            root,
            committed_package,
            committed_support,
        )
    except (OSError, ValueError) as exc:
        return [str(exc)]

    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    identity_failures = _artifact_identity_failures(wheels, sdists, version=version)
    if identity_failures:
        return identity_failures

    try:
        wheel_names, wheel_payloads = _wheel_payload(wheels[0])
        sdist_names, sdist_payloads = _sdist_payload(
            sdists[0],
            expected_root=f"agency_runtime-{version}",
        )
    except (OSError, tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
        return [str(exc)]

    try:
        metadata_name, metadata_payload = _metadata(wheel_payloads)
        metadata = BytesParser(policy=policy.default).parsebytes(metadata_payload)
    except ValueError as exc:
        return [str(exc)]

    committed_package_files = set(committed_package)
    committed_support_files = set(committed_support)
    committed_sdist_files = committed_package_files | committed_support_files
    required_package_files = REQUIRED_PACKAGE_FILES | committed_package_files
    required_sdist_files = REQUIRED_SDIST_FILES | committed_sdist_files
    failures.extend(
        _missing_file_failures(
            set(wheel_payloads),
            set(sdist_payloads),
            required_package_files,
            required_sdist_files,
        )
    )
    failures.extend(
        _wheel_payload_contract_failures(
            wheel_payloads,
            committed_package_files,
            version=version,
        )
    )
    failures.extend(_sdist_payload_contract_failures(sdist_payloads, committed_sdist_files))
    for artifact, names in (("wheel", wheel_names), ("sdist", sdist_names)):
        failures.extend(_junk_failures(artifact, names))
    failures.extend(
        _payload_mismatch_failures(
            required_package_files,
            wheel_payloads,
            sdist_payloads,
        )
    )
    failures.extend(
        _committed_payload_failures(
            "wheel",
            wheel_payloads,
            committed_package,
            object_algorithm,
        )
    )
    failures.extend(
        _committed_payload_failures(
            "sdist package",
            sdist_payloads,
            committed_package,
            object_algorithm,
        )
    )
    failures.extend(
        _committed_payload_failures(
            "sdist release support",
            sdist_payloads,
            committed_support,
            object_algorithm,
        )
    )
    failures.extend(
        _metadata_failures(
            metadata_name,
            metadata,
            set(wheel_payloads),
            wheel_payloads,
            expected_version=version,
            expected_dependencies=expected_dependencies,
            expected_license=expected_license,
        )
    )
    failures.extend(
        _sdist_generated_metadata_failures(
            sdist_payloads,
            expected_version=version,
            expected_dependencies=expected_dependencies,
        )
    )
    try:
        _reviewed_checkout(root, reviewed_commit)
    except (OSError, ValueError) as exc:
        failures.append(str(exc))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    parser.add_argument(
        "--expected-commit",
        required=True,
        help="Full immutable Git commit object ID captured before the build",
    )
    args = parser.parse_args(argv)
    failures = verify(args.dist_dir.resolve(), expected_commit=args.expected_commit)
    if failures:
        print("Distribution verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Distribution verification passed (wheel and sdist contents match release policy).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
