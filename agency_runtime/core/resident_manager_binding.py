"""Pure, content-free lifecycle contract for resident-manager host bindings."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from agency_runtime.core.bounded_json import (
    BoundedJSONError,
    DuplicateJSONKeyError,
    NonFiniteJSONNumberError,
    safe_load_bounded_json,
)
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL_HASH,
    RESIDENT_MANAGER_KERNEL_REFERENCE,
)

RESIDENT_MANAGER_BINDING_VERSION: Final[int] = 2
RESIDENT_MANAGER_BINDING_ID_PREFIX: Final[str] = "rmb-"
RESIDENT_MANAGER_BINDING_ID_HEX_CHARS: Final[int] = 32
MAX_RESIDENT_MANAGER_HOST_BYTES: Final[int] = 64
MAX_RESIDENT_MANAGER_BINDING_BYTES: Final[int] = 1_024
MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS: Final[int] = 384
MAX_RESIDENT_MANAGER_CONTROL_GENERATION: Final[int] = 2**63 - 1

PERSISTENT_RESIDENT_MANAGER_HOSTS: Final[tuple[str, ...]] = ("claude",)
REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS: Final[tuple[str, ...]] = (
    "codex",
    "openclaw",
    "hermes",
    "litellm",
    "unknown",
)
CANONICAL_RESIDENT_MANAGER_HOSTS: Final[tuple[str, ...]] = (
    *PERSISTENT_RESIDENT_MANAGER_HOSTS,
    *REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS,
)

RESIDENT_MANAGER_HOST_MODES: Final[tuple[str, str]] = (
    "persistent",
    "request_scoped",
)
RESIDENT_MANAGER_DELIVERY_MODES: Final[tuple[str, ...]] = (
    "injected",
    "reused",
    "restored",
    "request",
)

_PERSISTENT_DELIVERY_MODES: Final[frozenset[str]] = frozenset({"injected", "reused", "restored"})
_REQUEST_DELIVERY_MODES: Final[frozenset[str]] = frozenset({"request"})
_BINDING_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "binding_id",
        "host",
        "host_mode",
        "delivery_mode",
        "control_epoch",
        "kernel",
    }
)
_CONTROL_EPOCH_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "master_generation",
        "master_materialized",
        "host_generation",
        "host_materialized",
    }
)
_KERNEL_FIELDS: Final[frozenset[str]] = frozenset({"version", "content_hash", "slugs"})
_DOMAIN_SEPARATOR: Final[bytes] = b"agency-runtime:resident-manager-binding:v2\0"
_TURN_DOMAIN_SEPARATOR: Final[bytes] = b"agency-runtime:resident-manager-turn:v2\0"


@dataclass(frozen=True, slots=True)
class ResidentControlEpoch:
    """Exact master and host control identity governing one binding."""

    master_generation: int | None
    master_materialized: bool
    host_generation: int
    host_materialized: bool

    @property
    def reusable(self) -> bool:
        """Return whether persistent reuse is safe for this control identity."""

        return bool(
            self.master_materialized
            and self.master_generation is not None
            and self.host_materialized
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the exact bounded evidence projection."""

        return {
            "master_generation": self.master_generation,
            "master_materialized": self.master_materialized,
            "host_generation": self.host_generation,
            "host_materialized": self.host_materialized,
        }


@dataclass(frozen=True, slots=True)
class ResidentManagerBinding:
    """One session-bound resident-manager lifecycle decision.

    ``session_id`` deliberately is not a field. The opaque ``binding_id`` binds
    it cryptographically without copying correlation data into evidence.
    """

    version: int
    binding_id: str
    host: str
    host_mode: str
    delivery_mode: str
    control_epoch: ResidentControlEpoch

    @property
    def requires_kernel_injection(self) -> bool:
        """Return whether this delivery must include the compact kernel body."""

        return self.delivery_mode != "reused"

    def as_dict(self) -> dict[str, Any]:
        """Return the exact bounded, content-free evidence projection."""

        return {
            "version": self.version,
            "binding_id": self.binding_id,
            "host": self.host,
            "host_mode": self.host_mode,
            "delivery_mode": self.delivery_mode,
            "control_epoch": self.control_epoch.as_dict(),
            "kernel": RESIDENT_MANAGER_KERNEL_REFERENCE.as_dict(),
        }


