"""The full roster participates in deterministic semantic recall."""

from __future__ import annotations

import operator

import pytest

from agency_runtime.core.selector import semantic_retrieval as subject
from agency_runtime.core.selector.semantic_retrieval import (
    RevisionedCatalog,
    clear_semantic_retrieval_cache,
    retrieve_candidate_union,
    semantic_retrieve,
)


def _agent(slug: str, division: str, capabilities: list[str], **extra):
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "division": division,
        "description": " ".join(capabilities),
        "categories": [division],
        "capabilities": capabilities,
        "task_types": ["analysis"],
        "preferred_when": [],
        "required_tools": [],
        "expected_output_contract": "Evidence-backed result",
        **extra,
    }


def test_semantic_alias_recalls_specialist_without_literal_query_overlap() -> None:
    catalog = [
        _agent("identity-engineer", "security", ["authentication", "authorization"]),
        _agent("technical-writer", "documentation", ["documentation", "editing"]),
    ]

    agents, scores = semantic_retrieve("fix auth boundary", catalog)

    assert [agent["slug"] for agent in agents][:1] == ["identity-engineer"]
    assert scores[0] > 0


def test_candidate_union_has_no_alphabetical_zero_padding() -> None:
    catalog = [
        _agent("alpha", "finance", ["tax planning"]),
        _agent("identity-engineer", "security", ["authentication", "authorization"]),
        _agent("zulu", "marketing", ["campaign planning"]),
    ]

    result = retrieve_candidate_union("repair auth", catalog, limit=3)

    assert result.candidates
    assert result.candidates[0]["slug"] == "identity-engineer"
    assert "alpha" not in [agent["slug"] for agent in result.candidates]
    assert result.full_roster_count == 3


def test_union_adds_bounded_near_neighbor_hard_negative() -> None:
    catalog = [
        _agent("auth-reviewer", "security", ["authentication review"]),
        _agent("network-reviewer", "security", ["network review"]),
        _agent("incident-responder", "security", ["incident coordination"]),
        _agent("writer", "documentation", ["documentation"]),
    ]

    result = retrieve_candidate_union("authentication review", catalog, limit=3)

    assert result.hard_negative_count >= 1
    assert "incident-responder" in [agent["slug"] for agent in result.candidates]
    assert result.scores[-1] == 0.0


def test_catalog_mutation_invalidates_embedding_content_key() -> None:
    clear_semantic_retrieval_cache()
    catalog = [_agent("specialist", "engineering", ["database indexing"])]
    first, _scores = semantic_retrieve("database", catalog)
    assert first

    catalog[0]["capabilities"] = ["visual design"]
    catalog[0]["description"] = "visual design"
    second, _scores = semantic_retrieve("database", catalog)
    assert second == []


def test_revision_cache_still_rejects_mutated_agent_identity() -> None:
    clear_semantic_retrieval_cache()
    catalog = RevisionedCatalog(
        [_agent("specialist", "engineering", ["database indexing"])],
        revision="exact-roster-revision",
    )
    first, _scores = semantic_retrieve("database", catalog)
    assert first

    catalog[0]["slug"] = "different-specialist"
    with pytest.raises(ValueError, match="reused with different agent identities"):
        semantic_retrieve("database", catalog)


def test_sparse_cosine_uses_the_smaller_vector_without_changing_the_score() -> None:
    query = {1: 0.5, 3: 0.25}
    agent = {0: 0.1, 1: 0.4, 2: 0.2, 3: 0.8}

    assert subject._cosine(query, agent) == pytest.approx(0.4)
    assert subject._cosine(agent, query) == pytest.approx(0.4)


def test_compiled_sparse_vectors_remain_immutable() -> None:
    index = subject._catalog_index([_agent("specialist", "engineering", ["database indexing"])])
    vector = index.embeddings[0]
    feature = next(iter(vector))

    with pytest.raises(TypeError):
        operator.setitem(vector, feature, 0.0)


