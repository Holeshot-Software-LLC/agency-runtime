"""Bounded learned-embedding seam for workforce candidate recall.

Recall never selects a transport implicitly. Production callers may bind the
explicit HTTP transport in this module to one configured provider, while tests
and offline evaluation can inject the same narrow callable without credentials
or network access.
"""

from __future__ import annotations

import json
import math
import time
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from typing import TypeAlias

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import (
    MAX_INFERENCE_EMBEDDING_DIMENSIONS,
    ProviderEntry,
    _is_loopback_http_url,
    is_safe_credential_url,
)
from agency_runtime.core.http_safety import open_no_redirect

MAX_EMBEDDING_INPUTS = 10_016
MAX_EMBEDDING_DIMENSIONS = MAX_INFERENCE_EMBEDDING_DIMENSIONS
MAX_EMBEDDING_VECTOR_VALUES = 1_000_000
MAX_EMBEDDING_TEXT_BYTES = 16 * 1_024
MAX_EMBEDDING_BATCH_BYTES = 32 * 1_024 * 1_024
MAX_EMBEDDING_RESPONSE_BYTES = 64 * 1_024 * 1_024
MAX_EMBEDDING_RESPONSE_NODES = 1_000_000
MAX_EMBEDDING_IDENTITY_CHARS = 512
MAX_EMBEDDING_LATENCY_MS = 86_400_000
MAX_EMBEDDING_TIMEOUT_SECONDS = 120.0
EMBEDDING_NORMALIZATION_IDENTITY = "l2-unit-v1"

_OPENAI_COMPATIBLE_TYPES = frozenset({"openai", "openai-compatible", "litellm"})
_EMBEDDING_RESPONSE_FIXED_NODE_RESERVE = 256
_EMBEDDING_RESPONSE_ROW_NODE_OVERHEAD = 4


@dataclass(frozen=True, slots=True)
class EmbeddingProviderResponse:
    """Untrusted embedding response returned by an injected provider invoker."""

    vectors: Sequence[Sequence[float]]
    provider_name: str = ""
    requested_model: str = ""
    actual_model: str = ""
    latency_ms: int = 0


@dataclass(frozen=True, slots=True)
class EmbeddingReceipt:
    """Content-free evidence for one bounded embedding attempt."""

    status: str
    reason_code: str
    provider_name: str
    requested_model: str
    actual_model: str
    input_count: int
    dimensions: int
    latency_ms: int


@dataclass(frozen=True, slots=True)
class EmbeddingBatch:
    """Validated unit-normalized vectors plus their provider receipt."""

    vectors: tuple[tuple[float, ...], ...]
    receipt: EmbeddingReceipt


EmbeddingInvoker: TypeAlias = Callable[
    [tuple[str, ...]],
    EmbeddingProviderResponse | Mapping[str, object],
]


def _identity(value: object) -> str:
    text = " ".join(str(value or "").split())
    text = "".join(character for character in text if character.isprintable())
    return text[:MAX_EMBEDDING_IDENTITY_CHARS]


def _configured_text(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"embedding provider {label} must be text")
    text = " ".join(value.split())
    if (
        not text
        or len(text) > MAX_EMBEDDING_IDENTITY_CHARS
        or any(not character.isprintable() for character in text)
    ):
        raise ValueError(f"embedding provider {label} is empty or invalid")
    return text