def canonical_resident_manager_host(host: object) -> str:
    """Return one canonical host without retaining an unknown host label."""

    if host is None:
        return "unknown"
    if not isinstance(host, str):
        raise ValueError("resident-manager host must be a string")
    try:
        encoded = host.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("resident-manager host must be valid UTF-8 text") from exc
    if not host.isprintable():
        raise ValueError("resident-manager host must contain only printable characters")
    if len(encoded) > MAX_RESIDENT_MANAGER_HOST_BYTES:
        raise ValueError(
            f"resident-manager host exceeds the {MAX_RESIDENT_MANAGER_HOST_BYTES}-byte UTF-8 limit"
        )
    normalized = host.strip().casefold()
    if not normalized:
        return "unknown"
    return normalized if normalized in CANONICAL_RESIDENT_MANAGER_HOSTS else "unknown"


def resident_manager_host_mode(host: object) -> str:
    """Return the canonical lifecycle scope for ``host``."""

    return (
        "persistent"
        if canonical_resident_manager_host(host) in PERSISTENT_RESIDENT_MANAGER_HOSTS
        else "request_scoped"
    )


def _framed(parts: tuple[str, ...]) -> bytes:
    payload = bytearray()
    for part in parts:
        encoded = part.encode("utf-8")
        payload.extend(len(encoded).to_bytes(4, byteorder="big"))
        payload.extend(encoded)
    return bytes(payload)


def _control_generation(value: object, *, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= MAX_RESIDENT_MANAGER_CONTROL_GENERATION
    ):
        raise ValueError(f"resident-manager {field} is invalid")
    return value


def _materialized(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"resident-manager {field} must be a boolean")
    return value


def _master_control_generation(value: object, *, materialized: bool) -> int | None:
    if value is None:
        if materialized:
            raise ValueError("resident-manager materialized master control requires a generation")
        return None
    generation = _control_generation(value, field="master_generation")
    if not materialized and generation != 0:
        raise ValueError(
            "resident-manager unmaterialized master control generation must be zero or null"
        )
    return generation


def build_resident_control_epoch(
    *,
    master_generation: object = 0,
    master_materialized: object = True,
    host_generation: object = 0,
    host_materialized: object = True,
) -> ResidentControlEpoch:
    """Build one exact validated control epoch."""

    normalized_master_materialized = _materialized(
        master_materialized,
        field="master_materialized",
    )
    normalized_host_materialized = _materialized(
        host_materialized,
        field="host_materialized",
    )
    normalized_host_generation = _control_generation(
        host_generation,
        field="host_generation",
    )
    if not normalized_host_materialized and normalized_host_generation != 0:
        raise ValueError("resident-manager unmaterialized host control generation must be zero")
    return ResidentControlEpoch(
        master_generation=_master_control_generation(
            master_generation,
            materialized=normalized_master_materialized,
        ),
        master_materialized=normalized_master_materialized,
        host_generation=normalized_host_generation,
        host_materialized=normalized_host_materialized,
    )


def validate_resident_control_epoch(value: object) -> ResidentControlEpoch:
    """Validate one exact control epoch object."""

    if isinstance(value, ResidentControlEpoch):
        raw: Mapping[str, Any] = value.as_dict()
    elif isinstance(value, Mapping):
        raw = value
    else:
        raise ValueError("resident-manager control_epoch must be an object")
    if len(raw) != len(_CONTROL_EPOCH_FIELDS) or set(raw) != _CONTROL_EPOCH_FIELDS:
        raise ValueError("resident-manager control_epoch has invalid fields")
    return build_resident_control_epoch(
        master_generation=raw.get("master_generation"),
        master_materialized=raw.get("master_materialized"),
        host_generation=raw.get("host_generation"),
        host_materialized=raw.get("host_materialized"),
    )


def resident_manager_binding_id(
    *,
    session_id: object,
    host: object,
    control_epoch: object | None = None,
) -> str:
    """Return the deterministic session, host, and kernel-bound opaque ID."""

    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_host = canonical_resident_manager_host(host)
    epoch = validate_resident_control_epoch(
        build_resident_control_epoch() if control_epoch is None else control_epoch
    )
    digest = hashlib.sha256(
        _DOMAIN_SEPARATOR
        + _framed(
            (
                normalized_session,
                normalized_host,
                RESIDENT_MANAGER_KERNEL_HASH,
                "null" if epoch.master_generation is None else str(epoch.master_generation),
                "1" if epoch.master_materialized else "0",
                str(epoch.host_generation),
                "1" if epoch.host_materialized else "0",
            )
        )
    ).hexdigest()[:RESIDENT_MANAGER_BINDING_ID_HEX_CHARS]
    return f"{RESIDENT_MANAGER_BINDING_ID_PREFIX}{digest}"


