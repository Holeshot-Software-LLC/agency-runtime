"""Windows-native, result-only operator verification for prepared mutations.

The packaged helper owns the trusted Windows Hello prompt.  This module binds
one prepared roster rollback to an exact byte protocol, launches only the
reviewed package artifact through the atomically contained process runner, and
consumes the nonce-bound result synchronously.  It never returns a receipt or
other transferable authorization value.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import secrets
import struct
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agency_runtime.core.operator_presence import OperatorPresenceError
from agency_runtime.core.owned_process import (
    BoundedBinaryProcessResult,
    run_bounded_binary_process,
)
from agency_runtime.core.process_argv import (
    PersistentArtifactIdentity,
    PreparedProcessArgv,
    revalidate_persistent_artifacts,
    snapshot_persistent_artifact,
)

if TYPE_CHECKING:
    from agency_runtime.core.store.roster import _RosterRollbackBinding

_PROTOCOL_HEADER = b"AGENCY-OPERATOR-PRESENCE/1\n"
_ACTION = "roster.rollback.v1"
_RESOURCE_PARTS = ("native", "windows", "operator_presence")
_EXECUTABLE_NAME = "operator_presence_verifier.exe"
_SOURCE_NAME = "operator_presence_verifier.cpp"
_PROVENANCE_NAME = "operator_presence_verifier.provenance.json"
_MAX_PROVENANCE_BYTES = 8 * 1024
_MAX_HELPER_BYTES = 2 * 1024 * 1024
_MAX_PROTOCOL_BYTES = 2 * 1024
_MAX_RESULT_BYTES = 512
_PROCESS_TIMEOUT_SECONDS = 120.0
_OPERATOR_PRESENCE_MECHANISM = "windows-user-consent-verifier/v1"
_EXPECTED_SOURCE_SIZE = 26_482
_EXPECTED_SOURCE_SHA256 = "8fb94318fcd8dd9c6c624bdd6faa841e5298bed449958dd42b2c22910deed085"
_EXPECTED_EXECUTABLE_SIZE = 165_888
_EXPECTED_EXECUTABLE_SHA256 = "f525c64775ac49fbb0be7ffcf9b8c5d013ec85ac5756ab6f69be6afe5c9d55fd"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_VERSION = re.compile(r"sha256:[0-9a-f]{64}\Z")
_SLUG = re.compile(r"[a-z0-9][a-z0-9._-]{1,127}\Z")
_AUTHORITIES = frozenset({"bundled", "snapshot"})
_PREPARED_BINDING_FIELDS = (
    "config_path",
    "database_path",
    "database_device",
    "database_inode",
    "roster_generation",
    "slug",
    "current_version",
    "current_hash",
    "current_projection_digest",
    "target_revision_id",
    "target_version",
    "target_hash",
    "target_content_metadata_digest",
    "activation_authority_kind",
    "activation_authority_digest",
    "workforce_identity_digest",
)


@dataclass(frozen=True, slots=True)
class _ReviewedVerifier:
    argv: PreparedProcessArgv
    working_directory: str


def _windows_build() -> int:
    getter = getattr(sys, "getwindowsversion", None)
    if not callable(getter):
        return 0
    return int(getter().build)


def _runtime_platform() -> str:
    return sys.platform


def _runtime_architecture() -> str:
    return platform.machine()


def _pointer_size() -> int:
    return struct.calcsize("P")


def _random_nonce_bytes() -> bytes:
    return secrets.token_bytes(32)


def _assert_supported_host() -> None:
    if _runtime_platform() != "win32":
        raise OperatorPresenceError("native operator verification requires Windows 11")
    machine = _runtime_architecture().casefold()
    if _pointer_size() != 8 or machine not in {"amd64", "x86_64"}:
        raise OperatorPresenceError("native operator verification requires an x64 process")
    if _windows_build() < 22_000:
        raise OperatorPresenceError("native operator verification requires Windows 11")


def _resource_path(name: str) -> Path:
    node: Any = resources.files("agency_runtime")
    for part in (*_RESOURCE_PARTS, name):
        node = node.joinpath(part)
    try:
        path = Path(os.fspath(node))
    except TypeError as exc:
        raise OperatorPresenceError(
            "native operator verifier is not installed as a filesystem resource"
        ) from exc
    if not path.is_absolute():
        raise OperatorPresenceError("native operator verifier resource path is not absolute")
    return path


def _read_bounded_resource(
    path: Path,
    *,
    limit: int,
    label: str,
) -> tuple[bytes, PersistentArtifactIdentity]:
    try:
        lexical = os.lstat(path)
        if int(lexical.st_size) < 0 or int(lexical.st_size) > limit:
            raise OperatorPresenceError(f"{label} exceeds its packaged size limit")
        identity = snapshot_persistent_artifact(path, platform_name="nt")
        if identity.resolved_size > limit:
            raise OperatorPresenceError(f"{label} exceeds its packaged size limit")
        with path.open("rb") as stream:
            payload = stream.read(limit + 1)
        if len(payload) > limit:
            raise OperatorPresenceError(f"{label} exceeds its packaged size limit")
        if hashlib.sha256(payload).hexdigest() != identity.sha256:
            raise OperatorPresenceError(f"{label} changed while it was read")
        revalidate_persistent_artifacts((identity,), platform_name="nt")
    except OperatorPresenceError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise OperatorPresenceError(f"{label} is unavailable or untrusted") from exc
    return payload, identity


def _artifact_identity(
    value: dict[str, Any],
    *,
    prefix: str,
    expected_path: str,
    label: str,
) -> tuple[int, str]:
    if value.get(f"{prefix}_path") != expected_path:
        raise OperatorPresenceError(f"{label} provenance path is invalid")
    size = value.get(f"{prefix}_size")
    digest = value.get(f"{prefix}_sha256")
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= _MAX_HELPER_BYTES:
        raise OperatorPresenceError(f"{label} provenance size is invalid")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise OperatorPresenceError(f"{label} provenance digest is invalid")
    return size, digest


def _decode_provenance(payload: bytes) -> tuple[tuple[int, str], tuple[int, str]]:
    """Decode the exact reviewed-artifact subset of the bounded provenance record."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate provenance field")
            value[key] = item
        return value

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OperatorPresenceError("native operator verifier provenance is invalid") from exc
    if not isinstance(value, dict):
        raise OperatorPresenceError("native operator verifier provenance is invalid")
    expected_fields = {
        "schema_version",
        "asset_role",
        "distribution_classification",
        "source_path",
        "source_size",
        "source_sha256",
        "executable_path",
        "executable_size",
        "executable_sha256",
        "target",
        "toolchain",
        "build_contract",
    }
    if set(value) != expected_fields:
        raise OperatorPresenceError("native operator verifier provenance schema is invalid")
    if (
        type(value.get("schema_version")) is not int
        or value.get("schema_version") != 1
        or value.get("asset_role") != "windows_operator_presence_verifier"
        or value.get("distribution_classification")
        != "reviewed_unsigned_windows_executable_package_data"
    ):
        raise OperatorPresenceError("native operator verifier provenance schema is invalid")
    target = value.get("target")
    if target != {
        "architecture": "x86_64",
        "minimum_windows_build": 22_000,
        "subsystem": "windows",
    }:
        raise OperatorPresenceError("native operator verifier target provenance is invalid")
    toolchain = value.get("toolchain")
    if (
        not isinstance(toolchain, dict)
        or set(toolchain)
        != {
            "compiler_version",
            "msvc_tools_version",
            "visual_studio_version",
            "windows_sdk_version",
        }
        or any(
            not isinstance(item, str)
            or not item
            or len(item) > 64
            or any(ord(character) < 32 or ord(character) == 127 for character in item)
            for item in toolchain.values()
        )
    ):
        raise OperatorPresenceError("native operator verifier toolchain provenance is invalid")
    build = value.get("build_contract")
    if not isinstance(build, dict) or set(build) != {
        "deterministic",
        "compiler_flags",
        "linker_flags",
    }:
        raise OperatorPresenceError("native operator verifier build provenance is invalid")
    flags = (build.get("compiler_flags"), build.get("linker_flags"))
    if build.get("deterministic") is not True or any(
        not isinstance(group, list)
        or not group
        or len(group) > 64
        or len(group) != len(set(group))
        or any(
            not isinstance(flag, str)
            or not flag
            or len(flag) > 256
            or any(ord(character) < 32 or ord(character) == 127 for character in flag)
            for flag in group
        )
        for group in flags
    ):
        raise OperatorPresenceError("native operator verifier build provenance is invalid")
    source = _artifact_identity(
        value,
        prefix="source",
        expected_path=("agency_runtime/native/windows/operator_presence/" + _SOURCE_NAME),
        label="native operator verifier source",
    )
    executable = _artifact_identity(
        value,
        prefix="executable",
        expected_path=("agency_runtime/native/windows/operator_presence/" + _EXECUTABLE_NAME),
        label="native operator verifier executable",
    )
    return source, executable


