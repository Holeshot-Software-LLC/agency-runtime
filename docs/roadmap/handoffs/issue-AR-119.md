---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-09-05
tags: [handoff, vision, inference, child-delivery, contractors, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/acceptance/evidence/AR-348-installed-delivery-20260905.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-oldest-first-disposition
evidence_commit: d9ea419bb85f01108387e8eaae57396c636892b4
minimum_ledger_commit: 4d0bd08c472de5160f767ac72bb7d7d0d414cf33
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

## Checkpoint

September 5 owner priority is oldest-first backlog reconciliation: one item,
PR, merge, then next, with Windows work reserved for the owner. AR-115 was
retired in PR #690 at d9ea419b; #127 is CLOSED/NOT_PLANNED. AR-119 absorbs its
surviving ordinary staffing/header outcome, not its obsolete selection design.

AR-119 is retained in_progress. This package reconciles its stale current-state
presentation and capsule and aligns the matrix's R1 narrative with the already
recorded retraction. It does not implement or certify five-host completion.
Current owned branch is above; shared main is d9ea419b.

## Completed evidence

- The founding vision remains unchanged: inference owns selection, current-turn
  cards load into callers and harness-native children, Agency does not spawn,
  genuine gaps use the contractor lifecycle, cards expire per turn, unavailable
  Agency does not withhold host service, and all five hosts share the contract.
- The canonical matrix still targets 1bd7e37c with an August 18 cutoff and
  vision digest 8d81be4301ea76b3820b792f54842916321a9557b4a13fce58d6688abe962e50.
  Three of 45 cells are proven (R2/R3/R7 Claude); 42 are unproven. All rows and
  layer receipts are preserved. Historical proof is not September proof.
- Source is unchanged from installed AR-348 revision 0309f251. Fresh AR-115
  focused checks: 183 passed (19.11s); fast spine: 1075 passed/three skips
  (68.74s); UI: 138 passed. Earlier installed eight-check deterministic smoke
  is not a five-host live canary. No new live inference was run in this package.
- The prior August 25 capsule is retained in Git at d9ea419b, including its
  checkpoint f2c472b5/ledger a04a1d2f, failed draws, Store hashes and native
  receipts. Detailed history stays in the canonical issue and vision-loop
  record. Its host availability and permission statements are dated history.
- In particular, the prior Hermes async draw remains failed: parent
  705cfd21-216b-4476-8339-88e73eebb09c finalized response_invalid before child
  completion; delegation 7333c869-49f5-4416-b4e4-11d80a7e1c9f had no validated
  specialist/activation/terminal/delivery proof. Child route 9ed701ed-dadd-4c06-
  b5ee-4b3504504643 was native_child_inference_failure. Exit zero was not proof.

## Exact blocker

Current exact-candidate installed/live evidence is incomplete, not waived.
AR-252 owns host-backed accepted outcomes and automatic promotion; AR-253 owns
host dispatch/cold-latency remeasurement; AR-255/281 own native-child evidence;
AR-125 owns independent matched-value evaluation. The 15,000 ms cold floor is
unchanged. The old 88.3s/195.9s latency sample is historical, not a new result.

The current session's header is unverified. A requested Codex-only refresh
returned exit 1: files installed, activation required, hook trust unverified,
and a projection mismatch against the separately retained OpenClaw package.
No fresh-session activation was verified. Do not silently grant trust, create
credentials, restart the live gateway, or mark a matrix cell proven.

## Same-task continuity

Keep the issue and #132 open. Record this bounded disposition through an owned
worktree PR, then proceed to AR-120 under AR-404; do not stall on this umbrella.
At the 50-percent checkpoint commit the smallest safe substantive/ledger pair
and continue. Do not create empty recovery commits or restart unchanged draws.

## Next bounded work package

Publish this record reconciliation; the next backlog item is AR-120.
A later AR-119 live package must choose one exact candidate and host obligation
from the existing dependency records, establish its actual credential/trust/
availability boundary, and collect the host-authored proof required by the
matrix. Operator-only boundaries are explicit exits, not retry loops.

## Verification

Record regressions: 93 passed (3.32s). Metadata and strict docs pass for 1115
Markdown files; strict tracker parity passes for 397 mapped records. All matrix
and layer rows, candidate/cutoff/vision identity, and founding text are unchanged
against d9ea419b; runtime/test/script diff is empty. Diff check passes.

Run documentation metadata, policy availability, exact worklog, strict docs and
tracker parity, focused document/tracker regressions, and diff checks. Compare
all matrix/layer rows and candidate/cutoff/vision identity against d9ea419b.
Retain current source-test receipts above without calling them live evidence.

## Constraints

Owner-authorized pushes, PRs, merges and justified tracker closures are current;
the prior capsule's local-only restriction is historical, not current authority.
No native specialist was staffed or spawned for this review. Do not restore
Job B, planned work units, heuristic staffing, or the superseded Why/How header.
No Windows work, trust bypass, credential creation, provider-policy change,
unmanaged gateway interruption or exhaustive workflow dispatch in this package.
