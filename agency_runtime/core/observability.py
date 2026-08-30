"""Content-free runtime boundary observations.

The envelope in this module is deliberately much smaller than a general
structured logger.  Callers may record only fixed labels, a random request
identity, a one-way correlation digest, timings, and an optional Store
generation.  Prompts, tool arguments, bearer tokens, exception messages, SQL,
and filesystem paths have no field in the contract.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
from contextvars import ContextVar, Token
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic_ns
from types import TracebackType
from typing import Any
from uuid import UUID

from agency_runtime.core.correlation import validate_correlation_id

logger = logging.getLogger("agency_runtime.observation")

OBSERVATION_SCHEMA_VERSION = 1
SLOW_SQLITE_MILLISECONDS = 50.0

_SURFACES = frozenset({"dashboard", "hook", "http", "mcp", "store", "ui"})
_OUTCOMES = frozenset({"bypassed", "degraded", "denied", "error", "ok"})
_LABEL = re.compile(r"[a-z][a-z0-9_.-]{0,63}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_AGENCY_REQUEST_ID = re.compile(r"arq-[a-f0-9]{32}\Z")

_current_request_id: ContextVar[str] = ContextVar(
    "agency_observation_request_id",
    default="",
)
_current_correlation_digest: ContextVar[str] = ContextVar(
    "agency_observation_correlation_digest",
    default="",
)
_current_boundary: ContextVar[RuntimeBoundary | None] = ContextVar(
    "agency_observation_boundary",
    default=None,
)


def new_request_id() -> str:
    """Return a cryptographically random, log-safe request identifier."""

    return f"arq-{secrets.token_hex(16)}"


def normalize_request_id(value: object) -> str:
    """Accept an Agency ID or a canonical browser-generated UUIDv4."""

    text = str(value or "").strip().casefold()
    if _AGENCY_REQUEST_ID.fullmatch(text) is not None:
        return text
    try:
        parsed = UUID(text)
    except (AttributeError, ValueError):
        raise ValueError("request_id must be a random Agency ID or canonical UUIDv4") from None
    if parsed.version != 4 or str(parsed) != text:
        raise ValueError("request_id must be a random Agency ID or canonical UUIDv4")
    return text


def correlation_observation_digest(value: object) -> str:
    """Hash one bounded correlation ID without retaining the source value.

    Correlation IDs are opaque runtime identities, not user content.  The
    domain prefix prevents the digest from being confused with evidence or
    credential hashes elsewhere in the runtime.
    """

    normalized = validate_correlation_id(value, field="observation_correlation_id")
    return sha256(b"agency-runtime-observation-v1\x00" + normalized.encode("utf-8")).hexdigest()


def _label(value: object, *, field: str) -> str:
    text = str(value or "").strip().casefold()
    if _LABEL.fullmatch(text) is None:
        raise ValueError(f"{field} must be a bounded observation label")
    return text


def _digest(value: object) -> str:
    text = str(value or "").strip().casefold()
    if text and _DIGEST.fullmatch(text) is None:
        raise ValueError("correlation_digest must be a lowercase SHA-256 digest")
    return text


def _generation(value: object | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2**63 - 1:
        raise ValueError("store_generation must be a non-negative integer")
    return value


@dataclass(frozen=True)
class ObservationEnvelope:
    """Validated metadata-only result emitted at one runtime boundary."""

    request_id: str
    correlation_digest: str
    surface: str
    operation: str
    outcome: str
    reason_code: str
    duration_ms: float
    store_generation: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", normalize_request_id(self.request_id))
        object.__setattr__(self, "correlation_digest", _digest(self.correlation_digest))
        surface = _label(self.surface, field="surface")
        if surface not in _SURFACES:
            raise ValueError("surface is not supported")
        object.__setattr__(self, "surface", surface)
        object.__setattr__(self, "operation", _label(self.operation, field="operation"))
        outcome = _label(self.outcome, field="outcome")
        if outcome not in _OUTCOMES:
            raise ValueError("outcome is not supported")
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "reason_code", _label(self.reason_code, field="reason_code"))
        if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, (int, float)):
            raise ValueError("duration_ms must be numeric")
        duration = round(float(self.duration_ms), 3)
        if not 0.0 <= duration <= 86_400_000.0:
            raise ValueError("duration_ms is outside the observation bound")
        object.__setattr__(self, "duration_ms", duration)
        object.__setattr__(self, "store_generation", _generation(self.store_generation))

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": OBSERVATION_SCHEMA_VERSION,
            "request_id": self.request_id,
            "correlation_digest": self.correlation_digest,
            "surface": self.surface,
            "operation": self.operation,
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "duration_ms": self.duration_ms,
        }
        if self.store_generation is not None:
            payload["store_generation"] = self.store_generation
        return payload

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def emit_observation(envelope: ObservationEnvelope) -> None:
    """Emit one single-line envelope with no content-bearing interpolation."""

    logger.info("agency_observation %s", envelope.to_json())


class RuntimeBoundary:
    """Context manager that correlates nested Store work with one request."""

    def __init__(
        self,
        *,
        surface: str,
        operation: str,
        request_id: str | None = None,
        correlation_digest: str = "",
        store_generation: int | None = None,
    ) -> None:
        inherited_request = _current_request_id.get()
        inherited_digest = _current_correlation_digest.get()
        self.request_id = normalize_request_id(request_id or inherited_request or new_request_id())
        self.correlation_digest = _digest(correlation_digest or inherited_digest)
        self.surface = _label(surface, field="surface")
        if self.surface not in _SURFACES:
            raise ValueError("surface is not supported")
        self.operation = _label(operation, field="operation")
        self.store_generation = _generation(store_generation)
        self._started_ns = 0
        self._outcome = ""
        self._reason_code = ""
        self._emitted: ObservationEnvelope | None = None
        self._tokens: tuple[Token[str], Token[str], Token[RuntimeBoundary | None]] | None = None

    def __enter__(self) -> RuntimeBoundary:
        if self._started_ns:
            raise RuntimeError("observation boundary cannot be re-entered")
        self._started_ns = monotonic_ns()
        self._tokens = (
            _current_request_id.set(self.request_id),
            _current_correlation_digest.set(self.correlation_digest),
            _current_boundary.set(self),
        )
        return self

    def set_outcome(
        self,
        outcome: str,
        reason_code: str,
        *,
        store_generation: int | None = None,
        only_if_unset: bool = False,
    ) -> None:
        if only_if_unset and self._outcome:
            return
        normalized_outcome = _label(outcome, field="outcome")
        if normalized_outcome not in _OUTCOMES:
            raise ValueError("outcome is not supported")
        self._outcome = normalized_outcome
        self._reason_code = _label(reason_code, field="reason_code")
        if store_generation is not None:
            self.store_generation = _generation(store_generation)

    def set_correlation_id(self, value: object) -> str:
        """Attach a one-way digest after a boundary creates its trace."""

        digest = correlation_observation_digest(value)
        self.correlation_digest = digest
        _current_correlation_digest.set(digest)
        return digest

    def emit(self) -> ObservationEnvelope:
        if self._emitted is not None:
            return self._emitted
        if not self._started_ns:
            raise RuntimeError("observation boundary has not started")
        elapsed = min((monotonic_ns() - self._started_ns) / 1_000_000.0, 86_400_000.0)
        self._emitted = ObservationEnvelope(
            request_id=self.request_id,
            correlation_digest=self.correlation_digest,
            surface=self.surface,
            operation=self.operation,
            outcome=self._outcome or "ok",
            reason_code=self._reason_code or "completed",
            duration_ms=elapsed,
            store_generation=self.store_generation,
        )
        emit_observation(self._emitted)
        return self._emitted

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del exc, traceback
        try:
            if exc_type is not None and not self._outcome:
                self.set_outcome(
                    "error",
                    "interrupted"
                    if issubclass(exc_type, (KeyboardInterrupt, SystemExit))
                    else "internal_error",
                )
            self.emit()
        finally:
            if self._tokens is not None:
                request_token, digest_token, boundary_token = self._tokens
                _current_boundary.reset(boundary_token)
                _current_correlation_digest.reset(digest_token)
                _current_request_id.reset(request_token)
                self._tokens = None
        return False


def mark_current_observation(
    outcome: str,
    reason_code: str,
    *,
    store_generation: int | None = None,
    only_if_unset: bool = False,
) -> None:
    """Set the terminal result for the innermost active boundary, if any."""

    boundary = _current_boundary.get()
    if boundary is not None:
        boundary.set_outcome(
            outcome,
            reason_code,
            store_generation=store_generation,
            only_if_unset=only_if_unset,
        )


def correlate_current_observation(value: object) -> str:
    """Attach an opaque runtime correlation ID to the active boundary."""

    boundary = _current_boundary.get()
    return boundary.set_correlation_id(value) if boundary is not None else ""


def current_observation_context() -> tuple[str, str]:
    """Return the current request and correlation identities for nested work."""

    return _current_request_id.get(), _current_correlation_digest.get()


def emit_store_observation(
    *,
    operation: str,
    duration_ms: float,
    outcome: str,
    reason_code: str,
    store_generation: int | None = None,
) -> ObservationEnvelope:
    """Emit a bounded Store observation without ever accepting SQL or values."""

    request_id, correlation_digest = current_observation_context()
    envelope = ObservationEnvelope(
        request_id=request_id or new_request_id(),
        correlation_digest=correlation_digest,
        surface="store",
        operation=operation,
        outcome=outcome,
        reason_code=reason_code,
        duration_ms=duration_ms,
        store_generation=store_generation,
    )
    emit_observation(envelope)
    return envelope


__all__ = [
    "OBSERVATION_SCHEMA_VERSION",
    "SLOW_SQLITE_MILLISECONDS",
    "ObservationEnvelope",
    "RuntimeBoundary",
    "correlate_current_observation",
    "correlation_observation_digest",
    "current_observation_context",
    "emit_observation",
    "emit_store_observation",
    "mark_current_observation",
    "new_request_id",
    "normalize_request_id",
]
