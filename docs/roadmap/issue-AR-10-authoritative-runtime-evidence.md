---
title: "AR-10: Make runtime evidence authoritative"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-11
tags: [evidence, delegation, correctness]
related:
  - docs/decisions/0007-six-line-evidence-header.md
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0016-central-finalization-and-session-correlation.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-10
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/10"
depends_on: []
blocks: [AR-07, AR-12]
---

# AR-10: Make runtime evidence authoritative

## Problem

Agency Runtime must never claim that a specialist loaded, a delegation ran, a
model resolved, or work completed unless a correlated runtime event proves it.
The current implementation can promote failed or unrelated tool calls and can
accept model-authored header claims that disagree with canonical storage.

## Current state

Runtime event promotion is now failure-aware. Delegation events use stable
work-unit identity; duplicate IDs and missing results fail; unsuccessful
prerequisites skip dependents; and failed worktree branches are excluded from
merge. Finalization fills or overwrites response evidence from canonical store
records and rejects spoofed claims on every attempt.

Routing decisions receive a fresh trace and are stored without the raw prompt by
default. SQLite enforces unique trace parents and migrates legacy orphaned
evidence. Focused evidence, delegation-lifecycle, routing, and storage tests
exercise the failure paths. Tracker issue #10 remains open because this
documentation change does not perform issue closure.

## Approach

Introduce typed, correlated event outcomes keyed by session, turn, trace, and
work-unit identity. Promote evidence only after verified success, gate dependent
execution on prerequisite success, and derive final headers from authoritative
events. Treat absent, ambiguous, spoofed, and failed evidence as explicit
non-success states.

## Dependencies

None. This correctness boundary must land before production host wiring and the
operator dashboard can safely expose runtime claims.

## Acceptance

- [x] Failed load or delegation calls never create success evidence.
- [x] Every delegation event correlates to the intended work-unit identity.
- [x] Dependents do not execute after a prerequisite fails.
- [x] Duplicate work-unit IDs and missing results fail explicitly.
- [x] Final headers are derived from or reconciled with canonical evidence.
- [x] Spoofed or stale claims are rejected in automated tests.