def _latency(value: object, *, measured: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return measured
    return min(MAX_EMBEDDING_LATENCY_MS, max(0, value))


def _receipt(
    *,
    status: str,
    reason_code: str,
    provider_name: str,
    requested_model: str,
    actual_model: str = "",
    input_count: int,
    dimensions: int = 0,
    latency_ms: int = 0,
) -> EmbeddingReceipt:
    return EmbeddingReceipt(
        status=status,
        reason_code=reason_code,
        provider_name=_identity(provider_name),
        requested_model=_identity(requested_model),
        actual_model=_identity(actual_model),
        input_count=input_count,
        dimensions=dimensions,
        latency_ms=min(MAX_EMBEDDING_LATENCY_MS, max(0, latency_ms)),
    )


def validate_and_normalize_vectors(
    vectors: object,
    *,
    expected_count: int,
    maximum_dimensions: int = MAX_EMBEDDING_DIMENSIONS,
) -> tuple[tuple[float, ...], ...]:
    """Validate an exact rectangular finite matrix and unit-normalize its rows.

    Booleans, non-finite values, zero vectors, mixed dimensions, surplus rows,
    and missing rows are rejected. No provider score is trusted as calibrated
    evidence; callers compare only locally normalized vectors.
    """

    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or expected_count < 0
        or expected_count > MAX_EMBEDDING_INPUTS
    ):
        raise ValueError("expected embedding count is outside the supported range")
    if (
        isinstance(maximum_dimensions, bool)
        or not isinstance(maximum_dimensions, int)
        or not 1 <= maximum_dimensions <= MAX_EMBEDDING_DIMENSIONS
    ):
        raise ValueError("maximum embedding dimensions is outside the supported range")
    if (
        not isinstance(vectors, Sequence)
        or isinstance(vectors, (str, bytes, bytearray))
        or len(vectors) != expected_count
    ):
        raise ValueError("embedding response count does not match its request")
    if expected_count == 0:
        return ()

    dimensions: int | None = None
    normalized: list[tuple[float, ...]] = []
    for raw_vector in vectors:
        if not isinstance(raw_vector, Sequence) or isinstance(raw_vector, (str, bytes, bytearray)):
            raise ValueError("embedding vector must be a numeric sequence")
        if dimensions is None:
            dimensions = len(raw_vector)
            if not 1 <= dimensions <= maximum_dimensions:
                raise ValueError("embedding dimensions are outside the supported range")
            if expected_count * dimensions > MAX_EMBEDDING_VECTOR_VALUES:
                raise ValueError("embedding matrix exceeds its scalar-count bound")
        elif len(raw_vector) != dimensions:
            raise ValueError("embedding vectors must have identical dimensions")

        row: list[float] = []
        for raw_value in raw_vector:
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError("embedding vectors must contain only numeric values")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError("embedding vectors must contain only finite values")
            row.append(value)
        magnitude = math.sqrt(math.fsum(value * value for value in row))
        if not math.isfinite(magnitude) or magnitude <= 0.0:
            raise ValueError("embedding vectors must have non-zero finite magnitude")
        normalized.append(tuple(value / magnitude for value in row))
    return tuple(normalized)


def _response_fields(
    value: EmbeddingProviderResponse | Mapping[str, object],
) -> tuple[object, str, str, str, object]:
    if isinstance(value, EmbeddingProviderResponse):
        return (
            value.vectors,
            value.provider_name,
            value.requested_model,
            value.actual_model,
            value.latency_ms,
        )
    if isinstance(value, Mapping):
        return (
            value.get("vectors"),
            _identity(value.get("provider_name")),
            _identity(value.get("requested_model")),
            _identity(value.get("actual_model")),
            value.get("latency_ms"),
        )
    raise ValueError("embedding invoker returned an unsupported response")


def _bounded_inputs(texts: Sequence[str]) -> tuple[str, ...]:
    if isinstance(texts, (str, bytes, bytearray)) or len(texts) > MAX_EMBEDDING_INPUTS:
        raise ValueError("embedding input count is outside the supported range")
    result: list[str] = []
    total_bytes = 0
    for raw_text in texts:
        if not isinstance(raw_text, str):
            raise TypeError("embedding inputs must be text")
        text = " ".join(raw_text.split())
        encoded = text.encode("utf-8")
        if not text or len(encoded) > MAX_EMBEDDING_TEXT_BYTES:
            raise ValueError("embedding input text is empty or exceeds its size bound")
        total_bytes += len(encoded)
        if total_bytes > MAX_EMBEDDING_BATCH_BYTES:
            raise ValueError("embedding input batch exceeds its size bound")
        result.append(text)
    return tuple(result)


