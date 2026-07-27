"""Rebuild and byte-verify the reviewed Windows operator-presence helper."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "agency_runtime" / "native" / "windows" / "operator_presence"
SOURCE_PATH = ASSET_ROOT / "operator_presence_verifier.cpp"
EXECUTABLE_PATH = ASSET_ROOT / "operator_presence_verifier.exe"
PROVENANCE_PATH = ASSET_ROOT / "operator_presence_verifier.provenance.json"
SOURCE_RELATIVE = SOURCE_PATH.relative_to(ROOT).as_posix()
EXECUTABLE_RELATIVE = EXECUTABLE_PATH.relative_to(ROOT).as_posix()

VISUAL_STUDIO_SERIES = "17.14"
VISUAL_STUDIO_VERSION = "17.14.37111.16"
MSVC_TOOLS_VERSION = "14.44.35207"
COMPILER_VERSION = "19.44.35225"
WINDOWS_SDK_VERSION = "10.0.26100.0"
MAX_PROVENANCE_BYTES = 8 * 1024
MAX_SOURCE_BYTES = 512 * 1024
MAX_EXECUTABLE_BYTES = 512 * 1024
REVIEWED_SOURCE_SIZE = 26_482
REVIEWED_SOURCE_SHA256 = "8fb94318fcd8dd9c6c624bdd6faa841e5298bed449958dd42b2c22910deed085"
REVIEWED_EXECUTABLE_SIZE = 165_888
REVIEWED_EXECUTABLE_SHA256 = "f525c64775ac49fbb0be7ffcf9b8c5d013ec85ac5756ab6f69be6afe5c9d55fd"

COMPILER_FLAGS = (
    "/nologo",
    "/std:c++20",
    "/permissive-",
    "/EHsc",
    "/W4",
    "/WX",
    "/O2",
    "/MT",
    "/utf-8",
    "/sdl",
    "/guard:cf",
    "/Zc:__cplusplus",
    "/Zc:inline",
    "/Zc:preprocessor",
    "/Zc:wchar_t",
    "/DUNICODE",
    "/D_UNICODE",
    "/D_WIN32_WINNT=0x0A00",
    "/DWINVER=0x0A00",
    "/DNTDDI_VERSION=0x0A000004",
)
LINKER_FLAGS = (
    "/SUBSYSTEM:WINDOWS,10.00",
    "/MACHINE:X64",
    "/INCREMENTAL:NO",
    "/OPT:REF",
    "/OPT:ICF",
    "/Brepro",
    "/RELEASE",
    "/DYNAMICBASE",
    "/NXCOMPAT",
    "/HIGHENTROPYVA",
    "/CETCOMPAT",
    "/guard:cf",
    "/DEPENDENTLOADFLAG:0x800",
    "windowsapp.lib",
    "user32.lib",
    "shell32.lib",
    "advapi32.lib",
    "gdi32.lib",
)

_FORBIDDEN_CMD_PATH = re.compile(r'[&|<>^%!"\r\n]')

EXPECTED_DEPENDENCIES = frozenset(
    {
        "api-ms-win-core-com-l1-1-0.dll",
        "api-ms-win-core-console-l1-1-0.dll",
        "api-ms-win-core-errorhandling-l1-1-0.dll",
        "api-ms-win-core-fibers-l1-1-0.dll",
        "api-ms-win-core-file-l1-1-0.dll",
        "api-ms-win-core-handle-l1-1-0.dll",
        "api-ms-win-core-heap-l1-1-0.dll",
        "api-ms-win-core-heap-l2-1-0.dll",
        "api-ms-win-core-interlocked-l1-1-0.dll",
        "api-ms-win-core-libraryloader-l1-2-0.dll",
        "api-ms-win-core-localization-l1-2-0.dll",
        "api-ms-win-core-memory-l1-1-0.dll",
        "api-ms-win-core-processenvironment-l1-1-0.dll",
        "api-ms-win-core-processthreads-l1-1-0.dll",
        "api-ms-win-core-rtlsupport-l1-1-0.dll",
        "api-ms-win-core-string-l1-1-0.dll",
        "api-ms-win-core-string-obsolete-l1-1-0.dll",
        "api-ms-win-core-synch-l1-1-0.dll",
        "api-ms-win-core-util-l1-1-0.dll",
        "api-ms-win-core-winrt-error-l1-1-1.dll",
        "api-ms-win-core-winrt-l1-1-0.dll",
        "api-ms-win-security-base-l1-1-0.dll",
        "api-ms-win-security-sddl-l1-1-0.dll",
        "api-ms-win-shcore-obsolete-l1-1-0.dll",
        "gdi32.dll",
        "kernel32.dll",
        "oleaut32.dll",
        "user32.dll",
    }
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _vswhere_path() -> Path:
    program_files = Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    path = program_files / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not path.is_file():
        raise RuntimeError("Visual Studio Installer vswhere.exe is unavailable")
    return path


def _visual_studio() -> tuple[Path, str]:
    completed = subprocess.run(
        [
            str(_vswhere_path()),
            "-products",
            "*",
            "-version",
            f"[{VISUAL_STUDIO_SERIES},17.15)",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-format",
            "json",
            "-utf8",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError("vswhere failed while locating exact Visual Studio 2022 17.14")
    try:
        candidates = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("vswhere returned malformed discovery JSON") from exc
    if not isinstance(candidates, list):
        raise RuntimeError("vswhere returned malformed discovery JSON")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        version = candidate.get("installationVersion")
        raw_path = candidate.get("installationPath")
        if (
            isinstance(version, str)
            and version == VISUAL_STUDIO_VERSION
            and isinstance(raw_path, str)
        ):
            path = Path(raw_path).resolve()
            if _FORBIDDEN_CMD_PATH.search(str(path)):
                raise RuntimeError("Visual Studio installation path is unsafe for VsDevCmd")
            tools = path / "VC" / "Tools" / "MSVC" / MSVC_TOOLS_VERSION
            if tools.is_dir():
                return path, version
    raise RuntimeError("exact Visual Studio 2022 17.14 with MSVC tools 14.44.35207 is unavailable")


def _toolchain_environment(installation: Path) -> dict[str, str]:
    command = installation / "Common7" / "Tools" / "VsDevCmd.bat"
    if not command.is_file():
        raise RuntimeError("Visual Studio 2022 VsDevCmd.bat is unavailable")
    with tempfile.TemporaryDirectory(prefix="agency-runtime-vsenv-") as temporary:
        batch = Path(temporary) / "capture-environment.cmd"
        batch.write_text(
            "@echo off\n"
            f'call "{command}" -no_logo -arch=x64 -host_arch=x64 '
            f"-vcvars_ver=14.44 -winsdk={WINDOWS_SDK_VERSION} >nul\n"
            "if errorlevel 1 exit /b %errorlevel%\n"
            "set\n",
            encoding="utf-8",
        )
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", str(batch)],
            check=False,
            capture_output=True,
            timeout=30,
        )
    if completed.returncode != 0 or completed.stderr:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            "exact Visual Studio 2022 build environment initialization failed"
            f" (exit={completed.returncode}, stderr={detail!r})"
        )
    try:
        text = completed.stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        text = completed.stdout.decode("mbcs", errors="strict")
    environment = os.environ.copy()
    for line in text.splitlines():
        if "=" not in line or line.startswith("="):
            continue
        name, value = line.split("=", 1)
        environment[name] = value
    for name in tuple(environment):
        if name.upper() in {"CL", "_CL_", "LINK", "_LINK_"}:
            del environment[name]
    vc_version = environment.get("VCToolsVersion", "").rstrip("\\/")
    sdk_version = environment.get("WindowsSDKVersion", "").rstrip("\\/")
    if vc_version != MSVC_TOOLS_VERSION or sdk_version != WINDOWS_SDK_VERSION:
        raise RuntimeError(
            "VsDevCmd did not select the exact reviewed MSVC 14.44 / SDK 26100 toolchain"
        )
    return environment


def _compiler_path(installation: Path) -> Path:
    compiler = (
        installation
        / "VC"
        / "Tools"
        / "MSVC"
        / MSVC_TOOLS_VERSION
        / "bin"
        / "Hostx64"
        / "x64"
        / "cl.exe"
    )
    if not compiler.is_file():
        raise RuntimeError("exact reviewed x64 MSVC compiler is unavailable")
    return compiler


def _dumpbin_path(compiler: Path) -> Path:
    dumpbin = compiler.with_name("dumpbin.exe")
    if not dumpbin.is_file():
        raise RuntimeError("exact reviewed x64 dumpbin is unavailable")
    return dumpbin


def _read_regular_bounded(path: Path, *, maximum: int, label: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise RuntimeError(f"{label} is unavailable") from exc
    reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    attributes = int(getattr(before, "st_file_attributes", 0) or 0)
    if (
        not stat.S_ISREG(before.st_mode)
        or path.is_symlink()
        or attributes & reparse
        or before.st_size <= 0
        or before.st_size > maximum
    ):
        raise RuntimeError(f"{label} is not a bounded non-reparse regular file")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if (
                opened.st_dev != before.st_dev
                or opened.st_ino != before.st_ino
                or opened.st_size != before.st_size
                or not stat.S_ISREG(opened.st_mode)
            ):
                raise RuntimeError(f"{label} changed while it was opened")
            payload = stream.read(maximum + 1)
            if len(payload) != before.st_size or stream.read(1):
                raise RuntimeError(f"{label} changed while it was read")
    except OSError as exc:
        raise RuntimeError(f"{label} is unreadable") from exc
    return payload


def _require_compiler_version(compiler: Path, environment: dict[str, str]) -> None:
    completed = subprocess.run(
        [str(compiler)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode != 0 or f"Version {COMPILER_VERSION} for x64" not in output:
        raise RuntimeError(f"reviewed MSVC compiler {COMPILER_VERSION} is unavailable")


def _run_static_analysis(
    analysis_root: Path,
    *,
    compiler: Path,
    environment: dict[str, str],
    source_payload: bytes,
) -> None:
    analysis_root.mkdir(parents=False, exist_ok=False)
    source = analysis_root / SOURCE_PATH.name
    source.write_bytes(source_payload)
    completed = subprocess.run(
        [
            str(compiler),
            *COMPILER_FLAGS,
            "/external:anglebrackets",
            "/external:W0",
            "/analyze",
            "/analyze:WX-",
            "/analyze:only",
            source.name,
            f"/Fo:{SOURCE_PATH.stem}.analysis.obj",
        ],
        cwd=analysis_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    detail = (completed.stdout + completed.stderr).strip()
    warnings = re.findall(r"(?im)^.*\bwarning\s+([A-Z]\d+):.*$", detail)
    known_sdk_warnings = re.findall(
        r"(?im)^.*[\\/]WindowsNumerics\.inl\(2375\)\s*:\s*warning\s+"
        r"(C28252|C28253|C6101):.*$",
        detail,
    )
    if completed.returncode != 0 or sorted(warnings) != sorted(known_sdk_warnings):
        raise RuntimeError(f"native helper MSVC /analyze pass failed: {detail[-8_192:]}")


def _verify_dumpbin_contract(
    executable: Path,
    *,
    dumpbin: Path,
    environment: dict[str, str],
) -> None:
    completed = subprocess.run(
        [str(dumpbin), "/nologo", "/headers", "/loadconfig", "/dependents", str(executable)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError("dumpbin could not inspect the rebuilt native helper")
    output = completed.stdout
    required_markers = (
        "machine (x64)",
        "subsystem (Windows GUI)",
        "High Entropy Virtual Addresses",
        "Dynamic base",
        "NX compatible",
        "Control Flow Guard",
        "CET compatible",
        "Dependent Load Flag",
        "CF instrumented",
        "FID table present",
    )
    if any(marker not in output for marker in required_markers):
        raise RuntimeError("rebuilt native helper lacks a required dumpbin mitigation marker")
    cookie = re.search(r"(?m)^\s+([0-9A-F]{16}) Security Cookie\s*$", output)
    if cookie is None or int(cookie.group(1), 16) == 0:
        raise RuntimeError("rebuilt native helper lacks a nonzero security cookie")
    section = re.search(
        r"Image has the following dependencies:\r?\n(.*?)"
        r"\r?\n\s*Section contains the following load config:",
        output,
        re.DOTALL,
    )
    if section is None:
        raise RuntimeError("dumpbin did not report the native helper dependency set")
    dependencies = {
        match.group(1).lower()
        for match in re.finditer(r"(?m)^\s+([A-Za-z0-9._-]+\.dll)\s*$", section.group(1))
    }
    if dependencies != EXPECTED_DEPENDENCIES:
        raise RuntimeError(
            "rebuilt native helper dependency set differs from the reviewed contract: "
            f"expected={sorted(EXPECTED_DEPENDENCIES)!r}, observed={sorted(dependencies)!r}"
        )


def _build_once(
    build_root: Path,
    *,
    compiler: Path,
    environment: dict[str, str],
    source_payload: bytes,
) -> bytes:
    build_root.mkdir(parents=False, exist_ok=False)
    source = build_root / SOURCE_PATH.name
    source.write_bytes(source_payload)
    arguments = [
        str(compiler),
        *COMPILER_FLAGS,
        source.name,
        f"/Fo:{SOURCE_PATH.stem}.obj",
        f"/Fe:{EXECUTABLE_PATH.name}",
        "/link",
        *LINKER_FLAGS,
    ]
    completed = subprocess.run(
        arguments,
        cwd=build_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise RuntimeError(f"native helper compilation failed: {detail[-8_192:]}")
    executable = build_root / EXECUTABLE_PATH.name
    if not executable.is_file():
        raise RuntimeError("native helper compiler did not produce the expected executable")
    return _read_regular_bounded(
        executable,
        maximum=MAX_EXECUTABLE_BYTES,
        label="rebuilt native helper",
    )


def _pe_contract(payload: bytes) -> None:
    if len(payload) < 512 or payload[:2] != b"MZ":
        raise RuntimeError("native helper is not a bounded PE executable")
    pe_offset = struct.unpack_from("<I", payload, 0x3C)[0]
    if pe_offset + 24 > len(payload) or payload[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise RuntimeError("native helper PE header is malformed")
    machine = struct.unpack_from("<H", payload, pe_offset + 4)[0]
    optional_size = struct.unpack_from("<H", payload, pe_offset + 20)[0]
    optional = pe_offset + 24
    if optional + optional_size > len(payload) or optional_size < 152:
        raise RuntimeError("native helper optional PE header is malformed")
    magic = struct.unpack_from("<H", payload, optional)[0]
    subsystem = struct.unpack_from("<H", payload, optional + 68)[0]
    dll_characteristics = struct.unpack_from("<H", payload, optional + 70)[0]
    certificate_offset, certificate_size = struct.unpack_from("<II", payload, optional + 144)
    required_characteristics = 0x0020 | 0x0040 | 0x0100 | 0x4000
    if machine != 0x8664 or magic != 0x20B or subsystem != 2:
        raise RuntimeError("native helper must be an x64 Windows-subsystem PE32+ executable")
    if dll_characteristics & required_characteristics != required_characteristics:
        raise RuntimeError("native helper is missing required PE ASLR, NX, or CFG characteristics")
    if certificate_offset != 0 or certificate_size != 0:
        raise RuntimeError("bounded native helper must remain the reviewed unsigned executable")
    if len(payload) > MAX_EXECUTABLE_BYTES:
        raise RuntimeError("native helper exceeds its 512 KiB package-data budget")


def _provenance(
    *,
    source: bytes,
    executable: bytes,
) -> dict[str, Any]:
    return {
        "asset_role": "windows_operator_presence_verifier",
        "build_contract": {
            "compiler_flags": list(COMPILER_FLAGS),
            "deterministic": True,
            "linker_flags": list(LINKER_FLAGS),
        },
        "distribution_classification": "reviewed_unsigned_windows_executable_package_data",
        "executable_path": EXECUTABLE_RELATIVE,
        "executable_sha256": _sha256(executable),
        "executable_size": len(executable),
        "schema_version": 1,
        "source_path": SOURCE_RELATIVE,
        "source_sha256": _sha256(source),
        "source_size": len(source),
        "target": {
            "architecture": "x86_64",
            "minimum_windows_build": 22000,
            "subsystem": "windows",
        },
        "toolchain": {
            "compiler_version": COMPILER_VERSION,
            "msvc_tools_version": MSVC_TOOLS_VERSION,
            "visual_studio_version": VISUAL_STUDIO_VERSION,
            "windows_sdk_version": WINDOWS_SDK_VERSION,
        },
    }


def _canonical_json(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        metadata = path.lstat()
        reparse = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
        attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or attributes & reparse:
            raise RuntimeError(f"refusing to replace non-regular package asset: {path.name}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _load_provenance(payload: bytes) -> dict[str, Any]:
    if not payload or len(payload) > MAX_PROVENANCE_BYTES:
        raise RuntimeError("native helper provenance exceeds its byte budget")
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("native helper provenance is malformed") from exc
    if not isinstance(document, dict) or _canonical_json(document) != payload:
        raise RuntimeError("native helper provenance is not canonical JSON")
    return document


def verify_payload_contract(
    source: bytes,
    executable: bytes,
    provenance: bytes,
) -> dict[str, Any]:
    """Verify the exact reviewed source, PE, and canonical provenance payloads."""

    if len(source) != REVIEWED_SOURCE_SIZE or _sha256(source) != REVIEWED_SOURCE_SHA256:
        raise RuntimeError("native helper source differs from the reviewed hard pin")
    if (
        len(executable) != REVIEWED_EXECUTABLE_SIZE
        or _sha256(executable) != REVIEWED_EXECUTABLE_SHA256
    ):
        raise RuntimeError(
            "native helper executable differs from the reviewed hard pin: "
            f"observed size={len(executable)}, sha256={_sha256(executable)}"
        )
    _pe_contract(executable)
    observed = _load_provenance(provenance)
    expected = _provenance(source=source, executable=executable)
    if observed != expected:
        raise RuntimeError("native helper provenance differs from the reviewed payload contract")
    return observed


def build_and_verify(*, update_package: bool, work_root: Path | None = None) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("the native Windows helper can only be rebuilt on Windows")
    source = _read_regular_bounded(
        SOURCE_PATH,
        maximum=MAX_SOURCE_BYTES,
        label="native helper source",
    )
    installation, _visual_studio_version = _visual_studio()
    environment = _toolchain_environment(installation)
    compiler = _compiler_path(installation)
    dumpbin = _dumpbin_path(compiler)
    _require_compiler_version(compiler, environment)

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if work_root is None:
        temporary = tempfile.TemporaryDirectory(prefix="agency-runtime-presence-build-")
        parent = Path(temporary.name)
    else:
        parent = work_root.resolve()
        parent.mkdir(parents=True, exist_ok=False)
    try:
        _run_static_analysis(
            parent / "analysis",
            compiler=compiler,
            environment=environment,
            source_payload=source,
        )
        first = _build_once(
            parent / "build-a",
            compiler=compiler,
            environment=environment,
            source_payload=source,
        )
        second = _build_once(
            parent / "build-b",
            compiler=compiler,
            environment=environment,
            source_payload=source,
        )
        if first != second:
            raise RuntimeError("/Brepro builds from distinct roots are not byte-identical")
        _pe_contract(first)
        _verify_dumpbin_contract(
            parent / "build-a" / EXECUTABLE_PATH.name,
            dumpbin=dumpbin,
            environment=environment,
        )
        expected = _provenance(source=source, executable=first)
        expected_payload = _canonical_json(expected)
        verify_payload_contract(source, first, expected_payload)
        if update_package:
            _atomic_write(EXECUTABLE_PATH, first)
            _atomic_write(PROVENANCE_PATH, expected_payload)
        else:
            if (
                _read_regular_bounded(
                    EXECUTABLE_PATH,
                    maximum=MAX_EXECUTABLE_BYTES,
                    label="packaged native helper",
                )
                != first
            ):
                raise RuntimeError("packaged native helper differs from the deterministic rebuild")
            observed = _load_provenance(
                _read_regular_bounded(
                    PROVENANCE_PATH,
                    maximum=MAX_PROVENANCE_BYTES,
                    label="native helper provenance",
                )
            )
            if observed != expected:
                raise RuntimeError("packaged native helper provenance differs from the rebuild")
            verify_payload_contract(source, first, _canonical_json(observed))
        return expected
    finally:
        if temporary is not None:
            temporary.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-package",
        action="store_true",
        help="replace the reviewed package-data executable and canonical provenance",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        help="create two distinct build roots under this new directory",
    )
    args = parser.parse_args(argv)
    try:
        provenance = build_and_verify(
            update_package=args.update_package,
            work_root=args.work_root,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Windows operator-presence build failed: {exc}\n")
    action = "updated and verified" if args.update_package else "verified"
    print(
        f"Windows operator-presence helper {action}: "
        f"sha256={provenance['executable_sha256']} "
        f"bytes={provenance['executable_size']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
