"""Compatible-set routing is deterministic and fail-closed."""

from __future__ import annotations

import hashlib

from agency_runtime.core.config import AgencyConfig, JudgeConfig
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector.compatibility import (
    enforce_compatible_set,
    filter_eligible_catalog,
)
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent


def _agent(slug: str, **overrides):
    return {
        "slug": slug,
        "audit_status": "approved",
        "routing_contract_valid": True,
        "supported_hosts": ["codex", "claude"],
        "supported_platforms": ["windows", "linux"],
        "required_tools": [],
        "requires": [],
        "conflicts_with": [],
        "authority": "advise",
        "context_mode": "direct_safe",
        "independence_group": slug,
        **overrides,
    }


def _policy(*companions: str) -> dict[str, object]:
    return {
        "actions": {
            "CODING": {
                "triggers": ["implement"],
                "always_include": [
                    {"slug": slug, "reason": "bounded test companion"} for slug in companions
                ],
                "conditional": [],
            }
        },
        "division_anchors": {},
        "specialist_availability": {
            "schema_version": 1,
            "enabled": list(companions),
            "roster_gated": {"reason": "not active", "slugs": []},
        },
    }


def _codex_receipt(session_id: str):
    return native_adapter_capability_receipt(
        "codex",
        platform="windows",
        session_id=session_id,
        trace_id="route",
    )


def test_hard_filter_rejects_audit_host_platform_and_tool_mismatches() -> None:
    catalog = [
        _agent("good", required_tools=["source"]),
        _agent("quarantined", audit_status="quarantined"),
        _agent(
            "linux-only",
            supported_platforms=["linux"],
            required_tools=["source"],
        ),
        _agent("openclaw-only", supported_hosts=["openclaw"]),
        _agent("needs-shell", required_tools=["shell"]),
    ]

    result = filter_eligible_catalog(
        catalog,
        host="codex",
        platform="windows",
        available_tools={"source"},
    )

    assert [item["slug"] for item in result.eligible] == ["good"]
    assert {item["slug"] for item in result.rejected} == {
        "quarantined",
        "linux-only",
        "openclaw-only",
        "needs-shell",
    }


def test_compatible_set_adds_requirements_and_rejects_explicit_conflicts() -> None:
    catalog = [
        _agent("implementer", requires=["architect"], authority="modify"),
        _agent("architect", authority="plan"),
        _agent("reviewer", conflicts_with=["implementer"], authority="review"),
    ]

    result = enforce_compatible_set(
        ["implementer", "reviewer"],
        catalog,
    )

    assert result["selected_ids"] == ["architect", "implementer"]
    assert result["added_requirements"] == ["architect"]
    assert result["rejected"] == [{"slug": "reviewer", "reason": "conflicts_with:implementer"}]


def test_required_closure_does_not_consume_the_requested_specialist_budget() -> None:
    catalog = [
        _agent("implementer", requires=["architect"], authority="modify"),
        _agent("architect", authority="plan"),
        _agent("optional", authority="advise"),
    ]

    result = enforce_compatible_set(
        ["implementer", "optional"],
        catalog,
        limit=1,
    )

    assert result["selection_limit"] == 1
    assert result["selected_ids"] == ["architect", "implementer"]
    assert result["selected_root_ids"] == ["implementer"]
    assert result["added_requirements"] == ["architect"]
    assert result["rejected"] == [{"slug": "optional", "reason": "compatible_set_limit"}]


def test_explicitly_proposed_dependency_still_does_not_consume_root_budget() -> None:
    catalog = [
        _agent("implementer", requires=["architect"], authority="modify"),
        _agent("architect", authority="plan"),
    ]

    result = enforce_compatible_set(
        ["architect", "implementer"],
        catalog,
        limit=1,
    )

    assert result["selected_ids"] == ["architect", "implementer"]
    assert result["selected_root_ids"] == ["implementer"]
    assert result["added_requirements"] == []
    assert result["rejected"] == []


