---
title: "Worklog detail: Audit guided dashboard asset budget"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [testing, dashboard, packaging, release]
related:
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 80d898801c5b1703a1d1b7d06cbd9d62671a1a2a
short: 80d89880
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
---

# Worklog detail: Audit guided dashboard asset budget

## Purpose

Restore the release pre-push gate after the required AR-290 setup journey
exceeded the dashboard's prior audited asset ceiling.

## Approach

Measure each guarded asset against current main, retain the fully tested setup
surface, and raise the ceiling only from 360 to 368 KiB. Record the exact
374,372-byte candidate so the remaining 2,460-byte margin stays below one
percent and future growth requires another explicit audit.

## Challenges encountered

The push hook surfaced the regression only after earlier source and installed
gates were green. A restricted direct pytest rerun could not attest its private
test root; the identical command under the normal user boundary then exercised
the actual gate without bypassing it.

## Decisions and alternatives

The setup UI was not removed or minified outside its branch-tested source form.
The gate was not skipped and was not given broad headroom. No durable product or
security decision changed, so a new ADR is unnecessary.

## Verification

- The unchanged gate failed at 374,372 bytes against 360 KiB.
- Current main measured 365,821 bytes; AR-290 accounts for the 8,551-byte delta.
- All 161 workflow-contract tests pass with warnings strict after the audit.
- Focused Ruff, 830-file documentation validation, and diff checks pass.

## Follow-ups

Create and link the AR-295 tracker item only after explicit tracker
authorization. Retry the ordinary pre-push gate; never use its skip override.
