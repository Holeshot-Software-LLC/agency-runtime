"""Bounded native reranker transport for additive workforce recall.

The structured text reranker remains available for local models, LiteLLM,
direct API providers, and authenticated CLI subscriptions. This module owns
only explicit native reranker profiles, beginning with Jina's ``/v1/rerank``
contract. Provider scores are validated as transport data and are never
treated as calibrated staffing evidence.
"""

from __future__ import annotations

import json
import math
import time
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from numbers import Real
from typing import TypeAlias

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import (
    ProviderEntry,
    _is_loopback_http_url,
    is_safe_credential_url,
)
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.provider_deadline import remaining_provider_timeout
from agency_runtime.core.structured_provider import _read_http_response

MAX_RERANKER_DOCUMENTS = 64
MAX_RERANKER_QUERY_BYTES = 256 * 1_024
MAX_RERANKER_DOCUMENT_BYTES = 64 * 1_024
MAX_RERANKER_BATCH_BYTES = 4 * 1_024 * 1_024
MAX_RERANKER_RESPONSE_BYTES = 4 * 1_024 * 1_024
MAX_RERANKER_IDENTITY_CHARS = 512
MAX_RERANKER_LATENCY_MS = 86_400_000
MAX_RERANKER_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class RerankerProviderResponse:
    """Untrusted native reranker response from an injected provider invoker."""

    ranked_indices: Sequence[int]
    scores: Sequence[float]
    provider_name: str = ""
    requested_model: str = ""
    actual_model: str = ""
    latency_ms: int = 0


@dataclass(frozen=True, slots=True)
class RerankerReceipt:
    """Content-free evidence for one bounded native reranker attempt."""

    status: str
    reason_code: str
    provider_name: str
    requested_model: str
    actual_model: str
    input_count: int
    latency_ms: int


@dataclass(frozen=True, slots=True)
class RerankerBatch:
    """An exact provider-ordered permutation plus its content-free receipt."""

    ranked_indices: tuple[int, ...]
    receipt: RerankerReceipt


RerankerInvoker: TypeAlias = Callable[
    [str, tuple[str, ...]],
    RerankerProviderResponse | Mapping[str, object],
]


def _identity(value: object) -> str:
    text = " ".join(str(value or "").split())
    text = "".join(character for character in text if character.isprintable())
    return text[:MAX_RERANKER_IDENTITY_CHARS]


def _configured_text(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"reranker provider {label} must be text")
    text = " ".join(value.split())
    if (
        not text
        or len(text) > MAX_RERANKER_IDENTITY_CHARS
        or any(not character.isprintable() for character in text)
    ):
        raise ValueError(f"reranker provider {label} is empty or invalid")
    return text


def _response_identity(value: object, *, label: str) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise ValueError(f"reranker response {label} must be text")
    identity = _identity(value)
    if not identity or any(not character.isprintable() for character in value):
        raise ValueError(f"reranker response {label} is invalid")
    return identity


