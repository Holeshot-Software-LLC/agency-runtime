---
title: "Retire a duplicate mandatory coverage checklist"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, coverage, evidence, supersession]
related:
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/acceptance/evidence/AR-145-instrumented-contracts-20260907.md
  - docs/decisions/0224-retire-duplicate-mandatory-coverage-checklist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c09eb1b88ef55d5f903af6cae25f53876b90b34f
short: c09eb1b8
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
---

# Worklog detail: Retire duplicate coverage checklist

## Approach and decision

Apply ADR-0105's existing optional-exhaustive policy instead of treating
AR-145's historical mandatory release gate as current. ADR-0224 retires this
duplicate checklist and explicitly transfers still-relevant fixture/aggregate
diagnostic work to AR-176. It is not an acceptance verdict or threshold waiver.

## Challenges and alternatives

The original synchronization/reporting repairs are already in the tests.
Leaving the old failure narrative current invites another expensive full run;
marking the old criteria done would invent missing aggregate evidence.
Preserve that history and every criterion, retain the configured 97-percent
floor and record the actual remaining owner. Also record release-checklist UI
command drift under the existing AR-156 workflow-doc reconciliation, without
changing its implementation in this package.

## Verification

Forty-one focused observation, persisted-owner, synthetic-report and authority
cases pass under branch instrumentation in 12.08s. No repository-wide aggregate
report, native Windows or hosted dispatch ran. Product/test/script bytes are
unchanged from accepted AR-138 candidate 2ecde1a5; prior fast-spine/UI/conformance
receipts and AR-140's standalone performance report retain their exact scopes.
Metadata, policy availability, exact worklog, strict docs/tracker and diff pass.

## Follow-ups

AR-176 retains the six known stale fixtures and requested coverage diagnostics.
AR-156 retains the documented UI command discrepancy. Counts become 40 actual
open trackers plus 96 unfinished legacy records (136), without a tracker
closure. After publication, AR-150 follows; Windows-only AR-147 stays with owner.