def _load_reviewed_verifier() -> _ReviewedVerifier:
    provenance_path = _resource_path(_PROVENANCE_NAME)
    source_path = _resource_path(_SOURCE_NAME)
    executable_path = _resource_path(_EXECUTABLE_NAME)
    provenance_payload, _provenance_identity = _read_bounded_resource(
        provenance_path,
        limit=_MAX_PROVENANCE_BYTES,
        label="native operator verifier provenance",
    )
    expected_source, expected_executable = _decode_provenance(provenance_payload)
    if expected_source != (_EXPECTED_SOURCE_SIZE, _EXPECTED_SOURCE_SHA256):
        raise OperatorPresenceError(
            "native operator verifier source provenance does not match the reviewed pin"
        )
    if expected_executable != (_EXPECTED_EXECUTABLE_SIZE, _EXPECTED_EXECUTABLE_SHA256):
        raise OperatorPresenceError(
            "native operator verifier executable provenance does not match the reviewed pin"
        )
    _source_payload, source_identity = _read_bounded_resource(
        source_path,
        limit=_MAX_HELPER_BYTES,
        label="native operator verifier source",
    )
    if (source_identity.resolved_size, source_identity.sha256) != expected_source:
        raise OperatorPresenceError("native operator verifier source does not match provenance")

    try:
        executable_lexical = os.lstat(executable_path)
        if not 1 <= int(executable_lexical.st_size) <= _MAX_HELPER_BYTES:
            raise OperatorPresenceError(
                "native operator verifier executable exceeds its packaged size limit"
            )
        argv = PreparedProcessArgv(
            [str(executable_path)],
            artifact_paths=(str(executable_path),),
        ).freeze_persistent(platform_name="nt")
    except OperatorPresenceError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise OperatorPresenceError("native operator verifier executable is unavailable") from exc
    if len(argv.persistent_artifact_identities) != 1:
        raise OperatorPresenceError("native operator verifier identity is incomplete")
    executable_identity = argv.persistent_artifact_identities[0]
    if (
        executable_identity.resolved_size > _MAX_HELPER_BYTES
        or (
            executable_identity.resolved_size,
            executable_identity.sha256,
        )
        != expected_executable
    ):
        raise OperatorPresenceError("native operator verifier executable does not match provenance")
    return _ReviewedVerifier(
        argv=argv,
        working_directory=str(Path(executable_identity.resolved_path).parent),
    )


