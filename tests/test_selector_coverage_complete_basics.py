"""Adversarial coverage contracts for selector utilities and eval harnesses."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig, SelectorConfig
from agency_runtime.core.evals import benchmarks
from agency_runtime.core.evals import delegation as delegation_eval
from agency_runtime.core.evals import full_roster as full_roster_eval
from agency_runtime.core.evals import routing as routing_eval
from agency_runtime.core.selector import (
    cache,
    candidate_narrow,
    delegation_detection,
    explain,
    intent_text,
    pipeline,
    semantic_retrieval,
    stickiness,
)
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent


@pytest.fixture(autouse=True)
def _isolated_selector_caches() -> None:
    cache.clear_cache()
    stickiness.clear_session_routing()
    yield
    cache.clear_cache()
    stickiness.clear_session_routing()


@dataclass(frozen=True)
class _FingerprintValue:
    name: str


class _StableObject:
    def __repr__(self) -> str:
        return "stable-object"


class _UncopyableObject:
    def __deepcopy__(self, _memo: dict[int, object]) -> object:
        raise TypeError("copy disabled")


class _UncomparableObject:
    def __eq__(self, _other: object) -> bool:
        raise TypeError("comparison disabled")


def test_cache_canonicalizes_unordered_paths_dataclasses_and_unknown_values() -> None:
    assert cache._canonicalize(_FingerprintValue("value")) == {"name": "value"}
    assert cache._canonicalize({Path("b"), Path("a")}) == ["a", "b"]
    assert cache._canonicalize(Path("folder") / "file") == str(Path("folder") / "file")
    assert cache._canonicalize(_StableObject()) == "stable-object"

    guard = cache._policy_mutation_guard(
        {"specialist_availability": {"roster_gated": ["not", "a", "mapping"]}}
    )
    assert "list" in repr(guard)


def test_structural_fallback_guards_detect_roster_and_policy_mutations() -> None:
    catalog = [
        {
            "slug": "security-specialist",
            "name": "Security Specialist",
            "description": "Reviews authentication controls",
            "division": "security",
            "categories": ["security"],
            "capabilities": ["threat modeling"],
            "tool_affinity": ["terminal"],
        }
    ]
    roster_guard = cache._catalog_guard(catalog)
    catalog[0]["categories"].append("identity")
    assert cache._catalog_guard(catalog) != roster_guard

    container = ["first"]
    container_guard = cache._container_guard(container)
    container.append("second")
    assert cache._container_guard(container) != container_guard

    policy = {
        "actions": {
            "SECURITY_REVIEW": {
                "triggers": ["security review"],
                "always_include": ["security-specialist"],
                "conditional": [],
            },
            "legacy": "disabled",
        },
        "division_anchors": {
            "security": {
                "anchor": "security-specialist",
                "keywords": ["security"],
                "conditional": [],
            },
            "legacy": "disabled",
        },
        "specialist_availability": {
            "schema_version": 1,
            "enabled": ["security-specialist"],
            "roster_gated": {
                "reason": "optional roster entry",
                "slugs": ["security-specialist"],
            },
        },
    }
    policy_guard = cache._policy_mutation_guard(policy)
    policy["actions"]["SECURITY_REVIEW"]["triggers"].append("threat model")
    assert cache._policy_mutation_guard(policy) != policy_guard

    absent_availability = cache._policy_mutation_guard({})[-1]
    assert absent_availability == ("NoneType", "None")


def test_mutation_snapshots_use_complete_and_defensive_fallback_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete = cache._mutation_snapshot({"nested": ["value"]}, lambda: "unused")
    assert complete.complete is True
    assert cache._snapshot_matches({"nested": ["value"]}, complete, lambda: "unused")
    assert not cache._snapshot_matches({"nested": ["changed"]}, complete, lambda: "unused")

    fallback = cache._mutation_snapshot(_UncopyableObject(), lambda: "guard")
    assert fallback == cache._MutationSnapshot("guard", complete=False)
    assert cache._snapshot_matches(object(), fallback, lambda: "guard")
    assert not cache._snapshot_matches(
        _UncomparableObject(),
        cache._MutationSnapshot(_UncomparableObject(), complete=True),
        lambda: "unused",
    )

    catalog = [{"slug": "first", "extra": {"revision": 1}}]
    config = object()
    policy: dict[str, Any] = {}
    initial = cache.routing_fingerprint(catalog, config, policy)
    catalog[0]["extra"]["revision"] = 2
    assert cache.routing_fingerprint(catalog, config, policy) != initial

    # Simulate eviction after lock-free snapshot validation. The already-read
    # immutable entry remains safe to return and must not cause an LRU KeyError.
    current = cache.routing_fingerprint(catalog, config, policy)
    real_matches = cache._snapshot_matches
    matches = 0

    def evict_after_validation(
        value: Any,
        snapshot: cache._MutationSnapshot,
        guard: Any,
    ) -> bool:
        nonlocal matches
        matches += 1
        matched = real_matches(value, snapshot, guard)
        if matches == 2:
            cache.clear_cache()
        return matched

    monkeypatch.setattr(cache, "_snapshot_matches", evict_after_validation)
    assert cache.routing_fingerprint(catalog, config, policy) == current
    assert not cache._FINGERPRINT_CACHE


def test_cache_derives_context_keys_evicts_guards_and_expires_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cache, "_FINGERPRINT_MAX_ENTRIES", 1)
    first_catalog = [{"slug": "first"}]
    second_catalog = [{"agent_slug": "second"}]

    first_fingerprint = cache.routing_fingerprint(first_catalog, object(), {})
    second_fingerprint = cache.routing_fingerprint(second_catalog, object(), {})
    assert first_fingerprint != second_fingerprint
    assert len(cache._FINGERPRINT_CACHE) == 1

    derived = cache.cache_key(
        "  Same   Query ",
        catalog=first_catalog,
        config=SimpleNamespace(mode="one"),
        policy={},
    )
    assert derived != cache.cache_key("same query")

    assert cache.catalog_active_ids(
        first_catalog,
        context_fingerprint=first_fingerprint,
    ) == frozenset({"first"})
    assert cache.catalog_active_ids(
        second_catalog,
        context_fingerprint=second_fingerprint,
    ) == frozenset({"second"})
    assert len(cache._ACTIVE_IDS_CACHE) == 1
    assert cache.catalog_active_ids(
        second_catalog,
        context_fingerprint=second_fingerprint,
    ) == frozenset({"second"})

    clock = iter([1.0, 3.0])
    monkeypatch.setattr(cache.time, "monotonic", lambda: next(clock))
    cache.cache_put("expiring", {"selected_ids": ["first"]})
    assert cache.cache_get("expiring", ttl=1.0) is None
    assert "expiring" not in cache._ROUTING_CACHE


def test_candidate_helpers_accept_generic_metadata_without_false_signal() -> None:
    assert candidate_narrow._field_values({"ignored": "mapping"}) == ()
    assert set(candidate_narrow._field_values({"alpha", None, "beta"})) == {
        "alpha",
        "beta",
    }
    assert candidate_narrow._field_values(b"bytes") == ("b'bytes'",)
    assert candidate_narrow._field_values(7) == ("7",)

    compiled = candidate_narrow._compiled_agent_score_inputs(
        candidate_narrow._agent_signature(
            {
                "slug": "same-specialist",
                "agent_slug": "same-specialist",
            }
        )
    )
    assert dict(compiled[0])["same"] == 4.0
    assert candidate_narrow._contains_phrase(("code", "review"), ("code", "review"))
    assert not candidate_narrow._contains_phrase(("code", "review"), ("review", "code"))
    assert not candidate_narrow._contains_phrase(("code",), ("code",))
    assert candidate_narrow.score_agent({"slug": "x"}, set()) == 0.0

    catalog = [{"slug": "first"}, {"slug": "second"}]
    selected, scores = candidate_narrow.pre_narrow("the and with", catalog, limit=1)
    assert selected == [catalog[0]]
    assert scores == [0.0]
    matched, matched_scores = candidate_narrow.pre_narrow("first", catalog, limit=1)
    assert matched == [catalog[0]]
    assert matched_scores[0] > 0


def test_delegation_detector_keeps_actionable_leaves_and_deduplicates_spans() -> None:
    message = "1. Build the API\n   - Current status\n   - Test the API\n2. Deploy the app"
    assert delegation_detection._list_units(message) == ["Test the API", "Deploy the app"]
    assert delegation_detection._imperative_units("Fix x fix x") == ["Fix x"]
    multiple = delegation_detection.detect_work_units(
        "Fix the API, test the database, deploy the service"
    )
    assert multiple["source"] == "multiple_imperatives"
    assert multiple["delegate"] is True


def test_intent_mask_preserves_newlines_and_rejects_non_text() -> None:
    with pytest.raises(TypeError, match="must be a string"):
        intent_text.mask_excluded_intent(7)  # type: ignore[arg-type]

    masked = intent_text.mask_excluded_intent("Ship this:\nnot deploy but test locally")
    assert masked.count("\n") == 1
    assert "deploy" not in masked
    assert "test locally" in masked


def test_explanation_helpers_bound_invalid_limits_and_render_missing_agents() -> None:
    assert explain._clamp_limit(object()) == explain._DEFAULT_LIMIT  # type: ignore[arg-type]
    assert explain._agent_summary(None) == {
        "slug": "",
        "name": "",
        "division": "",
        "description": "",
        "selected": False,
    }
    assert explain._domain_terms(
        "review code",
        "review code [domain context: security, performance]",
    ) == ["security", "performance"]


def test_stickiness_rejects_stale_context_and_bounds_session_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert stickiness.session_check("", "security review") is None
    assert stickiness.session_check("missing", "security review") is None

    stickiness.session_put(
        "session",
        "security review",
        {"selected_ids": ["security", "retired"]},
        context_fingerprint="one",
    )
    assert (
        stickiness.session_check(
            "session",
            "security review",
            context_fingerprint="two",
        )
        is None
    )
    assert stickiness.session_check("session", "", context_fingerprint="one") is None
    assert (
        stickiness.session_check(
            "session",
            "unrelated database migration",
            context_fingerprint="one",
        )
        is None
    )
    reused = stickiness.session_check(
        "session",
        "security review",
        context_fingerprint="one",
        valid_ids={"security"},
    )
    assert reused is not None
    assert reused["selected_ids"] == ["security"]

    stickiness.session_put("evict", "other work", {"selected_ids": ["other"]}, max_entries=1)
    assert list(stickiness._SESSION_ROUTING) == ["evict"]

    monkeypatch.setattr(stickiness.time, "monotonic", lambda: 100.0)
    stickiness._SESSION_ROUTING["evict"]["_ts"] = 0.0
    assert stickiness.session_check("evict", "other work", max_age=1.0) is None


def test_pipeline_refreshes_legacy_cache_and_survives_persistence_failure() -> None:
    routing = {
        "selected_ids": ["semantic", "old-companion"],
        "available_companion_ids": ["old-companion"],
    }
    refreshed = pipeline._refresh_reused_routing(
        routing,
        active_ids={"semantic", "new-companion"},
        matched_actions=["CODING"],
        companion_ids=["semantic", "new-companion"],
        available_companion_ids=["semantic", "new-companion"],
        unavailable_companion_ids=[],
        work_units={"delegate": False},
    )
    assert refreshed is routing
    assert refreshed["selected_ids"] == ["semantic", "new-companion"]

    class BrokenStore:
        def record_routing_decision(self, **_kwargs: Any) -> str:
            raise OSError("store unavailable")

    finalized = pipeline._finalize_decision(
        {},
        session_id="session",
        user_message="work",
        context_fingerprint="fingerprint",
        store=BrokenStore(),  # type: ignore[arg-type]
        trace_id="trace",
    )
    assert finalized["trace_id"] == "trace"
    assert "decision_id" not in finalized


def test_workforce_route_does_not_expose_legacy_keyword_companions() -> None:
    signals = pipeline._RouteSignals(
        policy_validation={
            "valid": True,
            "errors": [],
            "enabled_slugs": ["business-strategist"],
            "disabled_count": 0,
        },
        matched_actions=["BUSINESS"],
        companion_ids=["business-strategist"],
        available_companion_ids=["business-strategist"],
        unavailable_companion_ids=[],
        fallback_companion_ids=["agents-orchestrator", "chief-of-staff"],
        available_fallback_companion_ids=["agents-orchestrator", "chief-of-staff"],
        unavailable_fallback_companion_ids=[],
        work_units={"delegate": False},
    )

    result = pipeline._attach_workforce_signals(
        {
            "selected_ids": ["application-integration-verifier"],
            "semantic_ids": ["application-integration-verifier"],
        },
        SimpleNamespace(
            source_message_hash="a" * 64,
            capability_receipt={},
            eligibility_rejections=(),
        ),  # type: ignore[arg-type]
        signals,
    )

    assert result["selected_ids"] == ["application-integration-verifier"]
    assert result["companion_actions"] == []
    assert result["companion_ids"] == []
    assert result["selected_companion_ids"] == []
    assert result["fallback_companion_ids"] == [
        "agents-orchestrator",
        "chief-of-staff",
    ]


def test_pipeline_uses_cached_reuse_and_renders_every_context_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = AgencyConfig(
        judge=JudgeConfig(model="", base_url=""),
        ollama=OllamaConfig(enabled=False, model=""),
        selector=SelectorConfig(max_user_msg_len=4, min_confidence=0.5),
    )
    assert pipeline.refine_query("abcdefgh", cfg) == "abcd"
    assert pipeline._available_companions(["active", "missing"], {"active"}) == (
        ["active"],
        ["missing"],
    )

    request = pipeline._RouteRequest(
        session_id="session",
        trace_id="trace",
        user_message="work",
        catalog=[{"slug": "active"}],
        workforce_catalog=[{"slug": "active"}],
        config=cfg,
        policy={},
        context_fingerprint="fingerprint",
        routing_query="work",
        cache_key="key",
        source_message_hash="current",
        active_ids=frozenset({"active"}),
    )
    signals = pipeline._RouteSignals(
        policy_validation={"valid": True, "errors": [], "enabled_slugs": [], "disabled_count": 0},
        matched_actions=[],
        companion_ids=[],
        available_companion_ids=[],
        unavailable_companion_ids=[],
        fallback_companion_ids=["agents-orchestrator", "chief-of-staff"],
        available_fallback_companion_ids=["agents-orchestrator", "chief-of-staff"],
        unavailable_fallback_companion_ids=[],
        work_units={"delegate": False},
    )
    monkeypatch.setattr(pipeline, "_route_request", lambda *_args, **_kwargs: request)
    monkeypatch.setattr(
        pipeline,
        "cache_get",
        lambda _key: {
            "selected_ids": ["active"],
            "semantic_ids": ["active"],
            "source_message_hash": "previous",
        },
    )
    monkeypatch.setattr(pipeline, "_route_signals", lambda _request: signals)
    continuation_message = "continue"
    unchanged_continuation = classify_turn_intent(
        continuation_message,
        TurnState(
            previous_trace_id="prior-trace",
            state_known=True,
            state_status="current",
            previous_status="active",
            previous_turn_kind="new_intent",
            active_plan=True,
        ),
    )

    reused = pipeline.route(
        "session",
        continuation_message,
        request.catalog,
        config=cfg,
        turn_classification=unchanged_continuation,
    )
    assert reused["selected_ids"] == ["active"]
    assert reused["source_message_hash"] == "current"

    monkeypatch.setattr(
        pipeline,
        "cache_get",
        lambda _key: {
            "selected_ids": ["active"],
            "source_message_hash": "current",
        },
    )
    exact = pipeline.route(
        "session",
        continuation_message,
        request.catalog,
        config=cfg,
        turn_classification=unchanged_continuation,
    )
    assert exact["selected_ids"] == ["active"]

    low_confidence = {
        "selected_ids": ["active"],
        "confidence": 0.1,
        "status": "token_fallback",
        "work_units": {"delegate": False},
    }
    assert "source=cache" in pipeline.build_routing_context(
        {**low_confidence, "cache_hit": True}, cfg
    )
    assert "source=session" in pipeline.build_routing_context(
        {**low_confidence, "session_reused": True}, cfg
    )
    opportunity = pipeline.build_routing_context(
        {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "unknown",
            "work_units": {"delegate": True, "count": 2, "units": []},
        },
        cfg,
    )
    assert "[DELEGATION OPPORTUNITY]" in opportunity
    assert "Detected work units:" not in opportunity
    trivial_routing = pipeline.route(
        "session",
        "ok",
        [
            {"slug": "agents-orchestrator"},
            {"slug": "chief-of-staff"},
        ],
        config=cfg,
        turn_state={"state_known": True},
    )
    trivial_context = pipeline.build_routing_context(trivial_routing, cfg)
    assert "agents-orchestrator, chief-of-staff" in trivial_context
    assert "source=policy_fallback" in trivial_context


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"iterations": 0}, "iterations"),
        ({"workers": 0}, "workers"),
        ({"roster_size": 0}, "roster_size"),
    ],
)
def test_microbenchmark_rejects_invalid_dimensions_without_timing(
    kwargs: dict[str, int],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        benchmarks.run_candidate_microbenchmark(**kwargs)


def test_eval_helpers_fail_closed_without_running_wall_clock_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="non-empty catalog"):
        benchmarks._run_concurrency_probe(
            query="query",
            catalog=[],
            concurrent_calls=1,
            workers=1,
        )
    with pytest.raises(ValueError, match="non-negative"):
        benchmarks.generated_catalog(-1)
    assert benchmarks._percentile([], 0.95) == 0.0

    failed = delegation_eval._run_case(
        "assertion",
        lambda: (_ for _ in ()).throw(AssertionError("contract failed")),
    )
    assert failed == {"name": "assertion", "passed": False, "error": "contract failed"}

    monkeypatch.setattr(
        routing_eval,
        "POLICY_CASES",
        (
            {
                "id": "missing-required",
                "message": "work",
                "required": ["REQUIRED"],
                "required_companions": [],
                "forbidden": [],
            },
        ),
    )
    monkeypatch.setattr(routing_eval, "load_bundled_policy", lambda: {})
    monkeypatch.setattr(routing_eval, "detect_actions", lambda *_args, **_kwargs: ([], []))
    metrics, details = routing_eval._policy_metrics()
    assert metrics["required_recall"] == 0.0
    assert details[0]["passed"] is False

    monkeypatch.setattr(routing_eval, "_routing_metrics", lambda: ({}, []))
    monkeypatch.setattr(routing_eval, "_policy_metrics", lambda: ({}, []))
    monkeypatch.setattr(routing_eval, "_delegation_metrics", lambda: ({}, []))
    monkeypatch.setattr(routing_eval, "run_candidate_microbenchmark", lambda: {})
    monkeypatch.setattr(
        routing_eval,
        "run_semantic_retrieval_scale_benchmark",
        lambda: {
            "version": "synthetic",
            "query_sha256": "0" * 64,
            "cold_includes_tracemalloc": True,
            "tiers": [],
        },
    )
    monkeypatch.setattr(
        routing_eval,
        "run_cli_version_startup_benchmark",
        lambda: {
            "version": "synthetic",
            "iterations": 0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "samples_ms": [],
            "output_valid": True,
        },
    )
    monkeypatch.setattr(routing_eval, "_gates", lambda _metrics: [])
    report = routing_eval.run_routing_eval(include_details=False)
    assert report["passed"] is True
    assert "details" not in report


def test_generated_benchmark_catalog_reserves_resident_manager_slots() -> None:
    assert benchmarks.generated_catalog(0) == []
    assert [item["slug"] for item in benchmarks.generated_catalog(1)] == ["agents-orchestrator"]
    assert [item["slug"] for item in benchmarks.generated_catalog(3)] == [
        "agents-orchestrator",
        "chief-of-staff",
        "security-specialist-0000",
    ]


def test_semantic_retrieval_scale_benchmark_uses_deterministic_measurements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = [{"slug": "performance-specialist-0000"}]
    retrieval_calls: list[int] = []
    ticks = iter((0.0, 0.001, 1.0, 1.001, 2.0, 2.001, 3.0, 3.001))

    monkeypatch.setattr(
        benchmarks,
        "generated_catalog",
        lambda size: [{"slug": f"catalog-entry-{size}"}],
    )
    monkeypatch.setattr(benchmarks, "clear_semantic_retrieval_cache", lambda: None)
    monkeypatch.setattr(benchmarks.gc, "collect", lambda: 0)
    monkeypatch.setattr(benchmarks.tracemalloc, "is_tracing", lambda: False)
    monkeypatch.setattr(benchmarks.tracemalloc, "start", lambda: None)
    monkeypatch.setattr(benchmarks.tracemalloc, "stop", lambda: None)
    monkeypatch.setattr(
        benchmarks.tracemalloc,
        "get_traced_memory",
        lambda: (0, 1024 * 1024),
    )
    monkeypatch.setattr(benchmarks.time, "perf_counter", lambda: next(ticks))

    def retrieve(
        _query: str,
        _catalog: object,
        *,
        limit: int,
    ) -> tuple[list[dict[str, str]], list[float]]:
        retrieval_calls.append(limit)
        return selected, [1.0]

    monkeypatch.setattr(benchmarks, "semantic_retrieve", retrieve)

    report = benchmarks.run_semantic_retrieval_scale_benchmark(
        tiers=(263,),
        warm_samples=3,
    )

    assert retrieval_calls == [40, 40, 40, 40]
    assert report["passed"] is True
    assert report["tiers"] == [
        {
            **report["tiers"][0],
            "roster_size": 263,
            "selected_count": 1,
            "cold_ms": 1.0,
            "warm_samples": 3,
            "warm_p95_ms": 1.0,
            "warm_samples_ms": [1.0, 1.0, 1.0],
            "peak_mib": 1.0,
            "deterministic": True,
            "correctness": True,
            "gates": {
                "cold_latency": True,
                "warm_latency": True,
                "peak_memory": True,
                "deterministic_correctness": True,
            },
            "passed": True,
        }
    ]


def test_cli_version_startup_benchmark_uses_deterministic_subprocess_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter((0.0, 0.001, 1.0, 1.002, 2.0, 2.003))
    commands: list[list[str]] = []
    monkeypatch.setattr(benchmarks.time, "perf_counter", lambda: next(ticks))

    def run(command: list[str], **kwargs: object) -> object:
        commands.append(command)
        assert kwargs == {
            "check": False,
            "capture_output": True,
            "text": True,
            "timeout": 5.0,
        }
        return SimpleNamespace(
            returncode=0,
            stdout=f"agency {benchmarks.__version__}\n",
            stderr="",
        )

    monkeypatch.setattr(benchmarks.subprocess, "run", run)

    report = benchmarks.run_cli_version_startup_benchmark(iterations=3)

    assert len(commands) == 3
    assert all(command[0] == benchmarks.sys.executable for command in commands)
    assert report["samples_ms"] == [1.0, 2.0, 3.0]
    assert report["p50_ms"] == 2.0
    assert report["p95_ms"] == 3.0
    assert report["output_valid"] is True
    assert report["passed"] is True


def test_benchmark_contracts_reject_invalid_dimensions_and_active_tracing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="warm_samples"):
        benchmarks.run_semantic_retrieval_scale_benchmark(warm_samples=True)
    with pytest.raises(ValueError, match="tiers"):
        benchmarks.run_semantic_retrieval_scale_benchmark(tiers=())
    monkeypatch.setattr(benchmarks.tracemalloc, "is_tracing", lambda: True)
    with pytest.raises(RuntimeError, match="idle tracemalloc"):
        benchmarks.run_semantic_retrieval_scale_benchmark(tiers=(263,))
    with pytest.raises(ValueError, match="iterations"):
        benchmarks.run_cli_version_startup_benchmark(iterations=True)


def test_full_roster_probe_scaffolding_is_neutral_to_both_retrievers() -> None:
    scaffold = full_roster_eval._PROBE_QUERY_TEMPLATE.format(
        first="",
        second="",
        paraphrased="",
    )

    assert candidate_narrow.tokenize(scaffold) == set()
    assert semantic_retrieval._tokens(scaffold) == ()


def test_full_roster_card_projection_skips_nonapproved_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = {
        "agents": [
            {
                "slug": "quarantined-agent",
                "display_name": "Quarantined Agent",
                "audit_status": "quarantined",
            },
            {
                "slug": "approved-agent",
                "display_name": "Approved Agent",
                "audit_status": "approved",
            },
        ]
    }
    monkeypatch.setattr(full_roster_eval, "bundled_manifest", lambda: manifest)
    monkeypatch.setattr(full_roster_eval, "selector_roster_projection", dict)
    monkeypatch.setattr(full_roster_eval, "KNOWN_CONTRACTORS_BY_SLUG", {})

    loaded_manifest, cards = full_roster_eval._routing_cards()

    assert loaded_manifest is manifest
    assert cards == [
        {
            "slug": "approved-agent",
            "display_name": "Approved Agent",
            "audit_status": "approved",
            "agent_slug": "approved-agent",
            "name": "Approved Agent",
        }
    ]


@pytest.mark.parametrize(
    ("warm", "probe", "message"),
    [
        (
            {"selected_ids": [], "trace_id": "warm"},
            {"selected_ids": [], "trace_id": "probe", "cache_hit": True},
            "warm-up did not produce a cacheable selection",
        ),
        (
            {"selected_ids": ["agents-orchestrator"], "trace_id": "warm"},
            {"selected_ids": ["agents-orchestrator"], "trace_id": "probe"},
            "warm-up was not reused by the probe request",
        ),
        (
            {"selected_ids": ["agents-orchestrator"], "trace_id": "warm"},
            {
                "selected_ids": ["chief-of-staff"],
                "trace_id": "probe",
                "cache_hit": True,
            },
            "probe changed the warm-up selection",
        ),
    ],
)
def test_microbenchmark_rejects_an_invalid_cache_warmup(
    monkeypatch: pytest.MonkeyPatch,
    warm: dict[str, Any],
    probe: dict[str, Any],
    message: str,
) -> None:
    monkeypatch.setattr(benchmarks, "_WARMUP_CALLS", 0)
    monkeypatch.setattr(benchmarks, "_BENCHMARK_BATCHES", 1)
    monkeypatch.setattr(benchmarks, "_MIN_CACHE_SAMPLES", 1)
    monkeypatch.setattr(
        benchmarks,
        "_run_concurrency_probe",
        lambda **_kwargs: {
            "results": [()],
            "elapsed_ms": 1.0,
            "overlap": 1,
            "threads": 1,
            "synchronized": True,
        },
    )
    responses = iter((warm, probe))
    monkeypatch.setattr(benchmarks, "route", lambda *_args, **_kwargs: next(responses))

    with pytest.raises(RuntimeError, match=message):
        benchmarks.run_candidate_microbenchmark(
            roster_size=1,
            iterations=1,
            workers=1,
        )


def test_microbenchmark_harness_runs_with_synthetic_clock_not_wall_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(benchmarks, "_WARMUP_CALLS", 1)
    monkeypatch.setattr(benchmarks, "_BENCHMARK_BATCHES", 2)
    monkeypatch.setattr(benchmarks, "_MIN_CACHE_SAMPLES", 2)
    ticks = count()
    monkeypatch.setattr(benchmarks.time, "perf_counter", lambda: next(ticks) / 1000)

    def narrow(
        _query: str,
        catalog: list[dict[str, Any]],
        limit: int,
    ) -> tuple[list[dict[str, Any]], list[float]]:
        assert limit == 20
        return [catalog[0]], [1.0]

    monkeypatch.setattr(benchmarks, "pre_narrow", narrow)
    monkeypatch.setattr(
        benchmarks,
        "_run_concurrency_probe",
        lambda **kwargs: {
            "results": [
                (str(kwargs["catalog"][0]["slug"]),) for _ in range(kwargs["concurrent_calls"])
            ],
            "elapsed_ms": 1.0,
            "overlap": kwargs["workers"],
            "threads": kwargs["workers"],
            "synchronized": True,
        },
    )
    route_counter = count()

    def synthetic_route(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        index = next(route_counter)
        return {
            "selected_ids": ["performance-specialist-0000"],
            "trace_id": f"trace-{index}",
            "cache_hit": index > 0,
        }

    monkeypatch.setattr(benchmarks, "route", synthetic_route)
    monkeypatch.setattr(benchmarks, "clear_cache", lambda: None)
    monkeypatch.setattr(benchmarks, "clear_session_routing", lambda: None)

    result = benchmarks.run_candidate_microbenchmark(
        roster_size=1,
        iterations=2,
        workers=2,
    )

    assert result["latency_samples"] == 4
    assert result["cache_hit_samples"] == 4
    assert result["p95_ms"] == 1.0
    assert result["cache_hit_p95_ms"] == 1.0
    assert result["deterministic"] is True
    assert result["cache_hit_deterministic"] is True


def test_routing_eval_exercises_accuracy_gates_with_synthetic_performance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        routing_eval,
        "run_candidate_microbenchmark",
        lambda: {
            "p95_ms": 0.0,
            "cache_hit_p95_ms": 0.0,
            "concurrent_calls_per_second": 100.0,
            "concurrent_overlap": 2,
            "concurrent_probe_synchronized": True,
            "deterministic": True,
            "cache_hit_deterministic": True,
        },
    )
    monkeypatch.setattr(
        routing_eval,
        "run_semantic_retrieval_scale_benchmark",
        lambda: {
            "version": "synthetic",
            "query_sha256": "0" * 64,
            "cold_includes_tracemalloc": True,
            "tiers": [
                {
                    "roster_size": size,
                    "cold_ms": 0.0,
                    "warm_p95_ms": 0.0,
                    "peak_mib": 0.0,
                    "deterministic": True,
                    "correctness": True,
                }
                for size in (263, 1000, 10000)
            ],
        },
    )
    monkeypatch.setattr(
        routing_eval,
        "run_cli_version_startup_benchmark",
        lambda: {
            "version": "synthetic",
            "iterations": 1,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "samples_ms": [0.0],
            "output_valid": True,
        },
    )

    report = routing_eval.run_routing_eval(include_details=True)

    assert report["passed"] is True
    synthetic_areas = {"retrieval_scale", "cli_startup"}
    synthetic_gates = [gate for gate in report["gates"] if gate["area"] in synthetic_areas]
    assert {gate["area"] for gate in synthetic_gates} == synthetic_areas
    assert all(gate["passed"] for gate in synthetic_gates)
    assert report["details"]["routing"]
    assert report["details"]["policy"]
    assert report["details"]["delegation"]
