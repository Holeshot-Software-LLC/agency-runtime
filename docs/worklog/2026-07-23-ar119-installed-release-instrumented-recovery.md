---
title: "Worklog: Record installed-release instrumented recovery"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, instrumentation, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: a6007afc713a5eadb4b1cbbc753f93f747457591
short: a6007af
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record installed-release instrumented recovery

## Purpose

Preserve a second complete installed-release Agency outcome before benchmark
projection, determine whether the preceding generation-preparation abstention
repeats under identical controls, and advance AR-119 without changing governed
product or policy semantics from configured-model variance.

## Approach

The prior pass-through benchmark router was reduced to the one canonical
installed-cross-platform-release case. It called `plan_and_staff_workforce`
with the matched harness arguments, atomically serialized the unchanged outcome
outside the repository, and returned it to the normal scorer. The run retained
the audited Store snapshot, Windows/Codex context, full tool union, configured
provider and model, 15000 ms cold gate, and one-call fast budget.

## Challenges encountered

The Agency arm recovered, so the locked next action was a complete unchanged
19-case corpus. Before that expensive run began, local telemetry reached 48.4%
remaining and triggered the repository's mandatory checkpoint rule. The corpus
was therefore left unstarted rather than risking an incomplete live package.

## Decisions and alternatives

The accepted five-unit plan required only `implementation` for its first
software unit and selected `cross-platform-installer-engineer` at confidence
and margin 1.0. It did not repeat `generation-preparation`. This directly
supports the existing plan-shape-variance classification and does not justify
a scenario route, capability erasure, worker broadening, parser relaxation,
typed-coverage weakening, latency increase, or call-budget increase.

The upstream arm returned complete typed coverage but exceeded the unchanged
latency gate. That observation remains descriptive; it is not a superiority
claim. A coordination correction prohibited another task dispatch, so this
package stops at the clean ledger checkpoint with corpus ownership unresolved
outside this task.

## Verification

- The instrumented process returned status 0 in 23.807251 seconds; identical
  690,970-byte report/stdout documents had SHA-256
  `20d1e5791d25188f525920b009d07a8b759a088277a581c88739144b90417871`,
  and stderr was empty.
- The complete 56,678-byte Agency outcome had SHA-256
  `de013181e16b869378d746b7a87b52f44c49cc79dd6f813e4260ccd04c48a704`.
- The exact 767-byte projection had SHA-256
  `c1ccfd1db84a7937de026edbdf43a5ae4ff114d57e85f1e7a87b029604de6bd1`.
- The benchmark was valid, Agency passed at 6778.164 ms with complete typed
  coverage, and both arms retained one applied explicit-model call and zero
  forbidden, ineligible, or conflict selections.
- Metadata, policy availability, worklog, documentation, and diff checks passed
  against the final ledger worktree.

## Follow-ups

The next live package remains one unchanged complete 19-case corpus with both
streams captured outside the repository before parsing. No task was dispatched
from this checkpoint. Malformed, absent, or timed-out upstream arms remain
benchmark-validity failures, never losses, and no Agency superiority claim is
available.
