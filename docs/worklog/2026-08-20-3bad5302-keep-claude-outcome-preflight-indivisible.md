---
title: "Worklog detail: Keep Claude outcome preflight indivisible"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [canary, claude, outcomes, inference, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
supersedes: []
superseded_by: null
type: worklog
commit: 3bad53028b0447b5316e2077d5b00ad89506d096
short: 3bad5302
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
---

# Worklog detail: Keep Claude outcome preflight indivisible

## Purpose

Keep the isolated accepted-outcome canary inside the parent planner's existing
single-work-unit path before spending another live Claude draw.

## Approach

The exact merged-main prompt measured 2,316 characters but did not satisfy
`_explicit_indivisible_unit_request`. The canary-only preamble now declares
the producer/verifier sequence to be exactly one indivisible work unit and
forbids splitting or decomposition. The resulting 2,367-character prompt
satisfies the same production detector before workforce inference runs.

One regression asserts that the complete generated prompt remains inside that
path. The change does not alter provider selection, model profiles, ordinary
turns, the accepted-outcome Store contract, or global configuration.

## Challenges encountered

The first fast-harness attempt reached pytest but the managed sandbox refused
the repository's attested private scratch boundary. The identical local harness
was rerun outside that sandbox boundary and passed; this was an execution-
environment refusal, not a failing product assertion.

## Decisions and alternatives

The repair shapes only this fixed canary prompt. Changing the Claude planner
profile, provider order, child-judge pin, or the general indivisible detector
would have changed ordinary-turn or provider behavior without evidence that
such a broader change was needed.

The prior live failure remains authoritative. Passing the detector locally is a
falsifiable repair candidate, not proof that the next provider invocation will
staff or produce verified child artifacts.

## Verification

- Exact accepted-outcome prompt tests: 11 passed.
- Widened accepted-outcome, collector, activation-contract, and workforce-
  inference surface: 102 passed.
- Ruff lint and format checks passed for the changed code and test.
- Local fast harness: 12/12 gates in 1.3 minutes, including 161 workflow
  contracts, 151 mutation snippets, and 134 dashboard tests.
- Metadata, policy, worklog-currentness, `git diff --check`, and 711-file
  documentation validation passed.
- No provider call, accepted outcome, attestation, promotion, candidate advance,
  or matrix change occurred.

## Follow-ups

- Obtain fresh owner authority before push, PR, merge, exact-main installation,
  or one bounded Claude accepted-outcome falsification draw.
- If that draw staffs, continue AR-252's verified-outcome and automatic-
  promotion evidence. If it does not, preserve the new exact parent boundary
  and diagnose the next deterministic failure without changing the pin.
