"""Focused contracts for the bounded no-match specialist fallback."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.litellm.callback import LiteLLMAdapter
from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig
from agency_runtime.core.header.contract import parse_header
from agency_runtime.core.header.finalize import finalize_response
from agency_runtime.core.installer import ensure_no_match_fallback_roster, seed_starter_roster
from agency_runtime.core.policy.defaults import NO_MATCH_FALLBACK_SLUGS, STARTER_ROSTER
from agency_runtime.core.roster.bundled import SOURCE_REPOSITORY, bundled_manifest
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.policy import load_bundled_policy
from agency_runtime.core.selector.semantic_retrieval import semantic_retrieve
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _isolated_selector_state() -> Iterator[None]:
    clear_cache()
    clear_session_routing()
    yield
    clear_session_routing()
    clear_cache()


def _offline_config() -> AgencyConfig:
    return AgencyConfig(
        providers=(),
        judge=JudgeConfig(
            model="",
            confidence_bypass_threshold=999.0,
            max_selected=3,
        ),
        ollama=OllamaConfig(enabled=False),
    )


def _fallback_only_store(path: Path) -> Store:
    store = Store(path)
    for entry in STARTER_ROSTER:
        if entry["slug"] in NO_MATCH_FALLBACK_SLUGS:
            store.activate_agent_if_missing(entry)
    return store


def test_fresh_seed_activates_both_bundled_fallback_prompts(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    source_revision = bundled_manifest()["source"]["revision"]

    assert seed_starter_roster(store) == len(STARTER_ROSTER)
    assert seed_starter_roster(store) == 0

    for slug in NO_MATCH_FALLBACK_SLUGS:
        entry = store.get_roster_entry(slug)
        prompt = store.get_specialist_prompt(slug)

        assert entry is not None
        assert entry["source"] == SOURCE_REPOSITORY
        assert entry["source_id"] == "agency-agents"
        assert entry["source_revision"] == source_revision
        assert entry["source_content_hash"]
        assert entry["prompt_path"] == f"bundled://agency-agents/{slug}"
        assert prompt is not None
        assert prompt["prompt_body"].strip()


def test_fallback_ensure_skips_noop_writes_and_restores_external_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    seed_starter_roster(store)
    statements: list[str] = []
    original_connect = store._connect

    def traced_connect():
        conn = original_connect()
        conn.set_trace_callback(statements.append)
        return conn

    monkeypatch.setattr(store, "_connect", traced_connect)

    assert ensure_no_match_fallback_roster(store) == 0
    assert not any(statement == "BEGIN IMMEDIATE" for statement in statements)

    conn = original_connect()
    try:
        conn.executemany(
            "DELETE FROM agent_active WHERE agent_slug = ?",
            [(slug,) for slug in NO_MATCH_FALLBACK_SLUGS],
        )
        conn.commit()
    finally:
        conn.close()
    statements.clear()

    assert ensure_no_match_fallback_roster(store) == len(NO_MATCH_FALLBACK_SLUGS)
    assert sum(statement == "BEGIN IMMEDIATE" for statement in statements) == len(
        NO_MATCH_FALLBACK_SLUGS
    )
    assert {entry["agent_slug"] for entry in store.get_active_roster()} >= set(
        NO_MATCH_FALLBACK_SLUGS
    )


def test_route_reserves_fallback_pair_until_primary_routing_has_no_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    catalog = [dict(agent) for agent in STARTER_ROSTER]
    fallback_ids = set(NO_MATCH_FALLBACK_SLUGS)

    no_match = pipeline.route(
        "fallback-session",
        "How do I cook a mushroom risotto?",
        catalog,
        config=_offline_config(),
    )

    assert no_match["selected_ids"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert no_match["semantic_ids"] == []
    assert no_match["fallback_companion_ids"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert no_match["fallback_considered"] is True
    assert no_match["fallback_applied"] is True
    assert no_match["status"] == "policy_fallback"
    assert no_match["source"] == "policy_fallback"
    assert no_match["semantic_status"] == "abstained"

    primary_match = pipeline.route(
        "fallback-session",
        "Review this authentication code for bugs and missing tests",
        catalog,
        config=_offline_config(),
    )

    assert primary_match["selected_ids"]
    assert fallback_ids.isdisjoint(primary_match["selected_ids"])
    assert primary_match["fallback_considered"] is False
    assert primary_match["fallback_applied"] is False


def test_full_roster_polyseme_requires_an_unreal_domain_anchor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    catalog = [dict(agent) for agent in STARTER_ROSTER]

    unrelated = pipeline.route(
        "cook-food",
        "How do I cook a mushroom risotto?",
        catalog,
        config=_offline_config(),
    )
    engine_candidates, engine_scores = semantic_retrieve(
        "Diagnose Unreal cook failures and optimize Niagara assets",
        catalog,
    )

    assert unrelated["selected_ids"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert unrelated["semantic_status"] == "abstained"
    assert engine_candidates[0]["slug"] == "unreal-technical-artist"
    assert engine_scores[0] > 0


def test_trivial_no_signal_route_skips_semantic_judge_and_applies_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("trivial turns must not call the semantic judge")
        ),
    )

    result = pipeline.route(
        "trivial-fallback",
        "ok",
        [dict(agent) for agent in STARTER_ROSTER],
        config=_offline_config(),
        turn_state={"state_known": True},
    )

    assert result["selected_ids"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert result["semantic_ids"] == []
    assert result["semantic_status"] == "abstained"
    assert result["status"] == "policy_fallback"
    assert result["source"] == "policy_fallback"
    assert result["candidate_count"] == 0


def test_explain_receipt_distinguishes_policy_fallback_from_semantic_abstention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    monkeypatch.setattr(
        "agency_runtime.core.selector.explain.load_policy",
        lambda *_args: load_bundled_policy(),
    )

    receipt = explain_route(
        "explain-fallback",
        "How do I cook a mushroom risotto?",
        [dict(agent) for agent in STARTER_ROSTER],
        config=_offline_config(),
    )

    selection = receipt["signals"]["selection"]
    assert selection["status"] == "policy_fallback"
    assert selection["source"] == "policy_fallback"
    assert selection["semantic_status"] == "abstained"
    assert selection["semantic_ids"] == []
    assert {item["source"] for item in receipt["selected"]} == {"policy_fallback"}
    assert set(NO_MATCH_FALLBACK_SLUGS).isdisjoint(
        {item["slug"] for item in receipt["considered_candidates"]}
    )


def test_fallback_agents_are_excluded_from_semantic_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    request = pipeline._route_request(
        "session",
        "ambiguous request",
        [dict(agent) for agent in STARTER_ROSTER],
        _offline_config(),
    )
    signals = pipeline._route_signals(request)

    semantic_slugs = {str(agent["slug"]) for agent in pipeline._semantic_catalog(request, signals)}

    assert set(NO_MATCH_FALLBACK_SLUGS).isdisjoint(semantic_slugs)
    assert len(signals.fallback_companion_ids) == 2


def test_confident_semantic_result_cannot_select_a_reserved_fallback_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    request = pipeline._route_request(
        "session",
        "review code",
        [dict(agent) for agent in STARTER_ROSTER],
        _offline_config(),
    )
    signals = pipeline._route_signals(request)

    result = pipeline._merge_computed_routing(
        {
            "selected_ids": ["agents-orchestrator", "code-reviewer"],
            "confidence": 0.99,
            "status": "confidence_bypass",
        },
        request,
        signals,
    )

    assert result["semantic_ids"] == ["code-reviewer"]
    assert "agents-orchestrator" not in result["selected_ids"]
    assert result["fallback_considered"] is False
    assert result["fallback_applied"] is False


def test_fresh_store_trivial_preflight_exposes_resident_pair_without_specialist_hydration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.selector.policy.load_policy",
        lambda *_args: load_bundled_policy(),
    )
    cases = (
        (
            "codex",
            lambda store: CodexAdapter(store=store),
            lambda adapter: adapter.run_preflight("codex-session", "ok"),
            "codex-session",
        ),
        (
            "hermes",
            lambda store: HermesAdapter(store=store),
            lambda adapter: adapter.pre_llm_call_handler(
                "hermes-session",
                "ok",
                "task-general",
                "hermes-trace",
            ),
            "hermes-session",
        ),
        (
            "litellm",
            lambda store: LiteLLMAdapter(store=store, config=_offline_config()),
            lambda adapter: adapter.pre_call_handler(
                "litellm-session",
                "ok",
                "task-general",
                trace_id="litellm-trace",
            ),
            "litellm-session",
        ),
    )

    for host, make_adapter, preflight, session_id in cases:
        store = Store(tmp_path / f"{host}.db")
        adapter = make_adapter(store)

        result = preflight(adapter)

        assert result is not None
        assert "managers=agents-orchestrator,chief-of-staff" in result["context"]
        assert result["resident_managers"] == list(NO_MATCH_FALLBACK_SLUGS)
        assert result["selected_specialists"] == []
        assert result["loaded_specialists"] == []
        assert store.get_specialists_for_session(session_id) == []
        if host == "codex":
            assert "[AGENCY PREFLIGHT]" in result["context"]
            assert "[AGENCY LOADED]" not in result["context"]
        else:
            assert "[Agency resident-manager kernel v1]" in result["context"]


@pytest.mark.parametrize(
    ("host", "adapter_type"),
    (("codex", CodexAdapter), ("claude", ClaudeAdapter)),
)
def test_isolated_trivial_fallback_can_finalize_without_child_activation(
    tmp_path: Path,
    host: str,
    adapter_type: type[CodexAdapter] | type[ClaudeAdapter],
) -> None:
    store = _fallback_only_store(tmp_path / f"{host}-trivial.db")
    adapter = adapter_type(store=store)
    trace_id = f"{host}-trivial-turn"

    preflight = adapter.build_preflight_context(
        f"{host}-session",
        "ok",
        trace_id=trace_id,
    )

    assert preflight is not None
    assert preflight["resident_managers"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert preflight["selected_specialists"] == []
    assert preflight["loaded_specialists"] == []
    assert "managers=agents-orchestrator,chief-of-staff" in preflight["context"]

    finalized = finalize_response(
        "Acknowledged.",
        {"session_id": f"{host}-session", "trace_id": trace_id, "host": host},
        store,
    )

    assert finalized["action"] == "accept"
    assert finalized["missing"] == []
    assert parse_header(finalized["text"])["agencies_loaded"] == (
        "agents-orchestrator, chief-of-staff"
    )
    assert store.get_run(trace_id)["status"] == "completed"


@pytest.mark.parametrize(
    ("host", "adapter_type"),
    (("codex", CodexAdapter), ("claude", ClaudeAdapter)),
)
def test_isolated_nontrivial_manager_fallback_does_not_invent_child_activation(
    tmp_path: Path,
    host: str,
    adapter_type: type[CodexAdapter] | type[ClaudeAdapter],
) -> None:
    store = _fallback_only_store(tmp_path / f"{host}-nontrivial.db")
    adapter = adapter_type(store=store)
    trace_id = f"{host}-nontrivial-turn"

    preflight = adapter.build_preflight_context(
        f"{host}-session",
        "Investigate this unusual request thoroughly and produce a durable implementation.",
        trace_id=trace_id,
    )

    assert preflight is not None
    assert preflight["resident_managers"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert preflight["selected_specialists"] == []
    assert preflight["loaded_specialists"] == []
    assert "managers=agents-orchestrator,chief-of-staff" in preflight["context"]

    finalized = finalize_response(
        "Implementation complete.",
        {"session_id": f"{host}-session", "trace_id": trace_id, "host": host},
        store,
    )

    assert finalized["action"] == "accept"
    assert finalized["missing"] == []
    assert parse_header(finalized["text"])["agencies_loaded"] == (
        "agents-orchestrator, chief-of-staff"
    )
    assert store.get_run(trace_id)["status"] == "completed"


def test_partial_legacy_roster_gains_fallback_without_overwriting_operator_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.selector.policy.load_policy",
        lambda *_args: load_bundled_policy(),
    )
    store = Store(tmp_path / "partial.db")
    operator_entry = {
        "slug": "operator-specialist",
        "name": "Operator Specialist",
        "source": "operator",
        "version": "9.0.0",
        "description": "Operator-owned specialist.",
        "prompt_body": "Preserve this operator-owned prompt.",
    }
    store._activate_prevalidated_agent(operator_entry)
    before = store.get_roster_entry("operator-specialist")

    result = HermesAdapter(store=store).pre_llm_call_handler(
        "legacy-session",
        "ok",
        "task-general",
        "legacy-turn",
    )

    assert result is not None
    assert "managers=agents-orchestrator,chief-of-staff" in result["context"]
    assert store.get_roster_entry("operator-specialist") == before
    assert store.get_specialist_prompt("operator-specialist")["prompt_body"] == (
        "Preserve this operator-owned prompt."
    )
    for slug in NO_MATCH_FALLBACK_SLUGS:
        entry = store.get_roster_entry(slug)
        assert entry["source"] == SOURCE_REPOSITORY
        assert entry["source_id"] == "agency-agents"
