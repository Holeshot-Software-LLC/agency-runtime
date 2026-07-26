---
title: "Worklog detail: Record parallel evidence and HTTP gap"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, performance, http, reliability, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 74468aa
short: 74468aa
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
---

# Worklog detail: Record parallel evidence and HTTP gap

## Purpose

Keep the production-readiness recovery state honest after three rejected
parallel samples, and govern the public HTTP disconnect defect discovered by
the loaded corpus before implementation begins.

## Approach

AR-156 now records each failed run ID, exact elapsed time, passing-shard count,
failure mechanism, and the rule that none is benchmark evidence. It also
records the same-runtime path A/B and the bounded short-path repair. The active
AR-119 capsule points at the latest clean code/ledger pair and makes the matched
one-worker control explicit.

AR-157 distinguishes public API response-write behavior from the already
completed dashboard-only AR-94 scope. Its acceptance contract requires one
shared platform classifier, quiet primary and defensive-response disconnects,
degraded observation evidence, and unchanged genuine-failure logging.

## Challenges encountered

The full loaded corpus revealed both a test-budget symptom and a real transport
defect. They are recorded separately: a 15-second loopback client budget may be
appropriate for loaded testing, but it does not repair the server's second
write and traceback behavior after the client has gone away.

## Verification

- Documentation metadata passed for 402 Markdown files.
- Documentation validation passed for all 402 files.
- Policy availability, worklog generation, and diff checks passed.
- The active recovery capsule remains below 180 lines and 12 KiB.

## Follow-ups

Implement AR-157, then collect green four-worker and matched one-worker timing
arms before making any local speed or hosted-cost claim.