def test_rejected_root_does_not_leave_a_dependency_that_blocks_later_work() -> None:
    catalog = [
        _agent("blocker"),
        _agent("doomed", requires=["helper"], conflicts_with=["blocker"]),
        _agent("helper"),
        _agent("alternative", conflicts_with=["helper"]),
    ]

    result = enforce_compatible_set(
        ["blocker", "doomed", "alternative"],
        catalog,
        limit=2,
    )

    assert result["selected_ids"] == ["blocker", "alternative"]
    assert result["selected_root_ids"] == ["blocker", "alternative"]
    assert result["added_requirements"] == []
    assert result["rejected"] == [{"slug": "doomed", "reason": "conflicts_with:blocker"}]


def test_shared_and_repeated_requirements_are_resolved_once() -> None:
    catalog = [
        _agent("first", requires=["left", "right"]),
        _agent("second", requires=["right"]),
        _agent("left", requires=["shared"]),
        _agent("right", requires=["shared"]),
        _agent("shared"),
    ]

    result = enforce_compatible_set(["first", "second"], catalog, limit=2)

    assert result["selected_ids"] == ["shared", "left", "right", "first", "second"]
    assert result["selected_root_ids"] == ["first", "second"]
    assert result["added_requirements"] == ["shared", "left", "right"]
    assert result["rejected"] == []


def test_requirement_closure_cannot_exceed_absolute_safety_bound() -> None:
    dependencies = [f"dependency-{index}" for index in range(16)]
    catalog = [
        _agent("root", requires=dependencies),
        *[_agent(slug) for slug in dependencies],
    ]

    result = enforce_compatible_set(["root"], catalog, limit=16)

    assert result["selected_ids"] == []
    assert result["selected_root_ids"] == []
    assert result["added_requirements"] == []
    assert result["rejected"] == [{"slug": "root", "reason": "compatible_set_limit"}]


def test_only_an_explicit_separated_reviewer_may_overflow_the_budget() -> None:
    catalog = [
        _agent("builder", authority="modify", independence_group="auth"),
        _agent(
            "reviewer",
            authority="review",
            context_mode="isolated_only",
            independence_group="review",
        ),
    ]

    bounded = enforce_compatible_set(["builder", "reviewer"], catalog, limit=1)
    explicit_review = enforce_compatible_set(
        ["builder", "reviewer"],
        catalog,
        limit=1,
        review_overflow_ids=["reviewer"],
    )

    assert bounded["selected_ids"] == ["builder"]
    assert bounded["overflow_review_ids"] == []
    assert bounded["rejected"] == [{"slug": "reviewer", "reason": "compatible_set_limit"}]
    assert explicit_review["selected_ids"] == ["builder", "reviewer"]
    assert explicit_review["overflow_review_ids"] == ["reviewer"]
    assert explicit_review["separate_context_pairs"] == [["builder", "reviewer"]]


def test_modify_and_review_are_kept_but_forced_into_separate_contexts() -> None:
    catalog = [
        _agent("builder", authority="modify", independence_group="auth"),
        _agent("reviewer", authority="review", independence_group="auth"),
    ]

    result = enforce_compatible_set(["builder", "reviewer"], catalog)

    assert result["selected_ids"] == ["builder", "reviewer"]
    assert result["separate_context_pairs"] == [["builder", "reviewer"]]


def test_missing_requirement_and_cycles_fail_closed() -> None:
    missing = enforce_compatible_set(
        ["dependent"],
        [_agent("dependent", requires=["absent"])],
    )
    assert missing["selected_ids"] == []
    assert missing["rejected"] == [{"slug": "dependent", "reason": "missing_requirement:absent"}]

    cycle = enforce_compatible_set(
        ["a"],
        [_agent("a", requires=["b"]), _agent("b", requires=["a"])],
    )
    assert cycle["selected_ids"] == []
    assert cycle["rejected"][0]["reason"].startswith("requirement_cycle:")


