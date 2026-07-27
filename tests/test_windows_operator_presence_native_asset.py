from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import build_windows_operator_presence as builder
from scripts import verify_distribution

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / builder.SOURCE_RELATIVE
EXECUTABLE = ROOT / builder.EXECUTABLE_RELATIVE
PROVENANCE = (
    ROOT
    / "agency_runtime"
    / "native"
    / "windows"
    / "operator_presence"
    / "operator_presence_verifier.provenance.json"
)


def _payloads() -> tuple[bytes, bytes, bytes]:
    return SOURCE.read_bytes(), EXECUTABLE.read_bytes(), PROVENANCE.read_bytes()


def _valid_request() -> bytes:
    return (
        b"AGENCY-OPERATOR-PRESENCE/1\n"
        b"action=roster.rollback.v1\n"
        b"slug=security-reviewer\n"
        + b"current-version=sha256:"
        + b"1" * 64
        + b"\ncurrent-hash="
        + b"2" * 64
        + b"\ntarget-version=sha256:"
        + b"3" * 64
        + b"\ntarget-hash="
        + b"4" * 64
        + b"\nauthority=snapshot\nnonce="
        + b"5" * 64
        + b"\n"
    )


def _valid_codex_request() -> bytes:
    return (
        b"AGENCY-OPERATOR-PRESENCE/1\n"
        b"action=install.codex.v1\n"
        b"host=codex\n"
        b"plugin=agency-preflight@agency-runtime\n"
        b"target-path=C:\\Users\\owner\\.agency-runtime\\marketplaces\\codex\n"
        b"current-plugin-version=0.1.0+codex.current123\n"
        b"candidate-plugin-version=0.1.0+codex.candidate456\n"
        + b"current-bundle-sha256="
        + b"1" * 64
        + b"\ncandidate-plan-sha256="
        + b"2" * 64
        + b"\ncodex-executable-sha256="
        + b"3" * 64
        + b"\nconfig-revision=sha256:"
        + b"4" * 64
        + b"\nroster-generation=5\n"
        + b"will-backup=yes\n"
        + b"will-reregister=yes\n"
        + b"recovery=restore-prior-managed-bundle-and-registration\n"
        + b"binding-sha256="
        + b"6" * 64
        + b"\nnonce="
        + b"7" * 64
        + b"\n"
    )


def test_reviewed_native_payload_and_provenance_are_exact() -> None:
    source, executable, provenance = _payloads()
    observed = builder.verify_payload_contract(source, executable, provenance)

    assert len(source) == builder.REVIEWED_SOURCE_SIZE == 41_551
    assert hashlib.sha256(source).hexdigest() == builder.REVIEWED_SOURCE_SHA256
    assert len(executable) == builder.REVIEWED_EXECUTABLE_SIZE == 187_392
    assert hashlib.sha256(executable).hexdigest() == builder.REVIEWED_EXECUTABLE_SHA256
    assert observed["distribution_classification"] == (
        "reviewed_unsigned_windows_executable_package_data"
    )
    assert observed["target"] == {
        "architecture": "x86_64",
        "minimum_windows_build": 22_000,
        "subsystem": "windows",
    }
    assert observed["toolchain"] == {
        "compiler_version": "19.44.35225",
        "msvc_tools_version": "14.44.35207",
        "visual_studio_version": "17.14.37111.16",
        "windows_sdk_version": "10.0.26100.0",
    }
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert (
        "agency_runtime/native/windows/operator_presence/operator_presence_verifier.exe binary"
        in attributes.splitlines()
    )


