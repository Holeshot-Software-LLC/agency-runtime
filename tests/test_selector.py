"""Tests for the selector pipeline — token scoring, pre-narrow, work unit detection."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.selector.cache import cache_get, cache_key, cache_put, clear_cache
from agency_runtime.core.selector.candidate_narrow import pre_narrow, score_agent, tokenize
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.intent_text import (
    affirmative_intent,
    mask_excluded_intent,
)
from agency_runtime.core.selector.pipeline import (
    build_route_request,
    build_routing_context,
    is_trivial,
    refine_query,
    route,
)
from agency_runtime.core.selector.policy import detect_actions, detect_fallback_companions
from agency_runtime.core.selector.receipt_projection import project_durable_routing_receipt
from agency_runtime.core.turn_intent import classify_turn_intent
from agency_runtime.core.turn_routing_context import project_turn_routing_context_guard

# ─── Token scoring ──────────────────────────────────────────────────


def test_tokenize_basic():
    tokens = tokenize("code review for python")
    assert "code" in tokens
    assert "review" in tokens
    assert "python" in tokens


def test_tokenize_strips_stopwords():
    tokens = tokenize("help me with code review")
    assert "help" not in tokens
    assert "code" in tokens
    assert "review" in tokens


def test_tokenize_handles_separators():
    tokens = tokenize("code-reviewer senior-developer")
    assert "code" in tokens
    assert "reviewer" in tokens
    assert "senior" in tokens
    assert "developer" in tokens


def test_score_agent_basic():
    agent = {
        "slug": "code-reviewer",
        "name": "Code Reviewer",
        "description": "Reviews code for bugs and quality",
        "division": "engineering",
    }
    query_tokens = tokenize("review code for bugs")
    score = score_agent(agent, query_tokens)
    assert score > 0, "should have non-zero score for matching tokens"


def test_score_agent_no_match():
    agent = {
        "slug": "chef",
        "name": "Chef",
        "description": "Cooks food",
        "division": "kitchen",
    }
    query_tokens = tokenize("code review python")
    score = score_agent(agent, query_tokens)
    assert score == 0.0, "should have zero score for non-matching agent"


def test_repeated_token_values_do_not_multiply_one_field_weight():
    base = {
        "slug": "ui-specialist",
        "name": "UI Specialist",
        "categories": ["design"],
        "capabilities": ["interface design"],
    }
    repeated = {
        **base,
        "capabilities": [
            "interface design",
            "dashboard design",
            "component design",
        ],
    }
    tokens = tokenize("design")

    assert score_agent(repeated, tokens) == score_agent(base, tokens)


def test_pre_narrow_returns_top_candidates():
    catalog = [
        {"slug": "code-reviewer", "name": "Code Reviewer", "description": "Reviews code"},
        {"slug": "chef", "name": "Chef", "description": "Cooks food"},
        {"slug": "senior-developer", "name": "Senior Developer", "description": "Writes code"},
    ]
    candidates, scores = pre_narrow("review code", catalog, limit=2)
    assert len(candidates) <= 2
    assert candidates[0]["slug"] == "code-reviewer"
    assert scores[0] > 0


def test_pre_narrow_pads_when_few_matches():
    catalog = [
        {"slug": "a", "name": "A", "description": "desc a"},
        {"slug": "b", "name": "B", "description": "desc b"},
        {"slug": "c", "name": "C", "description": "desc c"},
    ]
    candidates, _scores = pre_narrow("zzz", catalog, limit=3)
    assert len(candidates) == 3


# ─── Domain expansion ───────────────────────────────────────────────


def test_expand_query_conveyor():
    result = expand_query("fix the conveyor pipeline")
    assert "[domain context:" in result
    assert "ci cd pipeline" in result


def test_expand_query_no_match():
    result = expand_query("hello world")
    assert result == "hello world"


def test_expand_query_requires_complete_domain_terms():
    assert expand_query("slackened validation rules") == "slackened validation rules"
    assert "real-time communication" in expand_query("Configure Slack alerts")


def test_expand_query_routes_agency_runtime_language_to_agent_system_domains():
    expanded = expand_query("Explain the Agency response header, dashboard, and agent selection")

    assert "agent orchestration" in expanded
    assert "specialist routing" in expanded
    assert "specialist compatibility constraints" in expanded
    assert "compatibility analysis" not in expanded
    assert "runtime dashboard" in expanded
    assert "configuration interface" in expanded
    assert "response telemetry" in expanded


def test_affirmative_intent_masks_only_explicit_exclusions():
    message = (
        "Do not redesign the dashboard UI; fix authentication security. The login is not working."
    )
    masked = mask_excluded_intent(message)

    assert len(masked) == len(message)
    assert "dashboard" not in affirmative_intent(message)
    assert "fix authentication security" in affirmative_intent(message)
    assert "not working" in affirmative_intent(message)
    assert "skip tests" in affirmative_intent("Do not skip tests before release")
    assert affirmative_intent("No UI changes, fix the backend") == ", fix the backend"


# ─── Work unit detection ────────────────────────────────────────────


def test_detect_work_units_single():
    result = detect_work_units("fix the bug in auth.py")
    assert result["count"] == 1
    assert result["delegate"] is False


def test_detect_work_units_numbered_list():
    result = detect_work_units(
        "Please do the following:\n1. Fix the login bug\n2. Update the README\n3. Add tests"
    )
    assert result["count"] >= 2
    assert result["delegate"] is True
    assert result["source"] == "numbered_list"


def test_detect_work_units_boundary_words():
    result = detect_work_units(
        "Fix the login bug in auth.py. Also, update the README file to document the new flow."
    )
    assert result["count"] >= 2
    assert result["delegate"] is True


def test_detect_work_units_status_query_not_delegated():
    result = detect_work_units("What's the status of the project?")
    assert result["delegate"] is False
    assert result["source"] == "status_query"


def test_detect_work_units_whats_next_not_delegated():
    result = detect_work_units("What's next?")
    assert result["delegate"] is False


def test_detect_work_units_ignores_explicitly_negated_items():
    result = detect_work_units("1. Do not deploy the service\n2. Update the README")

    assert result["delegate"] is False
    assert result["count"] == 1
    assert result["source"] == "single"


# ─── Trivial message detection ─────────────────────────────────────


def test_legacy_trivial_projection_cannot_authorize_a_no_state_bypass():
    assert is_trivial("ok") is False
    assert is_trivial("yes") is False
    assert is_trivial("thanks") is False
    assert is_trivial("ok", turn_state={"state_known": True}) is True
    assert is_trivial("thanks", turn_state={"state_known": True}) is True


def test_is_trivial_meaningful():
    assert is_trivial("Please review the pull request") is False
    assert is_trivial("Fix the authentication bug in the login flow") is False


def test_is_trivial_short_meaningful_not_trivial(monkeypatch, tmp_path):
    """Short messages that carry real intent must not be trivial."""
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "nonexistent.yaml"))
    from agency_runtime.core.config import load_config

    load_config(reload=True)
    assert is_trivial("whats next") is False
    assert is_trivial("status") is False
    assert is_trivial("how's it going") is False
    # Without pending work, a pure social greeting under confirmed-current
    # state needs no specialist: it is classified as pure conversation and is
    # therefore trivial (mirrors the "ok"/"thanks" case above and the social
    # classification in test_turn_intent). Short actionable messages that do
    # carry intent, such as "whats next" and "status", stay non-trivial.


def test_bundled_companion_policy_finds_coding_defaults(monkeypatch, tmp_path):
    """Force bundled policy by pointing env to a missing file, then reset cache."""
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(tmp_path / "missing-policy.yaml"))
    from agency_runtime.core.selector import policy as policy_mod

    policy_mod._COMPANION_POLICY = None
    policy_mod._POLICY_MTIME = 0.0
    matched_actions, companion_ids = detect_actions("fix the routing bug and add tests")

    assert "CODING" in matched_actions
    assert "senior-developer" in companion_ids
    assert "code-reviewer" in companion_ids
    assert "reality-checker" not in companion_ids


def test_bundled_coding_policy_reserves_reality_checker_for_final_certification(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(tmp_path / "missing-policy.yaml"))
    from agency_runtime.core.selector import policy as policy_mod

    policy_mod._COMPANION_POLICY = None
    policy_mod._POLICY_MTIME = 0.0

    matched_actions, companion_ids = detect_actions(
        "Review this code for final integration certification"
    )
    _ordinary_actions, ordinary_companions = detect_actions("Implement the final integration code")

    assert "CODING" in matched_actions
    assert "reality-checker" in companion_ids
    assert "reality-checker" not in ordinary_companions


def test_bundled_companion_policy_has_no_deterministic_worker_fallback(monkeypatch, tmp_path):
    """DEFAULT never turns deterministic action results into worker selection."""
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(tmp_path / "missing.yaml"))
    # Force reload of cached policy
    from agency_runtime.core.selector import policy as policy_mod

    policy_mod._COMPANION_POLICY = None
    policy_mod._POLICY_MTIME = 0.0
    _, companion_ids = detect_actions("anything at all")

    assert "agents-orchestrator" not in companion_ids
    assert "chief-of-staff" not in companion_ids
    assert detect_fallback_companions() == []


def test_bundled_policy_has_all_broad_actions(monkeypatch, tmp_path):
    """Bundled policy must include all 16 broad actions."""
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(tmp_path / "missing.yaml"))
    from agency_runtime.core.selector import policy as policy_mod

    policy_mod._COMPANION_POLICY = None
    policy_mod._POLICY_MTIME = 0.0
    policy = policy_mod.load_policy()
    expected = {
        "CODING",
        "PERFORMANCE",
        "GITHUB_WRITE",
        "ARCHITECTURE",
        "ORCHESTRATION",
        "DEBUGGING",
        "DEVOPS_INFRA",
        "IDEATION",
        "DOCUMENTATION",
        "SECURITY",
        "TESTING_QA",
        "UI_UX",
        "DATA_ML",
        "BUSINESS",
        "PROJECT_MGMT",
        "DEFAULT",
    }
    found = set(policy.get("actions", {}).keys())
    missing = expected - found
    assert not missing, f"Bundled policy missing actions: {missing}"


def test_routing_context_surfaces_low_confidence_default_agents():
    context = build_routing_context(
        {
            "selected_ids": ["senior-developer", "code-reviewer"],
            "confidence": 0.3,
            "status": "token_fallback",
            "work_units": {"delegate": False, "count": 1},
        }
    )

    assert "Default specialist routing suggestion" in context
    assert "senior-developer, code-reviewer" in context


def test_routing_context_makes_advisory_no_execution_boundary_explicit():
    context = build_routing_context(
        {
            "selected_ids": ["project-shepherd"],
            "confidence": 0.99,
            "status": "accepted",
            "selection_required": True,
            "execution_decision_required": False,
        }
    )

    assert "[AGENCY ADVISORY TURN]" in context
    assert "read-only parent assessment" in context
    assert "Do not infer workspace mutation" in context


def test_workforce_contract_verifier_is_not_regated_by_legacy_catalog(monkeypatch):
    from agency_runtime.core.workforce import inference, routing_projection

    captured = {}

    def fake_plan_and_staff(
        _request,
        _snapshot,
        *,
        config,
        context,
        routing_context_fingerprint="",
        turn_routing_context=None,
        **_kwargs,
    ):
        del config, routing_context_fingerprint, turn_routing_context
        captured["eligible_worker_ids"] = context.eligible_worker_ids
        return SimpleNamespace(attempts=())

    def fake_projection(_outcome, catalog, **_kwargs):
        captured["projected_catalog"] = catalog
        return {
            "selected_ids": ["catalog-only"],
            "semantic_ids": ["catalog-only"],
            "confidence": 0.99,
            "margin": 0.5,
            "status": "accepted",
            "source": "workforce_inference",
            "work_units": {
                "count": 1,
                "units": ["Assess current state and recommend the next step."],
                "delegate": False,
            },
        }

    monkeypatch.setattr(inference, "plan_and_staff_workforce", fake_plan_and_staff)
    monkeypatch.setattr(routing_projection, "project_workforce_routing", fake_projection)
    catalog = [
        {
            "agent_slug": "catalog-only",
            "slug": "catalog-only",
            "name": "Catalog Only",
            "description": "A reasoning specialist",
            "routing_contract_valid": True,
            "required_tools": ["browser"],
        }
    ]
    snapshot = SimpleNamespace(
        generation=7,
        worker_count=1,
        contract_fingerprint="sha256:" + "a" * 64,
    )

    route(
        "workforce-contract-gate",
        "Review this implementation",
        catalog,
        config=AgencyConfig(),
        workforce_snapshot=snapshot,
    )

    assert captured["eligible_worker_ids"] is None
    assert [item["agent_slug"] for item in captured["projected_catalog"]] == ["catalog-only"]


def test_advisory_classification_constrains_workforce_to_read_only_analysis(monkeypatch):
    from agency_runtime.core.selector import pipeline
    from agency_runtime.core.workforce import inference, routing_projection

    captured = {}

    def fake_plan_and_staff(_request, _snapshot, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(attempts=())

    def fake_projection(_outcome, _catalog, **_kwargs):
        return {
            "selected_ids": ["project-shepherd"],
            "semantic_ids": ["project-shepherd"],
            "confidence": 0.99,
            "margin": 0.5,
            "status": "accepted",
            "source": "workforce_inference",
            "work_units": {
                "count": 1,
                "units": ["Assess the current work and recommend the next step."],
                "delegate": False,
            },
            "workforce_unit_descriptors": [
                {
                    "ordinal": 1,
                    "artifact_kind": "analysis",
                    "lifecycle_phase": "discovery",
                    "authority": "advise",
                    "mutation_scope": "read_only",
                }
            ],
            "workforce_unit_bindings": [
                {
                    "selected": ["project-shepherd"],
                    "delivery": "load",
                    "depends_on": [],
                    "mutation_scope": "read_only",
                    "artifact_kind": "analysis",
                }
            ],
            "unit_assignment_agents": [{"slug": "project-shepherd"}],
        }

    def fake_gap_hiring(outcome, request, config, store, snapshot, catalog, **kwargs):
        del request, config, store
        captured["gap_hiring_considered"] = True
        captured["gap_hiring_deferred"] = kwargs["defer_commits"]
        return outcome, snapshot, catalog, []

    monkeypatch.setattr(inference, "plan_and_staff_workforce", fake_plan_and_staff)
    monkeypatch.setattr(routing_projection, "project_workforce_routing", fake_projection)
    monkeypatch.setattr(pipeline, "_run_gap_hiring", fake_gap_hiring)
    snapshot = SimpleNamespace(
        generation=7,
        worker_count=1,
        contract_fingerprint="sha256:" + "a" * 64,
    )
    message = "what's next?"
    classification = classify_turn_intent(message, {"state_known": True})
    turn_context = {
        "context_version": 1,
        "source_trace_id": "prior-work",
        "source_status": "completed",
        "source_turn_kind": "new_intent",
        "specialists": [],
        "workforce_unit_descriptors": [],
        "workforce_subject_hints": {
            "domains": ["software-engineering"],
            "languages": ["python"],
            "frameworks": ["sqlite"],
            "capability_ids": ["technical-analysis"],
            "platforms": ["windows"],
        },
    }

    result = route(
        "advisory-workforce-contract",
        message,
        [
            {
                "agent_slug": "project-shepherd",
                "slug": "project-shepherd",
                "name": "Project Shepherd",
                "description": "Assesses project state and next steps",
                "routing_contract_valid": True,
            }
        ],
        config=AgencyConfig(),
        workforce_snapshot=snapshot,
        turn_classification=classification,
        turn_routing_context=turn_context,
    )

    assert captured["max_planned_units"] == 1
    assert captured["required_planned_artifact_kind"] == "analysis"
    assert captured["turn_routing_context"] == turn_context
    assert captured["gap_hiring_considered"] is True
    assert captured["gap_hiring_deferred"] is False
    assert result["selection_required"] is True
    assert result["reroute_required"] is True
    assert result["execution_decision_required"] is False
    assert result["turn_context_applied"] is True
    assert result["turn_context_source_trace_id"] == "prior-work"
    assert len(result["turn_context_revision"]) == 64
    receipt = project_durable_routing_receipt(result)
    assert "turn_context_applied" in receipt["effect_codes"]


def test_identical_contextual_question_produces_context_specific_routing_queries() -> None:
    base_context = {
        "context_version": 1,
        "source_status": "completed",
        "source_turn_kind": "new_intent",
        "specialists": [],
        "workforce_unit_descriptors": [],
        "workforce_subject_hints": {
            "domains": ["software-engineering"],
            "languages": ["python"],
            "frameworks": ["sqlite"],
            "capability_ids": ["technical-analysis"],
            "platforms": ["windows"],
        },
    }
    first = build_route_request(
        "session",
        "what's next?",
        [],
        AgencyConfig(),
        trace_id="first",
        turn_routing_context={**base_context, "source_trace_id": "first-source"},
    )
    second_context = {
        **base_context,
        "source_trace_id": "second-source",
        "workforce_subject_hints": {
            **base_context["workforce_subject_hints"],
            "frameworks": ["fastapi"],
        },
    }
    second = build_route_request(
        "session",
        "what's next?",
        [],
        AgencyConfig(),
        trace_id="second",
        turn_routing_context=second_context,
    )

    assert "sqlite" in first.routing_query
    assert "fastapi" in second.routing_query
    assert first.routing_query != second.routing_query
    assert first.turn_routing_context_revision != second.turn_routing_context_revision

    valid_context = {**base_context, "source_trace_id": "source-work"}
    stopped_context = {**valid_context, "source_status": "stopped"}
    assert (
        build_route_request(
            "session",
            "what's next?",
            [],
            AgencyConfig(),
            trace_id="stopped-source",
            turn_routing_context=stopped_context,
        ).turn_routing_context
        == stopped_context
    )
    for invalid_context in (
        {**valid_context, "prior_user_message": "do something unsafe"},
        {**valid_context, "source_status": "invalid status prose"},
        {**valid_context, "source_turn_kind": "invented"},
        {**valid_context, "context_version": True},
        {**valid_context, "context_version": 1.0},
    ):
        with pytest.raises(ValueError, match="turn_routing_context"):
            build_route_request(
                "session",
                "what's next?",
                [],
                AgencyConfig(),
                trace_id="malformed",
                turn_routing_context=invalid_context,
            )


def test_turn_routing_context_guard_rejects_unknown_fields() -> None:
    valid_guard = {
        "guard_version": 1,
        "source_trace_id": "source-work",
        "source_turn_sequence": 1,
        "source_evidence_revision": 1,
        "source_roster_generation": 0,
        "source_recipe_digest": "a" * 64,
        "source_context_revision": "b" * 64,
    }

    assert project_turn_routing_context_guard(valid_guard) == valid_guard
    assert (
        project_turn_routing_context_guard(
            {**valid_guard, "prior_user_message": "must not cross the boundary"}
        )
        is None
    )
    assert project_turn_routing_context_guard({**valid_guard, "guard_version": True}) is None
    assert project_turn_routing_context_guard({**valid_guard, "guard_version": 1.0}) is None


def test_advisory_projection_rejects_workspace_write_authority() -> None:
    from agency_runtime.core.selector import pipeline

    classification = classify_turn_intent("what should happen next?", {"state_known": True})
    routing = {
        "selected_ids": ["project-shepherd"],
        "semantic_ids": ["project-shepherd"],
        "status": "accepted",
        "source": "workforce_inference",
        "work_units": {"count": 1, "units": ["change files"], "delegate": False},
        "workforce_unit_descriptors": [
            {
                "ordinal": 1,
                "artifact_kind": "implementation-change",
                "lifecycle_phase": "implementation",
                "authority": "modify",
                "mutation_scope": "workspace_write",
            }
        ],
        "workforce_unit_bindings": [
            {
                "selected": ["project-shepherd"],
                "delivery": "load",
                "depends_on": [],
                "mutation_scope": "workspace_write",
                "artifact_kind": "implementation-change",
            }
        ],
        "unit_assignment_agents": [{"slug": "project-shepherd"}],
    }

    result = pipeline._advisory_projection(routing, classification)

    assert result["status"] == "inference_invalid"
    assert result["source"] == "workforce_inference_failure"
    assert result["selected_ids"] == []
    assert result["work_units"]["delegate"] is False
    assert result["workforce_unit_bindings"] == []
    assert "advisory_contract_invalid" in result["error"]


# ─── Query refinement ───────────────────────────────────────────────


def test_refine_query_strips_urls():
    result = refine_query("Check https://example.com/page for details")
    assert "https://example.com" not in result
    assert "details" in result


def test_refine_query_strips_prefix():
    result = refine_query("Hermes: review this code")
    assert not result.startswith("Hermes")
    assert "review" in result


# ─── Cache ──────────────────────────────────────────────────────────


def test_cache_key_deterministic():
    key1 = cache_key("review code")
    key2 = cache_key("review code")
    assert key1 == key2


def test_cache_key_different():
    key1 = cache_key("review code")
    key2 = cache_key("write tests")
    assert key1 != key2


def test_cache_put_get():
    clear_cache()
    key = cache_key("test query")
    cache_put(key, {"selected_ids": ["code-reviewer"], "confidence": 0.9})
    result = cache_get(key)
    assert result is not None
    assert result["selected_ids"] == ["code-reviewer"]
    assert result.get("cache_hit") is True


def test_cache_miss():
    clear_cache()
    result = cache_get("nonexistent_key")
    assert result is None
