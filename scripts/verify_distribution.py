"""Verify built Agency Runtime wheel and source distribution contents."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tarfile
import zipfile
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

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
PACKAGE_SOURCE_SUFFIXES = {".css", ".html", ".js", ".json", ".py", ".yaml", ".yml"}


def _source_package_files() -> set[str]:
    """Return every source-controlled package payload expected in artifacts."""

    package_root = Path(__file__).resolve().parents[1] / "agency_runtime"
    return {
        path.relative_to(package_root.parent).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path.suffix.lower() in PACKAGE_SOURCE_SUFFIXES
    }


def _safe_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive member: {name}")
    return path


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


def _wheel_payload(path: Path) -> tuple[set[str], dict[str, bytes]]:
    with zipfile.ZipFile(path) as archive:
        names = set()
        payloads: dict[str, bytes] = {}
        for item in archive.infolist():
            name = _safe_name(item.filename).as_posix()
            names.add(name)
            if not item.is_dir():
                payloads[name] = archive.read(item)
        return names, payloads


def _sdist_payload(path: Path) -> tuple[set[str], dict[str, bytes]]:
    with tarfile.open(path, mode="r:gz") as archive:
        members = archive.getmembers()
        roots = {_safe_name(item.name).parts[0] for item in members if _safe_name(item.name).parts}
        if len(roots) != 1:
            raise ValueError(f"sdist must have one top-level directory, found {sorted(roots)}")
        names = set()
        payloads: dict[str, bytes] = {}
        for item in members:
            path_name = _safe_name(item.name)
            if item.issym() or item.islnk():
                raise ValueError(f"sdist contains a link: {item.name}")
            stripped = PurePosixPath(*path_name.parts[1:]).as_posix()
            if stripped == ".":
                continue
            names.add(stripped)
            if item.isfile():
                extracted = archive.extractfile(item)
                if extracted is None:
                    raise ValueError(f"unable to read sdist member: {item.name}")
                payloads[stripped] = extracted.read()
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
) -> list[str]:
    failures: list[str] = []
    missing_wheel = sorted(required_package_files - wheel_names)
    missing_sdist = sorted((REQUIRED_SDIST_FILES | required_package_files) - sdist_names)
    if missing_wheel:
        failures.append(f"wheel missing required files: {', '.join(missing_wheel)}")
    if missing_sdist:
        failures.append(f"sdist missing required files: {', '.join(missing_sdist)}")
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
    return [
        f"wheel/sdist payload mismatch: {name}"
        for name in sorted(names)
        if _hash(wheel_payloads[name]) != _hash(sdist_payloads[name])
    ]


def _metadata_failures(
    metadata_name: str,
    metadata: Message,
    wheel_names: set[str],
    wheel_payloads: dict[str, bytes],
) -> list[str]:
    failures: list[str] = []
    if metadata.get("Name") != "agency-runtime":
        failures.append(f"unexpected package name: {metadata.get('Name')!r}")
    version = metadata.get("Version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-z]+\d+)?", version):
        failures.append(f"version is not a normalized release version: {version!r}")
    if metadata.get("Requires-Python") != ">=3.10":
        failures.append(f"unexpected Requires-Python: {metadata.get('Requires-Python')!r}")
    if metadata.get("License-Expression") != "MIT":
        failures.append(f"unexpected license expression: {metadata.get('License-Expression')!r}")
    classifiers = set(metadata.get_all("Classifier", []))
    missing_classifiers = sorted(REQUIRED_CLASSIFIERS - classifiers)
    if missing_classifiers:
        failures.append(f"missing classifiers: {', '.join(missing_classifiers)}")
    requirements = metadata.get_all("Requires-Dist", [])
    if not any(
        re.match(r"pyyaml<7,>=6\.0(?:;|$)", requirement.lower()) for requirement in requirements
    ):
        failures.append("runtime dependency metadata does not constrain PyYAML to >=6.0,<7")

    dist_info = metadata_name.rsplit("/", 1)[0]
    for required in ("WHEEL", "RECORD", "entry_points.txt", "licenses/LICENSE"):
        name = f"{dist_info}/{required}"
        if name not in wheel_names:
            failures.append(f"wheel missing metadata file: {name}")
    wheel_metadata = wheel_payloads.get(f"{dist_info}/WHEEL", b"").decode("utf-8", errors="replace")
    if "Tag: py3-none-any" not in wheel_metadata:
        failures.append("wheel is not tagged py3-none-any")
    return failures


def verify(dist_dir: Path) -> list[str]:
    failures: list[str] = []
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        return [
            f"expected one wheel and one sdist, found {len(wheels)} wheel(s) and {len(sdists)} sdist(s)"
        ]

    try:
        wheel_names, wheel_payloads = _wheel_payload(wheels[0])
        sdist_names, sdist_payloads = _sdist_payload(sdists[0])
    except (OSError, tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
        return [str(exc)]

    required_package_files = REQUIRED_PACKAGE_FILES | _source_package_files()
    failures.extend(_missing_file_failures(wheel_names, sdist_names, required_package_files))
    for artifact, names in (("wheel", wheel_names), ("sdist", sdist_names)):
        failures.extend(_junk_failures(artifact, names))
    failures.extend(
        _payload_mismatch_failures(
            required_package_files & wheel_names & sdist_names,
            wheel_payloads,
            sdist_payloads,
        )
    )

    try:
        metadata_name, metadata_payload = _metadata(wheel_payloads)
        metadata = BytesParser(policy=policy.default).parsebytes(metadata_payload)
    except ValueError as exc:
        failures.append(str(exc))
        return failures

    failures.extend(_metadata_failures(metadata_name, metadata, wheel_names, wheel_payloads))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    failures = verify(args.dist_dir.resolve())
    if failures:
        print("Distribution verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Distribution verification passed (wheel and sdist contents match release policy).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