def test_native_source_exposes_only_the_two_fixed_consent_contracts() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    for required in (
        "IUserConsentVerifierInterop",
        "RequestVerificationForWindowAsync",
        'constexpr std::string_view kRollbackAction = "roster.rollback.v1"',
        'constexpr std::string_view kCodexInstallAction = "install.codex.v1"',
        'field(lines[2], "slug="',
        'field(lines[3], "current-version="',
        'field(lines[4], "current-hash="',
        'field(lines[5], "target-version="',
        'field(lines[6], "target-hash="',
        'field(lines[7], "authority="',
        'field(lines[8], "nonce="',
        'field(lines[2], "host="',
        'field(lines[3], "plugin="',
        'field(lines[4], "target-path="',
        'field(lines[5], "current-plugin-version="',
        'field(lines[6], "candidate-plugin-version="',
        'field(lines[7], "current-bundle-sha256="',
        'field(lines[8], "candidate-plan-sha256="',
        'field(lines[9], "codex-executable-sha256="',
        'field(lines[10], "config-revision="',
        'field(lines[11], "roster-generation="',
        'field(lines[12], "will-backup="',
        'field(lines[13], "will-reregister="',
        'field(lines[14], "recovery="',
        'field(lines[15], "binding-sha256="',
        'field(lines[16], "nonce="',
        'L"&Verify"',
        'L"&Verify reinstall"',
        'L"&Cancel"',
        "IsDialogMessageW",
        "VK_ESCAPE",
        "ConvertSidToStringSidW",
        'L"Local\\\\AgencyRuntime.OperatorPresence."',
        "SetLastError(ERROR_SUCCESS)",
        "DWORD const create_error = GetLastError()",
        "constexpr size_t slug_wrap = 64",
        "GetForegroundWindow() != window",
        "state.operation_started = true",
        "full authoritative roster projection",
        "source provenance",
        "workforce routing",
        "preserving current worker lifecycle",
        "employment and standing",
        "append rollback audit history",
        "advance roster generation",
        "replace only the managed Agency",
        "every other plugin remain unchanged",
        "transaction plan",
        "component bytes",
        "launcher-publication plan",
        "re-attested before installation",
        "does not grant hook trust",
        "production publisher trust",
    ):
        assert required in source
    assert "candidate_plugin_version == current_plugin_version" not in source
    assert "candidate_plan_sha256 == current_bundle_sha256" not in source
    assert "read_prompt" not in source
    assert "operation.Cancel" not in source
    assert "operation.Close" not in source
    assert "nlohmann" not in source

    factory = source.index("get_activation_factory")
    foreground = source.index("GetForegroundWindow() != window", factory)
    request = source.index("RequestVerificationForWindowAsync", foreground)
    assert factory < foreground < request

    create_mutex = source.index("CreateMutexW")
    capture_error = source.index("DWORD const create_error = GetLastError()", create_mutex)
    attach_mutex = source.index("acquisition.handle.attach(raw_mutex)", capture_error)
    assert create_mutex < capture_error < attach_mutex


