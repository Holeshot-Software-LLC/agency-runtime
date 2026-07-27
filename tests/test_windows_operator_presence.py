"""AR-143 exact native-process contract and prepared CLI integration."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.cli import main as cli_main
from agency_runtime.cli import roster_commands
from agency_runtime.core import windows_operator_presence as subject
from agency_runtime.core.operator_presence import OperatorPresenceError
from agency_runtime.core.process_argv import PreparedProcessArgv
from agency_runtime.core.store.roster import _RosterRollbackBinding

_NONCE = bytes.fromhex("ab" * 32)


def _prepared(**changes: Any) -> _RosterRollbackBinding:
    values: dict[str, Any] = {
        "config_path": r"C:\Users\owner\.agency-runtime\config.yaml",
        "database_path": r"C:\Users\owner\.agency-runtime\agency.db",
        "database_device": 7,
        "database_inode": 11,
        "roster_generation": 5,
        "slug": "security-reviewer",
        "current_version": "sha256:" + "1" * 64,
        "current_hash": "2" * 64,
        "current_projection_digest": "3" * 64,
        "target_revision_id": "revision-1",
        "target_version": "sha256:" + "4" * 64,
        "target_hash": "5" * 64,
        "target_content_metadata_digest": "6" * 64,
        "activation_authority_kind": "bundled",
        "activation_authority_digest": "7" * 64,
        "workforce_identity_digest": "8" * 64,
    }
    values.update(changes)
    return _RosterRollbackBinding(**values)


def test_native_binding_covers_every_prepared_store_field() -> None:
    assert _RosterRollbackBinding._fields == subject._PREPARED_BINDING_FIELDS


def _result(**changes: Any) -> subject.BoundedBinaryProcessResult:
    values: dict[str, Any] = {
        "returncode": 0,
        "stdout": subject._verified_stdout(_NONCE.hex()),
        "stderr": b"",
        "timed_out": False,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "cancelled": False,
        "failure_category": None,
    }
    values.update(changes)
    return subject.BoundedBinaryProcessResult(**values)


def _enable_test_verifier(
    monkeypatch: pytest.MonkeyPatch,
    result: subject.BoundedBinaryProcessResult,
) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    argv = PreparedProcessArgv(
        [r"C:\trusted\verifier.exe"], artifact_paths=(r"C:\trusted\verifier.exe",)
    )
    monkeypatch.setattr(subject, "_assert_supported_host", lambda: None)
    monkeypatch.setattr(subject, "_random_nonce_bytes", lambda: _NONCE)
    monkeypatch.setattr(
        subject,
        "_load_reviewed_verifier",
        lambda: subject._ReviewedVerifier(argv=argv, working_directory=r"C:\trusted"),
    )

    def run(candidate: PreparedProcessArgv, **kwargs: Any) -> subject.BoundedBinaryProcessResult:
        observed["argv"] = candidate
        observed.update(kwargs)
        return result

    monkeypatch.setattr(subject, "run_bounded_binary_process", run)
    return observed


def test_native_verification_sends_exact_record_and_consumes_no_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed = _enable_test_verifier(monkeypatch, _result())

    assert subject._verify_roster_rollback_binding(_prepared()) is None

    assert observed["input_bytes"] == (
        b"AGENCY-OPERATOR-PRESENCE/1\n"
        b"action=roster.rollback.v1\n"
        b"slug=security-reviewer\n"
        + b"current-version=sha256:"
        + b"1" * 64
        + b"\ncurrent-hash="
        + b"2" * 64
        + b"\ntarget-version=sha256:"
        + b"4" * 64
        + b"\ntarget-hash="
        + b"5" * 64
        + b"\nauthority=bundled\nnonce="
        + b"ab" * 32
        + b"\n"
    )
    assert observed["env"] == {}
    assert observed["cwd"] == r"C:\trusted"
    assert observed["retain_output_tail"] is False
    assert observed["max_input_bytes"] == subject._MAX_PROTOCOL_BYTES
    assert observed["max_stdout_bytes"] == subject._MAX_RESULT_BYTES
    assert observed["max_stderr_bytes"] == subject._MAX_RESULT_BYTES


_DENIED_RESULTS = (
    "device-not-present",
    "not-configured",
    "disabled-by-policy",
    "device-busy",
    "retries-exhausted",
    "canceled",
    "window-not-active",
    "already-running",
    "error",
)


@pytest.mark.parametrize("status", _DENIED_RESULTS)
def test_every_nonverified_status_is_denied(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    stdout = (
        subject._PROTOCOL_HEADER
        + b"mode=verification\n"
        + b"action=roster.rollback.v1\n"
        + f"result={status}\n".encode("ascii")
        + b"nonce="
        + _NONCE.hex().encode("ascii")
        + b"\n"
    )
    _enable_test_verifier(monkeypatch, _result(returncode=20, stdout=stdout))

    with pytest.raises(OperatorPresenceError, match="was not verified"):
        subject._verify_roster_rollback_binding(_prepared())


@pytest.mark.parametrize(
    "changes",
    [
        {"stdout": subject._verified_stdout("cd" * 32)},
        {"stdout": subject._verified_stdout(_NONCE.hex()) + b"extra"},
        {"stdout": subject._verified_stdout(_NONCE.hex()).replace(b"\n", b"\r\n")},
        {
            "stdout": subject._verified_stdout(_NONCE.hex()).replace(
                b"roster.rollback.v1", b"roster.activate.v1"
            )
        },
        {"stderr": b"diagnostic"},
        {"returncode": 1},
        {"timed_out": True},
        {"stdout_truncated": True},
        {"stderr_truncated": True},
        {"cancelled": True},
        {"failure_category": "containment"},
    ],
    ids=(
        "wrong-nonce",
        "extra-stdout",
        "crlf",
        "wrong-action",
        "stderr",
        "nonzero",
        "timeout",
        "stdout-truncated",
        "stderr-truncated",
        "cancelled",
        "containment-failure",
    ),
)
def test_malformed_or_failed_process_result_is_denied(
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, Any],
) -> None:
    _enable_test_verifier(monkeypatch, _result(**changes))

    with pytest.raises(OperatorPresenceError, match="was not verified"):
        subject._verify_roster_rollback_binding(_prepared())


def test_availability_result_can_never_authorize(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = subject._PROTOCOL_HEADER + b"mode=availability\nresult=available\n"
    _enable_test_verifier(monkeypatch, _result(stdout=stdout))

    with pytest.raises(OperatorPresenceError, match="was not verified"):
        subject._verify_roster_rollback_binding(_prepared())


def test_prepared_tuple_cannot_change_during_native_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    _enable_test_verifier(monkeypatch, _result())

    def mutate_then_verify(
        _candidate: PreparedProcessArgv,
        **_kwargs: Any,
    ) -> subject.BoundedBinaryProcessResult:
        with pytest.raises(AttributeError, match="can't set attribute"):
            object.__setattr__(prepared, "target_hash", "9" * 64)
        return _result()

    monkeypatch.setattr(subject, "run_bounded_binary_process", mutate_then_verify)

    subject._verify_roster_rollback_binding(prepared)
    assert prepared.target_hash == "5" * 64


def test_invalid_prepared_type_never_reaches_host_or_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "_assert_supported_host",
        lambda: pytest.fail("invalid prepared value reached host verification"),
    )

    with pytest.raises(OperatorPresenceError, match="binding is invalid"):
        subject._verify_roster_rollback_binding(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("platform_name", "architecture", "pointer_size", "build", "message"),
    [
        ("linux", "x86_64", 8, 22_000, "Windows 11"),
        ("win32", "arm64", 8, 22_000, "x64 process"),
        ("win32", "AMD64", 4, 22_000, "x64 process"),
        ("win32", "AMD64", 8, 21_999, "Windows 11"),
    ],
)
def test_unsupported_host_is_rejected_before_resource_loading(
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
    architecture: str,
    pointer_size: int,
    build: int,
    message: str,
) -> None:
    monkeypatch.setattr(subject, "_runtime_platform", lambda: platform_name)
    monkeypatch.setattr(subject, "_runtime_architecture", lambda: architecture)
    monkeypatch.setattr(subject, "_pointer_size", lambda: pointer_size)
    monkeypatch.setattr(subject, "_windows_build", lambda: build)
    monkeypatch.setattr(
        subject,
        "_load_reviewed_verifier",
        lambda: pytest.fail("unsupported host loaded the verifier"),
    )

    with pytest.raises(OperatorPresenceError, match=message):
        subject._verify_roster_rollback_binding(_prepared())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slug", "A-bad-slug"),
        ("current_version", "1.0.0"),
        ("current_hash", "A" * 64),
        ("target_version", "sha256:short"),
        ("target_hash", "0" * 63),
        ("activation_authority_kind", "manual"),
    ],
)
def test_invalid_prepared_protocol_fields_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
) -> None:
    monkeypatch.setattr(subject, "_assert_supported_host", lambda: None)
    monkeypatch.setattr(subject, "_random_nonce_bytes", lambda: _NONCE)
    monkeypatch.setattr(
        subject,
        "_load_reviewed_verifier",
        lambda: pytest.fail("invalid prepared value loaded the verifier"),
    )

    with pytest.raises(OperatorPresenceError, match="binding is invalid"):
        subject._verify_roster_rollback_binding(_prepared(**{field: value}))


def _provenance_record(*, source_size: int = 10, executable_size: int = 20) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "asset_role": "windows_operator_presence_verifier",
        "distribution_classification": "reviewed_unsigned_windows_executable_package_data",
        "source_path": "agency_runtime/native/windows/operator_presence/operator_presence_verifier.cpp",
        "source_size": source_size,
        "source_sha256": "1" * 64,
        "executable_path": "agency_runtime/native/windows/operator_presence/operator_presence_verifier.exe",
        "executable_size": executable_size,
        "executable_sha256": "2" * 64,
        "target": {
            "architecture": "x86_64",
            "minimum_windows_build": 22_000,
            "subsystem": "windows",
        },
        "toolchain": {
            "compiler_version": "19.44.35225",
            "msvc_tools_version": "14.44.35207",
            "visual_studio_version": "17.14.37111.16",
            "windows_sdk_version": "10.0.26100.0",
        },
        "build_contract": {
            "deterministic": True,
            "compiler_flags": ["/Brepro"],
            "linker_flags": ["/Brepro"],
        },
    }


def test_provenance_schema_is_exact_and_bounded() -> None:
    payload = json.dumps(_provenance_record()).encode("utf-8")
    assert subject._decode_provenance(payload) == ((10, "1" * 64), (20, "2" * 64))

    invalid = _provenance_record()
    invalid["unexpected"] = True
    with pytest.raises(OperatorPresenceError, match="schema is invalid"):
        subject._decode_provenance(json.dumps(invalid).encode("utf-8"))

    duplicate = payload.replace(
        b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,'
    )
    with pytest.raises(OperatorPresenceError, match="provenance is invalid"):
        subject._decode_provenance(duplicate)

    boolean_schema = _provenance_record()
    boolean_schema["schema_version"] = True
    with pytest.raises(OperatorPresenceError, match="schema is invalid"):
        subject._decode_provenance(json.dumps(boolean_schema).encode("utf-8"))


def test_runtime_pins_match_exact_packaged_source_executable_and_provenance() -> None:
    source = subject._resource_path(subject._SOURCE_NAME).read_bytes()
    executable = subject._resource_path(subject._EXECUTABLE_NAME).read_bytes()
    provenance = subject._resource_path(subject._PROVENANCE_NAME).read_bytes()

    assert (len(source), subject.hashlib.sha256(source).hexdigest()) == (
        subject._EXPECTED_SOURCE_SIZE,
        subject._EXPECTED_SOURCE_SHA256,
    )
    assert (len(executable), subject.hashlib.sha256(executable).hexdigest()) == (
        subject._EXPECTED_EXECUTABLE_SIZE,
        subject._EXPECTED_EXECUTABLE_SHA256,
    )
    assert subject._decode_provenance(provenance) == (
        (subject._EXPECTED_SOURCE_SIZE, subject._EXPECTED_SOURCE_SHA256),
        (subject._EXPECTED_EXECUTABLE_SIZE, subject._EXPECTED_EXECUTABLE_SHA256),
    )


@pytest.mark.skipif(subject._runtime_platform() != "win32", reason="Windows package identity")
def test_reviewed_packaged_verifier_freezes_complete_trusted_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    copied: dict[str, Path] = {}
    for name in (subject._SOURCE_NAME, subject._EXECUTABLE_NAME, subject._PROVENANCE_NAME):
        target = tmp_path / name
        target.write_bytes(subject._resource_path(name).read_bytes())
        copied[name] = target
    monkeypatch.setattr(subject, "_resource_path", copied.__getitem__)

    reviewed = subject._load_reviewed_verifier()

    assert reviewed.argv == [str(copied[subject._EXECUTABLE_NAME])]
    assert len(reviewed.argv.persistent_artifact_identities) == 1
    identity = reviewed.argv.persistent_artifact_identities[0]
    assert (identity.resolved_size, identity.sha256) == (
        subject._EXPECTED_EXECUTABLE_SIZE,
        subject._EXPECTED_EXECUTABLE_SHA256,
    )


@pytest.mark.parametrize(
    ("filename", "label"),
    [
        ("operator_presence_verifier.provenance.json", "verifier provenance"),
        ("operator_presence_verifier.cpp", "verifier source"),
        ("operator_presence_verifier.exe", "verifier executable"),
    ],
)
def test_resource_hash_or_identity_race_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    filename: str,
    label: str,
) -> None:
    resource = tmp_path / filename
    resource.write_bytes(b"reviewed")
    identity = SimpleNamespace(resolved_size=8, sha256="0" * 64)
    monkeypatch.setattr(subject, "snapshot_persistent_artifact", lambda *_args, **_kwargs: identity)
    monkeypatch.setattr(
        subject,
        "revalidate_persistent_artifacts",
        lambda *_args, **_kwargs: pytest.fail("hash mismatch reached revalidation"),
    )

    with pytest.raises(OperatorPresenceError, match="changed while it was read"):
        subject._read_bounded_resource(resource, limit=100, label=label)

    matching = SimpleNamespace(
        resolved_size=8,
        sha256=subject.hashlib.sha256(b"reviewed").hexdigest(),
    )
    monkeypatch.setattr(subject, "snapshot_persistent_artifact", lambda *_args, **_kwargs: matching)
    monkeypatch.setattr(
        subject,
        "revalidate_persistent_artifacts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("identity drift")),
    )
    with pytest.raises(OperatorPresenceError, match="unavailable or untrusted"):
        subject._read_bounded_resource(resource, limit=100, label=label)


def test_untrusted_or_linked_resource_identity_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resource = tmp_path / "verifier.exe"
    resource.write_bytes(b"binary")
    monkeypatch.setattr(
        subject,
        "snapshot_persistent_artifact",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("link or ACL")),
    )

    with pytest.raises(OperatorPresenceError, match="unavailable or untrusted"):
        subject._read_bounded_resource(resource, limit=100, label="test executable")


def test_executable_digest_or_frozen_identity_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = {
        name: tmp_path / name
        for name in (subject._PROVENANCE_NAME, subject._SOURCE_NAME, subject._EXECUTABLE_NAME)
    }
    for path in paths.values():
        path.write_bytes(b"x" * 20)
    monkeypatch.setattr(subject, "_resource_path", paths.__getitem__)
    provenance_identity = SimpleNamespace(resolved_size=20, sha256="9" * 64)
    source_identity = SimpleNamespace(
        resolved_size=subject._EXPECTED_SOURCE_SIZE,
        sha256=subject._EXPECTED_SOURCE_SHA256,
    )

    def read_resource(
        _path: Path,
        *,
        limit: int,
        label: str,
    ) -> tuple[bytes, object]:
        assert limit > 0
        if label.endswith("provenance"):
            return b"provenance", provenance_identity
        return b"source", source_identity

    monkeypatch.setattr(subject, "_read_bounded_resource", read_resource)
    monkeypatch.setattr(
        subject,
        "_decode_provenance",
        lambda _payload: (
            (subject._EXPECTED_SOURCE_SIZE, subject._EXPECTED_SOURCE_SHA256),
            (subject._EXPECTED_EXECUTABLE_SIZE, subject._EXPECTED_EXECUTABLE_SHA256),
        ),
    )

    def freeze(candidate: PreparedProcessArgv, **_kwargs: Any) -> PreparedProcessArgv:
        candidate.persistent_artifact_identities = (
            SimpleNamespace(
                resolved_size=20,
                sha256="3" * 64,
                resolved_path=str(paths[subject._EXECUTABLE_NAME]),
            ),
        )
        return candidate

    monkeypatch.setattr(PreparedProcessArgv, "freeze_persistent", freeze)

    with pytest.raises(OperatorPresenceError, match="does not match provenance"):
        subject._load_reviewed_verifier()


def test_executable_freeze_rejects_untrusted_namespace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    paths = {
        name: tmp_path / name
        for name in (subject._PROVENANCE_NAME, subject._SOURCE_NAME, subject._EXECUTABLE_NAME)
    }
    for path in paths.values():
        path.write_bytes(b"x" * 20)
    monkeypatch.setattr(subject, "_resource_path", paths.__getitem__)
    monkeypatch.setattr(
        subject,
        "_read_bounded_resource",
        lambda *_args, **kwargs: (
            b"provenance" if kwargs["label"].endswith("provenance") else b"source",
            SimpleNamespace(
                resolved_size=subject._EXPECTED_SOURCE_SIZE,
                sha256=subject._EXPECTED_SOURCE_SHA256,
            ),
        ),
    )
    monkeypatch.setattr(
        subject,
        "_decode_provenance",
        lambda _payload: (
            (subject._EXPECTED_SOURCE_SIZE, subject._EXPECTED_SOURCE_SHA256),
            (subject._EXPECTED_EXECUTABLE_SIZE, subject._EXPECTED_EXECUTABLE_SHA256),
        ),
    )
    monkeypatch.setattr(
        PreparedProcessArgv,
        "freeze_persistent",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("untrusted namespace")),
    )

    with pytest.raises(OperatorPresenceError, match="executable is unavailable"):
        subject._load_reviewed_verifier()


def test_handler_delegates_one_call_to_store_owned_coordinator(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, object]] = []
    prepared = _prepared()

    class Store:
        def rollback_agent_revision(self, *args: Any, **kwargs: Any) -> dict[str, str]:
            calls.append(("coordinator", (args, kwargs)))
            return {
                "agent_slug": prepared.slug,
                "version": prepared.target_version,
                "hash": prepared.target_hash,
            }

    store = Store()
    monkeypatch.setattr(roster_commands, "_store", lambda: store)
    result = cli_main.main(
        [
            "roster",
            "rollback",
            prepared.slug,
            prepared.target_version,
            "--expected-current-version",
            prepared.current_version,
            "--expected-current-hash",
            prepared.current_hash,
        ]
    )

    assert result == 0
    assert [name for name, _value in calls] == ["coordinator"]
    args, kwargs = calls[0][1]
    assert args == (prepared.slug, prepared.target_version)
    assert kwargs == {
        "expected_current_version": prepared.current_version,
        "expected_current_hash": prepared.current_hash,
    }
    assert "Rolled back security-reviewer" in capsys.readouterr().out


def test_coordinator_denial_propagates_without_a_second_cli_mutation_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    prepared = _prepared()

    class Store:
        def rollback_agent_revision(self, *_args: Any, **_kwargs: Any) -> dict[str, str]:
            calls.append("coordinator")
            raise OperatorPresenceError("operator canceled")

    monkeypatch.setattr(roster_commands, "_store", Store)
    result = cli_main.main(
        [
            "roster",
            "rollback",
            prepared.slug,
            prepared.target_version,
            "--expected-current-version",
            prepared.current_version,
            "--expected-current-hash",
            prepared.current_hash,
        ]
    )

    assert result == 1
    assert calls == ["coordinator"]
