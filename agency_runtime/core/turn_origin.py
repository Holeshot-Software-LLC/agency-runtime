"""Process-sealed origin evidence for adapter turn lifecycle events.

Origin is derived by owned adapter code from a host event and exact
correlation.  It is never accepted from user-message content or a serialized
request field.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field, replace
from typing import Final, Literal

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS

TurnOrigin = Literal[
    "external_user",
    "internal_retry",
    "stop_revalidation",
    "automatic_continuation",
    "native_child",
]

TURN_ORIGINS: Final[frozenset[str]] = frozenset(
    {
        "external_user",
        "internal_retry",
        "stop_revalidation",
        "automatic_continuation",
        "native_child",
    }
)
TURN_ORIGIN_CONTRACT_VERSION: Final[str] = "1"
TURN_ORIGIN_TTL_SECONDS: Final[int] = 60
TURN_ORIGIN_HOSTS: Final[frozenset[str]] = frozenset(
    (*EXECUTION_HOSTS, "generic", "http", "litellm", "mcp", "python")
)
_TURN_ORIGIN_TTL_NS: Final[int] = TURN_ORIGIN_TTL_SECONDS * 1_000_000_000
_TURN_ORIGIN_KEY: Final[bytes] = secrets.token_bytes(32)
_EVENTS_BY_ORIGIN: Final[dict[str, frozenset[str]]] = {
    "external_user": frozenset(
        {
            "adapter_preflight",
            "before_prompt_build",
            "pre_llm_call",
            "user_prompt_submit",
            "wrapper",
        }
    ),
    "internal_retry": frozenset(
        {
            "before_prompt_build_retry",
            "pre_llm_call_retry",
            "user_prompt_submit_retry",
        }
    ),
    "stop_revalidation": frozenset({"outbound_gate", "pre_verify", "stop"}),
    "automatic_continuation": frozenset({"goal_continuation", "post_compact"}),
    "native_child": frozenset({"native_child_started", "subagent_spawned", "subagent_start"}),
}


@dataclass(frozen=True, slots=True)
class TurnOriginReceipt:
    """Opaque current-process proof of one adapter-derived event origin."""

    origin: TurnOrigin
    host: str
    event: str
    session_id: str
    trace_id: str
    _attestation: str = field(default="", repr=False, compare=False)
    _expires_monotonic_ns: int = field(default=0, repr=False, compare=False)

    def as_dict(self) -> dict[str, str]:
        return {
            "contract_version": TURN_ORIGIN_CONTRACT_VERSION,
            "origin": self.origin,
            "host": self.host,
            "event": self.event,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
        }


def _payload(receipt: TurnOriginReceipt) -> bytes:
    return "\0".join(
        (
            TURN_ORIGIN_CONTRACT_VERSION,
            receipt.origin,
            receipt.host,
            receipt.event,
            receipt.session_id,
            receipt.trace_id,
            str(receipt._expires_monotonic_ns),
        )
    ).encode("utf-8")


def native_adapter_turn_origin(
    origin: TurnOrigin,
    *,
    host: object,
    event: object,
    session_id: object,
    trace_id: object,
) -> TurnOriginReceipt:
    """Seal one allowlisted owned-adapter lifecycle event."""

    if origin not in TURN_ORIGINS:
        raise ValueError("turn origin is invalid")
    normalized_host = str(host or "").strip().casefold()
    if normalized_host not in TURN_ORIGIN_HOSTS:
        raise ValueError("turn origin requires a supported adapter surface")
    normalized_event = str(event or "").strip().casefold()
    if normalized_event not in _EVENTS_BY_ORIGIN[origin]:
        raise ValueError("turn origin event is invalid for the declared origin")
    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    now = time.monotonic_ns()
    receipt = TurnOriginReceipt(
        origin=origin,
        host=normalized_host,
        event=normalized_event,
        session_id=normalized_session,
        trace_id=normalized_trace,
        _expires_monotonic_ns=now + _TURN_ORIGIN_TTL_NS,
    )
    signature = hmac.new(_TURN_ORIGIN_KEY, _payload(receipt), hashlib.sha256).hexdigest()
    return replace(receipt, _attestation=signature)


def current_turn_origin(
    value: object,
    *,
    host: object,
    session_id: object,
    trace_id: object,
) -> TurnOriginReceipt | None:
    """Return a fresh exact-correlation receipt, otherwise fail closed."""

    if not isinstance(value, TurnOriginReceipt):
        return None
    normalized_host = str(host or "").strip().casefold()
    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_trace = validate_correlation_id(trace_id, field="trace_id")
    if (
        value.origin not in TURN_ORIGINS
        or value.host != normalized_host
        or value.event not in _EVENTS_BY_ORIGIN[value.origin]
        or value.session_id != normalized_session
        or value.trace_id != normalized_trace
        or not value._attestation
        or value._expires_monotonic_ns <= 0
    ):
        return None
    expected = hmac.new(_TURN_ORIGIN_KEY, _payload(value), hashlib.sha256).hexdigest()
    remaining = value._expires_monotonic_ns - time.monotonic_ns()
    if (
        not hmac.compare_digest(value._attestation, expected)
        or remaining < 0
        or remaining > _TURN_ORIGIN_TTL_NS
    ):
        return None
    return value


__all__ = [
    "TURN_ORIGINS",
    "TURN_ORIGIN_CONTRACT_VERSION",
    "TURN_ORIGIN_HOSTS",
    "TURN_ORIGIN_TTL_SECONDS",
    "TurnOrigin",
    "TurnOriginReceipt",
    "current_turn_origin",
    "native_adapter_turn_origin",
]
