---
title: "Align selector fixtures with the traced workforce contract"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, routing, selector, tests, AR-119, green-main]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 45f78cc
short: 45f78cc
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
---

# Worklog detail: test(routing): align selector fixtures with the traced workforce contract

## Purpose

PR #129 widened the routing contract to carry a trace id and a workforce
catalog end to end, and made the turn-intent classifier state-aware about
social greetings. Several test fixtures were not updated with that change,
so four test files failed on merged `main`: `_RouteRequest.__init__()`
raised `missing 2 required positional arguments: 'trace_id' and
'workforce_catalog'`, `fake_plan_and_staff` rejected
`routing_context_fingerprint`, and one assertion expected a pure social
greeting to be meaningful under known-current state.

## Approach

Confirmed production is the intended contract and the tests lagged:

- `_RouteRequest` (selector/pipeline.py) intentionally requires
  `trace_id` and `workforce_catalog`; the single production constructor
  (`_route_request`) supplies both. Adding defaults would silently
  propagate `None` into the workforce receipt thread. Fix the fixtures.
- `plan_and_staff_workforce` accepts `routing_context_fingerprint`
  (defaulted) and the real caller always passes it. Fix the fake's
  signature.
- The classifier classifies "how's it going" as `_PURE_CONVERSATION`
  (a peer of "hello"/"hi"/"good morning"). Under `state_known=True` with
  no pending work, pure social conversation correctly needs no specialist
  (`selection_required=False`). This is corroborated by three passing
  tests (`test_turn_intent` social -> no selection; `test_selector`
  "ok"/"thanks" trivial under state). The lone contradicting expectation
  was stale.

Changes:
- `test_orchestration_refactors._request` and the two `_RouteRequest`
  builds in `test_coverage_final_selection_planning` now pass
  `trace_id="trace"` and a `workforce_catalog` mirroring their `catalog`.
- `test_selector.fake_plan_and_staff` accepts
  `routing_context_fingerprint=""`.
- Dropped the stale `is_trivial("how's it going",
  turn_state={"state_known": True}) is False` assertion, leaving the
  test's stated purpose intact ("whats next", "status", and the no-state
  greeting all stay non-trivial).

## Challenges encountered

- The CI shard summary conflated the `routing_context_fingerprint`
  failure with `test_coverage_final_selection_planning`; the stale fake
  actually lives in `test_selector.py`.
- Had to distinguish test-lag from a genuine regression for the greeting
  case. The three corroborating passing tests settled it: production is
  intended.

## Decisions and alternatives

- Align tests to the traced-workforce contract (ADR-0080, ADR-0083)
  rather than revert production. Reverting would discard the trace
  lineage and versioned-catalog plumbing that AR-119 depends on.
- Rejected: adding defaults to `_RouteRequest`. That weakens invariants.

## Verification

- `pytest tests/test_orchestration_refactors.py tests/test_selector.py
  tests/test_coverage_final_selection_planning.py -q -W error` ->
  **76 passed**.
- `ruff check` + `ruff format --check` clean.

## Follow-ups

- P0c is one slice of the green-main phase. Remaining Phase 0 work:
  workforce-contract fixture alignment + the D1/D2 genuine roster
  regressions; store/schema TEST ALIGN; dashboard/MCP/delegation TEST
  ALIGN (incl. the larger F6 NativeChildAssignment fixture rewrite).
  Tracked under
  [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
  [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md).