def _latency(value: object, *, measured: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return measured
    return min(MAX_RERANKER_LATENCY_MS, max(0, value))


def _receipt(
    *,
    status: str,
    reason_code: str,
    provider_name: str,
    requested_model: str,
    actual_model: str = "",
    input_count: int,
    latency_ms: int = 0,
) -> RerankerReceipt:
    return RerankerReceipt(
        status=status,
        reason_code=reason_code,
        provider_name=_identity(provider_name),
        requested_model=_identity(requested_model),
        actual_model=_identity(actual_model),
        input_count=input_count,
        latency_ms=min(MAX_RERANKER_LATENCY_MS, max(0, latency_ms)),
    )


def _bounded_text(value: object, *, label: str, maximum_bytes: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"reranker {label} must be text")
    text = value.strip()
    encoded = text.encode("utf-8")
    if not text or any(ord(character) < 32 for character in text) or len(encoded) > maximum_bytes:
        raise ValueError(f"reranker {label} is empty or exceeds its size bound")
    return text


def _bounded_inputs(query: object, documents: Sequence[str]) -> tuple[str, tuple[str, ...]]:
    bounded_query = _bounded_text(
        query,
        label="query",
        maximum_bytes=MAX_RERANKER_QUERY_BYTES,
    )
    if (
        isinstance(documents, (str, bytes, bytearray))
        or not 1 <= len(documents) <= MAX_RERANKER_DOCUMENTS
    ):
        raise ValueError("reranker document count is outside the supported range")
    bounded_documents: list[str] = []
    total_bytes = len(bounded_query.encode("utf-8"))
    for raw_document in documents:
        document = _bounded_text(
            raw_document,
            label="document",
            maximum_bytes=MAX_RERANKER_DOCUMENT_BYTES,
        )
        total_bytes += len(document.encode("utf-8"))
        if total_bytes > MAX_RERANKER_BATCH_BYTES:
            raise ValueError("reranker input batch exceeds its size bound")
        bounded_documents.append(document)
    return bounded_query, tuple(bounded_documents)


def validate_rerank_results(
    ranked_indices: object,
    scores: object,
    *,
    expected_count: int,
) -> tuple[int, ...]:
    """Require one complete permutation with finite descending scores."""

    if (
        isinstance(expected_count, bool)
        or not isinstance(expected_count, int)
        or not 1 <= expected_count <= MAX_RERANKER_DOCUMENTS
    ):
        raise ValueError("expected reranker count is outside the supported range")
    if (
        not isinstance(ranked_indices, Sequence)
        or isinstance(ranked_indices, (str, bytes, bytearray))
        or len(ranked_indices) != expected_count
    ):
        raise ValueError("reranker response count does not match its request")
    if (
        not isinstance(scores, Sequence)
        or isinstance(scores, (str, bytes, bytearray))
        or len(scores) != expected_count
    ):
        raise ValueError("reranker score count does not match its request")

    order: list[int] = []
    normalized_scores: list[float] = []
    for raw_index, raw_score in zip(ranked_indices, scores, strict=True):
        if (
            isinstance(raw_index, bool)
            or not isinstance(raw_index, int)
            or not 0 <= raw_index < expected_count
        ):
            raise ValueError("reranker response contains an invalid document index")
        if isinstance(raw_score, bool) or not isinstance(raw_score, Real):
            raise ValueError("reranker response scores must be numeric")
        score = float(raw_score)
        if not math.isfinite(score):
            raise ValueError("reranker response scores must be finite")
        order.append(raw_index)
        normalized_scores.append(score)
    if len(set(order)) != expected_count:
        raise ValueError("reranker must return every document exactly once")
    if any(later > earlier for earlier, later in pairwise(normalized_scores)):
        raise ValueError("reranker response scores are not in descending order")
    return tuple(order)


def _join_api_path(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if base.casefold().endswith(normalized_path.casefold()):
        return base
    if base.casefold().endswith("/v1") and normalized_path.casefold().startswith("/v1/"):
        normalized_path = normalized_path[3:]
    return f"{base}{normalized_path}"


def _timeout(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(float(value))
        or not 0.0 < float(value) <= MAX_RERANKER_TIMEOUT_SECONDS
    ):
        raise ValueError("reranker provider timeout is outside the supported range")
    return float(value)


def _provider_request(
    provider: ProviderEntry,
    query: str,
    documents: tuple[str, ...],
) -> tuple[urllib.request.Request, float]:
    if not isinstance(provider, ProviderEntry):
        raise TypeError("reranker provider must be a configured ProviderEntry")
    provider_type = _configured_text(provider.type, label="type").casefold()
    if provider_type != "jina":
        raise ValueError("native reranker provider type is unsupported")
    model = _configured_text(provider.model, label="model")
    base_url = _configured_text(provider.base_url, label="base URL")
    api_key = provider.resolve_api_key()
    if (
        not isinstance(api_key, str)
        or len(api_key) > 16_384
        or any(character.isspace() or not character.isprintable() for character in api_key)
    ):
        raise ValueError("reranker provider credential is invalid")
    loopback = _is_loopback_http_url(base_url)
    if api_key:
        if not is_safe_credential_url(base_url):
            raise ValueError("reranker endpoint or credential configuration is unsafe")
    elif not loopback:
        raise ValueError("keyless reranker endpoints must be loopback-local")

    body = json.dumps(
        {
            "documents": list(documents),
            "model": model,
            "query": query,
            "return_documents": False,
            "top_n": len(documents),
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(body) > MAX_RERANKER_BATCH_BYTES + (1 * 1_024 * 1_024):
        raise ValueError("reranker request exceeds its serialized size bound")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return (
        urllib.request.Request(
            _join_api_path(base_url, "/v1/rerank"),
            data=body,
            headers=headers,
            method="POST",
        ),
        _timeout(provider.timeout),
    )


def _response_ranking(
    value: object,
    *,
    expected_count: int,
) -> tuple[tuple[int, ...], tuple[float, ...], str]:
    if not isinstance(value, Mapping):
        raise ValueError("reranker provider returned a non-object response")
    rows = value.get("results")
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes, bytearray))
        or len(rows) != expected_count
    ):
        raise ValueError("reranker response count does not match its request")
    indices: list[object] = []
    scores: list[object] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("reranker response row must be an object")
        indices.append(row.get("index"))
        scores.append(row.get("relevance_score"))
    validated = validate_rerank_results(indices, scores, expected_count=expected_count)
    return (
        validated,
        tuple(float(score) for score in scores),
        _response_identity(value.get("model"), label="model"),
    )


def invoke_reranker_provider(
    provider: ProviderEntry,
    query: str,
    documents: Sequence[str],
) -> RerankerProviderResponse:
    """Invoke one explicit Jina-compatible native reranker endpoint."""

    bounded_query, bounded_documents = _bounded_inputs(query, documents)
    request, timeout = _provider_request(provider, bounded_query, bounded_documents)
    timeout = remaining_provider_timeout(timeout)
    if timeout <= 0:
        raise TimeoutError("provider_deadline_exhausted")
    started = time.monotonic()
    with open_no_redirect(request, timeout=timeout) as response:
        raw = _read_http_response(
            response, deadline=started + timeout, maximum_bytes=MAX_RERANKER_RESPONSE_BYTES
        )
    if raw is None:
        raise ValueError("reranker provider response exceeds its size or time bound")
    decoded = safe_load_bounded_json(
        raw,
        maximum_bytes=MAX_RERANKER_RESPONSE_BYTES,
        maximum_depth=16,
        maximum_nodes=100_000,
    )
    ranked_indices, scores, actual_model = _response_ranking(
        decoded,
        expected_count=len(bounded_documents),
    )
    return RerankerProviderResponse(
        ranked_indices=ranked_indices,
        scores=scores,
        provider_name=_identity(provider.name),
        requested_model=_identity(provider.model),
        actual_model=actual_model,
        latency_ms=min(
            MAX_RERANKER_LATENCY_MS,
            max(0, int((time.monotonic() - started) * 1_000)),
        ),
    )


def _response_fields(
    value: RerankerProviderResponse | Mapping[str, object],
) -> tuple[object, object, str, str, str, object]:
    if isinstance(value, RerankerProviderResponse):
        return (
            value.ranked_indices,
            value.scores,
            _response_identity(value.provider_name, label="provider name"),
            _response_identity(value.requested_model, label="requested model"),
            _response_identity(value.actual_model, label="actual model"),
            value.latency_ms,
        )
    if isinstance(value, Mapping):
        return (
            value.get("ranked_indices"),
            value.get("scores"),
            _response_identity(value.get("provider_name"), label="provider name"),
            _response_identity(value.get("requested_model"), label="requested model"),
            _response_identity(value.get("actual_model"), label="actual model"),
            value.get("latency_ms"),
        )
    raise ValueError("reranker invoker returned an unsupported response")


def rerank_documents(
    query: str,
    documents: Sequence[str],
    *,
    invoker: RerankerInvoker | None = None,
    provider_name: str = "",
    requested_model: str = "",
) -> RerankerBatch:
    """Invoke and validate one exact native reranker permutation.

    Provider failures and malformed results return a content-free failed batch,
    allowing additive recall to retain its unchanged typed-only baseline.
    """

    bounded_query, bounded_documents = _bounded_inputs(query, documents)
    if invoker is None:
        return RerankerBatch(
            (),
            _receipt(
                status="skipped",
                reason_code="reranker_invoker_unavailable",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=len(bounded_documents),
            ),
        )

    started = time.monotonic()
    try:
        raw_response = invoker(bounded_query, bounded_documents)
    except Exception:
        measured = min(
            MAX_RERANKER_LATENCY_MS,
            max(0, int((time.monotonic() - started) * 1_000)),
        )
        return RerankerBatch(
            (),
            _receipt(
                status="failed",
                reason_code="reranker_provider_failed",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=len(bounded_documents),
                latency_ms=measured,
            ),
        )

    measured = min(
        MAX_RERANKER_LATENCY_MS,
        max(0, int((time.monotonic() - started) * 1_000)),
    )
    try:
        (
            raw_indices,
            raw_scores,
            response_provider,
            response_requested,
            actual_model,
            raw_latency,
        ) = _response_fields(raw_response)
        expected_provider = _identity(provider_name)
        expected_model = _identity(requested_model)
        if (
            response_provider
            and expected_provider
            and response_provider.casefold() != expected_provider.casefold()
        ):
            raise ValueError("reranker response provider does not match its request")
        if (
            response_requested
            and expected_model
            and response_requested.casefold() != expected_model.casefold()
        ):
            raise ValueError("reranker response model request does not match")
        ranked_indices = validate_rerank_results(
            raw_indices,
            raw_scores,
            expected_count=len(bounded_documents),
        )
    except Exception:
        return RerankerBatch(
            (),
            _receipt(
                status="failed",
                reason_code="reranker_response_invalid",
                provider_name=provider_name,
                requested_model=requested_model,
                input_count=len(bounded_documents),
                latency_ms=measured,
            ),
        )
    if not actual_model:
        return RerankerBatch(
            (),
            _receipt(
                status="failed",
                reason_code="reranker_model_identity_missing",
                provider_name=response_provider or provider_name,
                requested_model=response_requested or requested_model,
                input_count=len(bounded_documents),
                latency_ms=_latency(raw_latency, measured=measured),
            ),
        )
    return RerankerBatch(
        ranked_indices,
        _receipt(
            status="applied",
            reason_code="",
            provider_name=response_provider or provider_name,
            requested_model=response_requested or requested_model,
            actual_model=actual_model,
            input_count=len(bounded_documents),
            latency_ms=_latency(raw_latency, measured=measured),
        ),
    )


__all__ = [
    "MAX_RERANKER_BATCH_BYTES",
    "MAX_RERANKER_DOCUMENTS",
    "MAX_RERANKER_DOCUMENT_BYTES",
    "MAX_RERANKER_QUERY_BYTES",
    "MAX_RERANKER_RESPONSE_BYTES",
    "RerankerBatch",
    "RerankerInvoker",
    "RerankerProviderResponse",
    "RerankerReceipt",
    "invoke_reranker_provider",
    "rerank_documents",
    "validate_rerank_results",
]
