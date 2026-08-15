---
title: "Worklog detail: name the requirement axis a staffing failure could not cover"
status: active
category: worklog
created: 2026-08-15
updated: 2026-08-15
tags: [workforce, staffing, evidence, receipts, recruiter, diagnosis]
related:
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/selector/receipt_projection.py
supersedes: []
superseded_by: null
type: worklog
commit: a75a906fe997b0c370ece28d54ee02357e9bcb16
short: a75a906f
date: 2026-08-15
pr: null
related_issues:
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: name the requirement axis a staffing failure could not cover

## Purpose

`staff_without_safe_team` named the failing unit and nothing else. That is not
enough to act on: the same code covers a recruiter that ranked badly and a
recruiter that was handed a unit no ranking could staff. Separating those took a
day of offline roster arithmetic, and the wrong branch of that fork was
published twice before the right one was found.

## Approach

`_uncoverable_requirement_axis` unions `typed_staffing_coverage` over the whole
roster snapshot and returns the axis of the first requirement nothing covers.
Team sufficiency is conjunctive across the six axes, so one uncovered axis
defeats every possible team.

The result is a fault classifier. **Present**, the plan or the roster is at
fault and no bounded repair can succeed. **Absent**, the roster could have
covered every axis, so the ranking is the recruiter's own mistake — which is
what ADR-0132's funded repair is for.

`REQUIREMENT_AXES` is defined in `staffing_verifier.py` beside the
`_requirements` function that produces the axes, and both `inference.py` and
`receipt_projection.py` import it. `_NOMINATION_FAILURE_CODES` is already
restated in both modules; adding a second such pair would have been the same
mistake twice.

The axis is a closed six-value set carrying no request content, so it crosses
the content-free receipt boundary. The detail string became `unit=code:axis`,
and `project_nomination_failures` projects `requirement_axis` as an optional
third key — optional so existing two-key expectations keep holding — and fails
closed on any value outside the vocabulary, matching the strictness the rest of
that projection already applies.

Naming the axis also makes the funded repair recoverable instead of doomed.
When an axis is uncoverable, the repair prompt states the only honest answer —
declare gap — rather than asking for a faithful ranking that cannot exist.

## Challenges encountered

Editing the `staff_without_safe_team` line broke the
`implicit-staffing-failure-becomes-hiring-gap` mutation, because
`core/evals/decision_conformance.py` stores the **literal source text** of that
line as its `before` snippet. The coupling is invisible from the edit site. Both
were updated in the same commit.

`test_recruiter_repair_declares_gap_when_typed_recall_proves_uncovered_requirements`
failed on the new feedback payload. Reading it showed the test is named for
exactly this scenario — a roster that cannot supply `capability:automation` —
and previously proved the recruiter reached `gap` by inference alone. Its
expectation was updated to the message that now tells it.

A first attempt asserted that a contract with `capability_ids=("review",)`
leaves `capability:analysis` uncovered. It does not: `_supports` matches
capabilities semantically rather than by identity. The assertion was rewritten
to vary the unit's required capability instead.

## Decisions and alternatives

Encoding the axis as a suffix on `reason_code` (`staff_without_safe_team:domain`)
was rejected for the projected output: `_NOMINATION_FAILURE_CODES` is a closed
allowlist, and a compound code would either force every consumer to split it or
silently drop every failure. The wire detail uses the compact form; the
projection splits it into a separate key.

Naming *every* uncoverable axis rather than the first was considered and
dropped. One is enough to classify the fault, and the receipt is deliberately
bounded.

## Verification

- `tests/test_workforce_inference.py`, `tests/test_preflight_failure_diagnosis.py`,
  `tests/test_decision_conformance.py`, `tests/test_routing_correctness.py`,
  `tests/test_workforce_selection_safety.py`,
  `tests/test_workforce_dynamic_hiring.py`,
  `tests/test_workforce_staffing_foundation.py`,
  `tests/test_workforce_intent.py` — 261 passed, 1 skipped, `-W error`.
- CI's fast production spine plus every affected suite — 830 passed, 20 skipped;
  the only failures were the two pre-existing `test_upstream_selection_eval.py`
  cases.
- `scripts/verify_docs.py` — passed for 689 Markdown files.

`agency eval decision-conformance` cannot run its mutation phase on this
workstation. Its sandboxed child dies in ~122 ms with `No module named pytest`
— `least_privilege_subprocess_environment` redirects `HOME`/`APPDATA` away from
the user site-packages where pytest lives — so it reports `status: failed`,
`failed_nodes: 0`, and `killed: 0` of 151. A pristine `origin/main` worktree
reproduces it identically, and GitHub CI is green on `b8a5d5ca`.

Because the mutation proof could not run here, the edited `before` snippet was
verified directly instead: every one of the 151 snippets still matches its
source file exactly once.

## Follow-ups

- `eval decision-conformance` has no way to point its sandboxed child at a
  usable interpreter, so the mutation proof cannot be run before pushing on any
  machine whose pytest lives in user site-packages.
  ([AR-119](../roadmap/issue-AR-119-inference-first-workforce.md))
- The next live Claude canary is still the real test of the plan-boundary fix
  this axis work accompanies.
  ([AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md))