@pytest.mark.parametrize(
    "payload",
    (
        b"",
        _valid_request().replace(b"slug=security-reviewer", b"slug=Security-reviewer"),
        _valid_request().replace(b"\nslug=", b"\r\nslug="),
        _valid_request().replace(b"slug=security", b"slug=security\xe2\x80\xae"),
        _valid_request() + b"extra=true\n",
        _valid_request().replace(b"nonce=" + b"5" * 64, b"nonce=" + b"G" * 64),
        _valid_codex_request().replace(b"host=codex", b"host=claude"),
        _valid_codex_request().replace(
            b"plugin=agency-preflight@agency-runtime",
            b"plugin=other@agency-runtime",
        ),
        _valid_codex_request().replace(b"target-path=C:\\", b"target-path=c:\\"),
        _valid_codex_request().replace(
            b"candidate-plugin-version=0.1.0+codex.candidate456",
            b"candidate-plugin-version=bad version",
        ),
        _valid_codex_request().replace(
            b"candidate-plan-sha256=" + b"2" * 64,
            b"candidate-plan-sha256=" + b"A" * 64,
        ),
        _valid_codex_request().replace(b"will-backup=yes", b"will-backup=no"),
        _valid_codex_request().replace(b"binding-sha256=" + b"6" * 64, b"binding-sha256=x"),
        _valid_codex_request() + b"extra=true\n",
    ),
)
@pytest.mark.skipif(os.name != "nt", reason="reviewed helper is a Windows x64 executable")
def test_invalid_native_requests_fail_without_showing_verification_ui(payload: bytes) -> None:
    completed = subprocess.run(
        [EXECUTABLE],
        input=payload,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 64
    assert completed.stdout == (
        b"AGENCY-OPERATOR-PRESENCE/1\nmode=verification\nresult=invalid-input\n"
    )
    assert completed.stderr == b""


@pytest.mark.skipif(os.name != "nt", reason="availability uses the Windows credential API")
def test_availability_probe_is_explicitly_non_authorizing_and_has_no_stderr() -> None:
    completed = subprocess.run(
        [EXECUTABLE, "--availability-only"],
        input=b"",
        capture_output=True,
        check=False,
        timeout=15,
    )
    results = {
        "available": 0,
        "device-not-present": 20,
        "not-configured": 21,
        "disabled-by-policy": 22,
        "device-busy": 23,
        "canceled": 25,
        "error": 70,
    }
    lines = completed.stdout.decode("ascii").splitlines()

    assert lines[:2] == ["AGENCY-OPERATOR-PRESENCE/1", "mode=availability"]
    assert len(lines) == 3 and lines[2].startswith("result=")
    result = lines[2].removeprefix("result=")
    assert completed.returncode == results[result]
    assert result != "verified"
    assert b"nonce=" not in completed.stdout
    assert completed.stderr == b""


def test_payload_contract_rejects_source_executable_and_provenance_drift() -> None:
    source, executable, provenance = _payloads()
    with pytest.raises(RuntimeError, match="source differs"):
        builder.verify_payload_contract(source + b" ", executable, provenance)
    with pytest.raises(RuntimeError, match="executable differs"):
        builder.verify_payload_contract(source, executable[:-1] + b"X", provenance)

    changed = json.loads(provenance)
    changed["toolchain"]["compiler_version"] = "19.44.0"
    changed_payload = (json.dumps(changed, indent=2, sort_keys=True) + "\n").encode()
    with pytest.raises(RuntimeError, match="provenance differs"):
        builder.verify_payload_contract(source, executable, changed_payload)


def test_pe_contract_rejects_wrong_target_mitigations_and_signature() -> None:
    executable = bytearray(EXECUTABLE.read_bytes())
    pe_offset = struct.unpack_from("<I", executable, 0x3C)[0]
    optional = pe_offset + 24

    for offset, value, message in (
        (pe_offset + 4, 0x014C, "x64 Windows-subsystem"),
        (optional + 68, 3, "x64 Windows-subsystem"),
        (optional + 70, 0, "ASLR, NX, or CFG"),
    ):
        changed = bytearray(executable)
        struct.pack_into("<H", changed, offset, value)
        with pytest.raises(RuntimeError, match=message):
            builder._pe_contract(bytes(changed))

    signed = bytearray(executable)
    struct.pack_into("<II", signed, optional + 144, 1, 1)
    with pytest.raises(RuntimeError, match="reviewed unsigned"):
        builder._pe_contract(bytes(signed))
    with pytest.raises(RuntimeError, match="not a bounded PE"):
        builder._pe_contract(b"MZ")


def test_toolchain_environment_removes_option_injection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installation = tmp_path / "Visual Studio"
    command = installation / "Common7" / "Tools" / "VsDevCmd.bat"
    command.parent.mkdir(parents=True)
    command.write_text("@exit /b 0\n", encoding="utf-8")
    monkeypatch.setenv("CL", "/DATTACK=1")
    monkeypatch.setenv("_LINK_", "/ENTRY:attacker")

    def fake_run(arguments: list[str], **_kwargs: object) -> SimpleNamespace:
        assert arguments[:3] == ["cmd.exe", "/d", "/c"]
        batch = Path(arguments[3])
        assert "VsDevCmd.bat" in batch.read_text(encoding="utf-8")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                b"VCToolsVersion=14.44.35207\r\n"
                b"WindowsSDKVersion=10.0.26100.0\\\r\n"
                b"Cl=/DINJECTED\r\n_LINK_=/ENTRY:injected\r\n"
            ),
            stderr=b"",
        )

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    environment = builder._toolchain_environment(installation)

    assert not {name.upper() for name in environment}.intersection({"CL", "_CL_", "LINK", "_LINK_"})
    assert environment["VCToolsVersion"] == "14.44.35207"


