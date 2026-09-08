---
title: "AR-371 next-turn resident binding recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, resident-managers, lifecycle, fail-open]
related:
  - docs/roadmap/issue-AR-371-stalled-binding-makes-the-header-claim-none.md
  - docs/roadmap/acceptance/evidence/AR-371-next-turn-binding-recovery-20260907.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0152-fail-open-with-honest-header-when-no-specialist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-371
branch: codex/ar371-recover-closed-resident-claims
evidence_commit: c3b217f1bca39968f19f9935fe7c44a1c236ed9e
minimum_ledger_commit: 5538beb6969ee3c63922143236e5176f54c5df82
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/521
---

# AR-371 next-turn resident binding recovery capsule

## Checkpoint

Branch-only step 2 candidate; metadata names the first source/ledger checkpoint,
not an accepted or installed build. Final retention correction and wrap-up
evidence accompany this capsule; exact history is in the worklog. Worktree:
`/tmp/agency-runtime-ar371-recover-closed-resident-claims`.
Phase: fast_verification. Existing step 1 header evidence/history is preserved.

## Completed evidence

Source trace confirms every conflicting pending trace was refused forever.
Candidate permits the existing CAS to move a closed old claim to a newer/latest
same-host/session turn only at its valid claim boundary. Delivery stays pending,
with identical mode/restore generation and all epoch/kernel checks retained.
The final source also checks retired-turn ordering through the existing verified
HMAC session tombstones. Thirty-six new real-Store cases plus nearby lifecycle
and header checks passed: 46 tests in 11.90s. Bounded independent source review
reported no remaining scoped finding; scoped Ruff lint/format and diff checks pass.

## Exact blocker

Broad suite, isolated acceptance and installed native proof remain pending.
No accepted-completion claim; tracker #521 stays open/in_progress.

## Same-task continuity

Owner initially deferred tests, then authorized focused wrap-up execution while
requesting a clean stopping point and parent-run installation/live evaluation.
No owner Store read/write, profile mutation or host operation was performed.
Finish the clean handoff; no new triage or provider/native calls in this task.

## Next bounded work package

Parent integrates/publishes the reviewed in-progress candidate, then owns the
combined artifact installation and native evaluation. Do not close the issue
on source review and focused tests alone; preserve outstanding acceptance gates.

## Verification

Exact focused command, result and review/retention scope are in the source
evidence receipt. No full trim-command, broader suite or native claim is made.

## Constraints

No timer-based stealing, read-time release, fabricated ack/reuse, raw body
logging or cross-host/session recovery. The same fail-open turn may still be
awaiting Stop; run closure alone is not abandonment. Missing/retired run proof,
unknown status, invalid timestamps, active prior turns and stale candidates stay
closed. Additional restore generations must not be consumed early.
Newer retired turns block conservatively per session because tombstones retain
no host field; retirement cannot make an older candidate latest again.
