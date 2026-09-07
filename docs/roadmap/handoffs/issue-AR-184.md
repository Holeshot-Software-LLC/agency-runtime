---
title: "AR-184 private POSIX sdist recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, packaging, linux, windows]
related:
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/roadmap/acceptance/evidence/AR-183-AR-184-private-linux-producer-20260907.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-184
branch: codex/ar184-linux-producer-reconciliation
evidence_commit: 30214408a0073e69550ba695b99ef68d9238f857
minimum_ledger_commit: 5ccca3c36e9ee63b833531787e8bddcfcdcaa649
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-184 private POSIX sdist recovery capsule

## Checkpoint

The records-only package follows AR183 PR #733/main30214408 and its merge
ledger. Existing source-mode implementation is retained, with original
acceptance checkbox states unchanged. No new acceptance verdict.

## Completed evidence

The shared receipt proves real clean detached08fab1c4 Linux/Python3.12.3
canonical production under umask077, strict Twine and independent explicit
portable verification, all exit0. Sdist SHA2b0887ed60ab80caf71b6ad13efa27525f4d9e4aff845d74db8200989bf68d4d;
2,291 canonical0644 files and40 canonical0755 directories, no other types.
Four focused modules:498passed/one native-Windows skip in40.38s.
Exact-mode and byte-convergence regressions are included.
This reuses AR183's actual producer, not a new run or different candidate.

## Exact blocker

Same-SHA native Windows/Linux sdist equality and merged three-file release
set verification are unproven. Owner reserved Windows work for Windows.
Retain in_progress; no blanket build failure or new Linux defect is asserted.

## Same-task continuity

Continue non-Windows oldest-first backlog in this same task after the clean
substantive/ledger checkpoint. No empty commit, repeated Linux build or
context-threshold waiting. Preserve other worktrees.

## Next bounded work package

Publish this retained disposition through normal PR/merge, then AR185.
Future owner comparison must use08fab1c4 on Windows or rebuild both platforms
at one newly frozen SHA. Do not compare unrelated source revisions.

## Verification

Reuse the shared source/build/command receipt; run metadata, policy, ledger,
docs, strict tracker, Ruff and whitespace publication checks. No native
Windows, exhaustive corpus, coverage shards or compatibility matrix.

## Constraints

No owner host installation, credential/profile/trust changes, model calls,
signing, upload or release claim. One Linux portable pair is not a merged
cross-platform release set.