def bound_embedding_inputs(texts: Sequence[str]) -> tuple[str, ...]:
    """Normalize and validate one complete logical embedding input set.

    Higher-level callers may divide this already-bounded set into multiple
    scalar-safe provider requests. Validating the logical set first prevents a
    later chunk from discovering an input-count or byte-bound failure after an
    earlier provider call has already occurred.
    """

    return _bounded_inputs(texts)


def embedding_batch_input_limit(dimensions: int) -> int:
    """Return the row limit satisfying both scalar and response-node bounds."""

    if (
        isinstance(dimensions, bool)
        or not isinstance(dimensions, int)
        or not 1 <= dimensions <= MAX_EMBEDDING_DIMENSIONS
    ):
        raise ValueError("embedding dimensions are outside the supported range")
    scalar_limit = MAX_EMBEDDING_VECTOR_VALUES // dimensions
    response_node_limit = (
        MAX_EMBEDDING_RESPONSE_NODES - _EMBEDDING_RESPONSE_FIXED_NODE_RESERVE
    ) // (dimensions + _EMBEDDING_RESPONSE_ROW_NODE_OVERHEAD)
    return max(1, min(MAX_EMBEDDING_INPUTS, scalar_limit, response_node_limit))


def _join_api_path(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if base.casefold().endswith("/v1") and normalized_path.casefold().startswith("/v1/"):
        normalized_path = normalized_path[3:]
    return f"{base}{normalized_path}"


def _timeout(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or not 0.0 < float(value) <= MAX_EMBEDDING_TIMEOUT_SECONDS
    ):
        raise ValueError("embedding provider timeout is outside the supported range")
    return float(value)


def _configured_dimensions(value: object, *, input_count: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= MAX_EMBEDDING_DIMENSIONS
    ):
        raise ValueError("embedding provider dimensions are outside the supported range")
    if value and input_count * value > MAX_EMBEDDING_VECTOR_VALUES:
        raise ValueError("embedding matrix exceeds its scalar-count bound")
    return value


def _provider_request(
    provider: ProviderEntry,
    texts: tuple[str, ...],
) -> tuple[urllib.request.Request, float, bool, int]:
    if not isinstance(provider, ProviderEntry):
        raise TypeError("embedding provider must be a configured ProviderEntry")
    provider_type = _configured_text(provider.type, label="type").casefold()
    if provider_type in {"anthropic", "cli"}:
        raise ValueError("embedding transport does not support CLI or Anthropic providers")
    ollama_mode = provider.ollama_mode or provider_type == "ollama"
    if not ollama_mode and provider_type not in _OPENAI_COMPATIBLE_TYPES:
        raise ValueError("embedding provider type is unsupported")
    model = _configured_text(provider.model, label="model")
    base_url = _configured_text(provider.base_url, label="base URL")
    dimensions = _configured_dimensions(provider.dimensions, input_count=len(texts))

    api_key = provider.resolve_api_key()
    if (
        not isinstance(api_key, str)
        or len(api_key) > 16_384
        or any(character.isspace() or not character.isprintable() for character in api_key)
    ):
        raise ValueError("embedding provider credential is invalid")
    loopback = _is_loopback_http_url(base_url)
    credential_safe = is_safe_credential_url(base_url)
    if ollama_mode:
        if not (loopback or (credential_safe and base_url.casefold().startswith("https://"))):
            raise ValueError("Ollama embedding endpoint is not transport-safe")
    elif api_key:
        if not credential_safe:
            raise ValueError("embedding endpoint or credential configuration is unsafe")
    elif not loopback:
        raise ValueError("keyless embedding endpoints must be loopback-local")

    if ollama_mode:
        payload = {"model": model, "input": list(texts)}
        path = "/api/embed"
    else:
        payload = {
            "encoding_format": "float",
            "input": list(texts),
            "model": model,
        }
        path = "/v1/embeddings"
    if dimensions:
        payload["dimensions"] = dimensions
    body = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(body) > MAX_EMBEDDING_BATCH_BYTES + (1 * 1_024 * 1_024):
        raise ValueError("embedding request exceeds its serialized size bound")
    headers = {"Content-Type": "application/json"}
    if api_key and not ollama_mode:
        headers["Authorization"] = f"Bearer {api_key}"
    return (
        urllib.request.Request(
            _join_api_path(base_url, path),
            data=body,
            headers=headers,
            method="POST",
        ),
        _timeout(provider.timeout),
        ollama_mode,
        dimensions,
    )


def _response_vectors(
    value: object,
    *,
    expected_count: int,
    ollama_mode: bool,
) -> tuple[object, str]:
    if not isinstance(value, Mapping):
        raise ValueError("embedding provider returned a non-object response")
    actual_model = _identity(value.get("model"))
    if ollama_mode:
        vectors = value.get("embeddings")
        return vectors, actual_model

    rows = value.get("data")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes, bytearray))
        or len(rows) != expected_count
    ):
        raise ValueError("embedding response count does not match its request")
    vectors: list[object] = []
    for ordinal, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("embedding response row must be an object")
        index = row.get("index")
        if isinstance(index, bool) or not isinstance(index, int) or index != ordinal:
            raise ValueError("embedding response rows are not in request order")
        vectors.append(row.get("embedding"))
    return vectors, actual_model


