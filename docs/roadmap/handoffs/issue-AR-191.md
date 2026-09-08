---
title: "AR-191 obsolete V2 checklist retirement recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, codex, native-child, backlog, governance]
related:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/acceptance/evidence/AR-191-v2-checklist-retirement-20260907.md
  - docs/decisions/0236-retire-obsolete-codex-v2-grant-checklist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-191
branch: codex/ar191-v2-checklist-retirement
evidence_commit: 49bea737318f05667ab72a9c267fda05a31250c6
minimum_ledger_commit: f2114595445eda65b7018fe4c83eae59f0323423
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-191 obsolete V2 checklist retirement recovery capsule

## checkpoint

This records-only retirement is branch-only until parent-coordinated
publication. Substantive `49bea737` and ledger `f2114595` freeze the retirement.
The parent now authorizes publication after AR-190/PR740 merged `d39ec14d`.
A normal merge integrates exact main ledger `f0e38863`, preserving both
histories and the frozen AR-185/190/408/409 acceptance files unchanged.
The proposed disposition is `wont_do`, superseded by AR-255 under ADR-0236,
not `done` or acceptance against all nine historical criteria.

## completed-evidence

- All original criterion wording and eight checked/one unchecked states remain
  verbatim in AR-191. The July state is labelled historical, not current policy.
- Both exact spawn aliases, explicit follow-up aliases, argument preservation,
  truthful exit codes and the existing-Store boundary remain implemented.
- `b222414b` removed the old activation-grant APIs. `7e1b3603` requires
  inference-owned, host-proven delivery and rejects invalid explicit parent
  turns; only omitted turns may use the unique-open-trace fallback.
- Fresh narrow Linux offline tests: 23 passed in 3.47s; exact command/stdout in
  the receipt. Earlier 64 passed in 13.08s is explicitly summary-only history.
- Reused main AR-180 proof covers one restricted no-bypass Codex 0.153.4
  exec-depth-one v6 card, completed child and accepted v4-bound finalization.
  It is not ordinary encrypted-spawn, TUI/Desktop, multi-card or child-only proof.

## exact-blocker

No runtime blocker is introduced by this records-only retirement. Parent
review and PR publication remain before this
branch's disposition is published. No isolated acceptance verdict was requested
or produced. AR-255/AR-180 retain current staffing and broader live obligations;
AR-185/AR-192 retain verification and trust boundaries.

## same-task-continuity

Use the portable evidence rather than repeating the live canary or reconstructing
removed grants. The cumulative 50-percent checkpoint rule requires durable
state, not a fresh task, empty commit or waiting for context to rise.

## next-bounded-work-package

Publish the parent-authorized AR-191 retirement at order45 after AR-189/190;
then release the serial token to AR-192. Current main is merged normally with
all intervening records preserved. The branch includes
registry/queue updates and removes the obsolete AR-180 dependency while
preserving its AR-255 dependency and all broader live gates. AR-255 itself has
only reciprocal `related` links added.
Do not close AR-180 or AR-255 because this obsolete checklist was retired.

## verification

The receipt records the exact fresh 23-case command and exit-zero result.
Documentation-only publication checks are:

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
git diff --check
```

Initial draft metadata (1,240 files), policy, whitespace and exact-original-
checkbox comparison passed. Its four documentation errors were the base merge
ledger, ADR registry row and AR-180 reciprocal dependency. The full publication
checkpoint supplies those records and reruns documentation gates; no prior
failed check is relabelled green. Capsule is below both size limits.
Full-checkpoint metadata/docs (including require-tracker) pass for 1,240 files;
policy, worklog, Ruff lint/format767, diff and repeated original-checkbox
comparison pass. Source/tests/scripts are unchanged from the 23-case proof.
No full corpus, native canary, provider call or Windows check is needed merely
to retire this duplicate checklist.

## constraints

- Preserve every original checkbox; do not invent `satisfied` verdicts or a
  successful July grant graph. Current immutable delivery receipts stay required.
- No restoration of grant issuance or invalid-explicit-turn fallback.
- No owner-profile, trust, credential or Store mutation; no new TUI approval
  or certification of the current parent session is claimed.
- No runtime edits or tracker writes. Parent coordinates sequential PR/merge
  publication; the local substantive and narrow ledger are authorized checkpoints.