def test_pipeline_filters_before_inference_and_enforces_returned_set(monkeypatch) -> None:
    catalog = [
        _agent("builder", authority="modify", independence_group="auth"),
        _agent(
            "reviewer",
            authority="review",
            independence_group="review",
            conflicts_with=["builder"],
        ),
        _agent(
            "linux-only",
            supported_platforms=["linux"],
            required_tools=["source"],
        ),
    ]
    observed: list[str] = []

    def fake_judge(_task, candidates, **_kwargs):
        observed.extend(item["slug"] for item in candidates)
        return {
            "selected_ids": ["builder", "reviewer"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
        }

    monkeypatch.setattr(pipeline, "query_judge", fake_judge)
    result = pipeline.route(
        "session",
        "Implement and independently review authentication",
        catalog,
        config=AgencyConfig(),
        host="codex",
        platform="windows",
        capability_receipt=_codex_receipt("session"),
    )

    assert observed == ["builder", "reviewer"]
    assert result["semantic_ids"] == ["builder"]
    assert result["compatibility"]["rejected"] == [
        {"slug": "reviewer", "reason": "conflicts_with:builder"}
    ]
    assert result["eligibility_rejections"] == [
        {"slug": "linux-only", "reason": "unsupported_tool_platform:windows"}
    ]


def test_pipeline_caps_semantic_plus_policy_companions_at_configured_max(
    monkeypatch,
) -> None:
    catalog = [
        _agent("domain-primary"),
        _agent("domain-secondary"),
        _agent("code-reviewer", authority="review", context_mode="isolated_only"),
        _agent("senior-developer", authority="modify"),
    ]
    monkeypatch.setattr(
        pipeline,
        "load_policy",
        lambda *_args: _policy(
            "code-reviewer",
            "senior-developer",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["domain-primary", "domain-secondary"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
        },
    )

    result = pipeline.route(
        "bounded-policy",
        "Implement the domain change",
        catalog,
        config=AgencyConfig(judge=JudgeConfig(max_selected=2)),
        host="codex",
        platform="windows",
        capability_receipt=_codex_receipt("bounded-policy"),
    )

    assert result["selected_ids"] == ["domain-primary", "domain-secondary"]
    assert result["semantic_ids"] == ["domain-primary", "domain-secondary"]
    assert result["selected_companion_ids"] == []
    assert result["compatibility"]["selection_limit"] == 2
    assert result["compatibility"]["rejected"] == [
        {"slug": "code-reviewer", "reason": "compatible_set_limit"},
        {"slug": "senior-developer", "reason": "compatible_set_limit"},
    ]


def test_versioned_compatibility_receipt_proves_only_current_exact_hits() -> None:
    catalog = [_agent("primary"), _agent("manager")]
    config = AgencyConfig(judge=JudgeConfig(max_selected=1))
    request = pipeline._RouteRequest(
        session_id="receipt",
        user_message="work",
        catalog=catalog,
        config=config,
        policy={},
        context_fingerprint="fingerprint",
        routing_query="work",
        cache_key="key",
        source_message_hash="hash",
        active_ids=frozenset({"primary", "manager"}),
    )
    receipt = enforce_compatible_set(["primary"], catalog, limit=1)
    current = {
        "selected_ids": ["primary"],
        "compatibility": receipt,
    }

    assert pipeline._compatibility_projection_is_current(current, request) is True
    assert pipeline._compatibility_projection_is_current({}, request) is False
    assert (
        pipeline._compatibility_projection_is_current(
            {**current, "compatibility": {**receipt, "contract_version": 0}},
            request,
        )
        is False
    )
    assert (
        pipeline._compatibility_projection_is_current(
            {**current, "compatibility": {**receipt, "selection_limit": 2}},
            request,
        )
        is False
    )

    fallback = {
        "selected_ids": ["manager"],
        "fallback_applied": True,
        "fallback_companion_ids": ["manager"],
        "compatibility": enforce_compatible_set([], catalog, limit=1),
    }
    assert pipeline._compatibility_projection_is_current(fallback, request) is True
    assert (
        pipeline._compatibility_projection_is_current(
            {**fallback, "fallback_companion_ids": ["other"]},
            request,
        )
        is False
    )


def test_pipeline_keeps_required_dependency_beyond_configured_root_max(
    monkeypatch,
) -> None:
    catalog = [
        _agent("implementer", requires=["architect"], authority="modify"),
        _agent("architect", authority="plan"),
    ]
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: _policy())
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["implementer"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
        },
    )

    result = pipeline.route(
        "dependency-closure",
        "Implement the dependency-aware change",
        catalog,
        config=AgencyConfig(judge=JudgeConfig(max_selected=1)),
        host="codex",
        platform="windows",
    )

    assert result["selected_ids"] == ["architect", "implementer"]
    assert result["semantic_ids"] == ["implementer"]
    assert result["compatibility"]["selection_limit"] == 1
    assert result["compatibility"]["selected_root_ids"] == ["implementer"]
    assert result["compatibility"]["added_requirements"] == ["architect"]


