---
title: "AR-254: Reconcile canonical worklog history after merged ledger violations"
status: in_progress
category: roadmap
created: 2026-08-11
updated: 2026-08-11
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

Canonical `main` contains 13 commits missing from the generated worklog and
four published `docs(worklog):` commits that also changed the AR-119 roadmap
record. The automatic PR gate checks full canonical history, so every later PR
fails documentation verification even when its own ledger is correct.

## Current state

`scripts/update_worklog.py --check` reports a stale index. After rebuilding the
index, `scripts/verify_docs.py` rejects published commits `56e7dee0`,
`410c1d1d`, `66f62b90`, and `d38e08b5`. Rewriting those shared commits is not
safe. Future mixed ledger commits must still fail.

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
