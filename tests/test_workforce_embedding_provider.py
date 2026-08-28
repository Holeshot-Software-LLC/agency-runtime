"""Focused transport regressions for bounded workforce embeddings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.workforce import embedding_provider
from agency_runtime.core.workforce.embedding_provider import (
    EmbeddingProviderResponse,
    embed_texts,
    embedding_batch_input_limit,
    invoke_embedding_provider,
)


class _Response:
    def __init__(self, payload: Mapping[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _size: int = -1) -> bytes:
        return self._body


def _provider(*, provider_type: str, dimensions: int) -> ProviderEntry:
    return ProviderEntry(
        name=f"local-{provider_type}",
        type=provider_type,
        model="qwen3-embedding:latest",
        base_url="http://127.0.0.1:11434",
        ollama_mode=provider_type == "ollama",
        timeout=5.0,
        dimensions=dimensions,
    )


def _response_payload(
    provider_type: str,
    vectors: list[list[float]],
) -> dict[str, Any]:
    if provider_type == "ollama":
        return {
            "model": "qwen3-embedding:latest",
            "embeddings": vectors,
        }
    return {
        "model": "qwen3-embedding:latest",
        "data": [{"index": index, "embedding": vector} for index, vector in enumerate(vectors)],
    }


@pytest.mark.parametrize(
    "provider_type",
    ["ollama", "openai-compatible", "litellm"],
)
@pytest.mark.parametrize(
    ("dimensions", "expected_in_payload"),
    [(1_024, True), (0, False)],
    ids=("configured", "default"),
)
def test_ar286_embedding_payload_forwards_only_configured_dimensions(
    monkeypatch: pytest.MonkeyPatch,
    provider_type: str,
    dimensions: int,
    expected_in_payload: bool,
) -> None:
    provider = _provider(provider_type=provider_type, dimensions=dimensions)
    observed: dict[str, object] = {}
    response_dimensions = dimensions or 3
    vector = [1.0] + [0.0] * (response_dimensions - 1)

    def respond(request: Any, *, timeout: float) -> _Response:
        observed["payload"] = json.loads(request.data.decode("utf-8"))
        observed["timeout"] = timeout
        return _Response(_response_payload(provider_type, [vector]))

    monkeypatch.setattr(embedding_provider, "open_no_redirect", respond)

    response = invoke_embedding_provider(provider, ("bounded input",))

    payload = observed["payload"]
    assert isinstance(payload, dict)
    if expected_in_payload:
        assert payload["dimensions"] == dimensions
    else:
        assert "dimensions" not in payload
    assert observed["timeout"] == pytest.approx(5.0)
    assert len(response.vectors[0]) == response_dimensions


def test_ar286_embedding_response_must_match_configured_dimensions_exactly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(provider_type="ollama", dimensions=2)

    monkeypatch.setattr(
        embedding_provider,
        "open_no_redirect",
        lambda *_args, **_kwargs: _Response(_response_payload("ollama", [[1.0]])),
    )

    with pytest.raises(ValueError, match="dimensions"):
        invoke_embedding_provider(provider, ("bounded input",))


def test_ar286_known_embedding_matrix_overflow_rejects_before_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(provider_type="ollama", dimensions=1_024)

    def unexpected_transport(*_args: object, **_kwargs: object) -> None:
        pytest.fail("embedding transport was reached after a known matrix overflow")

    monkeypatch.setattr(embedding_provider, "open_no_redirect", unexpected_transport)

    with pytest.raises(ValueError, match="scalar-count"):
        invoke_embedding_provider(
            provider,
            tuple(f"bounded input {index}" for index in range(977)),
        )


def test_ar286_embedding_receipt_keeps_observed_dimensions() -> None:
    result = embed_texts(
        ("bounded input",),
        invoker=lambda _texts: EmbeddingProviderResponse(
            vectors=((1.0, 0.0, 0.0),),
            provider_name="local-embedding",
            requested_model="embedding-model",
            actual_model="embedding-model-receipt",
        ),
        provider_name="local-embedding",
        requested_model="embedding-model",
    )

    assert result.receipt.status == "applied"
    assert result.receipt.dimensions == 3
    assert result.receipt.actual_model == "embedding-model-receipt"


def test_ar303_embedding_batch_limit_reserves_response_structure_nodes() -> None:
    assert embedding_batch_input_limit(4_096) == 243
    assert embedding_provider.MAX_EMBEDDING_VECTOR_VALUES >= 243 * 4_096
    assert (
        243 * (4_096 + embedding_provider._EMBEDDING_RESPONSE_ROW_NODE_OVERHEAD)
        + embedding_provider._EMBEDDING_RESPONSE_FIXED_NODE_RESERVE
        <= embedding_provider.MAX_EMBEDDING_RESPONSE_NODES
    )
