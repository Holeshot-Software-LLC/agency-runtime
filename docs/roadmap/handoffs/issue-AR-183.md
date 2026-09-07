---
title: "AR-183 private POSIX producer evidence handoff"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, release, packaging, linux, reproducibility]
related:
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/roadmap/acceptance/evidence/AR-183-AR-184-private-linux-producer-20260907.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-183
branch: codex/ar183-private-producer-evidence
evidence_commit: 2274823ca3d56ddeaa78cd69cf8a6d9dedf3407c
minimum_ledger_commit: 99805b592457996a908cf88fc99b5e98e02169da
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-183 private POSIX producer evidence handoff

## Checkpoint

The September 7 publication follows AR181 PR #731/main2274823c and its
immediate merge ledger. The independent producer uses a separate clean
detached worktree at08fab1c4, not the later evidence-writing branch. This
package records the Linux proof and preserves the Windows-only hold.

## Completed evidence

The real detached Linux/Python 3.12.3 producer under `umask 077` emits its
portable wheel and sdist. Strict Twine and the independent explicit `portable`
verifier exit zero. Source remains clean and detached after production.

The shared AR-183/AR-184 receipt records exact commands, artifact hashes,
sizes and canonical output mode counts. Wheel ordinary files normalize to
`0644`, RECORD to `0664`; sdist files normalize to `0644`, directories to
`0755`. The four focused canonicalizer/build/verifier/release-package modules
pass 498 tests with one native-Windows observation skipped in 40.38 seconds.

## Exact blocker

Neither a native Windows producer nor same-SHA Windows/Linux sdist equality
or merged three-file verification has run. Those criteria remain unproven;
the issue is still `in_progress`. No acceptance verifier or verdict was run
for this evidence-only package. Tracker URL remains the canonical null value;
parent reconciliation owns any tracker/registry change.

## Same-task continuity

Continue same-task normal PR/merge publication, then reuse the portable receipt
for AR184. Preserve other workers' edits. The user reserves Windows work for a
Windows machine; context thresholds do not require waiting or task transfer.

## Next bounded work package

1. Parent reviews and publishes the Linux evidence with its required ledger.
2. Reuse the shared receipt when reconciling AR-184; do not rebuild Linux
   merely because the same producer criterion appears twice.
3. Leave both cross-platform criteria explicitly open for owner Windows work.
   Compare only identical source SHAs, rebuilding both sides if necessary.

## Verification

Canonical builder, strict Twine and explicit portable independent verifier:
all exit zero at the immutable source SHA above. Focused tests: 498 passed,
one skipped. Exact commands, stdout and artifact identities are preserved in
the repository-local shared receipt. No source/runtime behavior was edited.
The worker's initial docs check found only the inherited08fab1c4 merge ledger
gap on its old base, also reproduced on pristine source. Publication now
contains that already-recorded merge; full record gates are checked again.

## Constraints

No owner installation, profile, credential, provider or native-host changes.
No Windows execution, exhaustive corpus, coverage shards, compatibility
matrix, signing, package upload or public release. Builder evidence is not an
acceptance verdict and one Linux pair is not cross-platform release proof.