def test_bounded_reader_and_atomic_writer_reject_non_regular_targets(tmp_path: Path) -> None:
    regular = tmp_path / "regular.bin"
    regular.write_bytes(b"payload")
    assert builder._read_regular_bounded(regular, maximum=7, label="fixture") == b"payload"

    oversized = tmp_path / "oversized.bin"
    oversized.write_bytes(b"12345678")
    with pytest.raises(RuntimeError, match="bounded non-reparse"):
        builder._read_regular_bounded(oversized, maximum=7, label="fixture")
    with pytest.raises(RuntimeError, match="bounded non-reparse"):
        builder._read_regular_bounded(tmp_path, maximum=7, label="fixture")

    link = tmp_path / "linked.bin"
    try:
        link.symlink_to(regular)
    except OSError:
        pytest.skip("file symlinks require Windows Developer Mode on this host")
    with pytest.raises(RuntimeError, match="bounded non-reparse"):
        builder._read_regular_bounded(link, maximum=7, label="fixture")
    with pytest.raises(RuntimeError, match="refusing to replace"):
        builder._atomic_write(link, b"replacement")
    assert regular.read_bytes() == b"payload"


def test_static_analysis_allows_only_exact_sdk_annotation_defects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    known = (
        "C:\\Program Files (x86)\\Windows Kits\\10\\include\\10.0.26100.0\\um\\"
        "WindowsNumerics.inl(2375) : warning C6101: SDK annotation defect"
    )
    outputs = [known, known + "\noperator_presence_verifier.cpp(4): warning C6001: real finding"]

    def fake_run(arguments: list[str], **_kwargs: object) -> SimpleNamespace:
        assert "/analyze" in arguments
        assert "/analyze:WX-" in arguments
        return SimpleNamespace(returncode=0, stdout=outputs.pop(0), stderr="")

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    builder._run_static_analysis(
        tmp_path / "analysis-good",
        compiler=Path("cl.exe"),
        environment={},
        source_payload=b"int main() {}\n",
    )
    with pytest.raises(RuntimeError, match="/analyze pass failed"):
        builder._run_static_analysis(
            tmp_path / "analysis-bad",
            compiler=Path("cl.exe"),
            environment={},
            source_payload=b"int main() {}\n",
        )


def _dumpbin_output(dependencies: set[str]) -> str:
    return (
        "8664 machine (x64)\n"
        "2 subsystem (Windows GUI)\n"
        "High Entropy Virtual Addresses\nDynamic base\nNX compatible\n"
        "Control Flow Guard\nCET compatible\nDependent Load Flag\n"
        "CF instrumented\nFID table present\n"
        "    0000000140000001 Security Cookie\n"
        "Image has the following dependencies:\n\n"
        + "".join(f"    {name}\n" for name in sorted(dependencies))
        + "\nSection contains the following load config:\n"
    )


def test_dumpbin_contract_requires_exact_mitigations_and_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    outputs = [
        _dumpbin_output(set(builder.EXPECTED_DEPENDENCIES)),
        _dumpbin_output(set(builder.EXPECTED_DEPENDENCIES) - {"user32.dll"}),
    ]

    def fake_run(_arguments: list[str], **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=0, stdout=outputs.pop(0), stderr="")

    monkeypatch.setattr(builder.subprocess, "run", fake_run)
    builder._verify_dumpbin_contract(
        Path("verifier.exe"), dumpbin=Path("dumpbin.exe"), environment={}
    )
    with pytest.raises(RuntimeError, match="dependency set differs"):
        builder._verify_dumpbin_contract(
            Path("verifier.exe"), dumpbin=Path("dumpbin.exe"), environment={}
        )


def test_distribution_verifier_enforces_native_payload_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, executable, provenance = _payloads()
    payloads = {
        builder.SOURCE_RELATIVE: source,
        builder.EXECUTABLE_RELATIVE: executable,
        (
            "agency_runtime/native/windows/operator_presence/"
            "operator_presence_verifier.provenance.json"
        ): provenance,
    }
    assert verify_distribution._native_operator_presence_failures(payloads, artifact="wheel") == []
    assert verify_distribution._native_operator_presence_failures({}, artifact="wheel") == []

    def reject(*_args: object) -> None:
        raise RuntimeError("fixture drift")

    monkeypatch.setattr(verify_distribution, "verify_payload_contract", reject)
    assert verify_distribution._native_operator_presence_failures(payloads, artifact="wheel") == [
        "wheel Windows operator-presence asset contract failed: fixture drift"
    ]
