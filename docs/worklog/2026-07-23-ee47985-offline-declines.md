---
title: "Offline declines instead of deterministic selection (ADR-0087)"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, workforce, selection, inference, AR-119, AR-121]
related:
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
supersedes: []
superseded_by: null
type: worklog
commit: ee47985
short: ee47985
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
---

# Worklog detail: feat(workforce): offline declines instead of deterministic selection (ADR-0087)

## Purpose

Implement the first runtime slice of ADR-0087: the runtime ships no
deterministic decider. When no inference provider is configured, the
workforce path declines to select a specialist instead of falling back to
the deterministic plan-and-staff decider (whose picks rest on keyword luck
and cannot read intent). This replaces a silent empty/abstained selection
(looked like a bug) with a labeled, honest decline.

## Approach

`plan_and_staff_workforce` (the single runtime entry into workforce
selection) branched on provider availability: with a provider it ran
inference; without one it called `_deterministic_outcome`, which ran
`deterministic_plan_and_staff`. Replace the offline branch with a new
`_declined_outcome` that returns a well-formed
`WorkforceRoutingOutcome(status="declined", inference_mode="declined_no_provider",
abstention_codes=("no_inference_provider",), plan=None, staffing=empty)`.

The deterministic decider (`workforce/fallback.py` plan-and-staff +
`staffing_verifier` verify) is **not deleted**. It survives as a governed
evaluation baseline (evals compare the algorithms) and as the typed recall
stage that feeds inference. Only the runtime's offline dispatch to it is
removed. This keeps the change surgical: one branch point, no cascade
through evals or hiring.

## Challenges encountered

- An earlier attempt to fix the deterministic fallback (deriving
  capabilities from artifact_kind) regressed a green test that pins the
  decider to pick the *optimal* specialist per unit, exposing that the
  decider's "optimality" rested on keyword-luck token overlap. That
  motivated the ADR-0087 pivot: don't try to make the decider good;
  remove it from the runtime.
- The offline decline surfaces to selection-asserting suites (http/mcp/
  delegation preflight tests) as `selected_specialists == []`. These now
  require a configured provider to exercise the inference path — that
  stub-provider wiring is the next work package (WP3), not a regression.

## Decisions and alternatives

- Decline offline rather than ship a deterministic decider or vendor the
  upstream selector as a floor (both rejected in ADR-0087: deterministic
  selection is shit-by-nature at "best for this ask"; the upstream asset
  worth borrowing is the audited pool, not its selector).
- Keep the decider code for evals/hiring rather than delete it in this
  slice, to keep the change surgical and reversible.

## Verification

- `pytest tests/test_workforce_inference.py -q -W error` -> 45 passed
  (the 3 no-provider tests converted to assert the decline).
- `pytest tests/test_workforce_selection_safety.py
  tests/test_workforce_selection_eval.py
  tests/test_workforce_dynamic_hiring.py tests/test_selector.py` -> 73
  passed (these call the decider directly and are unaffected).
- The 14 selection-asserting failures in http/mcp/delegation now surface
  a clean `declined` ([] selection, no crash) — the intended offline
  behavior, awaiting the WP3 stub-provider wiring.
- `ruff check` + `ruff format --check` clean.

## Follow-ups

- WP3: wire the inference-primary funnel with a stub provider so the
  selection-asserting suites exercise real inference (recall -> decide ->
  hire) and pass again. This is where "pick the best specialist for any
  ask, or hire a contractor on a real gap" is proven.
- WP2: close the Codex/Claude child-routing plumbing so unplanned children
  self-route the governed path; add a ZCode adapter as a test harness.
- WP4: green main once the pivot + WP3 land.
