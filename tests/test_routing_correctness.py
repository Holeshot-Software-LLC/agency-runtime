"""Focused correctness tests for routing reuse and provider failover."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import urllib.error

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
    SelectorConfig,
)
from agency_runtime.core.selector import judge as judge_module
from agency_runtime.core.selector import pipeline as pipeline_module
from agency_runtime.core.selector.cache import (
    cache_get,
    cache_key,
    cache_put,
    clear_cache,
    routing_fingerprint,
)
from agency_runtime.core.selector.judge import query_judge
from agency_runtime.core.selector.pipeline import route
from agency_runtime.core.selector.stickiness import (
    clear_session_routing,
    session_check,
    session_put,
)


CATALOG_A = [
    {
        "slug": "code-reviewer",
        "name": "Code Reviewer",
        "description": "Reviews authentication code and tests",
    }
]
CATALOG_B = [
    {
        "slug": "security-auditor",
        "name": "Security Auditor",
        "description": "Audits authentication security",
    }
]


class _Response:
    def __init__(self, selected_ids: list[str], confidence: object) -> None:
        content = json.dumps({
            "selected_ids": selected_ids,
            "confidence": confidence,
        })
        self._body = json.dumps({
            "choices": [{"message": {"content": content}}],
        }).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]


def _offline_config(*, providers: tuple[ProviderEntry, ...] = ()) -> AgencyConfig:
    return AgencyConfig(
        providers=providers,
        judge=JudgeConfig(model="", confidence_bypass_threshold=999.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )


def test_routing_fingerprint_covers_roster_config_and_policy() -> None:
    base_config = _offline_config()
    changed_config = AgencyConfig(
        judge=base_config.judge,
        ollama=base_config.ollama,
        selector=SelectorConfig(min_confidence=0.8),
    )
    policy_a = {"actions": {"DEFAULT": {"always_include": []}}}
    policy_b = {"actions": {"DEFAULT": {"always_include": [{"slug": "x"}]}}}

    base = routing_fingerprint(CATALOG_A, base_config, policy_a)
    assert routing_fingerprint(list(reversed(CATALOG_A)), base_config, policy_a) == base
    assert routing_fingerprint(CATALOG_B, base_config, policy_a) != base
    assert routing_fingerprint(CATALOG_A, changed_config, policy_a) != base
    assert routing_fingerprint(CATALOG_A, base_config, policy_b) != base


def test_cache_and_stickiness_reject_ids_outside_current_catalog(monkeypatch) -> None:
    clear_cache()
    clear_session_routing()
    calls: list[str] = []

    def fake_judge(_task: str, catalog: list[dict[str, object]], **_kwargs: object) -> dict[str, object]:
        slug = str(catalog[0]["slug"])
        calls.append(slug)
        return {
            "selected_ids": [slug],
            "confidence": 0.9,
            "latency_ms": 0,
            "status": "applied",
        }

    # Force a context collision to prove the defensive ID validation works even
    # if a future fingerprint regression or hash collision occurs.
    monkeypatch.setattr(pipeline_module, "routing_fingerprint", lambda *_args: "same")
    monkeypatch.setattr(pipeline_module, "query_judge", fake_judge)
    monkeypatch.setattr(pipeline_module, "load_policy", lambda: {})
    config = _offline_config()

    first = route("session", "review authentication code", CATALOG_A, config=config)
    second = route("session", "review authentication code", CATALOG_B, config=config)

    assert first["selected_ids"] == ["code-reviewer"]
    assert second["selected_ids"] == ["security-auditor"]
    assert calls == ["code-reviewer", "security-auditor"]

    # Exercise the stickiness path separately from the exact-query cache.
    clear_cache()
    third = route(
        "sticky-session",
        "review authentication code and tests",
        CATALOG_A,
        config=config,
    )
    clear_cache()
    fourth = route(
        "sticky-session",
        "carefully review authentication code and tests",
        CATALOG_B,
        config=config,
    )
    assert third["selected_ids"] == ["code-reviewer"]
    assert fourth["selected_ids"] == ["security-auditor"]


def test_stickiness_recomputes_work_units_for_current_message(monkeypatch) -> None:
    clear_cache()
    clear_session_routing()
    monkeypatch.setattr(pipeline_module, "load_policy", lambda: {})
    monkeypatch.setattr(
        pipeline_module,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["code-reviewer"],
            "confidence": 0.9,
            "latency_ms": 0,
            "status": "applied",
        },
    )
    config = _offline_config()

    first = route(
        "work-session",
        "review authentication code tests documentation",
        CATALOG_A,
        config=config,
    )
    clear_cache()
    second = route(
        "work-session",
        "review authentication code tests documentation\n"
        "1. Review authentication code\n"
        "2. Review authentication tests\n"
        "3. Review authentication documentation",
        CATALOG_A,
        config=config,
    )

    assert first["work_units"]["count"] == 1
    assert second["session_reused"] is True
    assert second["work_units"]["count"] == 3
    assert second["work_units"]["delegate"] is True


def test_cache_and_session_state_are_thread_safe_and_bounded() -> None:
    clear_cache()
    clear_session_routing()

    def write(index: int) -> None:
        key = cache_key(f"query {index}")
        cache_put(key, {"selected_ids": [str(index)]}, max_entries=8)
        cache_get(key)
        session_put(
            f"session-{index}",
            f"query {index}",
            {"selected_ids": [str(index)]},
            max_entries=8,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write, range(64)))

    assert sum(cache_get(cache_key(f"query {index}")) is not None for index in range(64)) <= 8
    assert sum(
        session_check(f"session-{index}", f"query {index}") is not None
        for index in range(64)
    ) <= 8


def test_zero_signal_token_fallback_abstains() -> None:
    result = query_judge(
        "unrelated gibberish xyzzy",
        CATALOG_A,
        config=_offline_config(),
    )

    assert result["selected_ids"] == []
    assert result["confidence"] == 0.0
    assert result["status"] == "abstained"


def test_token_fallback_does_not_pad_with_zero_score_candidates() -> None:
    catalog = [
        {
            "slug": "technical-writer",
            "name": "Technical Writer",
            "description": "Writes README documentation and runbooks",
        },
        {
            "slug": "database-optimizer",
            "name": "Database Optimizer",
            "description": "Profiles SQL queries and database indexes",
        },
    ]

    result = query_judge(
        "write README documentation",
        catalog,
        config=_offline_config(),
    )

    assert result["status"] == "token_fallback"
    assert result["selected_ids"] == ["technical-writer"]


def test_semantically_invalid_provider_fails_over_and_bounds_confidence(monkeypatch) -> None:
    providers = (
        ProviderEntry(
            name="first",
            model="judge-a",
            base_url="https://first.invalid",
            api_key="key",
        ),
        ProviderEntry(
            name="second",
            model="judge-b",
            base_url="https://second.invalid",
            api_key="key",
        ),
    )
    responses = iter([
        _Response(["hallucinated-agent"], 0.9),
        _Response(["code-reviewer"], 7.5),
    ])
    calls: list[str] = []

    def fake_urlopen(request: object, **_kwargs: object) -> _Response:
        calls.append(str(getattr(request, "full_url", "")))
        return next(responses)

    monkeypatch.setattr(judge_module, "open_no_redirect", fake_urlopen)
    result = query_judge(
        "review authentication code",
        CATALOG_A,
        config=_offline_config(providers=providers),
    )

    assert len(calls) == 2
    assert result["selected_ids"] == ["code-reviewer"]
    assert result["confidence"] == 1.0
    assert result["provider"] == "second (openai-compatible)"


def test_provider_latency_is_cumulative_and_duplicate_ollama_retry_is_skipped(monkeypatch) -> None:
    provider = ProviderEntry(
        name="configured-ollama",
        type="ollama",
        model="judge",
        base_url="http://127.0.0.1:11434",
        ollama_mode=True,
    )
    config = AgencyConfig(
        providers=(provider,),
        judge=JudgeConfig(
            model="judge",
            base_url="http://127.0.0.1:11434",
            ollama_mode=True,
            confidence_bypass_threshold=999.0,
        ),
        ollama=OllamaConfig(
            enabled=True,
            model="judge",
            base_url="http://127.0.0.1:11434",
        ),
    )
    calls = 0

    def failing_urlopen(*_args: object, **_kwargs: object) -> _Response:
        nonlocal calls
        calls += 1
        raise urllib.error.URLError("offline")

    clock = iter([0.0, 0.0, 0.0, 0.25])
    monkeypatch.setattr(judge_module, "open_no_redirect", failing_urlopen)
    monkeypatch.setattr(judge_module.time, "monotonic", lambda: next(clock))

    result = query_judge(
        "review authentication code",
        CATALOG_A,
        config=config,
    )

    assert calls == 1
    assert result["status"] == "token_fallback"
    assert result["latency_ms"] == 250