def _prepared_text(prepared: _RosterRollbackBinding, field: str) -> str:
    value = getattr(prepared, field, None)
    if not isinstance(value, str):
        raise OperatorPresenceError("prepared roster rollback binding is invalid")
    return value


def _complete_prepared_binding(prepared: _RosterRollbackBinding) -> tuple[str | int, ...]:
    from agency_runtime.core.store.roster import _roster_rollback_binding_primitives

    return _roster_rollback_binding_primitives(prepared)


def _request_payload(prepared: _RosterRollbackBinding, nonce: str) -> bytes:
    slug = _prepared_text(prepared, "slug")
    current_version = _prepared_text(prepared, "current_version")
    current_hash = _prepared_text(prepared, "current_hash")
    target_version = _prepared_text(prepared, "target_version")
    target_hash = _prepared_text(prepared, "target_hash")
    authority = _prepared_text(prepared, "activation_authority_kind")
    if (
        _SLUG.fullmatch(slug) is None
        or _VERSION.fullmatch(current_version) is None
        or _SHA256.fullmatch(current_hash) is None
        or _VERSION.fullmatch(target_version) is None
        or _SHA256.fullmatch(target_hash) is None
        or authority not in _AUTHORITIES
        or _SHA256.fullmatch(nonce) is None
    ):
        raise OperatorPresenceError("prepared roster rollback binding is invalid")
    payload = (
        "AGENCY-OPERATOR-PRESENCE/1\n"
        f"action={_ACTION}\n"
        f"slug={slug}\n"
        f"current-version={current_version}\n"
        f"current-hash={current_hash}\n"
        f"target-version={target_version}\n"
        f"target-hash={target_hash}\n"
        f"authority={authority}\n"
        f"nonce={nonce}\n"
    ).encode("ascii")
    if len(payload) > _MAX_PROTOCOL_BYTES:
        raise OperatorPresenceError("prepared roster rollback binding exceeds its size limit")
    return payload


