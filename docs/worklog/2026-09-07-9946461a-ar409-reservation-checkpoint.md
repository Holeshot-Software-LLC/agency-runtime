---
title: "Reserve mandatory stages within owner budgets (AR-409)"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, budgets, reliability]
related:
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/roadmap/acceptance/issue-AR-409.md
  - docs/roadmap/handoffs/issue-AR-409.md
  - docs/decisions/0235-reserve-required-staffing-calls-before-optional-work.md
supersedes: []
superseded_by: null
type: worklog
commit: 9946461a96007eda1ca06830121c4a29edeb2ea7
short: 9946461a
date: 2026-09-07
pr: null
related_issues: [docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md]
---

# Worklog detail: Reserve mandatory stages within owner budgets (AR-409)

## Purpose

Keep optional subject attempts and early repairs from consuming calls required
for later staffing stages under the unchanged owner-configured envelope.

## Approach

Use the same ledger with downstream floors: subject 2+C, planner 1+C,
recruiter C and critic zero, where C is one only in strict mode. Cap actual
subject calls at one across the provider chain, refunding only pre-request
refusals. Preserve validation, strict review, cached-stage admission order and
all default and explicit budgets. Retain the exact budget-refusal cause when
otherwise lost in durable failed staffing.

## Challenges encountered

Independent review found an early floor refusal could retain only a generic
unavailable reason. The bounded fix appends the closed budget cause without
changing status or losing existing verifier reasons; real Store regressions
cover zero-call and recruiter-reservation failure. The evidence record retains
initial red tests, setup/import errors and conformance fixture failures.

## Decisions and alternatives

ADR-0235 supplements ADR-0132/0197. Do not enlarge owner caps or bypass the
critic. Subject plus both repairs and critic requires six calls, not five;
future cache/gap reservations may conservatively abstain sooner. No paired
live model-quality or end-to-end latency equivalence is claimed.

## Verification

Recorded evidence includes 532 passed/1 skipped/3 Windows deselected before
the receipt refinement, 201 passed afterward, independent 134 passed/1 Windows
deselected and final receipt recheck 62 passed. Full 188-mutation conformance
passed before the receipt refinement; the fresh five-mutation subset killed
all four new anchors and the existing default-budget control afterward.
Routing passed all 39 gates; focused Ruff/format checks passed.
After integration through d28ccc23 the final related command again passed
201 tests in 3.05s. Metadata checked 1242 Markdown files; diff checks passed.

## Follow-ups

Integrate AR-408, adapt its now-obsolete current-flow reproduction to the actual
exhausted-critic boundary, freeze the combined acceptance candidate, obtain
isolated verdicts, and let the parent install/live-check and publish it.
This checkpoint is branch-only and not accepted or installed.

Normal integration `f670e6b5` incorporates accepted AR-408 checkpoint `ae916dd1`,
preserves both runtime corrections and adapts two receipt fixtures without
rewriting the accepted historical snapshot. Combined verification: 210 focused
passes in 3.89s, named production spine 1085 passes/3 skips in 69.50s, five
targeted mutation kills with unchanged source, routing passed, Ruff/format
passed. Acceptance freeze and installed delivery remain pending.

Freeze `51909ae8` binds acceptance to combined candidate `f670e6b5` and its
ledger `2236d996`. Bounded excerpt audit included every cited row for all five
criteria (5/5, 5/5, 5/5, 6/6 and 5/5 excerpts, each below the 32KiB budget).
Documentation validation passed for 1251 Markdown files. Isolated judgments
and installed delivery remain subsequent work.

Execution note `70009cd7` preserves the first all-five verifier invocation's
five unavailable results and no recorded verdicts. Exact local namespace
checks found the Claude package/bin directories group-writable (0775); one
authorized nonrecursive `chmod g-w` restored 0755 and usable authenticated
CLI 2.1.263. Source bytes, credentials and trust guards were unchanged; the
actor that changed the modes is unknown. One same-candidate retry is next.

Normal merge `2c5ee2b9` integrates main `f408b6f2` after accepted AR-189
publication. All incoming records and its new uninstall regression are retained.
The complete `agency_runtime` tree is unchanged from artifact source `51909ae8`;
the AR-409 candidate and isolated evidence digests remain unchanged.

Checkpoint `985769e6` retains four satisfied single-criterion judgments. The
second pass's fifth criterion produced no judgment after the same executable
namespace became group-writable during the run (00:08:07/08Z mtimes). No
adverse verdict was changed or completed criterion repeated. Further repair
loops are not authorized; the parent separately authorized one supported
Codex-verifier attempt for the missing fifth result, with the same candidate.
