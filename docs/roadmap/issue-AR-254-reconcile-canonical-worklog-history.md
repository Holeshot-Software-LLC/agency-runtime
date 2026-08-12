---
title: "AR-254: Reconcile canonical worklog history after merged ledger violations"
status: in_progress
category: roadmap
created: 2026-08-11
updated: 2026-08-12
tags: [documentation, governance, ci, worklog, history]
related:
  - docs/roadmap/handoffs/issue-AR-236.md
  - docs/worklog/README.md
  - scripts/update_worklog.py
  - scripts/verify_docs.py
supersedes: []
superseded_by: null
type: issue
epic: documentation
issue_id: AR-254
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/272"
depends_on: []
blocks:
  - AR-236
---

# AR-254: Reconcile canonical worklog history after merged ledger violations

## Problem

Canonical history originally contained 13 commits missing from the generated
worklog and four published `docs(worklog):` commits that also changed the
AR-119 roadmap record. The automatic PR gate checks full canonical history, so
every later PR failed documentation verification even when its own ledger was
correct.

## Current state

The deterministic generator and exact immutable-history exceptions pass on the
pre-Job-B branch. Rebasing PR #270 onto merged PRs #271 and #273 rewrote 21
branch commits and added seven canonical commits, so the checked-in table is
again stale until regenerated. This is expected generated-history drift, not a
new exception or permission to weaken future enforcement.

## Approach

- Rebuild the worklog from full Git history with the canonical generator.
- Record the four immutable violations in provenance and grandfather only their
  exact full SHAs.
- Keep the allowed-path rule unchanged for every other commit.
- Prove both documentation commands and the hosted canonical-history gate pass.

## Dependencies

- PR #270 / AR-236 is the first observed downstream gate blocked by this
  canonical-history drift.

## Acceptance

- [x] The generated worklog exactly matches full repository history.
- [x] Only the four named published commits bypass the ledger-path rule.
- [x] A new mixed `docs(worklog):` commit still fails verification.
- [x] `scripts/update_worklog.py --check` and `scripts/verify_docs.py` pass.
- [ ] The PR #270 automatic gate reaches a green aggregate.

## Implementation checkpoint

Rebased commit `d1f8ed28` rebuilds the canonical index and records the four
published violations. Hosted Linux then exposed clone-dependent `%h`
abbreviation width; rebased commit `a78653ce` derives collision-checked
eight-character IDs from full SHAs and proves invalid, colliding, and
mixed-ledger cases. Documentation verification and 143 focused tests passed
before the Job B rebase. The post-rebase AR-236 recovery checkpoint regenerates
the table against `c7cf1d96` and reruns the same exact checks.
