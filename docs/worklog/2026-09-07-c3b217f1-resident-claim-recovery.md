---
title: "AR-371 next-turn resident claim recovery source checkpoint"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [resident-managers, lifecycle, fail-open]
related:
  - docs/roadmap/issue-AR-371-stalled-binding-makes-the-header-claim-none.md
  - docs/roadmap/acceptance/evidence/AR-371-next-turn-binding-recovery-20260907.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0152-fail-open-with-honest-header-when-no-specialist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c3b217f1bca39968f19f9935fe7c44a1c236ed9e
short: c3b217f1
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-371-stalled-binding-makes-the-header-claim-none.md
---

# Worklog detail: fix(residents): recover closed claims only on a later current turn (AR-371)

## Purpose

Bound a closed-trace resident-binding stall without treating preflight failure
as proof that the same native turn no longer awaits Stop. Preserve AR-371's
step 1 header/history; this is an in-progress step 2 implementation.

## Approach

The existing ready/fail-open transaction checks old/new exact same-host/session
runs, recognized closed old status and valid ended_at, increasing positive
turn sequences, and the newest candidate's own active/in-progress or fail-open
claim boundary. The existing full binding CAS retargets pending/last trace while
retaining mode/generation. Kernel and control-epoch validation remain prerequisites.
Only the new trace's own Stop may acknowledge delivery; later restore generations
remain outstanding. Planning/readers gain no write path.

## Challenges encountered

Run closure is not native response completion: fail-open closes before Stop.
Using elapsed time or closed status alone would steal the current delivery.
The candidate instead requires a different, newer, latest exact run. Unknown,
missing, malformed, active, wrong-scope or out-of-order evidence remains refused.
Missing/retired run proof is intentionally not inferred from historical prose.

The earlier AR-367 conflict regression used a closed old turn, so its expected
transition is intentionally updated to recovery. New real-Store cases preserve
the genuinely active-old conflict boundary and show that bookkeeping refusal
does not undo the new fail-open close. All are written assertions, not executions.

## Decisions and alternatives

Existing ADR-0122/ADR-0152 govern; no new staffing, authority, schema or runtime
policy. Reject read-time clearing, timers, unconditional pending reset, fabricated
acknowledgment and early consumption of restore generations.

## Verification

Scoped Ruff lint/format and git diff check passed. Metadata checked 1284 Markdown
documents. Thirty-two new real-Store cases plus the adapted hook lifecycle case
are unrun under the owner's code-first direction. No tests, CI, model/provider
request, native operation or owner Store mutation. At 18.4% remaining telemetry,
this substantive/ledger pair is the bounded clean checkpoint.

## Follow-ups

Finish independent frozen-source review, integrate current main and publish
normally with #521 open/in_progress. Runtime checks, isolated acceptance and
native installed evidence remain pending; do not claim accepted completion.