def _verified_stdout(nonce: str) -> bytes:
    return (
        _PROTOCOL_HEADER
        + b"mode=verification\n"
        + f"action={_ACTION}\n".encode("ascii")
        + b"result=verified\n"
        + f"nonce={nonce}\n".encode("ascii")
    )


def _result_authorizes(result: BoundedBinaryProcessResult, *, nonce: str) -> bool:
    return (
        result.returncode == 0
        and result.stdout == _verified_stdout(nonce)
        and result.stderr == b""
        and not result.timed_out
        and not result.stdout_truncated
        and not result.stderr_truncated
        and not result.cancelled
        and result.failure_category is None
    )


def _verify_roster_rollback_binding(prepared: _RosterRollbackBinding) -> None:
    """Consume one native verification result for ``prepared`` or fail closed."""

    from agency_runtime.core.store.roster import _RosterRollbackBinding as PreparedType

    if type(prepared) is not PreparedType:
        raise OperatorPresenceError("prepared roster rollback binding is invalid")
    prepared_binding = _complete_prepared_binding(prepared)
    _assert_supported_host()
    nonce_bytes = _random_nonce_bytes()
    if not isinstance(nonce_bytes, bytes) or len(nonce_bytes) != 32:
        raise OperatorPresenceError("native operator verification nonce generation failed")
    nonce = nonce_bytes.hex()
    payload = _request_payload(prepared, nonce)
    verifier = _load_reviewed_verifier()
    try:
        result = run_bounded_binary_process(
            verifier.argv,
            timeout=_PROCESS_TIMEOUT_SECONDS,
            cwd=verifier.working_directory,
            env={},
            input_bytes=payload,
            max_input_bytes=_MAX_PROTOCOL_BYTES,
            max_stdout_bytes=_MAX_RESULT_BYTES,
            max_stderr_bytes=_MAX_RESULT_BYTES,
            retain_output_tail=False,
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise OperatorPresenceError(
            "native operator verification could not be completed; no persistent change was made"
        ) from exc
    if not _result_authorizes(result, nonce=nonce):
        raise OperatorPresenceError(
            "native operator presence was not verified; no persistent change was made"
        )
    if _complete_prepared_binding(prepared) != prepared_binding:
        raise OperatorPresenceError(
            "prepared roster rollback changed during operator verification; "
            "no persistent change was made"
        )


__all__: list[str] = []
