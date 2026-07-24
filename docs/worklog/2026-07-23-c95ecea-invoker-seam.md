---
title: "Add invoker test seam to plan_and_staff_workforce"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, workforce, inference, testing, AR-119, AR-121]
related:
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
supersedes: []
superseded_by: null
type: worklog
commit: c95ecea
short: c95ecea
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
---

# Worklog detail: feat(workforce): add invoker test seam to plan_and_staff_workforce

## Purpose

After the offline-decline pivot (`ee47985`), selection-asserting suites
that run through the full `preflight -> route -> workforce` stack could
only exercise the (now-declining) offline path: `pipeline.route` calls
`plan_and_staff_workforce` without an `invoker=`, so it used the
function-default `invoke_structured_provider_result`, which shells out to
a real CLI and cannot be stubbed. A test seam is needed so those suites
can exercise real inference (or a stub) through the whole stack.

## Approach

Change the `invoker` parameter default on `plan_and_staff_workforce` from
the function-bound `invoke_structured_provider_result` to `None`, and
resolve `None` to the module-global `invoke_structured_provider_result`
at call time. Callers that do not pass an invoker now honor a
monkeypatched `agency_runtime.core.workforce.inference
.invoke_structured_provider_result`.

## Challenges encountered

- Verified (live, against codex-cli 0.145.0) that the inference funnel
  runs end-to-end: recall -> planner (1 call, ~8s, applied) -> recruiter
  nomination -> verify. But it abstains with
  `no_safe_sufficient_team`/`recruiter_abstained` because the model
  returns `selected=[]` and dumps the correct specialists into
  `forbidden`. Root cause is an over-specified nomination contract, not
  the seam; recorded as the next bounded package in the capsule.
- Confirmed the seam resolves a monkeypatched stub (1 call observed)
  and that production behavior is unchanged (None resolves to the same
  default; explicit-invoker callers unaffected).

## Decisions and alternatives

- Resolve-at-call-time (None default) rather than add a config flag or a
  global registry. Minimal, no new production state, and only affects
  testability.

## Verification

- `pytest tests/test_workforce_inference.py -q -W error` -> 45 passed
  (no regression).
- Probe: monkeypatched stub was invoked; live codex call completed.
- `ruff check` + `ruff format --check` clean.

## Follow-ups

- Redesign the nomination contract so the model decides (selected or
  gap) and the runtime verifies; iterate live until inference nominates
  the best specialist or hires. Then convert the 14 selection-asserting
  suites to provider+stub (or live).
