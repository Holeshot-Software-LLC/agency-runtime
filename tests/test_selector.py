"""Tests for the selector pipeline — token scoring, pre-narrow, work unit detection."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency_runtime.core.selector.candidate_narrow import tokenize, score_agent, pre_narrow
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.pipeline import is_trivial, refine_query
from agency_runtime.core.selector.cache import cache_key, cache_put, cache_get, clear_cache


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
    candidates, scores = pre_narrow("zzz", catalog, limit=3)
    assert len(candidates) == 3


# ─── Domain expansion ───────────────────────────────────────────────


def test_expand_query_conveyor():
    result = expand_query("fix the conveyor pipeline")
    assert "[domain context:" in result
    assert "ci cd pipeline" in result


def test_expand_query_no_match():
    result = expand_query("hello world")
    assert result == "hello world"


# ─── Work unit detection ────────────────────────────────────────────


def test_detect_work_units_single():
    result = detect_work_units("fix the bug in auth.py")
    assert result["count"] == 1
    assert result["delegate"] is False


def test_detect_work_units_numbered_list():
    result = detect_work_units("Please do the following:\n1. Fix the login bug\n2. Update the README\n3. Add tests")
    assert result["count"] >= 2
    assert result["delegate"] is True
    assert result["source"] == "numbered_list"


def test_detect_work_units_boundary_words():
    result = detect_work_units("Fix the login bug in auth.py. Also, update the README file to document the new flow.")
    assert result["count"] >= 2
    assert result["delegate"] is True


def test_detect_work_units_status_query_not_delegated():
    result = detect_work_units("What's the status of the project?")
    assert result["delegate"] is False
    assert result["source"] == "status_query"


def test_detect_work_units_whats_next_not_delegated():
    result = detect_work_units("What's next?")
    assert result["delegate"] is False


# ─── Trivial message detection ─────────────────────────────────────


def test_is_trivial_short():
    assert is_trivial("ok") is True
    assert is_trivial("yes") is True
    assert is_trivial("thanks") is True


def test_is_trivial_meaningful():
    assert is_trivial("Please review the pull request") is False
    assert is_trivial("Fix the authentication bug in the login flow") is False


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
