"""Pure, bounded contracts for one-use native-child specialist activation.

This module deliberately contains no persistence or prompt retrieval.  It
defines the immutable, content-free objects that an append-only Store can later
issue and consume atomically without placing prompt bodies, user messages, or
bearer secrets in durable evidence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, cast

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.resident_managers import is_resident_manager_slug
from agency_runtime.core.store.version_identity import normalize_version_identity

NATIVE_CHILD_ACTIVATION_LEGACY_VERSION: Final[int] = 1
NATIVE_CHILD_ACTIVATION_VERSION: Final[int] = 2
SUPPORTED_NATIVE_CHILD_ACTIVATION_VERSIONS: Final[tuple[int, ...]] = (
    NATIVE_CHILD_ACTIVATION_LEGACY_VERSION,
    NATIVE_CHILD_ACTIVATION_VERSION,
)
NATIVE_CHILD_ACTIVATION_GRANT_ID_PREFIX: Final[str] = "ncg-"
NATIVE_CHILD_ACTIVATION_RECEIPT_ID_PREFIX: Final[str] = "ncr-"
NATIVE_CHILD_ACTIVATION_ID_HEX_CHARS: Final[int] = 32
MAX_NATIVE_CHILD_ACTIVATION_BYTES: Final[int] = 8_192
MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS: Final[int] = 3_600
MAX_NATIVE_CHILD_TIMESTAMP: Final[int] = 2**63 - 1
MAX_NATIVE_CHILD_WORK_UNIT_BYTES: Final[int] = 160
MAX_NATIVE_CHILD_PATH_PREFIXES: Final[int] = 16
MAX_NATIVE_CHILD_PATH_BYTES: Final[int] = 256
MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS: Final[int] = 16
MAX_NATIVE_CHILD_EVIDENCE_TOKEN_BYTES: Final[int] = 64
MAX_NATIVE_CHILD_RUN_ID_BYTES: Final[int] = 256

CANONICAL_NATIVE_CHILD_HOSTS: Final[tuple[str, ...]] = (
    "claude",
    "codex",
    "hermes",
    "openclaw",
)
NATIVE_CHILD_MUTATION_MODES: Final[tuple[str, ...]] = (
    "read_only",
    "workspace_write",
)
NATIVE_CHILD_WORKER_BINDING_MODES: Final[tuple[str, ...]] = (
    "late_bound",
    "prebound",
)

_WORK_UNIT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")
_EVIDENCE_TOKEN_PATTERN = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,255}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID_PATTERN = re.compile(r"^(?:ncg|ncr)-[0-9a-f]{32}$")

_GRANT_V1_FIELDS = frozenset(
    {
        "version",
        "grant_id",
        "use_limit",
        "parent_session_id",
        "parent_trace_id",
        "work_unit_id",
        "host",
        "specialist",
        "mutation_scope",
        "evidence_contract",
        "issued_at",
        "expires_at",
    }
)
_GRANT_V2_FIELDS = _GRANT_V1_FIELDS | frozenset({"worker_binding"})
_SPECIALIST_FIELDS = frozenset({"slug", "version", "content_hash"})
_MUTATION_SCOPE_FIELDS = frozenset({"mode", "path_prefixes"})
_EVIDENCE_CONTRACT_FIELDS = frozenset({"contract_id", "requirements"})
_WORKER_BINDING_FIELDS = frozenset({"mode", "worker_kind", "worker_id"})
_RUN_IDENTITY_FIELDS = frozenset({"worker_kind", "worker_id", "native_run_id"})
_RECEIPT_FIELDS = frozenset(
    {
        "version",
        "receipt_id",
        "grant_id",
        "status",
        "parent_session_id",
        "parent_trace_id",
        "work_unit_id",
        "host",
        "specialist",
        "child_run",
        "consumed_at",
    }
)

_GRANT_DOMAINS = {
    NATIVE_CHILD_ACTIVATION_LEGACY_VERSION: (b"agency-runtime:native-child-activation-grant:v1\0"),
    NATIVE_CHILD_ACTIVATION_VERSION: b"agency-runtime:native-child-activation-grant:v2\0",
}
_RECEIPT_DOMAINS = {
    NATIVE_CHILD_ACTIVATION_LEGACY_VERSION: (
        b"agency-runtime:native-child-activation-receipt:v1\0"
    ),
    NATIVE_CHILD_ACTIVATION_VERSION: (b"agency-runtime:native-child-activation-receipt:v2\0"),
}


@dataclass(frozen=True, slots=True)
class NativeChildSpecialistIdentity:
    """Exactly one immutable non-manager specialist reference."""

    slug: str
    version: str
    content_hash: str

    def as_dict(self) -> dict[str, str]:
        return {
            "slug": self.slug,
            "version": self.version,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class NativeChildMutationScope:
    """Portable repository-relative mutation authority for one child."""

    mode: str
    path_prefixes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "path_prefixes": list(self.path_prefixes),
        }


@dataclass(frozen=True, slots=True)
class NativeChildEvidenceContract:
    """Versioned content-free evidence requirements for one child."""

    contract_id: str
    requirements: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "requirements": list(self.requirements),
        }


@dataclass(frozen=True, slots=True)
class NativeChildRunIdentity:
    """Host-neutral identity emitted by a native worker harness."""

    worker_kind: str
    worker_id: str
    native_run_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "worker_kind": self.worker_kind,
            "worker_id": self.worker_id,
            "native_run_id": self.native_run_id,
        }


@dataclass(frozen=True, slots=True)
class NativeChildWorkerBinding:
    """Authenticated worker semantics for one activation grant.

    ``prebound`` names the only worker allowed to consume the grant.
    ``late_bound`` deliberately carries no worker ID and authorizes the Store
    to bind the first successful consumer exactly once.
    """

    mode: str
    worker_kind: str
    worker_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "mode": self.mode,
            "worker_kind": self.worker_kind,
            "worker_id": self.worker_id,
        }


@dataclass(frozen=True, slots=True)
class NativeChildActivationGrant:
    """One immutable activation capsule intended for one atomic consumption."""

    version: int
    grant_id: str
    parent_session_id: str
    parent_trace_id: str
    work_unit_id: str
    host: str
    specialist: NativeChildSpecialistIdentity
    mutation_scope: NativeChildMutationScope
    evidence_contract: NativeChildEvidenceContract
    worker_binding: NativeChildWorkerBinding | None
    issued_at: int
    expires_at: int

    @property
    def use_limit(self) -> int:
        return 1

    @property
    def consumption_key(self) -> str:
        """Return the Store uniqueness key for atomic one-use enforcement."""

        return self.grant_id

    def as_dict(self) -> dict[str, Any]:
        result = {
            "version": self.version,
            "grant_id": self.grant_id,
            "use_limit": self.use_limit,
            "parent_session_id": self.parent_session_id,
            "parent_trace_id": self.parent_trace_id,
            "work_unit_id": self.work_unit_id,
            "host": self.host,
            "specialist": self.specialist.as_dict(),
            "mutation_scope": self.mutation_scope.as_dict(),
            "evidence_contract": self.evidence_contract.as_dict(),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }
        if self.version >= NATIVE_CHILD_ACTIVATION_VERSION:
            if self.worker_binding is None:
                raise RuntimeError("v2 native-child activation grant has no worker binding")
            result["worker_binding"] = self.worker_binding.as_dict()
        return result


@dataclass(frozen=True, slots=True)
class NativeChildActivationReceipt:
    """Append-only projection proving which native child consumed a grant."""

    version: int
    receipt_id: str
    grant_id: str
    parent_session_id: str
    parent_trace_id: str
    work_unit_id: str
    host: str
    specialist: NativeChildSpecialistIdentity
    child_run: NativeChildRunIdentity
    consumed_at: int

    @property
    def status(self) -> str:
        return "consumed"

    @property
    def consumption_key(self) -> str:
        return self.grant_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "receipt_id": self.receipt_id,
            "grant_id": self.grant_id,
            "status": self.status,
            "parent_session_id": self.parent_session_id,
            "parent_trace_id": self.parent_trace_id,
            "work_unit_id": self.work_unit_id,
            "host": self.host,
            "specialist": self.specialist.as_dict(),
            "child_run": self.child_run.as_dict(),
            "consumed_at": self.consumed_at,
        }


def _exact_mapping(
    value: object,
    *,
    fields: frozenset[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    if len(value) != len(fields) or set(value) != fields:
        raise ValueError(f"{label} has invalid fields")
    return value


def _bounded_utf8(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    try:
        encoded = normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be valid UTF-8 text") from exc
    if not normalized.isprintable():
        raise ValueError(f"{field} must contain only printable characters")
    if len(encoded) > maximum:
        raise ValueError(f"{field} exceeds the {maximum}-byte UTF-8 limit")
    return normalized


def _bounded_integer(value: object, *, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= MAX_NATIVE_CHILD_TIMESTAMP
    ):
        raise ValueError(f"{field} is invalid")
    return value


def _activation_version(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value not in SUPPORTED_NATIVE_CHILD_ACTIVATION_VERSIONS
    ):
        raise ValueError("native-child activation version is unsupported")
    return value


def _framed(parts: Sequence[str]) -> bytes:
    result = bytearray()
    for part in parts:
        encoded = part.encode("utf-8")
        result.extend(len(encoded).to_bytes(4, byteorder="big"))
        result.extend(encoded)
    return bytes(result)


def _digest_id(prefix: str, domain: bytes, parts: Sequence[str]) -> str:
    digest = hashlib.sha256(domain + _framed(parts)).hexdigest()
    return f"{prefix}{digest[:NATIVE_CHILD_ACTIVATION_ID_HEX_CHARS]}"


def canonical_native_child_host(value: object) -> str:
    """Return one exact supported native child host."""

    host = _bounded_utf8(value, field="host", maximum=32).casefold()
    if host not in CANONICAL_NATIVE_CHILD_HOSTS:
        raise ValueError("host must be exactly one of " + ", ".join(CANONICAL_NATIVE_CHILD_HOSTS))
    return host


def validate_native_child_work_unit_id(value: object) -> str:
    """Validate one stable, content-free work-unit identifier."""

    work_unit_id = _bounded_utf8(
        value,
        field="work_unit_id",
        maximum=MAX_NATIVE_CHILD_WORK_UNIT_BYTES,
    )
    if _WORK_UNIT_PATTERN.fullmatch(work_unit_id) is None:
        raise ValueError("work_unit_id must be a stable content-free identifier")
    return work_unit_id


def build_native_child_specialist_identity(
    *,
    slug: object,
    version: object,
    content_hash: object,
) -> NativeChildSpecialistIdentity:
    """Build one exact immutable non-manager specialist identity."""

    normalized_slug = normalize_agent_slug(slug)
    if is_resident_manager_slug(normalized_slug):
        raise ValueError("resident managers cannot be native-child specialists")
    if not isinstance(version, str):
        raise ValueError("specialist version must be a string")
    normalized_version = normalize_version_identity(version)
    if _RUN_ID_PATTERN.fullmatch(normalized_version) is None:
        raise ValueError("specialist version must be a bounded content-free identifier")
    if not isinstance(content_hash, str):
        raise ValueError("specialist content_hash must be a string")
    normalized_hash = content_hash.strip().casefold()
    if _SHA256_PATTERN.fullmatch(normalized_hash) is None:
        raise ValueError("specialist content_hash must be a lowercase SHA-256 digest")
    return NativeChildSpecialistIdentity(
        slug=normalized_slug,
        version=normalized_version,
        content_hash=normalized_hash,
    )


def validate_native_child_specialist_identity(
    value: object,
) -> NativeChildSpecialistIdentity:
    if isinstance(value, NativeChildSpecialistIdentity):
        raw: Mapping[str, Any] = value.as_dict()
    else:
        raw = _exact_mapping(
            value,
            fields=_SPECIALIST_FIELDS,
            label="specialist identity",
        )
    return build_native_child_specialist_identity(
        slug=raw.get("slug"),
        version=raw.get("version"),
        content_hash=raw.get("content_hash"),
    )


def _canonical_path_prefix(value: object) -> str:
    path = _bounded_utf8(
        value,
        field="mutation path prefix",
        maximum=MAX_NATIVE_CHILD_PATH_BYTES,
    )
    if path.startswith(("/", "\\", "~")) or "\\" in path or ":" in path or "//" in path:
        raise ValueError("mutation path prefixes must be repository-relative POSIX paths")
    if path == ".":
        return path
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("mutation path prefixes must be canonical repository-relative paths")
    return path


def build_native_child_mutation_scope(
    *,
    mode: object,
    path_prefixes: object = (),
) -> NativeChildMutationScope:
    """Build a deterministic, portable mutation boundary."""

    if not isinstance(mode, str):
        raise ValueError("mutation scope mode must be a string")
    normalized_mode = mode.strip().casefold()
    if normalized_mode not in NATIVE_CHILD_MUTATION_MODES:
        raise ValueError(
            "mutation scope mode must be exactly one of " + ", ".join(NATIVE_CHILD_MUTATION_MODES)
        )
    if not isinstance(path_prefixes, (list, tuple)):
        raise ValueError("mutation path_prefixes must be a list")
    if len(path_prefixes) > MAX_NATIVE_CHILD_PATH_PREFIXES:
        raise ValueError(
            f"mutation scope supports at most {MAX_NATIVE_CHILD_PATH_PREFIXES} path prefixes"
        )
    normalized_paths = tuple(sorted(_canonical_path_prefix(item) for item in path_prefixes))
    if len(normalized_paths) != len(set(normalized_paths)):
        raise ValueError("mutation path_prefixes must not contain duplicates")
    if normalized_mode == "read_only" and normalized_paths:
        raise ValueError("read_only mutation scope cannot contain writable path prefixes")
    if normalized_mode == "workspace_write" and not normalized_paths:
        raise ValueError("workspace_write mutation scope requires at least one path prefix")
    return NativeChildMutationScope(
        mode=normalized_mode,
        path_prefixes=normalized_paths,
    )


def validate_native_child_mutation_scope(value: object) -> NativeChildMutationScope:
    if isinstance(value, NativeChildMutationScope):
        raw: Mapping[str, Any] = value.as_dict()
    else:
        raw = _exact_mapping(
            value,
            fields=_MUTATION_SCOPE_FIELDS,
            label="mutation scope",
        )
    return build_native_child_mutation_scope(
        mode=raw.get("mode"),
        path_prefixes=raw.get("path_prefixes"),
    )


def _evidence_token(value: object, *, field: str) -> str:
    token = _bounded_utf8(
        value,
        field=field,
        maximum=MAX_NATIVE_CHILD_EVIDENCE_TOKEN_BYTES,
    ).casefold()
    if _EVIDENCE_TOKEN_PATTERN.fullmatch(token) is None:
        raise ValueError(f"{field} must be a bounded lowercase policy token")
    return token


def build_native_child_evidence_contract(
    *,
    contract_id: object,
    requirements: object = (),
) -> NativeChildEvidenceContract:
    """Build one versioned content-free evidence requirement set."""

    normalized_contract = _evidence_token(contract_id, field="evidence contract_id")
    if not isinstance(requirements, (list, tuple)):
        raise ValueError("evidence requirements must be a list")
    if len(requirements) > MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS:
        raise ValueError(
            "evidence contract supports at most "
            f"{MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS} requirements"
        )
    normalized_requirements = tuple(
        sorted(_evidence_token(item, field="evidence requirement") for item in requirements)
    )
    if len(normalized_requirements) != len(set(normalized_requirements)):
        raise ValueError("evidence requirements must not contain duplicates")
    return NativeChildEvidenceContract(
        contract_id=normalized_contract,
        requirements=normalized_requirements,
    )


def validate_native_child_evidence_contract(
    value: object,
) -> NativeChildEvidenceContract:
    if isinstance(value, NativeChildEvidenceContract):
        raw: Mapping[str, Any] = value.as_dict()
    else:
        raw = _exact_mapping(
            value,
            fields=_EVIDENCE_CONTRACT_FIELDS,
            label="evidence contract",
        )
    return build_native_child_evidence_contract(
        contract_id=raw.get("contract_id"),
        requirements=raw.get("requirements"),
    )


def build_native_child_run_identity(
    *,
    worker_kind: object,
    worker_id: object,
    native_run_id: object,
) -> NativeChildRunIdentity:
    """Build one host-neutral native-worker identity."""

    values: dict[str, str] = {}
    for field, value in (
        ("worker_kind", worker_kind),
        ("worker_id", worker_id),
        ("native_run_id", native_run_id),
    ):
        normalized = _bounded_utf8(
            value,
            field=field,
            maximum=MAX_NATIVE_CHILD_RUN_ID_BYTES,
        )
        if _RUN_ID_PATTERN.fullmatch(normalized) is None:
            raise ValueError(f"{field} must be a bounded content-free identifier")
        values[field] = normalized
    return NativeChildRunIdentity(**values)


def validate_native_child_run_identity(value: object) -> NativeChildRunIdentity:
    if isinstance(value, NativeChildRunIdentity):
        raw: Mapping[str, Any] = value.as_dict()
    else:
        raw = _exact_mapping(
            value,
            fields=_RUN_IDENTITY_FIELDS,
            label="native child run identity",
        )
    return build_native_child_run_identity(
        worker_kind=raw.get("worker_kind"),
        worker_id=raw.get("worker_id"),
        native_run_id=raw.get("native_run_id"),
    )


def build_native_child_worker_binding(
    *,
    mode: object,
    worker_kind: object,
    worker_id: object = "",
) -> NativeChildWorkerBinding:
    """Build explicit prebound or one-time late-bound worker semantics."""

    if not isinstance(mode, str):
        raise ValueError("worker binding mode must be a string")
    normalized_mode = mode.strip().casefold()
    if normalized_mode not in NATIVE_CHILD_WORKER_BINDING_MODES:
        raise ValueError(
            "worker binding mode must be exactly one of "
            + ", ".join(NATIVE_CHILD_WORKER_BINDING_MODES)
        )
    normalized_kind = _bounded_utf8(
        worker_kind,
        field="worker binding worker_kind",
        maximum=MAX_NATIVE_CHILD_RUN_ID_BYTES,
    )
    if _RUN_ID_PATTERN.fullmatch(normalized_kind) is None:
        raise ValueError("worker binding worker_kind must be a content-free identifier")
    if not isinstance(worker_id, str):
        raise ValueError("worker binding worker_id must be a string")
    normalized_worker = worker_id.strip()
    if normalized_mode == "late_bound":
        if normalized_worker:
            raise ValueError("late_bound worker binding cannot name a worker_id")
    else:
        normalized_worker = _bounded_utf8(
            normalized_worker,
            field="worker binding worker_id",
            maximum=MAX_NATIVE_CHILD_RUN_ID_BYTES,
        )
        if _RUN_ID_PATTERN.fullmatch(normalized_worker) is None:
            raise ValueError("worker binding worker_id must be a content-free identifier")
    return NativeChildWorkerBinding(
        mode=normalized_mode,
        worker_kind=normalized_kind,
        worker_id=normalized_worker,
    )


def validate_native_child_worker_binding(value: object) -> NativeChildWorkerBinding:
    if isinstance(value, NativeChildWorkerBinding):
        raw: Mapping[str, Any] = value.as_dict()
    else:
        raw = _exact_mapping(
            value,
            fields=_WORKER_BINDING_FIELDS,
            label="worker binding",
        )
    return build_native_child_worker_binding(
        mode=raw.get("mode"),
        worker_kind=raw.get("worker_kind"),
        worker_id=raw.get("worker_id"),
    )


def _worker_binding_for_version(
    version: int,
    value: object,
) -> NativeChildWorkerBinding | None:
    if version == NATIVE_CHILD_ACTIVATION_LEGACY_VERSION:
        if value is not None:
            raise ValueError("v1 native-child activation grants cannot contain worker_binding")
        return None
    if value is None:
        return build_native_child_worker_binding(
            mode="late_bound",
            worker_kind="generic-worker",
        )
    return validate_native_child_worker_binding(value)


def _grant_id_parts(
    *,
    version: int,
    parent_session_id: str,
    parent_trace_id: str,
    work_unit_id: str,
    host: str,
    specialist: NativeChildSpecialistIdentity,
    mutation_scope: NativeChildMutationScope,
    evidence_contract: NativeChildEvidenceContract,
    worker_binding: NativeChildWorkerBinding | None,
    issued_at: int,
    expires_at: int,
) -> tuple[str, ...]:
    legacy_parts = (
        parent_session_id,
        parent_trace_id,
        work_unit_id,
        host,
        specialist.slug,
        specialist.version,
        specialist.content_hash,
        mutation_scope.mode,
        *mutation_scope.path_prefixes,
        "",
        evidence_contract.contract_id,
        *evidence_contract.requirements,
        "",
        str(issued_at),
        str(expires_at),
        "1",
    )
    if version == NATIVE_CHILD_ACTIVATION_LEGACY_VERSION:
        return legacy_parts
    binding = cast(NativeChildWorkerBinding, worker_binding)
    return (
        *legacy_parts,
        binding.mode,
        binding.worker_kind,
        binding.worker_id,
        str(version),
    )


def native_child_activation_grant_id(
    *,
    parent_session_id: object,
    parent_trace_id: object,
    work_unit_id: object,
    host: object,
    specialist: object,
    mutation_scope: object,
    evidence_contract: object,
    worker_binding: object = None,
    issued_at: object,
    expires_at: object,
    version: object = NATIVE_CHILD_ACTIVATION_VERSION,
) -> str:
    """Return a deterministic opaque ID bound to the complete grant capsule."""

    activation_version = _activation_version(version)
    session = validate_correlation_id(parent_session_id, field="parent_session_id")
    trace = validate_correlation_id(parent_trace_id, field="parent_trace_id")
    unit = validate_native_child_work_unit_id(work_unit_id)
    canonical_host = canonical_native_child_host(host)
    specialist_identity = validate_native_child_specialist_identity(specialist)
    scope = validate_native_child_mutation_scope(mutation_scope)
    evidence = validate_native_child_evidence_contract(evidence_contract)
    binding = _worker_binding_for_version(activation_version, worker_binding)
    issued = _bounded_integer(issued_at, field="issued_at")
    expires = _bounded_integer(expires_at, field="expires_at")
    if expires <= issued:
        raise ValueError("expires_at must be greater than issued_at")
    if expires - issued > MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS:
        raise ValueError(
            "native-child activation lifetime exceeds the "
            f"{MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS}-second limit"
        )
    return _digest_id(
        NATIVE_CHILD_ACTIVATION_GRANT_ID_PREFIX,
        _GRANT_DOMAINS[activation_version],
        _grant_id_parts(
            version=activation_version,
            parent_session_id=session,
            parent_trace_id=trace,
            work_unit_id=unit,
            host=canonical_host,
            specialist=specialist_identity,
            mutation_scope=scope,
            evidence_contract=evidence,
            worker_binding=binding,
            issued_at=issued,
            expires_at=expires,
        ),
    )


def build_native_child_activation_grant(
    *,
    parent_session_id: object,
    parent_trace_id: object,
    work_unit_id: object,
    host: object,
    specialist: object,
    mutation_scope: object,
    evidence_contract: object,
    worker_binding: object = None,
    issued_at: object,
    expires_at: object,
    version: object = NATIVE_CHILD_ACTIVATION_VERSION,
) -> NativeChildActivationGrant:
    """Build one immutable one-use activation capsule."""

    activation_version = _activation_version(version)
    session = validate_correlation_id(parent_session_id, field="parent_session_id")
    trace = validate_correlation_id(parent_trace_id, field="parent_trace_id")
    unit = validate_native_child_work_unit_id(work_unit_id)
    canonical_host = canonical_native_child_host(host)
    specialist_identity = validate_native_child_specialist_identity(specialist)
    scope = validate_native_child_mutation_scope(mutation_scope)
    evidence = validate_native_child_evidence_contract(evidence_contract)
    binding = _worker_binding_for_version(activation_version, worker_binding)
    issued = _bounded_integer(issued_at, field="issued_at")
    expires = _bounded_integer(expires_at, field="expires_at")
    grant_id = native_child_activation_grant_id(
        parent_session_id=session,
        parent_trace_id=trace,
        work_unit_id=unit,
        host=canonical_host,
        specialist=specialist_identity,
        mutation_scope=scope,
        evidence_contract=evidence,
        worker_binding=binding,
        issued_at=issued,
        expires_at=expires,
        version=activation_version,
    )
    return NativeChildActivationGrant(
        version=activation_version,
        grant_id=grant_id,
        parent_session_id=session,
        parent_trace_id=trace,
        work_unit_id=unit,
        host=canonical_host,
        specialist=specialist_identity,
        mutation_scope=scope,
        evidence_contract=evidence,
        worker_binding=binding,
        issued_at=issued,
        expires_at=expires,
    )


def validate_native_child_activation_grant(
    value: object,
) -> NativeChildActivationGrant:
    """Validate and reconstruct an exact activation grant."""

    if isinstance(value, NativeChildActivationGrant):
        raw: Mapping[str, Any] = value.as_dict()
    elif isinstance(value, Mapping):
        raw = value
    else:
        raise ValueError("native-child activation grant must be an object")
    activation_version = _activation_version(raw.get("version"))
    raw = _exact_mapping(
        raw,
        fields=(
            _GRANT_V1_FIELDS
            if activation_version == NATIVE_CHILD_ACTIVATION_LEGACY_VERSION
            else _GRANT_V2_FIELDS
        ),
        label="native-child activation grant",
    )
    if raw.get("use_limit") != 1 or isinstance(raw.get("use_limit"), bool):
        raise ValueError("native-child activation grant must be exactly one-use")
    grant = build_native_child_activation_grant(
        parent_session_id=raw.get("parent_session_id"),
        parent_trace_id=raw.get("parent_trace_id"),
        work_unit_id=raw.get("work_unit_id"),
        host=raw.get("host"),
        specialist=raw.get("specialist"),
        mutation_scope=raw.get("mutation_scope"),
        evidence_contract=raw.get("evidence_contract"),
        worker_binding=(
            raw.get("worker_binding")
            if activation_version == NATIVE_CHILD_ACTIVATION_VERSION
            else None
        ),
        issued_at=raw.get("issued_at"),
        expires_at=raw.get("expires_at"),
        version=activation_version,
    )
    supplied_id = raw.get("grant_id")
    if (
        not isinstance(supplied_id, str)
        or _OPAQUE_ID_PATTERN.fullmatch(supplied_id) is None
        or not supplied_id.startswith(NATIVE_CHILD_ACTIVATION_GRANT_ID_PREFIX)
        or not hmac.compare_digest(supplied_id, grant.grant_id)
    ):
        raise ValueError("native-child activation grant_id does not match its capsule")
    return grant


def _receipt_id_parts(
    grant: NativeChildActivationGrant,
    child_run: NativeChildRunIdentity,
    consumed_at: int,
) -> tuple[str, ...]:
    return (
        grant.grant_id,
        grant.parent_session_id,
        grant.parent_trace_id,
        grant.work_unit_id,
        grant.host,
        grant.specialist.slug,
        grant.specialist.version,
        grant.specialist.content_hash,
        child_run.worker_kind,
        child_run.worker_id,
        child_run.native_run_id,
        str(consumed_at),
        "consumed",
    )


def build_native_child_activation_receipt(
    grant: object,
    *,
    child_run: object,
    consumed_at: object,
) -> NativeChildActivationReceipt:
    """Build the append-only projection for one atomic grant consumption."""

    validated_grant = validate_native_child_activation_grant(grant)
    run = validate_native_child_run_identity(child_run)
    consumed = _bounded_integer(consumed_at, field="consumed_at")
    if not validated_grant.issued_at <= consumed <= validated_grant.expires_at:
        raise ValueError("consumed_at must fall within the activation grant lifetime")
    receipt_id = _digest_id(
        NATIVE_CHILD_ACTIVATION_RECEIPT_ID_PREFIX,
        _RECEIPT_DOMAINS[validated_grant.version],
        _receipt_id_parts(validated_grant, run, consumed),
    )
    return NativeChildActivationReceipt(
        version=validated_grant.version,
        receipt_id=receipt_id,
        grant_id=validated_grant.grant_id,
        parent_session_id=validated_grant.parent_session_id,
        parent_trace_id=validated_grant.parent_trace_id,
        work_unit_id=validated_grant.work_unit_id,
        host=validated_grant.host,
        specialist=validated_grant.specialist,
        child_run=run,
        consumed_at=consumed,
    )


def validate_native_child_activation_receipt(
    value: object,
    *,
    grant: object,
) -> NativeChildActivationReceipt:
    """Validate one receipt against the exact grant it claims to consume."""

    if isinstance(value, NativeChildActivationReceipt):
        raw: Mapping[str, Any] = value.as_dict()
    else:
        raw = _exact_mapping(
            value,
            fields=_RECEIPT_FIELDS,
            label="native-child activation receipt",
        )
    receipt_version = _activation_version(raw.get("version"))
    if raw.get("status") != "consumed":
        raise ValueError("native-child activation receipt status must be consumed")
    validated_grant = validate_native_child_activation_grant(grant)
    if receipt_version != validated_grant.version:
        raise ValueError("native-child activation receipt version does not match its grant")
    expected = build_native_child_activation_receipt(
        validated_grant,
        child_run=raw.get("child_run"),
        consumed_at=raw.get("consumed_at"),
    )
    projected_grant_fields = (
        ("grant_id", validated_grant.grant_id),
        ("parent_session_id", validated_grant.parent_session_id),
        ("parent_trace_id", validated_grant.parent_trace_id),
        ("work_unit_id", validated_grant.work_unit_id),
        ("host", validated_grant.host),
    )
    if any(raw.get(field) != expected_value for field, expected_value in projected_grant_fields):
        raise ValueError("native-child activation receipt does not match its grant")
    try:
        specialist = validate_native_child_specialist_identity(raw.get("specialist"))
    except ValueError as exc:
        raise ValueError("native-child activation receipt specialist is invalid") from exc
    if specialist != validated_grant.specialist:
        raise ValueError("native-child activation receipt specialist does not match its grant")
    supplied_id = raw.get("receipt_id")
    if (
        not isinstance(supplied_id, str)
        or _OPAQUE_ID_PATTERN.fullmatch(supplied_id) is None
        or not supplied_id.startswith(NATIVE_CHILD_ACTIVATION_RECEIPT_ID_PREFIX)
        or not hmac.compare_digest(supplied_id, expected.receipt_id)
    ):
        raise ValueError("native-child activation receipt_id does not match its projection")
    return expected


def _canonical_json(value: Mapping[str, Any], *, label: str) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(payload.encode("utf-8")) > MAX_NATIVE_CHILD_ACTIVATION_BYTES:
        raise RuntimeError(f"{label} exceeds its serialization budget")
    return payload


def serialize_native_child_activation_grant(value: object) -> str:
    grant = validate_native_child_activation_grant(value)
    return _canonical_json(grant.as_dict(), label="native-child activation grant")


def serialize_native_child_activation_receipt(
    value: object,
    *,
    grant: object,
) -> str:
    receipt = validate_native_child_activation_receipt(value, grant=grant)
    return _canonical_json(receipt.as_dict(), label="native-child activation receipt")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("native-child activation JSON contains duplicate fields")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("native-child activation JSON contains a non-finite number")


def _parse_canonical_json(payload: object) -> Mapping[str, Any]:
    if not isinstance(payload, str):
        raise ValueError("native-child activation JSON must be a string")
    try:
        encoded = payload.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("native-child activation JSON must be valid UTF-8 text") from exc
    if len(encoded) > MAX_NATIVE_CHILD_ACTIVATION_BYTES:
        raise ValueError(
            "native-child activation JSON exceeds the "
            f"{MAX_NATIVE_CHILD_ACTIVATION_BYTES}-byte limit"
        )
    try:
        raw = json.loads(
            payload,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("native-child activation JSON is invalid") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("native-child activation JSON must contain an object")
    return raw


def deserialize_native_child_activation_grant(payload: object) -> NativeChildActivationGrant:
    raw = _parse_canonical_json(payload)
    grant = validate_native_child_activation_grant(raw)
    if serialize_native_child_activation_grant(grant) != payload:
        raise ValueError("native-child activation grant JSON is not canonical")
    return grant


def deserialize_native_child_activation_receipt(
    payload: object,
    *,
    grant: object,
) -> NativeChildActivationReceipt:
    raw = _parse_canonical_json(payload)
    receipt = validate_native_child_activation_receipt(raw, grant=grant)
    if serialize_native_child_activation_receipt(receipt, grant=grant) != payload:
        raise ValueError("native-child activation receipt JSON is not canonical")
    return receipt


__all__ = [
    "CANONICAL_NATIVE_CHILD_HOSTS",
    "MAX_NATIVE_CHILD_ACTIVATION_BYTES",
    "MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS",
    "MAX_NATIVE_CHILD_EVIDENCE_REQUIREMENTS",
    "MAX_NATIVE_CHILD_EVIDENCE_TOKEN_BYTES",
    "MAX_NATIVE_CHILD_PATH_BYTES",
    "MAX_NATIVE_CHILD_PATH_PREFIXES",
    "MAX_NATIVE_CHILD_RUN_ID_BYTES",
    "MAX_NATIVE_CHILD_TIMESTAMP",
    "MAX_NATIVE_CHILD_WORK_UNIT_BYTES",
    "NATIVE_CHILD_ACTIVATION_GRANT_ID_PREFIX",
    "NATIVE_CHILD_ACTIVATION_ID_HEX_CHARS",
    "NATIVE_CHILD_ACTIVATION_LEGACY_VERSION",
    "NATIVE_CHILD_ACTIVATION_RECEIPT_ID_PREFIX",
    "NATIVE_CHILD_ACTIVATION_VERSION",
    "NATIVE_CHILD_MUTATION_MODES",
    "NATIVE_CHILD_WORKER_BINDING_MODES",
    "SUPPORTED_NATIVE_CHILD_ACTIVATION_VERSIONS",
    "NativeChildActivationGrant",
    "NativeChildActivationReceipt",
    "NativeChildEvidenceContract",
    "NativeChildMutationScope",
    "NativeChildRunIdentity",
    "NativeChildSpecialistIdentity",
    "NativeChildWorkerBinding",
    "build_native_child_activation_grant",
    "build_native_child_activation_receipt",
    "build_native_child_evidence_contract",
    "build_native_child_mutation_scope",
    "build_native_child_run_identity",
    "build_native_child_specialist_identity",
    "build_native_child_worker_binding",
    "canonical_native_child_host",
    "deserialize_native_child_activation_grant",
    "deserialize_native_child_activation_receipt",
    "native_child_activation_grant_id",
    "serialize_native_child_activation_grant",
    "serialize_native_child_activation_receipt",
    "validate_native_child_activation_grant",
    "validate_native_child_activation_receipt",
    "validate_native_child_evidence_contract",
    "validate_native_child_mutation_scope",
    "validate_native_child_run_identity",
    "validate_native_child_specialist_identity",
    "validate_native_child_work_unit_id",
    "validate_native_child_worker_binding",
]