def test_exact_cache_hit_is_reprojected_under_current_selection_budget(
    monkeypatch,
) -> None:
    catalog = [
        _agent("domain-primary"),
        _agent("code-reviewer"),
        _agent("senior-developer"),
    ]
    message = "continue"
    policy = _policy("code-reviewer", "senior-developer")
    policy["actions"]["CODING"]["triggers"] = ["continue"]  # type: ignore[index]
    monkeypatch.setattr(
        pipeline,
        "load_policy",
        lambda *_args: policy,
    )
    monkeypatch.setattr(
        pipeline,
        "cache_get",
        lambda _key: {
            "selected_ids": ["domain-primary", "code-reviewer", "senior-developer"],
            "semantic_ids": ["domain-primary"],
            "available_companion_ids": ["code-reviewer", "senior-developer"],
            "source_message_hash": hashlib.sha256(message.encode("utf-8")).hexdigest(),
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
            "cache_hit": True,
        },
    )

    def fail_judge(*_args, **_kwargs):
        raise AssertionError("an exact reusable route must not call the judge")

    monkeypatch.setattr(pipeline, "query_judge", fail_judge)
    continuation = classify_turn_intent(
        message,
        TurnState(
            previous_trace_id="prior-trace",
            state_known=True,
            state_status="current",
            previous_status="active",
            previous_turn_kind="new_intent",
            active_plan=True,
        ),
    )

    result = pipeline.route(
        "bounded-cache",
        message,
        catalog,
        config=AgencyConfig(judge=JudgeConfig(max_selected=1)),
        turn_classification=continuation,
        host="codex",
        platform="windows",
        capability_receipt=_codex_receipt("bounded-cache"),
    )

    assert result["cache_hit"] is True
    assert result["selected_ids"] == ["domain-primary"]
    assert result["semantic_ids"] == ["domain-primary"]
    assert result["selected_companion_ids"] == []
    assert result["compatibility"]["selection_limit"] == 1
    assert result["compatibility"]["rejected"] == [
        {"slug": "code-reviewer", "reason": "compatible_set_limit"},
        {"slug": "senior-developer", "reason": "compatible_set_limit"},
    ]


def test_pipeline_allows_one_explicit_review_companion_in_a_separate_context(
    monkeypatch,
) -> None:
    catalog = [
        _agent("builder", authority="modify", independence_group="auth"),
        _agent(
            "code-reviewer",
            authority="review",
            context_mode="isolated_only",
            independence_group="review",
        ),
    ]
    monkeypatch.setattr(pipeline, "load_policy", lambda *_args: _policy("code-reviewer"))
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["builder"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
        },
    )
    config = AgencyConfig(judge=JudgeConfig(max_selected=1))

    explicit = pipeline.route(
        "explicit-review",
        "Implement and independently review the change",
        catalog,
        config=config,
        host="codex",
        platform="windows",
        capability_receipt=_codex_receipt("explicit-review"),
    )
    negated = pipeline.route(
        "negated-review",
        "Implement the change but do not review it",
        catalog,
        config=config,
        host="codex",
        platform="windows",
        capability_receipt=_codex_receipt("negated-review"),
    )

    assert explicit["selected_ids"] == ["builder", "code-reviewer"]
    assert explicit["selected_companion_ids"] == ["code-reviewer"]
    assert explicit["compatibility"]["overflow_review_ids"] == ["code-reviewer"]
    assert explicit["compatibility"]["separate_context_pairs"] == [["builder", "code-reviewer"]]
    assert negated["selected_ids"] == ["builder"]
    assert negated["selected_companion_ids"] == []
