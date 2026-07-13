---
title: "AR-23: Stabilize hosted Windows PowerShell integration gate"
status: in_progress
category: roadmap
created: 2026-07-13
updated: 2026-07-13
tags: [windows, testing, ci, powershell, reliability]
related:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-23
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/24"
depends_on: []
blocks: [AR-17]
---

# AR-23: Stabilize hosted Windows PowerShell integration gate

## Problem

The first PowerShell companion integrations on both hosted Windows matrix jobs
can exhaust the test-only 20-second allowance. Later companion cases and all
exact-stdin boundary cases on the same transport path pass, leaving a false
negative in the release gate after the runner warms up.

## Current state

Windows Python 3.10 timed out in the first two companion parameters and Python
3.14 timed out in the first three. Each timeout observed the script's first-line
startup marker, but the marker has no timestamp and can be written near the
deadline after endpoint scanning and PowerShell cold start. Production command
delegation retains its independent 3,600-second default timeout.

## Approach

Increase only the Windows PowerShell integration-test allowance to a bounded 60
seconds. Leave production process transport and timeout behavior unchanged. Run
the focused native Windows companion and stdin-boundary cases, then require both
hosted Windows versions to pass before merge.

## Dependencies

This blocks AR-17's portable release gate. It does not change the product's
delegation contract or introduce a new durable architectural decision.

## Acceptance

- [x] Both failed jobs are diagnosed against their complete failure summaries.
- [x] Production delegation timeout behavior remains unchanged.
- [x] The Windows-only integration allowance has bounded hosted-runner margin.
- [x] Focused native Windows companion and stdin-boundary tests pass.
- [ ] Hosted Windows Python 3.10 and 3.14 suites pass.
- [ ] Review, merge, roadmap/worklog reconciliation, and tracker closure pass.
