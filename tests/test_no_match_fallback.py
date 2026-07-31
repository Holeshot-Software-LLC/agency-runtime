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
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_SLUGS
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


def _resident_only_store(path: Path) -> Store:
    return Store(path)


def test_fresh_seed_installs_imported_managers_without_a_worker_fallback(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    source_revision = bundled_manifest()["source"]["revision"]

    assert seed_starter_roster(store) == len(STARTER_ROSTER)
    assert seed_starter_roster(store) == 0

    assert NO_MATCH_FALLBACK_SLUGS == ()
    for slug in ("agents-orchestrator", "chief-of-staff"):
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


def test_removed_fallback_ensure_is_a_write_free_noop(
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
    monkeypatch.setattr(
        store,
        "get_active_roster",
        lambda **_kwargs: pytest.fail(
            "fallback presence checks must not decode the complete active roster"
        ),
    )

    assert ensure_no_match_fallback_roster(store) == 0
    assert not any(statement == "BEGIN IMMEDIATE" for statement in statements)
    presence_queries = [
        statement
        for statement in statements
        if "FROM agent_active AS a JOIN agent_versions AS v" in statement
        and "WHERE a.agent_slug IN" in statement
    ]
    assert presence_queries == []
    assert ensure_no_match_fallback_roster(store) == 0
    assert not any(statement == "BEGIN IMMEDIATE" for statement in statements)


def test_unconfigured_inference_never_restores_a_no_match_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: load_bundled_policy())
    catalog = [dict(agent) for agent in STARTER_ROSTER]
    no_match = pipeline.route(
        "fallback-session",
        "How do I cook a mushroom risotto?",
        catalog,
        config=_offline_config(),
    )

    assert no_match["selected_ids"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert no_match["semantic_ids"] == []
    assert no_match["fallback_companion_ids"] == list(NO_MATCH_FALLBACK_SLUGS)
    assert no_match["fallback_considered"] is False
    assert no_match["fallback_applied"] is False
    assert no_match["status"] == "inference_unavailable"

    primary_match = pipeline.route(
        "fallback-session",
        "Review this authentication code for bugs and missing tests",
        catalog,
        config=_offline_config(),
    )

    assert primary_match["selected_ids"] == []
    assert primary_match["status"] == "inference_unavailable"
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
    assert unrelated["status"] == "inference_unavailable"
    assert engine_candidates[0]["slug"] == "unreal-technical-artist"
    assert engine_scores[0] > 0


def test_trivial_no_signal_route_skips_semantic_judge_without_a_worker_fallback(
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
    assert result["status"] == "abstained"
    assert result["fallback_considered"] is False
    assert result["fallback_applied"] is False
    assert result["selection_required"] is False
    assert result["candidate_count"] == 0


def test_explain_receipt_reports_inference_failure_without_a_fallback_identity(
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
    assert selection["status"] == "inference_unavailable"
    assert selection["semantic_ids"] == []
    assert receipt["selected"] == []
    assert set(NO_MATCH_FALLBACK_SLUGS).isdisjoint(
        {item["slug"] for item in receipt["considered_candidates"]}
    )


def test_no_match_policy_reserves_no_imported_manager_identity(
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

    assert signals.fallback_companion_ids == []
    assert signals.available_fallback_companion_ids == []
    assert signals.unavailable_fallback_companion_ids == []


def test_imported_orchestrator_is_an_ordinary_inference_candidate(
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

    assert result["semantic_ids"] == ["agents-orchestrator", "code-reviewer"]
    assert result["selected_ids"] == ["agents-orchestrator", "code-reviewer"]
    assert result["fallback_considered"] is False
    assert result["fallback_applied"] is False


def test_fresh_store_trivial_preflight_exposes_steward_without_specialist_hydration(
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
        assert "managers=agency-steward" in result["context"]
        assert result["resident_managers"] == list(RESIDENT_MANAGER_SLUGS)
        assert result["selected_specialists"] == []
        assert result["loaded_specialists"] == []
        assert store.get_specialists_for_session(session_id) == []
        if host == "codex":
            assert "[AGENCY PREFLIGHT]" in result["context"]
            assert "[AGENCY LOADED]" not in result["context"]
        else:
            assert "[Agency resident-steward kernel v2]" in result["context"]


@pytest.mark.parametrize(
    ("host", "adapter_type"),
    (("codex", CodexAdapter), ("claude", ClaudeAdapter)),
)
def test_isolated_trivial_steward_can_finalize_without_child_activation(
    tmp_path: Path,
    host: str,
    adapter_type: type[CodexAdapter] | type[ClaudeAdapter],
) -> None:
    store = _resident_only_store(tmp_path / f"{host}-trivial.db")
    adapter = adapter_type(store=store)
    trace_id = f"{host}-trivial-turn"

    preflight = adapter.build_preflight_context(
        f"{host}-session",
        "ok",
        trace_id=trace_id,
    )

    assert preflight is not None
    assert preflight["resident_managers"] == list(RESIDENT_MANAGER_SLUGS)
    assert preflight["selected_specialists"] == []
    assert preflight["loaded_specialists"] == []
    assert "managers=agency-steward" in preflight["context"]

    finalized = finalize_response(
        "Acknowledged.",
        {"session_id": f"{host}-session", "trace_id": trace_id, "host": host},
        store,
    )

    assert finalized["action"] == "accept"
    assert finalized["missing"] == []
    assert parse_header(finalized["text"])["agencies_loaded"] == ("agency-steward")
    assert store.get_run(trace_id)["status"] == "completed"


@pytest.mark.parametrize(
    ("host", "adapter_type"),
    (("codex", CodexAdapter), ("claude", ClaudeAdapter)),
)
def test_isolated_nontrivial_turn_fails_before_a_generalist_answer(
    tmp_path: Path,
    host: str,
    adapter_type: type[CodexAdapter] | type[ClaudeAdapter],
) -> None:
    store = _resident_only_store(tmp_path / f"{host}-nontrivial.db")
    adapter = adapter_type(store=store)
    trace_id = f"{host}-nontrivial-turn"

    with pytest.raises(RuntimeError, match="no accepted specialist or contractor"):
        adapter.build_preflight_context(
            f"{host}-session",
            "Investigate this unusual request thoroughly and produce a durable implementation.",
            trace_id=trace_id,
        )
    assert store.get_specialists_for_session(f"{host}-session") == []


def test_partial_legacy_roster_preserves_operator_entry_without_a_fallback_write(
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
    assert "managers=agency-steward" in result["context"]
    assert store.get_roster_entry("operator-specialist") == before
    assert store.get_specialist_prompt("operator-specialist")["prompt_body"] == (
        "Preserve this operator-owned prompt."
    )
    assert store.get_roster_entry("agents-orchestrator") is None
    assert store.get_roster_entry("chief-of-staff") is None