def _validate_delivery_mode(*, host_mode: str, delivery_mode: object) -> str:
    if not isinstance(delivery_mode, str) or delivery_mode not in RESIDENT_MANAGER_DELIVERY_MODES:
        raise ValueError(
            "resident-manager delivery_mode must be exactly one of "
            + ", ".join(RESIDENT_MANAGER_DELIVERY_MODES)
        )
    allowed = _PERSISTENT_DELIVERY_MODES if host_mode == "persistent" else _REQUEST_DELIVERY_MODES
    if delivery_mode not in allowed:
        raise ValueError(f"resident-manager delivery_mode is invalid for {host_mode}")
    return delivery_mode


def build_resident_manager_binding(
    *,
    session_id: object,
    host: object,
    delivery_mode: object,
    control_epoch: object | None = None,
) -> ResidentManagerBinding:
    """Build one exact binding after canonicalizing its host."""

    canonical_host = canonical_resident_manager_host(host)
    host_mode = resident_manager_host_mode(canonical_host)
    normalized_delivery = _validate_delivery_mode(
        host_mode=host_mode,
        delivery_mode=delivery_mode,
    )
    epoch = validate_resident_control_epoch(
        build_resident_control_epoch() if control_epoch is None else control_epoch
    )
    return ResidentManagerBinding(
        version=RESIDENT_MANAGER_BINDING_VERSION,
        binding_id=resident_manager_binding_id(
            session_id=session_id,
            host=canonical_host,
            control_epoch=epoch,
        ),
        host=canonical_host,
        host_mode=host_mode,
        delivery_mode=normalized_delivery,
        control_epoch=epoch,
    )


def _exact_kernel_reference(value: object) -> None:
    if (
        not isinstance(value, Mapping)
        or len(value) != len(_KERNEL_FIELDS)
        or set(value) != _KERNEL_FIELDS
    ):
        raise ValueError("resident-manager kernel reference has invalid fields")
    version = value.get("version")
    content_hash = value.get("content_hash")
    slugs = value.get("slugs")
    expected = RESIDENT_MANAGER_KERNEL_REFERENCE
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != expected.version
        or not isinstance(content_hash, str)
        or content_hash != expected.content_hash
        or not isinstance(slugs, list)
        or slugs != list(expected.slugs)
        or any(not isinstance(slug, str) for slug in slugs)
    ):
        raise ValueError("resident-manager kernel reference is not current")


def _binding_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, ResidentManagerBinding):
        return value.as_dict()
    if isinstance(value, Mapping):
        return value
    raise ValueError("resident-manager binding must be an object")


def validate_resident_manager_binding(
    value: object,
    *,
    session_id: object,
) -> ResidentManagerBinding:
    """Validate and reconstruct an exact binding for ``session_id``."""

    raw = _binding_mapping(value)
    if len(raw) != len(_BINDING_FIELDS) or set(raw) != _BINDING_FIELDS:
        raise ValueError("resident-manager binding has invalid fields")

    version = raw.get("version")
    binding_id = raw.get("binding_id")
    host = raw.get("host")
    host_mode = raw.get("host_mode")
    delivery_mode = raw.get("delivery_mode")
    control_epoch = validate_resident_control_epoch(raw.get("control_epoch"))
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != RESIDENT_MANAGER_BINDING_VERSION
    ):
        raise ValueError("resident-manager binding version is unsupported")
    if not isinstance(host, str) or host not in CANONICAL_RESIDENT_MANAGER_HOSTS:
        raise ValueError("resident-manager binding host is not canonical")
    expected_host_mode = resident_manager_host_mode(host)
    if not isinstance(host_mode, str) or host_mode != expected_host_mode:
        raise ValueError("resident-manager binding host_mode does not match its host")
    normalized_delivery = _validate_delivery_mode(
        host_mode=host_mode,
        delivery_mode=delivery_mode,
    )
    _exact_kernel_reference(raw.get("kernel"))
    if (
        not isinstance(binding_id, str)
        or len(binding_id)
        != len(RESIDENT_MANAGER_BINDING_ID_PREFIX) + RESIDENT_MANAGER_BINDING_ID_HEX_CHARS
        or not binding_id.startswith(RESIDENT_MANAGER_BINDING_ID_PREFIX)
        or any(
            char not in "0123456789abcdef"
            for char in binding_id[len(RESIDENT_MANAGER_BINDING_ID_PREFIX) :]
        )
    ):
        raise ValueError("resident-manager binding_id is malformed")
    expected_binding_id = resident_manager_binding_id(
        session_id=session_id,
        host=host,
        control_epoch=control_epoch,
    )
    if not hmac.compare_digest(binding_id, expected_binding_id):
        raise ValueError("resident-manager binding_id does not match its session")
    return ResidentManagerBinding(
        version=version,
        binding_id=binding_id,
        host=host,
        host_mode=host_mode,
        delivery_mode=normalized_delivery,
        control_epoch=control_epoch,
    )


