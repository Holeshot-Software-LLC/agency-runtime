"""Bounded, identity-free cases for the packaged-roster contract evaluation.

These prompts are deliberately phrased as user needs rather than specialist
names.  They exercise retrieval and ordering; they are not model-output or
task-outcome evidence.
"""

from __future__ import annotations

from typing import Final

RETRIEVAL_CASES: Final[tuple[dict[str, object], ...]] = (
    {
        "id": "direct-independent-code-review",
        "kind": "direct",
        "query": (
            "Inspect this supplied patch for correctness regressions, security "
            "defects, and maintainability risks. Rank only evidence-backed findings."
        ),
        "required": ("code-reviewer",),
        "forbidden_above_required": ("technical-writer",),
        "max_required_rank": 10,
    },
    {
        "id": "silent-failure-review",
        "kind": "direct",
        "query": (
            "Review this change's error handling for swallowed exceptions, fallbacks "
            "that hide failures from callers, and lost stack traces. Report located, "
            "rated findings only; do not implement fixes."
        ),
        "required": ("silent-failure-hunter",),
        "forbidden_above_required": ("technical-writer",),
        "max_required_rank": 10,
    },
    {
        "id": "type-design-review",
        "kind": "direct",
        "query": (
            "Score the type design in this module: encapsulation, whether the "
            "invariants keep illegal states unrepresentable, and where escape "
            "hatches bypass enforcement. Findings only; do not change the types."
        ),
        "required": ("type-design-analyzer",),
        "forbidden_above_required": ("technical-writer",),
        "max_required_rank": 10,
    },
    {
        "id": "short-auth-repair",
        "kind": "short_indirect",
        "query": "fix auth",
        "required": ("application-security-engineer",),
        "forbidden_above_required": (),
        "max_required_rank": 16,
    },
    {
        "id": "indirect-release-pipeline",
        "kind": "indirect",
        "query": (
            "The release pipeline fails after signed artifacts are handed off. "
            "Trace the automation failure and make the delivery path repeatable."
        ),
        "required": ("devops-automator",),
        "forbidden_above_required": (),
        "max_required_rank": 10,
    },
    {
        "id": "ambiguous-accessibility-neighbor",
        "kind": "near_neighbor_hard_negative",
        "query": (
            "Review an existing interface for keyboard focus, screen-reader "
            "announcements, and WCAG barriers; do not redesign the visual system."
        ),
        "required": ("accessibility-auditor",),
        "forbidden_above_required": ("ui-designer",),
        "max_required_rank": 10,
    },
    {
        "id": "incident-not-offensive-testing",
        "kind": "negated_near_neighbor",
        "query": (
            "Contain an active breach and preserve forensic evidence. Do not probe "
            "the live target offensively; produce a reversible recovery plan."
        ),
        "required": ("incident-responder",),
        "forbidden_above_required": ("penetration-tester",),
        "max_required_rank": 10,
    },
    {
        "id": "multi-intent-accessibility-performance",
        "kind": "multi_intent",
        "query": (
            "Audit keyboard and screen-reader barriers, then design a bounded "
            "latency and throughput benchmark for the same product surface."
        ),
        "required": ("accessibility-auditor", "performance-benchmarker"),
        "forbidden_above_required": (),
        "max_required_rank": 10,
    },
    {
        "id": "out-of-domain-abstention",
        "kind": "no_match",
        "query": "Which quasar is brightest above my backyard tonight?",
        "required": (),
        "forbidden_above_required": (),
        "max_required_rank": 0,
        "abstain": True,
    },
)