def invoke_embedding_provider(
    provider: ProviderEntry,
    texts: Sequence[str],
) -> EmbeddingProviderResponse:
    """Invoke one explicit HTTP embedding provider with a bounded exact batch.

    Supported transports are OpenAI-compatible/LiteLLM ``/v1/embeddings`` and
    Ollama ``/api/embed``. This function is never called by recall unless a
    caller deliberately wraps and injects it as an :class:`EmbeddingInvoker`.
    """

    bounded = bound_embedding_inputs(texts)
    if not bounded:
        raise ValueError("embedding provider input batch must not be empty")
    request, timeout, ollama_mode, dimensions = _provider_request(provider, bounded)
    started = time.monotonic()
    with open_no_redirect(request, timeout=timeout) as response:
        raw = response.read(MAX_EMBEDDING_RESPONSE_BYTES + 1)
    if len(raw) > MAX_EMBEDDING_RESPONSE_BYTES:
        raise ValueError("embedding provider response exceeds its size bound")
    decoded = safe_load_bounded_json(
        raw,
        maximum_bytes=MAX_EMBEDDING_RESPONSE_BYTES,
        maximum_depth=16,
        maximum_nodes=MAX_EMBEDDING_RESPONSE_NODES,
    )
    raw_vectors, actual_model = _response_vectors(
        decoded,
        expected_count=len(bounded),
        ollama_mode=ollama_mode,
    )
    vectors = validate_and_normalize_vectors(
        raw_vectors,
        expected_count=len(bounded),
        maximum_dimensions=dimensions or MAX_EMBEDDING_DIMENSIONS,
    )
    if dimensions and len(vectors[0]) != dimensions:
        raise ValueError("embedding response dimensions do not match the configured request")
    return EmbeddingProviderResponse(
        vectors=vectors,
        provider_name=_identity(provider.name),
        requested_model=_identity(provider.model),
        actual_model=actual_model,
        latency_ms=min(
            MAX_EMBEDDING_LATENCY_MS,
            max(0, int((time.monotonic() - started) * 1_000)),
        ),
    )


