---
title: "AR-410 Claude transport warm-up recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, claude, canary]
related:
  - docs/roadmap/issue-AR-410-disable-claude-warmup-staffing.md
  - docs/roadmap/acceptance/evidence/AR-410-claude-warmup-control-20260907.md
  - docs/decisions/0237-isolate-claude-bootstrap-from-agency-evaluation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-410
branch: codex/ar410-disable-claude-warmup-staffing
evidence_commit: 0e8e9307071bd25260d17fb623ebc7d88c56aef0
minimum_ledger_commit: fb3ef70efaba7693953435cf5eb398c9ec3a2a3e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/744
---

# AR-410 Claude transport warm-up recovery capsule

## Checkpoint

Branch-only reviewed source; metadata identifies source and immediate ledger,
not an accepted or installed changed candidate. Phase: fast_verification.
Only warm-up argv disables native hooks. Actual nonce argv has no override;
master control, requested authority and every existing proof gate are unchanged.

## Completed evidence

Final seven focused tests pass in 0.22s. Independent final review: 28 pass in
1.37s, no scoped source findings. Initial private-control approach was rejected
despite 40 green tests; explicit installed owner binding defeated it. Preserve
that finding and intermediate fixture errors in the evidence receipt.

## Exact blocker

Tracker #744 exists. Isolated acceptance, installed candidate and native
activation remain pending.
No successful native result is claimed. No acceptance model calls were run.

## Same-task continuity

Worktree: `/tmp/agency-runtime-ar410-disable-claude-warmup-staffing`.
Runtime ownership is canary_backends.py and the new focused test module;
record files are scoped to AR-410/ADR-0237. Preserve parallel workers' changes.

## Next bounded work package

Complete record/tracker parity, publish reviewed source in_progress, then run
isolated acceptance and exact-installed native verification.
Do not relaunch the earlier failed canary unchanged.

## Verification

Use the exact focused command in the evidence receipt. The parent owns artifact
build, install and the changed-candidate live check. A simulated host cannot
prove second-session plugin activation after disabled bootstrap.

## Constraints

No owner profile/control, provider, staffing budget, trust, permission or
deadline changes. No weakened nonce/finalization/child-card proof. Record
failures honestly; keep status in_progress until full evidence exists.