COMPATIBILITY_CASES: Final[tuple[dict[str, object], ...]] = (
    {
        "id": "explicit-conflict-rejected",
        "requested": (
            "application-security-engineer",
            "ai-generated-code-security-auditor",
        ),
        "expected_selected": ("application-security-engineer",),
        "expected_added": (),
        "expected_rejected": ("ai-generated-code-security-auditor",),
        "expected_separate_pair": (),
    },
    {
        "id": "requirement-closure-is-dependency-first",
        "requested": ("ui-designer",),
        "expected_selected": ("accessibility-auditor", "ui-designer"),
        "expected_added": ("accessibility-auditor",),
        "expected_rejected": (),
        "expected_separate_pair": ("accessibility-auditor", "ui-designer"),
    },
    {
        "id": "modifier-and-reviewer-use-separate-contexts",
        "requested": ("technical-writer", "code-reviewer"),
        "expected_selected": ("technical-writer", "code-reviewer"),
        "expected_added": (),
        "expected_rejected": (),
        "expected_separate_pair": ("technical-writer", "code-reviewer"),
    },
    {
        "id": "independent-review-domains-remain-compatible",
        "requested": ("accessibility-auditor", "performance-benchmarker"),
        "expected_selected": ("accessibility-auditor", "performance-benchmarker"),
        "expected_added": (),
        "expected_rejected": (),
        "expected_separate_pair": (
            "accessibility-auditor",
            "performance-benchmarker",
        ),
    },
)

TURN_CASES: Final[tuple[dict[str, object], ...]] = (
    {
        "id": "pure-acknowledgement-with-current-empty-state",
        "message": "thanks",
        "state": {"state_known": True, "state_status": "current"},
        "turn_kind": "acknowledgement",
        "selection_required": False,
        "reroute_required": False,
    },
    {
        "id": "acknowledgement-cannot-bypass-active-plan",
        "message": "thanks",
        "state": {
            "state_known": True,
            "state_status": "current",
            "previous_trace_id": "trace-active",
            "previous_status": "open",
            "previous_turn_kind": "new_intent",
            "active_plan": True,
        },
        "turn_kind": "continuation",
        "selection_required": True,
        "reroute_required": False,
    },
    {
        "id": "yes-grants-pending-authorization",
        "message": "yes",
        "state": {
            "state_known": True,
            "state_status": "current",
            "previous_trace_id": "trace-auth",
            "previous_status": "open",
            "previous_turn_kind": "new_intent",
            "pending_authorization": True,
        },
        "turn_kind": "continuation",
        "selection_required": True,
        "reroute_required": True,
    },
    {
        "id": "continue-resumes-active-work",
        "message": "continue",
        "state": {
            "state_known": True,
            "state_status": "current",
            "previous_trace_id": "trace-plan",
            "previous_status": "open",
            "previous_turn_kind": "new_intent",
            "unfinished_work": True,
        },
        "turn_kind": "continuation",
        "selection_required": True,
        "reroute_required": False,
    },
    {
        "id": "ship-it-is-contextual-mutation",
        "message": "ship it",
        "state": {
            "state_known": True,
            "state_status": "current",
            "previous_trace_id": "trace-release",
            "previous_status": "open",
            "previous_turn_kind": "new_intent",
            "pending_question": True,
        },
        "turn_kind": "continuation",
        "selection_required": True,
        "reroute_required": True,
    },
    {
        "id": "go-without-trusted-state-reroutes",
        "message": "go",
        "state": None,
        "turn_kind": "new_intent",
        "selection_required": True,
        "reroute_required": True,
    },
    {
        "id": "constraint-change-is-revision",
        "message": "no, Windows too",
        "state": {
            "state_known": True,
            "state_status": "current",
            "previous_trace_id": "trace-revision",
            "previous_status": "open",
            "previous_turn_kind": "new_intent",
            "active_plan": True,
        },
        "turn_kind": "revision",
        "selection_required": True,
        "reroute_required": True,
    },
    {
        "id": "exact-control-uses-control-path",
        "message": "agency status",
        "state": None,
        "turn_kind": "control",
        "selection_required": False,
        "reroute_required": False,
    },
)

__all__ = ["COMPATIBILITY_CASES", "RETRIEVAL_CASES", "TURN_CASES"]
