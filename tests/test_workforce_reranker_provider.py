"""Focused transport regressions for bounded native workforce reranking."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.workforce import reranker_provider
from agency_runtime.core.workforce.reranker_provider import (
    MAX_RERANKER_DOCUMENTS,
    RerankerProviderResponse,
    invoke_reranker_provider,
    rerank_documents,
    validate_rerank_results,
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


def _provider(
    *,
    base_url: str = "https://api.jina.ai/v1",
    api_key: str = "jina-test-key",
) -> ProviderEntry:
    return ProviderEntry(
        name="jina-reranker",
        type="jina",
        model="jina-reranker-v3.5",
        base_url=base_url,
        api_key=api_key,
        timeout=5.0,
    )


def _payload(order: tuple[int, ...] = (1, 0)) -> dict[str, Any]:
    return {
        "model": "jina-reranker-v3.5",
        "results": [
            {"index": index, "relevance_score": 0.9 - ordinal * 0.1}
            for ordinal, index in enumerate(order)
        ],
    }


@pytest.mark.parametrize(
    "base_url",
    ["https://api.jina.ai", "https://api.jina.ai/v1", "https://api.jina.ai/v1/rerank"],
)
def test_ar289_jina_request_accepts_root_v1_or_exact_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    base_url: str,
) -> None:
    observed: dict[str, object] = {}

    def respond(request: Any, *, timeout: float) -> _Response:
        observed["url"] = request.full_url
        observed["method"] = request.method
        observed["authorization"] = request.get_header("Authorization")
        observed["payload"] = json.loads(request.data.decode("utf-8"))
        observed["timeout"] = timeout
        return _Response(_payload())

    monkeypatch.setattr(reranker_provider, "open_no_redirect", respond)

    response = invoke_reranker_provider(
        _provider(base_url=base_url),
        "find the best specialist",
        ("candidate zero", "candidate one"),
    )

    assert observed == {
        "url": "https://api.jina.ai/v1/rerank",
        "method": "POST",
        "authorization": "Bearer jina-test-key",
        "payload": {
            "documents": ["candidate zero", "candidate one"],
            "model": "jina-reranker-v3.5",
            "query": "find the best specialist",
            "return_documents": False,
            "top_n": 2,
        },
        "timeout": 5.0,
    }
    assert tuple(response.ranked_indices) == (1, 0)
    assert tuple(response.scores) == pytest.approx((0.9, 0.8))
    assert response.actual_model == "jina-reranker-v3.5"


@pytest.mark.parametrize(
    ("provider", "message"),
    [
        (_provider(api_key=""), "keyless"),
        (_provider(base_url="http://api.jina.ai/v1"), "unsafe"),
    ],
)
def test_ar289_jina_remote_transport_requires_safe_credentials(
    monkeypatch: pytest.MonkeyPatch,
    provider: ProviderEntry,
    message: str,
) -> None:
    monkeypatch.setattr(
        reranker_provider,
        "open_no_redirect",
        lambda *_args, **_kwargs: pytest.fail("unsafe reranker request reached transport"),
    )

    with pytest.raises(ValueError, match=message):
        invoke_reranker_provider(provider, "query", ("document",))


def test_ar289_keyless_loopback_native_reranker_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _provider(base_url="http://127.0.0.1:9999/v1", api_key="")
    observed: dict[str, object] = {}

    def respond(request: Any, *, timeout: float) -> _Response:
        observed["authorization"] = request.get_header("Authorization")
        observed["timeout"] = timeout
        return _Response(
            {
                "model": "local-reranker-receipt",
                "results": [{"index": 0, "relevance_score": 0.5}],
            }
        )

    monkeypatch.setattr(reranker_provider, "open_no_redirect", respond)

    response = invoke_reranker_provider(provider, "query", ("document",))

    assert observed == {"authorization": None, "timeout": 5.0}
    assert response.actual_model == "local-reranker-receipt"


def test_ar289_jina_credential_resolves_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ProviderEntry(
        name="jina-reranker",
        type="jina",
        model="jina-reranker-v3.5",
        base_url="https://api.jina.ai/v1",
        api_key_env="JINA_TEST_KEY",
        timeout=5.0,
    )
    monkeypatch.setenv("JINA_TEST_KEY", "environment-only-key")
    observed: dict[str, object] = {}

    def respond(request: Any, *, timeout: float) -> _Response:
        observed["authorization"] = request.get_header("Authorization")
        observed["timeout"] = timeout
        return _Response(
            {
                "model": "jina-reranker-v3.5",
                "results": [{"index": 0, "relevance_score": 0.5}],
            }
        )

    monkeypatch.setattr(reranker_provider, "open_no_redirect", respond)

    invoke_reranker_provider(provider, "query", ("document",))

    assert observed == {
        "authorization": "Bearer environment-only-key",
        "timeout": 5.0,
    }


@pytest.mark.parametrize(
    ("indices", "scores", "message"),
    [
        ((0,), (0.9,), "count"),
        ((0, 0), (0.9, 0.8), "every document"),
        ((0, 2), (0.9, 0.8), "invalid document index"),
        ((0, 1), (0.8, 0.9), "descending"),
        ((0, 1), (0.9, float("nan")), "finite"),
        ((0, 1), (0.9, True), "numeric"),
    ],
)
def test_ar289_native_results_require_an_exact_finite_descending_permutation(
    indices: object,
    scores: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_rerank_results(indices, scores, expected_count=2)


def test_ar289_native_reranker_rejects_surplus_inputs_before_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reranker_provider,
        "open_no_redirect",
        lambda *_args, **_kwargs: pytest.fail("oversized reranker batch reached transport"),
    )

    with pytest.raises(ValueError, match="document count"):
        invoke_reranker_provider(
            _provider(),
            "query",
            tuple(f"document {index}" for index in range(MAX_RERANKER_DOCUMENTS + 1)),
        )


def test_ar289_injected_reranker_requires_actual_model_receipt() -> None:
    result = rerank_documents(
        "query",
        ("zero", "one"),
        invoker=lambda _query, _documents: RerankerProviderResponse(
            ranked_indices=(1, 0),
            scores=(0.9, 0.8),
            provider_name="jina-reranker",
            requested_model="jina-reranker-v3.5",
            actual_model="",
        ),
        provider_name="jina-reranker",
        requested_model="jina-reranker-v3.5",
    )

    assert result.ranked_indices == ()
    assert result.receipt.status == "failed"
    assert result.receipt.reason_code == "reranker_model_identity_missing"


def test_ar289_injected_reranker_rejects_non_text_model_identity() -> None:
    result = rerank_documents(
        "query",
        ("document",),
        invoker=lambda _query, _documents: {
            "ranked_indices": (0,),
            "scores": (0.9,),
            "actual_model": 123,
        },
        provider_name="jina-reranker",
        requested_model="jina-reranker-v3.5",
    )

    assert result.ranked_indices == ()
    assert result.receipt.status == "failed"
    assert result.receipt.reason_code == "reranker_response_invalid"


def test_ar289_injected_reranker_failure_is_content_free() -> None:
    secret = "jina-secret-that-must-not-be-recorded"

    def fail(_query: str, _documents: tuple[str, ...]) -> RerankerProviderResponse:
        raise RuntimeError(f"provider rejected {secret}")

    result = rerank_documents(
        "private query",
        ("private document",),
        invoker=fail,
        provider_name="jina-reranker",
        requested_model="jina-reranker-v3.5",
    )

    assert result.ranked_indices == ()
    assert result.receipt.status == "failed"
    assert result.receipt.reason_code == "reranker_provider_failed"
    assert secret not in repr(result)
    assert "private query" not in repr(result)
    assert "private document" not in repr(result)
