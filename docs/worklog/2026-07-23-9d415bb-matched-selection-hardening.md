---
title: "Worklog: Harden matched workforce selection semantics"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, roster, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 9d415bbd5113bba22e3631618f66b332f487107c
short: 9d415bb
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Harden matched workforce selection semantics

## Purpose

Reconcile the first matched-selection canary's audited incident capability gap
and harden general selection semantics across the 19-case corpus without adding
scenario routes, weakening typed coverage, or converting provider failures into
positive evidence. This commit is the mandatory local recovery boundary after
context telemetry crossed the repository's 50-percent handoff threshold.

## Approach

The roster audit now describes incident response planning, operations,
investigation, and risk analysis and language-server analysis as capabilities
their source contracts actually support. The generated roster remains pinned
to upstream revision `459dce837db3bdfdc4763d3fefd1fd854e73c8f1` with audited
artifact and review hashes.

Compact intent compilation, deterministic fallback, lifecycle ownership, and
staffing verification now normalize several general modeling boundaries exposed
by configured inference: prohibited mutation language is not requested work;
research is a method capability when a subject domain already exists; a domain
misplaced in the capability array is removed only when that exact governed
domain is already declared; acyclic model units are topologically ordered;
assurance artifacts remain distinct; and stackless audited cross-cutting roles
can complement stack owners. Disabled semantic winners retain disclosure even
when safe staffing abstains, and an applied inference plan is no longer
misreported as a provider failure merely because deterministic staffing then
abstains.

The global cold selection budget was predeclared as 15000 ms before corpus
expansion. The one-call fast setting, exact provider/model bindings, parity
checks, and fail-closed malformed-arm behavior remain unchanged.

## Challenges encountered

Configured-provider outputs exposed several legitimate representation variants
and several invalid responses. The general fixes cover only variants whose
meaning is already proved by typed fields. Unknown capabilities, malformed
assignments, unknown disabled shadows, missing model receipts, and timeouts
remain failures.

Bounded Agency runs now produce safe sufficient teams for the incident,
runtime-routing, language-server, PostgreSQL, clinical/legal, finance,
composition, and broad multi-stack cases. The broad Agency arm selected its
exact nine helpful workers, but a paired upstream response was malformed; the
benchmark correctly remained invalid. The full 19-case run was not started
after telemetry reported 40.7 percent context remaining.

## Decisions and alternatives

The incident gap was resolved by audited contract coverage and general plan
semantics, not by recognizing the case text. The latency budget was adjusted
once, globally, before the full corpus based on observed valid cold calls; it
must not be raised after corpus results. Provider variability is retained as
evidence and never scored as comparative lift.

This package still makes no superiority claim. Exact activation, an untouched
corpus with predeclared statistics, and blinded completed-outcome trials remain
separate gates.

## Verification

- 257 compact-intent, inference, staffing, matched-selection,
  selection-safety, upstream-architecture, CLI, contract, and bundled-roster
  tests passed with warnings treated as errors.
- Full `ruff check agency_runtime tests scripts` and
  `ruff format --check agency_runtime tests scripts` passed.
- Metadata, policy availability, worklog-current, documentation, and
  `git diff --check` gates passed; documentation validation covered 284 files.
- The pinned roster rebuilt reproducibly with 263 approved, zero quarantined,
  and zero retired contracts.
- Valid Windows canaries used `codex-subscription` with requested/actual model
  `gpt-5.6-luna`, low reasoning effort, and zero Agency forbidden, ineligible,
  or conflict selections. Recorded Agency latencies included 11272 ms for
  incident containment, 14041.717 ms for language-server indexing, 5469.497 ms
  for PostgreSQL analysis, 8519.167 ms for clinical/legal separation, and
  7938.386 ms for the disabled-winner safe abstention.

The expensive full repository matrix, the full 19-case configured-provider
run, hosted Actions, and publication were intentionally deferred.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) from
this exact recovery commit. Run the full 19-case matched corpus with unchanged
budgets, preserve all parity and model receipts, distinguish Agency selection
defects from provider-arm invalidations, and fix any remaining unsafe or
clearly inferior Agency result before advancing to contractor lifecycle work.
Keep the larger [AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md)
activation, untouched-corpus, outcome, and release gates open.
