"""Tests for the selector pipeline — token scoring, pre-narrow, work unit detection."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency_runtime.core.selector.cache import cache_get, cache_key, cache_put, clear_cache
from agency_runtime.core.selector.candidate_narrow import pre_narrow, score_agent, tokenize
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.intent_text import (
    affirmative_intent,
    mask_excluded_intent,
)
from agency_runtime.core.selector.pipeline import build_routing_context, is_trivial, refine_query
from agency_runtime.core.selector.policy import detect_actions

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


def test_is_trivial_short():
    assert is_trivial("ok") is True
    assert is_trivial("yes") is True
    assert is_trivial("thanks") is True


def test_is_trivial_meaningful():
    assert is_trivial("Please review the pull request") is False
    assert is_trivial("Fix the authentication bug in the login flow") is False


def test_is_trivial_short_meaningful_not_trivial(monkeypatch):
    """Short messages that carry real intent must not be trivial."""
    monkeypatch.setenv("AGENCY_CONFIG_PATH", "/nonexistent")
    from agency_runtime.core.config import load_config

    load_config(reload=True)
    assert is_trivial("whats next") is False
    assert is_trivial("status") is False
    assert is_trivial("how's it going") is False


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


def test_bundled_companion_policy_skips_gated_default_agents(monkeypatch, tmp_path):
    """DEFAULT agents remain disabled until they exist in an active roster."""
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(tmp_path / "missing.yaml"))
    # Force reload of cached policy
    from agency_runtime.core.selector import policy as policy_mod

    policy_mod._COMPANION_POLICY = None
    policy_mod._POLICY_MTIME = 0.0
    _, companion_ids = detect_actions("anything at all")

    assert "agents-orchestrator" not in companion_ids
    assert "chief-of-staff" not in companion_ids


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
