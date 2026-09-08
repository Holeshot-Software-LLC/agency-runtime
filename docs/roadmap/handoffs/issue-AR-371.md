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
evidence_commit: 9b15107a3769ac475fd2d1a72d4f6598b7d1cef1
minimum_ledger_commit: 9b15107a3769ac475fd2d1a72d4f6598b7d1cef1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/521
---

# AR-371 next-turn resident binding recovery capsule

## Checkpoint

Branch-only step 2 candidate; metadata names the clean source base, not an
accepted or installed changed build. Worktree:
`/tmp/agency-runtime-ar371-recover-closed-resident-claims`.
Phase: implementing. Existing step 1 header evidence/history is preserved.

## Completed evidence

Source trace confirms every conflicting pending trace was refused forever.
Candidate permits the existing CAS to move a closed old claim to a newer/latest
same-host/session turn only at its valid claim boundary. Delivery stays pending,
with identical mode/restore generation and all epoch/kernel checks retained.
Thirty-two new real-Store cases and an updated hook lifecycle regression are
written, not run. Scoped Ruff lint/format and diff checks pass.

## Exact blocker

Frozen-source review, test execution, isolated acceptance and native proof are
pending. No accepted-completion claim; tracker #521 stays open/in_progress.

## Same-task continuity

Owner requested code-first with no new tests, CI, live canaries or model calls.
No owner Store read/write, profile mutation or host operation was performed.
Continue in this same task after recording the substantive/ledger checkpoint.

## Next bounded work package

Finish bounded independent source review; fix scoped findings, integrate current
main and publish an in-progress PR. Leave tests and acceptance explicit until
the owner reopens execution. Do not close the issue on static evidence.

## Verification

Static commands and exact written test boundaries are in the source evidence
receipt. A test assertion's presence is not a passing test result.

## Constraints

No timer-based stealing, read-time release, fabricated ack/reuse, raw body
logging or cross-host/session recovery. The same fail-open turn may still be
awaiting Stop; run closure alone is not abandonment. Missing/retired run proof,
unknown status, invalid timestamps, active prior turns and stale candidates stay
closed. Additional restore generations must not be consumed early.
