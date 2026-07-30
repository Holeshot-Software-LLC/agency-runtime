---
title: "Worklog detail: Bind recruiter repair evidence"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [workforce, inference, recruiter, repair, evidence, security]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/handoffs/issue-AR-202.md
  - docs/roadmap/handoffs/issue-AR-203.md
  - docs/decisions/0115-aggregate-bounded-recruiter-repair-failures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: b45bd28f6b82f4915e81b7b47c20f34a8e3b521b
short: b45bd28
date: 2026-07-30
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/188
related_issues:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
---

# Worklog detail: Bind recruiter repair evidence

## Purpose

Resolve the two valid post-merge P1 findings on PR 187 before asking the owner
to trust its hook hashes or spending the single replacement README-story trial.

## Approach

The recruiter accumulator now records the exact ordered failed-unit tuple.
Every repair response is schema-checked into temporary rows and must match that
tuple before any retained nomination can change. A full-plan, partial, or
reordered response therefore fails before it can overwrite an already valid
row.

Durable validation evidence continues to accept only governed planned-unit
shapes and allowlisted reason codes. Each accepted unit identity now passes
through the common routing identity projection, so an identifier containing a
sensitive marker becomes a stable SHA-256 identity. Canonical digests are
accepted unchanged to preserve normalization idempotence.

## Challenges encountered

The Codex review contained three P1 threads. Git ancestry disproved the worklog
claim: merge `26a3911` has the expected second parent and preserves
`d470993` plus its ledger commits. The other two findings exposed real
boundaries that existing prompt and semantic tests did not cover. Red
regressions first reproduced both defects. The restricted dashboard test
runner stopped at Windows `spawn EPERM`; its owner-context rerun passed. A
parallel quiet Python run completed after its output channel closed, so the
same named spine was rerun alone to retain auditable output.

## Decisions and alternatives

Online inference remains authoritative for specialist ranking and selection.
The repair does not reintroduce deterministic role anchors or accept an
expanded repair merely because every row belongs to the original plan.
ADR-0115 owns the exact repair-set and durable identity boundaries.

## Verification

- The changed recruiter and receipt boundary passes 108 tests with 1 skipped.
- Decision conformance passes its baseline and kills 23/23 mutations with zero
  survivors or invalid results; source inputs remain unchanged.
- The named fast Python spine passes 675 tests with 6 skipped.
- Dashboard UI passes 109 tests.
- Routing evaluation 1.3.0 passes every gate, including routing p95 5.013 ms
  and cache-hit p95 1.404 ms.
- Documentation validation passes 552 files; Ruff checks and format-validates
  all 603 Python inputs; `git diff --check` passes.

## Follow-ups

Publish the replacement pull request, merge and exact-install its accepted
revision for Codex, ZCode, and the local dashboard, then perform the one
attended dashboard-open and hook-trust step. Run exactly one replacement trial.
If the same recruiter boundary fails again, stop for owner direction under
[AR-203](../roadmap/issue-AR-203-prove-product-canary-write-and-activation.md).
