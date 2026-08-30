---
title: "AR-20: Validate documentation ledgers against canonical full history"
status: done
category: roadmap
created: 2026-07-13
updated: 2026-07-14
tags: [ci, documentation, git, testing, release]
related:
  - docs/decisions/0025-self-contained-linked-documentation.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-20
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/21"
depends_on: []
blocks: [AR-17]
---

# AR-20: Validate documentation ledgers against canonical full history

## Problem

The hosted documentation-ledger gate ran against GitHub Actions' default
depth-one synthetic pull-request merge checkout. `scripts/update_worklog.py
--check` derives the canonical worklog from every durable substantive commit,
so it saw only the ephemeral merge commit and incorrectly reported a current
full-history index as stale.

Merely fetching complete history for the synthetic merge is also incorrect:
the temporary merge commit is not part of the branch and cannot be recorded in
its ledger.

## Current state

Disposable checkouts reproduced all three cases. A depth-one synthetic merge
fails, and a full-history synthetic merge remains an invalid ledger input. A
complete checkout of the durable pull-request head passes the current worklog
check. Python 3.14 is unrelated; that matrix entry is simply the sole owner of
the documentation-ledger gate.

## Approach

Keep source, test, dependency, and whitespace checks on GitHub's pull-request
merge result. Immediately before documentation validation, re-check out the
complete durable pull-request head, or the current commit for push and manual
runs. Assert both non-shallow history and the expected head before running the
validators. Keep credentials non-persistent and limit the additional fetch to
the single ledger-owning matrix entry.

## Dependencies

This bug was surfaced by AR-17's final hosted matrix. The canonical-history
Ubuntu/Python 3.14 ledger job passed, enforcing ADR-0025's
planning-to-evidence chain through the pinned, read-only workflow boundary
governed by ADR-0037.

## Acceptance

- [x] A depth-one synthetic merge reproduces the stale worklog-index failure.
- [x] Full synthetic-merge history is rejected as a non-durable ledger input.
- [x] Tests and merge-safety checks continue to run against the PR merge result.
- [x] The ledger gate receives the complete durable PR head or push commit.
- [x] CI asserts the checkout is non-shallow and at the expected commit.
- [x] Credentials remain non-persistent and ordinary jobs remain shallow.
- [x] A workflow regression test binds the ledger gate to this checkout.
- [x] Hosted Ubuntu/Python 3.14 documentation-ledger validation passes.
- [x] The reviewed fix is merged and tracker issue #21 is closed.