def embed_texts(
    texts: Sequence[str],
    *,
    invoker: EmbeddingInvoker | None = None,
    provider_name: str = "",
    requested_model: str = "",
    expected_dimensions: int = 0,
) -> EmbeddingBatch:
    """Invoke one injected embedding provider and validate its whole response.

    Without an injected invoker this function performs no external action and
    returns a typed skip receipt. Provider exceptions and malformed responses
    likewise produce an empty failed batch so candidate recall can fall back to
    its unchanged typed baseline.
    """

    bounded = bound_embedding_inputs(texts)
    configured_dimensions = _configured_dimensions(
        expected_dimensions,
        input_count=len(bounded),
    )
    if not bounded:
        return EmbeddingBatch(
            (),
            _receipt(
                status="skipped",
                reason_code="embedding_inputs_empty",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=0,
            ),
        )
    if invoker is None:
        return EmbeddingBatch(
            (),
            _receipt(
                status="skipped",
                reason_code="embedding_invoker_unavailable",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=len(bounded),
            ),
        )

    started = time.monotonic()
    try:
        raw_response = invoker(bounded)
    except Exception:
        measured = min(
            MAX_EMBEDDING_LATENCY_MS,
            max(0, int((time.monotonic() - started) * 1_000)),
        )
        return EmbeddingBatch(
            (),
            _receipt(
                status="failed",
                reason_code="embedding_provider_failed",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=len(bounded),
                latency_ms=measured,
            ),
        )
    try:
        raw_vectors, response_provider, response_requested, actual_model, raw_latency = (
            _response_fields(raw_response)
        )
        expected_provider = _identity(provider_name)
        expected_model = _identity(requested_model)
        if (
            response_provider
            and expected_provider
            and response_provider.casefold() != expected_provider.casefold()
        ):
            raise ValueError("embedding response provider does not match its request")
        if (
            response_requested
            and expected_model
            and response_requested.casefold() != expected_model.casefold()
        ):
            raise ValueError("embedding response model request does not match")
        vectors = validate_and_normalize_vectors(
            raw_vectors,
            expected_count=len(bounded),
            maximum_dimensions=configured_dimensions or MAX_EMBEDDING_DIMENSIONS,
        )
        if configured_dimensions and len(vectors[0]) != configured_dimensions:
            raise ValueError("embedding response dimensions do not match the configured request")
    except Exception:
        measured = min(
            MAX_EMBEDDING_LATENCY_MS,
            max(0, int((time.monotonic() - started) * 1_000)),
        )
        return EmbeddingBatch(
            (),
            _receipt(
                status="failed",
                reason_code="embedding_response_invalid",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=len(bounded),
                latency_ms=measured,
            ),
        )

    measured = min(
        MAX_EMBEDDING_LATENCY_MS,
        max(0, int((time.monotonic() - started) * 1_000)),
    )
    latency_ms = _latency(raw_latency, measured=measured)
    dimensions = len(vectors[0]) if vectors else 0
    return EmbeddingBatch(
        vectors,
        _receipt(
            status="applied",
            reason_code="",
            provider_name=response_provider or provider_name,
            requested_model=response_requested or requested_model,
            actual_model=actual_model,
            input_count=len(bounded),
            dimensions=dimensions,
            latency_ms=latency_ms,
        ),
    )


__all__ = [
    "EMBEDDING_NORMALIZATION_IDENTITY",
    "MAX_EMBEDDING_BATCH_BYTES",
    "MAX_EMBEDDING_DIMENSIONS",
    "MAX_EMBEDDING_INPUTS",
    "MAX_EMBEDDING_LATENCY_MS",
    "MAX_EMBEDDING_RESPONSE_BYTES",
    "MAX_EMBEDDING_RESPONSE_NODES",
    "MAX_EMBEDDING_TEXT_BYTES",
    "MAX_EMBEDDING_VECTOR_VALUES",
    "EmbeddingBatch",
    "EmbeddingInvoker",
    "EmbeddingProviderResponse",
    "EmbeddingReceipt",
    "bound_embedding_inputs",
    "embed_texts",
    "embedding_batch_input_limit",
    "invoke_embedding_provider",
    "validate_and_normalize_vectors",
]