def serialize_resident_manager_binding(
    value: object,
    *,
    session_id: object,
) -> str:
    """Serialize one validated binding into its canonical bounded JSON form."""

    binding = validate_resident_manager_binding(value, session_id=session_id)
    serialized = json.dumps(
        binding.as_dict(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(serialized.encode("utf-8")) > MAX_RESIDENT_MANAGER_BINDING_BYTES:
        raise RuntimeError("resident-manager binding exceeds its serialization budget")
    return serialized


def deserialize_resident_manager_binding(
    payload: object,
    *,
    session_id: object,
) -> ResidentManagerBinding:
    """Parse only the canonical JSON emitted by this contract."""

    if not isinstance(payload, str):
        raise ValueError("resident-manager binding JSON must be a string")
    try:
        encoded = payload.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("resident-manager binding JSON must be valid UTF-8 text") from exc
    if len(encoded) > MAX_RESIDENT_MANAGER_BINDING_BYTES:
        raise ValueError(
            "resident-manager binding JSON exceeds the "
            f"{MAX_RESIDENT_MANAGER_BINDING_BYTES}-byte limit"
        )
    try:
        raw = safe_load_bounded_json(
            payload,
            maximum_bytes=MAX_RESIDENT_MANAGER_BINDING_BYTES,
            maximum_depth=4,
            maximum_nodes=64,
        )
    except DuplicateJSONKeyError as exc:
        raise ValueError("resident-manager binding JSON contains duplicate fields") from exc
    except NonFiniteJSONNumberError as exc:
        raise ValueError("resident-manager binding JSON contains a non-finite number") from exc
    except BoundedJSONError as exc:
        raise ValueError("resident-manager binding JSON is invalid") from exc
    except TypeError as exc:
        raise ValueError("resident-manager binding JSON is invalid") from exc
    binding = validate_resident_manager_binding(raw, session_id=session_id)
    if serialize_resident_manager_binding(binding, session_id=session_id) != payload:
        raise ValueError("resident-manager binding JSON is not canonical")
    return binding


def resident_manager_turn_reference_context(
    value: object,
    *,
    session_id: object,
    trace_id: object,
) -> str:
    """Render one bounded, prompt-free reference for the current turn."""

    binding = validate_resident_manager_binding(value, session_id=session_id)
    normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    turn_reference = hashlib.sha256(
        _TURN_DOMAIN_SEPARATOR
        + _framed(
            (
                binding.binding_id,
                normalized_trace,
            )
        )
    ).hexdigest()[:RESIDENT_MANAGER_BINDING_ID_HEX_CHARS]
    kernel = RESIDENT_MANAGER_KERNEL_REFERENCE
    context = (
        "[Agency resident managers active"
        f"; binding={binding.binding_id}"
        f"; turn=rmt-{turn_reference}"
        f"; host={binding.host}"
        f"; host_mode={binding.host_mode}"
        f"; delivery={binding.delivery_mode}"
        f"; epoch={binding.control_epoch.master_generation}:"
        f"{int(binding.control_epoch.master_materialized)}:"
        f"{binding.control_epoch.host_generation}:"
        f"{int(binding.control_epoch.host_materialized)}"
        f"; kernel=v{kernel.version}:{kernel.content_hash}"
        f"; managers={','.join(kernel.slugs)}]"
    )
    if len(context) > MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS:
        raise RuntimeError("resident-manager turn reference exceeds its context budget")
    return context


__all__ = [
    "CANONICAL_RESIDENT_MANAGER_HOSTS",
    "MAX_RESIDENT_MANAGER_BINDING_BYTES",
    "MAX_RESIDENT_MANAGER_CONTROL_GENERATION",
    "MAX_RESIDENT_MANAGER_HOST_BYTES",
    "MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS",
    "PERSISTENT_RESIDENT_MANAGER_HOSTS",
    "REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS",
    "RESIDENT_MANAGER_BINDING_ID_HEX_CHARS",
    "RESIDENT_MANAGER_BINDING_ID_PREFIX",
    "RESIDENT_MANAGER_BINDING_VERSION",
    "RESIDENT_MANAGER_DELIVERY_MODES",
    "RESIDENT_MANAGER_HOST_MODES",
    "ResidentControlEpoch",
    "ResidentManagerBinding",
    "build_resident_control_epoch",
    "build_resident_manager_binding",
    "canonical_resident_manager_host",
    "deserialize_resident_manager_binding",
    "resident_manager_binding_id",
    "resident_manager_host_mode",
    "resident_manager_turn_reference_context",
    "serialize_resident_manager_binding",
    "validate_resident_control_epoch",
    "validate_resident_manager_binding",
]