def test_subword_overlap_alone_cannot_manufacture_semantic_signal() -> None:
    catalog = [
        {
            "slug": "technical-writer",
            "name": "Technical Writer",
            "division": "documentation",
            "description": (
                "Writes README files, installation guides, runbooks, changelogs, and release notes."
            ),
            "categories": ["documentation", "writing"],
            "capabilities": [
                "technical writing",
                "editing",
                "documentation structure",
                "release notes",
            ],
            "tool_affinity": ["markdown", "docs"],
        }
    ]

    agents, scores = semantic_retrieve("How do I cook a mushroom risotto?", catalog)

    assert agents == []
    assert scores == []


def test_narrative_only_polyseme_requires_strong_domain_support() -> None:
    catalog = [
        _agent(
            "unreal-technical-artist",
            "game-development",
            [
                "author Unreal materials Niagara and PCG systems",
                "design scalable technical-art pipelines",
            ],
            categories=["game-development", "unreal-engine", "technical-art"],
            expected_output_contract=(
                "A scoped Unreal technical-art change with cook results and profiler captures."
            ),
        )
    ]

    unrelated, unrelated_scores = semantic_retrieve(
        "How do I cook a mushroom risotto?",
        catalog,
    )
    related, related_scores = semantic_retrieve(
        "Diagnose the Unreal cook pipeline",
        catalog,
    )

    assert unrelated == []
    assert unrelated_scores == []
    assert [agent["slug"] for agent in related] == ["unreal-technical-artist"]
    assert related_scores[0] > 0


def test_metadata_value_normalization_is_bounded_and_type_safe() -> None:
    assert subject._values(None) == ()
    assert subject._values("security") == ("security",)
    assert subject._values(["security", "", None]) == ("security",)
    assert subject._values({"security": True}) == ()
    assert set(subject._values({"security", "review"})) == {"security", "review"}
    assert subject._values(b"security") == ("b'security'",)


def test_semantic_retrieval_rejects_invalid_bounds_and_zero_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [_agent("identity-engineer", "security", ["authentication"])]

    assert semantic_retrieve("authentication", catalog, limit=0) == ([], [])
    assert semantic_retrieve("authentication", []) == ([], [])
    assert semantic_retrieve("a and the", catalog) == ([], [])

    monkeypatch.setattr(subject, "MAX_ACTIVE_ROSTER_SIZE", 1)
    with pytest.raises(ValueError, match="catalog cannot contain more than 1 agents"):
        semantic_retrieve("authentication", catalog * 2)


def test_candidate_union_backfills_after_skipping_a_selected_hard_negative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = [
        _agent(
            f"specialist-{index:02d}",
            "shared" if index < 9 else f"other-{index}",
            ["shared capability"],
        )
        for index in range(11)
    ]

    def lexical_retriever(query, candidates, limit):
        del query, limit
        return candidates, [float(len(candidates) - index) for index in range(len(candidates))]

    monkeypatch.setattr(subject, "semantic_retrieve", lambda *_args, **_kwargs: ([], []))

    result = retrieve_candidate_union(
        "shared capability",
        catalog,
        limit=10,
        lexical_retriever=lexical_retriever,
    )

    assert len(result.candidates) == 10
    assert result.hard_negative_count == 1
    assert [agent["slug"] for agent in result.candidates].count("specialist-08") == 1
    assert result.candidates[-1]["slug"] == "specialist-09"

    no_neighbor_catalog = [
        _agent(f"isolated-{index:02d}", f"division-{index:02d}", ["shared capability"])
        for index in range(11)
    ]
    backfilled = retrieve_candidate_union(
        "shared capability",
        no_neighbor_catalog,
        limit=10,
        lexical_retriever=lexical_retriever,
    )

    assert backfilled.hard_negative_count == 0
    assert len(backfilled.candidates) == 10
